import os
import asyncio
import datetime
import discord
from discord.ext import tasks
from curl_cffi.requests import AsyncSession

PROXY_URL=os.getenv("PROXY_URL")
TOKEN=os.getenv("DISCORD_TOKEN")
CHAN_ID=int(os.getenv("DISCORD_CHANNEL_ID","0"))
URL="https://api.prizepicks.com/projections?per_page=250&page=1&single_stat=true&in_game=false&state_code=MA&game_mode=pickem"

async def fetch_markets():
    p={"http":PROXY_URL,"https":PROXY_URL} if PROXY_URL else None
    async with AsyncSession(impersonate="chrome") as s:
        for i in range(1,4):
            try:
                r=await s.get(URL,proxies=p,headers={"Referer":"https://app.prizepicks.com/","Origin":"https://app.prizepicks.com"},timeout=20)
                print(f"PrizePicks {r.status_code} attempt {i}")
                if r.status_code==200:
                    return r.json()
            except Exception as e:
                print(f"Fetch attempt {i} error: {e}")
            await asyncio.sleep(2**i)
    return None

def parse_props(payload):
    if not payload:
        return []
    data=payload.get('data',[])
    inc=payload.get('included',[])
    players={p.get('id'):p.get('attributes',{}).get('name','?') for p in inc if p.get('type')=='new_player'}
    out=[]
    for prop in data:
        a=prop.get('attributes',{})
        rel=prop.get('relationships',{})
        pid=(rel.get('new_player',{}).get('data',{}) or {}).get('id')
        out.append({'id':prop.get('id'),'player':players.get(pid,'?'),'line':a.get('line_score'),'start':a.get('start_time'),'stat':a.get('stat_type')})
    return out

def format_start(start):
    if not start:
        return 'TBD'
    try:
        dt=datetime.datetime.fromisoformat(start.replace('Z','+00:00'))
        return f"<t:{int(dt.timestamp())}:t>"
    except Exception:
        return str(start)

def build_embed(row):
    stat=row.get('stat','')
    return discord.Embed(title=row['player'],description=f"{stat} {row['line']} - {format_start(row['start'])}",color=0x00ff00)

intents=discord.Intents.default()
client=discord.Client(intents=intents)
posted=set()
first_run=True

@tasks.loop(minutes=5)
async def poll_loop():
    global first_run
    ch=client.get_channel(CHAN_ID)
    if not ch:
        return
    try:
        payload=await fetch_markets()
    except Exception as e:
        print(f"Fetch error {e}")
        return
    if not payload:
        print("Fetch failed")
        return

    rows=parse_props(payload)
    print(f"Got {len(rows)} props")

    if first_run:
        for r in rows:
            posted.add(r['id'])
        first_run=False
        print(f"First run seeded {len(posted)} - no spam")
        return

    for r in rows:
        if r['id'] in posted:
            continue
        posted.add(r['id'])
        try:
            await ch.send(embed=build_embed(r))
            await asyncio.sleep(1)
        except Exception as e:
            print('Send error',e)

@poll_loop.before_loop
async def before_poll():
    await client.wait_until_ready()

@client.event
async def on_ready():
    print('Logged in as',client.user)
    if not poll_loop.is_running():
        poll_loop.start()

client.run(TOKEN)
