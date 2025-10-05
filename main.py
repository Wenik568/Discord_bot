import discord
from discord.ext import commands
import yt_dlp
import asyncio
import os
import re
from dotenv import load_dotenv
from collections import deque

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
SPOTIFY_CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
SPOTIFY_CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
bot = commands.Bot(command_prefix='!', intents=intents)

def find_ffmpeg():
    """Find FFmpeg in project folder or system PATH"""
    local_ffmpeg = os.path.join(os.path.dirname(__file__), 'ffmpeg.exe')
    if os.path.exists(local_ffmpeg):
        print(f'✅ Found FFmpeg in project folder: {local_ffmpeg}')
        return local_ffmpeg
    print('ℹ️ Using system FFmpeg from PATH')
    return 'ffmpeg'

FFMPEG_PATH = find_ffmpeg()

YDL_OPTIONS = {
    'format': 'bestaudio[ext=webm]/bestaudio[ext=m4a]/bestaudio/best',
    'noplaylist': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'ytsearch',
    'source_address': '0.0.0.0',
    'ignoreerrors': True,
    'nocheckcertificate': True,
    'geo_bypass': True,
    'age_limit': None,
    'no_check_certificate': True,
    'prefer_insecure': False,
    'socket_timeout': 10,
    'retries': 2,
}

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn -b:a 128k'
}

# URL patterns for auto-detection
YOUTUBE_PATTERNS = [
    r'https?://(?:www\.)?youtube\.com/watch\?v=[\w-]+',
    r'https?://(?:www\.)?youtu\.be/[\w-]+',
    r'https?://(?:www\.)?youtube\.com/playlist\?list=[\w-]+',
]

SPOTIFY_TRACK_PATTERNS = [
    r'https?://open\.spotify\.com/track/[\w]+',
    r'https?://spotify\.link/[\w]+',
]

SPOTIFY_PLAYLIST_PATTERNS = [
    r'https?://open\.spotify\.com/playlist/[\w]+',
]

SPOTIFY_ALBUM_PATTERNS = [
    r'https?://open\.spotify\.com/album/[\w]+',
]

SPOTIFY_PATTERNS = SPOTIFY_TRACK_PATTERNS + SPOTIFY_PLAYLIST_PATTERNS + SPOTIFY_ALBUM_PATTERNS

def find_music_link(message):
    """Search for YouTube or Spotify link in message"""
    for pattern in YOUTUBE_PATTERNS:
        match = re.search(pattern, message)
        if match:
            return match.group(0)

    for pattern in SPOTIFY_PATTERNS:
        match = re.search(pattern, message)
        if match:
            return match.group(0)

    return None

def is_spotify_link(url):
    for pattern in SPOTIFY_PATTERNS:
        if re.search(pattern, url):
            return True
    return False

def is_spotify_playlist(url):
    for pattern in SPOTIFY_PLAYLIST_PATTERNS:
        if re.search(pattern, url):
            return True
    return False

def is_spotify_album(url):
    for pattern in SPOTIFY_ALBUM_PATTERNS:
        if re.search(pattern, url):
            return True
    return False

# Spotify token cache
spotify_token_cache = {'token': None, 'expires_at': 0}

