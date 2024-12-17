import requests
import json
import os
import re
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from time import sleep
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

# Memuat data pengguna dari GitHub Secrets
def load_data_from_env():
    raw_data = os.getenv("DATA_JSON")
    data = json.loads(raw_data)
    return data

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

def login(session, username, password):
    """Logs in the user."""
    data = {
        USER_NAME: username,
        PASS_NAME: password,
    }
    response = session.post(LOGIN_URL, data=data)
    if response.url.endswith('pembayaran.php'):
        return True
    else:
        print(f"Failed login for {username}, status code: {response.status_code}")
        return False

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

        if login(session, username, password):
            print(f"{username} successfully logged in!")
            messages.append(f"{username} logged in successfully.")
        else:
            fails += 1
            print(f"{username} failed to log in.")
            messages.append(f"{username} failed to log in.")

    result_message = "\n".join(messages)
    if fails > 0:
        result_message += f"\n{fails} login failures."
    else:
        result_message += "\nAll logins successful."

    send_whatsapp_message(result_message)

if __name__ == "__main__":
    main()
