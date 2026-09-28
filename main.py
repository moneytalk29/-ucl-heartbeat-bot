import discord
from discord.ext import tasks
import os

intents = discord.Intents.default()
client = discord.Client(intents=intents)

@tasks.loop(minutes=30)
async def heartbeat():
    print("Trying heartbeat...")
    for guild in client.guilds:
        # Find ONLY heartbeat channel
        channel = discord.utils.get(guild.text_channels, name="heartbeat")
        if channel:
            await channel.send("💓 UCL Bot heartbeat - I'm alive!")
            print(f"Heartbeat sent to heartbeat in {guild.name}")
        else:
            print(f"No heartbeat channel in {guild.name}")

@client.event
async def on_ready():
    print(f'Logged in as {client.user}')
    heartbeat.start()

client.run(os.getenv("DISCORD_TOKEN"))
