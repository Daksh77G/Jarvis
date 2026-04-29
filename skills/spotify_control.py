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

def _open_spotify_search(query: str):
    """Open Spotify search URI and press Enter to play first result"""
    q = query.replace(" ", "%20")
    os.startfile(f"spotify:search:{q}")
    if PYAUTOGUI_AVAILABLE:
        time.sleep(3)       # wait for Spotify to load the search
        pyautogui.press("enter")  # select first result

def play_song(query: str) -> str:
    sp = get_spotify()

    # Premium path — full API control
    if sp:
        try:
            results = sp.search(q=query, type="track", limit=1)
            tracks = results["tracks"]["items"]
            if not tracks:
                return f"Couldn't find '{query}' on Spotify."
            track = tracks[0]
            track_name = track["name"]
            artist = track["artists"][0]["name"]
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
            return f"Playing '{track_name}' by {artist}."
        except Exception:
            pass

    # Free account path — search URI + auto Enter
    _open_spotify_search(query)
    return f"Playing '{query}' on Spotify."

def play_playlist(query: str) -> str:
    sp = get_spotify()

    # Premium path
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

    # Free account path — search + Enter
    _open_spotify_search(f"playlist {query}")
    return f"Playing playlist '{query}' on Spotify."

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
        artist = track["artists"][0]["name"]
        return f"Currently playing '{name}' by {artist}."
    except Exception:
        return "Couldn't get current song."