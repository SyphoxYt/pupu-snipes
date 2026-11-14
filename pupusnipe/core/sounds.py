"""
PupuSnipe Snipe Sound Engine
Bundled, dependency-free WAV sound effects for the "link sniped" alert.

The library is synthesized locally at 44.1 kHz / 16-bit mono so the app ships with
meme-style variety without bundling copyrighted audio clips or adding playback
dependencies. Users can also select their own .wav file from the Misc tab.
"""
from __future__ import annotations

import math
import os
import random
import wave
from array import array
from typing import Dict, List, Optional

try:
    import winsound  # Windows-only; guarded so tests and imports work cross-platform
except Exception:  # pragma: no cover - non-Windows
    winsound = None

SAMPLE_RATE = 44100
DEFAULT_SOUND_ID = "chime"
SYSTEM_BEEP_ID = "system_beep"
CUSTOM_SOUND_ID = "custom"

# Ordered list shown in the UI. "file" is relative to pupusnipe/assets/sounds.
SOUND_PRESETS: List[Dict[str, str]] = [
    {"id": "chime", "name": "✨ Pupu Chime (Default)", "file": "chime.wav", "description": "Clean four-note victory chime"},
    {"id": "vine_boom", "name": "💥 Vine Boom", "file": "vine_boom.wav", "description": "Deep cinematic meme boom"},
    {"id": "bruh", "name": "😐 Bruh", "file": "bruh.wav", "description": "Low descending bruh buzz"},
    {"id": "airhorn", "name": "📢 Airhorn", "file": "airhorn.wav", "description": "Triple blast hype horn"},
    {"id": "among_us", "name": "🚨 Among Us", "file": "among_us.wav", "description": "Urgent emergency-meeting alarm"},
    {"id": "rizz", "name": "💫 Rizz", "file": "rizz.wav", "description": "Sparkly ascending rizz flourish"},
    {"id": "emotional_damage", "name": "🎻 Emotional Damage", "file": "emotional_damage.wav", "description": "Dramatic descending sting"},
    {"id": "metal_pipe", "name": "🔧 Metal Pipe", "file": "metal_pipe.wav", "description": "Clanging metal pipe meme"},
    {"id": "nope", "name": "🙅 Nope", "file": "nope.wav", "description": "Fast two-syllable nope"},
    {"id": "sad_violin", "name": "🎻 Sad Violin", "file": "sad_violin.wav", "description": "Melancholic minor chord"},
    {"id": "coin", "name": "🪙 Coin", "file": "coin.wav", "description": "Retro coin pickup"},
]

_PRESET_BY_ID = {p["id"]: p for p in SOUND_PRESETS}


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
def get_sound_dir() -> str:
    """Returns the bundled sound directory in both source and PyInstaller builds."""
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(os.path.dirname(here), "assets", "sounds")


def get_preset_file(preset_id: str) -> Optional[str]:
    preset = _PRESET_BY_ID.get(str(preset_id))
    if not preset:
        return None
    return os.path.join(get_sound_dir(), preset["file"])


def get_preset(preset_id: str) -> Optional[Dict[str, str]]:
    return _PRESET_BY_ID.get(str(preset_id))


def get_preset_label(preset_id: str) -> str:
    if preset_id == SYSTEM_BEEP_ID:
        return "🔔 Windows System Beep"
    if preset_id == CUSTOM_SOUND_ID:
        return "📂 Custom WAV file…"
    preset = get_preset(preset_id)
    return preset["name"] if preset else "Unknown sound"


# ---------------------------------------------------------------------------
# Tiny synthesizer helpers
# ---------------------------------------------------------------------------
def _osc(kind: str, phase: float) -> float:
    if kind == "square":
        return 1.0 if math.sin(phase) >= 0.0 else -1.0
    if kind == "saw":
        return 2.0 * ((phase / (2.0 * math.pi)) % 1.0) - 1.0
    if kind == "triangle":
        return 2.0 * abs(2.0 * ((phase / (2.0 * math.pi)) % 1.0) - 1.0) - 1.0
    return math.sin(phase)


def _envelope(progress: float, duration: float, attack: float, release: float) -> float:
    attack = max(0.0005, min(attack, duration * 0.45))
    release = max(0.0005, min(release, duration * 0.95))
    if progress < attack / duration:
        return progress * duration / attack
    if progress > 1.0 - release / duration:
        return max(0.0, (1.0 - progress) * duration / release)
    return 1.0


