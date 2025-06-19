# app.py
# Copyright @ISmartDevs
# Channel t.me/TheSmartDev

from flask import Flask, request, jsonify
from pyrogram import Client
from pyrogram.errors import PeerIdInvalid, UsernameNotOccupied, ChannelInvalid
from pyrogram.enums import ChatType
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from config import API_ID, API_HASH, BOT_TOKEN
import logging
import os
import asyncio
import atexit
import threading

app = Flask(__name__)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Pyrogram client with session file in /tmp
session_path = os.path.join('/tmp', 'info_bot.session')
bot = Client(
    name="info_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    workdir="/tmp"  # Set working directory to /tmp
)

# Create an event loop for async operations
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

# Function to start Pyrogram client
async def start_bot():
    logger.info("Starting Pyrogram client")
    try:
        await bot.start()
        logger.info("Pyrogram client started successfully")
    except Exception as e:
        logger.error(f"Failed to start Pyrogram client: {str(e)}")
        raise

# Function to stop Pyrogram client
async def stop_bot():
    logger.info("Stopping Pyrogram client")
    try:
        await bot.stop()
        logger.info("Pyrogram client stopped successfully")
    except Exception as e:
        logger.error(f"Failed to stop Pyrogram client: {str(e)}")

# Run bot start in a thread-safe manner
def run_start_bot():
    future = asyncio.run_coroutine_threadsafe(start_bot(), loop)
    future.result()  # Wait for completion

# Run bot stop in a thread-safe manner
def run_stop_bot():
    future = asyncio.run_coroutine_threadsafe(stop_bot(), loop)
    future.result()

# Start a separate thread to run the event loop
def start_loop(loop):
    asyncio.set_event_loop(loop)
    loop.run_forever()

threading.Thread(target=start_loop, args=(loop,), daemon=True).start()

# Start bot when application starts
run_start_bot()

# Register bot stop on application exit
atexit.register(run_stop_bot)

# DC locations function
def get_dc_locations():
    return {
        1: "MIA, Miami, USA, US",
        2: "AMS, Amsterdam, Netherlands, NL",
        3: "MBA, Mumbai, India, IN",
        4: "STO, Stockholm, Sweden, SE",
        5: "SIN, Singapore, SG",
        6: "LHR, London, United Kingdom, GB",
        7: "FRA, Frankfurt, Germany, DE",
        8: "JFK, New York, USA, US",
        9: "HKG, Hong Kong, HK",
        10: "TYO, Tokyo, Japan, JP",
        11: "SYD, Sydney, Australia, AU",
        12: "GRU, São Paulo, Brazil, BR",
        13: "DXB, Dubai, UAE, AE",
        14: "CDG, Paris, France, FR",
        15: "ICN, Seoul, South Korea, KR",
    }

# Function to calculate account age
def calculate_account_age(creation_date):
    today = datetime.now()
    delta = relativedelta(today, creation_date)
    years = delta.years
    months = delta.months
    days = delta.days
    return f"{years} years, {months} months, {days} days"

# Function to estimate account creation date based on user ID
def estimate_account_creation_date(user_id):
    reference_points = [
        (100000000, datetime(2013, 8, 1)),  # Telegram's launch date
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

# Function to map user status
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

# Root endpoint with welcome message and usage tutorial
@app.route('/')
def welcome():
    return jsonify({
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
    })

# Info endpoint
@app.route('/info')
def get_info():
    username = request.args.get('username')
    if not username:
        return jsonify({"error": "Username parameter is required"}), 400

    # Clean username
    username = username.strip('@').replace('https://', '').replace('http://', '').replace('t.me/', '').replace('/', '').replace(':', '')
    logger.info(f"Fetching info for: {username}")

    async def fetch_user_info():
        try:
            user = await bot.get_users(username)
            return {"user": user}
        except Exception as e:
            return {"error": e}

    async def fetch_chat_info():
        try:
            chat = await bot.get_chat(username)
            return {"chat": chat}
        except Exception as e:
            return {"error": e}

    try:
        DC_LOCATIONS = get_dc_locations()

        # Try fetching user or bot
        future = asyncio.run_coroutine_threadsafe(fetch_user_info(), loop)
        result = future.result()

        if "user" in result:
            user = result["user"]
            logger.info(f"User/bot found: {username}")
            premium_status = "Yes" if user.is_premium else "No"
            dc_location = DC_LOCATIONS.get(user.dc_id, "Unknown")
            account_created = estimate_account_creation_date(user.id)
            account_created_str = account_created.strftime("%B %d, %Y")
            account_age = calculate_account_age(account_created)
            verified_status = "Yes" if getattr(user, 'is_verified', False) else "No"
            status = map_user_status(user.status)
            flags = "Scam" if getattr(user, 'is_scam', False) else "Fake" if getattr(user, 'is_fake', False) else "Clean"

            return jsonify({
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
            })

        logger.info(f"Username '{username}' not found as user/bot. Checking for chat...")
        future = asyncio.run_coroutine_threadsafe(fetch_chat_info(), loop)
        result = future.result()

        if "chat" in result:
            chat = result["chat"]
            dc_location = DC_LOCATIONS.get(chat.dc_id, "Unknown")
            chat_type = {
                ChatType.SUPERGROUP: "Supergroup",
                ChatType.GROUP: "Group",
                ChatType.CHANNEL: "Channel"
            }.get(chat.type, "Unknown")

            return jsonify({
                "type": chat_type.lower(),
                "title": chat.title,
                "id": chat.id,
                "type_description": chat_type,
                "member_count": chat.members_count if chat.members_count else "Unknown",
                "data_center": f"{chat.dc_id} ({dc_location})"
            })

        error = result.get("error")
        if isinstance(error, UsernameNotOccupied):
            logger.error(f"Username '{username}' does not exist")
            return jsonify({"error": f"Username '@{username}' does not exist"}), 404
        elif isinstance(error, (ChannelInvalid, PeerIdInvalid)):
            error_message = "Bot lacks permission to access this channel or group"
            logger.error(f"Permission error for '{username}': {str(error)}")
            return jsonify({"error": error_message}), 403
        else:
            logger.error(f"Error fetching info for '{username}': {str(error)}")
            return jsonify({"error": f"Failed to fetch info: {str(error)}"}), 500

    except Exception as e:
        logger.error(f"Unhandled exception for '{username}': {str(e)}")
        return jsonify({"error": "Internal Server Error"}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
