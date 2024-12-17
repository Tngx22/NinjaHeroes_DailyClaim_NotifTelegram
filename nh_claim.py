"""
Updated nh_claim-fast.py for GitHub with WhatsApp notifications via Twilio
"""

import concurrent.futures
import itertools
import os
import json
import platform
import re
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Functions to Load Data from Environment
def load_data_from_env():
    """Load data from the environment variable DATA_JSON."""
    try:
        # Get string JSON from environment variable
        raw_data = os.getenv("DATA_JSON")
        if not raw_data:
            raise ValueError("Environment variable 'DATA_JSON' tidak ditemukan atau kosong.")

        # Parse string JSON to Python object
        data = json.loads(raw_data)

        # Validate structure
        if not isinstance(data, list) or not all(isinstance(item, dict) for item in data):
            raise ValueError("Isi 'DATA_JSON' tidak valid. Harus berupa list of dictionaries.")

        return data

    except json.JSONDecodeError:
        raise ValueError("DATA_JSON mengandung string yang tidak valid sebagai JSON.")

    except Exception as e:
        raise Exception(f"Terjadi kesalahan saat memuat DATA_JSON: {e}")

# Constants
ROOT = Path(__file__).parent
SYSTEM = platform.system()
PERIOD = datetime.utcnow() + timedelta(hours=7)
PERIOD_D = PERIOD.replace(month=PERIOD.month % 12 + 1, day=1) - timedelta(days=1)
LOGIN_URL = 'https://kageherostudio.com/payment/server_.php'
CLAIM_URL = 'https://kageherostudio.com/event/index_.php?act=daily'
EVENT_URL = 'https://kageherostudio.com/event/?event=daily'
USER_NAME = 'txtuserid'
PASS_NAME = 'txtpassword'
ITEM_POST = 'itemId'
PROD_POST = 'periodId'
SRVR_POST = 'selserver'
REWARD_ID = 'data-id'
REWARD_CLS = '.reward-star'
REWARD_PROD = 'data-period'

# Twilio API credentials
TWILIO_SID = os.getenv("TWILIO_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER")
RECIPIENT_WHATSAPP_NUMBER = os.getenv("RECIPIENT_WHATSAPP_NUMBER")


def send_whatsapp_message(message):
    """Sends a WhatsApp message via Twilio."""
    url = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_SID}/Messages.json"
    data = {
        "From": f"whatsapp:{TWILIO_WHATSAPP_NUMBER}",
        "To": f"whatsapp:{RECIPIENT_WHATSAPP_NUMBER}",
        "Body": message,
    }
    auth = (TWILIO_SID, TWILIO_AUTH_TOKEN)

    response = requests.post(url, data=data, auth=auth)
    if response.status_code == 201:
        print("WhatsApp notification sent successfully.")
    else:
        print(f"Failed to send WhatsApp notification: {response.text}")


def main(data):
    """Main function to execute claims."""
    max_data = max(
        map(
            lambda x: re.search(r'^.*(?=@)', x.get('username')).group(),
            data
        ),
        key=len
    )
    max_len = len(max_data)

    n_threads = len(data) + 1
    stop = []
    fails = 0
    messages = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=n_threads) as executor:
        executor.submit(print_wait, stop)

        futures = [executor.submit(user_claim, user) for user in data]

        for future, user in zip(futures, data):
            username = user.get('username')
            username = re.sub(r'@.*', '', username).ljust(max_len)

            try:
                message = future.result()
                messages.append(f"{username}: {message}")
            except Exception as e:
                message = f"ERROR: {str(e)}"
                fails += 1
                messages.append(f"{username}: {message}")

            print(username, message)

        stop.append(0)

    result_message = "\n".join(messages)
    if fails:
        result_message += f"\n{fails} failed attempt{'s' if fails > 1 else ''}."
    else:
        result_message += "\n(➜ SUCCESSFULLY CLAIMED!)"

    send_whatsapp_message(result_message)


def print_wait(stop):
    """Prints a waiting animation."""
    for dot in itertools.cycle(['.', '..', '...']):
        if stop:
            break
        print(f'PLEASE WAIT{dot:<3}', end='\r')
        time.sleep(0.5)


def user_claim(user):
    """Handles individual claim logic."""
    username = user.get('username')
    password = user.get('password')
    server = user.get('server')

    session = requests.Session()
    is_logged = login(session, username, password)

    if not is_logged:
        raise Exception("Invalid login credentials")

    html = session.get(EVENT_URL)
    sess_html = BeautifulSoup(html.text, 'html.parser')

    is_claimed = claim(session, sess_html, server)

    return check_claim(sess_html, is_claimed)


def claim(session, sess_html, server):
    """Attempts to claim the reward."""
    reward = sess_html.select(REWARD_CLS)

    if not reward:
        return False

    item_id = reward[0].get(REWARD_ID)
    item_prod = reward[0].get(REWARD_PROD)

    result = session.post(CLAIM_URL, data={
        ITEM_POST: item_id,
        PROD_POST: item_prod,
        SRVR_POST: server,
    }).json()

    message = result.get('message')
    data = result.get('data')

    if '[-102]' in data:
        raise Exception("Invalid server ID")
    if 'invalid' in data:
        raise Exception("Reward/Period mismatch")

    return message == 'success'


def check_claim(sess_html, is_claimed):
    """Checks if the reward has been claimed."""
    n_claim = int(
        re.search(r'\d+', sess_html.select('h5')[0].text).group()
    )

    message = ('👍 CLAIM COMPLETED ' if not is_claimed else '') + f'CLAIMED: {n_claim + is_claimed}/{PERIOD_D.day} DAYS'

    return message


def login(session, username, password):
    """Logs in the user."""
    data = {
        USER_NAME: username,
        PASS_NAME: password,
    }

    response = session.post(LOGIN_URL, data=data)

    return response.url.endswith('pembayaran.php')


if __name__ == '__main__':
    os.system('cls' if SYSTEM == 'Windows' else 'clear')

    try:
        data = load_data_from_env()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

    main(data)
