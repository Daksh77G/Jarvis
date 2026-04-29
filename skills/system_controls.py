import subprocess
import os
import datetime


def volume_up() -> str:
    subprocess.run(["powershell", "-command",
        "(New-Object -ComObject WScript.Shell).SendKeys([char]175)"])
    return "Volume increased."


def volume_down() -> str:
    subprocess.run(["powershell", "-command",
        "(New-Object -ComObject WScript.Shell).SendKeys([char]174)"])
    return "Volume decreased."


def mute() -> str:
    subprocess.run(["powershell", "-command",
        "(New-Object -ComObject WScript.Shell).SendKeys([char]173)"])
    return "Toggled mute."


def set_volume(level: int) -> str:
    level = max(0, min(100, level))
    try:
        subprocess.run(
            ["powershell", "-command",
             f"$wsh = New-Object -ComObject WScript.Shell; "
             f"1..50 | ForEach-Object {{ $wsh.SendKeys([char]174) }}; "
             f"$steps = [math]::Round({level} / 2); "
             f"1..$steps | ForEach-Object {{ $wsh.SendKeys([char]175) }}"],
            capture_output=True
        )
        return f"Volume set to approximately {level}%."
    except Exception as e:
        return f"Couldn't set volume: {e}"


# media_play_pause, media_next, media_previous removed —
# now handled directly via Spotify API in spotify_control.py


def shutdown(delay: int = 10) -> str:
    os.system(f"shutdown /s /t {delay}")
    return f"Shutting down in {delay} seconds."


def cancel_shutdown() -> str:
    os.system("shutdown /a")
    return "Shutdown cancelled."


def restart() -> str:
    os.system("shutdown /r /t 0")
    return "Restarting..."


def sleep_pc() -> str:
    os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
    return "Going to sleep."


def get_battery() -> str:
    result = subprocess.run(
        ["powershell", "-command",
         "(Get-WmiObject Win32_Battery).EstimatedChargeRemaining"],
        capture_output=True, text=True
    )
    level = result.stdout.strip()
    return f"Battery is at {level}%." if level else "No battery found (desktop PC)."


def take_screenshot() -> str:
    filename = os.path.join(
        os.path.expanduser("~"), "Desktop",
        f"screenshot_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    )
    subprocess.run(["powershell", "-command",
        f"Add-Type -AssemblyName System.Windows.Forms,System.Drawing; "
        f"$s=[System.Windows.Forms.Screen]::PrimaryScreen.Bounds; "
        f"$b=New-Object System.Drawing.Bitmap $s.Width,$s.Height; "
        f"$g=[System.Drawing.Graphics]::FromImage($b); "
        f"$g.CopyFromScreen($s.Location,[System.Drawing.Point]::Empty,$s.Size); "
        f"$b.Save('{filename}')"], capture_output=True)
    return "Screenshot saved to Desktop."