def _tone(
    duration: float,
    freq_start: float,
    freq_end: Optional[float] = None,
    wave: str = "sine",
    volume: float = 0.5,
    attack: float = 0.005,
    release: float = 0.08,
    vibrato_hz: float = 0.0,
    vibrato_depth: float = 0.0,
    tremolo_hz: float = 0.0,
    harmonics: Optional[List[tuple]] = None,
) -> List[float]:
    n = max(1, int(SAMPLE_RATE * duration))
    out: List[float] = []
    phase = 0.0
    for i in range(n):
        progress = i / (n - 1) if n > 1 else 0.0
        freq = freq_start if freq_end is None else freq_start + (freq_end - freq_start) * progress
        if vibrato_hz:
            freq *= 1.0 + vibrato_depth * math.sin(2.0 * math.pi * vibrato_hz * (i / SAMPLE_RATE))
        phase += 2.0 * math.pi * max(20.0, freq) / SAMPLE_RATE
        sample = _osc(wave, phase)
        if harmonics:
            for mult, amp in harmonics:
                sample += amp * math.sin(phase * mult)
        env = _envelope(progress, duration, attack, release)
        if tremolo_hz:
            env *= 0.78 + 0.22 * math.sin(2.0 * math.pi * tremolo_hz * (i / SAMPLE_RATE))
        out.append(sample * volume * env)
    return out


def _noise(duration: float, volume: float = 0.2, attack: float = 0.001, release: float = 0.2, seed: int = 1) -> List[float]:
    n = max(1, int(SAMPLE_RATE * duration))
    rng = random.Random(seed)
    out: List[float] = []
    for i in range(n):
        progress = i / (n - 1) if n > 1 else 0.0
        out.append(rng.uniform(-1.0, 1.0) * volume * _envelope(progress, duration, attack, release))
    return out


def _mix(*tracks: List[float]) -> List[float]:
    length = max((len(t) for t in tracks), default=0)
    out = [0.0] * length
    for track in tracks:
        for i, value in enumerate(track):
            out[i] += value
    return out


def _overlay(parts: List[tuple]) -> List[float]:
    """parts = [(samples, offset_seconds), ...]"""
    length = max((int(off * SAMPLE_RATE) + len(track) for track, off in parts), default=0)
    out = [0.0] * length
    for track, offset in parts:
        start = int(offset * SAMPLE_RATE)
        for i, value in enumerate(track):
            if start + i < length:
                out[start + i] += value
    return out


def _master(track: List[float], peak: float = 0.9) -> List[float]:
    highest = max((abs(v) for v in track), default=0.0)
    if highest <= 0.00001:
        return track
    gain = peak / highest
    return [max(-1.0, min(1.0, v * gain)) for v in track]