async def get_spotify_token():
    """Get Spotify API access token"""
    import time

    if spotify_token_cache['token'] and time.time() < spotify_token_cache['expires_at']:
        return spotify_token_cache['token']

    if not SPOTIFY_CLIENT_ID or not SPOTIFY_CLIENT_SECRET:
        print('⚠️ Spotify API credentials not configured')
        return None

    import aiohttp
    import base64

    auth_str = f'{SPOTIFY_CLIENT_ID}:{SPOTIFY_CLIENT_SECRET}'
    auth_bytes = auth_str.encode('ascii')
    auth_base64 = base64.b64encode(auth_bytes).decode('ascii')

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(
                'https://accounts.spotify.com/api/token',
                data={'grant_type': 'client_credentials'},
                headers={'Authorization': f'Basic {auth_base64}'},
                timeout=10
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    token = data.get('access_token')
                    expires_in = data.get('expires_in', 3600)

                    import time
                    spotify_token_cache['token'] = token
                    spotify_token_cache['expires_at'] = time.time() + expires_in - 60

                    print(f'✅ Got Spotify token (valid for {expires_in} seconds)')
                    return token
                else:
                    print(f'❌ Spotify token error: {response.status}')
                    return None
        except Exception as e:
            print(f'❌ Spotify auth error: {e}')
            return None

async def get_spotify_track_info(track_id):
    """Get track info from Spotify API"""
    token = await get_spotify_token()

    if not token:
        return None

    import aiohttp

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(
                f'https://api.spotify.com/v1/tracks/{track_id}',
                headers={'Authorization': f'Bearer {token}'},
                timeout=10
            ) as response:
                if response.status == 200:
                    data = await response.json()

                    name = data.get('name', '')
                    artists = data.get('artists', [])
                    artist_names = [artist.get('name', '') for artist in artists]

                    if name and artist_names:
                        search_query = f"{', '.join(artist_names)} - {name}"
                        print(f'✅ Spotify API: {search_query}')
                        return search_query

                    return name if name else None
                else:
                    print(f'❌ Spotify API returned {response.status}')
                    return None
        except Exception as e:
            print(f'❌ Spotify API error: {e}')
            return None

async def get_spotify_album_tracks(album_id):
    """Get all tracks from Spotify album"""
    token = await get_spotify_token()

    if not token:
        return None

    import aiohttp

    async with aiohttp.ClientSession() as session:
        try:
            url = f'https://api.spotify.com/v1/albums/{album_id}'
            async with session.get(
                url,
                headers={'Authorization': f'Bearer {token}'},
                timeout=15
            ) as response:
                if response.status == 200:
                    data = await response.json()

                    album_name = data.get('name', 'Unknown album')
                    album_artists = data.get('artists', [])
                    album_artist_names = [artist.get('name', '') for artist in album_artists]

                    items = data.get('tracks', {}).get('items', [])
                    all_tracks = []

                    for item in items:
                        name = item.get('name', '')
                        artists = item.get('artists', [])
                        artist_names = [artist.get('name', '') for artist in artists]

                        if not artist_names and album_artist_names:
                            artist_names = album_artist_names

                        if name and artist_names:
                            search_query = f"{', '.join(artist_names)} - {name}"
                            all_tracks.append(search_query)

                    print(f'📝 Got {len(all_tracks)} tracks from album "{album_name}"')
                    return all_tracks if all_tracks else None
                else:
                    error_text = await response.text()
                    print(f'❌ Spotify album API returned {response.status}')
                    print(f'❌ Response: {error_text[:200]}')
                    return None
        except Exception as e:
            print(f'❌ Album fetch error: {e}')
            import traceback
            traceback.print_exc()
            return None

async def get_spotify_playlist_tracks(playlist_id):
    """Get all tracks from Spotify playlist (Note: may not work with Client Credentials flow)"""
    token = await get_spotify_token()

    if not token:
        return None

    import aiohttp

    all_tracks = []
    offset = 0
    limit = 100

    async with aiohttp.ClientSession() as session:
        while True:
            try:
                url = f'https://api.spotify.com/v1/playlists/{playlist_id}/tracks?offset={offset}&limit={limit}'
                async with session.get(
                    url,
                    headers={'Authorization': f'Bearer {token}'},
                    timeout=15
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        items = data.get('items', [])

                        if not items:
                            break

                        for item in items:
                            track = item.get('track')
                            if not track:
                                continue

                            name = track.get('name', '')
                            artists = track.get('artists', [])
                            artist_names = [artist.get('name', '') for artist in artists]

                            if name and artist_names:
                                search_query = f"{', '.join(artist_names)} - {name}"
                                all_tracks.append(search_query)

                        if len(items) < limit:
                            break

                        offset += limit
                    else:
                        error_text = await response.text()
                        print(f'❌ Spotify playlist API returned {response.status}')
                        print(f'❌ Response: {error_text[:200]}')

                        if response.status == 404 and offset == 0:
                            print('🔄 Trying alternative method...')
                            alt_url = f'https://api.spotify.com/v1/playlists/{playlist_id}?fields=tracks.items(track(name,artists(name)))'
                            async with session.get(
                                alt_url,
                                headers={'Authorization': f'Bearer {token}'},
                                timeout=15
                            ) as alt_response:
                                if alt_response.status == 200:
                                    alt_data = await alt_response.json()
                                    items = alt_data.get('tracks', {}).get('items', [])

                                    for item in items:
                                        track = item.get('track')
                                        if not track:
                                            continue

                                        name = track.get('name', '')
                                        artists = track.get('artists', [])
                                        artist_names = [artist.get('name', '') for artist in artists]

                                        if name and artist_names:
                                            search_query = f"{', '.join(artist_names)} - {name}"
                                            all_tracks.append(search_query)

                                    break
                        break
            except Exception as e:
                print(f'❌ Playlist fetch error: {e}')
                import traceback
                traceback.print_exc()
                break

    print(f'📝 Got {len(all_tracks)} tracks from playlist')
    return all_tracks if all_tracks else None

async def convert_spotify_to_youtube(spotify_url):
    """Convert Spotify URL to YouTube search query"""
    try:
        print(f'🔗 Processing Spotify URL: {spotify_url}')

        track_match = re.search(r'track/([a-zA-Z0-9]+)', spotify_url)

        if track_match:
            track_id = track_match.group(1)
            print(f'🆔 Track ID: {track_id}')

            if SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET:
                print('🔑 Using Spotify API')
                track_info = await get_spotify_track_info(track_id)
                if track_info:
                    return track_info

                print('⚠️ Spotify API failed, trying oembed...')

            # Fallback: oembed API
            import aiohttp

            async with aiohttp.ClientSession() as session:
                clean_url = f'https://open.spotify.com/track/{track_id}'
                oembed_url = f'https://open.spotify.com/oembed?url={clean_url}'

                print(f'🌐 Requesting Spotify oembed: {oembed_url}')
                try:
                    async with session.get(oembed_url, timeout=10) as response:
                        if response.status == 200:
                            data = await response.json()
                            title = data.get('title', '')

                            if title:
                                print(f'✅ Spotify (oembed): {title}')
                                return title

                except Exception as e:
                    print(f'❌ Oembed error: {e}')

        print('⚠️ Failed to extract info from Spotify')
        return None

    except Exception as e:
        print(f'⚠️ Spotify conversion error: {e}')
        return None

async def extract_info_async(url, ydl_options):
    """Async wrapper for yt-dlp to prevent blocking"""
    loop = asyncio.get_event_loop()

    def _extract():
        try:
            with yt_dlp.YoutubeDL(ydl_options) as ydl:
                return ydl.extract_info(url, download=False)
        except Exception as e:
            print(f'❌ Error in _extract: {e}')
            raise

    try:
        return await asyncio.wait_for(
            loop.run_in_executor(None, _extract),
            timeout=30.0
        )
    except asyncio.TimeoutError:
        print('⏱️ Timeout getting info from yt-dlp')
        raise Exception('Timeout searching video')

# Music queue for each server
music_queues = {}
now_playing = {}

class MusicQueue:
    def __init__(self):
        self.queue = deque()
        self.loop = False
        self.current = None

    def add(self, song):
        self.queue.append(song)

    def next(self):
        if self.loop and self.current:
            return self.current
        if self.queue:
            self.current = self.queue.popleft()
            return self.current
        return None

    def clear(self):
        self.queue.clear()
        self.current = None

    def is_empty(self):
        return len(self.queue) == 0

def get_queue(guild_id):
    if guild_id not in music_queues:
        music_queues[guild_id] = MusicQueue()
    return music_queues[guild_id]

async def play_next(ctx):
    """Play next song from queue"""
    queue = get_queue(ctx.guild.id)

    if queue.is_empty() and not queue.loop:
        now_playing[ctx.guild.id] = None
        await ctx.send("✅ Queue is empty! Use `!play <song>` to add music", silent=True)
        return

    song = queue.next()
    if not song:
        return

    voice_client = ctx.guild.voice_client

    try:
        # Get fresh stream URL before playback
        if 'url' in song:
            info = await extract_info_async(song['url'], YDL_OPTIONS)
        else:
            info = await extract_info_async(song['search'], YDL_OPTIONS)
            if 'entries' in info:
                info = info['entries'][0]

        stream_url = info.get('url')
        webpage_url = info.get('webpage_url', info.get('original_url', 'N/A'))
        title = info.get('title', 'Unknown song')

        http_headers = info.get('http_headers', {})

        print(f'🔍 Webpage: {webpage_url}')
        print(f'🔍 Stream URL (first 80 chars): {stream_url[:80] if stream_url else "None"}...')

        if not stream_url or not stream_url.startswith('http'):
            await ctx.send('❌ Failed to get direct stream URL!', silent=True)
            print(f'❌ Invalid stream_url: {stream_url}')
            return

        # Verify it's a direct stream (should be from googlevideo CDN)
        if 'googlevideo.com' not in stream_url and 'youtube.com/watch' in stream_url:
            print('⚠️ WARNING: Got webpage URL instead of direct stream!')
            await ctx.send('❌ Error: got webpage URL instead of direct stream', silent=True)
            return

        now_playing[ctx.guild.id] = title

        def after_playing(error):
            if error:
                print(f'❌ Playback error: {error}')
                print(f'Error type: {type(error).__name__}')
            else:
                print(f'✅ Playback finished successfully')
            asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop)

        print(f'🎵 Starting playback: {title}')

        if not voice_client or not voice_client.is_connected():
            await ctx.send('❌ Bot not connected to voice channel!', silent=True)
            return

        ffmpeg_before_options = '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5'

        if http_headers:
            user_agent = http_headers.get('User-Agent', '')
            if user_agent:
                ffmpeg_before_options += f' -user_agent "{user_agent}"'

        ffmpeg_before_options += ' -headers "Referer: https://www.youtube.com/"'

        print(f'🔧 FFmpeg options: {ffmpeg_before_options}')

        source = discord.FFmpegPCMAudio(
            stream_url,
            executable=FFMPEG_PATH,
            before_options=ffmpeg_before_options + ' -analyzeduration 0 -probesize 32',
            options='-vn -f s16le -ar 48000 -ac 2 -bufsize 512k'
        )

        print(f'🎵 Source created, starting playback...')

        voice_client.play(source, after=after_playing)

        print(f'▶️ Playback started')
        await ctx.send(f'🎵 Now playing: **{title}**', silent=True)

    except Exception as e:
        print(f'❌ CRITICAL ERROR: {e}')
        print(f'Type: {type(e).__name__}')
        import traceback
        traceback.print_exc()
        await ctx.send(f'❌ Playback error: {str(e)}', silent=True)
        asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop)

