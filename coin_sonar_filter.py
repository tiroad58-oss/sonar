import asyncio
import time
import re
import aiohttp
from aiohttp import web

try:
    import uvloop
    uvloop.install()
except Exception:
    pass

from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.network import ConnectionTcpAbridged


# ================= CONFIG =================

API_ID         = 28807546
API_HASH       = "37624d57b1d83e6bb51b2db777658d0f"
BOT_TOKEN      = "7913078821:AAH_jUTHXlFx66daqBkYY7mKw7UZnwpp_A0"
CHAT_ID        = 1692583809
SESSION_STRING = "1BJWap1wBuzx_OTCt3Xy_83N0Eej5M2__CbVLaXQzxovBXI..."
SOURCE_CHAT    = "CoinSonarV2"
PORT           = 8080

# ==========================================


# ============================================================
# TELEGRAM USER CLIENT
# This listens to CoinSonarV2.
# ============================================================

client = TelegramClient(
    StringSession(SESSION_STRING),
    API_ID,
    API_HASH,
    connection=ConnectionTcpAbridged,
    connection_retries=10,
    retry_delay=1,
    auto_reconnect=True,
    catch_up=False,
    receive_updates=True,
    flood_sleep_threshold=0,
)


# Persistent HTTP session used to send the bot message
http_session = None


# ============================================================
# FILTER
# ============================================================

def matches(text):
    return (
        "Alerts in this hour: 3" in text
        and "Buys:" in text
    )


def format_alert(text):
    return text.strip()


# ============================================================
# SEND NOTIFICATION
# Direct Telegram Bot API
# ============================================================

async def send_notification(text, coin="UNKNOWN", source_age=None):

    global http_session

    if http_session is None or http_session.closed:
        http_session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=15)
        )

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "disable_web_page_preview": True,
    }

    started = time.perf_counter()

    try:

        async with http_session.post(
            url,
            json=payload
        ) as response:

            body = await response.text()

            elapsed = time.perf_counter() - started

            if response.status == 200:

                if source_age is not None:

                    total_age = (
                        time.time()
                        - (
                            time.time()
                            - source_age
                        )
                    )

                print(
                    f"📤 SENT {coin} | "
                    f"API={elapsed:.3f}s | "
                    f"source_age={source_age:.3f}s",
                    flush=True,
                )

                return True

            # Telegram rate limit
            if response.status == 429:

                try:
                    data = await response.json()

                    retry_after = (
                        data.get("parameters", {})
                        .get("retry_after", 1)
                    )

                except Exception:

                    retry_after = 1

                print(
                    f"⚠️ Telegram rate limit: "
                    f"retrying in {retry_after}s",
                    flush=True,
                )

                await asyncio.sleep(retry_after)

                async with http_session.post(
                    url,
                    json=payload
                ) as retry_response:

                    retry_body = await retry_response.text()

                    if retry_response.status == 200:

                        print(
                            f"📤 RETRY SENT {coin}",
                            flush=True,
                        )

                        return True

                    print(
                        f"❌ Retry failed "
                        f"HTTP {retry_response.status}: "
                        f"{retry_body}",
                        flush=True,
                    )

                    return False

            print(
                f"❌ Telegram API error "
                f"HTTP {response.status}: {body}",
                flush=True,
            )

            return False

    except asyncio.TimeoutError:

        print(
            f"❌ Telegram API timeout for {coin}",
            flush=True,
        )

        return False

    except Exception as e:

        print(
            f"❌ Send error for {coin}: {repr(e)}",
            flush=True,
        )

        return False


# ============================================================
# PROCESS MESSAGE
# ============================================================

async def process(text, source_timestamp=None):

    if not text:

        print(
            "EMPTY TEXT",
            flush=True,
        )

        return

    processing_started = time.perf_counter()

    # Calculate actual age of CoinSonar message
    source_age = None

    if source_timestamp is not None:

        source_age = max(
            0.0,
            time.time() - source_timestamp
        )

    # Find coin
    coin_match = re.search(
        r"\$(\w+)",
        text
    )

    coin = (
        f"${coin_match.group(1)}"
        if coin_match
        else "UNKNOWN"
    )

    print(
        f"📨 RECEIVED {coin} | "
        f"source_age="
        f"{source_age:.3f}s"
        if source_age is not None
        else
        f"📨 RECEIVED {coin}",
        flush=True,
    )

    print(
        f"RAW: {repr(text[:200])}",
        flush=True,
    )

    # ========================================================
    # FILTER
    # ========================================================

    if matches(text):

        filter_elapsed = (
            time.perf_counter()
            - processing_started
        )

        print(
            f"✅ MATCH {coin} | "
            f"filter="
            f"{filter_elapsed * 1000:.1f}ms",
            flush=True,
        )

        # Send immediately
        asyncio.create_task(
            send_notification(
                format_alert(text),
                coin,
                source_age
            )
        )

    else:

        print(
            f"⏭️ SKIP {coin}",
            flush=True,
        )


