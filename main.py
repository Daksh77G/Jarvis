import os
import re
from groq import Groq
from skills.app_launcher import open_app, open_website, close_app, launch_steam_game, STEAM_GAMES
from skills.system_controls import (volume_up, volume_down, mute, set_volume,
    media_play_pause, media_next, media_previous,
    shutdown, cancel_shutdown, restart, sleep_pc, get_battery, take_screenshot)

ASSISTANT_NAME = "Jarvis"
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
conversation_history = []

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

    # --- Media ---
    if any(x in t for x in ["pause music", "pause media", "pause song",
                              "resume music", "resume media", "play pause"]):
        return media_play_pause()
    if any(x in t for x in ["next song", "next track", "skip song", "skip track"]):
        return media_next()
    if any(x in t for x in ["previous song", "last song", "go back track"]):
        return media_previous()

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

    # --- List Steam Games ---
    if any(x in t for x in ["list games", "list steam", "what games", "which games", "my games"]):
        if STEAM_GAMES:
            names = ", ".join(sorted(STEAM_GAMES.keys()))
            return f"I found these Steam games: {names}."
        return "I couldn't find any Steam games."

    # --- Close App ---
    if re.search(r'\b(close|quit|kill)\b', t) and not t.startswith("exit"):
        app = re.sub(r'\b(close|quit|kill)\b', '', t).strip()
        if app:
            return close_app(app)

    # --- Websites ---
    website_triggers = [".com", ".org", ".net", ".io", ".tv",
                        "youtube", "google", "reddit", "github",
                        "netflix", "spotify", "twitter", "instagram", "twitch", "chatgpt"]
    if any(x in t for x in website_triggers) and any(x in t for x in ["open", "go to", "visit", "browse"]):
        for word in t.split():
            clean = word.strip(".,!?")
            if "." in clean or clean in website_triggers:
                return open_website(clean)

    # --- Steam Games (play/run/launch) ---
    if re.search(r'\b(play|launch|run|start)\b', t):
        app = re.sub(r'\b(play|launch|run|start)\b', '', t).strip()
        if app:
            # Try Steam first
            result = launch_steam_game(app)
            if "Couldn't find" not in result:
                return result
            # Fall back to general app open
            return open_app(app)

    # --- Open Apps (includes Steam games via open_app fallback) ---
    if re.search(r'^open .+', t):
        app = re.sub(r'^open\s+', '', t).strip()
        if app:
            return open_app(app)

    return None  # Hand off to LLM

def ask_llm(user_input):
    game_list = ", ".join(sorted(STEAM_GAMES.keys())) if STEAM_GAMES else "none detected"
    conversation_history.append({"role": "user", "content": user_input})
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": (
                f"You are {ASSISTANT_NAME}, a voice-controlled desktop AI assistant. "
                f"You can open apps, websites, control volume, and answer questions. "
                f"When asked to DO something on the computer, confirm you're doing it — don't give instructions. "
                f"Keep responses short and conversational. "
                f"Your actually detected Steam games are: {game_list}. "
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