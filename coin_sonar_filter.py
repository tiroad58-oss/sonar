import asyncio
import time
import aiohttp

from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.network import ConnectionTcpAbridged


# ============================================================
# CONFIG
# ============================================================

API_ID = YOUR_API_ID
API_HASH = "YOUR_API_HASH"

# Your Telegram USER session
SESSION_STRING = "YOUR_SESSION_STRING"

# Your Telegram BOT
BOT_TOKEN = "YOUR_BOT_TOKEN"
CHAT_ID = YOUR_CHAT_ID

# CoinSonarV2 Telegram chat/channel
SOURCE_CHAT = "CoinSonarV2"


# ============================================================
# TELEGRAM USER CLIENT
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


# One persistent HTTP connection for the Bot API
http_session = None


# ============================================================
# EXACT FILTER
# ============================================================

def should_notify(text):
    """
    Expected message:

    1 $FIDA | #FIDAUSDT | TradingView
    2 Price: ...
    3 └1 min change: ...
    4 26.2K USDT traded in 1 min
    5 └Buys: 19.9K USDT [76%] 🟢
    6 24h Vol: ...
    7 Alerts in this hour: 3 ⭐

    We require:

    LINE 5 contains "Buys"
    AND
    LINE 7 contains "Alerts in this hour: 3"
    """

    lines = text.splitlines()

    # Need at least 7 lines
    if len(lines) < 7:
        return False

    line_5 = lines[4].strip()
    line_7 = lines[6].strip()

    return (
        "Buys" in line_5
        and "Alerts in this hour: 3" in line_7
    )


# ============================================================
# SEND BOT NOTIFICATION
# ============================================================

async def send_notification(text, source_age):
    global http_session

    url = (
        f"https://api.telegram.org/"
        f"bot{BOT_TOKEN}/sendMessage"
    )

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

                print(
                    f"📤 NOTIFICATION SENT | "
                    f"Bot API: {elapsed:.3f}s | "
                    f"Source age: {source_age:.3f}s",
                    flush=True,
                )

                return

            print(
                f"❌ Telegram API error "
                f"{response.status}: {body}",
                flush=True,
            )

    except Exception as e:

        print(
            f"❌ Send error: {repr(e)}",
            flush=True,
        )


# ============================================================
# MESSAGE HANDLER
# ============================================================

@client.on(
    events.NewMessage(
        chats=SOURCE_CHAT
    )
)
async def message_handler(event):

    received_at = time.time()

    message = event.message

    if not message:
        return

    text = message.message or ""

    if not text:
        return

    # --------------------------------------------------------
    # Measure delay between CoinSonar timestamp and our script
    # --------------------------------------------------------

    if message.date:

        source_age = max(
            0,
            received_at - message.date.timestamp()
        )

    else:

        source_age = 0

    print(
        f"\n📨 MESSAGE RECEIVED | "
        f"AGE = {source_age:.3f}s",
        flush=True,
    )

    # --------------------------------------------------------
    # Show the important lines
    # --------------------------------------------------------

    lines = text.splitlines()

    if len(lines) >= 7:

        print(
            f"LINE 5: {lines[4]}",
            flush=True,
        )

        print(
            f"LINE 7: {lines[6]}",
            flush=True,
        )

    else:

        print(
            f"⚠️ Message has only {len(lines)} lines",
            flush=True,
        )

    # --------------------------------------------------------
    # EXACT FILTER
    # --------------------------------------------------------

    filter_started = time.perf_counter()

    if should_notify(text):

        filter_time = (
            time.perf_counter()
            - filter_started
        )

        print(
            f"✅ MATCH | "
            f"filter={filter_time * 1000:.2f}ms",
            flush=True,
        )

        # Send immediately
        asyncio.create_task(
            send_notification(
                text,
                source_age
            )
        )

    else:

        print(
            "⏭️ NO MATCH",
            flush=True,
        )


# ============================================================
# CONNECTION MONITOR
# ============================================================

async def connection_monitor():

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

                print(
                    "💓 Telegram connection OK",
                    flush=True,
                )

        except Exception as e:

            print(
                f"❌ Connection error: {repr(e)}",
                flush=True,
            )


# ============================================================
# MAIN
# ============================================================

async def main():

    global http_session

    # Persistent HTTP session
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
            "❌ SESSION_STRING is not authorized."
        )

    print(
        "✅ Telegram connected",
        flush=True,
    )

    print(
        f"🎯 Listening to: {SOURCE_CHAT}",
        flush=True,
    )

    print(
        "🎯 Rule:",
        flush=True,
    )

    print(
        '   LINE 5 contains "Buys"',
        flush=True,
    )

    print(
        '   LINE 7 contains "Alerts in this hour: 3"',
        flush=True,
    )

    print(
        "🚀 REAL-TIME LISTENER ACTIVE",
        flush=True,
    )

    asyncio.create_task(
        connection_monitor()
    )

    try:

        await client.run_until_disconnected()

    finally:

        if http_session:
            await http_session.close()


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    asyncio.run(main())
