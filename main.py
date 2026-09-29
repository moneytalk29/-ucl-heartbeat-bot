import os
import time
import requests
from datetime import datetime

WEBHOOK = os.getenv("DISCORD_WEBHOOK_URL")
BASE = "https://api.elections.kalshi.com/trade-api/v2"

SERIES = ["KXNFLGAME","KXNFLPLAYER","KXNFLPROPS","KXCFBGAME","KXCFB","KXMLBGAME","KXEPLGAME","KXLALIGA","KXBUNDESLIGA","KXSERIEA","KXMLSGAME","KXATPMATCH","KXWTAMATCH"]
SEEN = set()

def post(m):
    try:
        requests.post(WEBHOOK, json={"content": m[:1900]}, timeout=10)
    except:
        pass

for s in SERIES:
    try:
        r = requests.get(f"{BASE}/markets", params={"series_ticker": s, "status": "open", "limit": 100}, timeout=10)
        for x in r.json().get("markets", []):
            SEEN.add(x['ticker'])
    except:
        pass

post(f"✅ KALSHI FIXED - LIVE - Tracking {len(SEEN)} markets")

while True:
    alerts = []
    for series in SERIES:
        try:
            r = requests.get(f"{BASE}/markets", params={"series_ticker": series, "status": "open", "limit": 100}, timeout=12)
            if r.status_code != 200:
                continue
            for m in r.json().get("markets", []):
                ya = int(float(m.get("yes_ask_dollars") or 1)*100)
                na = int(float(m.get("no_ask_dollars") or 1)*100)
                title = m.get("title","")[:120]
                ticker = m["ticker"]
                total = ya + na
                is_new = ticker not in SEEN
                if is_new:
                    SEEN.add(ticker)
                if total < 98 and ya > 0 and na > 0:
                    alerts.append(f"🚨 LIVE ERROR {series} PICK YES+NO {ticker} YES {ya}c + NO {na}c = {total}c EDGE +{100-total}c {title}")
                elif ya <= 20:
                    alerts.append(f"🚨 LOW LINE {series} PICK YES @ {ya}c {ticker} {title}")
                elif na <= 20:
                    alerts.append(f"🚨 LOW LINE {series} PICK NO @ {na}c {ticker} {title}")
                elif is_new and "PLAYER" in series and ya <= 35:
                    alerts.append(f"🆕 PROPS DROP {series} PICK YES @ {ya}c NEW {ticker} {title}")
        except Exception as e:
            print(e)
    for a in alerts[:6]:
        post(a)
        time.sleep(1)
    print(f"{datetime.now().strftime('%H:%M:%S')} clean {len(SEEN)}")
    time.sleep(20)
