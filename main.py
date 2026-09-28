import discord
import os
import asyncio
from aiohttp import web
from discord.ext import tasks

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

async def handle(request):
    return web.Response(text="UCL Bot Alive")

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8080)
    await site.start()

@client.event
async def on_ready():
    print(f'Logged in as {client.user}')
    print('Starting heartbeat...')
    heartbeat.start()

@tasks.loop(minutes=1)
async def heartbeat():
    print("Trying heartbeat...")
    for guild in client.guilds:
        for ch in guild.text_channels:
            if ch.permissions_for(guild.me).send_messages:
                try:
                    await ch.send("❤️ **UCL Heartbeat** - Bot is alive! (every 1 min for testing)")
                    print(f"Heartbeat sent to {ch.name}")
                    return
                except:
                    continue

@client.event
async def on_message(message):
    if message.author == client.user:
        return
    if "ucl" in message.content.lower():
        await message.channel.send("UCL! 🔥")

async def main():
    await start_web_server()
    await client.start(os.environ['DISCORD_TOKEN'])

if __name__ == '__main__':
    asyncio.run(main())