@bot.event
async def on_ready():
    print(f'🎵 {bot.user} online!')
    print(f'Prefix: !')

    try:
        import nacl
        print('✅ PyNaCl installed')
    except ImportError:
        print('❌ WARNING: PyNaCl not installed! Run: pip install PyNaCl')

    print('Ready to play music!')

@bot.event
async def on_message(message):
    """Auto-detect music links in messages"""
    if message.author == bot.user:
        return

    music_link = find_music_link(message.content)

    if music_link:
        print(f'🔗 Found link: {music_link}')
        print(f'👤 From user: {message.author}')

        if message.author.voice:
            ctx = await bot.get_context(message)
            await ctx.invoke(bot.get_command('play'), query=music_link)
        else:
            await message.channel.send('❌ Join a voice channel to play music!', silent=True)

    await bot.process_commands(message)

@bot.command(name='play', aliases=['p'])
async def play(ctx, *, query):
    """Play music from YouTube or Spotify"""

    if not ctx.author.voice:
        await ctx.send('❌ Join a voice channel first!', silent=True)
        return

    voice_channel = ctx.author.voice.channel

    if not ctx.guild.voice_client:
        await voice_channel.connect()
    elif ctx.guild.voice_client.channel != voice_channel:
        await ctx.guild.voice_client.move_to(voice_channel)

    queue = get_queue(ctx.guild.id)

    # Handle Spotify links
    if is_spotify_link(query):
        # Spotify albums
        if is_spotify_album(query):
            await ctx.send(f'💿 Spotify album detected, loading tracks...', silent=True)

            album_match = re.search(r'album/([a-zA-Z0-9]+)', query)
            if not album_match:
                await ctx.send('❌ Failed to extract album ID!', silent=True)
                return

            album_id = album_match.group(1)

            tracks = await get_spotify_album_tracks(album_id)

            if not tracks:
                await ctx.send('❌ Failed to get album tracks!', silent=True)
                return

            await ctx.send(f'✅ Found **{len(tracks)}** tracks. Adding to queue...', silent=True)

            for track in tracks:
                queue.add({'search': f'ytsearch:{track}'})

            await ctx.send(f'✅ Added **{len(tracks)}** tracks to queue!', silent=True)

            if not ctx.guild.voice_client.is_playing():
                await play_next(ctx)

            return

        # Spotify playlists (not supported)
        if is_spotify_playlist(query):
            await ctx.send('⚠️ **Spotify playlists not supported due to API limitations.**\n\n💡 But you can:\n• Use Spotify **albums** (they work!)\n• Add individual **tracks** from Spotify\n• Use YouTube playlists', silent=True)
            return

        # Spotify tracks
        await ctx.send(f'🎧 Spotify link detected, converting to YouTube...', silent=True)
        search_query = await convert_spotify_to_youtube(query)

        if not search_query:
            await ctx.send('❌ Failed to get info from Spotify!', silent=True)
            return

        await ctx.send(f'🔍 Searching on YouTube: **{search_query}**...', silent=True)

        try:
            info = await extract_info_async(f'ytsearch:{search_query}', YDL_OPTIONS)
            if 'entries' in info and len(info['entries']) > 0:
                video = info['entries'][0]
                queue.add({'search': f'ytsearch:{search_query}'})
                await ctx.send(f'✅ Added to queue: **{video.get("title", search_query)}**', silent=True)
            else:
                await ctx.send('❌ Nothing found on YouTube!', silent=True)
                return
        except Exception as e:
            await ctx.send(f'❌ Error: {str(e)}', silent=True)
            return

        if not ctx.guild.voice_client.is_playing():
            await play_next(ctx)

        return

    # Handle YouTube links and search
    await ctx.send(f'🔍 Searching: **{query}**...', silent=True)

    try:
        if query.startswith('http'):
            info = await extract_info_async(query, YDL_OPTIONS)

            # YouTube playlists
            if 'entries' in info:
                await ctx.send(f'📝 Adding playlist: **{info.get("title", "Playlist")}** ({len(info["entries"])} songs)', silent=True)
                for entry in info['entries']:
                    queue.add({'url': entry['url']})
            else:
                queue.add({'url': query})
                await ctx.send(f'✅ Added to queue: **{info.get("title", query)}**', silent=True)
        else:
            # YouTube search
            info = await extract_info_async(f'ytsearch:{query}', YDL_OPTIONS)
            if 'entries' in info and len(info['entries']) > 0:
                video = info['entries'][0]
                queue.add({'search': f'ytsearch:{query}'})
                await ctx.send(f'✅ Added to queue: **{video.get("title", query)}**', silent=True)
            else:
                await ctx.send('❌ Nothing found!', silent=True)
                return

        if not ctx.guild.voice_client.is_playing():
            await play_next(ctx)

    except Exception as e:
        await ctx.send(f'❌ Error: {str(e)}', silent=True)

