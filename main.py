import os
import asyncio
import datetime
import discord
from discord.ext import tasks
from curl_cffi.requests import AsyncSession
from urllib.parse import quote

TOKEN=os.getenv("DISCORD_TOKEN")
CHAN_ID=int(os.getenv("DISCORD_CHANNEL_ID","0"))
URL="https://api.prizepicks.com/projections?per_page=250&page=1&single_stat=true&in_game=false&state_code=MA&game_mode=pickem"

# Froxy proxy - handles ;;;; password
PROXY_USER=os.getenv("PROXY_USER")
PROXY_PASSWORD=os.getenv("PROXY_PASSWORD")
PROXY_HOST=os.getenv("PROXY_HOST","proxy.froxy.com")
PROXY_PORT=os.getenv("PROXY_PORT","9000")
PROXY_URL=os.getenv("PROXY_URL")

if PROXY_USER and PROXY_PASSWORD:
    enc_pwd = quote(PROXY_PASSWORD, safe='')
    PROXY_URL = f"http://{PROXY_USER}:{enc_pwd}@{PROXY_HOST}:{PROXY_PORT}"

async def fetch_markets():
    async with AsyncSession(impersonate="chrome") as s:
        for i in range(1,4):
            try:
                r=await s.get(URL, proxy=PROXY_URL, headers={"Referer":"https://app.prizepicks.com/","Origin":"https://app.prizepicks.com"}, timeout=20)
                print(f"PrizePicks {r.status_code} attempt {i}")
                if r.status_code==200:
                    return r.json()
            except Exception as e:
                print(f"Fetch {i} error: {e}")
            await asyncio.sleep(2**i)
    return None

def parse_props(payload):
    if not payload:
        return []
    data=payload.get('data',[])
    inc=payload.get('included',[])
    players={p.get('id'):p.get('attributes',{}).get('name','?') for p in inc if p.get('type')=='new_player'}
    leagues={}
    for it in inc:
        if it.get('type')=='league':
            leagues[it.get('id')] = it.get('attributes',{}).get('name','').lower()
    player_league={}
    for p in inc:
        if p.get('type')=='new_player':
            rel = p.get('relationships',{}).get('league',{}).get('data',{})
            if rel:
                player_league[p.get('id')] = rel.get('id')
    out=[]
    for prop in data:
        a=prop.get('attributes',{})
        rel=prop.get('relationships',{})
        pid=(rel.get('new_player',{}).get('data',{}) or {}).get('id')
        lid = player_league.get(pid)
        league_name = leagues.get(lid, '') if lid else ''
        blob = f"{league_name} {a.get('description','')} {a.get('league','')} {a.get('stat_type','')}".lower()
        is_soccer = ('soccer' in blob or 'champions' in blob or 'ucl' in blob or 'uefa' in blob or 'mls' in blob or 'epl' in blob or 'la liga' in blob)
        if not is_soccer:
            continue
        out.append({'id':prop.get('id'),'player':players.get(pid,'?'),'line':a.get('line_score'),'start':a.get('start_time'),'stat':a.get('stat_type'),'league':league_name or 'soccer'})
    return out

def format_start(start):
    if not start:
        return 'TBD'
    try:
        dt=datetime.datetime.fromisoformat(start.replace('Z','+00:00'))
        return f"<t:{int(dt.timestamp())}:t>"
    except:
        return str(start)

def build_embed(row):
    return discord.Embed(title=row['player'],description=f"⚽ {row['league']} | {row['stat']} {row['line']} - {format_start(row['start'])}",color=0x00ff00)

intents=discord.Intents.default()
client=discord.Client(intents=intents)
posted=set()
first_run=True

@tasks.loop(minutes=5)
async def poll_loop():
    global first_run
    try:
        ch=client.get_channel(CHAN_ID)
        if not ch:
            print(f"Channel {CHAN_ID} not found")
            return
        payload=await fetch_markets()
        if not payload:
            return
        rows=parse_props(payload)
        print(f"Got {len(rows)} SOCCER props from {len(payload.get('data',[]))}")
        if first_run:
            for r in rows:
                posted.add(r['id'])
            first_run=False
            print(f"Seeded {len(posted)}")
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
    except Exception as e:
        print(f"Loop error: {e}")

@poll_loop.before_loop
async def before_poll():
    await client.wait_until_ready()

@client.event
async def on_ready():
    print('Logged in as',client.user)
    if not poll_loop.is_running():
        poll_loop.start()

client.run(TOKEN)
