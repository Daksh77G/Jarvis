import os
import re
import skills.app_launcher as al
from groq import Groq
from skills.app_launcher import open_app, open_website, close_app, launch_steam_game, search_youtube
from skills.spotify_control import play_song, play_playlist, get_current_song
from skills.system_controls import (volume_up, volume_down, mute, set_volume,
    media_play_pause, media_next, media_previous,
    shutdown, cancel_shutdown, restart, sleep_pc, get_battery, take_screenshot)

ASSISTANT_NAME = "Jarvis"
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
conversation_history = []

APP_PRIORITY = ["spotify", "discord", "steam", "roblox", "minecraft",
                "riot client", "valorant", "vscode", "chrome", "firefox"]

def speak(text):
    print(f"\n{ASSISTANT_NAME}: {text}\n")

def extract_number(text):
    match = re.search(r'\b(\d+)\b', text)
    return int(match.group(1)) if match else None

def handle_command(text: str):
    t = text.lower().strip()

    # --- Volume ---
    if re.search(r'volume (up|increase|raise|higher)|louder|turn it up', t):
        return volume_up()
    if re.search(r'volume (down|decrease|lower)|quieter|turn it down', t):
        return volume_down()
    if re.search(r'(set|turn).*(volume|sound).*(\d+)|volume.*(\d+)', t):
        n = extract_number(t)
        return set_volume(n) if n else volume_down()
    if any(x in t for x in ["max volume", "volume max", "full volume"]):
        return set_volume(100)
    if any(x in t for x in ["min volume", "volume min", "no volume"]):
        return set_volume(0)
    if "mute" in t:
        return mute()

    # --- Media controls ---
    if any(x in t for x in ["pause music", "pause song", "pause media",
                              "resume music", "resume song", "resume media",
                              "play music", "start music", "unpause"]):
        return media_play_pause()
    if any(x in t for x in ["next song", "next track", "skip song", "skip track"]):
        return media_next()
    if any(x in t for x in ["previous song", "last song", "go back track"]):
        return media_previous()

    # --- What's playing ---
    if any(x in t for x in ["what song", "what's playing", "whats playing",
                              "current song", "what is this song"]):
        return get_current_song()

    # --- Screenshot ---
    if "screenshot" in t or "screen capture" in t:
        return take_screenshot()

    # --- Battery ---
    if "battery" in t:
        return get_battery()

    # --- System ---
    if re.search(r'shut\s*down|turn off (the )?(pc|computer|laptop)', t):
        n = extract_number(t)
        return shutdown(n if n else 10)
    if any(x in t for x in ["cancel shutdown", "abort shutdown"]):
        return cancel_shutdown()
    if "restart" in t or "reboot" in t:
        return restart()
    if "sleep" in t and any(x in t for x in ["pc", "computer", "laptop", "put"]):
        return sleep_pc()

    # --- List / Refresh Steam Games ---
    if any(x in t for x in ["list games", "list steam", "what games", "which games", "my games"]):
        games = al.STEAM_GAMES
        if games:
            names = ", ".join(sorted(games.keys()))
            return f"I found these games: {names}."
        return "I couldn't find any Steam games."
    if any(x in t for x in ["refresh games", "rescan games", "update games", "scan games"]):
        al.STEAM_GAMES = al.refresh_games()
        return f"Done! Found {len(al.STEAM_GAMES)} games."

    # --- Close App ---
    if re.search(r'\b(close|quit|kill)\b', t) and not t.startswith("exit"):
        app = re.sub(r'\b(close|quit|kill)\b', '', t).strip()
        if app:
            return close_app(app)

    # --- Subreddit shortcut ---
    subreddit_match = re.search(r'r/(\w+)', t)
    if subreddit_match:
        return open_website(f"reddit.com/r/{subreddit_match.group(1)}")

    # --- Spotify: explicit playlist keyword ---
    playlist_match = re.search(r'(?:play|start|put on) (.+?) playlist', t)
    if playlist_match:
        return play_playlist(playlist_match.group(1).strip())

    # --- Spotify: "play X on/in spotify" ---
    spotify_explicit = re.search(
        r'(?:play|listen to|put on|search) (.+?) (?:on spotify|in spotify)', t)
    if spotify_explicit:
        query = spotify_explicit.group(1).strip()
        if re.search(r'\bby\b', query):
            return play_song(query)
        return play_playlist(query)

    # --- Spotify: "play X by Y" → specific song ---
    spotify_by = re.search(r'play (.+?) by (.+)', t)
    if spotify_by and not any(x in t for x in ["game", "steam", "launch", "video", "youtube"]):
        song = spotify_by.group(1).strip()
        artist = spotify_by.group(2).strip()
        return play_song(f"{song} {artist}")

    # --- Spotify: "play X" with no "by" and no game/video context → playlist/genre ---
    spotify_generic = re.search(r'^(?:play|put on|listen to) (.+?)$', t)
    if spotify_generic and not any(x in t for x in ["game", "steam", "launch",
                                                      "video", "youtube",
                                                      "song", "track", "media"]):
        query = spotify_generic.group(1).strip()
        # Skip if it looks like a Steam game launch
        result = launch_steam_game(query)
        if result and "Couldn't find" not in result:
            return result
        return play_playlist(query)

    # --- YouTube: latest video ---
    yt_play = re.search(
        r'(?:play|find|show|watch) (.+?)(?:\'s)? (?:latest |most recent |new )?(?:video|videos)', t)
    if yt_play:
        return search_youtube(f"{yt_play.group(1).strip()} latest")

    # --- YouTube: help video ---
    yt_help = re.search(
        r'(?:find|show|search) (?:a |me a )?video (?:about|on|for|that|to help) (.+)', t)
    if yt_help:
        return search_youtube(yt_help.group(1).strip())

    # --- YouTube: search ---
    yt_search = re.search(r'(?:search|find|look up) (.+?) on youtube', t)
    if yt_search:
        return search_youtube(yt_search.group(1).strip())

    # --- YouTube: channel ---
    yt_channel = re.search(
        r'open (.+?)(?:\'s)? (?:youtube channel|yt channel|channel on youtube)', t)
    if yt_channel:
        q = yt_channel.group(1).strip().replace(" ", "+")
        return open_website(f"youtube.com/results?search_query={q}+channel")

    # --- Google search ---
    google_match = re.search(r'^(?:google|search for|search) (.+)', t)
    if google_match and not any(x in t for x in ["game", "steam", "youtube"]):
        q = google_match.group(1).strip().replace(" ", "+")
        return open_website(f"google.com/search?q={q}")

    # --- Websites ---
    website_triggers = [".com", ".org", ".net", ".io", ".tv",
                        "youtube", "google", "reddit", "github",
                        "netflix", "twitter", "instagram", "twitch", "chatgpt"]
    if any(x in t for x in website_triggers) and any(x in t for x in ["open", "go to", "visit", "browse"]):
        if not any(app in t for app in APP_PRIORITY):
            for word in t.split():
                clean = word.strip(".,!?")
                if "." in clean or clean in website_triggers:
                    return open_website(clean)

    # --- Steam Games ---
    if re.search(r'\b(launch|run|start)\b', t):
        if not any(x in t for x in ["music", "song", "track", "media",
                                     "spotify", "youtube", "video", "playlist"]):
            app = re.sub(r'\b(launch|run|start)\b', '', t).strip()
            if app:
                result = launch_steam_game(app)
                if "Couldn't find" not in result:
                    return result
                return open_app(app)

    # --- Open Apps ---
    if re.search(r'^open .+', t):
        app = re.sub(r'^open\s+', '', t).strip()
        if app:
            return open_app(app)

    return None

def ask_llm(user_input):
    game_list = ", ".join(sorted(al.STEAM_GAMES.keys())) if al.STEAM_GAMES else "none detected"
    conversation_history.append({"role": "user", "content": user_input})
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": (
                f"You are {ASSISTANT_NAME}, a voice-controlled desktop AI assistant. "
                f"You can open apps, websites, control volume, play Spotify songs, and answer questions. "
                f"When asked to DO something on the computer, confirm you're doing it — don't give instructions. "
                f"Keep responses short and conversational. "
                f"Your detected Steam games are: {game_list}. "
                f"ONLY list games from this exact list when asked. Never make up game names."
            )},
            *conversation_history
        ]
    )
    reply = response.choices[0].message.content
    conversation_history.append({"role": "assistant", "content": reply})
    return reply

if __name__ == "__main__":
    speak(f"Hello! I am {ASSISTANT_NAME}. How can I help?")
    while True:
        user_input = input("You: ").strip()
        if not user_input:
            continue
        if user_input.lower() in ["exit", "goodbye", "quit"]:
            speak("Goodbye!")
            break
        result = handle_command(user_input)
        if result:
            speak(result)
        else:
            reply = ask_llm(user_input)
            speak(reply)