import subprocess
import webbrowser
import os
import glob
import re
import string
import json
import winreg
from rapidfuzz import fuzz

# ── Blocked executables ───────────────────────────────────────────────
BLOCKED = [
    "sh.exe", "bash.exe", "cmd.exe", "powershell.exe",
    "unins", "uninstall", "setup", "vcredist", "directx",
    "redist", "dotnet", "crashhandler", "crashreport",
    "bugreport", "git", "mingw", "msys", "cygwin",
    "linkshandler", "vconsole", "ndp", "dxsetup", "vc_redist",
    "commonredist", "prerequisite", "physx", "unarc",
    "helper", "launcher_installer", "easyanticheat_setup"
]

# ── Folders that are NOT real games ──────────────────────────────────
BLOCKED_GAME_FOLDERS = [
    "steamworks common redistributables",
    "steamworks shared",
    "_commonredist",
    "steam controller configs",
    "proton",
]

# ── Protected apps — exact match, never fuzzy ─────────────────────────
PROTECTED_APPS = {
    "steam":        r"C:\Program Files (x86)\Steam\steam.exe",
    "notepad":      "notepad.exe",
    "calculator":   "calc.exe",
    "explorer":     "explorer.exe",
    "task manager": "taskmgr.exe",
    "paint":        "mspaint.exe",
}

# ── Known non-Steam apps ──────────────────────────────────────────────
APP_MAP = {
    "chrome":      r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "firefox":     r"C:\Program Files\Mozilla Firefox\firefox.exe",
    "vscode":      r"%LOCALAPPDATA%\Programs\Microsoft VS Code\Code.exe",
    "discord":     r"%LOCALAPPDATA%\Discord\Update.exe",
    "spotify":     r"%APPDATA%\Spotify\Spotify.exe",
    "riot client": r"C:\Riot Games\Riot Client\RiotClientServices.exe",
    "valorant":    r"C:\Riot Games\Riot Client\RiotClientServices.exe --launch-product=valorant --launch-patchline=live",
    "roblox":      r"%LOCALAPPDATA%\Roblox\Versions\RobloxPlayerLauncher.exe",
    "minecraft":   r"%APPDATA%\.minecraft\launcher\MinecraftLauncher.exe",
    "epic games":  r"C:\Program Files (x86)\Epic Games\Launcher\Portal\Binaries\Win32\EpicGamesLauncher.exe",
    "fortnite":    r"C:\Program Files\Epic Games\Fortnite\FortniteGame\Binaries\Win64\FortniteClient-Win64-Shipping.exe",
}

# ── Games where we know the exact exe name ────────────────────────────
# Overrides "largest exe" logic for known problem games
KNOWN_EXE_NAMES = {
    "counter-strike 2": "cs2.exe",
    "counter-strike global offensive": "cs2.exe",
    "aim lab": "AimLab_tb.exe",
    "aimlabs": "AimLab_tb.exe",
    "the finals": "Discovery.exe",
    "geometry dash": "GeometryDash.exe",
    "ghost of tsushima": "GhostOfTsushima.exe",
    "forza horizon 5": "ForzaHorizon5.exe",
    "elden ring": "eldenring.exe",
}

def is_safe_exe(path: str) -> bool:
    name = os.path.basename(path).lower()
    return not any(b in name for b in BLOCKED)

def is_real_game_folder(name: str) -> bool:
    n = name.lower()
    return not any(b in n for b in BLOCKED_GAME_FOLDERS)

def launch_detached(path: str, args: str = ""):
    full = f'"{path}" {args}' if args else f'"{path}"'
    subprocess.Popen(
        full,
        creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
        shell=True,
        close_fds=True
    )

# ── Drive + Steam detection ───────────────────────────────────────────

def get_all_drives() -> list:
    drives = []
    for letter in string.ascii_uppercase:
        drive = f"{letter}:\\"
        if os.path.exists(drive):
            drives.append(drive)
    return drives

