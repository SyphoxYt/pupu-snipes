"""
FishSol Python Engine (Converted and Enhanced from FishSol v2.1)
High-precision Sol's RNG auto-fishing, selling path, collection navigation, and biome camping engine.
"""
import os
import sys
import time
import ctypes
from ctypes import wintypes
import threading
import subprocess
from typing import Optional, Callable, Dict, Any
from .logger import get_logger

logger = get_logger()

# Windows API constants
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_WHEEL = 0x0800
KEYEVENTF_KEYUP = 0x0002

# Virtual Key Codes
VK_ESCAPE = 0x1B
VK_RETURN = 0x0D
VK_SPACE = 0x20
VK_KEY_W = 0x57
VK_KEY_A = 0x41
VK_KEY_S = 0x53
VK_KEY_D = 0x44
VK_KEY_E = 0x45
VK_KEY_R = 0x52
VK_KEY_O = 0x4F


class ScreenDC:
    """Context manager for acquiring and releasing Screen Device Context safely."""
    def __enter__(self):
        self.hdc = ctypes.windll.user32.GetDC(0) if sys.platform == "win32" else 0
        return self.hdc

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.hdc and sys.platform == "win32":
            ctypes.windll.user32.ReleaseDC(0, self.hdc)


class Win32Automation:
    """Low-level Windows automation for sub-millisecond precision input and pixel inspection."""

    @staticmethod
    def set_mouse_pos(x: int, y: int):
        if sys.platform == "win32":
            ctypes.windll.user32.SetCursorPos(int(x), int(y))

    @staticmethod
    def mouse_click(button: str = "left", delay_ms: int = 40):
        if sys.platform != "win32":
            return
        user32 = ctypes.windll.user32
        if button == "left":
            user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            time.sleep(delay_ms / 1000.0)
            user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)

    @staticmethod
    def mouse_move_and_click(x: int, y: int, delay_before: int = 150, delay_after: int = 150):
        Win32Automation.set_mouse_pos(x, y)
        time.sleep(delay_before / 1000.0)
        Win32Automation.mouse_click("left")
        time.sleep(delay_after / 1000.0)

    @staticmethod
    def mouse_wheel(delta: int):
        if sys.platform == "win32":
            ctypes.windll.user32.mouse_event(MOUSEEVENTF_WHEEL, 0, 0, delta, 0)

    @staticmethod
    def key_down(vk_code: int):
        if sys.platform == "win32":
            ctypes.windll.user32.keybd_event(vk_code, 0, 0, 0)

    @staticmethod
    def key_up(vk_code: int):
        if sys.platform == "win32":
            ctypes.windll.user32.keybd_event(vk_code, 0, KEYEVENTF_KEYUP, 0)

    @staticmethod
    def press_key(vk_code: int, hold_ms: int = 80):
        Win32Automation.key_down(vk_code)
        time.sleep(hold_ms / 1000.0)
        Win32Automation.key_up(vk_code)

    @staticmethod
    def get_pixel_color(x: int, y: int, hdc: Optional[int] = None) -> int:
        """Returns 0xRRGGBB integer color of screen pixel."""
        if sys.platform != "win32":
            return 0
        should_release = False
        if not hdc:
            hdc = ctypes.windll.user32.GetDC(0)
            should_release = True
        try:
            color = ctypes.windll.gdi32.GetPixel(hdc, int(x), int(y))
            r = color & 0xFF
            g = (color >> 8) & 0xFF
            b = (color >> 16) & 0xFF
            return (r << 16) | (g << 8) | b
        finally:
            if should_release and hdc:
                ctypes.windll.user32.ReleaseDC(0, hdc)

    @staticmethod
    def pixel_search_line(x1: int, x2: int, y: int, target_rgb: int, tolerance: int = 12) -> Optional[int]:
        """Ultra-fast horizontal scanline pixel search (as used in FishSol v2.1)."""
        if sys.platform != "win32":
            return None
        target_r = (target_rgb >> 16) & 0xFF
        target_g = (target_rgb >> 8) & 0xFF
        target_b = target_rgb & 0xFF

        with ScreenDC() as hdc:
            step = 3
            for x in range(x1, x2, step):
                c = ctypes.windll.gdi32.GetPixel(hdc, x, y)
                r = c & 0xFF
                g = (c >> 8) & 0xFF
                b = (c >> 16) & 0xFF
                if abs(r - target_r) <= tolerance and abs(g - target_g) <= tolerance and abs(b - target_b) <= tolerance:
                    return x
        return None

    @staticmethod
    def activate_roblox_window() -> bool:
        """Finds and brings the Roblox window to foreground via EnumWindows."""
        if sys.platform != "win32":
            return False

        user32 = ctypes.windll.user32
        found_hwnd = [0]

        WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

        def enum_cb(hwnd, lparam):
            if user32.IsWindowVisible(hwnd):
                length = user32.GetWindowTextLengthW(hwnd)
                if length > 0:
                    buff = ctypes.create_unicode_buffer(length + 1)
                    user32.GetWindowTextW(hwnd, buff, length + 1)
                    title = buff.value
                    if "Roblox" in title and "Studio" not in title:
                        found_hwnd[0] = hwnd
                        return False
            return True

        user32.EnumWindows(WNDENUMPROC(enum_cb), 0)

        if found_hwnd[0]:
            user32.ShowWindow(found_hwnd[0], 9)  # SW_RESTORE
            user32.SetForegroundWindow(found_hwnd[0])
            return True

        return False


