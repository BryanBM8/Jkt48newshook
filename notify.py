import json
import os
import time

from bs4 import BeautifulSoup
from curl_cffi import requests

BASE = "https://jkt48.com"
WEBHOOK = os.environ.get("DISCORD_WEBHOOK_URL")
if not WEBHOOK:
    raise SystemExit("Error: Environment variable DISCORD_WEBHOOK_URL belum diatur!")
STATE = "data/seen.json"


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://jkt48.com/",
    "Sec-Ch-Ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
}


def fetch_news():
    targets = ["chrome124", "chrome120", "safari17_0", "chrome"]
    last_response = None

    for target in targets:
        try:
            session = requests.Session(impersonate=target)
            # Ambil cookie/sesi dari root domain terlebih dahulu
            try:
                session.get(BASE, headers=HEADERS, timeout=15)
            except Exception:
                pass

            r = session.get(f"{BASE}/news", headers=HEADERS, timeout=30)
            if r.status_code == 200:
                soup = BeautifulSoup(r.text, "html.parser")
                items = []
                for a in soup.select('a[href^="/news/"]'):
                    title = a.select_one("div.font-bold")
                    if not title:
                        continue
                    cat = a.select_one("div.rounded-full")
                    date = a.select_one("div.lg\\:text-base")
                    items.append(
                        {
                            "slug": a["href"],
                            "title": title.get_text(strip=True),
                            "category": cat.get_text(strip=True) if cat else "-",
                            "date": date.get_text(strip=True) if date else "-",
                        }
                    )
                if items:
                    return items
            last_response = r
        except Exception as e:
            print(f"Percobaan dengan impersonate '{target}' gagal: {e}")

    if last_response is not None:
        print(f"Fetch gagal. Status Code: {last_response.status_code}")
        print(f"Headers: Server={last_response.headers.get('server')}, CF-Ray={last_response.headers.get('cf-ray')}")
        print("Response body preview:", last_response.text[:500])
        last_response.raise_for_status()

    raise SystemExit("Gagal mengambil berita setelah mencoba semua profil browser.")


def send(i):
    payload = {
        "embeds": [
            {
                "title": i["title"][:256],
                "url": BASE + i["slug"],
                "description": f"{i['category']} • {i['date']}",
                "color": 0xE20514,
                "footer": {"text": "JKT48 Official Website"},
            }
        ]
    }
    r = requests.post(WEBHOOK, json=payload, timeout=20)
    r.raise_for_status()


def load_seen():
    try:
        with open(STATE) as f:
            return json.load(f)
    except FileNotFoundError:
        return None


def save_seen(slugs):
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    with open(STATE, "w") as f:
        json.dump(slugs[-300:], f)


def main():
    items = fetch_news()
    if not items:
        raise SystemExit("Tidak ada berita terbaca (struktur HTML berubah atau diblok)")
    slugs = [i["slug"] for i in items]
    seen = load_seen()
    if seen is None:  # run pertama: tandai saja, jangan kirim
        save_seen(slugs[::-1])
        print("Run pertama: berita yang ada ditandai, tidak dikirim")
        return
    new = [i for i in reversed(items) if i["slug"] not in seen]
    for i in new:
        send(i)
        seen.append(i["slug"])
        save_seen(seen)
        time.sleep(1)
    print(f"{len(new)} berita baru dikirim")


if __name__ == "__main__":
    main()
