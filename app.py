# app.py
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from pyrogram import Client
from pyrogram.errors import PeerIdInvalid, UsernameNotOccupied, ChannelInvalid
from pyrogram.enums import ChatType
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from config import API_ID, API_HASH, BOT_TOKEN
import logging
import uvicorn

app = FastAPI()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Pyrogram client
bot = Client("info_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# DC locations function (same as before)
def get_dc_locations():
    return {
        1: "MIA, Miami, USA, US",
        # ... (rest of the function)
    }

# Calculate account age (same as before)
def calculate_account_age(creation_date):
    today = datetime.now()
    delta = relativedelta(today, creation_date)
    years = delta.years
    months = delta.months
    days = delta.days
    return f"{years} years, {months} months, {days} days"

# Estimate account creation date (same as before)
def estimate_account_creation_date(user_id):
    reference_points = [
        (100000000, datetime(2013, 8, 1)),
        (1273841502, datetime(2020, 8, 13)),
        (1500000000, datetime(2021, 5, 1)),
        (2000000000, datetime(2022, 12, 1)),
    ]
    closest_point = min(reference_points, key=lambda x: abs(x[0] - user_id))
    closest_user_id, closest_date = closest_point
    id_difference = user_id - closest_user_id
    days_difference = id_difference / 20000000
    creation_date = closest_date + timedelta(days=days_difference)
    return creation_date

# Map user status (same as before)
def map_user_status(status):
    if not status:
        return "Unknown"
    status_str = str(status).upper()
    if "ONLINE" in status_str:
        return "Online"
    elif "OFFLINE" in status_str:
        return "Offline"
    elif "RECENTLY" in status_str:
        return "Recently online"
    elif "LAST_WEEK" in status_str:
        return "Last seen within week"
    elif "LAST_MONTH" in status_str:
        return "Last seen within month"
    return "Unknown"

# Start Pyrogram client at app startup
@app.on_event("startup")
async def start_bot():
    logger.info("Starting Pyrogram client")
    await bot.start()

# Stop Pyrogram client at app shutdown
@app.on_event("shutdown")
async def stop_bot():
    logger.info("Stopping Pyrogram client")
    await bot.stop()

# Root endpoint
@app.get("/")
async def welcome():
    return {
        "message": "Welcome to the SmartDevs Info API!",
        "usage": {
            "endpoint": "/info",
            "query_param": "username",
            "description": "Retrieve information about a Telegram user, bot, group, or channel.",
            "examples": [
                "/info?username=TestUser",
                "/info?username=@TestUser",
                "/info?username=t.me/TestUser",
                "/info?username=https://t.me/TestUser"
            ],
            "response": "JSON object containing entity details (user/bot/channel/group info, account age, data center, etc.)"
        },
        "note": "Ensure valid Telegram credentials are set in config.py."
    }

# Info endpoint
@app.get("/info")
async def get_info(username: str = None):
    if not username:
        raise HTTPException(status_code=400, detail="Username parameter is required")

    # Clean username
    username = username.strip('@').replace('https://', '').replace('http://', '').replace('t.me/', '').replace('/', '').replace(':', '')
    logger.info(f"Fetching info for: {username}")

    try:
        DC_LOCATIONS = get_dc_locations()

        # Try fetching user or bot
        try:
            user = await bot.get_users(username)
            logger.info(f"User/bot found: {username}")
            premium_status = "Yes" if user.is_premium else "No"
            dc_location = DC_LOCATIONS.get(user.dc_id, "Unknown")
            account_created = estimate_account_creation_date(user.id)
            account_created_str = account_created.strftime("%B %d, %Y")
            account_age = calculate_account_age(account_created)
            verified_status = "Yes" if getattr(user, 'is_verified', False) else "No"
            status = map_user_status(user.status)
            flags = "Scam" if getattr(user, 'is_scam', False) else "Fake" if getattr(user, 'is_fake', False) else "Clean"

            return {
                "type": "bot" if user.is_bot else "user",
                "full_name": f"{user.first_name} {user.last_name or ''}",
                "id": user.id,
                "username": f"@{user.username}" if user.username else "None",
                "context_id": user.id,
                "data_center": f"{user.dc_id} ({dc_location})",
                "premium": premium_status,
                "verified": verified_status,
                "flags": flags,
                "status": status,
                "account_created_on": account_created_str,
                "account_age": account_age
            }

        except Exception as e:
            logger.info(f"Username '{username}' not found as user/bot. Error: {str(e)}. Checking for chat...")
            try:
                chat = await bot.get_chat(username)
                dc_location = DC_LOCATIONS.get(chat.dc_id, "Unknown")
                chat_type = {
                    ChatType.SUPERGROUP: "Supergroup",
                    ChatType.GROUP: "Group",
                    ChatType.CHANNEL: "Channel"
                }.get(chat.type, "Unknown")

                return {
                    "type": chat_type.lower(),
                    "title": chat.title,
                    "id": chat.id,
                    "type_description": chat_type,
                    "member_count": chat.members_count if chat.members_count else "Unknown",
                    "data_center": f"{chat.dc_id} ({dc_location})"
                }

            except (ChannelInvalid, PeerIdInvalid) as e:
                error_message = "Looks Like I Don't Have Control Over The Channel" if chat_type == "Channel" else "Looks Like I Don't Have Control Over The Group"
                logger.error(f"Permission error: {error_message}. Error: {str(e)}")
                raise HTTPException(status_code=403, detail=error_message)

            except Exception as e:
                logger.error(f"Error fetching chat info: {str(e)}")
                raise HTTPException(status_code=403, detail="Looks Like I Don't Have Control Over The Group")

    except Exception as e:
        logger.error(f"Unhandled exception: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
