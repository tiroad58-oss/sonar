import os
import re
import time
import json
import requests
from datetime import datetime, timezone
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
client = TelegramClient(StringSession(SESSION_STRING), api_id, api_hash)

# --- 3. Daily Reset & Duplicate Tracking ---
NOTIFIED_FILE = "notified_coins.json"

def load_notified_coins():
    if os.path.exists(NOTIFIED_FILE):
        try:
            with open(NOTIFIED_FILE, "r") as f:
                data = json.load(f)
                return data.get("date"), set(data.get("coins", []))
        except Exception:
            return None, set()
    return None, set()

def save_notified_coins(date_str, coins_set):
    with open(NOTIFIED_FILE, "w") as f:
        json.dump({"date": date_str, "coins": list(coins_set)}, f)

def get_coin_name(message_text):
    # Extracts the coin name after the $ sign at the beginning of the line
    match = re.search(r'^\$([A-Z0-9]+)', message_text, re.MULTILINE)
    if match:
        return match.group(1)
    return None

# --- 4. Bot Notification Function ---
def send_bot_notification(message_text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
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

# --- 5. Message Handler ---
@client.on(events.NewMessage(chats=group_username))
async def handler(event):
    message_text = event.raw_text
    
    # Step A: Extract Coin Name
    coin_name = get_coin_name(message_text)
    if not coin_name:
        return  # Ignore messages that don't have a coin name format
        
    # Step B: Check Daily Reset & Duplicates
    current_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    saved_date, notified_coins = load_notified_coins()
    
    if saved_date != current_date:
        # It's a new day (UTC), reset the list
        notified_coins = set()
        save_notified_coins(current_date, notified_coins)
        
    if coin_name in notified_coins:
        print(f"⏭️ Skipping {coin_name}: Already notified today.")
        return

    # Step C: Check Conditions
    has_buys = "Buys" in message_text
    has_alerts = "Alerts in this hour: 3" in message_text
    
    if has_buys and has_alerts:
        start_time = time.time()
        print(f"✅ Conditions met for {coin_name}! Triggering bot notification...")
        
        success = send_bot_notification(message_text)
        end_time = time.time()
        
        if success:
            duration = end_time - start_time
            print(f"✅ Notification sent successfully via Bot. (Total duration: {duration:.3f}s)")
            
            # Add to notified list and save to file
            notified_coins.add(coin_name)
            save_notified_coins(current_date, notified_coins)
        else:
            print("❌ Notification failed to send.")

# --- 6. Start the Client ---
print(f"👂 Listening for new messages in @{group_username}...")
client.start()
client.run_until_disconnected()
