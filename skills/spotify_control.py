import os
import time
import webbrowser

try:
    import pyautogui
    PYAUTOGUI_AVAILABLE = True
except ImportError:
    PYAUTOGUI_AVAILABLE = False

try:
    import spotipy
    from spotipy.oauth2 import SpotifyOAuth
    SPOTIPY_AVAILABLE = True
except ImportError:
    SPOTIPY_AVAILABLE = False

_sp = None

def get_spotify():
    global _sp
    if _sp:
        return _sp
    if not SPOTIPY_AVAILABLE:
        return None
    try:
        _sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
            client_id=os.getenv("SPOTIFY_CLIENT_ID"),
            client_secret=os.getenv("SPOTIFY_CLIENT_SECRET"),
            redirect_uri=os.getenv("SPOTIFY_REDIRECT_URI", "http://localhost:8888/callback"),
            scope="user-read-playback-state user-modify-playback-state user-read-currently-playing"
        ))
        return _sp
    except Exception:
        return None

def _spotify_play_song(query: str):
    """Specific song — escape, tab, enter, enter"""
    q = query.replace(" ", "%20")
    os.startfile(f"spotify:search:{q}")
    if PYAUTOGUI_AVAILABLE:
        time.sleep(3.5)        # wait for Spotify to load
        pyautogui.press("escape")
        time.sleep(0.05)
        pyautogui.press("tab")
        time.sleep(0.05)
        pyautogui.press("enter")
        time.sleep(0.05)
        pyautogui.press("enter")

def _spotify_play_playlist(query: str):
    """Playlist/genre — escape, tab, enter, wait, tab, tab, enter"""
    q = query.replace(" ", "%20")
    os.startfile(f"spotify:search:{q}")
    if PYAUTOGUI_AVAILABLE:
        time.sleep(3.5)        # wait for Spotify to load
        pyautogui.press("escape")
        time.sleep(0.05)
        pyautogui.press("tab")
        time.sleep(0.05)
        pyautogui.press("enter")
        time.sleep(1.0)        # wait for playlist page to load
        pyautogui.press("tab")
        time.sleep(0.05)
        pyautogui.press("tab")
        time.sleep(0.05)
        pyautogui.press("enter")
        
def play_song(query: str) -> str:
    sp = get_spotify()

    if sp:
        try:
            results = sp.search(q=query, type="track", limit=1)
            tracks = results["tracks"]["items"]
            if not tracks:
                return f"Couldn't find '{query}' on Spotify."
            track = tracks[0]
            track_name = track["name"]
            devices = sp.devices()
            device_list = devices.get("devices", [])
            if not device_list:
                os.startfile("spotify:")
                return f"Open Spotify first, then ask me again to play '{track_name}'."
            device_id = next(
                (d["id"] for d in device_list if d["is_active"]),
                device_list[0]["id"]
            )
            sp.start_playback(device_id=device_id, uris=[track["uri"]])
            return f"Playing '{track_name}' on Spotify."
        except Exception:
            pass

    _spotify_play_song(query)
    return f"Playing '{query}' on Spotify."

def play_playlist(query: str) -> str:
    sp = get_spotify()

    if sp:
        try:
            results = sp.search(q=query, type="playlist", limit=1)
            playlists = results["playlists"]["items"]
            if not playlists:
                return f"Couldn't find playlist '{query}'."
            playlist = playlists[0]
            playlist_name = playlist["name"]
            devices = sp.devices()
            device_list = devices.get("devices", [])
            if not device_list:
                os.startfile("spotify:")
                return f"Open Spotify first, then ask me again to play '{playlist_name}'."
            device_id = next(
                (d["id"] for d in device_list if d["is_active"]),
                device_list[0]["id"]
            )
            sp.start_playback(device_id=device_id, context_uri=playlist["uri"])
            return f"Playing playlist '{playlist_name}'."
        except Exception:
            pass

    # Free path — search everything including liked songs as a playlist
    _spotify_play_playlist(query)
    return f"Playing '{query}' on Spotify."

def get_current_song() -> str:
    sp = get_spotify()
    if not sp:
        return "Spotify API not connected."
    try:
        current = sp.current_playback()
        if not current or not current.get("item"):
            return "Nothing is playing right now."
        track = current["item"]
        name = track["name"]
        artists = ", ".join(a["name"] for a in track["artists"])
        return f"Currently playing '{name}' by {artists}."
    except Exception:
        return "Couldn't get current song."