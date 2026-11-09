"""
Global Hotkey Manager
Uses pynput to register and listen for configurable system-wide keyboard shortcuts.
"""
import threading
from typing import Dict, Callable, Optional
from pynput import keyboard


class HotkeyManager:
    """Manages configurable global keyboard shortcuts for PupuSnipe."""

    def __init__(
        self,
        on_toggle: Optional[Callable[[], None]] = None,
        on_pause: Optional[Callable[[], None]] = None,
        on_resume: Optional[Callable[[], None]] = None,
        on_emergency_stop: Optional[Callable[[], None]] = None,
        on_fish: Optional[Callable[[], None]] = None,
        on_reset_cooldown: Optional[Callable[[], None]] = None
    ):
        self.callbacks = {
            "toggle": on_toggle,
            "pause": on_pause,
            "resume": on_resume,
            "emergency_stop": on_emergency_stop,
            "fish": on_fish,
            "reset_cooldown": on_reset_cooldown
        }
        self.key_bindings: Dict[str, str] = {
            "toggle": "f4",
            "pause": "f5",
            "resume": "f6",
            "emergency_stop": "f7",
            "fish": "f8",
            "reset_cooldown": "f9"
        }
        self._listener: Optional[keyboard.Listener] = None
        self._is_active = False

    def update_binding(self, action: str, key_name: str):
        """Update a key binding (e.g. 'toggle' -> 'f4')."""
        if action == "fishsol":
            action = "fish"
        if action in self.key_bindings and key_name:
            self.key_bindings[action] = key_name.strip().lower()

    def start(self):
        """Starts the global keyboard listener in a daemon thread."""
        if self._is_active:
            return

        self._is_active = True
        self._listener = keyboard.Listener(on_press=self._on_press)
        self._listener.daemon = True
        self._listener.start()

    def stop(self):
        """Stops the keyboard listener."""
        self._is_active = False
        if self._listener:
            try:
                self._listener.stop()
            except Exception:
                pass
            self._listener = None

    def _get_key_str(self, key) -> str:
        try:
            if hasattr(key, "name"):
                return key.name.lower()
            elif hasattr(key, "char") and key.char:
                return key.char.lower()
            else:
                return str(key).replace("Key.", "").lower()
        except Exception:
            return ""

    def _on_press(self, key):
        if not self._is_active:
            return

        key_str = self._get_key_str(key)
        if not key_str:
            return

        for action, bound_key in self.key_bindings.items():
            if key_str == bound_key:
                cb = self.callbacks.get(action)
                if cb:
                    # Run callback in non-blocking thread to prevent keyboard hook lag
                    threading.Thread(target=cb, daemon=True).start()
