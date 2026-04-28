import subprocess
import os

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
    """Set exact volume level 0-100"""
    level = max(0, min(100, level))
    script = f"""
    $volume = {level / 100}
    $obj = New-Object -ComObject WScript.Shell
    Add-Type -TypeDefinition @'
    using System.Runtime.InteropServices;
    [Guid("5CDF2C82-841E-4546-9722-0CF74078229A"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    interface IAudioEndpointVolume {{
        int f(); int g(); int h(); int i();
        int SetMasterVolumeLevelScalar(float fLevel, System.Guid pguidEventContext);
        int j(); int k(); int l(); int m();
        int GetMasterVolumeLevelScalar(out float pfLevel);
    }}
    [Guid("BCDE0395-E52F-467C-8E3D-C4579291692E"), ClassInterface(ClassInterfaceType.None)]
    class MMDeviceEnumerator {{}}
    [Guid("A95664D2-9614-4F35-A746-DE8DB63617E6"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    interface IMMDeviceEnumerator {{
        int f();
        int GetDefaultAudioEndpoint(int dataFlow, int role, out System.IntPtr ppDevice);
    }}
'@
    $type = [System.Type]::GetTypeFromCLSID([Guid]"BCDE0395-E52F-467C-8E3D-C4579291692E")
    $obj2 = [System.Activator]::CreateInstance($type)
    $enumerator = [IMMDeviceEnumerator]$obj2
    $devicePtr = [System.IntPtr]::Zero
    $enumerator.GetDefaultAudioEndpoint(0, 1, [ref]$devicePtr) | Out-Null
    """
    # Simpler reliable method via nircmd or powershell audio API
    try:
        subprocess.run(
            ["powershell", "-command",
             f"$wsh = New-Object -ComObject WScript.Shell; "
             f"1..50 | ForEach-Object {{ $wsh.SendKeys([char]174) }}; "  # mute all the way down
             f"$steps = [math]::Round({level} / 2); "
             f"1..$steps | ForEach-Object {{ $wsh.SendKeys([char]175) }}"],  # bring up to level
            capture_output=True
        )
        return f"Volume set to approximately {level}%."
    except Exception as e:
        return f"Couldn't set volume: {e}"

def media_play_pause() -> str:
    subprocess.run(["powershell", "-command",
        "(New-Object -ComObject WScript.Shell).SendKeys([char]179)"])
    return "Toggled play/pause."

def media_next() -> str:
    subprocess.run(["powershell", "-command",
        "(New-Object -ComObject WScript.Shell).SendKeys([char]176)"])
    return "Skipped to next track."

def media_previous() -> str:
    subprocess.run(["powershell", "-command",
        "(New-Object -ComObject WScript.Shell).SendKeys([char]177)"])
    return "Went to previous track."

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
    import datetime
    filename = os.path.join(os.path.expanduser("~"), "Desktop",
               f"screenshot_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
    subprocess.run(["powershell", "-command",
        f"Add-Type -AssemblyName System.Windows.Forms,System.Drawing; "
        f"$s=[System.Windows.Forms.Screen]::PrimaryScreen.Bounds; "
        f"$b=New-Object System.Drawing.Bitmap $s.Width,$s.Height; "
        f"$g=[System.Drawing.Graphics]::FromImage($b); "
        f"$g.CopyFromScreen($s.Location,[System.Drawing.Point]::Empty,$s.Size); "
        f"$b.Save('{filename}')"], capture_output=True)
    return f"Screenshot saved to Desktop."