import asyncio
import time
import re
from aiohttp import web

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
API_ID         = 28807546
API_HASH       = "37624d57b1d83e6bb51b2db777658d0f"
BOT_TOKEN      = "7913078821:AAH_jUTHXlFx66daqBkYY7mKw7UZnwpp_A0"
CHAT_ID        = 1692583809
SESSION_STRING = "1BJWap1wBuzx_OTCt3Xy_83N0Eej5M2__CbVLaXQzxovBXmIbsigVPf9zGOhGRecDxzzU046J-Dg91Oftjxs6vjKHKZqzj-dWrgWOOTvOPjaskIVttRunbZo36Glu4lFv3WDL11YBOZHvvKvJWWhMIT3xoI5icLC2XS6fmx-nvA7uBJoa7UVcyYsaYDVvrBgwqM0d08R0z6iLrbDfz1tP4CFukIafcWIMEyhE84jgXRtTRBkFPboXhL-zmpfkBdsSFDPuP2U5cu8y1BCd2XPiNmjZA2BDFcogTXHcD9BWPbznNLZ6My4SVh1rCp-G7beTbnZOa6KV0QSgRGRWIQKvvT3EQ7j0-9Q="
SOURCE_CHAT    = "CoinSonarV2"
PORT           = 8080
# ==========================================

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
bot = TelegramClient(StringSession(""), API_ID, API_HASH,
    connection=ConnectionTcpAbridged)

def matches(text):
    return "Alerts in this hour: 3" in text and "Buys:" in text

def format_alert(text):
    return text.strip()

async def send_notification(text):
    try:
        if not bot.is_connected():
            await bot.connect()
        await bot.send_message(CHAT_ID, text, parse_mode=None)
    except FloodWaitError as e:
        await asyncio.sleep(e.seconds)
        await bot.send_message(CHAT_ID, text, parse_mode=None)
    except Exception as e:
        print("Send error:", e, flush=True)

async def process(text):
    if not text:
        print("EMPTY TEXT", flush=True)
        return
    coin_match = re.search(r'\$(\w+)', text)
    coin = f"${coin_match.group(1)}" if coin_match else "UNKNOWN"
    print(f"RAW: {repr(text[:120])}", flush=True)
    if matches(text):
        print(f"MATCH {coin}", flush=True)
        asyncio.create_task(send_notification(format_alert(text)))
    else:
        print(f"SKIP {coin}", flush=True)

@client.on(events.NewMessage(chats=SOURCE_CHAT))
async def new_message_handler(event):
    age = max(0.0, time.time() - event.message.date.timestamp())
    print(f"⏱ age={age:.1f}s", flush=True)
    await process(event.message.message or "")

@client.on(events.Album(chats=SOURCE_CHAT))
async def album_handler(event):
    if not event.messages:
        return
    age = max(0.0, time.time() - event.messages[0].date.timestamp())
    print(f"⏱ album age={age:.1f}s", flush=True)
    await process(event.messages[0].message or "")

async def ping_loop():
    while True:
        await asyncio.sleep(10)
        try:
            await client.get_me()
        except Exception as e:
            print(f"Ping error: {e}", flush=True)

# Tiny HTTP server so Railway never sleeps the container
async def health(request):
    return web.Response(text="ok")

async def start_web():
    app = web.Application()
    app.router.add_get("/", health)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    print(f"🌐 HTTP keepalive on port {PORT}", flush=True)

async def main():
    await start_web()
    await bot.start(bot_token=BOT_TOKEN)
    await client.connect()
    if not await client.is_user_authorized():
        raise SystemExit("Session expired. Generate a new session string.")
    asyncio.create_task(ping_loop())
    print("✅ Listening to CoinSonarV2 | filter: Alerts in this hour: 3 + Buys", flush=True)
    await client.run_until_disconnected()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
