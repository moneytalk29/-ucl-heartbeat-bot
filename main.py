import os,time,requests
W=os.environ.get("DISCORD_WEBHOOK_URL")
B="https://api.elections.kalshi.com/trade-api/v2"
S=["KXNFLGAME","KXNFLPLAYER","KXCFBGAME","KXMLBGAME"]
import json
requests.post(W,json={"content":"✅ BOT STARTED - testing"})
while True:
 for s in S:
  try:
   r=requests.get(f"{B}/markets",params={"series_ticker":s,"status":"open","limit":20},timeout=10).json()
   for m in r.get("markets",[]):
    ya=int(float(m.get("yes_ask_dollars")or 1)*100)
    if ya<=20: requests.post(W,json={"content":f"🚨 LOW YES @{ya}c {m['ticker']}"})
  except: pass
 print("clean")
 time.sleep(20)
