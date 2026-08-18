import asyncio
import time
import re
import os
import datetime

try:
    import uvloop
    uvloop.install()
except Exception:
    pass

from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.network import ConnectionTcpAbridged
from telethon.errors import FloodWaitError

# ================= CONFIG =================
# BEST PRACTICE: Set these in Railway's Environment Variables
API_ID         = int(os.getenv("API_ID", "28807546"))
API_HASH       = os.getenv("API_HASH", "37624d57b1d83e6bb51b2db777658d0f")
BOT_TOKEN      = os.getenv("BOT_TOKEN", "7913078821:AAH_jUTHXlFx66daqBkYY7mKw7UZnwpp_A0")
CHAT_ID        = int(os.getenv("CHAT_ID", "1692583809"))
SESSION_STRING = os.getenv("SESSION_STRING", "1BJWap1wBuzx_OTCt3Xy_83N0Eej5M2__CbVLaXQzxovBXmIbsigVPf9zGOhGRecDxzzU046J-Dg91Oftjxs6vjKHKZqzj-dWrgWOOTvOPjaskIVttRunbZo36Glu4lFv3WDL11YBOZHvvKvJWWhMIT3xoI5icLC2XS6fmx-nvA7uBJoa7UVcyYsaYDVvrBgwqM0d08R0z6iLrbDfz1tP4CFukIafcWIMEyhE84jgXRtTRBkFPboXhL-zmpfkBdsSFDPuP2U5cu8y1BCd2XPiNmjZA2BDFcogTXHcD9BWPbznNLZ6My4SVh1rCp-G7beTbnZOa6KV0QSgRGRWIQKvvT3EQ7j0-9Q=")
SOURCE_CHAT    = "CoinSonarV2"
# ==========================================

# User Client (StringSession is perfect for Railway)
client = TelegramClient(
    StringSession(SESSION_STRING), API_ID, API_HASH,
    connection=ConnectionTcpAbridged,
    connection_retries=10,
    retry_delay=1,
    auto_reconnect=True,
    catch_up=False,
    receive_updates=True,
    flood_sleep_threshold=0,
)

# Bot Client (Use a named session to cache login state across restarts)
bot = TelegramClient('bot_session', API_ID, API_HASH, connection=ConnectionTcpAbridged)

def matches(text):
    return "Alerts in this hour: 3" in text and "Buys:" in text

def format_alert(text):
    return text.strip()

async def send_notification(text):
    try:
        # Telethon automatically handles reconnection on send_message
        await bot.send_message(CHAT_ID, text, parse_mode=None)
    except FloodWaitError as e:
        print(f"⚠️ FloodWait: sleeping for {e.seconds}s", flush=True)
        await asyncio.sleep(e.seconds)
        try:
            await bot.send_message(CHAT_ID, text, parse_mode=None)
        except Exception as e2:
            print(f"Send error after sleep: {e2}", flush=True)
    except Exception as e:
        print(f"Send error: {e}", flush=True)

async def process(text):
    if not text:
        return
    
    # Use [A-Za-z0-9] to avoid matching underscores in tickers
    coin_match = re.search(r'\$([A-Za-z0-9]+)', text)
    coin = f"${coin_match.group(1)}" if coin_match else "UNKNOWN"
    
    if matches(text):
        print(f"✅ MATCH {coin}", flush=True)
        asyncio.create_task(send_notification(format_alert(text)))
    else:
        print(f"⏭️ SKIP {coin}", flush=True)

@client.on(events.NewMessage(chats=SOURCE_CHAT))
async def new_message_handler(event):
    # CRITICAL FIX: Ignore messages that are part of an album 
    # to prevent duplicate processing (handled by Album event below)
    if event.message.grouped_id:
        return

    # CRITICAL FIX: Force UTC timezone to prevent server timezone offset bugs
    msg_time = event.message.date.replace(tzinfo=datetime.timezone.utc)
    age = max(0.0, time.time() - msg_time.timestamp())
    print(f"⏱️ age={age:.1f}s", flush=True)
    await process(event.message.message or "")

@client.on(events.Album(chats=SOURCE_CHAT))
async def album_handler(event):
    if not event.messages:
        return
    
    msg_time = event.messages[0].date.replace(tzinfo=datetime.timezone.utc)
    age = max(0.0, time.time() - msg_time.timestamp())
    print(f"⏱️ album age={age:.1f}s", flush=True)
    await process(event.messages[0].message or "")

async def main():
    await bot.start(bot_token=BOT_TOKEN)
    await client.connect()
    if not await client.is_user_authorized():
        raise SystemExit("Session expired. Generate a new session string.")
    
    # REMOVED: ping_loop. Telethon handles keep-alives automatically. 
    # Calling get_me() every 20s will trigger FloodWait errors.
    
    print("✅ Listening to CoinSonarV2 | filter: Alerts in this hour: 3", flush=True)
    await client.run_until_disconnected()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
