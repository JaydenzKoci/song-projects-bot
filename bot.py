import discord
from discord import app_commands
from discord.ext import tasks
import aiohttp
import json
import asyncio
import re
import string
import io
from difflib import get_close_matches
from datetime import datetime, timedelta
import statistics
import os
import random
import uuid
import compare_midi
import subprocess
import mido
import requests
import enum
import hashlib
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)-8s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

BOT_TOKEN = ""
JSON_DATA_URL = "https://raw.githubusercontent.com/JaydenzKoci/jaydenzkoci.github.io/refs/heads/main/data/tracks.json"
ASSET_BASE_URL = "https://jaydenzkoci.github.io"
CONFIG_FILE = "config.json"
TRACK_CACHE_FILE = "tracks_cache.json"
TRACK_HISTORY_FILE = "track_history.json"
SUGGESTIONS_FILE = "suggestions.json"
CHANGELOG_FILE = "changelog.json"
MIDI_CHANGES_FILE = "midichanges.json"

LOCAL_MIDI_FOLDER = "midi_files/"
TEMP_FOLDER = "out/"

KEY_NAME_MAP = {
    "album": "Album",
    "artist": "Artist",
    "ageRating": "Age Rating",
    "bpm": "BPM",
    "charter": "Charter",
    "currentversion": "Chart Version",
    "complete": "Progress",
    "coverArist": "Cover | Artist",
    "createdAt": "Creation Date",
    "download": "Download",
    "doubleBass": "Double Bass",
    "duration": "Duration",
    "featured": "Updated Track",
    "finish": "Finished Track",
    "genre": "Genre",
    "glowTimes": "Modal Loading Phrase Glow Times",
    "id": "Shortname",
    "is_cover": "Is Cover",
    "is_verified": "Is Verified",
    "key": "Key",
    "lastFeatured": "Last Updated",
    "loading_phrase": "Loading Phrase",
    "new": "Playable Track",
    "newYear": "Cover | Release Year",
    "preview_end_time": "Preview End Time",
    "preview_time": "Preview Start Time",
    "previewEndTime": "Audio Preview End Time",
    "previewTime": "Audio Preview Start Time",
    "previewUrl": "Audio Preview",
    "proVoxHarmonies": "Pro Vox Harmonies",
    "rating": "Rating",
    "releaseYear": "Release Year",
    "rotated": "WIP Track",
    "songlink": "Song Link",
    "source": "Source",
    "spotify": "Song Link ID",
    "title": "Title",
    "videoPosition": "Modal Video Position",
    "videoUrl": "Video Modal URL",
    "videoZoom": "Video Modal Zoom",
    "difficulties.vocals": "Vocals Difficulty",
    "difficulties.lead": "Lead Difficulty",
    "difficulties.rhythm": "Rhythm Difficulty",
    "difficulties.bass": "Bass Difficulty",
    "difficulties.drums": "Drums Difficulty",
    "difficulties.keys": "Keys Difficulty",
    "difficulties.pro-vocals": "Pro Vocals Difficulty",
    "difficulties.plastic-guitar": "Pro Lead Difficulty",
    "difficulties.plastic-rhythm": "Pro Rhythm Difficulty",
    "difficulties.plastic-bass": "Pro Bass Difficulty",
    "difficulties.plastic-drums": "Pro Drums Difficulty",
    "difficulties.plastic-keys": "Pro Keys Difficulty",
    "difficulties.real-guitar": "Real Guitar Difficulty",
    "difficulties.real-keys": "Real Keys Difficulty",
    "difficulties.real-bass": "Real Bass Difficulty",
    "difficulties.real-drums": "Real Drums Difficulty",
    "youtubeLinks.vocals": "Vocals Video",
    "youtubeLinks.drums": "Drums Video",
    "youtubeLinks.bass": "Bass Video",
    "youtubeLinks.lead": "Lead Video",
    "modalShadowColors.default.color1": "Modal Color",
    "modalShadowColors.default.color2": "Modal Secondary Color",
    "modalShadowColors.hover.color1": "Modal Hover Color",
    "modalShadowColors.hover.color2": "Modal Hover Secondary Color",
}


intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

if not os.path.exists(LOCAL_MIDI_FOLDER): os.makedirs(LOCAL_MIDI_FOLDER)
if not os.path.exists(TEMP_FOLDER): os.makedirs(TEMP_FOLDER)


