"""
Audio playback manager for PupuSnipe.
Supports Windows native MCI (Media Control Interface) for MP3/WAV playback
with zero external dependencies and zero-overhead non-blocking execution.
"""
import os
import sys
import threading
import ctypes
import winsound
from typing import Dict, List, Tuple, Optional

# Registry of built-in sound effects
BUILTIN_SOUNDS: Dict[str, Tuple[str, str]] = {
    "vine_boom": ("Vine Boom (Meme)", "vine_boom.mp3"),
    "metal_pipe": ("Metal Pipe Falling (Meme)", "metal_pipe.mp3"),
    "taco_bell": ("Taco Bell Bong (Meme)", "taco_bell.mp3"),
    "roblox_oof": ("Roblox Classic Oof (Meme)", "roblox_oof.mp3"),
    "anime_wow": ("Anime Wow! (Meme)", "anime_wow.mp3"),
    "mlg_airhorn": ("MLG Airhorn (Meme)", "mlg_airhorn.mp3"),
    "bruh": ("Bruh (Meme)", "bruh.mp3"),
    "discord_ping": ("Discord Notification", "discord_ping.mp3"),
    "windows_error": ("Windows XP Error", "windows_error.mp3"),
    "bonk": ("Bonk / Bat (Meme)", "bonk.mp3"),
    "among_us": ("Among Us (Meme)", "among_us.mp3"),
    "default": ("Default Windows Chime", ""),
    "custom": ("Custom Audio File (.mp3 / .wav)...", "")
}

_mci_lock = threading.Lock()
_mci_counter = 0


def _get_sounds_dir() -> str:
    """Returns the absolute path to the assets/sounds directory."""
    if getattr(sys, "frozen", False):
        if hasattr(sys, "_MEIPASS"):
            for candidate in [
                os.path.join(sys._MEIPASS, "pupusnipe", "assets", "sounds"),
                os.path.join(sys._MEIPASS, "assets", "sounds"),
            ]:
                if os.path.isdir(candidate):
                    return candidate
        # Also check relative to executable / _internal
        exe_dir = os.path.dirname(sys.executable)
        for candidate in [
            os.path.join(exe_dir, "_internal", "pupusnipe", "assets", "sounds"),
            os.path.join(exe_dir, "_internal", "assets", "sounds"),
            os.path.join(exe_dir, "pupusnipe", "assets", "sounds"),
            os.path.join(exe_dir, "assets", "sounds"),
        ]:
            if os.path.isdir(candidate):
                return candidate

    # Development / local directory
    curr_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(curr_dir, "assets", "sounds")


def get_available_sounds() -> List[Tuple[str, str]]:
    """Returns list of (key, display_name) for UI dropdowns."""
    return [(k, v[0]) for k, v in BUILTIN_SOUNDS.items()]


def resolve_sound_path(sound_key: str, custom_path: str = "") -> Optional[str]:
    """Resolves sound key or custom path to an existing absolute file path."""
    if sound_key == "custom":
        if custom_path and os.path.isfile(custom_path):
            return os.path.abspath(custom_path)
        return None

    if sound_key == "default" or sound_key not in BUILTIN_SOUNDS:
        return None

    fname = BUILTIN_SOUNDS[sound_key][1]
    if not fname:
        return None

    target = os.path.join(_get_sounds_dir(), fname)
    if os.path.isfile(target):
        return target

    return None


def _play_mci(file_path: str, volume: int = 100):
    """Plays an audio file via Windows winmm.dll mciSendStringW."""
    global _mci_counter
    try:
        winmm = ctypes.windll.winmm
        with _mci_lock:
            _mci_counter = (_mci_counter + 1) % 1000
            alias = f"ps_sfx_{_mci_counter}"

        clean_path = file_path.replace("\\", "/")
        # Determine device type
        lower_path = clean_path.lower()
        dev_type = "mpegvideo" if lower_path.endswith(".mp3") else "waveaudio"

        # Close any previous instance of this alias
        winmm.mciSendStringW(f'close {alias}', None, 0, 0)

        # Open
        open_cmd = f'open "{clean_path}" type {dev_type} alias {alias}'
        res = winmm.mciSendStringW(open_cmd, None, 0, 0)
        if res != 0:
            # Fallback open without explicit type
            winmm.mciSendStringW(f'open "{clean_path}" alias {alias}', None, 0, 0)

        # Set Volume (0 to 1000 in MCI)
        scaled_vol = max(0, min(1000, int(volume * 10)))
        winmm.mciSendStringW(f'setaudio {alias} volume to {scaled_vol}', None, 0, 0)

        # Play
        winmm.mciSendStringW(f'play {alias}', None, 0, 0)
    except Exception:
        # Ultimate fallback
        try:
            winsound.MessageBeep(winsound.MB_ICONASTERISK)
        except Exception:
            pass


def play_sound(sound_key: str = "vine_boom", custom_path: str = "", volume: int = 100):
    """
    Plays the specified sound effect asynchronously in a daemon thread.
    Never blocks caller thread or network operations.
    """
    def _worker():
        if sound_key == "default":
            try:
                winsound.MessageBeep(winsound.MB_ICONASTERISK)
            except Exception:
                pass
            return

        resolved = resolve_sound_path(sound_key, custom_path)
        if resolved and os.path.isfile(resolved):
            _play_mci(resolved, volume)
        else:
            try:
                winsound.MessageBeep(winsound.MB_ICONASTERISK)
            except Exception:
                pass

    t = threading.Thread(target=_worker, name="AudioSFXThread", daemon=True)
    t.start()
