import asyncio
import time
import aiohttp
import logging

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

SOURCE_USERNAME = "@CoinSonarV2"

# Fallback polling interval.
# 2 seconds is fast without hammering Telegram.
POLL_INTERVAL = 2.0


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)


# ============================================================
# TELEGRAM CLIENT
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


# ============================================================
# GLOBALS
# ============================================================

http_session = None
source_entity = None
source_chat_id = None

# Last message we processed.
last_processed_id = None

# Prevent event + polling from processing the same message twice.
processing_ids = set()


# ============================================================
# FILTER
# ============================================================

def should_notify(text):

    if not text:
        return False

    lines = text.splitlines()

    if len(lines) < 7:
        return False

    line_5 = lines[4].strip()
    line_7 = lines[6].strip()

    condition_buys = (
        "buys" in line_5.lower()
    )

    condition_alert = (
        "alerts in this hour: 3"
        in line_7.lower()
    )

    print(
        f"LINE 5 = {line_5}",
        flush=True
    )

    print(
        f"LINE 7 = {line_7}",
        flush=True
    )

    print(
        f"BUYS MATCH = {condition_buys}",
        flush=True
    )

    print(
        f"ALERT MATCH = {condition_alert}",
        flush=True
    )

    return (
        condition_buys
        and condition_alert
    )


# ============================================================
# SEND TEXT TO YOUR BOT
# ============================================================

async def send_text(text, source_age):

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
                    "",
                    flush=True
                )

                print(
                    "📤 NOTIFICATION SENT",
                    flush=True
                )

                print(
                    f"⚡ BOT API: "
                    f"{elapsed:.3f}s",
                    flush=True
                )

                print(
                    f"⏱ SOURCE AGE: "
                    f"{source_age:.3f}s",
                    flush=True
                )

                return True

            print(
                f"❌ BOT API ERROR "
                f"{response.status}: {body}",
                flush=True
            )

            return False

    except Exception as e:

        print(
            f"❌ BOT SEND ERROR: "
            f"{repr(e)}",
            flush=True
        )

        return False


# ============================================================
# PROCESS MESSAGE
# ============================================================

async def process_message(message, method):

    global last_processed_id

    if not message:
        return

    message_id = message.id

    # --------------------------------------------------------
    # DUPLICATE PROTECTION
    # --------------------------------------------------------

    if message_id in processing_ids:
        return

    if (
        last_processed_id is not None
        and message_id <= last_processed_id
    ):
        return

    processing_ids.add(message_id)

    try:

        # ----------------------------------------------------
        # Update last seen message
        # ----------------------------------------------------

        if (
            last_processed_id is None
            or message_id > last_processed_id
        ):
            last_processed_id = message_id

        # ----------------------------------------------------
        # TEXT / CAPTION
        #
        # For a photo message, Telegram puts the caption here.
        # ----------------------------------------------------

        text = message.message or ""

        if not text:
            return

        received_at = time.time()

        if message.date:

            source_age = max(
                0.0,
                received_at
                - message.date.timestamp()
            )

        else:

            source_age = 0.0

        # ----------------------------------------------------
        # LOG
        # ----------------------------------------------------

        print(
            "",
            flush=True
        )

        print(
            "========================================",
            flush=True
        )

        print(
            "📨 COINSONAR MESSAGE FOUND",
            flush=True
        )

        print(
            f"METHOD: {method}",
            flush=True
        )

        print(
            f"MESSAGE ID: {message_id}",
            flush=True
        )

        print(
            f"SOURCE AGE: {source_age:.3f}s",
            flush=True
        )

        print(
            f"HAS MEDIA: {bool(message.media)}",
            flush=True
        )

        print(
            "CAPTION/TEXT:",
            flush=True
        )

        print(
            text,
            flush=True
        )

        print(
            "========================================",
            flush=True
        )

        # ----------------------------------------------------
        # FILTER
        # ----------------------------------------------------

        started = time.perf_counter()

        matched = should_notify(text)

        filter_time = (
            time.perf_counter()
            - started
        )

        if not matched:

            print(
                "⏭️ NO MATCH",
                flush=True
            )

            return

        # ----------------------------------------------------
        # MATCH
        # ----------------------------------------------------

        print(
            "",
            flush=True
        )

        print(
            "🚨🚨🚨 MATCH FOUND 🚨🚨🚨",
            flush=True
        )

        print(
            f"FILTER TIME: "
            f"{filter_time * 1000:.3f}ms",
            flush=True
        )

        # ----------------------------------------------------
        # SEND IMMEDIATELY
        # ----------------------------------------------------

        asyncio.create_task(
            send_text(
                text,
                source_age
            )
        )

    finally:

        processing_ids.discard(message_id)


# ============================================================
# EVENT LISTENER
# ============================================================

