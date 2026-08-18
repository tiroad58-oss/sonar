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
http_session = None

def matches(text):
    return "Alerts in this hour: 3" in text and "Buys:" in text

def format_alert(text):
    return text.strip()

async def send_notification(text):
    global http_session

    if http_session is None or http_session.closed:
        http_session = web.ClientSession(
            timeout=web.ClientTimeout(total=15)
        )

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "disable_web_page_preview": True,
    }

    started = time.perf_counter()
    try:
        async with http_session.post(url, json=payload) as response:
            body = await response.text()
            elapsed = time.perf_counter() - started

            if response.status != 200:
                print(
                    f"❌ Telegram API error HTTP {response.status}: {body}",
                    flush=True,
                )
                return

            print(
                f"📤 SENT to bot in {elapsed:.3f}s",
                flush=True,
            )
    except Exception as e:
        print(f"❌ Send error: {e}", flush=True)

async def process(text):
    received_at = time.perf_counter()

    if not text:
        print("EMPTY TEXT", flush=True)
        return
    coin_match = re.search(r'\$(\w+)', text)
    coin = f"${coin_match.group(1)}" if coin_match else "UNKNOWN"
    print(f"RAW: {repr(text[:120])}", flush=True)
    if matches(text):
        print(f"MATCH {coin}", flush=True)
        asyncio.create_task(send_notification(format_alert(text)))
        print(
            f"⚡ FILTERED {coin} in {(time.perf_counter() - received_at) * 1000:.1f}ms",
            flush=True,
        )
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
    global http_session

    await start_web()
    http_session = web.ClientSession(
        timeout=web.ClientTimeout(total=15)
    )

    await client.connect()
    if not await client.is_user_authorized():
        raise SystemExit("Session expired. Generate a new session string.")

    asyncio.create_task(ping_loop())

    print(
        "✅ Listening to CoinSonarV2 | filter: Alerts in this hour: 3 + Buys",
        flush=True,
    )

    try:
        await client.run_until_disconnected()
    finally:
        if http_session is not None and not http_session.closed:
            await http_session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
