import os
import json
import time
import requests
import cloudscraper
from dotenv import load_dotenv
from bs4 import BeautifulSoup

# Load environment variables from .env
load_dotenv()

# Constants
LOGIN_URL = 'https://kageherostudio.com/payment/server_.php'
EVENT_URL = 'https://kageherostudio.com/event/?event=daily'
CLAIM_URL = 'https://kageherostudio.com/event/index_.php?act=daily'

USER_NAME = 'txtuserid'
PASS_NAME = 'txtpassword'
ITEM_POST = 'itemId'
PROD_POST = 'periodId'
SRVR_POST = 'selserver'
REWARD_CLS = '.reward-star'

# Telegram Bot credentials from environment variables
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


# Function to load user data from environment variable
def load_data_from_env():
    """Load data from the environment variable DATA_JSON."""
    try:
        raw_data = os.getenv("DATA_JSON")
        if not raw_data:
            raise ValueError("Environment variable 'DATA_JSON' tidak ditemukan atau kosong.")

        data = json.loads(raw_data)

        # Validate structure
        if not isinstance(data, list) or not all(isinstance(item, dict) for item in data):
            raise ValueError("Isi 'DATA_JSON' tidak valid. Harus berupa list of dictionaries.")

        return data

    except json.JSONDecodeError:
        raise ValueError("DATA_JSON mengandung string yang tidak valid sebagai JSON.")

    except Exception as e:
        raise Exception(f"Terjadi kesalahan saat memuat DATA_JSON: {e}")


# Function to send Telegram messages
def send_telegram_message(message):
    """Sends a message via Telegram Bot with enhanced formatting."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram credentials are not set. Please check TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID.")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }

    try:
        response = requests.post(url, data=data)
        if response.status_code == 200:
            print("Telegram notification sent successfully.")
        else:
            print(f"Failed to send Telegram notification: {response.status_code}, {response.text}")
    except Exception as e:
        print(f"Error while sending Telegram message: {e}")


# Function to handle login
def login(session, username, password):
    """Logs in the user."""
    data = {
        USER_NAME: username,
        PASS_NAME: password,
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    try:
        response = session.post(LOGIN_URL, data=data, headers=headers)

        if response.status_code == 200:
            if "success" in response.url or response.url.endswith("pembayaran.php"):
                print(f"Successfully logged in for {username}")
                return True
            else:
                print(f"Unexpected successful response for {username}, URL: {response.url}")
                return False

        elif response.status_code == 403:
            print(f"Login failed for {username} (403 Forbidden). Checking for additional info...")
            print(f"Raw response content: {response.text}")
            return False

        else:
            print(f"Unexpected response for {username}, status code: {response.status_code}, content: {response.text}")
            return False

    except Exception as e:
        print(f"Error during login for {username}: {e}")
        return False


# Function to claim rewards
def claim_rewards(session, username, server):
    """Claim daily rewards for the user."""
    data = {
        SRVR_POST: server,
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    try:
        response = session.post(CLAIM_URL, data=data, headers=headers)
        if response.status_code == 200:
            # Parse the response to find claimed items (example placeholder logic)
            soup = BeautifulSoup(response.text, "html.parser")
            items = soup.select(REWARD_CLS)
            claimed_items = [item.get_text().strip() for item in items]
            if claimed_items:
                print(f"Claimed items: {', '.join(claimed_items)}")
                return claimed_items
            else:
                print(f"No items claimed for {username}.")
                return []
        else:
            print(f"Failed to claim rewards for {username}: {response.status_code}")
            return []

    except Exception as e:
        print(f"Error during claim for {username}: {e}")
        return []


# Main function to process logins and claim rewards
def main():
    try:
        data = load_data_from_env()
    except Exception as e:
        print(f"Error: {e}")
        send_telegram_message(f"❌ <b>Error in script execution:</b> {str(e)}")
        return

    session = cloudscraper.create_scraper()  # Use cloudscraper to handle Cloudflare challenges
    fails = 0
    messages = []

    for user in data:
        username = user.get("username")
        password = user.get("password")
        server = user.get("server")

        print(f"Processing login for: {username}")
        if login(session, username, password):
            messages.append(f"✅ <b>{username}</b> logged in successfully.")
            
            # Claim rewards after login
            claimed_items = claim_rewards(session, username, server)
            if claimed_items:
                items_message = f"🎁 <b>Items claimed for {username}:</b>\n" + "\n".join(claimed_items)
                messages.append(items_message)
            else:
                messages.append(f"⚠️ <b>{username}</b> did not claim any items.")
        else:
            fails += 1
            messages.append(f"❌ <b>{username}</b> failed to log in.")

        # Add delay to avoid rate-limiting
        time.sleep(2)

    # Enhanced Telegram message formatting
    result_message = "🌟 <b>Login and Rewards Results</b> 🌟\n\n"
    for message in messages:
        result_message += f"{message}\n"

    if fails > 0:
        result_message += f"\n⚠️ <b>{fails}</b> login attempts failed. Please check the credentials or server status."
    else:
        result_message += "\n🎉 <b>All logins were successful!</b> Great work!"

    result_message += "\n\n📅 <i>Report generated on:</i> <b>{}</b>".format(time.strftime("%Y-%m-%d %H:%M:%S"))

    # Send the result via Telegram
    send_telegram_message(result_message)


if __name__ == "__main__":
    main()
