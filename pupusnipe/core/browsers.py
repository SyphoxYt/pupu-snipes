"""
Browser discovery helpers for Turnstile-protected join pages.

xe33hunt links must be opened in a real browser because Cloudflare only reveals
the Roblox redirect after verifying the browser. Windows may route those links
to a browser the user is not signed into, so PupuSnipe lets the user choose the
browser that holds their Roblox session.
"""
from __future__ import annotations

import os
import shutil
import sys
from typing import Dict, List, Optional

BROWSER_CHOICES: List[Dict[str, str]] = [
    {"id": "default", "name": "Default browser (Windows)"},
    {"id": "brave", "name": "Brave"},
    {"id": "chrome", "name": "Google Chrome"},
    {"id": "edge", "name": "Microsoft Edge"},
    {"id": "firefox", "name": "Mozilla Firefox"},
    {"id": "custom", "name": "Custom executable…"},
]

_WINDOWS_CANDIDATES: Dict[str, List[str]] = {
    "brave": [
        r"%LOCALAPPDATA%\BraveSoftware\Brave-Browser\Application\brave.exe",
        r"%PROGRAMFILES%\BraveSoftware\Brave-Browser\Application\brave.exe",
        r"%PROGRAMFILES(X86)%\BraveSoftware\Brave-Browser\Application\brave.exe",
    ],
    "chrome": [
        r"%PROGRAMFILES%\Google\Chrome\Application\chrome.exe",
        r"%PROGRAMFILES(X86)%\Google\Chrome\Application\chrome.exe",
        r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe",
    ],
    "edge": [
        r"%PROGRAMFILES(X86)%\Microsoft\Edge\Application\msedge.exe",
        r"%PROGRAMFILES%\Microsoft\Edge\Application\msedge.exe",
        r"%LOCALAPPDATA%\Microsoft\Edge\Application\msedge.exe",
    ],
    "firefox": [
        r"%PROGRAMFILES%\Mozilla Firefox\firefox.exe",
        r"%PROGRAMFILES(X86)%\Mozilla Firefox\firefox.exe",
    ],
}

_WINDOWS_EXE_NAMES = {
    "brave": "brave.exe",
    "chrome": "chrome.exe",
    "edge": "msedge.exe",
    "firefox": "firefox.exe",
}


def _expand(path: str) -> str:
    return os.path.expandvars(os.path.expanduser(path))


def _registry_app_path(exe_name: str) -> Optional[str]:
    """Reads the Windows App Paths registry entry for a browser executable."""
    if sys.platform != "win32":
        return None
    try:
        import winreg
    except Exception:
        return None

    subkey = rf"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\{exe_name}"
    for root in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
        try:
            with winreg.OpenKey(root, subkey) as key:
                value, _ = winreg.QueryValueEx(key, "")
                path = _expand(str(value))
                if path and os.path.isfile(path):
                    return path
        except OSError:
            continue
    return None


def find_browser_executable(browser_id: str, custom_path: str = "") -> Optional[str]:
    """
    Returns the executable path for a browser choice.

    ``default`` intentionally returns None so the caller can use the operating
    system's default-browser handler.
    """
    browser_id = (browser_id or "default").strip().lower()

    if browser_id == "default":
        return None

    if browser_id == "custom":
        path = _expand((custom_path or "").strip())
        return path if path and os.path.isfile(path) else None

    exe_name = _WINDOWS_EXE_NAMES.get(browser_id)
    if not exe_name:
        return None

    for template in _WINDOWS_CANDIDATES.get(browser_id, []):
        path = _expand(template)
        if path and os.path.isfile(path):
            return path

    registry_path = _registry_app_path(exe_name)
    if registry_path:
        return registry_path

    # Last resort for portable installs added to PATH.
    return shutil.which(exe_name)


def describe_browser(browser_id: str, custom_path: str = "") -> str:
    """Returns a short human-readable status string for the settings UI."""
    choice = (browser_id or "default").strip().lower()

    if choice == "default":
        return "Uses whichever browser Windows has set as default."

    path = find_browser_executable(choice, custom_path)
    if path:
        return f"Launching: {path}"

    label = next(
        (item["name"] for item in BROWSER_CHOICES if item["id"] == choice),
        choice,
    )
    return f"{label} was not found. PupuSnipe will use the default browser instead."