def _write_wav(path: str, samples: List[float]):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    pcm = array("h", (int(max(-1.0, min(1.0, s)) * 32767) for s in samples))
    with wave.open(path, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(SAMPLE_RATE)
        handle.writeframes(pcm.tobytes())


# ---------------------------------------------------------------------------
# Sound recipes
# ---------------------------------------------------------------------------
def _build_chime() -> List[float]:
    notes = [(1046.50, 0.00, 0.30), (1318.51, 0.13, 0.30), (1567.98, 0.26, 0.34), (2093.00, 0.41, 0.62)]
    parts = []
    for freq, offset, duration in notes:
        parts.append((
            _tone(duration, freq, wave="sine", volume=0.55, attack=0.004, release=duration * 0.82,
                  harmonics=[(2.0, 0.32), (3.0, 0.15), (4.2, 0.06)]),
            offset,
        ))
    return _overlay(parts)


def _build_vine_boom() -> List[float]:
    return _mix(
        _tone(0.95, 120.0, 36.0, "sine", 0.95, attack=0.002, release=0.9),
        _tone(0.70, 240.0, 74.0, "triangle", 0.35, attack=0.002, release=0.65),
        _tone(0.90, 60.0, 28.0, "sine", 0.5, attack=0.004, release=0.88),
        _noise(0.06, 0.35, seed=3),
    )


def _build_bruh() -> List[float]:
    return _mix(
        _tone(0.52, 185.0, 88.0, "saw", 0.42, attack=0.008, release=0.3,
              vibrato_hz=8.0, vibrato_depth=0.02),
        _tone(0.52, 92.0, 44.0, "square", 0.22, attack=0.008, release=0.3),
        _noise(0.10, 0.06, release=0.09, seed=11),
    )


def _build_airhorn() -> List[float]:
    def blast(duration: float) -> List[float]:
        return _mix(
            _tone(duration, 466.0, wave="saw", volume=0.30, attack=0.008, release=0.04,
                  vibrato_hz=24.0, vibrato_depth=0.012),
            _tone(duration, 587.0, wave="saw", volume=0.20, attack=0.008, release=0.04,
                  vibrato_hz=19.0, vibrato_depth=0.012),
            _tone(duration, 698.0, wave="square", volume=0.10, attack=0.008, release=0.04),
        )

    return _overlay([
        (blast(0.14), 0.00),
        (blast(0.14), 0.20),
        (blast(0.14), 0.40),
        (blast(0.62), 0.60),
    ])


def _build_among_us() -> List[float]:
    parts = []
    for i in range(4):
        offset = i * 0.21
        parts.append((_tone(0.11, 880.0, wave="square", volume=0.32, attack=0.004, release=0.04), offset))
        parts.append((_tone(0.10, 660.0, wave="square", volume=0.30, attack=0.004, release=0.04), offset + 0.105))
    return _overlay(parts)


def _build_rizz() -> List[float]:
    notes = [(783.99, 0.00), (1046.50, 0.07), (1318.51, 0.14), (1567.98, 0.21), (2093.00, 0.29)]
    parts = []
    for freq, offset in notes:
        parts.append((
            _tone(0.34, freq, wave="sine", volume=0.44, attack=0.003, release=0.28,
                  harmonics=[(2.0, 0.25), (3.0, 0.10)]),
            offset,
        ))
    shimmer = _noise(0.55, 0.035, attack=0.05, release=0.48, seed=21)
    parts.append((shimmer, 0.05))
    return _overlay(parts)


def _build_emotional_damage() -> List[float]:
    return _mix(
        _tone(1.15, 720.0, 150.0, "saw", 0.50, attack=0.02, release=0.45,
              vibrato_hz=5.5, vibrato_depth=0.028, tremolo_hz=7.0,
              harmonics=[(2.0, 0.20), (3.0, 0.08)]),
        _tone(1.15, 360.0, 75.0, "triangle", 0.24, attack=0.02, release=0.45,
              vibrato_hz=5.5, vibrato_depth=0.025),
    )


def _build_metal_pipe() -> List[float]:
    parts = [
        (_noise(0.50, 0.22, attack=0.001, release=0.45, seed=7), 0.0),
        (_tone(0.26, 95.0, 52.0, "sine", 0.35, attack=0.002, release=0.23), 0.0),
    ]
    for freq, offset, volume in [(523.0, 0.0, 0.16), (781.5, 0.008, 0.14),
                                 (1129.0, 0.016, 0.11), (1620.0, 0.026, 0.08),
                                 (2489.0, 0.036, 0.05)]:
        parts.append((
            _tone(0.72, freq, wave="sine", volume=volume, attack=0.001, release=0.70,
                  harmonics=[(2.7, 0.28), (4.1, 0.18)]),
            offset,
        ))
    return _overlay(parts)


def _build_nope() -> List[float]:
    return _overlay([
        (_tone(0.16, 720.0, 430.0, "square", 0.28, attack=0.004, release=0.10), 0.00),
        (_tone(0.26, 430.0, 210.0, "square", 0.30, attack=0.004, release=0.20), 0.18),
    ])


def _build_sad_violin() -> List[float]:
    parts = []
    for freq in (440.0, 523.25, 659.25):
        parts.append((
            _tone(1.55, freq, wave="saw", volume=0.17, attack=0.18, release=0.65,
                  vibrato_hz=5.0, vibrato_depth=0.010,
                  harmonics=[(2.0, 0.18), (3.0, 0.07)]),
            0.0,
        ))
    return _overlay(parts)


def _build_coin() -> List[float]:
    return _overlay([
        (_tone(0.09, 987.77, wave="square", volume=0.30, attack=0.002, release=0.05), 0.00),
        (_tone(0.42, 1318.51, wave="square", volume=0.28, attack=0.002, release=0.36), 0.085),
    ])


_BUILDERS = {
    "chime": _build_chime,
    "vine_boom": _build_vine_boom,
    "bruh": _build_bruh,
    "airhorn": _build_airhorn,
    "among_us": _build_among_us,
    "rizz": _build_rizz,
    "emotional_damage": _build_emotional_damage,
    "metal_pipe": _build_metal_pipe,
    "nope": _build_nope,
    "sad_violin": _build_sad_violin,
    "coin": _build_coin,
}


def build_sound(preset_id: str) -> List[float]:
    """Synthesizes one preset and returns normalized float samples."""
    builder = _BUILDERS.get(str(preset_id))
    if not builder:
        raise KeyError(f"Unknown sound preset: {preset_id}")
    return _master(builder(), peak=0.9)


def generate_sound_library(directory: Optional[str] = None, force: bool = False) -> Dict[str, str]:
    """Writes every bundled preset to disk. Returns {preset_id: path}."""
    target_dir = directory or get_sound_dir()
    os.makedirs(target_dir, exist_ok=True)
    written: Dict[str, str] = {}
    for preset in SOUND_PRESETS:
        path = os.path.join(target_dir, preset["file"])
        if force or not os.path.isfile(path) or os.path.getsize(path) < 44:
            _write_wav(path, build_sound(preset["id"]))
        written[preset["id"]] = path
    return written


def ensure_preset_file(preset_id: str) -> Optional[str]:
    """Ensures a bundled preset exists on disk, generating it on demand if needed."""
    path = get_preset_file(preset_id)
    if not path:
        return None
    if not os.path.isfile(path) or os.path.getsize(path) < 44:
        preset = get_preset(preset_id)
        if not preset:
            return None
        try:
            _write_wav(path, build_sound(preset_id))
        except Exception:
            return None
    return path


# ---------------------------------------------------------------------------
# Playback
# ---------------------------------------------------------------------------
class SoundManager:
    """Plays the selected snipe sound asynchronously via winsound."""

    def __init__(self, preset_id: str = DEFAULT_SOUND_ID, custom_path: str = ""):
        self.preset_id = preset_id or DEFAULT_SOUND_ID
        self.custom_path = custom_path or ""
        self.last_error = ""

    def set_selection(self, preset_id: Optional[str] = None, custom_path: Optional[str] = None):
        if preset_id is not None:
            self.preset_id = str(preset_id) or DEFAULT_SOUND_ID
        if custom_path is not None:
            self.custom_path = str(custom_path)

    def active_file(self) -> Optional[str]:
        if self.preset_id == CUSTOM_SOUND_ID:
            path = self.custom_path.strip().strip('"')
            if path and os.path.isfile(path) and path.lower().endswith(".wav"):
                return path
            return None
        if self.preset_id in (SYSTEM_BEEP_ID, ""):
            return None
        return ensure_preset_file(self.preset_id)

    def play(self) -> bool:
        """Starts playback without blocking. Returns True when a sound was dispatched."""
        self.last_error = ""
        try:
            if winsound is None:
                self.last_error = "winsound is unavailable on this platform"
                return False

            if self.preset_id == SYSTEM_BEEP_ID:
                winsound.MessageBeep(winsound.MB_ICONASTERISK)
                return True

            path = self.active_file()
            if not path:
                self.last_error = "Selected custom WAV file is missing; using system beep"
                winsound.MessageBeep(winsound.MB_ICONASTERISK)
                return False

            flags = winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT
            winsound.PlaySound(path, flags)
            return True
        except Exception as exc:
            self.last_error = str(exc)
            try:
                if winsound is not None:
                    winsound.MessageBeep(winsound.MB_ICONASTERISK)
            except Exception:
                pass
            return False

    def stop(self):
        """Stops any sound currently playing."""
        try:
            if winsound is not None:
                winsound.PlaySound(None, winsound.SND_PURGE)
        except Exception:
            pass

    def describe(self) -> str:
        if self.preset_id == CUSTOM_SOUND_ID:
            if self.custom_path and os.path.isfile(self.custom_path) and self.custom_path.lower().endswith(".wav"):
                return f"Custom: {os.path.basename(self.custom_path)}"
            return "Custom WAV (no file selected)"
        return get_preset_label(self.preset_id)


# Generate the library once when this module is executed directly, e.g.
#   python -m pupusnipe.core.sounds
if __name__ == "__main__":  # pragma: no cover
    files = generate_sound_library(force=True)
    print(f"Generated {len(files)} sound files in {get_sound_dir()}")
    for sound_id, path in files.items():
        print(f"  {sound_id:18s} -> {path} ({os.path.getsize(path):,} bytes)")
