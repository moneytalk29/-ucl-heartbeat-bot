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
