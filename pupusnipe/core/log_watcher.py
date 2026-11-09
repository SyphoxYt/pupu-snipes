"""
Roblox & Bloxstrap Log Watcher
Monitors Roblox log files in real-time to detect current in-game biome and equipped aura (inspired by FishSol v2.1).
"""
import os
import re
import time
import threading
from typing import Optional, Callable
from .logger import get_logger

import json

logger = get_logger()

RE_RPC = re.compile(
    r'"state":\s*"((?:\\.|[^"])*)".*?"largeImage":\s*\{\s*"hoverText":\s*"((?:\\.|[^"])*)"',
    re.IGNORECASE
)
RE_HOVER = re.compile(r'"largeImage":\s*\{\s*"hoverText":\s*"((?:\\.|[^"])*)"', re.IGNORECASE)
RE_STATE = re.compile(r'"state":\s*"((?:\\.|[^"])*)"', re.IGNORECASE)


class RobloxLogWatcher:
    """Watches Roblox, Voidstrap, and Bloxstrap logs for RPC biome & aura events."""

    def __init__(
        self,
        on_biome_change: Optional[Callable[[str], None]] = None,
        on_aura_change: Optional[Callable[[str], None]] = None
    ):
        self.on_biome_change = on_biome_change
        self.on_aura_change = on_aura_change

        self.current_biome = "Unknown"
        self.current_aura = "None"

        self._is_running = False
        self._thread: Optional[threading.Thread] = None
        self._last_log_file = ""
        self._last_mtime = 0.0

    def start(self):
        if self._is_running:
            return
        self._is_running = True
        self._thread = threading.Thread(target=self._watch_loop, daemon=True, name="RobloxLogWatcher")
        self._thread.start()

    def stop(self):
        self._is_running = False

    def _get_candidate_log_dirs(self) -> list:
        dirs = []
        local_app = os.environ.get("LOCALAPPDATA", "")
        if local_app:
            dirs.append(os.path.join(local_app, "Roblox", "logs"))
            dirs.append(os.path.join(local_app, "Voidstrap", "Logs"))
            dirs.append(os.path.join(local_app, "Bloxstrap", "Logs"))
        
        # User Voidstrap installation
        dirs.append(r"D:\Void Strap 67\Logs")

        temp_dir = os.environ.get("TEMP", "")
        if temp_dir:
            dirs.append(os.path.join(temp_dir, "Voidstrap"))

        return [d for d in dirs if os.path.isdir(d)]

    def _get_latest_log_file(self) -> Optional[str]:
        best_file = None
        best_mtime = 0.0

        for log_dir in self._get_candidate_log_dirs():
            try:
                for fname in os.listdir(log_dir):
                    if fname.endswith(".log"):
                        full = os.path.join(log_dir, fname)
                        try:
                            mtime = os.path.getmtime(full)
                            if mtime > best_mtime:
                                best_mtime = mtime
                                best_file = full
                        except OSError:
                            continue
            except Exception:
                continue

        return best_file

    def _watch_loop(self):
        while self._is_running:
            try:
                log_file = self._get_latest_log_file()
                if log_file and os.path.exists(log_file):
                    mtime = os.path.getmtime(log_file)
                    if log_file != self._last_log_file or mtime > self._last_mtime:
                        self._last_log_file = log_file
                        self._last_mtime = mtime
                        self._read_log_tail(log_file)
            except Exception:
                pass
            time.sleep(0.8)

    def _read_log_tail(self, filepath: str, chunk_size: int = 32768):
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                f.seek(0, os.SEEK_END)
                size = f.tell()
                f.seek(max(0, size - chunk_size), os.SEEK_SET)
                content = f.read()

            lines = content.splitlines()
            # Scan in reverse for newest RPC line
            for line in reversed(lines):
                if "[BloxstrapRPC]" in line or "[VoidstrapRPC]" in line or "largeImage" in line:
                    biome_match = RE_HOVER.search(line)
                    state_match = RE_STATE.search(line)

                    if biome_match:
                        biome_clean = biome_match.group(1).strip().upper()
                        if biome_clean and biome_clean != self.current_biome:
                            self.current_biome = biome_clean
                            logger.info(f"[Biome Watcher] Biome Detected: {self.current_biome} (from {os.path.basename(filepath)})")
                            if self.on_biome_change:
                                self.on_biome_change(self.current_biome)

                    if state_match:
                        state_val = state_match.group(1)
                        aura_clean = state_val.replace("Equipped", "").replace('"', '').replace('\\', '').strip()
                        if aura_clean and aura_clean != self.current_aura and aura_clean != "_None_":
                            self.current_aura = aura_clean
                            logger.info(f"[Aura Watcher] Equipped Aura: {self.current_aura}")
                            if self.on_aura_change:
                                self.on_aura_change(self.current_aura)

                    if biome_match or state_match:
                        break
        except Exception:
            pass