class FishSolEngine:
    """
    Direct implementation of FishSol v2.1 Macro in Python.
    Includes auto-selling path, collection navigation, and minigame catching loop.
    """

    def __init__(
        self,
        on_status_change: Optional[Callable[[str], None]] = None,
        on_stats_update: Optional[Callable[[Dict[str, Any]], None]] = None
    ):
        self.on_status_change = on_status_change
        self.on_stats_update = on_stats_update

        # Settings
        self.is_running = False
        self.is_paused = False
        self.pathing_mode = "Vip Pathing"  # "Vip Pathing", "Non Vip Pathing", "Abyssal Pathing"
        self.resolution = "1080p"          # "1080p", "1440p", "1366x768"
        self.sell_all = True
        self.fishing_loop_count = 15       # Cycles before selling
        self.sell_loop_count = 56
        self.auto_fish_on_join = False
        self.join_delay_sec = 12           # Seconds to wait for server loading
        self.stay_in_target_biome = True   # Keeps fishing in target biome without hopping
        self.camping_target_biome = "CORRUPTION"  # Target biome to lock onto and camp indefinitely

        # Statistics
        self.fish_caught = 0
        self.cycles_completed = 0
        self.total_sells = 0

        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._auto: Win32Automation = Win32Automation()

    def set_status(self, text: str):
        logger.info(f"[FishSol] {text}")
        if self.on_status_change:
            self.on_status_change(text)

    def _emit_stats(self):
        if self.on_stats_update:
            self.on_stats_update({
                "fish_caught": self.fish_caught,
                "cycles_completed": self.cycles_completed,
                "total_sells": self.total_sells,
                "is_running": self.is_running,
                "is_paused": self.is_paused
            })

    def start(self):
        """Starts the fishing loop thread."""
        if self.is_running:
            return
        self.is_running = True
        self.is_paused = False
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._macro_loop, daemon=True, name="FishSolMacroThread")
        self._thread.start()
        self.set_status("FishSol Macro Started")
        self._emit_stats()

    def pause(self):
        self.is_paused = True
        self.set_status("FishSol Macro Paused")
        self._emit_stats()

    def resume(self):
        self.is_paused = False
        self.set_status("FishSol Macro Resumed")
        self._emit_stats()

    def stop(self):
        self.is_running = False
        self.is_paused = False
        self._stop_event.set()
        self.set_status("FishSol Macro Stopped")
        self._emit_stats()

    def trigger_join_sequence_async(self, biome_name: str = ""):
        """Triggered automatically when PupuSnipe snipes and joins a server."""
        if not self.auto_fish_on_join:
            return
        threading.Thread(target=self._run_server_join_workflow, args=(biome_name,), daemon=True).start()

    def _run_server_join_workflow(self, biome_name: str):
        """Waits for Roblox loading screen, then executes collection + selling path + fishing loop."""
        self.set_status(f"Server joined ({biome_name}). Waiting {self.join_delay_sec}s for Roblox to load...")
        time.sleep(self.join_delay_sec)

        if not self.is_running:
            return

        self._auto.activate_roblox_window()
        time.sleep(1.0)

        # 1. Reset character
        self.reset_character()

        # 2. Collection & Equip
        self.open_collection_and_equip()

        # 3. Pathing & Sell
        self.execute_selling_path()

        # 4. Resume continuous fishing loop
        self.set_status(f"Fishing active in {biome_name or 'server'}!")

    def reset_character(self):
        """Esc -> R -> Enter (Standard Roblox reset)."""
        self.set_status("Resetting character...")
        self._auto.press_key(VK_ESCAPE, 80)
        time.sleep(0.65)
        self._auto.press_key(VK_KEY_R, 80)
        time.sleep(0.65)
        self._auto.press_key(VK_RETURN, 80)
        time.sleep(2.6)

    def open_collection_and_equip(self):
        """Clicks Collection (30, 406 or 47, 467) and equips Abyssal Hunter / fishing setup."""
        self.set_status("Opening Collection / Inventory...")
        self._auto.mouse_move_and_click(47, 467, 200, 200)
        self._auto.mouse_move_and_click(382, 126, 200, 200)
        time.sleep(0.5)

        self._auto.mouse_move_and_click(30, 406, 200, 200)
        self._auto.mouse_move_and_click(947, 335, 200, 200)
        time.sleep(0.2)

        # Zoom calibration
        self.set_status("Calibrating camera zoom...")
        for _ in range(80):
            self._auto.mouse_wheel(120)
            time.sleep(0.01)
        time.sleep(0.3)
        for _ in range(45):
            self._auto.mouse_wheel(-120)
            time.sleep(0.01)
        time.sleep(0.3)

    def execute_selling_path(self):
        """Paths to the fish seller, executes sales cycles, and returns to the pond."""
        if self._stop_event.is_set():
            return

        self.set_status(f"Executing {self.pathing_mode}...")

        if self.pathing_mode == "Vip Pathing":
            self._auto.key_down(VK_KEY_W)
            self._auto.key_down(VK_KEY_A)
            time.sleep(4.15)
            self._auto.key_up(VK_KEY_W)
            time.sleep(0.6)
            self._auto.key_up(VK_KEY_A)
            time.sleep(0.2)

            self._auto.press_key(VK_KEY_W, 400)
            time.sleep(0.3)
            self._auto.press_key(VK_KEY_D, 180)
            time.sleep(0.15)
            self._auto.press_key(VK_KEY_W, 1100)
            time.sleep(0.3)
            self._auto.press_key(VK_KEY_S, 300)
            time.sleep(0.3)

            # Jump forward
            self._auto.key_down(VK_SPACE)
            time.sleep(0.025)
            self._auto.key_down(VK_KEY_W)
            time.sleep(1.2)
            self._auto.key_up(VK_SPACE)
            time.sleep(0.2)
            self._auto.key_up(VK_KEY_W)
            time.sleep(0.3)

            # Press E to talk to seller
            self._auto.press_key(VK_KEY_E, 300)
            time.sleep(0.3)
            self._auto.mouse_move_and_click(956, 803, 50, 50)
            self._auto.mouse_move_and_click(956, 938, 200, 800)

            # Selling cycles
            self._sell_items()

            # Walk to pond
            self.set_status("Pathing to fishing pond...")
            self._auto.press_key(VK_KEY_A, 1400)
            time.sleep(0.075)
            self._auto.press_key(VK_KEY_W, 2670)

        elif self.pathing_mode == "Abyssal Pathing":
            self.set_status("Executing Abyssal selling path...")
            self._auto.press_key(VK_KEY_W, 800)
            self._sell_items()
            self._auto.press_key(VK_KEY_W, 1760)

        else:
            self._auto.key_down(VK_KEY_W)
            self._auto.key_down(VK_KEY_A)
            time.sleep(5.19)
            self._auto.key_up(VK_KEY_W)
            time.sleep(0.8)
            self._auto.key_up(VK_KEY_A)
            time.sleep(0.2)
            self._auto.press_key(VK_KEY_E, 300)
            self._sell_items()
            self._auto.press_key(VK_KEY_W, 3300)

        self.total_sells += 1
        self._emit_stats()

    def _sell_items(self):
        """Sells collected fish."""
        self.set_status("Selling fish inventory...")
        loop_count = 0
        max_sell = min(self.sell_loop_count, 56)

        while loop_count < max_sell and not self._stop_event.is_set():
            self._auto.mouse_move_and_click(828, 404, 200, 200)
            if self.sell_all:
                self._auto.mouse_move_and_click(680, 804, 200, 200)
            else:
                self._auto.mouse_move_and_click(512, 804, 200, 200)

            time.sleep(0.5)
            self._auto.mouse_move_and_click(801, 626, 200, 500)
            loop_count += 1

        self._auto.mouse_move_and_click(1458, 266, 200, 200)

    def _macro_loop(self):
        """Continuous fishing loop."""
        self._auto.activate_roblox_window()
        time.sleep(0.5)

        current_cycle = 0

        while not self._stop_event.is_set():
            if self.is_paused:
                time.sleep(0.5)
                continue

            current_cycle += 1

            if current_cycle > self.fishing_loop_count:
                self.reset_character()
                self.open_collection_and_equip()
                self.execute_selling_path()
                current_cycle = 0

            # 1. Cast Rod: Click at (862, 843)
            self.set_status(f"Casting fishing rod (Cycle {current_cycle}/{self.fishing_loop_count})...")
            self._auto.mouse_move_and_click(862, 843, 300, 300)

            # 2. Wait for bite indicator (White pixel at 1176, 836 == 0xFFFFFF)
            bite_detected = False
            start_wait = time.time()
            failsafe_sec = 31.0

            with ScreenDC() as hdc:
                while (time.time() - start_wait) < failsafe_sec and not self._stop_event.is_set():
                    if self.is_paused:
                        break
                    color = self._auto.get_pixel_color(1176, 836, hdc=hdc)
                    if color == 0xFFFFFF:
                        bite_detected = True
                        break
                    time.sleep(0.04)

            if not bite_detected:
                self.set_status("Bite timeout, resetting cast...")
                self._auto.mouse_move_and_click(1268, 941, 200, 200)
                continue

            # 3. Minigame Bar Catching (Track barColor along y=767)
            self.set_status("Fish hooked! Playing minigame...")
            bar_color = self._auto.get_pixel_color(955, 767)
            minigame_start = time.time()

            while (time.time() - minigame_start) < 9.0 and not self._stop_event.is_set():
                if self.is_paused:
                    break
                found_x = self._auto.pixel_search_line(757, 1161, 767, bar_color, tolerance=10)
                if not found_x:
                    self._auto.mouse_click("left", delay_ms=25)
                time.sleep(0.015)

            # 4. Collect catch
            time.sleep(0.3)
            self._auto.mouse_move_and_click(1113, 342, 200, 500)
            self.fish_caught += 1
            self.cycles_completed += 1
            self.set_status(f"Caught fish #{self.fish_caught}!")
            self._emit_stats()
            time.sleep(0.8)

    @staticmethod
    def launch_external_fishsol_ahk(ahk_dir: str = r"D:\FishSol-v2.1") -> bool:
        """Launches external FishSol-v2.1.ahk script."""
        ahk_script = os.path.join(ahk_dir, "FishSol-v2.1.ahk")
        if not os.path.isfile(ahk_script):
            return False
        try:
            os.startfile(ahk_script)
            return True
        except Exception:
            return False
