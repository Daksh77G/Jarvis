import subprocess
import webbrowser
import os
import glob
from rapidfuzz import fuzz

APP_MAP = {
    "chrome": r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "firefox": r"C:\Program Files\Mozilla Firefox\firefox.exe",
    "notepad": "notepad.exe",
    "calculator": "calc.exe",
    "explorer": "explorer.exe",
    "vscode": r"C:\Users\%USERNAME%\AppData\Local\Programs\Microsoft VS Code\Code.exe",
    "discord": r"C:\Users\%USERNAME%\AppData\Local\Discord\Update.exe",
    "spotify": r"C:\Users\%USERNAME%\AppData\Roaming\Spotify\Spotify.exe",
    "steam": r"C:\Program Files (x86)\Steam\steam.exe",
    "riot client": r"C:\Riot Games\Riot Client\RiotClientServices.exe",
    "valorant": r"C:\Riot Games\VALORANT\live\VALORANT.exe",
    "word": r"C:\Program Files\Microsoft Office\root\Office16\WINWORD.EXE",
    "excel": r"C:\Program Files\Microsoft Office\root\Office16\EXCEL.EXE",
}

SEARCH_DIRS = [
    r"C:\Program Files",
    r"C:\Program Files (x86)",
    r"C:\Riot Games",
    r"C:\Games",
    r"D:\Games",
    r"D:\Program Files",
    os.path.expandvars(r"C:\Users\%USERNAME%\AppData\Roaming"),
    os.path.expandvars(r"C:\Users\%USERNAME%\AppData\Local"),
]

def open_app(app_name: str) -> str:
    app_name = app_name.lower().strip()

    # Fuzzy match against known apps
    best_match = None
    best_score = 0
    for key in APP_MAP:
        score = fuzz.partial_ratio(app_name, key)
        if score > best_score:
            best_score = score
            best_match = key

    if best_score >= 70:
        path = os.path.expandvars(APP_MAP[best_match])
        if os.path.exists(path):
            subprocess.Popen(path)
            return f"Opening {best_match}."
        # Fall through to search if path doesn't exist

    return search_and_open(app_name)

def search_and_open(app_name: str) -> str:
    """Fuzzy search entire PC for matching .exe"""
    app_clean = app_name.replace(" ", "").lower()
    best_match = None
    best_score = 0

    for directory in SEARCH_DIRS:
        if not os.path.exists(directory):
            continue
        try:
            matches = glob.glob(f"{directory}/**/*.exe", recursive=True)
            for path in matches:
                exe_name = os.path.basename(path).replace(".exe", "").replace("-", " ").replace("_", " ").lower()
                score = fuzz.partial_ratio(app_clean, exe_name.replace(" ", ""))
                if score > best_score:
                    best_score = score
                    best_match = path
        except PermissionError:
            continue

    if best_match and best_score >= 70:
        subprocess.Popen(best_match)
        return f"Found and opening {os.path.basename(best_match)}."

    return f"Couldn't find '{app_name}' on your PC."

def close_app(app_name: str) -> str:
    """Kill a running process by name"""
    app_name = app_name.lower().strip()
    exe = app_name if app_name.endswith(".exe") else app_name + ".exe"
    result = subprocess.run(["taskkill", "/F", "/IM", exe], capture_output=True, text=True)
    if "SUCCESS" in result.stdout:
        return f"Closed {app_name}."
    # Try fuzzy match on running processes
    ps = subprocess.run(["tasklist"], capture_output=True, text=True)
    for line in ps.stdout.splitlines():
        proc = line.split()[0].replace(".exe","").lower() if line.split() else ""
        if fuzz.partial_ratio(app_name, proc) >= 75:
            subprocess.run(["taskkill", "/F", "/IM", line.split()[0]], capture_output=True)
            return f"Closed {proc}."
    return f"Couldn't find '{app_name}' running."

def open_website(url: str) -> str:
    SITE_MAP = {
        "youtube": "youtube.com",
        "google": "google.com",
        "reddit": "reddit.com",
        "github": "github.com",
        "netflix": "netflix.com",
        "spotify": "open.spotify.com",
        "twitter": "twitter.com",
        "x": "x.com",
        "instagram": "instagram.com",
        "twitch": "twitch.tv",
        "chatgpt": "chatgpt.com",
    }
    url = url.lower().strip()
    url = SITE_MAP.get(url, url)
    if not url.startswith("http"):
        url = "https://" + url
    webbrowser.open(url)
    return f"Opening {url}."

def launch_steam_game(game_name: str) -> str:
    """Search Steam library folder for game .exe"""
    steam_dirs = [
        r"C:\Program Files (x86)\Steam\steamapps\common",
        r"D:\Steam\steamapps\common",
        r"D:\SteamLibrary\steamapps\common",
        r"C:\Steam\steamapps\common",
    ]
    game_clean = game_name.lower().replace(" ", "")
    best_match = None
    best_score = 0

    for steam_dir in steam_dirs:
        if not os.path.exists(steam_dir):
            continue
        for game_folder in os.listdir(steam_dir):
            folder_clean = game_folder.lower().replace(" ", "")
            score = fuzz.partial_ratio(game_clean, folder_clean)
            if score > best_score:
                best_score = score
                best_match = os.path.join(steam_dir, game_folder)

    if best_match and best_score >= 65:
        # Find the main .exe inside the game folder
        exes = glob.glob(f"{best_match}/**/*.exe", recursive=True)
        # Filter out uninstallers and redistributables
        exes = [e for e in exes if not any(x in e.lower() for x in
                ["unins", "redist", "setup", "install", "vcredist", "directx"])]
        if exes:
            # Pick the largest .exe (usually the game itself)
            main_exe = max(exes, key=os.path.getsize)
            subprocess.Popen(main_exe)
            return f"Launching {os.path.basename(best_match)}."

    # Fallback: open Steam itself
    steam = r"C:\Program Files (x86)\Steam\steam.exe"
    if os.path.exists(steam):
        subprocess.Popen(steam)
        return f"Couldn't find {game_name} directly. Opening Steam instead."

    return f"Couldn't find {game_name}."