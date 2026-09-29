import os, time, requests
from datetime import datetime

WEBHOOK = os.environ.get("DISCORD_WEBHOOK_URL")
BASE = "https://api.elections.kalshi.com/trade-api/v2"
SERIES = ["KXNFLGAME","KXNFLPLAYER","KXCFBGAME","KXMLBGAME"]
SEEN = set()

def post(m):
    try:
        requests.post(WEBHOOK, json={"content": m[:1900]}, timeout=10)
    except:
        pass

post("✅ BOT STARTED - testing")

while True:
    try:
        for s in SERIES:
            r = requests.get(f"{BASE}/markets", params={"series_ticker": s, "status": "open", "limit": 20}, timeout=10)
            if r.status_code != 200:
                continue
            for mk in r.json().get("markets", []):
                ya = int(float(mk.get("yes_ask_dollars") or 1)*100)
                na = int(float(mk.get("no_ask_dollars") or 1)*100)
                if ya + na < 98:
                    post(f"🚨 ERROR {s} YES {ya}c + NO {na}c = {ya+na}c")
                if ya <= 20:
                    post(f"🚨 LOW YES @ {ya}c {mk['ticker']}")
    except Exception as e:
        print(e)
    print("clean")
    time.sleep(20)
