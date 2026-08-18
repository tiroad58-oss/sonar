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

SOURCE_USERNAME = "@CoinSonarV2"


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


http_session = None
source_chat_id = None


# ============================================================
# FILTER
# ============================================================

def should_notify(text):

    if not text:
        return False

    lines = text.splitlines()

    print(
        f"📏 MESSAGE HAS {len(lines)} LINES",
        flush=True
    )

    if len(lines) < 7:
        return False

    # Python indexes from zero:
    #
    # lines[0] = line 1
    # lines[1] = line 2
    # lines[2] = line 3
    # lines[3] = line 4
    # lines[4] = line 5
    # lines[5] = line 6
    # lines[6] = line 7

    line_5 = lines[4].strip()
    line_7 = lines[6].strip()

    print(
        f"LINE 5: {line_5}",
        flush=True
    )

    print(
        f"LINE 7: {line_7}",
        flush=True
    )

    condition_1 = "buys" in line_5.lower()

    condition_2 = (
        "alerts in this hour: 3"
        in line_7.lower()
    )

    print(
        f"CHECK LINE 5 BUYS: {condition_1}",
        flush=True
    )

    print(
        f"CHECK LINE 7 ALERTS: {condition_2}",
        flush=True
    )

    return condition_1 and condition_2


# ============================================================
# SEND TELEGRAM BOT MESSAGE
# ============================================================

async def send_notification(
    text,
    source_age,
    image_path=None
):

    global http_session

    # --------------------------------------------------------
    # If there is an image, send photo + caption
    # --------------------------------------------------------

    if image_path:

        url = (
            f"https://api.telegram.org/"
            f"bot{BOT_TOKEN}/sendPhoto"
        )

        try:

            started = time.perf_counter()

            data = aiohttp.FormData()

            data.add_field(
                "chat_id",
                str(CHAT_ID)
            )

            data.add_field(
                "caption",
                text
            )

            with open(
                image_path,
                "rb"
            ) as photo_file:

                data.add_field(
                    "photo",
                    photo_file,
                    filename="coinsonar.jpg",
                    content_type="image/jpeg"
                )

                async with http_session.post(
                    url,
                    data=data
                ) as response:

                    body = await response.text()

            elapsed = (
                time.perf_counter()
                - started
            )

            if response.status == 200:

                print(
                    f"📤 PHOTO + TEXT SENT | "
                    f"API={elapsed:.3f}s | "
                    f"SOURCE AGE={source_age:.3f}s",
                    flush=True
                )

                return True

            print(
                f"❌ BOT PHOTO ERROR "
                f"{response.status}: {body}",
                flush=True
            )

            return False

        except Exception as e:

            print(
                f"❌ PHOTO SEND ERROR: {repr(e)}",
                flush=True
            )

            return False

    # --------------------------------------------------------
    # Text only
    # --------------------------------------------------------

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
                    f"📤 TEXT SENT | "
                    f"API={elapsed:.3f}s | "
                    f"SOURCE AGE={source_age:.3f}s",
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
            f"❌ TEXT SEND ERROR: {repr(e)}",
            flush=True
        )

        return False


# ============================================================
# MAIN MESSAGE HANDLER
#
# IMPORTANT:
# We listen to ALL new messages here.
# Then we check source_chat_id ourselves.
#
# This is more reliable than:
# events.NewMessage(chats="@CoinSonarV2")
#
# It also handles photo + caption messages.
# ============================================================

