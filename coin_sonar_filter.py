import re
import time
import requests
from telethon import TelegramClient, events

# --- Telegram API Credentials ---
api_id = '28807546'
api_hash = '37624d57b1d83e6bb51b2db777658d0f'
group_username = 'CoinSonarV2'

# --- Bot Notification Credentials ---
BOT_TOKEN = '8833328238:AAHD-03Tz7r2kCYxmHn4k62IGwafuv3tyjk'      # e.g., '123456789:ABCdefGHIjklMNOpqrsTUVwxyz'
CHAT_ID = '1692583809'          # e.g., '123456789'


client = TelegramClient('coin_sonar_monitor', api_id, api_hash)

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

@client.on(events.NewMessage(chats=group_username))
async def handler(event):
    message_text = event.raw_text
    
    # Condition 1: Must contain "Buys"
    has_buys = "Buys" in message_text
    
    # Condition 2: Must contain "Alerts in this hour: 3"
    has_alerts = "Alerts in this hour: 3" in message_text
    
    if has_buys and has_alerts:
        # Start timer exactly when the message is received and conditions are met
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

print(f"👂 Listening for new messages in @{group_username}...")
client.start()
client.run_until_disconnected()