@bot.command(name='pause')
async def pause(ctx):
    """Pause playback"""
    if ctx.guild.voice_client and ctx.guild.voice_client.is_playing():
        ctx.guild.voice_client.pause()
        await ctx.send('⏸️ Paused', silent=True)
    else:
        await ctx.send('❌ Nothing is playing!', silent=True)

@bot.command(name='resume')
async def resume(ctx):
    """Resume playback"""
    if ctx.guild.voice_client and ctx.guild.voice_client.is_paused():
        ctx.guild.voice_client.resume()
        await ctx.send('▶️ Resumed', silent=True)
    else:
        await ctx.send('❌ Playback not paused!', silent=True)

@bot.command(name='skip', aliases=['s'])
async def skip(ctx):
    """Skip current song"""
    if ctx.guild.voice_client and ctx.guild.voice_client.is_playing():
        ctx.guild.voice_client.stop()
        await ctx.send('⏭️ Skipped!', silent=True)
    else:
        await ctx.send('❌ Nothing is playing!', silent=True)

@bot.command(name='stop')
async def stop(ctx):
    """Stop music and clear queue"""
    queue = get_queue(ctx.guild.id)
    queue.clear()

    if ctx.guild.voice_client:
        ctx.guild.voice_client.stop()
        await ctx.send('⏹️ Stopped and queue cleared!', silent=True)
    else:
        await ctx.send('❌ Bot not connected!', silent=True)

