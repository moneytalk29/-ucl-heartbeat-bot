import discord
import os
import asyncio
from aiohttp import web

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

async def handle(request):
    return web.Response(text="UCL Bot is alive!")

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', int(os.environ.get('PORT', 8080)))
    await site.start()

@client.event
async def on_ready():
    print(f'Logged in as {client.user}')

@client.event
async def on_message(message):
    if message.author == client.user:
        return
    if "ucl" in message.content.lower():
        await message.channel.send("UCL Heartbeat Bot is live! ⚽")

async def main():
    await start_web_server()
    await client.start(os.environ['DISCORD_TOKEN'])

if __name__ == '__main__':
    asyncio.run(main())
