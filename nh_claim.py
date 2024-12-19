import os
import json
import time
import requests
import cloudscraper
from dotenv import load_dotenv
from bs4 import BeautifulSoup

# Memuat variabel lingkungan dari .env
load_dotenv()

# Konstanta
LOGIN_URL = 'https://kageherostudio.com/payment/server_.php'
EVENT_URL = 'https://kageherostudio.com/event/?event=daily'
CLAIM_URL = 'https://kageherostudio.com/event/index_.php?act=daily'

USER_NAME = 'txtuserid'
PASS_NAME = 'txtpassword'
SRVR_POST = 'selserver'
REWARD_CLS = '.reward-star'

# Kredensial Telegram Bot dari variabel lingkungan
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


# Fungsi untuk memuat data pengguna dari variabel lingkungan
def load_data_from_env():
    try:
        raw_data = os.getenv("DATA_JSON")
        if not raw_data:
            raise ValueError("Variabel lingkungan 'DATA_JSON' tidak ditemukan atau kosong.")
        data = json.loads(raw_data)
        if not isinstance(data, list) or not all(isinstance(item, dict) for item in data):
            raise ValueError("Isi 'DATA_JSON' tidak valid. Harus berupa list of dictionaries.")
        return data
    except json.JSONDecodeError:
        raise ValueError("DATA_JSON mengandung string yang tidak valid sebagai JSON.")
    except Exception as e:
        raise Exception(f"Terjadi kesalahan saat memuat DATA_JSON: {e}")


# Fungsi untuk mengirim pesan Telegram
def send_telegram_message(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Kredensial Telegram tidak diatur.")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        response = requests.post(url, data=data)
        if response.status_code == 200:
            print("Notifikasi Telegram berhasil dikirim.")
        else:
            print(f"Gagal mengirim notifikasi Telegram: {response.status_code}, {response.text}")
    except Exception as e:
        print(f"Kesalahan saat mengirim pesan Telegram: {e}")


# Fungsi untuk memeriksa klaim harian
def is_claimed_today():
    today = time.strftime("%Y-%m-%d")
    if os.path.exists("claimed_today.txt"):
        with open("claimed_today.txt", "r") as file:
            last_claim_date = file.read().strip()
            return last_claim_date == today
    return False


# Fungsi untuk menandai klaim selesai hari ini
def mark_claimed_today():
    today = time.strftime("%Y-%m-%d")
    with open("claimed_today.txt", "w") as file:
        file.write(today)


# Fungsi untuk melakukan login
def login(session, username, password):
    data = {USER_NAME: username, PASS_NAME: password}
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        response = session.post(LOGIN_URL, data=data, headers=headers)
        if response.status_code == 200 and "success" in response.url:
            print(f"Berhasil login untuk {username}")
            return True
        else:
            print(f"Gagal login untuk {username}: {response.text}")
            return False
    except Exception as e:
        print(f"Kesalahan saat login untuk {username}: {e}")
        return False


# Fungsi untuk mengklaim hadiah
def claim_rewards(session, username, server):
    data = {SRVR_POST: server}
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        response = session.post(CLAIM_URL, data=data, headers=headers)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            items = soup.select(REWARD_CLS)
            claimed_items = [item.get_text().strip() for item in items]
            if claimed_items:
                print(f"Item yang diklaim: {', '.join(claimed_items)}")
                return claimed_items
            else:
                print(f"Tidak ada item yang diklaim untuk {username}.")
                return []
        else:
            print(f"Gagal klaim hadiah untuk {username}: {response.status_code}")
            return []
    except Exception as e:
        print(f"Kesalahan saat klaim hadiah untuk {username}: {e}")
        return []


# Fungsi utama
def main():
    if is_claimed_today():
        print("Klaim sudah dilakukan hari ini. Melewati proses.")
        send_telegram_message("⚠️ Klaim sudah dilakukan hari ini. Tidak ada tindakan lebih lanjut.")
        return

    try:
        data = load_data_from_env()
    except Exception as e:
        print(f"Kesalahan: {e}")
        send_telegram_message(f"❌ Terjadi kesalahan: {str(e)}")
        return

    session = cloudscraper.create_scraper()
    success_count = 0
    fail_count = 0
    messages = []

    for user in data:
        username = user.get("username")
        password = user.get("password")
        server = user.get("server")

        if login(session, username, password):
            success_count += 1
            messages.append(f"✅ <b>{username}</b> berhasil login.")
            claimed_items = claim_rewards(session, username, server)
            if claimed_items:
                messages.append(f"🎁 Item diklaim: {', '.join(claimed_items)}")
            else:
                messages.append(f"⚠️ <b>{username}</b> tidak ada item yang diklaim.")
        else:
            fail_count += 1
            messages.append(f"❌ <b>{username}</b> gagal login.")

    result_message = "🌟 <b>Hasil Login dan Klaim</b> 🌟\n\n" + "\n".join(messages)
    result_message += f"\n🎉 Total Login Berhasil: {success_count}\n⚠️ Total Login Gagal: {fail_count}\n"
    send_telegram_message(result_message)

    if success_count > 0:
        mark_claimed_today()


if __name__ == "__main__":
    main()
