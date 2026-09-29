import os,time,requests
TOKEN=os.getenv("DISCORD_TOKEN")
CHAN=os.getenv("DISCORD_CHANNEL_ID")
if not CHAN:
 CHAN=os.getenv("DISCORD_CHANNEL_I")
BASE="https://api.elections.kalshi.com"
PATH="/trade-api/v2/markets"
def post(m):
 a="https://discord.com"
 b="/api/v10/channels/"
 c="/messages"
 u=a+b+CHAN+c
 h={"Authorization":"Bot "+TOKEN}
 requests.post(u,headers=h,json={"content":m})
post("BOT STARTED")
while True:
 for s in ["KXNFLGAME","KXCFBGAME"]:
  r=requests.get(BASE+PATH,params={"series_ticker":s,"status":"open","limit":20},timeout=10).json()
  for k in r.get("markets",[]):
   ya=int(float(k.get("yes_ask_dollars")or 1)*100)
   if ya<=25:
    post(f"LOW {ya}c {k['ticker']}")
 time.sleep(20)
