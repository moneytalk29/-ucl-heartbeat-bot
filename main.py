import os
import asyncio
from datetime import datetime

import aiohttp
import discord
from discord.ext import tasks

DISCORD_TOKEN = os.environ['DISCORD_TOKEN']
CHANNEL_ID = int(os.environ['CHANNEL_ID_3'])

API_URL = 'https://api.prizepicks.com/projections'
PARAMS = {'league_id': '7', 'per_page': '250', 'single_stat': 'true'}
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                  '(KHTML, like Gecko) Chrome/120.0 Safari/537.36',
    'Accept': 'application/json',
    'Referer': 'https://app.prizepicks.com/',
    'Origin': 'https://app.prizepicks.com',
}

POLL_SECONDS = 300
PURPLE = 0x9B59B6

intents = discord.Intents.default()
client = discord.Client(intents=intents)
posted_ids = set()


async def fetch_projections():
    timeout = aiohttp.ClientTimeout(total=30)
    async with aiohttp.ClientSession(headers=HEADERS, timeout=timeout) as session:
        async with session.get(API_URL, params=PARAMS) as resp:
            if resp.status != 200:
                print('PrizePicks HTTP', resp.status)
                return None
            return await resp.json(content_type=None)


def parse_pass_attempts(payload):
    results = []
    players = {}
    for item in payload.get('included', []):
        if item.get('type') == 'new_player':
            attrs = item.get('attributes', {})
            players[item.get('id')] = attrs.get('display_name') or attrs.get('name') or 'Unknown'

    for prop in payload.get('data', []):
        attrs = prop.get('attributes', {})
        stat_type = str(attrs.get('stat_type', '')).lower()
        if 'pass attempt' not in stat_type:
            continue

        rel = prop.get('relationships', {})
        player_id = (rel.get('new_player', {}).get('data') or {}).get('id')
        name = players.get(player_id, 'Unknown')

        results.append({
            'id': prop.get('id'),
            'player': name,
            'line': attrs.get('line_score'),
            'start': attrs.get('start_time'),
        })
    return results


def format_start(start):
    if not start:
        return 'TBD'
    try:
        dt = datetime.fromisoformat(start)
        return '<t:' + str(int(dt.timestamp())) + ':F>'
    except Exception:
        return str(start)


def build_embed(row):
    line = row['line']
    date_text = format_start(row['start'])
    description = str(line) + ' - Pass Attempts\n\nStarts ' + date_text + '\n'
    embed = discord.Embed(
        title=row['player'],
        description=description,
        color=PURPLE,
    )
    embed.set_author(name='PrizePicks - Pass Attempts Are Up')
    return embed


@tasks.loop(seconds=POLL_SECONDS)
async def poll_loop():
    channel = client.get_channel(CHANNEL_ID)
    if channel is None:
        try:
            channel = await client.fetch_channel(CHANNEL_ID)
        except Exception as e:
            print('Channel error:', e)
            return

    try:
        payload = await fetch_projections()
    except Exception as e:
        print('Fetch error:', e)
        return
    if not payload:
        return

    rows = parse_pass_attempts(payload)
    print('Pass attempt props found:', len(rows))

    for row in rows:
        if row['id'] in posted_ids:
            continue
        posted_ids.add(row['id'])
        try:
            await channel.send(embed=build_embed(row))
            await asyncio.sleep(1.5)
        except Exception as e:
            print('Send error:', e)


@poll_loop.before_loop
async def before_poll():
    await client.wait_until_ready()


@client.event
async def on_ready():
    print('Logged in as', client.user)
    if not poll_loop.is_running():
        poll_loop.start()


client.run(DISCORD_TOKEN)