def get_steam_library_paths() -> list:
    paths = []
    try:
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                             r"SOFTWARE\WOW6432Node\Valve\Steam")
        steam_path = winreg.QueryValueEx(key, "InstallPath")[0]
        winreg.CloseKey(key)
        vdf_path = os.path.join(steam_path, "steamapps", "libraryfolders.vdf")
        if os.path.exists(vdf_path):
            with open(vdf_path, "r", encoding="utf-8") as f:
                content = f.read()
            for match in re.finditer(r'"path"\s+"([^"]+)"', content):
                lib_path = match.group(1).replace("\\\\", "\\")
                common = os.path.join(lib_path, "steamapps", "common")
                if os.path.exists(common) and common not in paths:
                    paths.append(common)
    except Exception:
        pass

    for drive in get_all_drives():
        for name in ["Steam\\steamapps\\common",
                     "SteamLibrary\\steamapps\\common",
                     "Games\\Steam\\steamapps\\common",
                     "Program Files (x86)\\Steam\\steamapps\\common"]:
            full = os.path.join(drive, name)
            if os.path.exists(full) and full not in paths:
                paths.append(full)
    return paths

def find_best_exe(folder_path: str, game_name: str) -> str:
    """Find the best game exe — uses known names first, then largest safe exe"""
    game_lower = game_name.lower()

    # Check known exe names first
    if game_lower in KNOWN_EXE_NAMES:
        known = KNOWN_EXE_NAMES[game_lower].lower()
        for root, dirs, files in os.walk(folder_path):
            depth = root.replace(folder_path, "").count(os.sep)
            if depth > 4:
                dirs.clear()
                continue
            for f in files:
                if f.lower() == known:
                    return os.path.join(root, f)

    # Collect all safe exes up to 3 levels deep
    exes = []
    for root, dirs, files in os.walk(folder_path):
        depth = root.replace(folder_path, "").count(os.sep)
        if depth > 3:
            dirs.clear()
            continue
        # Skip tool/redist subfolders
        if any(b in root.lower() for b in ["_commonredist", "redist",
               "vcredist", "directx", "dotnet", "streamingassets",
               "deeplinking", "bin\\win64\\tools", "support"]):
            dirs.clear()
            continue
        for f in files:
            if f.endswith(".exe") and is_safe_exe(f):
                exes.append(os.path.join(root, f))

    if not exes:
        return ""

    # Prefer exe whose name fuzzy matches the game name
    game_clean = game_name.lower().replace(" ", "")
    best_by_name = max(exes, key=lambda p:
        fuzz.partial_ratio(game_clean, os.path.basename(p).replace(".exe","").lower()))
    name_score = fuzz.partial_ratio(game_clean,
        os.path.basename(best_by_name).replace(".exe","").lower())

    if name_score >= 60:
        return best_by_name

    # Fall back to largest exe
    return max(exes, key=os.path.getsize)

def get_all_steam_games() -> dict:
    games = {}
    for library in get_steam_library_paths():
        if not os.path.exists(library):
            continue
        print(f"  Scanning: {library}")
        steamapps_dir = os.path.dirname(library)

        # Method 1: ACF manifests (most accurate names)
        acf_games = {}
        try:
            for acf_file in glob.glob(os.path.join(steamapps_dir, "*.acf")):
                try:
                    with open(acf_file, "r", encoding="utf-8") as f:
                        content = f.read()
                    name_match = re.search(r'"name"\s+"([^"]+)"', content)
                    dir_match = re.search(r'"installdir"\s+"([^"]+)"', content)
                    if name_match and dir_match:
                        game_name = name_match.group(1)
                        install_dir = dir_match.group(1)
                        if not is_real_game_folder(game_name):
                            continue
                        folder_path = os.path.join(library, install_dir)
                        if os.path.exists(folder_path):
                            acf_games[game_name] = folder_path
                except Exception:
                    continue
        except Exception:
            pass

        for game_name, folder_path in acf_games.items():
            exe = find_best_exe(folder_path, game_name)
            if exe:
                games[game_name.lower()] = exe
                print(f"    + {game_name}")

        # Method 2: Folder scan fallback for anything ACF missed
        try:
            for game_folder in os.listdir(library):
                if not is_real_game_folder(game_folder):
                    continue
                if game_folder.lower() in games:
                    continue
                folder_path = os.path.join(library, game_folder)
                if not os.path.isdir(folder_path):
                    continue
                exe = find_best_exe(folder_path, game_folder)
                if exe:
                    games[game_folder.lower()] = exe
                    print(f"    + {game_folder} (folder scan)")
        except Exception:
            pass

    return games

