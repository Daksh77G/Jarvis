import subprocess
import webbrowser
import os
import glob
import re
import string
import winreg
from rapidfuzz import fuzz

# ── Blocked executables ───────────────────────────────────────────────
BLOCKED = [
    "sh.exe", "bash.exe", "cmd.exe", "powershell.exe",
    "unins", "uninstall", "setup", "install", "vcredist",
    "directx", "redist", "dotnet", "crashhandler", "crashreport",
    "bugreport", "updater", "update", "git", "mingw", "msys", "cygwin"
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

# ── Known apps — fuzzy matched ────────────────────────────────────────
APP_MAP = {
    "chrome":      r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "firefox":     r"C:\Program Files\Mozilla Firefox\firefox.exe",
    "vscode":      r"%LOCALAPPDATA%\Programs\Microsoft VS Code\Code.exe",
    "discord":     r"%LOCALAPPDATA%\Discord\Update.exe",
    "spotify":     r"%APPDATA%\Spotify\Spotify.exe",
    "riot client": r"C:\Riot Games\Riot Client\RiotClientServices.exe",
    "valorant":    r"C:\Riot Games\Riot Client\RiotClientServices.exe --launch-product=valorant --launch-patchline=live",
}

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

    # 1. Read Steam registry for VDF config
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

    # 2. Scan all drives for common Steam folder names
    steam_folder_names = [
        "Steam\\steamapps\\common",
        "SteamLibrary\\steamapps\\common",
        "Games\\Steam\\steamapps\\common",
        "Games\\steamapps\\common",
        "Program Files (x86)\\Steam\\steamapps\\common",
    ]
    for drive in get_all_drives():
        for name in steam_folder_names:
            full = os.path.join(drive, name)
            if os.path.exists(full) and full not in paths:
                paths.append(full)

    return paths

def get_app_search_dirs() -> list:
    dirs = []
    for drive in get_all_drives():
        for folder in ["Program Files", "Program Files (x86)", "Riot Games", "Games"]:
            full = os.path.join(drive, folder)
            if os.path.exists(full):
                dirs.append(full)
    dirs.append(os.path.expandvars(r"%APPDATA%"))
    dirs.append(os.path.expandvars(r"%LOCALAPPDATA%"))
    return dirs

def get_all_steam_games() -> dict:
    games = {}
    for library in get_steam_library_paths():
        if not os.path.exists(library):
            continue
        print(f"  Scanning: {library}")
        for game_folder in os.listdir(library):
            folder_path = os.path.join(library, game_folder)
            if not os.path.isdir(folder_path):
                continue
            # Root folder first
            exes = [f for f in glob.glob(f"{folder_path}/*.exe") if is_safe_exe(f)]
            if not exes:
                # One level deeper
                try:
                    for sub in os.listdir(folder_path):
                        sub_path = os.path.join(folder_path, sub)
                        if os.path.isdir(sub_path):
                            exes += [f for f in glob.glob(f"{sub_path}/*.exe")
                                     if is_safe_exe(f)]
                except PermissionError:
                    pass
            if exes:
                main_exe = max(exes, key=os.path.getsize)
                games[game_folder.lower()] = main_exe
                print(f"    + {game_folder}")
    return games

# ── Startup scan ──────────────────────────────────────────────────────
print("Scanning Steam libraries across all drives...")
STEAM_GAMES = get_all_steam_games()
print(f"Found {len(STEAM_GAMES)} Steam games.")

# Save index for debugging
_index_path = os.path.join(os.path.dirname(__file__), "..", "game_index.txt")
try:
    with open(_index_path, "w", encoding="utf-8") as f:
        for name, path in sorted(STEAM_GAMES.items()):
            f.write(f"{name} => {path}\n")
    print(f"Game index saved → game_index.txt")
except Exception:
    pass

APP_SEARCH_DIRS = get_app_search_dirs()

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

    # 1. Protected apps — substring match, no fuzzy
    for key, path in PROTECTED_APPS.items():
        if key in app_clean or app_clean in key:
            expanded = os.path.expandvars(path)
            if os.path.exists(expanded) and is_safe_exe(expanded):
                launch_detached(expanded)
                return f"Opening {key}."
            else:
                try:
                    subprocess.Popen(
                        path,
                        creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
                    )
                    return f"Opening {key}."
                except Exception:
                    pass

    # 2. APP_MAP — fuzzy match
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
    steam_result = launch_steam_game(app_clean)
    if "Couldn't find" not in steam_result:
        return steam_result

    # 4. Broad PC folder search
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
        return f"Opening {os.path.basename(best_match).replace('.exe', '')}."

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
        proc = parts[0].replace(".exe", "").lower()
        if fuzz.partial_ratio(app_name, proc) >= 75:
            subprocess.run(["taskkill", "/F", "/IM", parts[0]], capture_output=True)
            return f"Closed {proc}."
    return f"Couldn't find '{app_name}' running."

def open_website(url: str) -> str:
    SITE_MAP = {
        "youtube":   "youtube.com",
        "google":    "google.com",
        "reddit":    "reddit.com",
        "github":    "github.com",
        "netflix":   "netflix.com",
        "spotify":   "open.spotify.com",
        "twitter":   "twitter.com",
        "x":         "x.com",
        "instagram": "instagram.com",
        "twitch":    "twitch.tv",
        "chatgpt":   "chatgpt.com",
    }
    url = url.lower().strip()
    url = SITE_MAP.get(url, url)
    if not url.startswith("http"):
        url = "https://" + url
    webbrowser.open(url)
    return f"Opening {url}."