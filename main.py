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

PROXY_URL=os.getenv("PROXY_URL","").strip() or None
print(f"Proxy active: {bool(PROXY_URL)} -> {PROXY_URL[:30] if PROXY_URL else 'NONE'}")

async def fetch_markets():
    async with AsyncSession(impersonate="chrome120", timeout=25) as s:
        out={'data':[],'included':[]}
        for page in range(1,3):
            for attempt in range(1,4):
                try:
                    r=await s.get(URL.format(page=page), proxy=PROXY_URL, headers={"Referer":"https://app.prizepicks.com/","Origin":"https://app.prizepicks.com"}, timeout=25)
                    txt=r.text[:200].replace('\n',' ')
                    print(f"p{page} {r.status_code} len={len(r.text)} {txt}")
                    if r.status_code==200 and len(r.text)>1000:
                        j=r.json()
                        out['data'].extend(j.get('data',[]))
                        out['included'].extend(j.get('included',[]))
                        break
                    if r.status_code==429:
                        print("429 rate limit, sleep 30s")
                        await asyncio.sleep(30)
                    else:
                        await asyncio.sleep(5*attempt)
                except Exception as e:
                    print(f"err p{page} a{attempt}: {e}")
                    await asyncio.sleep(5)
            await asyncio.sleep(6)
        return out if out['data'] else None

def parse_props(payload):
    if not payload: return []
    data=payload.get('data',[]); inc=payload.get('included',[])
    players={p.get('id'):p.get('attributes',{}).get('name','?') for p in inc if p.get('type')=='new_player'}
    leagues={}
    for it in inc:
        if it.get('type')=='league':
            leagues[it.get('id')] = it.get('attributes',{}).get('name','').lower()
    player_league={}
    for p in inc:
        if p.get('type')=='new_player':
            rel = p.get('relationships',{}).get('league',{}).get('data',{})
            if rel: player_league[p.get('id')] = rel.get('id')
    out=[]
    for prop in data:
        a=prop.get('attributes',{}); rel=prop.get('relationships',{})
        pid=(rel.get('new_player',{}).get('data',{}) or {}).get('id')
        lid = player_league.get(pid)
        league_name = leagues.get(lid, '') if lid else ''
        blob = f"{league_name} {a.get('description','')} {a.get('league','')} {a.get('stat_type','')}".lower()
        is_soccer = any(x in blob for x in ['soccer','champions','ucl','uefa','mls','epl','premier','la liga','bundesliga'])
        if not is_soccer: continue
        out.append({'id':prop.get('id'),'player':players.get(pid,'?'),'line':a.get('line_score'),'start':a.get('start_time'),'stat':a.get('stat_type'),'league':league_name or 'soccer'})
    return out

def format_start(start):
    if not start: return 'TBD'
    try:
        dt=datetime.datetime.fromisoformat(start.replace('Z','+00:00'))
        return f"<t:{int(dt.timestamp())}:t>"
    except: return str(start)

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
        if not ch: return
        payload=await fetch_markets()
        if not payload: return
        rows=parse_props(payload)
        print(f"Got {len(rows)} SOCCER from {len(payload.get('data',[]))} total")
        if first_run:
            for r in rows: posted.add(r['id'])
            first_run=False; print(f"Seeded {len(posted)}"); return
        for r in rows:
            if r['id'] in posted: continue
            posted.add(r['id'])
            try: await ch.send(embed=build_embed(r)); await asyncio.sleep(1)
            except Exception as e: print('Send err',e)
    except Exception as e: print(f"Loop err: {e}")

@poll_loop.before_loop
async def before_poll(): await client.wait_until_ready()
@client.event
async def on_ready():
    print('Logged in as',client.user)
    if not poll_loop.is_running(): poll_loop.start()
client.run(TOKEN)