# ============================================================
# NEW MESSAGE
# ============================================================

@client.on(
    events.NewMessage(
        chats=SOURCE_CHAT
    )
)
async def new_message_handler(event):

    try:

        message = event.message

        if not message:
            return

        message_timestamp = (
            message.date.timestamp()
            if message.date
            else None
        )

        age = (
            max(
                0.0,
                time.time()
                - message_timestamp
            )
            if message_timestamp
            else 0.0
        )

        print(
            f"⏱ NEW MESSAGE AGE = "
            f"{age:.3f}s",
            flush=True,
        )

        await process(
            message.message or "",
            message_timestamp
        )

    except Exception as e:

        print(
            f"❌ New message handler error: "
            f"{repr(e)}",
            flush=True,
        )


# ============================================================
# ALBUM
# ============================================================

@client.on(
    events.Album(
        chats=SOURCE_CHAT
    )
)
async def album_handler(event):

    try:

        if not event.messages:
            return

        message = event.messages[0]

        message_timestamp = (
            message.date.timestamp()
            if message.date
            else None
        )

        age = (
            max(
                0.0,
                time.time()
                - message_timestamp
            )
            if message_timestamp
            else 0.0
        )

        print(
            f"⏱ ALBUM AGE = "
            f"{age:.3f}s",
            flush=True,
        )

        await process(
            message.message or "",
            message_timestamp
        )

    except Exception as e:

        print(
            f"❌ Album handler error: "
            f"{repr(e)}",
            flush=True,
        )


# ============================================================
# CONNECTION PING
# ============================================================

async def ping_loop():

    while True:

        await asyncio.sleep(30)

        try:

            if not client.is_connected():

                print(
                    "⚠️ Telegram disconnected. "
                    "Reconnecting...",
                    flush=True,
                )

                await client.connect()

            else:

                await client.get_me()

                print(
                    "💓 Telegram connection OK",
                    flush=True,
                )

        except Exception as e:

            print(
                f"❌ Ping error: {repr(e)}",
                flush=True,
            )


# ============================================================
# RAILWAY HEALTH SERVER
# ============================================================

async def health(request):

    return web.Response(
        text="ok"
    )


async def start_web():

    app = web.Application()

    app.router.add_get(
        "/",
        health
    )

    runner = web.AppRunner(app)

    await runner.setup()

    site = web.TCPSite(
        runner,
        "0.0.0.0",
        PORT
    )

    await site.start()

    print(
        f"🌐 HTTP keepalive on port {PORT}",
        flush=True,
    )


# ============================================================
# MAIN
# ============================================================

async def main():

    global http_session

    await start_web()

    # IMPORTANT:
    # ClientSession comes from aiohttp,
    # NOT aiohttp.web
    http_session = aiohttp.ClientSession(
        timeout=aiohttp.ClientTimeout(
            total=15
        )
    )

    print(
        "🔌 Connecting to Telegram...",
        flush=True,
    )

    await client.connect()

    if not await client.is_user_authorized():

        raise SystemExit(
            "❌ Session expired. "
            "Generate a new session string."
        )

    print(
        "✅ Telegram user account connected",
        flush=True,
    )

    print(
        f"🎯 Listening to {SOURCE_CHAT}",
        flush=True,
    )

    print(
        "⚡ Filter: "
        "Alerts in this hour: 3 + Buys:",
        flush=True,
    )

    print(
        "🚀 REAL-TIME LISTENER ACTIVE",
        flush=True,
    )

    asyncio.create_task(
        ping_loop()
    )

    try:

        await client.run_until_disconnected()

    finally:

        if (
            http_session
            and not http_session.closed
        ):

            await http_session.close()


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    try:

        asyncio.run(main())

    except KeyboardInterrupt:

        pass
