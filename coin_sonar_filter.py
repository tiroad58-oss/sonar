import os
import time
import requests
from telethon import TelegramClient, events
from telethon.sessions import StringSession

# --- 1. Read Credentials from Railway Environment Variables ---
api_id = int(os.environ.get("API_ID"))
api_hash = os.environ.get("API_HASH")
group_username = 'CoinSonarV2'

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
SESSION_STRING = os.environ.get("SESSION_STRING")

# --- 2. Initialize Telegram Client with String Session ---
# This allows the script to run on Railway without needing a local .session file
client = TelegramClient(StringSession(SESSION_STRING), api_id, api_hash)

# --- 3. Bot Notification Function ---
def send_bot_notification(message_text):
    """Sends the exact raw message to you via your custom Telegram Bot."""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    
    # We only send the raw text, no extra formatting or added text
    payload = {
        "chat_id": CHAT_ID,
        "text": message_text
    }
    
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            return True
        else:
            print(f"❌ Failed to send notification: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error sending notification: {e}")
        return False

# --- 4. Message Handler ---
@client.on(events.NewMessage(chats=group_username))
async def handler(event):
    message_text = event.raw_text
    
    # Check conditions
    has_buys = "Buys" in message_text
    has_alerts = "Alerts in this hour: 3" in message_text
    
    if has_buys and has_alerts:
        # Start timer exactly when conditions are met
        start_time = time.time()
        
        print("✅ Conditions met! Triggering bot notification...")
        
        # Send the notification
        success = send_bot_notification(message_text)
        
        # Stop timer exactly when the send request finishes
        end_time = time.time()
        
        if success:
            # Calculate the total duration from receive to sent
            duration = end_time - start_time
            print(f"✅ Notification sent successfully via Bot. (Total duration: {duration:.3f}s)")
        else:
            print("❌ Notification failed to send.")

# --- 5. Start the Client ---
print(f"👂 Listening for new messages in @{group_username}...")
client.start()
client.run_until_disconnected()
