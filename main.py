import discord, requests, os, asyncio
from discord.ext import tasks
from datetime import datetime

TOKEN = os.getenv("DISCORD_TOKEN")
SOCCER_CH = int(os.getenv("CHANNEL_ID_1", "0")) # SOCCER
NFL_CH = int(os.getenv("CHANNEL_ID_2", "0")) # NFL
MLB_CH = int(os.getenv("CHANNEL_ID_3", "0")) # MLB

bot = discord.Client(intents=discord.Intents.default())
tracked = set()

def make_embed(title, player_stat, line, starts, platform, league_tag):
    desc = f"**{player_stat}** `{line}`\n\n**Starts**\n{starts}\n\n{platform} • 1 prop(s) | Today at {datetime.now().strftime('%-I:%M %p')}"
    embed = discord.Embed(title=title, description=desc, color=0x2B2D31)
    embed.set_author(name=f"🚨 {platform} — {league_tag} {player_stat.split('—')[-1].strip().upper()} ARE UP")
    return embed

def route(league_name):
    up = league_name.upper()
    if any(x in up for x in ["EPL","LA LIGA","BUNDESLIGA","SERIE A","LIGUE 1","MLS","CHAMPIONS","SOCCER"]):
        return SOCCER_CH, "SOCCER"
    if any(x in up for x in ["NFL","NCAAF"]):
        return NFL_CH, "NFL"
    if "MLB" in up:
        return MLB_CH, "MLB"
    return None, None

@tasks.loop(seconds=75)
async def loop():
    try:
        data = requests.get("https://api.prizepicks.com/projections?per_page=250", headers={"User-Agent":"Mozilla/5.0"}, timeout=15).json()
    except:
        return
    inc = {x['id']: x for x in data.get('included', [])}
    for p in data.get('data', []):
        if p['id'] in tracked: continue
        league = inc.get(p['relationships']['league']['data']['id'],{}).get('attributes',{}).get('name','')
        target, tag = route(league)
        if not target: continue

        stat = p['attributes'].get('stat_type','')
        player = inc.get(p['relationships']['new_player']['data']['id'],{}).get('attributes',{}).get('name','Unknown')
        line = p['attributes'].get('line_score',0)

        # SAME FORMAT FOR ALL 3
        title = player
        starts = datetime.now().strftime("%A, %B %d, %Y at %-I:%M %p")
        player_stat = f"{player} — {stat}"

        embed = make_embed(title, player_stat, line, starts, "PrizePicks", tag)
        ch = bot.get_channel(target)
        if ch: await ch.send(embed=embed)
        tracked.add(p['id'])
        await asyncio.sleep(0.3)

@bot.event
async def on_ready():
    print("Ready - Soccer/NFL/MLB same format")
    loop.start()

bot.run(TOKEN)
