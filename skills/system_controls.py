import subprocess
import os
import platform

def set_volume(level: int) -> str:
    """Set volume 0-100 on Windows"""
    level = max(0, min(100, level))
    script = f"""
    $obj = New-Object -com wscript.shell
    $obj.SendKeys([char]173)  # mute toggle reset
    Add-Type -TypeDefinition @'
    using System.Runtime.InteropServices;
    [Guid("5CDF2C82-841E-4546-9722-0CF74078229A"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    interface IAudioEndpointVolume {{ int f(); int g(); int h(); int i(); int SetMasterVolumeLevelScalar(float fLevel, System.Guid pguidEventContext); }}
    [Guid("BCDE0395-E52F-467C-8E3D-C4579291692E"), ClassInterface(ClassInterfaceType.None)]
    class MMDeviceEnumerator {{}}
'@
    """
    try:
        subprocess.run(
            ["powershell", "-command",
             f"$wshShell = New-Object -ComObject WScript.Shell; "
             f"[audio]::Volume = {level/100}"],
            capture_output=True
        )
        subprocess.run(
            ["powershell", "-command",
             f"(Get-WmiObject -Namespace root/cimv2 -Class Win32_Volume) | ForEach-Object {{$_.SetVolume({level/100})}}"],
            capture_output=True
        )
        return f"Volume set to {level}%."
    except Exception as e:
        return f"Couldn't set volume: {e}"

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

def shutdown(delay: int = 0) -> str:
    os.system(f"shutdown /s /t {delay}")
    return f"Shutting down in {delay} seconds."

def restart() -> str:
    os.system("shutdown /r /t 0")
    return "Restarting..."

def sleep_pc() -> str:
    os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
    return "Going to sleep."

def get_battery() -> str:
    result = subprocess.run(
        ["powershell", "-command", "(Get-WmiObject Win32_Battery).EstimatedChargeRemaining"],
        capture_output=True, text=True
    )
    level = result.stdout.strip()
    return f"Battery is at {level}%." if level else "Couldn't read battery level."

def take_screenshot() -> str:
    import datetime
    filename = f"screenshot_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    subprocess.run(["powershell", "-command",
        f"Add-Type -AssemblyName System.Windows.Forms; "
        f"[System.Windows.Forms.Screen]::PrimaryScreen | ForEach-Object {{"
        f"$bmp = New-Object System.Drawing.Bitmap($_.Bounds.Width, $_.Bounds.Height);"
        f"$g = [System.Drawing.Graphics]::FromImage($bmp);"
        f"$g.CopyFromScreen($_.Bounds.Location, [System.Drawing.Point]::Empty, $_.Bounds.Size);"
        f"$bmp.Save('{filename}')}}"])
    return f"Screenshot saved as {filename}."