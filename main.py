import os
import asyncio
import datetime
import discord
from discord.ext import tasks
from curl_cffi.requests import AsyncSession
from urllib.parse import quote

TOKEN=os.getenv("DISCORD_TOKEN","").strip()
CHAN_ID=int(os.getenv("DISCORD_CHANNEL_ID","0"))
URL="https://api.prizepicks.com/projections?per_page=250&page={page}&single_stat=true&in_game=false&state_code=MA&game_mode=pickem"

# --- PROXY FIX: strip spaces, prefer PROXY_URL ---
PROXY_USER=os.getenv("PROXY_USER","").strip()
PROXY_PASSWORD=os.getenv("PROXY_PASSWORD","").strip()
PROXY_HOST=os.getenv("PROXY_HOST","proxy.froxy.com").strip()
PROXY_PORT=os.getenv("PROXY_PORT","9000").strip()
PROXY_URL=os.getenv("PROXY_URL","").strip() or None

if PROXY_USER and PROXY_PASSWORD and not PROXY_URL:
    enc_pwd = quote(PROXY_PASSWORD, safe='')
    PROXY_URL = f"http://{PROXY_USER}:{enc_pwd}@{PROXY_HOST}:{PROXY_PORT}"

print(f"Using proxy: {'YES' if PROXY_URL else 'NO'} {PROXY_HOST}:{PROXY_PORT}")

async def fetch_markets():
    async with AsyncSession(impersonate="chrome120", timeout=20) as s:
        all_payload = {'data': [], 'included': []}
        for page in range(1,6): # fetch 5 pages = 1250 props
            for attempt in range(1,4):
                try:
                    url = URL.format(page=page)
                    r=await s.get(url, proxy=PROXY_URL, headers={
                        "Referer":"https://app.prizepicks.com/",
                        "Origin":"https://app.prizepicks.com",
                        "User-Agent":"Mozilla/5.0"
                    })
                    print(f"PrizePicks p{page} {r.status_code} attempt {attempt} len={len(r.text)}")
                    if r.status_code==200:
                        j=r.json()
                        # DEBUG LOGGING
                        if page==1:
                            leagues_debug=set()
                            for it in j.get('included',[]):
                                if it.get('type')=='league':
                                    leagues_debug.add(it.get('attributes',{}).get('name',''))
                            print(f"Leagues on page1: {list(leagues_debug)[:20]} total_items={len(j.get('data',[]))}")
                        all_payload['data'].extend(j.get('data',[]))
                        all_payload['included'].extend(j.get('included',[]))
                        break
                except Exception as e:
                    print(f"Fetch p{page} {attempt} error: {e}")
                await asyncio.sleep(2**attempt)
            await asyncio.sleep(0.8)
        return all_payload if all_payload['data'] else None

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
        blob = f"{league_name} {a.get('description','')} {str(a.get('league',''))} {a.get('stat_type','')} {a.get('league_name','')}".lower()
        is_soccer = any(x in blob for x in ['soccer','champions','ucl','uefa','mls','epl','premier league','la liga','bundesliga','ligue 1','serie a','ucl '])
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
        print(f"Got {len(rows)} SOCCER props from {len(payload.get('data',[]))} total")
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