@client.on(events.NewMessage())
async def event_handler(event):

    try:

        if source_chat_id is None:
            return

        if event.chat_id != source_chat_id:
            return

        print(
            "⚡ EVENT RECEIVED",
            flush=True
        )

        await process_message(
            event.message,
            "EVENT"
        )

    except Exception as e:

        print(
            f"❌ EVENT ERROR: {repr(e)}",
            flush=True
        )


# ============================================================
# POLLING FALLBACK
# ============================================================

async def polling_loop():

    global last_processed_id

    print(
        f"🔄 FALLBACK POLLING ACTIVE "
        f"EVERY {POLL_INTERVAL}s",
        flush=True
    )

    while True:

        try:

            # Get the newest message from CoinSonar.
            messages = await client.get_messages(
                source_entity,
                limit=1
            )

            if messages:

                newest = messages[0]

                # First startup:
                #
                # We establish the current ID but don't
                # send an old message.
                if last_processed_id is None:

                    last_processed_id = newest.id

                    print(
                        f"📌 Starting from message ID "
                        f"{last_processed_id}",
                        flush=True
                    )

                elif newest.id > last_processed_id:

                    print(
                        "🔄 POLLING FOUND NEW MESSAGE",
                        flush=True
                    )

                    await process_message(
                        newest,
                        "POLL"
                    )

        except Exception as e:

            print(
                f"❌ POLLING ERROR: {repr(e)}",
                flush=True
            )

        await asyncio.sleep(
            POLL_INTERVAL
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
                    flush=True
                )

            else:

                print(
                    "⚠️ Telegram disconnected",
                    flush=True
                )

                await client.connect()

        except Exception as e:

            print(
                f"❌ CONNECTION ERROR: "
                f"{repr(e)}",
                flush=True
            )


# ============================================================
# MAIN
# ============================================================

async def main():

    global http_session
    global source_entity
    global source_chat_id

    # --------------------------------------------------------
    # HTTP
    # --------------------------------------------------------

    http_session = aiohttp.ClientSession(
        timeout=aiohttp.ClientTimeout(
            total=15
        )
    )

    try:

        # ----------------------------------------------------
        # TELEGRAM
        # ----------------------------------------------------

        print(
            "🔌 Connecting to Telegram...",
            flush=True
        )

        await client.connect()

        if not await client.is_user_authorized():

            raise SystemExit(
                "❌ Telegram session is not authorized."
            )

        print(
            "✅ Telegram connected",
            flush=True
        )

        # ----------------------------------------------------
        # RESOLVE SOURCE
        # ----------------------------------------------------

        print(
            f"🔎 Resolving "
            f"{SOURCE_USERNAME}...",
            flush=True
        )

        source_entity = await client.get_entity(
            SOURCE_USERNAME
        )

        source_chat_id = source_entity.id

        print(
            "✅ SOURCE RESOLVED",
            flush=True
        )

        print(
            f"   Username: "
            f"{SOURCE_USERNAME}",
            flush=True
        )

        print(
            f"   ID: "
            f"{source_chat_id}",
            flush=True
        )

        print(
            f"   Type: "
            f"{type(source_entity).__name__}",
            flush=True
        )

        # ----------------------------------------------------
        # IMPORTANT STARTUP CHECK
        # ----------------------------------------------------

        latest = await client.get_messages(
            source_entity,
            limit=1
        )

        if latest:

            print(
                f"📌 LATEST SOURCE MESSAGE ID: "
                f"{latest[0].id}",
                flush=True
            )

            print(
                f"📌 LATEST MESSAGE DATE: "
                f"{latest[0].date}",
                flush=True
            )

            print(
                f"📌 LATEST HAS MEDIA: "
                f"{bool(latest[0].media)}",
                flush=True
            )

            last_processed_id = latest[0].id

        else:

            print(
                "⚠️ SOURCE HAS NO MESSAGES",
                flush=True
            )

        # ----------------------------------------------------
        # READY
        # ----------------------------------------------------

        print(
            "",
            flush=True
        )

        print(
            "🎯 SOURCE:",
            SOURCE_USERNAME,
            flush=True
        )

        print(
            "🎯 RULE:",
            flush=True
        )

        print(
            '   LINE 5 contains "Buys"',
            flush=True
        )

        print(
            '   LINE 7 contains '
            '"Alerts in this hour: 3"',
            flush=True
        )

        print(
            "🎯 PHOTO + CAPTION SUPPORTED",
            flush=True
        )

        print(
            "",
            flush=True
        )

        print(
            "🚀 LISTENER ACTIVE",
            flush=True
        )

        # ----------------------------------------------------
        # START FALLBACK
        # ----------------------------------------------------

        asyncio.create_task(
            polling_loop()
        )

        asyncio.create_task(
            connection_monitor()
        )

        # ----------------------------------------------------
        # RUN
        # ----------------------------------------------------

        await client.run_until_disconnected()

    finally:

        if http_session:

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
            flush=True
        )
