import subprocess
import webbrowser
import os
import glob

# Common apps - user can add more
APP_MAP = {
    "chrome": r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "firefox": r"C:\Program Files\Mozilla Firefox\firefox.exe",
    "notepad": "notepad.exe",
    "calculator": "calc.exe",
    "explorer": "explorer.exe",
    "vscode": r"C:\Users\%USERNAME%\AppData\Local\Programs\Microsoft VS Code\Code.exe",
    "discord": r"C:\Users\%USERNAME%\AppData\Local\Discord\Update.exe --processStart Discord.exe",
    "spotify": r"C:\Users\%USERNAME%\AppData\Roaming\Spotify\Spotify.exe",
    "steam": r"C:\Program Files (x86)\Steam\steam.exe",
    "word": r"C:\Program Files\Microsoft Office\root\Office16\WINWORD.EXE",
    "excel": r"C:\Program Files\Microsoft Office\root\Office16\EXCEL.EXE",
}

def open_app(app_name: str) -> str:
    app_name = app_name.lower().strip()

    # Direct match
    if app_name in APP_MAP:
        path = os.path.expandvars(APP_MAP[app_name])
        try:
            subprocess.Popen(path)
            return f"Opening {app_name}."
        except FileNotFoundError:
            return f"Couldn't find {app_name} at the expected path."

    # Search for .exe on the PC
    return search_and_open(app_name)

def search_and_open(app_name: str) -> str:
    """Search common directories for the .exe"""
    search_dirs = [
        r"C:\Program Files",
        r"C:\Program Files (x86)",
        os.path.expandvars(r"C:\Users\%USERNAME%\AppData\Roaming"),
        os.path.expandvars(r"C:\Users\%USERNAME%\AppData\Local"),
        r"C:\Games",
        r"D:\Games",
        r"D:\Program Files",
    ]
    for directory in search_dirs:
        if not os.path.exists(directory):
            continue
        matches = glob.glob(f"{directory}/**/{app_name}.exe", recursive=True)
        if matches:
            try:
                subprocess.Popen(matches[0])
                return f"Found and opening {app_name}."
            except Exception as e:
                return f"Found {app_name} but couldn't open it: {e}"

    return f"Couldn't find {app_name} on your PC. Try adding it to the app list."

def open_website(url: str) -> str:
    """Open any website in the default browser"""
    if not url.startswith("http"):
        url = "https://" + url
    webbrowser.open(url)
    return f"Opening {url} in your browser."

def open_steam_game(game_name: str) -> str:
    """Launch a Steam game by name via Steam's URL protocol"""
    # First try opening Steam itself
    steam_path = os.path.expandvars(r"C:\Program Files (x86)\Steam\steam.exe")
    if os.path.exists(steam_path):
        # Steam can launch games by name search
        subprocess.Popen([steam_path, f"steam://run/{game_name}"])
        return f"Launching {game_name} via Steam."
    else:
        # Try searching for the game .exe directly
        return search_and_open(game_name)