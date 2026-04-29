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
    "task manager": "taskmgr.exe",
    "paint": "mspaint.exe",
}

# These will NEVER be launched — safety blocklist
BLOCKED_EXECUTABLES = [
    "sh.exe", "bash.exe", "cmd.exe", "powershell.exe",
    "unins000.exe", "uninstall.exe", "setup.exe", "install.exe",
    "vcredist", "directx", "redist", "dotnet", "vc_redist",
    "crashhandler", "crashreport", "bugreport", "updater.exe",
    "update.exe", "launcher_installer"
]

STEAM_DIRS = [
    r"C:\Program Files (x86)\Steam\steamapps\common",
    r"D:\Steam\steamapps\common",
    r"D:\SteamLibrary\steamapps\common",
    r"C:\Steam\steamapps\common",
    r"E:\Steam\steamapps\common",
]

APP_SEARCH_DIRS = [
    r"C:\Program Files",
    r"C:\Program Files (x86)",
    r"C:\Riot Games",
    os.path.expandvars(r"C:\Users\%USERNAME%\AppData\Roaming"),
    os.path.expandvars(r"C:\Users\%USERNAME%\AppData\Local"),
]

def is_safe_exe(path: str) -> bool:
    name = os.path.basename(path).lower()
    return not any(blocked in name for blocked in BLOCKED_EXECUTABLES)

def launch_detached(path: str):
    """Launch a process fully detached from CMD so it doesn't freeze terminal"""
    subprocess.Popen(
        path,
        creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
        close_fds=True
    )

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

    if best_score >= 75:
        path = os.path.expandvars(APP_MAP[best_match])
        if os.path.exists(path) and is_safe_exe(path):
            launch_detached(path)
            return f"Opening {best_match}."

    return search_and_open(app_name)

def search_and_open(app_name: str) -> str:
    app_clean = app_name.replace(" ", "").lower()
    best_match = None
    best_score = 0

    for directory in APP_SEARCH_DIRS:
        if not os.path.exists(directory):
            continue
        try:
            # Only search 2 levels deep for speed
            for root, dirs, files in os.walk(directory):
                depth = root.replace(directory, "").count(os.sep)
                if depth > 2:
                    dirs.clear()
                    continue
                for file in files:
                    if not file.endswith(".exe"):
                        continue
                    if not is_safe_exe(file):
                        continue
                    exe_name = file.replace(".exe","").replace("-"," ").replace("_"," ").lower()
                    score = fuzz.partial_ratio(app_clean, exe_name.replace(" ",""))
                    if score > best_score:
                        best_score = score
                        best_match = os.path.join(root, file)
        except PermissionError:
            continue

    if best_match and best_score >= 75 and is_safe_exe(best_match):
        launch_detached(best_match)
        return f"Opening {os.path.basename(best_match).replace('.exe','')}."

    return f"Couldn't find '{app_name}'. You can add it manually in the app list."

def close_app(app_name: str) -> str:
    app_name = app_name.lower().strip()
    exe = app_name if app_name.endswith(".exe") else app_name + ".exe"
    result = subprocess.run(["taskkill", "/F", "/IM", exe], capture_output=True, text=True)
    if "SUCCESS" in result.stdout:
        return f"Closed {app_name}."
    ps = subprocess.run(["tasklist"], capture_output=True, text=True)
    for line in ps.stdout.splitlines():
        parts = line.split()
        if not parts:
            continue
        proc = parts[0].replace(".exe","").lower()
        if fuzz.partial_ratio(app_name, proc) >= 75:
            subprocess.run(["taskkill", "/F", "/IM", parts[0]], capture_output=True)
            return f"Closed {proc}."
    return f"Couldn't find '{app_name}' running."

def open_website(url: str) -> str:
    SITE_MAP = {
        "youtube": "youtube.com", "google": "google.com",
        "reddit": "reddit.com", "github": "github.com",
        "netflix": "netflix.com", "spotify": "open.spotify.com",
        "twitter": "twitter.com", "x": "x.com",
        "instagram": "instagram.com", "twitch": "twitch.tv",
        "chatgpt": "chatgpt.com",
    }
    url = url.lower().strip()
    url = SITE_MAP.get(url, url)
    if not url.startswith("http"):
        url = "https://" + url
    webbrowser.open(url)
    return f"Opening {url}."

def launch_steam_game(game_name: str) -> str:
    game_clean = game_name.lower().replace(" ", "")
    best_match_folder = None
    best_score = 0

    for steam_dir in STEAM_DIRS:
        if not os.path.exists(steam_dir):
            continue
        try:
            for game_folder in os.listdir(steam_dir):
                folder_clean = game_folder.lower().replace(" ", "")
                score = fuzz.partial_ratio(game_clean, folder_clean)
                if score > best_score:
                    best_score = score
                    best_match_folder = os.path.join(steam_dir, game_folder)
        except Exception:
            continue

    if best_match_folder and best_score >= 65:
        # Find all .exe files directly in the game folder (not subdirs first)
        game_folder_exes = glob.glob(f"{best_match_folder}/*.exe")
        game_folder_exes = [e for e in game_folder_exes if is_safe_exe(e)]

        if not game_folder_exes:
            # Go one level deeper only
            game_folder_exes = glob.glob(f"{best_match_folder}/**/*.exe", recursive=False)
            game_folder_exes = [e for e in game_folder_exes if is_safe_exe(e)]

        if game_folder_exes:
            # Pick largest .exe = most likely the game
            main_exe = max(game_folder_exes, key=os.path.getsize)
            launch_detached(main_exe)
            return f"Launching {os.path.basename(best_match_folder)}."

    # Fallback: open Steam
    steam = r"C:\Program Files (x86)\Steam\steam.exe"
    if os.path.exists(steam):
        launch_detached(steam)
        return f"Couldn't find {game_name} directly. Opening Steam for you."

    return f"Couldn't find {game_name}."