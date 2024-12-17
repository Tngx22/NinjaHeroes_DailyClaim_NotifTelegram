import requests
import json
import os
import re
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from time import sleep
import concurrent.futures
import itertools

# Load environment variables
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

# Twilio API credentials
TWILIO_SID = os.getenv("TWILIO_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER")
RECIPIENT_WHATSAPP_NUMBER = os.getenv("RECIPIENT_WHATSAPP_NUMBER")


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


# Function to send WhatsApp messages using Twilio
def send_whatsapp_message(message):
    """Sends a WhatsApp message via Twilio."""
    url = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_SID}/Messages.json"
    data = {
        "From": f"whatsapp:{TWILIO_WHATSAPP_NUMBER}",
        "To": f"whatsapp:{RECIPIENT_WHATSAPP_NUMBER}",
        "Body": message,
    }
    auth = (TWILIO_SID, TWILIO_AUTH_TOKEN)
    try:
        response = requests.post(url, data=data, auth=auth)
        if response.status_code == 201:
            print("WhatsApp notification sent successfully.")
        else:
            print(f"Failed to send WhatsApp notification: {response.text}")
    except Exception as e:
        print(f"Error while sending message: {e}")


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

        if response.status_code == 403:
            print(f"Login failed for {username} (403 Forbidden). Checking for additional info...")
            if response.headers.get("Content-Type", "").startswith("application/json"):
                try:
                    error_details = response.json()
                    print(f"Server response: {error_details}")
                except ValueError:
                    print("Failed to parse JSON from response content.")
            else:
                print(f"Raw response content: {response.text}")
            return False

        elif response.status_code == 200:
            if "success" in response.url or response.url.endswith("pembayaran.php"):
                print(f"Successfully logged in for {username}")
                return True
            else:
                print(f"Unexpected successful response for {username}, URL: {response.url}")
                return False

        elif response.status_code == 429:
            print(f"Rate-limit reached for {username}. Waiting before retrying...")
            sleep(60)  # Wait for 60 seconds before retrying
            return False

        else:
            print(f"Unexpected response for {username}, status code: {response.status_code}, content: {response.text}")
            return False

    except requests.RequestException as e:
        print(f"Error during login for {username}: {e}")
        return False


# Main function to process logins
def main():
    try:
        data = load_data_from_env()
    except Exception as e:
        print(f"Error: {e}")
        send_whatsapp_message(f"Error in script execution: {str(e)}")
        return

    session = requests.Session()
    fails = 0
    messages = []

    for user in data:
        username = user.get("username")
        password = user.get("password")
        server = user.get("server")

        print(f"Processing login for: {username}")
        if login(session, username, password):
            messages.append(f"{username} logged in successfully.")
        else:
            fails += 1
            messages.append(f"{username} failed to log in.")

    result_message = "\n".join(messages)
    if fails > 0:
        result_message += f"\n{fails} login failures."
    else:
        result_message += "\nAll logins successful."

    send_whatsapp_message(result_message)


if __name__ == "__main__":
    main()
