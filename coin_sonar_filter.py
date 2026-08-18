import asyncio
import time
import aiohttp

from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.network import ConnectionTcpAbridged


# ============================================================
# CONFIG
# ============================================================

API_ID = 28807546
API_HASH = "37624d57b1d83e6bb51b2db777658d0f"

# Your Telegram USER session
SESSION_STRING = "1BJWap1wBu7zXC1n0i_ZEYU8tlQb7YatgCqbcBfVF_nsWzkeMZc0QHAq2OJhzjvzNIOoAvCETaKx88iuxVbDH8iJcdhnJN7wXkuxnbAmJqiNs4c4JOYpe4rUV53HbkF6qI38N-TIxZQFwc6NVWkdjhdWdYdoAOkq7FniGs8m_FXl6Pq8rqkphjNFPasxGgs-LY4aJPYsH2DF_arA7SQ9NI2lSuteDVBFwh4CkzlCKFr5KfGD6OeoO1fMgIn2DBrq647GO-jUBXRgs6JBbkcRQTxwciudMcmcrVjfiXJ_ngSS_7enkC4l0_WPXMKFMFhBTSzujcxNpUMZL05NDAK--QNzV3gTS1sw="

# Your Telegram BOT
BOT_TOKEN = "8833328238:AAHD-03Tz7r2kCYxmHn4k62IGwafuv3tyjk"
CHAT_ID = 1692583809

# CoinSonarV2 source
SOURCE_CHAT = "@CoinSonarV2"


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

    # Do not process old messages after startup
    catch_up=False,

    receive_updates=True,

    flood_sleep_threshold=0,
)


# Persistent HTTP session
http_session = None


# ============================================================
# FILTER
# ============================================================

def should_notify(text):

    lines = text.splitlines()

    # We require exactly the structure we expect:
    #
    # line 1
    # line 2
    # line 3
    # line 4
    # line 5 = Buys
    # line 6
    # line 7 = Alerts in this hour: 3

    if len(lines) < 7:
        return False

    line_5 = lines[4].strip()
    line_7 = lines[6].strip()

    return (
        "Buys" in line_5
        and
        "Alerts in this hour: 3" in line_7
    )


# ============================================================
# SEND BOT MESSAGE
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

            elapsed = (
                time.perf_counter()
                - started
            )

            if response.status == 200:

                print(
                    f"📤 NOTIFICATION SENT | "
                    f"API={elapsed:.3f}s | "
                    f"SOURCE AGE={source_age:.3f}s",
                    flush=True,
                )

                return True

            print(
                f"❌ BOT API ERROR "
                f"{response.status}: {body}",
                flush=True,
            )

            return False

    except Exception as e:

        print(
            f"❌ SEND ERROR: {repr(e)}",
            flush=True,
        )

        return False


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
    # MEASURE MESSAGE AGE
    # --------------------------------------------------------

    if message.date:

        source_age = max(
            0.0,
            received_at - message.date.timestamp()
        )

    else:

        source_age = 0.0

    # --------------------------------------------------------
    # LOG
    # --------------------------------------------------------

    print(
        "",
        flush=True,
    )

    print(
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        flush=True,
    )

    print(
        "📨 COINSONAR MESSAGE RECEIVED",
        flush=True,
    )

    print(
        f"⏱ SOURCE AGE: {source_age:.3f}s",
        flush=True,
    )

    # --------------------------------------------------------
    # SHOW LINES 5 AND 7
    # --------------------------------------------------------

    lines = text.splitlines()

    print(
        f"📏 TOTAL LINES: {len(lines)}",
        flush=True,
    )

    if len(lines) >= 5:

        print(
            f"LINE 5: {lines[4]}",
            flush=True,
        )

    if len(lines) >= 7:

        print(
            f"LINE 7: {lines[6]}",
            flush=True,
        )

    # --------------------------------------------------------
    # FILTER
    # --------------------------------------------------------

    filter_started = time.perf_counter()

    matched = should_notify(text)

    filter_elapsed = (
        time.perf_counter()
        - filter_started
    )

    if not matched:

        print(
            "⏭️ NO MATCH",
            flush=True,
        )

        print(
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            flush=True,
        )

        return

    # --------------------------------------------------------
    # MATCH
    # --------------------------------------------------------

    print(
        "✅ MATCH!",
        flush=True,
    )

    print(
        f"⚡ FILTER: "
        f"{filter_elapsed * 1000:.3f}ms",
        flush=True,
    )

    # --------------------------------------------------------
    # SEND IMMEDIATELY
    # --------------------------------------------------------

    asyncio.create_task(
        send_notification(
            text,
            source_age
        )
    )

    print(
        "🚀 SEND TASK CREATED",
        flush=True,
    )

    print(
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        flush=True,
    )


# ============================================================
# CONNECTION MONITOR
# ============================================================

async def connection_monitor():

    while True:

        await asyncio.sleep(30)

        try:

            if client.is_connected():

                print(
                    "💓 Telegram connection OK",
                    flush=True,
                )

            else:

                print(
                    "⚠️ Telegram disconnected",
                    flush=True,
                )

                await client.connect()

        except Exception as e:

            print(
                f"❌ CONNECTION ERROR: {repr(e)}",
                flush=True,
            )


# ============================================================
# MAIN
# ============================================================

async def main():

    global http_session

    # --------------------------------------------------------
    # CREATE ONE PERSISTENT HTTP SESSION
    # --------------------------------------------------------

    http_session = aiohttp.ClientSession(
        timeout=aiohttp.ClientTimeout(
            total=15
        )
    )

    try:

        # ----------------------------------------------------
        # CONNECT
        # ----------------------------------------------------

        print(
            "🔌 Connecting to Telegram...",
            flush=True,
        )

        await client.connect()

        # ----------------------------------------------------
        # AUTH CHECK
        # ----------------------------------------------------

        if not await client.is_user_authorized():

            raise SystemExit(
                "❌ Telegram session is not authorized."
            )

        print(
            "✅ Telegram connected",
            flush=True,
        )

        # ----------------------------------------------------
        # SOURCE
        # ----------------------------------------------------

        print(
            "",
            flush=True,
        )

        print(
            f"🎯 Listening to: {SOURCE_CHAT}",
            flush=True,
        )

        # ----------------------------------------------------
        # FILTER
        # ----------------------------------------------------

        print(
            "",
            flush=True,
        )

        print(
            "🎯 FILTER:",
            flush=True,
        )

        print(
            '   LINE 5 contains "Buys"',
            flush=True,
        )

        print(
            '   LINE 7 contains '
            '"Alerts in this hour: 3"',
            flush=True,
        )

        # ----------------------------------------------------
        # READY
        # ----------------------------------------------------

        print(
            "",
            flush=True,
        )

        print(
            "🚀 REAL-TIME LISTENER ACTIVE",
            flush=True,
        )

        # ----------------------------------------------------
        # CONNECTION MONITOR
        # ----------------------------------------------------

        asyncio.create_task(
            connection_monitor()
        )

        # ----------------------------------------------------
        # WAIT FOR TELEGRAM EVENTS
        # ----------------------------------------------------

        await client.run_until_disconnected()

    finally:

        if http_session is not None:

            await http_session.close()

        if client.is_connected():

            await client.disconnect()


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    try:

        asyncio.run(main())

    except KeyboardInterrupt:

        print(
            "🛑 Stopped",
            flush=True,
        )
