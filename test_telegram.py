import os
import sys
import requests
from dotenv import load_dotenv

if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

def test_telegram():
    if not TOKEN:
        print("[ERROR] TELEGRAM_BOT_TOKEN is missing in .env")
        return
    if not CHAT_ID or CHAT_ID == "dummy_chat_id":
        print("[ERROR] CHAT_ID is empty or set to 'dummy_chat_id'. Please set your numeric CHAT_ID in .env")
        return

    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": "🚀 [TEST ALERT] Your Telegram Bot is successfully connected!\nSignals and trade charts will appear in this chat."
    }

    print(f"Sending test alert to Chat ID: {CHAT_ID}...")
    try:
        res = requests.post(url, data=payload, timeout=15)
        res_json = res.json()
        if res_json.get("ok"):
            print("[SUCCESS] Test message successfully sent to your Telegram chat!")
        else:
            print(f"[FAILED] Telegram API Error: {res_json.get('description')}")
    except Exception as e:
        print(f"[ERROR] Request failed: {e}")

if __name__ == "__main__":
    test_telegram()
