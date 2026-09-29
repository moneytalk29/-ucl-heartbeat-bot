import os, time, requests, re
from datetime import datetime
from difflib import SequenceMatcher

WEBHOOK = os.getenv("DISCORD_WEBHOOK_URL")
KALSHI = "https://api.elections.kalshi.com/trade-api/v2"
GAMMA = "https://gamma-api.polymarket.com"
CLOB = "https://clob.polymarket.com"

MIN_EDGE = 0.04 # 4c after fees
SEEN = set()

# Kalshi -> Polymarket tag map
SPORT_MAP = {
    "KXNFLGAME": "nfl",
    "KXCFBGAME": "ncaaf",
    "KXMLBGAME": "mlb",
    "KXEPLGAME": "epl",
    "KXATPMATCH": "atp",
    "KXWTAMATCH": "wta",
}

def post(msg):
    requests.post(WEBHOOK, json={"content": msg[:1900]}, timeout=10)

def get_kalshi_markets(series):
    r = requests.get(f"{KALSHI}/markets", params={"series_ticker": series, "status": "open", "limit": 100}, timeout=10)
    r.raise_for_status()
    return r.json().get("markets", [])

def get_poly_book(token_id):
    try:
        r = requests.get(f"{CLOB}/book", params={"token_id": token_id}, timeout=8)
        r.raise_for_status()
        asks = r.json().get("asks", [])
        if not asks: return 1.0, 0
        best = min(asks, key=lambda x: float(x['price']))
        return float(best['price']), float(best['size'])
    except: return 1.0, 0

def get_poly_markets(tag):
    try:
        r = requests.get(f"{GAMMA}/markets", params={"tag": tag, "active": True, "closed": False, "limit": 100}, timeout=10)
        r.raise_for_status()
        return r.json()
    except: return []

def similar(a,b):
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

# Preload seen
for s in SPORT_MAP.keys():
    try:
        for m in get_kalshi_markets(s):
            SEEN.add(m['ticker'])
    except: pass

post("✅ **FINAL SCANNER LIVE**\nNFL/CFB/MLB/Soccer/Tennis\nMoneyline + Props + Cross-Platform Kalshi vs Poly\nAlerts: PICK YES / PICK NO + 🚨")

while True:
    alerts = []
    try:
        for k_series, p_tag in SPORT_MAP.items():
            k_markets = get_kalshi_markets(k_series)
            p_markets = get_poly_markets(p_tag)

            for km in k_markets[:30]:
                ticker = km['ticker']
                title = km.get('title','') + " " + km.get('yes_sub_title','')
                ya = float(km.get('yes_ask_dollars') or 1)
                na = float(km.get('no_ask_dollars') or 1)
                yb = float(km.get('yes_bid_dollars') or 0)
                total = ya + na
                is_new = ticker not in SEEN
                if is_new: SEEN.add(ticker)

                # 1. LIVE ERROR INTRA Kalshi
                if total < 0.98:
                    alerts.append(f"🚨 **LIVE ERROR {k_series} — PICK YES+NO**\n`{ticker}`\nYES {ya*100:.0f}¢ + NO {na*100:.0f}¢ = {total*100:.0f}¢ | +{(1-total)*100:.0f}¢ FREE\n{title[:120]}")

                # 2. LOW LINE
                elif ya <= 0.20:
                    alerts.append(f"🚨 **LOW LINE {k_series} — PICK YES @ {ya*100:.0f}¢**\n`{ticker}`\n{title[:120]}")
                elif na <= 0.20:
                    alerts.append(f"🚨 **LOW LINE {k_series} — PICK NO @ {na*100:.0f}¢**\n`{ticker}`\n{title[:120]}")

                # 3. PROPS DROP
                if is_new and ya < 0.35:
                    alerts.append(f"🆕 **PROPS DROP {k_series} — PICK YES @ {ya*100:.0f}¢ (NEW)**\n`{ticker}`\n{title[:120]}")

                # 4. CROSS-PLATFORM Kalshi vs Polymarket
                # Find matching Poly market by name
                for pm in p_markets[:30]:
                    if similar(title, pm.get('question','')) > 0.65 or similar(km.get('ticker',''), pm.get('question','')) > 0.5:
                        tokens = pm.get('clobTokenIds')
                        if not tokens: continue
                        try:
                            import json
                            tids = json.loads(tokens) if isinstance(tokens, str) else tokens
                            py_ask, _ = get_poly_book(tids[0])
                            pn_ask, _ = get_poly_book(tids[1])

                            # Cross: Kalshi YES + Poly NO < 1
                            cross1 = ya + pn_ask
                            if cross1 < 1 - MIN_EDGE:
                                alerts.append(
                                    f"💰 **CROSS ARB {k_series} vs {p_tag.upper()}**\n"
                                    f"**PICK YES Kalshi @ {ya*100:.0f}¢ + NO Poly @ {pn_ask*100:.0f}¢**\n"
                                    f"Total {cross1*100:.0f}¢ | EDGE +{(1-cross1-0.02)*100:.0f}¢ net\n"
                                    f"Kalshi: `{ticker}`\nPoly: {pm.get('question','')[:80]}"
                                )
                            # Other side
                            cross2 = na + py_ask
                            if cross2 < 1 - MIN_EDGE:
                                alerts.append(
                                    f"💰 **CROSS ARB {k_series} vs {p_tag.upper()}**\n"
                                    f"**PICK NO Kalshi @ {na*100:.0f}¢ + YES Poly @ {py_ask*100:.0f}¢**\n"
                                    f"Total {cross2*100:.0f}¢ | EDGE +{(1-cross2-0.02)*100:.0f}¢ net\n"
                                    f"Kalshi: `{ticker}`"
                                )
                            break
                        except: pass

        if alerts:
            for a in alerts[:6]:
                post(a)
                time.sleep(1)
        else:
            print(f"{datetime.now().strftime('%H:%M:%S')} clean — {len(SEEN)} tracked")

    except Exception as e:
        post(f"🚨 **BOT ERROR** {e}")
        print(e)

    time.sleep(20)