@bot.command(name='leave', aliases=['disconnect', 'dc'])
async def leave(ctx):
    """Disconnect bot from voice channel"""
    if ctx.guild.voice_client:
        await ctx.guild.voice_client.disconnect()
        get_queue(ctx.guild.id).clear()
    else:
        await ctx.send('❌ Bot not connected!', silent=True)

@bot.command(name='queue', aliases=['q'])
async def queue_command(ctx):
    """Show music queue"""
    queue = get_queue(ctx.guild.id)

    if queue.is_empty() and not queue.current:
        await ctx.send('📝 Queue is empty!', silent=True)
        return

    message = '📝 **Music Queue:**\n\n'

    if ctx.guild.id in now_playing and now_playing[ctx.guild.id]:
        message += f'🎵 **Now playing:** {now_playing[ctx.guild.id]}\n\n'

    if not queue.is_empty():
        message += '**Up next:**\n'
        for i, song in enumerate(list(queue.queue)[:10], 1):
            song_name = song.get('url', song.get('search', 'Unknown song'))
            message += f'{i}. {song_name}\n'

        if len(queue.queue) > 10:
            message += f'\n...and {len(queue.queue) - 10} more songs'

    await ctx.send(message, silent=True)

@bot.command(name='loop')
async def loop_command(ctx):
    """Toggle loop for current song"""
    queue = get_queue(ctx.guild.id)
    queue.loop = not queue.loop

    if queue.loop:
        await ctx.send('🔁 Loop enabled!', silent=True)
    else:
        await ctx.send('➡️ Loop disabled!', silent=True)

