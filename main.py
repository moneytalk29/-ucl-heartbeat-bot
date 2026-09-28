import discord, os, time
from discord.ext import tasks
from datetime import datetime

TOKEN = os.getenv("DISCORD_TOKEN")
UFC_CH_ID = int(os.getenv("CHANNEL_ID_3", "0"))
HB_ID = int(os.getenv("HEARTBEAT_CHANNEL", "0"))

print(f"ENV CHECK: UFC_CH={UFC_CH_ID} HB={HB_ID}")

bot = discord.Client(intents=discord.Intents.default())

def format_exact(fight_title, props, starts_str, platform="Underdog"):
    lines_text = ""
    for name_stat, line in props:
        lines_text += f"**{name_stat}** `{line}`\n"
    desc = f"{lines_text}\n**Starts**\n{starts_str}\n\n{platform} • {len(props)} prop(s) | Today at {datetime.now().strftime('%-I:%M %p')}"
    embed = discord.Embed(title=fight_title, description=desc, color=0x2B2D31)
    embed.set_author(name=f"🚨 {platform} — UFC {props[0][0].split('—')[-1].strip().upper()} ARE UP")
    return embed

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} - EXACT CLONE MODE")
    ch = await bot.fetch_channel(UFC_CH_ID) if UFC_CH_ID else None
    if ch:
        embed = format_exact("Camila Reynoso vs Aieza Bertolso", [("Camila Reynoso — Significant Strikes", "10.5")], "Tuesday, September 29, 2026 at 7:20 PM", "Underdog")
        await ch.send(embed=embed)
        print("SENT TEST TO UFC")
    hb = await bot.fetch_channel(HB_ID) if HB_ID else None
    if hb:
        await hb.send(f"💜 Alive - Exact clone active | {datetime.now().strftime('%I:%M %p')}")

if not TOKEN:
    print("TOKEN MISSING")
    while True:
        time.sleep(60)
else:
    bot.run(TOKEN)