def load_json_file(filename: str, default_data: dict | list = None):
    if default_data is None:
        default_data = {}
    if not os.path.exists(filename):
        with open(filename, 'w') as f:
            json.dump(default_data, f, indent=4)
        return default_data
    try:
        with open(filename, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return default_data

def save_json_file(filename: str, data: dict | list):
    with open(filename, 'w') as f:
        json.dump(data, f, indent=4)

config = load_json_file(CONFIG_FILE)

class Instrument:
    def __init__(self, english:str = "Vocals", lb_code:str = "Solo_Vocals", plastic:bool = False, chopt:str = "vocals", midi:str = "PART VOCALS", replace:str = None, lb_enabled:bool = True, path_enabled: bool = True) -> None:
        self.english = english
        self.lb_code = lb_code
        self.plastic = plastic
        self.chopt = chopt
        self.midi = midi
        self.replace = replace
        self.lb_enabled = lb_enabled
        self.path_enabled = path_enabled

class Difficulty:
    def __init__(self, english:str = "Expert", chopt:str = "expert", pitch_ranges = [96, 100], diff_4k:bool = False) -> None:
        self.english = english
        self.chopt = chopt
        self.pitch_ranges = pitch_ranges
        self.diff_4k = diff_4k

class Instruments(enum.Enum):
    ProLead = Instrument(english="Pro Lead", lb_code="Solo_PeripheralGuitar", plastic=True, chopt="proguitar", midi="PLASTIC GUITAR", path_enabled=True)
    ProBass = Instrument(english="Pro Bass", lb_code="Solo_PeripheralBass", plastic=True, chopt="probass", midi="PLASTIC BASS", path_enabled=True)
    ProDrums = Instrument(english="Pro Drums", lb_code="Solo_PeripheralDrum", plastic=True, chopt="drums", midi="PLASTIC DRUMS", replace="PART DRUMS", lb_enabled=False, path_enabled=True)
    ProVocals = Instrument(english="Pro Vocals", lb_code="Solo_PeripheralVocals", plastic=True, chopt="vocals", midi="PRO VOCALS", lb_enabled=False, path_enabled=False)
    Bass = Instrument(english="Bass", lb_code="Solo_Bass", chopt="bass", midi="PART BASS", path_enabled=True)
    Lead = Instrument(english="Lead", lb_code="Solo_Guitar", chopt="guitar", midi="PART GUITAR", path_enabled=True)
    Drums = Instrument(english="Drums", lb_code="Solo_Drums", chopt="drums", midi="PART DRUMS", path_enabled=True)
    Vocals = Instrument(english="Vocals", lb_code="Solo_Vocals", chopt="vocals", midi="PART VOCALS", path_enabled=False)

class Difficulties(enum.Enum):
    Expert = Difficulty()
    Hard = Difficulty(english="Hard", chopt="hard", pitch_ranges=[84, 88], diff_4k=True)
    Medium = Difficulty(english="Medium", chopt="medium", pitch_ranges=[72, 76], diff_4k=True)
    Easy = Difficulty(english="Easy", chopt="easy", pitch_ranges=[60, 64], diff_4k=True)

class MidiArchiveTools:
    def __init__(self) -> None:
        pass
    
    def save_chart(self, chart_url:str, song_id: str) -> str:
        midiname = f"{song_id}.mid"
        local_path = os.path.join(LOCAL_MIDI_FOLDER, midiname)

        if os.path.exists(local_path):
            logging.info(f"Chart for song ID '{song_id}' already exists, using local copy.")
            return local_path
        else:
            logging.info(f"Downloading chart for song ID '{song_id}' from {chart_url}")
            response = requests.get(chart_url)
            response.raise_for_status()

            with open(local_path, 'wb') as f:
                f.write(response.content)
            
            logging.info(f"Successfully saved chart for '{song_id}' to {local_path}")
            return local_path
        
    def modify_midi_file(self, midi_file: str, instrument: Instrument, session_hash: str, shortname: str) -> str:
        mid = mido.MidiFile(midi_file)
        track_names_to_delete = []
        track_names_to_rename = {}

        if instrument.replace:
            track_names_to_delete.append(instrument.replace)
        track_names_to_rename[instrument.midi] = instrument.replace

        new_tracks = []
        for track in mid.tracks:
            if track.name in track_names_to_delete:
                continue
            
            modified_track = mido.MidiTrack()
            for msg in track:
                if msg.type == 'track_name' and msg.name in track_names_to_rename:
                    msg.name = track_names_to_rename[msg.name]
                modified_track.append(msg)
            new_tracks.append(modified_track)

        mid.tracks = new_tracks
        
        modified_midi_file_name = f"{shortname}_{session_hash}.mid"
        modified_midi_file = os.path.join(TEMP_FOLDER, modified_midi_file_name)

        mid.save(modified_midi_file)
        return modified_midi_file

def run_chopt(midi_file: str, command_instrument: str, output_image: str, squeeze_percent: int = 20, instrument: Instrument = None, difficulty: str = 'expert', extra_args: list = []):
    engine = 'fnf'
    if instrument.midi == 'PLASTIC DRUMS':
        engine = 'ch' 

    chopt_command = [
        'chopt.exe', 
        '-f', midi_file, 
        '--engine', engine, 
        '--squeeze', str(squeeze_percent),
        '--early-whammy', '0',
        '--diff', difficulty
    ]

    if instrument.midi != 'PLASTIC DRUMS':
        chopt_command.append('--no-pro-drums')

    chopt_command.extend(['-i', command_instrument, '-o', os.path.join(TEMP_FOLDER, output_image)])
    chopt_command.extend(extra_args)

    result = subprocess.run(chopt_command, text=True, capture_output=True)

    if result.returncode != 0:
        raise Exception(result.stderr)

    return result.stdout.strip()

def process_acts(arr):
    sum_phrases, sum_overlaps = 0, 0
    for string in arr:
        try:
            if "(" in string:
                x, y = string.split("(")
                y = y.replace(")", "")
                sum_phrases += int(x)
                sum_overlaps += int(y)
            else:
                sum_phrases += int(string)
        except Exception:
            pass
    return sum_phrases, sum_overlaps

def generate_session_hash(user_id, song_name):
    hash_int = int(hashlib.md5(f"{user_id}_{song_name}".encode()).hexdigest(), 16)
    return str(hash_int % 10**8).zfill(8)

def delete_session_files(session_hash):
    try:
        for file_name in os.listdir(TEMP_FOLDER):
            if session_hash in file_name:
                file_path = os.path.join(TEMP_FOLDER, file_name)
                os.remove(file_path)
                logging.info(f"Deleted file: {file_path}")
    except Exception as e:
        logging.error(f"Error while cleaning up files for session {session_hash}", exc_info=e)

async def log_error_to_channel(error_message: str):
    logging.error(error_message)
    config = load_json_file(CONFIG_FILE)
    error_channel_id = config.get('error_log_channels', {}).get('default')
    if error_channel_id:
        channel = client.get_channel(int(error_channel_id))
        if channel:
            try:
                embed = discord.Embed(
                    title="Bot Error",
                    description=error_message[:4000],
                    color=discord.Color.red(),
                    timestamp=datetime.now()
                )
                await channel.send(embed=embed)
            except discord.Forbidden:
                logging.error(f"Failed to send error log to channel {error_channel_id}: Missing permissions.")
            except Exception as e:
                logging.error(f"Failed to send error log message: {e}")

async def update_bot_status():
    try:
        tracks = get_cached_track_data()
        track_count = len(tracks)
        activity = discord.Activity(type=discord.ActivityType.playing, name=f"{track_count} Tracks")
        await client.change_presence(activity=activity)
        logging.info(f"Updated bot status: Playing {track_count} Tracks")
    except Exception as e:
        await log_error_to_channel(f"Error updating bot status: {str(e)}")

async def get_live_track_data() -> list | None:
    logging.info("Attempting to fetch live track data from source...")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(JSON_DATA_URL, timeout=10) as response:
                if response.status == 200:
                    data = await response.json(content_type=None)
                    tracks_list = []
                    if isinstance(data, dict):
                        for track_id, track_info in data.items():
                            track_info['id'] = track_id
                            tracks_list.append(track_info)
                    else:
                        await log_error_to_channel(f"Error: JSON data is not in the expected format (dictionary of tracks). Got type: {type(data)}")
                        return None
                    
                    logging.info(f"Successfully fetched {len(tracks_list)} live tracks.")
                    return tracks_list
                else:
                    await log_error_to_channel(f"Failed to fetch live data. Status code: {response.status}")
                    return None
    except (aiohttp.ClientError, json.JSONDecodeError, asyncio.TimeoutError) as e:
        await log_error_to_channel(f"Error during live data fetching or parsing: {str(e)}")
        return None

def get_cached_track_data() -> list:
    try:
        return load_json_file(TRACK_CACHE_FILE, {"tracks": []}).get("tracks", [])
    except Exception as e:
        asyncio.create_task(log_error_to_channel(f"Error reading track cache: {str(e)}"))
        return []

def parse_duration_to_seconds(duration_str: str) -> int:
    try:
        if not isinstance(duration_str, str): return 0
        seconds = 0
        if (minutes_match := re.search(r'(\d+)m', duration_str)):
            seconds += int(minutes_match.group(1)) * 60
        if (seconds_match := re.search(r'(\d+)s', duration_str)):
            seconds += int(seconds_match.group(1))
        return seconds
    except Exception as e:
        asyncio.create_task(log_error_to_channel(f"Error parsing duration: {str(e)}"))
        return 0

def remove_punctuation(text: str) -> str:
    try:
        return text.translate(str.maketrans('', '', string.punctuation))
    except Exception as e:
        asyncio.create_task(log_error_to_channel(f"Error removing punctuation: {str(e)}"))
        return text

def create_difficulty_bar(level: int, max_level: int = 7) -> str:
    try:
        if not isinstance(level, int) or level < 0: return ""
        level = min(level, max_level)
        return f"{'■' * level}{'□' * (max_level - level)}"
    except Exception as e:
        asyncio.create_task(log_error_to_channel(f"Error creating difficulty bar: {str(e)}"))
        return ""

def calculate_average_difficulty(track: dict) -> float:
    try:
        difficulties = track.get('difficulties', {})
        valid_diffs = [d for d in difficulties.values() if isinstance(d, int) and d != -1]
        if not valid_diffs:
            return 0.0
        return statistics.mean(valid_diffs)
    except Exception:
        return 0.0

def fuzzy_search_tracks(tracks: list, query: str, sort_method: str = None) -> list:
    try:
        sort_map = {
            'latest': ('createdAt', True, 25), 'earliest': ('createdAt', False, 25),
            'longest': ('duration', True, 25), 'shortest': ('duration', False, 25),
            'fastest': ('bpm', True, 25), 'slowest': ('bpm', False, 25),
            'newest': ('releaseYear', True, 25), 'oldest': ('releaseYear', False, 25),
            'charter': ('charter', False, 25), 'charter_za': ('charter', True, 25),
            'hardest': ('avg_difficulty', True, 25), 'easiest': ('avg_difficulty', False, 25)
        }
        if sort_method and sort_method.lower() in sort_map:
            key, reverse, limit = sort_map[sort_method.lower()]
            
            if key == 'duration':
                sort_key_func = lambda t: parse_duration_to_seconds(t.get(key, '0s'))
            elif key == 'createdAt':
                sort_key_func = lambda t: datetime.fromisoformat(t.get(key, '1970-01-01T00:00:00Z').replace('Z', '+00:00')).timestamp()
            elif key == 'charter':
                sort_key_func = lambda t: t.get(key, '').lower() 
            elif key == 'avg_difficulty':
                sort_key_func = calculate_average_difficulty
            else: 
                sort_key_func = lambda t: t.get(key, 0) if isinstance(t.get(key, 0), (int, float)) else 0

            sortable_tracks = [t for t in tracks if t.get(key) is not None and t.get(key) != ''] if key != 'avg_difficulty' else tracks
            
            sorted_tracks = sorted(sortable_tracks, key=sort_key_func, reverse=reverse)
            return sorted_tracks[:limit]

        if not query:
            return []

        search_term = remove_punctuation(query.lower())
        
        exact_matches, fuzzy_matches = [], []
        for track in tracks:
            title = remove_punctuation(track.get('title', '').lower())
            artist = remove_punctuation(track.get('artist', '').lower())
            track_id = track.get('id', '').lower()

            if search_term == track_id or search_term in title or search_term in artist:
                exact_matches.append(track)
            elif get_close_matches(search_term, [title, artist], n=1, cutoff=0.7):
                fuzzy_matches.append(track)
        
        filtered_tracks, seen_ids = [], set()
        for track in exact_matches + fuzzy_matches:
            if (track_id := track.get('id')) not in seen_ids:
                filtered_tracks.append(track)
                seen_ids.add(track_id)
        
        return filtered_tracks

    except Exception as e:
        asyncio.create_task(log_error_to_channel(f"Error in fuzzy search/sort: {str(e)}"))
        return []

def format_key(key_str: str) -> str:
    try:
        if not key_str or not isinstance(key_str, str):
            return "N/A"
            
        key_map = {"A♭": "G♯", "B♭": "A♯", "D♭": "C♯", "E♭": "D♯", "G♭": "F♯"}
        for flat, sharp in key_map.items():
            if flat in key_str:
                return f"{sharp} / {key_str}"
        return key_str
    except Exception as e:
        asyncio.create_task(log_error_to_channel(f"Error formatting key: {str(e)}"))
        return "N/A"

def create_track_embed_and_view(track: dict, author_id: int, is_log: bool = False):
    try:
        embed_title = "Track Added" if is_log else None
        
        hex_color = None
        if is_log:
            color = discord.Color.green()
        else:
            hover_color = track.get('modalShadowColors', {}).get('hover', {}).get('color2')
            if hover_color and isinstance(hover_color, str) and hover_color.startswith('#') and hover_color.lower() != '#ffffff':
                hex_color = hover_color
            else:
                hex_color = track.get('modalShadowColors', {}).get('default', {}).get('color1')

            if hex_color and isinstance(hex_color, str) and hex_color.startswith('#'):
                try: color = discord.Color.from_str(hex_color)
                except ValueError: color = discord.Color.from_str("#FFFFFF")
            else:
                color = discord.Color.from_str("#FFFFFF")

        description = f"## {track.get('title', 'N/A')} - {track.get('artist', 'N/A')}"
        
        embed = discord.Embed(title=embed_title, description=description, color=color)
        if track.get('cover'):
            embed.set_thumbnail(url=f"{ASSET_BASE_URL}/assets/covers/{track.get('cover')}")

        avg_difficulty = calculate_average_difficulty(track)
        
        embed.add_field(name="Release Year", value=str(track.get('releaseYear', 'N/A')))
        embed.add_field(name="Album", value=track.get('album', 'N/A'))
        embed.add_field(name="Genre", value=track.get('genre', 'N/A'))
        embed.add_field(name="Duration", value=track.get('duration', 'N/A'))
        embed.add_field(name="BPM", value=str(track.get('bpm', 'N/A')))
        embed.add_field(name="Key", value=format_key(track.get('key', 'N/A')))
        
        progress_value = track.get('complete', '0% Complete').replace(' Complete', '')
        embed.add_field(name="Progress", value=progress_value)
        
        embed.add_field(name="Rating", value=track.get('rating', 'N/A'))
        embed.add_field(name="Avg. Difficulty", value=f"`{create_difficulty_bar(round(avg_difficulty))}`")
        embed.add_field(name="Shortname", value=f"`{track.get('id', 'N/A')}`")
        
        if (loading_phrase := track.get('loading_phrase')):
            embed.add_field(name="Loading Phrase", value=f"\"{loading_phrase}\"", inline=True)
        
        inst_map = {'vocals': 'Vocals', 'guitar': 'Lead', 'bass': 'Bass', 'drums': 'Drums',
                    'plastic-bass': 'Pro Bass', 'plastic-drums': 'Pro Drums',
                    'plastic-guitar': 'Pro Lead', 'plastic-keys': 'Pro Keys'}
        diff_text = "\n".join(
            f"{name:<12}: {create_difficulty_bar(lvl)}"
            for inst, name in inst_map.items()
            if (lvl := track.get('difficulties', {}).get(inst)) is not None and lvl != -1)
        if diff_text:
            embed.add_field(name="Instrument Difficulties", value=f"```\n{diff_text}```", inline=False)

        if (created_at := track.get('createdAt')):
            try:
                ts = int(datetime.fromisoformat(created_at.replace('Z', '+00:00')).timestamp())
                embed.add_field(name="Date Added", value=f"<t:{ts}:F>", inline=True)
            except (ValueError, TypeError): pass
                
        if (last_featured_str := track.get('lastFeatured')) and last_featured_str != "TBA":
            try:
                dt_obj = datetime.strptime(last_featured_str, '%m/%d/%Y, %I:%M:%S %p')
                ts = int(dt_obj.timestamp())
                embed.add_field(name="Last Updated", value=f"<t:{ts}:F>", inline=True)
            except (ValueError, TypeError): pass
        
        if is_log and (chart_url := track.get('charturl')):
            embed.add_field(name="Chart URL", value=chart_url, inline=False)

        return embed, TrackInfoView(track=track, author_id=author_id)
    except Exception as e:
        asyncio.create_task(log_error_to_channel(f"Error creating track embed: {str(e)}"))
        return discord.Embed(title="Error", description="Could not create track embed.", color=discord.Color.red()), None

def create_update_log_embed(old_track: dict, new_track: dict) -> tuple[discord.Embed | None, dict]:
    try:
        embed = discord.Embed(title="Track Modified", description=f"## {new_track.get('title', 'N/A')} - {new_track.get('artist', 'N/A')}",
                              color=discord.Color.orange(), timestamp=datetime.now())
        if new_track.get('cover'):
            embed.set_thumbnail(url=f"{ASSET_BASE_URL}/assets/covers/{new_track.get('cover')}")

        changes_dict = {}

        def flatten(d, parent_key='', sep='.'):
            items = {}
            for k, v in d.items():
                new_key = f"{parent_key}{sep}{k}" if parent_key else k
                if isinstance(v, dict): items.update(flatten(v, new_key))
                else: items[new_key] = v
            return items

        flat_old, flat_new = flatten(old_track), flatten(new_track)
        all_keys = sorted(list(set(flat_old.keys()) | set(flat_new.keys())))
        ignored_keys = ['id', 'rotated']

        change_strings = []
        for key in all_keys:
            if any(key.startswith(ignored) for ignored in ignored_keys): continue
            
            old_val, new_val = flat_old.get(key), flat_new.get(key)
            if old_val != new_val:
                key_title = KEY_NAME_MAP.get(key) or KEY_NAME_MAP.get(key.lower(), key.replace('.', ' ').title())
                changes_dict[key] = {'old': old_val, 'new': new_val}
                change_strings.append(f"**{key_title}**\n```\nOld: {old_val or 'N/A'}\nNew: {new_val or 'N/A'}\n```")
        
        if not change_strings: return None, {}
        
        embed.description += "\n\n" + "\n\n".join(change_strings)
        if len(embed.description) > 4096:
            embed.description = embed.description[:4093] + "..."
            
        return embed, changes_dict
    except Exception as e:
        asyncio.create_task(log_error_to_channel(f"Error creating update log embed: {str(e)}"))
        return None, {}

class TrackInfoView(discord.ui.View):
    def __init__(self, track: dict, author_id: int):
        super().__init__(timeout=300.0)
        self.track = track
        self.author_id = author_id

        if track.get('previewUrl'): self.add_item(self.PreviewAudioButton(track=track))
        if track.get('videoUrl'): self.add_item(self.PreviewVideoButton(track=track))
        
        if spotify_id := track.get('spotify'):
            self.add_item(discord.ui.Button(label="Stream Song", url=f"https://song.link/s/{spotify_id}", row=1, emoji='🎧'))
        if track.get('download'):
            self.add_item(discord.ui.Button(label="Download Chart", url=track.get('download'), row=1, emoji='📥'))

        youtube_links = track.get('youtubeLinks', {})
        inst_video_map = {'vocals': 'Vocals', 'lead': 'Lead', 'drums': 'Drums', 'bass': 'Bass'}
        for part, name in inst_video_map.items():
            link = youtube_links.get(part) or (youtube_links.get('guitar') if part == 'lead' else None)
            if link:
                self.add_item(self.InstrumentVideoButton(part_name=name, link=link))

    async def interaction_check(self, interaction: discord.Interaction) -> bool: return True

    class PreviewAudioButton(discord.ui.Button):
        def __init__(self, track: dict):
            super().__init__(label="Preview Audio", style=discord.ButtonStyle.green, row=0, emoji='🎵')
            self.track = track

        async def callback(self, interaction: discord.Interaction):
            if not (preview_url := self.track.get('previewUrl')):
                await interaction.response.send_message("No audio preview URL found for this track.", ephemeral=True)
                return

            await interaction.response.defer(ephemeral=True, thinking=True)
            try:
                async with aiohttp.ClientSession() as s, s.get(preview_url) as r:
                    if r.status != 200:
                        await interaction.followup.send(f"Could not download audio preview (Status: {r.status}).", ephemeral=True)
                        return
                    
                    audio_data = await r.read()
                    buffer = io.BytesIO(audio_data)
                    
                    await interaction.followup.send(file=discord.File(buffer, "preview.mp3"), ephemeral=True)
            except Exception as e:
                await log_error_to_channel(f"Error fetching audio preview: {str(e)}")
                await interaction.followup.send("An error occurred while fetching the audio preview.", ephemeral=True)

    class PreviewVideoButton(discord.ui.Button):
        def __init__(self, track: dict):
            super().__init__(label="Preview Video", style=discord.ButtonStyle.primary, row=0, emoji='🎥')
            self.track = track
        
        async def callback(self, interaction: discord.Interaction):
            try:
                await interaction.response.send_message(f"Video preview:\n{ASSET_BASE_URL}/assets/preview/{self.track['videoUrl']}", ephemeral=True)
            except Exception as e:
                await log_error_to_channel(f"Error in preview video button: {str(e)}")

    class InstrumentVideoButton(discord.ui.Button):
        def __init__(self, part_name: str, link: str):
            emoji_map = {'Vocals': '🎤', 'Lead': '🎸', 'Drums': '🥁', 'Bass': '🎸'}
            super().__init__(label=f"{part_name} Video", row=2, emoji=emoji_map.get(part_name))
            self.link, self.part_name = link, part_name
        
        async def callback(self, interaction: discord.Interaction):
            try:
                await interaction.response.send_message(f"**{self.part_name} Video:**\n{self.link}", ephemeral=True)
            except Exception as e:
                await log_error_to_channel(f"Error in instrument video button: {str(e)}")

class TrackSelectDropdown(discord.ui.Select):
    def __init__(self, tracks: list, command_type: str, sort: str = None, command_args: dict = None):
        self.tracks_map = {t['id']: t for t in tracks[:25]}
        options, sort_lower = [], sort.lower() if sort else ''
        self.command_args = command_args or {}

        for t in self.tracks_map.values():
            desc = t.get('artist', 'N/A')
            if sort_lower in ['fastest', 'slowest']: desc += f" | BPM: {t.get('bpm', 'N/A')}"
            elif sort_lower in ['newest', 'oldest']: desc += f" | Year: {t.get('releaseYear', 'N/A')}"
            elif sort_lower in ['longest', 'shortest']: desc += f" | Duration: {t.get('duration', 'N/A')}"
            elif sort_lower in ['latest', 'earliest']:
                date_str = "N/A"
                if ca := t.get('createdAt'): date_str = datetime.fromisoformat(ca.replace('Z', '+00:00')).strftime('%Y-%m-%d')
                desc += f" | Added: {date_str}"
            elif sort_lower in ['charter', 'charter_za']: desc += f" | Charter: {t.get('charter', 'N/A')}"
            elif sort_lower in ['hardest', 'easiest']: desc += f" | Avg. Diff: {round(calculate_average_difficulty(t))}/7"
            options.append(discord.SelectOption(label=t['title'], value=t['id'], description=desc))

        placeholder = f"Select from {len(self.tracks_map)} sorted results..." if sort else f"Select from {len(tracks)} results..."
        super().__init__(placeholder=placeholder, options=options)
        self.command_type = command_type

    async def callback(self, interaction: discord.Interaction):
        try:
            track = self.tracks_map.get(self.values[0])
            if not track: return
            
            if self.command_type == 'path':
                await interaction.response.defer()

            self.view.stop()
            if self.command_type == 'info':
                embed, view = create_track_embed_and_view(track, interaction.user.id)
                if embed: await interaction.response.edit_message(content=None, embed=embed, view=view)
            elif self.command_type == 'history':
                view = HistoryPaginatorView(track, author_id=interaction.user.id)
                await interaction.response.edit_message(content=None, embed=view.create_embed(), view=view)
            elif self.command_type == 'path':
                content, embed, attachments, error = await generate_path_response(
                    user_id=interaction.user.id,
                    song_data=track,
                    **self.command_args
                )
                await interaction.edit_original_response(content=content, embed=embed, attachments=attachments or [], view=None)

        except Exception as e:
            await log_error_to_channel(f"Error in track select dropdown: {str(e)}")
            try:
                await interaction.followup.send("An error occurred during selection.", ephemeral=True)
            except discord.errors.InteractionResponded:
                pass

class TrackSelectionView(discord.ui.View):
    def __init__(self, tracks: list, author_id: int, command_type: str, sort: str = None, command_args: dict = None):
        super().__init__(timeout=60.0)
        self.author_id = author_id
        self.add_item(TrackSelectDropdown(tracks, command_type, sort, command_args))
        self.message: discord.InteractionMessage = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("This isn't your session!", ephemeral=True)
            return False
        return True

    async def on_timeout(self):
        try:
            if self.message:
                for item in self.children: item.disabled = True
                await self.message.edit(content="Search timed out.", view=self)
        except Exception as e:
            await log_error_to_channel(f"Error in track selection view timeout: {str(e)}")

class HistoryPaginatorView(discord.ui.View):
    def __init__(self, track: dict, author_id: int):
        super().__init__(timeout=120.0)
        self.track, self.author_id = track, author_id
        self.history = load_json_file(TRACK_HISTORY_FILE, {}).get(track['id'], [])
        self.midi_changes = load_json_file(MIDI_CHANGES_FILE, {})
        self.current_page, self.page_size = 0, 3
        self.total_pages = (len(self.history) + self.page_size - 1) // self.page_size
        self.message: discord.InteractionMessage = None
        self.update_buttons()

    def update_buttons(self):
        self.clear_items()
        self.add_item(self.prev_button)
        self.add_item(self.next_button)
        self.prev_button.disabled = self.current_page == 0
        self.next_button.disabled = self.current_page >= self.total_pages - 1

    def create_embed(self) -> discord.Embed:
        try:
            embed = discord.Embed(title=f"Update History for {self.track['title']}", color=discord.Color.blue())
            if not self.history:
                embed.description = "No update history found for this track."
                return embed
            
            start_index = self.current_page * self.page_size
            page_entries = self.history[start_index : start_index + self.page_size]
            
            desc = ""
            for entry in page_entries:
                ts = int(datetime.fromisoformat(entry['timestamp']).timestamp())
                desc += f"**<t:{ts}:F>**\n"
                for key, values in entry['changes'].items():
                    key_title = KEY_NAME_MAP.get(key) or KEY_NAME_MAP.get(key.lower(), key.replace('.', ' ').title())
                    desc += f"• **{key_title}**: `{values['old'] or 'N/A'}` → `{values['new'] or 'N/A'}`\n"
                
                entry_timestamp = entry['timestamp']
                if entry_timestamp in self.midi_changes:
                    changed_parts = ", ".join([change['instrument'] for change in self.midi_changes[entry_timestamp]])
                    if changed_parts:
                        desc += f"• **Chart Sections Changed**: `{changed_parts}`\n"
                desc += "\n"

            embed.description = desc
            embed.set_footer(text=f"Page {self.current_page + 1}/{self.total_pages}")
            return embed
        except Exception as e:
            asyncio.create_task(log_error_to_channel(f"Error creating history embed: {str(e)}"))
            return discord.Embed(title="Error", description="Failed to create history embed.", color=discord.Color.red())

    async def update_message(self, interaction: discord.Interaction):
        self.update_buttons()
        await interaction.response.edit_message(embed=self.create_embed(), view=self)

    @discord.ui.button(label="◀", style=discord.ButtonStyle.grey)
    async def prev_button(self, i: discord.Interaction, b: discord.ui.Button):
        if self.current_page > 0: self.current_page -= 1; await self.update_message(i)

    @discord.ui.button(label="▶", style=discord.ButtonStyle.grey)
    async def next_button(self, i: discord.Interaction, b: discord.ui.Button):
        if self.current_page < self.total_pages - 1: self.current_page += 1; await self.update_message(i)

@tasks.loop(seconds=10)
async def check_for_updates():
    try:
        config = load_json_file(CONFIG_FILE)
        if not (log_channels := config.get('update_log_channels', {})): return

        logging.info("Checking for track updates...")
        live_tracks = await get_live_track_data()
        if live_tracks is None:
            logging.warning("Update check failed: Could not fetch live data."); return

        cached_tracks = get_cached_track_data()
        
        old_tracks_by_id = {t['id']: t for t in cached_tracks}
        new_tracks_by_id = {t['id']: t for t in live_tracks}
        
        added_ids = new_tracks_by_id.keys() - old_tracks_by_id.keys()
        removed_ids = old_tracks_by_id.keys() - new_tracks_by_id.keys()
        modified_tracks = [{'old': old_tracks_by_id[t_id], 'new': new_tracks_by_id[t_id]} 
                           for t_id in new_tracks_by_id.keys() & old_tracks_by_id.keys() 
                           if old_tracks_by_id[t_id] != new_tracks_by_id[t_id]]

        if not (added_ids or removed_ids or modified_tracks):
            logging.info("No track updates found."); return

        logging.info(f"Changes detected! Added: {len(added_ids)}, Removed: {len(removed_ids)}, Modified: {len(modified_tracks)}. Processing...")
        history_data = load_json_file(TRACK_HISTORY_FILE, {})
        midi_changes_data = load_json_file(MIDI_CHANGES_FILE, {})
        
        for cid in log_channels.values():
            if not (channel := client.get_channel(int(cid))): continue
            
            for tid in added_ids:
                embed, _ = create_track_embed_and_view(new_tracks_by_id[tid], client.user.id, is_log=True)
                if embed: await channel.send(embed=embed)

            if removed_ids:
                embed = discord.Embed(title="Tracks Removed", color=discord.Color.red(), 
                                      description="\n".join(f"• **{old_tracks_by_id[tid]['title']}**" for tid in removed_ids))
                await channel.send(embed=embed)
            
            for mod_info in modified_tracks:
                current_update_timestamp = datetime.now().isoformat()
                embed, changes = create_update_log_embed(mod_info['old'], mod_info['new'])
                if embed:
                    logging.info(f"Logging modification for track: {mod_info['new']['id']}")
                    await channel.send(embed=embed)
                    history_data.setdefault(mod_info['new']['id'], []).insert(0, {'timestamp': current_update_timestamp, 'changes': changes})

                old_url = mod_info['old'].get('charturl')
                new_url = mod_info['new'].get('charturl')
                if old_url and new_url and old_url != new_url:
                    logging.info(f"Chart URL changed for {mod_info['new']['id']}. Comparing MIDI files.")
                    session_id = str(uuid.uuid4())
                    temp_dir = 'temp_midi'
                    os.makedirs(temp_dir, exist_ok=True)
                    old_path = os.path.join(temp_dir, f'old_{session_id}.mid')
                    new_path = os.path.join(temp_dir, f'new_{session_id}.mid')
                    
                    try:
                        async with aiohttp.ClientSession() as session:
                            async with session.get(old_url) as r1, session.get(new_url) as r2:
                                if r1.status == 200 and r2.status == 200:
                                    with open(old_path, 'wb') as f1, open(new_path, 'wb') as f2:
                                        f1.write(await r1.read())
                                        f2.write(await r2.read())
                                    
                                    format = mod_info['new'].get('format', 'json')
                                    comparison_results = compare_midi.run_comparison(
                                        old_path, new_path, session_id, 
                                        output_folder=temp_dir, 
                                        format=format
                                    )
                                    midi_change_log_entry = []
                                    for comp_track_name, image_path in comparison_results:
                                        
                                        previous_chart_change_ts = mod_info['new'].get('createdAt')
                                        if mod_info['new']['id'] in history_data:
                                            for past_change in history_data[mod_info['new']['id']][1:]: # Skip the current change
                                                if 'charturl' in past_change['changes']:
                                                    previous_chart_change_ts = past_change['timestamp']
                                                    break
                                        
                                        try:
                                            old_dt = datetime.fromisoformat(previous_chart_change_ts.replace('Z', '+00:00'))
                                            old_ts_str = f"<t:{int(old_dt.timestamp())}:D>"
                                        except:
                                            old_ts_str = "an earlier version"

                                        new_ts_str = f"<t:{int(datetime.now().timestamp())}:D>"

                                        vis_embed = discord.Embed(
                                            title=f"Chart Changes for {mod_info['new']['title']}",
                                            description=f"Instrument: **{comp_track_name}**\n\nDetected changes between:\n{old_ts_str} and {new_ts_str}",
                                            color=discord.Color.orange(),
                                        )
                                        if cover := mod_info['new'].get('cover'):
                                            vis_embed.set_thumbnail(url=f"{ASSET_BASE_URL}/assets/covers/{cover}")
                                        
                                        image_filename = os.path.basename(image_path)
                                        file = discord.File(image_path, filename=image_filename)
                                        vis_embed.set_image(url=f"attachment://{image_filename}")
                                        
                                        await channel.send(embed=vis_embed, file=file)
                                        
                                        midi_change_log_entry.append({"instrument": comp_track_name, "image_file": image_filename})
                                    
                                    if midi_change_log_entry:
                                        midi_changes_data[current_update_timestamp] = midi_change_log_entry
                    except Exception as e:
                        await log_error_to_channel(f"MIDI comparison failed for {mod_info['new']['id']}: {e}")
                    finally:
                        if os.path.exists(old_path): os.remove(old_path)
                        if os.path.exists(new_path): os.remove(new_path)

        save_json_file(TRACK_HISTORY_FILE, history_data)
        save_json_file(MIDI_CHANGES_FILE, midi_changes_data)
        save_json_file(TRACK_CACHE_FILE, {"tracks": live_tracks})
        await update_bot_status()
    except Exception as e:
        await log_error_to_channel(f"Error in check_for_updates task: {str(e)}")

@client.event
async def on_ready():
    try:
        logging.info("Starting on_ready event...")
        live_tracks = await get_live_track_data()
        logging.info(f"Live tracks fetched: {len(live_tracks or [])}")
        if live_tracks is not None:
            save_json_file(TRACK_CACHE_FILE, {"tracks": live_tracks})
        
        logging.info(f"Bot logged in as {client.user} (ID: {client.user.id})")
        logging.info(f"Found {len(client.guilds)} guilds: {[guild.name + ' (' + str(guild.id) + ')' for guild in client.guilds]}")
        
        logging.info("Attempting to sync commands globally...")
        try:
            await tree.sync()
            logging.info("Global command sync successful.")
        except Exception as e:
            await log_error_to_channel(f"Global command sync failed: {str(e)}")

        await update_bot_status()
        check_for_updates.start()
        logging.info("Bot is ready.")
    except Exception as e:
        await log_error_to_channel(f"Error in on_ready event: {str(e)}")
        raise

# --- AUTOCOMPLETE ---
async def track_autocomplete(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    try:
        choices = []
        for track in get_cached_track_data():
            if current.lower() in track.get('title', '').lower():
                if track['title'] not in [c.name for c in choices]:
                    choices.append(app_commands.Choice(name=track['title'], value=track['title']))
        return choices[:25]
    except Exception as e:
        await log_error_to_channel(f"Error in track_autocomplete: {str(e)}")
        return []

async def generate_path_response(user_id: int, song_data: dict, instrument: Instruments, difficulty: Difficulties, squeeze_percent: int, lefty_flip: bool, activation_opacity: int, no_bpms: bool, no_solos: bool, no_time_signatures: bool) -> tuple:
    """
    Generates the path image and response data.
    Returns a tuple of: (content, embed, attachments, error_string)
    """
    chosen_instrument = instrument.value
    chosen_diff = difficulty.value
    midi_tool = MidiArchiveTools()

    if not chosen_instrument.path_enabled:
        error_msg = f"Paths are not supported for {chosen_instrument.english}."
        return (error_msg, None, None, error_msg)

    extra_arguments = []
    field_argument_descriptors = []
    if lefty_flip:
        extra_arguments.append('--lefty-flip')
        field_argument_descriptors.append('**Lefty Flip:** Yes')
    if activation_opacity is not None:
        extra_arguments.extend(['--act-opacity', str(activation_opacity / 100)])
        field_argument_descriptors.append(f'**Activation Opacity:** {activation_opacity}%')
    if no_bpms:
        extra_arguments.append('--no-bpms')
        field_argument_descriptors.append('**No BPMs:** Yes')
    if no_solos:
        extra_arguments.append('--no-solos')
        field_argument_descriptors.append('**No Solos:** Yes')
    if no_time_signatures:
        extra_arguments.append('--no-time-sigs')
        field_argument_descriptors.append('**No Time Signatures:** Yes')

    session_hash = generate_session_hash(user_id, song_data['id'])

    try:
        chart_url = song_data.get('charturl')
        if not chart_url:
            error_msg = "This track does not have a chart URL."
            return (error_msg, None, None, error_msg)

        midi_file = midi_tool.save_chart(chart_url, song_data['id'])

        if chosen_instrument.replace:
            modified_midi_file = midi_tool.modify_midi_file(midi_file, chosen_instrument, session_hash, song_data['id'])
            if not modified_midi_file:
                error_msg = f"Failed to modify MIDI for '{instrument.name}'."
                return (error_msg, None, None, error_msg)
            midi_file = modified_midi_file

        output_image = f"{song_data['id']}_{chosen_instrument.chopt.lower()}_path_{session_hash}.png"
        chopt_output = run_chopt(midi_file, chosen_instrument.chopt, output_image, squeeze_percent, instrument=chosen_instrument, difficulty=chosen_diff.chopt, extra_args=extra_arguments)

        filtered_output = '\n'.join([line for line in chopt_output.splitlines() if "Optimising, please wait..." not in line])

        description = (
            f"**Instrument:** {chosen_instrument.english}\n"
            f"**Difficulty:** {chosen_diff.english}\n"
            f"**Squeeze:** {squeeze_percent}%\n"
        )
        description += '\n'.join(field_argument_descriptors)

        output_path = os.path.join(TEMP_FOLDER, output_image)
        if os.path.exists(output_path):
            file = discord.File(output_path, filename=output_image)
            embed = discord.Embed(
                title=f"Overdrive Path for **{song_data['title']}** - *{song_data['artist']}*",
                description=description,
                color=discord.Color.purple()
            )
            embed.add_field(name="Overdrive Path", value=f"```\n{filtered_output}\n```", inline=False)

            acts = filtered_output.split('\n')[0].replace('Path: ', '').split('-')
            total_acts = len(acts)
            phrases, overlaps = process_acts(acts)

            no_sp_score = filtered_output.split('\n')[1].split(' ').pop()
            total_score = filtered_output.split('\n')[2].split(' ').pop()

            embed.add_field(name="Phrases", value=phrases)
            embed.add_field(name="Activations", value=total_acts)
            embed.add_field(name="Overlaps", value=overlaps)
            embed.add_field(name="No OD Score", value=no_sp_score)
            embed.add_field(name="Total Score", value=total_score)
            embed.set_footer(text="Encore Bot")

            embed.set_image(url=f"attachment://{output_image}")
            if cover_url := song_data.get('cover'):
                embed.set_thumbnail(url=f"{ASSET_BASE_URL}/assets/covers/{cover_url}")

            return (None, embed, [file], None)
        else:
            error_msg = f"Failed to generate the path image for '{song_data['title']}'."
            return (error_msg, None, None, error_msg)

    except FileNotFoundError:
        error_msg = "Error: `chopt.exe` not found. Please ensure the executable is in the bot's root directory or in your system's PATH."
        await log_error_to_channel(error_msg)
        return (error_msg, None, None, error_msg)
    except Exception as e:
        error_msg = f"An error occurred: {e}"
        await log_error_to_channel(f"Error in path command: {e}")
        return (error_msg, None, None, error_msg)
    finally:
        delete_session_files(session_hash)

@tree.command(name="trackinfo", description="Get detailed information about a specific track.")
@app_commands.autocomplete(track_name=track_autocomplete)
@app_commands.describe(track_name="Search by title, artist, or ID.")
async def trackinfo(interaction: discord.Interaction, track_name: str):
    try:
        await interaction.response.defer()
        matched_tracks = fuzzy_search_tracks(get_cached_track_data(), track_name)
        
        if not matched_tracks:
            await interaction.followup.send(f"Sorry, no tracks were found matching your query: '{track_name}'")
            return
        
        if len(matched_tracks) == 1:
            embed, view = create_track_embed_and_view(matched_tracks[0], interaction.user.id)
            if embed: await interaction.followup.send(embed=embed, view=view)
        else:
            view = TrackSelectionView(matched_tracks, interaction.user.id, 'info')
            view.message = await interaction.followup.send(f"Found {len(matched_tracks)} results. Please select one:", view=view, ephemeral=True)
    except Exception as e:
        await log_error_to_channel(f"Error in trackinfo command: {str(e)}")
        await interaction.followup.send("An error occurred while processing your request.", ephemeral=True)

@tree.command(name="tracksort", description="Sorts all tracks by a specific criterion.")
@app_commands.describe(sort_by="The criterion to sort tracks by.")
@app_commands.choices(sort_by=[
    app_commands.Choice(name="Charter (A-Z)", value="charter"), app_commands.Choice(name="Charter (Z-A)", value="charter_za"),
    app_commands.Choice(name="Hardest (Avg. Difficulty)", value="hardest"), app_commands.Choice(name="Easiest (Avg. Difficulty)", value="easiest"),
    app_commands.Choice(name="Fastest (Highest BPM)", value="fastest"), app_commands.Choice(name="Slowest (Lowest BPM)", value="slowest"),
    app_commands.Choice(name="Newest (Recent Release Year)", value="newest"), app_commands.Choice(name="Oldest (Oldest Release Year)", value="oldest"),
    app_commands.Choice(name="Shortest (Shortest Length)", value="shortest"), app_commands.Choice(name="Longest (Longest Length)", value="longest"),
    app_commands.Choice(name="Latest (Recent Creation Date)", value="latest"), app_commands.Choice(name="Earliest (Oldest Creation Date)", value="earliest")])
async def tracksort(interaction: discord.Interaction, sort_by: str):
    try:
        await interaction.response.defer()
        sorted_tracks = fuzzy_search_tracks(get_cached_track_data(), query="", sort_method=sort_by)
        
        if not sorted_tracks:
            await interaction.followup.send("Could not find any tracks to sort.", ephemeral=True)
            return
        
        view = TrackSelectionView(sorted_tracks, interaction.user.id, 'info', sort=sort_by)
        view.message = await interaction.followup.send(f"Showing top results for tracks sorted by **{sort_by.replace('_', '-').title()}**:", view=view)
    except Exception as e:
        await log_error_to_channel(f"Error in tracksort command: {str(e)}")
        await interaction.followup.send("An error occurred while processing your request.", ephemeral=True)

@tree.command(name="trackhistory", description="Check the update history of a specific track.")
@app_commands.autocomplete(track_name=track_autocomplete)
@app_commands.describe(track_name="The name of the track to check the history for.")
async def trackhistory(interaction: discord.Interaction, track_name: str):
    try:
        await interaction.response.defer()
        matched_tracks = fuzzy_search_tracks(get_cached_track_data(), track_name)

        if not matched_tracks:
            await interaction.followup.send(f"Sorry, no tracks were found matching your query: '{track_name}'.")
            return

        if len(matched_tracks) == 1:
            track = matched_tracks[0]
            view = HistoryPaginatorView(track, author_id=interaction.user.id)
            view.message = await interaction.followup.send(embed=view.create_embed(), view=view)
        else:
            view = TrackSelectionView(matched_tracks, interaction.user.id, 'history')
            view.message = await interaction.followup.send(f"Found {len(matched_tracks)} results. Please select one:", view=view)
    except Exception as e:
        await log_error_to_channel(f"Error in trackhistory command: {str(e)}")
        await interaction.followup.send("An error occurred while processing your request.", ephemeral=True)


@tree.command(name="path", description="Generates a path image for a song's chart.")
@app_commands.autocomplete(song_name=track_autocomplete)
@app_commands.describe(
    song_name="The name of the song.",
    instrument="The instrument to generate the path for.",
    difficulty="The difficulty of the chart.",
    squeeze_percent="The percentage to squeeze the chart image horizontally.",
    lefty_flip="Flip the chart for left-handed players.",
    activation_opacity="Set the opacity of activation lanes (0-100).",
    no_bpms="Hide BPM markers on the chart.",
    no_solos="Hide solo markers on the chart.",
    no_time_signatures="Hide time signature markers on the chart."
)
async def path(interaction: discord.Interaction, 
             song_name: str, 
             instrument: Instruments, 
             difficulty: Difficulties = Difficulties.Expert,
             squeeze_percent: app_commands.Range[int, 0, 100] = 20,
             lefty_flip: bool = False,
             activation_opacity: app_commands.Range[int, 0, 100] = None,
             no_bpms: bool = False,
             no_solos: bool = False,
             no_time_signatures: bool = False):
    await interaction.response.defer()

    matched_tracks = fuzzy_search_tracks(get_cached_track_data(), song_name)
    if not matched_tracks:
        await interaction.followup.send(f"Sorry, no tracks were found matching your query: '{song_name}'")
        return

    command_args = {
        "instrument": instrument, "difficulty": difficulty, "squeeze_percent": squeeze_percent,
        "lefty_flip": lefty_flip, "activation_opacity": activation_opacity, "no_bpms": no_bpms,
        "no_solos": no_solos, "no_time_signatures": no_time_signatures
    }

    if len(matched_tracks) == 1:
        content, embed, attachments, error = await generate_path_response(
            user_id=interaction.user.id,
            song_data=matched_tracks[0],
            **command_args
        )
        await interaction.followup.send(content=content, embed=embed, files=attachments or [])
    else:
        view = TrackSelectionView(matched_tracks, interaction.user.id, 'path', command_args=command_args)
        view.message = await interaction.followup.send(f"Found {len(matched_tracks)} results. Please select one:", view=view)


class SuggestionModal(discord.ui.Modal, title="Suggest a Feature"):
    suggestion_input = discord.ui.TextInput(label="Your Suggestion", style=discord.TextStyle.long, 
                                            placeholder="Type your feature suggestion here...", required=True, max_length=1000)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            user_id = str(interaction.user.id)
            suggestion_data = load_json_file(SUGGESTIONS_FILE, default_data={"user_timestamps": {}, "suggestions": []})
            
            now, one_hour_ago = datetime.now(), datetime.now() - timedelta(hours=1)
            
            user_timestamps = suggestion_data["user_timestamps"].get(user_id, [])
            recent_timestamps = [ts for ts in user_timestamps if datetime.fromisoformat(ts) > one_hour_ago]
            
            if len(recent_timestamps) >= 2:
                await interaction.response.send_message("You have made 2 suggestions in the last hour. Please try again later.", ephemeral=True)
                return

            suggestion_data["suggestions"].append({"username": str(interaction.user), "user_id": user_id, 
                                                   "suggestion": self.suggestion_input.value, "timestamp": now.isoformat()})
            recent_timestamps.append(now.isoformat())
            suggestion_data["user_timestamps"][user_id] = recent_timestamps
            
            save_json_file(SUGGESTIONS_FILE, suggestion_data)
            await interaction.response.send_message("✅ Thank you! Your suggestion has been submitted.", ephemeral=True)

        except Exception as e:
            await log_error_to_channel(f"Error processing suggestion: {e}")
            await interaction.response.send_message("An error occurred while submitting your suggestion.", ephemeral=True)

class BotInfoView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(discord.ui.Button(label="Report a Bug", style=discord.ButtonStyle.link, url="https://github.com/JaydenzKoci/EncoreDiscordBot/issues/new"))
        self.add_item(discord.ui.Button(label="Encore Discord", style=discord.ButtonStyle.link, url="https://discord.gg/FmF8DpZVrx"))

    @discord.ui.button(label="Suggest a Feature", style=discord.ButtonStyle.green)
    async def suggest_button(self, i: discord.Interaction, b: discord.ui.Button): await i.response.send_modal(SuggestionModal())

    @discord.ui.button(label="Changelog", style=discord.ButtonStyle.secondary)
    async def changelog_button(self, i: discord.Interaction, b: discord.ui.Button):
        try:
            await i.response.defer(ephemeral=True)
            changelog = load_json_file(CHANGELOG_FILE)
            if not changelog:
                await i.followup.send("Could not load the changelog file.", ephemeral=True); return

            embed = discord.Embed(title=f"Changelog - Version {changelog.get('version', 'N/A')}", 
                                  description="\n".join(f"• {c}" for c in changelog.get('changes', ["No changes."])),
                                  color=discord.Color.blurple())
            await i.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            await log_error_to_channel(f"Error in changelog button: {str(e)}")
            await i.followup.send("An error occurred fetching the changelog.", ephemeral=True)

@tree.command(name="bot-info", description="Get information about the bot.")
async def bot_info(interaction: discord.Interaction):
    try:
        await interaction.response.defer()
        version = load_json_file(CHANGELOG_FILE, {}).get("version", "N/A")
        
        tracks = get_cached_track_data()
        playable = sum(1 for t in tracks if t.get('new'))
        wip = sum(1 for t in tracks if t.get('rotated'))
        finished = sum(1 for t in tracks if t.get('finish'))

        history = load_json_file(TRACK_HISTORY_FILE, {})
        updates = sum(len(v) for v in history.values())
        latest_update_ts = max((datetime.fromisoformat(u['timestamp']) for v in history.values() for u in v), default=None)

        embed = discord.Embed(title="Bot Information", description="Jaydenz Customs For Encore", color=discord.Color.purple())
        
        embed.add_field(name="📊 Track Statistics", value=(
            f"**Playable Tracks:** {playable}\n"
            f"**WIP Tracks:** {wip}\n"
            f"**Finished Tracks:** {finished}\n"
            f"**Total Tracks:** {len(tracks)}"
        ), inline=True)

        embed.add_field(name="🔄 Track Update History", value=(
            f"**Total Updates:** {updates}\n"
            f"**Last Update:** {f'<t:{int(latest_update_ts.timestamp())}:R>' if latest_update_ts else 'N/A'}"
        ), inline=True)
        
        embed.set_footer(text=f"Version {version}")
        
        await interaction.followup.send(embed=embed, view=BotInfoView())
    except Exception as e:
        await log_error_to_channel(f"Error in bot-info command: {str(e)}")
        await interaction.followup.send("An error occurred while fetching bot info.", ephemeral=True)

@tree.command(name="setlogchannel", description="Sets this channel for track update notifications.")
@app_commands.default_permissions(administrator=True)
async def setlogchannel(interaction: discord.Interaction):
    if not interaction.guild:
        await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
        return
    config = load_json_file(CONFIG_FILE, {"update_log_channels": {}})
    config.setdefault('update_log_channels', {})[str(interaction.guild.id)] = interaction.channel.id
    save_json_file(CONFIG_FILE, config)
    await interaction.response.send_message(f"✅ Update log channel set to {interaction.channel.mention}.", ephemeral=True)

@tree.command(name="testchartvisualization", description="Tests the MIDI chart visualization.")
@app_commands.default_permissions(administrator=True)
@app_commands.autocomplete(track_name=track_autocomplete)
@app_commands.describe(
    track_name="The name of the track to fetch cover art from.",
    old_midi_url="URL of the old MIDI file.",
    new_midi_url="URL of the new MIDI file.",
    format="The format of the chart to determine which tracks to scan."
)
@app_commands.choices(format=[
    app_commands.Choice(name="JSON (Default)", value="json"),
    app_commands.Choice(name="INI", value="ini")
])
async def testchartvisualization(interaction: discord.Interaction, track_name: str, old_midi_url: str, new_midi_url: str, format: app_commands.Choice[str] = None):
    await interaction.response.defer()
    
    matched_tracks = fuzzy_search_tracks(get_cached_track_data(), track_name)
    if not matched_tracks:
        await interaction.followup.send(f"Could not find a track matching '{track_name}' to get cover art from.")
        return
    track_info = matched_tracks[0]

    session_id = str(uuid.uuid4())
    temp_dir = 'temp_midi'
    os.makedirs(temp_dir, exist_ok=True)
    old_path = os.path.join(temp_dir, f'old_{session_id}.mid')
    new_path = os.path.join(temp_dir, f'new_{session_id}.mid')
    image_paths_to_clean = []

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(old_midi_url) as r1, session.get(new_midi_url) as r2:
                if r1.status != 200:
                    await interaction.followup.send(f"Error downloading old MIDI file: Status {r1.status}")
                    return
                if r2.status != 200:
                    await interaction.followup.send(f"Error downloading new MIDI file: Status {r2.status}")
                    return

                with open(old_path, 'wb') as f1, open(new_path, 'wb') as f2:
                    f1.write(await r1.read())
                    f2.write(await r2.read())
                
                test_format = format.value if format else 'json'
                comparison_results = compare_midi.run_comparison(
                    old_path, new_path, session_id, 
                    output_folder=temp_dir, 
                    format=test_format
                )

                if comparison_results:
                    await interaction.followup.send(f"MIDI comparison results (Format: **{test_format.upper()}**):")
                    for comp_track_name, image_path in comparison_results:
                        image_paths_to_clean.append(image_path)
                        
                        now_ts = f"<t:{int(datetime.now().timestamp())}:D>"
                        
                        vis_embed = discord.Embed(
                            title=f"Test Chart Changes for {track_info['title']}",
                            description=f"Instrument: **{comp_track_name}**\n\nDetected changes between:\nAn older version and the version from {now_ts}",
                            color=discord.Color.orange(),
                        )
                        if cover := track_info.get('cover'):
                            vis_embed.set_thumbnail(url=f"{ASSET_BASE_URL}/assets/covers/{cover}")
                        
                        image_filename = os.path.basename(image_path)
                        file = discord.File(image_path, filename=image_filename)
                        vis_embed.set_image(url=f"attachment://{image_filename}")
                        
                        await interaction.channel.send(embed=vis_embed, file=file)
                else:
                    await interaction.followup.send("No significant changes found between the MIDI files.")
    except Exception as e:
        await log_error_to_channel(f"Error during MIDI test command: {e}")
        await interaction.followup.send(f"An error occurred: {e}")
    finally:
        if os.path.exists(old_path): os.remove(old_path)
        if os.path.exists(new_path): os.remove(new_path)
        for p in image_paths_to_clean:
            if os.path.exists(p): os.remove(p)

if __name__ == "__main__":
    try:
        client.run(BOT_TOKEN)
    except discord.errors.LoginFailure:
        msg = "Login failed. Check your bot token and intents."
        logging.critical(msg)
        asyncio.run(log_error_to_channel(msg))
    except Exception as e:
        msg = f"An critical error occurred while running the bot: {e}"
        logging.critical(msg)
        asyncio.run(log_error_to_channel(msg))