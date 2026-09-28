import discord, requests, os, asyncio
from discord.ext import tasks
from datetime import datetime

TOKEN = os.getenv("DISCORD_TOKEN")
SOCCER_CH = int(os.getenv("CHANNEL_ID_1", "0"))
NFL_CH = int(os.getenv("CHANNEL_ID_2", "0"))
MLB_CH = int(os.getenv("CHANNEL_ID_3", "0"))

print(f"ENV CHECK: SOCCER={SOCCER_CH} NFL={NFL_CH} MLB={MLB_CH}")
if not TOKEN:
    print("ERROR: DISCORD_TOKEN missing in Railway Variables!")
    exit(1)

intents = discord.Intents.default()
bot = discord.Client(intents=intents)
tracked = set()

def make_embed(title, player_stat, line, starts, platform, tag):
    desc = f"**{player_stat}** `{line}`\n\n**Starts**\n{starts}\n\n{platform} • 1 prop(s) | Today at {datetime.now().strftime('%-I:%M %p')}"
    embed = discord.Embed(title=title, description=desc, color=0x2B2D31)
    embed.set_author(name=f"🚨 {platform} — {tag} ARE UP")
    return embed

def get_target(league):
    up = (league or "").upper()
    if any(x in up for x in ["SOCCER","EPL","MLS","LIGA","UCL","CHAMPIONS","LA LIGA"]):
        return SOCCER_CH, "SOCCER"
    if "NFL" in up or "NCAAF" in up:
        return NFL_CH, "NFL"
    if "MLB" in up:
        return MLB_CH, "MLB"
    return None, None

@tasks.loop(seconds=75)
async def loop():
    try:
        r = requests.get("https://api.prizepicks.com/projections?per_page=250", headers={"User-Agent":"Mozilla/5.0"}, timeout=15)
        data = r.json()
    except Exception as e:
        print(f"API error: {e}")
        return

    inc = {x['id']: x for x in data.get('included', [])}
    for p in data.get('data', []):
        try:
            pid = p['id']
            if pid in tracked:
                continue
            
            league_id = p['relationships']['league']['data']['id']
            league_name = inc.get(league_id,{}).get('attributes',{}).get('name','')
            target, tag = get_target(league_name)
            if not target or target == 0:
                continue

            stat = p['attributes'].get('stat_type','')
            player_id = p['relationships']['new_player']['data']['id']
            player = inc.get(player_id,{}).get('attributes',{}).get('name','Unknown')
            line = p['attributes'].get('line_score',0)
            
            embed = make_embed(player, f"{player} — {stat}", line, datetime.now().strftime("%A, %B %d, %Y at %-I:%M %p"), "PrizePicks", tag)
            ch = bot.get_channel(target)
            if ch:
                await ch.send(embed=embed)
                print(f"Sent {tag}: {player}")
            
            tracked.add(pid)
            await asyncio.sleep(0.4)
        except Exception as e:
            print(f"Loop item error: {e}")
            continue

@bot.event
async def on_ready():
    print(f"Bot Ready as {bot.user} - Soccer/NFL/MLB")
    if not loop.is_running():
        loop.start()

bot.run(TOKEN)