@bot.command(name='np', aliases=['nowplaying'])
async def now_playing_command(ctx):
    """Show currently playing song"""
    if ctx.guild.id in now_playing and now_playing[ctx.guild.id]:
        await ctx.send(f'🎵 **Now playing:** {now_playing[ctx.guild.id]}', silent=True)
    else:
        await ctx.send('❌ Nothing is playing!', silent=True)

@bot.command(name='help_music', aliases=['commands'])
async def help_music(ctx):
    """Show all commands"""
    help_text = """
🎵 **Music Bot - Commands:**

**Basic:**
`!play <song/URL>` - Play music (YouTube/Spotify)
`!pause` - Pause
`!resume` - Resume
`!skip` - Skip song
`!stop` - Stop and clear queue
`!leave` - Disconnect bot

**Queue:**
`!queue` - Show queue
`!np` - Now playing
`!loop` - Toggle loop for current song

**Support:**
- YouTube links and search
- Spotify tracks (auto-search on YouTube)
- Spotify albums (all tracks added to queue)
- YouTube playlists

**Note:** Spotify playlists not supported due to API limitations
    """
    await ctx.send(help_text, silent=True)

if __name__ == '__main__':
    if TOKEN:
        bot.run(TOKEN)
    else:
        print('❌ ERROR: Token not found! Create .env file')
