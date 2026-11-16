import json
import os
import time

from bs4 import BeautifulSoup
from curl_cffi import requests

BASE = "https://jkt48.com"
WEBHOOK = os.environ["https://discord.com/api/webhooks/1571742541085151282/uHSn5LKc6dcgSRCFf1u48f3NMlpIXduyrnu0zhVNvLpHnWWcKInb7IHXztCIkckdCSDe"]
STATE = "data/seen.json"


def fetch_news():
    r = requests.get(f"{BASE}/news", impersonate="chrome", timeout=30)
    r.raise_for_status()
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
    return items  # terbaru di depan


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
