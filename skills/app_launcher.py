import subprocess
import webbrowser
import os
import glob
import re
import winreg
from rapidfuzz import fuzz

# ── Blocked executables (never launch these) ──────────────────────────
BLOCKED = [
    "sh.exe", "bash.exe", "cmd.exe", "powershell.exe",
    "unins", "uninstall", "setup", "install", "vcredist",
    "directx", "redist", "dotnet", "crashhandler", "crashreport",
    "bugreport", "updater", "update", "git", "mingw", "msys", "cygwin"
]

# ── Known apps (fallback for non-Steam apps) ──────────────────────────
APP_MAP = {
    "chrome":       r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "firefox":      r"C:\Program Files\Mozilla Firefox\firefox.exe",
    "notepad":      "notepad.exe",
    "calculator":   "calc.exe",
    "explorer":     "explorer.exe",
    "task manager": "taskmgr.exe",
    "paint":        "mspaint.exe",
    "vscode":       r"%LOCALAPPDATA%\Programs\Microsoft VS Code\Code.exe",
    "discord":      r"%LOCALAPPDATA%\Discord\Update.exe",
    "spotify":      r"%APPDATA%\Spotify\Spotify.exe",
    "riot client":  r"C:\Riot Games\Riot Client\RiotClientServices.exe",
    "valorant":     r"C:\Riot Games\Riot Client\RiotClientServices.exe --launch-product=valorant --launch-patchline=live",
}

APP_SEARCH_DIRS = [
    r"C:\Program Files",
    r"C:\Program Files (x86)",
    r"C:\Riot Games",
    os.path.expandvars(r"%APPDATA%"),
    os.path.expandvars(r"%LOCALAPPDATA%"),
]

def is_safe_exe(path: str) -> bool:
    name = os.path.basename(path).lower()
    return not any(b in name for b in BLOCKED)

def launch_detached(path: str, args: str = ""):
    full = f'"{path}" {args}' if args else f'"{path}"'
    subprocess.Popen(
        full,
        creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
        shell=True,
        close_fds=True
    )

# ── Steam auto-detection ──────────────────────────────────────────────

def get_steam_library_paths() -> list:
    """Read Steam's libraryfolders.vdf to find ALL game library locations"""
    paths = []

    # Find Steam install path from registry
    try:
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                             r"SOFTWARE\WOW6432Node\Valve\Steam")
        steam_path = winreg.QueryValueEx(key, "InstallPath")[0]
        winreg.CloseKey(key)
    except Exception:
        steam_path = r"C:\Program Files (x86)\Steam"

    vdf_path = os.path.join(steam_path, "steamapps", "libraryfolders.vdf")
    if not os.path.exists(vdf_path):
        return [os.path.join(steam_path, "steamapps", "common")]

    with open(vdf_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Extract all library paths from the VDF file
    for match in re.finditer(r'"path"\s+"([^"]+)"', content):
        lib_path = match.group(1).replace("\\\\", "\\")
        common = os.path.join(lib_path, "steamapps", "common")
        if os.path.exists(common):
            paths.append(common)

    return paths if paths else [os.path.join(steam_path, "steamapps", "common")]

def get_all_steam_games() -> dict:
    """Return a dict of {game_name_lower: exe_path} for all installed Steam games"""
    games = {}
    for library in get_steam_library_paths():
        if not os.path.exists(library):
            continue
        for game_folder in os.listdir(library):
            folder_path = os.path.join(library, game_folder)
            if not os.path.isdir(folder_path):
                continue
            # Find best exe in the game's root folder
            exes = [f for f in glob.glob(f"{folder_path}/*.exe") if is_safe_exe(f)]
            if not exes:
                # Go one level deeper
                exes = [f for f in glob.glob(f"{folder_path}/**/*.exe", recursive=False)
                        if is_safe_exe(f)]
            if exes:
                main_exe = max(exes, key=os.path.getsize)
                games[game_folder.lower()] = main_exe
    return games

# Cache games at startup so search is instant
print("Scanning Steam library...")
STEAM_GAMES = get_all_steam_games()
print(f"Found {len(STEAM_GAMES)} Steam games.")

# ── Core functions ────────────────────────────────────────────────────

def launch_steam_game(game_name: str) -> str:
    game_clean = game_name.lower().strip()
    best_match = None
    best_score = 0

    for folder_name, exe_path in STEAM_GAMES.items():
        score = fuzz.partial_ratio(game_clean, folder_name)
        if score > best_score:
            best_score = score
            best_match = (folder_name, exe_path)

    if best_match and best_score >= 60:
        launch_detached(best_match[1])
        return f"Launching {best_match[0].title()}."

    return f"Couldn't find '{game_name}' in your Steam library."

def open_app(app_name: str) -> str:
    app_name_clean = app_name.lower().strip()

    # 1. Check known APP_MAP first
    best_key, best_score = None, 0
    for key in APP_MAP:
        score = fuzz.partial_ratio(app_name_clean, key)
        if score > best_score:
            best_score = score
            best_key = key

    if best_score >= 75:
        raw = os.path.expandvars(APP_MAP[best_key])
        # Handle entries with args (like valorant)
        parts = raw.split(".exe")
        exe = parts[0] + ".exe"
        args = parts[1].strip() if len(parts) > 1 else ""
        if os.path.exists(exe) and is_safe_exe(exe):
            launch_detached(exe, args)
            return f"Opening {best_key}."

    # 2. Check Steam games
    steam_result = launch_steam_game(app_name_clean)
    if "Couldn't find" not in steam_result:
        return steam_result

    # 3. Search PC folders (shallow)
    return search_and_open(app_name_clean)

def search_and_open(app_name: str) -> str:
    app_clean = app_name.replace(" ", "").lower()
    best_match, best_score = None, 0

    for directory in APP_SEARCH_DIRS:
        if not os.path.exists(directory):
            continue
        try:
            for root, dirs, files in os.walk(directory):
                depth = root.replace(directory, "").count(os.sep)
                if depth > 2:
                    dirs.clear()
                    continue
                for file in files:
                    if not file.endswith(".exe") or not is_safe_exe(file):
                        continue
                    # Skip Git/MinGW/system paths
                    if any(x in root.lower() for x in ["git", "mingw", "msys", "cygwin", "windows"]):
                        continue
                    exe_name = file.replace(".exe", "").replace("-", "").replace("_", "").lower()
                    score = fuzz.partial_ratio(app_clean, exe_name)
                    if score > best_score:
                        best_score = score
                        best_match = os.path.join(root, file)
        except PermissionError:
            continue

    if best_match and best_score >= 78 and is_safe_exe(best_match):
        launch_detached(best_match)
        return f"Opening {os.path.basename(best_match).replace('.exe', '')}."

    return f"Couldn't find '{app_name}'. You can add it to APP_MAP in app_launcher.py."

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
        proc = parts[0].replace(".exe", "").lower()
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