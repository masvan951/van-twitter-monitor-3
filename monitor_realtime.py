import os
import json
import asyncio
import requests
import twscrape

# ── KONFIGURASI ──────────────────────────────────────────────
TARGET_USERNAME  = os.environ.get("TWITTER_USERNAME", "elonmusk")
TELEGRAM_TOKEN   = os.environ.get("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
TW_EMAIL         = os.environ.get("TW_EMAIL", "")
TW_USERNAME      = os.environ.get("TW_USERNAME", "")
TW_PASSWORD      = os.environ.get("TW_PASSWORD", "")
SEEN_FILE        = "seen_tweets.json"
MAX_TWEETS       = 5
CHECK_INTERVAL   = 60  # detik
# ─────────────────────────────────────────────────────────────


def load_seen() -> set:
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE, "r") as f:
            return set(json.load(f))
    return set()


def save_seen(seen: set) -> None:
    with open(SEEN_FILE, "w") as f:
        json.dump(list(seen), f)


def send_telegram(message: str) -> bool:
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️  TELEGRAM_TOKEN atau TELEGRAM_CHAT_ID belum diset!")
        return False
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": False,
    }
    try:
        r = requests.post(url, json=payload, timeout=10)
        r.raise_for_status()
        print("✅ Pesan terkirim ke Telegram")
        return True
    except requests.RequestException as e:
        print(f"❌ Gagal kirim Telegram: {e}")
        return False


async def fetch_tweets_async(api: twscrape.API) -> list:
    tweets = []
    user = await api.user_by_login(TARGET_USERNAME)
    if not user:
        print(f"❌ User @{TARGET_USERNAME} tidak ditemukan")
        return []
    async for tweet in api.user_tweets(user.id, limit=MAX_TWEETS):
        tweets.append(tweet)
    return tweets


async def main_async():
    api = twscrape.API()
    await api.pool.add_account(TW_USERNAME, TW_PASSWORD, TW_EMAIL, TW_PASSWORD)
    await api.pool.login_all()

    print(f"🚀 Bot aktif! Memantau @{TARGET_USERNAME} setiap {CHECK_INTERVAL} detik...")
    send_telegram(f"✅ Bot monitoring <b>@{TARGET_USERNAME}</b> aktif!\nMemantau setiap {CHECK_INTERVAL} detik.")

    seen = load_seen()

    print("📥 Inisialisasi tweet lama...")
    existing = await fetch_tweets_async(api)
    for t in existing:
        seen.add(str(t.id))
    save_seen(seen)
    print(f"✅ {len(seen)} tweet lama diabaikan. Siap memantau!")

    while True:
        try:
            print(f"\n⏰ Mengecek tweet baru...")
            tweets = await fetch_tweets_async(api)
            new_count = 0

            for tweet in reversed(tweets):
                tweet_id = str(tweet.id)
                if tweet_id in seen:
                    continue

                tweet_url  = f"https://x.com/{TARGET_USERNAME}/status/{tweet_id}"
                tweet_text = tweet.rawContent or "(tanpa teks)"
                date_str   = tweet.date.strftime("%Y-%m-%d %H:%M UTC") if tweet.date else ""

                message = (
                    f"🐦 <b>Tweet baru dari @{TARGET_USERNAME}</b>\n\n"
                    f"{tweet_text}\n\n"
                    f"🕒 {date_str}\n"
                    f"🔗 {tweet_url}"
                )

                if send_telegram(message):
                    seen.add(tweet_id)
                    new_count += 1

            save_seen(seen)
            print(f"💬 {new_count} tweet baru dikirim.")

        except Exception as e:
            print(f"❌ Error: {e}")

        print(f"💤 Menunggu {CHECK_INTERVAL} detik...")
        await asyncio.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    asyncio.run(main_async())