@client.on(events.NewMessage())
async def message_handler(event):

    try:

        # ----------------------------------------------------
        # Ignore everything that isn't CoinSonarV2
        # ----------------------------------------------------

        if event.chat_id != source_chat_id:
            return

        received_at = time.time()

        message = event.message

        if not message:
            return

        # ----------------------------------------------------
        # THIS IS THE IMPORTANT PART
        #
        # For a photo message, the text underneath the photo
        # is stored here as the message caption.
        # ----------------------------------------------------

        text = message.message or ""

        print(
            "",
            flush=True
        )

        print(
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            flush=True
        )

        print(
            "📨 COINSONAR MESSAGE RECEIVED!",
            flush=True
        )

        print(
            f"🆔 CHAT ID: {event.chat_id}",
            flush=True
        )

        print(
            f"🖼 HAS MEDIA: {bool(message.media)}",
            flush=True
        )

        # ----------------------------------------------------
        # SOURCE AGE
        # ----------------------------------------------------

        if message.date:

            source_age = max(
                0.0,
                received_at
                - message.date.timestamp()
            )

        else:

            source_age = 0.0

        print(
            f"⏱ SOURCE AGE: "
            f"{source_age:.3f}s",
            flush=True
        )

        # ----------------------------------------------------
        # CHECK CAPTION
        # ----------------------------------------------------

        if not text:

            print(
                "⚠️ MESSAGE HAS NO TEXT/CAPTION",
                flush=True
            )

            print(
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
                flush=True
            )

            return

        print(
            "📝 CAPTION RECEIVED:",
            flush=True
        )

        print(
            text,
            flush=True
        )

        # ----------------------------------------------------
        # FILTER
        # ----------------------------------------------------

        filter_started = time.perf_counter()

        matched = should_notify(text)

        filter_elapsed = (
            time.perf_counter()
            - filter_started
        )

        # ----------------------------------------------------
        # NO MATCH
        # ----------------------------------------------------

        if not matched:

            print(
                "⏭️ NO MATCH",
                flush=True
            )

            print(
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
                flush=True
            )

            return

        # ----------------------------------------------------
        # MATCH
        # ----------------------------------------------------

        print(
            "🚨 MATCH!",
            flush=True
        )

        print(
            f"⚡ FILTER TIME: "
            f"{filter_elapsed * 1000:.3f}ms",
            flush=True
        )

        # ----------------------------------------------------
        # IMPORTANT:
        #
        # First test with TEXT ONLY.
        #
        # Once this works, we can add forwarding of the image.
        #
        # This keeps the first test as fast and simple as
        # possible.
        # ----------------------------------------------------

        asyncio.create_task(
            send_notification(
                text,
                source_age
            )
        )

        print(
            "🚀 NOTIFICATION TASK CREATED",
            flush=True
        )

        print(
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            flush=True
        )

    except Exception as e:

        print(
            f"❌ MESSAGE HANDLER ERROR: "
            f"{repr(e)}",
            flush=True
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
    global source_chat_id

    # --------------------------------------------------------
    # HTTP SESSION
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
        # RESOLVE COINSONAR
        # ----------------------------------------------------

        print(
            f"🔎 Resolving "
            f"{SOURCE_USERNAME}...",
            flush=True
        )

        source_entity = await client.get_entity(
            SOURCE_USERNAME
        )

        source_chat_id = (
            source_entity.id
        )

        print(
            "✅ COINSONAR RESOLVED",
            flush=True
        )

        print(
            f"   Username: "
            f"{SOURCE_USERNAME}",
            flush=True
        )

        print(
            f"   Telegram ID: "
            f"{source_chat_id}",
            flush=True
        )

        print(
            f"   Type: "
            f"{type(source_entity).__name__}",
            flush=True
        )

        # ----------------------------------------------------
        # FILTER INFO
        # ----------------------------------------------------

        print(
            "",
            flush=True
        )

        print(
            "🎯 FILTER:",
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
            "   PHOTO + CAPTION SUPPORTED",
            flush=True
        )

        print(
            "",
            flush=True
        )

        print(
            "🚀 REAL-TIME LISTENER ACTIVE",
            flush=True
        )

        # ----------------------------------------------------
        # MONITOR
        # ----------------------------------------------------

        asyncio.create_task(
            connection_monitor()
        )

        # ----------------------------------------------------
        # RUN FOREVER
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
