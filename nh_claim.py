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
ITEM_POST = 'itemId'
PROD_POST = 'periodId'
SRVR_POST = 'selserver'
REWARD_CLS = '.reward-star'

# Kredensial Telegram Bot dari variabel lingkungan
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


# Fungsi untuk memuat data pengguna dari variabel lingkungan
def load_data_from_env():
    """Memuat data dari variabel lingkungan DATA_JSON."""
    try:
        raw_data = os.getenv("DATA_JSON")
        if not raw_data:
            raise ValueError("Variabel lingkungan 'DATA_JSON' tidak ditemukan atau kosong.")

        data = json.loads(raw_data)

        # Validasi struktur data
        if not isinstance(data, list) or not all(isinstance(item, dict) for item in data):
            raise ValueError("Isi 'DATA_JSON' tidak valid. Harus berupa list of dictionaries.")

        return data

    except json.JSONDecodeError:
        raise ValueError("DATA_JSON mengandung string yang tidak valid sebagai JSON.")

    except Exception as e:
        raise Exception(f"Terjadi kesalahan saat memuat DATA_JSON: {e}")


# Fungsi untuk mengirim pesan Telegram
def send_telegram_message(message):
    """Mengirim pesan melalui Telegram Bot dengan format yang lebih baik."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Kredensial Telegram tidak diatur. Harap periksa TELEGRAM_BOT_TOKEN dan TELEGRAM_CHAT_ID.")
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
            print("Notifikasi Telegram berhasil dikirim.")
        else:
            print(f"Gagal mengirim notifikasi Telegram: {response.status_code}, {response.text}")
    except Exception as e:
        print(f"Terjadi kesalahan saat mengirim pesan Telegram: {e}")


# Fungsi untuk melakukan login
def login(session, username, password):
    """Melakukan login untuk pengguna."""
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
                print(f"Berhasil login untuk {username}")
                return True
            else:
                print(f"Respons sukses yang tidak terduga untuk {username}, URL: {response.url}")
                return False

        elif response.status_code == 403:
            print(f"Login gagal untuk {username} (403 Forbidden). Memeriksa informasi tambahan...")
            print(f"Konten respons mentah: {response.text}")
            return False

        else:
            print(f"Respons tidak terduga untuk {username}, status code: {response.status_code}, konten: {response.text}")
            return False

    except Exception as e:
        print(f"Terjadi kesalahan saat login untuk {username}: {e}")
        return False


# Fungsi untuk mengklaim hadiah
def claim_rewards(session, username, server):
    """Mengklaim hadiah harian untuk pengguna."""
    data = {
        SRVR_POST: server,
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    try:
        response = session.post(CLAIM_URL, data=data, headers=headers)
        if response.status_code == 200:
            # Parsing respons untuk menemukan item yang diklaim (logika placeholder)
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
            print(f"Gagal mengklaim hadiah untuk {username}: {response.status_code}")
            return []

    except Exception as e:
        print(f"Terjadi kesalahan saat mengklaim hadiah untuk {username}: {e}")
        return []


# Fungsi utama untuk memproses login dan klaim hadiah
def main():
    try:
        data = load_data_from_env()
    except Exception as e:
        print(f"Kesalahan: {e}")
        send_telegram_message(f"❌ <b>Terjadi kesalahan saat menjalankan skrip:</b> {str(e)}")
        return

    session = cloudscraper.create_scraper()  # Menggunakan cloudscraper untuk menangani tantangan Cloudflare
    fails = 0
    success_count = 0
    messages = []

    for user in data:
        username = user.get("username")
        password = user.get("password")
        server = user.get("server")

        print(f"Memproses login untuk: {username}")
        if login(session, username, password):
            success_count += 1
            messages.append(f"✅ <b>{username}</b> berhasil login.")
            
            # Klaim hadiah setelah login
            claimed_items = claim_rewards(session, username, server)
            if claimed_items:
                items_message = f"🎁 <b>Item yang diklaim untuk {username}:</b>\n" + "\n".join(claimed_items)
                messages.append(items_message)
            else:
                messages.append(f"⚠️ <b>{username}</b> tidak mengklaim item apapun.")
        else:
            fails += 1
            messages.append(f"❌ <b>{username}</b> gagal login.")

        # Tambahkan penundaan untuk menghindari pembatasan laju
        time.sleep(2)

    # Format notifikasi Telegram yang lebih baik
    result_message = "🌟 <b>Hasil Login dan Klaim Hadiah</b> 🌟\n\n"
    for message in messages:
        result_message += f"{message}\n"

    result_message += f"\n🎉 <b>Total Login Berhasil:</b> {success_count} dari <b>{len(data)}</b> akun.\n"
    result_message += f"⚠️ <b>Total Login Gagal:</b> {fails} percobaan.\n"

    result_message += "\n\n📅 <i>Laporan dihasilkan pada:</i> <b>{}</b>".format(time.strftime("%Y-%m-%d %H:%M:%S"))

    # Kirim hasil via Telegram
    send_telegram_message(result_message)


if __name__ == "__main__":
    main()
