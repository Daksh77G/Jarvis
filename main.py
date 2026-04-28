import os
import re
from groq import Groq
from skills.app_launcher import open_app, open_website, open_steam_game
from skills.system_controls import volume_up, volume_down, mute, shutdown, restart, sleep_pc, get_battery, take_screenshot

# --- Config ---
ASSISTANT_NAME = "Jarvis"
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
conversation_history = []

def speak(text):
    print(f"\n{ASSISTANT_NAME}: {text}\n")

def handle_command(user_input: str):
    text = user_input.lower()

    # --- Websites ---
    if "open" in text and any(x in text for x in [".com", ".org", ".net", "website", "youtube", "google", "reddit"]):
        # Extract URL or site name
        for word in text.split():
            if "." in word or word in ["youtube", "google", "reddit", "github", "netflix", "spotify"]:
                site_map = {
                    "youtube": "youtube.com",
                    "google": "google.com",
                    "reddit": "reddit.com",
                    "github": "github.com",
                    "netflix": "netflix.com",
                    "spotify": "open.spotify.com"
                }
                url = site_map.get(word, word)
                return open_website(url)

    # --- Volume ---
    if any(x in text for x in ["volume up", "turn up", "louder"]):
        return volume_up()
    if any(x in text for x in ["volume down", "turn down", "quieter", "lower volume"]):
        return volume_down()
    if "mute" in text:
        return mute()

    # --- System ---
    if "screenshot" in text:
        return take_screenshot()
    if "battery" in text:
        return get_battery()
    if "shutdown" in text or "turn off" in text:
        return shutdown(10)
    if "restart" in text or "reboot" in text:
        return restart()
    if "sleep" in text:
        return sleep_pc()

    # --- Games ---
    if "play" in text or ("open" in text and "game" in text):
        # Extract game name - word after "play" or before "game"
        words = text.replace("open", "").replace("play", "").replace("game", "").replace("launch", "").strip()
        game = words.strip()
        if game:
            return open_steam_game(game)

    # --- Apps ---
    if "open" in text or "launch" in text or "start" in text:
        words = text.replace("open", "").replace("launch", "").replace("start", "").strip()
        app = words.strip()
        if app:
            return open_app(app)

    # Not a command — send to LLM
    return None

def ask_llm(user_input):
    conversation_history.append({"role": "user", "content": user_input})
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": f"You are {ASSISTANT_NAME}, a helpful desktop AI assistant. Be concise."},
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

        # Try command first, fall back to LLM
        result = handle_command(user_input)
        if result:
            speak(result)
        else:
            reply = ask_llm(user_input)
            speak(reply)