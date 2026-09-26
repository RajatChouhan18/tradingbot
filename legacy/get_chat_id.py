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

def fetch_chat_id():
    if not TOKEN:
        print("[ERROR] TELEGRAM_BOT_TOKEN is missing in your .env file.")
        return

    print("==================================================")
    print("TELEGRAM CHAT ID RETRIEVER")
    print("==================================================")
    
    # 1. Verify Bot
    try:
        me_res = requests.get(f"https://api.telegram.org/bot{TOKEN}/getMe", timeout=10).json()
        if not me_res.get("ok"):
            print(f"[ERROR] Invalid Bot Token: {me_res.get('description')}")
            return
        bot_user = me_res["result"].get("username", "Unknown")
        print(f"Connected to Bot: @{bot_user}")
    except Exception as e:
        print(f"[ERROR] Connection error: {e}")
        return

    print("\nFetching recent messages...")
    try:
        res = requests.get(f"https://api.telegram.org/bot{TOKEN}/getUpdates", timeout=10).json()
        if not res.get("ok"):
            print(f"[ERROR] Telegram API error: {res.get('description')}")
            return
        
        updates = res.get("result", [])
        if not updates:
            print("\n[!] No messages detected yet!")
            print("--------------------------------------------------")
            print(f"Step 1: Open Telegram and search for: @{bot_user}")
            print(f"Direct Link: https://t.me/{bot_user}")
            print("Step 2: Click 'START' or send any message (e.g. 'hello').")
            print("        (If it is a group/channel: add the bot as Admin and send a message)")
            print("Step 3: Run this script again: python get_chat_id.py")
            print("--------------------------------------------------")
            return

        print("\n[OK] Found incoming messages!\n")
        seen_chats = set()
        for update in reversed(updates):
            msg = update.get("message") or update.get("channel_post") or update.get("my_chat_member", {}).get("chat")
            if not msg:
                continue

            chat = msg if "id" in msg and "type" in msg else msg.get("chat", {})
            chat_id = chat.get("id")
            if not chat_id or chat_id in seen_chats:
                continue
            seen_chats.add(chat_id)

            chat_type = chat.get("type", "private")
            title = chat.get("title") or chat.get("username") or chat.get("first_name", "Unknown")
            
            print(f"-> Chat ID: {chat_id}")
            print(f"   Name   : {title}")
            print(f"   Type   : {chat_type.upper()}")
            print("   -----------------------------------------------")

        print("\nCopy your numeric Chat ID and update your .env file:")
        print(f"   CHAT_ID=<your_chat_id_here>")
        print("==================================================")

    except Exception as e:
        print(f"[ERROR] Error fetching updates: {e}")

if __name__ == "__main__":
    fetch_chat_id()
