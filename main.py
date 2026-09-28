import os, requests, discord, asyncio
from datetime import datetime

TOKEN = os.getenv("DISCORD_TOKEN")
CH = int(os.getenv("CHANNEL_ID_3", "0"))

bot = discord.Client(intents=discord.Intents.default())

def get_prizepicks_pass_attempts():
    # PrizePicks API - soccer pass attempts
    try:
        r = requests.get("https://api.prizepicks.com/projections?league_id=7", headers={"User-Agent":"Mozilla/5.0"})
        data = r.json()
        # Filter for Pass Attempts / Passes Attempted
        props = []
        for p in data.get("data", []):
            stat = p["attributes"].get("stat_type", "").lower()
            if "pass attempt" in stat or stat == "passes attempted" or stat == "pass attempts":
                props.append(p)
        return props
    except Exception as e:
        print(f"API Error: {e}")
        return []

@bot.event
async def on_ready():
    print(f"Logged in {bot.user} - CH={CH}")
    if CH == 0:
        print("CHANNEL_ID_3 is 0 - fix in Railway!")
        return
        
    channel = await bot.fetch_channel(CH)
    props = get_prizepicks_pass_attempts()
    
    if not props:
        print("No Pass Attempts found right now")
        return

    for prop in props[:5]: # first 5
        attrs = prop["attributes
