"""
PupuSnipe Configuration and Constants
High-performance Sol's RNG Private Server Sniper
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any
import os

APP_NAME = "PupuSnipe"
APP_VERSION = "1.1.2"
APP_DESCRIPTION = "High-performance Sol's RNG Private Server Sniper"

# Primary Sol's RNG place ID
DEFAULT_SOLS_RNG_PLACE_ID = "15532314909"
SUPPORTED_PLACE_IDS = {
    "15532314909": "Sol's RNG",
    "15532962292": "Sol's RNG [Sub-instance]",
    "17068593414": "Sol's RNG [Testing / Event]"
}

# Place ID used by join-gateway pages (e.g. xe33cc.github.io/join/?s=<UUID>)
JOIN_GATEWAY_PLACE_ID = "15532962292"

# Legitimate Roblox domains
LEGITIMATE_ROBLOX_DOMAINS = [
    "roblox.com",
    "www.roblox.com",
    "web.roblox.com"
]

# Suspicious anti-bait terms
DEFAULT_ANTI_BAIT_KEYWORDS = [
    "fake",
    "scam",
    "expired",
    "troll",
    "phishing",
    "grabify",
    "free robux",
    "discord.gift"
]

# Default profiles matching Sol Sniper V3 & Sol's RNG
DEFAULT_PROFILES = [
    # Biomes
    {"id": "corruption", "category": "Biomes", "name": "Corruption", "keywords": ["corruption", "corrupt biome", "corrupt"], "is_regex": False, "priority": 10, "enabled": True, "pause_duration": 300},
    {"id": "glitched", "category": "Biomes", "name": "Glitched", "keywords": ["glitched", "glitch biome"], "is_regex": False, "priority": 10, "enabled": True, "pause_duration": 180},
    {"id": "dreamspace", "category": "Biomes", "name": "Dreamspace", "keywords": ["dreamspace", "dream space"], "is_regex": False, "priority": 9, "enabled": True, "pause_duration": 180},
    {"id": "cyberspace", "category": "Biomes", "name": "Cyberspace", "keywords": ["cyberspace", "cyber space"], "is_regex": False, "priority": 8, "enabled": True, "pause_duration": 720},
    {"id": "singularity", "category": "Biomes", "name": "Singularity", "keywords": ["singularity"], "is_regex": False, "priority": 8, "enabled": True, "pause_duration": 1200},
    {"id": "oblivion_biome", "category": "Biomes", "name": "Oblivion", "keywords": ["oblivion"], "is_regex": False, "priority": 10, "enabled": True, "pause_duration": 180},
    {"id": "starfall", "category": "Biomes", "name": "Starfall", "keywords": ["starfall"], "is_regex": False, "priority": 6, "enabled": True, "pause_duration": 60},
    # Merchants
    {"id": "jester", "category": "Merchants", "name": "Jester", "keywords": ["jester"], "is_regex": False, "priority": 9, "enabled": True, "pause_duration": 180},
    {"id": "mari", "category": "Merchants", "name": "Mari", "keywords": ["mari"], "is_regex": False, "priority": 8, "enabled": True, "pause_duration": 60},
    {"id": "rin", "category": "Merchants", "name": "Rin", "keywords": ["rin"], "is_regex": False, "priority": 7, "enabled": True, "pause_duration": 60},
    # Items
    {"id": "void_coin", "category": "Items", "name": "Void Coin", "keywords": ["void coin", "voidcoin"], "is_regex": False, "priority": 10, "enabled": True, "pause_duration": 120},
    {"id": "oblivion_potion", "category": "Items", "name": "Oblivion Potion", "keywords": ["oblivion pot", "oblivion potion"], "is_regex": False, "priority": 10, "enabled": True, "pause_duration": 180},
    {"id": "stellas_candle", "category": "Items", "name": "Stella's Candle", "keywords": ["stella's candle", "stellas candle", "candle"], "is_regex": False, "priority": 7, "enabled": True, "pause_duration": 60},
    {"id": "warp_potion", "category": "Items", "name": "Warp Potion", "keywords": ["warp potion", "warp pot"], "is_regex": False, "priority": 6, "enabled": True, "pause_duration": 60},
]

# Preset public Sol's RNG sniper channels (from sniper-v3)
DEFAULT_SNIPER_CHANNEL_PRESETS = [
    "1271189513619902515",
    "1337886908251902114",
    "1444176397286510852",
    "1497517434859683910",
    "1546359525471166484",
    "1271189425459826702",
    "1290022552105648168",
    "1472430010571816961"
]


@dataclass
class AppConfig:
    # General
    place_id: str = DEFAULT_SOLS_RNG_PLACE_ID
    auto_join: bool = True
    prewarm_roblox: bool = False
    roblox_client: str = "voidstrap"  # "voidstrap" (Voidstrap), "vanilla" (Normal Roblox), "auto" (Windows Protocol Default)
    launch_method: str = "protocol"  # "protocol", "direct_exe", "system"
    duplicate_cooldown_sec: int = 180
    enable_notifications: bool = True
    play_sound: bool = True
    sound_preset: str = "chime"  # Bundled snipe sound id (see core/sounds.py)
    custom_sound_path: str = ""  # Optional user-selected .wav for the "custom" preset
    join_all_in_monitored_channels: bool = True  # Allows joining links in targeted channels without requiring keyword text
    ui_scale: float = 1.0

    # Discord Webhook Alerts
    webhook_enabled: bool = False
    webhook_url: str = ""
    webhook_ping_everyone: bool = True
    
    # Advanced Options (from Sol Sniper V3)
    close_roblox_before_joining: bool = False
    leave_game_before_joining: bool = False
    minimize_other_windows: bool = False
    auto_pause_sniper: bool = False
    only_join_sols_links: bool = True
    
    # Custom Links (from Sol Sniper V3)
    snipe_ropro_links: bool = True
    snipe_joinrbx_links: bool = True
    snipe_roseal_links: bool = True
    snipe_fishstrap_links: bool = True
    snipe_joingate_links: bool = True

    # Browser used for Turnstile-protected join pages (xe33hunt)
    gateway_browser: str = "default"  # default, brave, chrome, edge, firefox, custom
    gateway_browser_path: str = ""  # Custom browser executable

    # Try to resolve protected pages off-screen and dispatch the captured
    # roblox:// URL through the native launcher. Falls back to opening the
    # selected browser when Cloudflare cannot be satisfied automatically.
    gateway_resolver_enabled: bool = True
    
    # Hotkeys
    hotkey_toggle: str = "F4"
    hotkey_pause: str = "F5"
    hotkey_resume: str = "F6"
    hotkey_emergency_stop: str = "F7"
    hotkey_fishsol: str = "F8"

    # Place ID
    place_id: str = DEFAULT_SOLS_RNG_PLACE_ID
