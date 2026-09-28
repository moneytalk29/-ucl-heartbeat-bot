import discord
import os
import asyncio
from discord.ext import tasks

TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f"Logged in as {client.user}")
    heartbeat.start()

@tasks.loop(minutes=1)
async def heartbeat():
    print("Heartbeat OK - bot is alive")

@client.event
async def on_message(message):
    if message.author == client.user:
        return
    if message.content.lower() == "!ping":
        await message.channel.send("Pong! Bot is alive")

# Crash protection
if not TOKEN:
    print("ERROR: DISCORD_TOKEN not set in Railway Variables")
    while True:
        print("Waiting for TOKEN...")
        import time
        time.sleep(60)
else:
    client.run(TOKEN)