# ── Cache system ──────────────────────────────────────────────────────
_CACHE_PATH = os.path.join(os.path.dirname(__file__), "..", "game_cache.json")
_INDEX_PATH = os.path.join(os.path.dirname(__file__), "..", "game_index.txt")

def save_game_cache(games: dict):
    try:
        with open(_CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(games, f, indent=2)
        with open(_INDEX_PATH, "w", encoding="utf-8") as f:
            for name, path in sorted(games.items()):
                f.write(f"{name} => {path}\n")
    except Exception:
        pass

def refresh_games() -> dict:
    print("Scanning Steam libraries across all drives...")
    games = get_all_steam_games()
    save_game_cache(games)
    print(f"Found {len(games)} games. Index saved → game_index.txt")
    return games

if os.path.exists(_CACHE_PATH):
    try:
        with open(_CACHE_PATH, "r", encoding="utf-8") as f:
            STEAM_GAMES = json.load(f)
        print(f"Loaded {len(STEAM_GAMES)} games from cache. Say 'refresh games' to rescan.")
    except Exception:
        STEAM_GAMES = refresh_games()
else:
    print("First run — scanning Steam library (one time only)...")
    STEAM_GAMES = refresh_games()

APP_SEARCH_DIRS = [d for drive in get_all_drives()
                   for d in [os.path.join(drive, "Program Files"),
                              os.path.join(drive, "Program Files (x86)"),
                              os.path.join(drive, "Riot Games")]
                   if os.path.exists(d)] + [
    os.path.expandvars(r"%APPDATA%"),
    os.path.expandvars(r"%LOCALAPPDATA%"),
]

# ── Core functions ────────────────────────────────────────────────────

def launch_steam_game(game_name: str) -> str:
    game_clean = game_name.lower().strip()
    best_match, best_score = None, 0
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
    app_clean = app_name.lower().strip()

    # 1. Protected apps
    for key, path in PROTECTED_APPS.items():
        if key in app_clean or app_clean in key:
            expanded = os.path.expandvars(path)
            if os.path.exists(expanded) and is_safe_exe(expanded):
                launch_detached(expanded)
                return f"Opening {key}."
            try:
                subprocess.Popen(path,
                    creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP)
                return f"Opening {key}."
            except Exception:
                pass

    # 2. APP_MAP fuzzy
    best_key, best_score = None, 0
    for key in APP_MAP:
        score = fuzz.partial_ratio(app_clean, key)
        if score > best_score:
            best_score = score
            best_key = key
    if best_score >= 75:
        raw = os.path.expandvars(APP_MAP[best_key])
        parts = raw.split(".exe")
        exe = parts[0] + ".exe"
        args = parts[1].strip() if len(parts) > 1 else ""
        if os.path.exists(exe) and is_safe_exe(exe):
            launch_detached(exe, args)
            return f"Opening {best_key}."

    # 3. Steam library
    result = launch_steam_game(app_clean)
    if "Couldn't find" not in result:
        return result

    # 4. PC folder search
    return search_and_open(app_clean)

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
                if any(x in root.lower() for x in ["git", "mingw", "msys", "cygwin", "windows"]):
                    dirs.clear()
                    continue
                for file in files:
                    if not file.endswith(".exe") or not is_safe_exe(file):
                        continue
                    exe_name = file.replace(".exe","").replace("-","").replace("_","").lower()
                    score = fuzz.partial_ratio(app_clean, exe_name)
                    if score > best_score:
                        best_score = score
                        best_match = os.path.join(root, file)
        except PermissionError:
            continue
    if best_match and best_score >= 78:
        launch_detached(best_match)
        return f"Opening {os.path.basename(best_match).replace('.exe','')}."
    return f"Couldn't find '{app_name}'. Add it to APP_MAP in app_launcher.py."

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