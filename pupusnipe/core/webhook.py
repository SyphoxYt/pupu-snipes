"""
Discord Webhook notification dispatcher for PupuSnipe.
Sends richly formatted Discord embeds with biome styling, latency metrics,
join links, and optional @everyone pings whenever a private server is sniped.
"""
import json
import time
import urllib.request
import urllib.parse
import threading
from datetime import datetime, timezone
from typing import Dict, Any, Tuple, Optional

# Visual color mapping per Sol's RNG Biome / Event
BIOME_COLORS: Dict[str, Tuple[int, str]] = {
    "DREAMSPACE": (0xff70a6, "🌸"),
    "GLITCHED": (0xa855f7, "⚡"),
    "CYBERSPACE": (0x00f0ff, "🌐"),
    "SINGULARITY": (0x6366f1, "🌌"),
    "CORRUPTION": (0x9333ea, "💜"),
    "STARFALL": (0x38bdf8, "⭐"),
    "SANDSTORM": (0xf59e0b, "⏳"),
    "HELL": (0xef4444, "🔥"),
    "RAIN": (0x60a5fa, "🌧️"),
    "SNOW": (0xe0f2fe, "❄️"),
    "JESTER": (0xeab308, "🃏"),
    "MARI": (0x10b981, "🎒"),
    "OBLIVION": (0x3b82f6, "🌀"),
    "DEFAULT": (0x00ff88, "🎯")
}

LOGO_URL = "https://raw.githubusercontent.com/SyphoxYt/pupu-snipes/main/pupusnipe/assets/logo.png"


def _resolve_biome_info(profile_name: str, keyword: str) -> Tuple[int, str, str]:
    """Resolves (color_int, emoji, formatted_name) for embed styling."""
    raw = f"{profile_name} {keyword}".upper()
    for key, (color, emoji) in BIOME_COLORS.items():
        if key in raw:
            clean_title = key.capitalize() if key != "DEFAULT" else "Sol's RNG Server"
            return color, emoji, f"{emoji} {clean_title}"

    return BIOME_COLORS["DEFAULT"][0], "🎯", f"🎯 {profile_name.capitalize() if profile_name else 'Private Server'}"


def _derive_web_url(protocol_url: str, link_code: str) -> str:
    """Constructs a browser-friendly roblox.com URL from protocol join link."""
    if not protocol_url and not link_code:
        return ""

    # 1. Share Links (code=XYZ)
    if "code=" in protocol_url or "share_links" in protocol_url:
        code = link_code
        if not code and "code=" in protocol_url:
            parsed = urllib.parse.urlparse(protocol_url)
            qs = urllib.parse.parse_qs(parsed.query)
            code = qs.get("code", [""])[0]
        if code:
            return f"https://www.roblox.com/share-links?code={code}&type=Server"

    # 2. Game Instance (placeId=...&gameInstanceId=...)
    if "gameInstanceId=" in protocol_url:
        parsed = urllib.parse.urlparse(protocol_url)
        qs = urllib.parse.parse_qs(parsed.query)
        pid = qs.get("placeId", ["15532962292"])[0]
        gid = qs.get("gameInstanceId", [link_code])[0]
        if pid and gid:
            return f"https://www.roblox.com/games/start?placeId={pid}&gameInstanceId={gid}"

    # 3. Standard Private Server Link Code
    if "linkCode=" in protocol_url:
        parsed = urllib.parse.urlparse(protocol_url)
        qs = urllib.parse.parse_qs(parsed.query)
        pid = qs.get("placeId", ["15532314909"])[0]
        lc = qs.get("linkCode", [link_code])[0]
        if pid and lc:
            return f"https://www.roblox.com/games/{pid}/game?privateServerLinkCode={lc}"

    # 4. Fallback with link_code
    if link_code:
        if len(link_code) == 36 and "-" in link_code:  # UUID
            return f"https://www.roblox.com/games/start?placeId=15532962292&gameInstanceId={link_code}"
        return f"https://www.roblox.com/share-links?code={link_code}&type=Server"

    return ""


def build_snipe_payload(event: Dict[str, Any], ping_everyone: bool = True) -> Dict[str, Any]:
    """Constructs a Discord webhook payload dictionary."""
    profile_name = str(event.get("profile_name", "")).strip() or "Server Sniped"
    keyword = str(event.get("keyword", "")).strip()
    color, emoji, display_biome = _resolve_biome_info(profile_name, keyword)

    latency_ms = event.get("latency_ms", 0.0)
    lat_str = f"`{latency_ms:.2f} ms`" if latency_ms > 0 else "`< 1 ms`"

    server_name = event.get("server_name", "Unknown Server")
    channel_name = event.get("channel_name", "VIP Channel")
    source_str = f"**{server_name}** • {channel_name}"

    protocol_url = event.get("protocol_url", "")
    link_code = event.get("link_code", "")
    web_url = _derive_web_url(protocol_url, link_code)

    now_iso = datetime.now(timezone.utc).isoformat()

    # Formatted description with fast join action
    desc_lines = [
        f"⚡ **PupuSnipe** instantly captured a Sol's RNG private server join link and executed native launch!",
        ""
    ]

    fields = [
        {
            "name": f"{emoji} Biome / Event",
            "value": f"**`{display_biome}`**",
            "inline": True
        },
        {
            "name": "⚡ Detect Latency",
            "value": lat_str,
            "inline": True
        },
        {
            "name": "📡 Discord Source",
            "value": source_str,
            "inline": False
        }
    ]

    # Join Links
    if protocol_url:
        fields.append({
            "name": "🚀 Instant Roblox Protocol Launch",
            "value": f"[**Click Here to Launch Roblox Directly**](<{protocol_url}>)",
            "inline": False
        })

    if web_url:
        fields.append({
            "name": "🌐 Web Browser / Mobile Link",
            "value": f"[**Open Server in Browser**](<{web_url}>)",
            "inline": False
        })

    if link_code:
        fields.append({
            "name": "🔑 Server Link Code / Instance ID",
            "value": f"`{link_code}`",
            "inline": False
        })

    embed = {
        "title": f"🎯 Sol's RNG Private Server Sniped! — {display_biome}",
        "description": "\n".join(desc_lines),
        "color": color,
        "fields": fields,
        "thumbnail": {
            "url": LOGO_URL
        },
        "footer": {
            "text": "PupuSnipe v1.0.0 • Sub-20ms Sol's RNG Private Server Sniper",
            "icon_url": LOGO_URL
        },
        "timestamp": now_iso
    }

    content_msg = "@everyone 🚨 **Sol's RNG VIP Server Sniped!**" if ping_everyone else "🚨 **Sol's RNG VIP Server Sniped!**"

    return {
        "username": "PupuSnipe VIP Alerts",
        "avatar_url": LOGO_URL,
        "content": content_msg,
        "embeds": [embed]
    }


def send_snipe_webhook(webhook_url: str, event: Dict[str, Any], ping_everyone: bool = True, timeout: float = 5.0) -> Tuple[bool, str]:
    """Synchronously sends a snipe notification to a Discord webhook URL."""
    clean_url = str(webhook_url).strip()
    if not clean_url or not clean_url.startswith("https://"):
        return False, "Invalid webhook URL: must start with https://"

    try:
        payload = build_snipe_payload(event, ping_everyone=ping_everyone)
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            clean_url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "PupuSnipe-DiscordWebhook/1.0"
            },
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status in (200, 204):
                return True, "Webhook sent successfully"
            return False, f"Unexpected response status: {resp.status}"
    except Exception as ex:
        return False, str(ex)


def send_test_webhook(webhook_url: str, ping_everyone: bool = False, timeout: float = 5.0) -> Tuple[bool, str]:
    """Sends a test webhook notification to verify connectivity."""
    clean_url = str(webhook_url).strip()
    if not clean_url or not clean_url.startswith("https://"):
        return False, "Invalid webhook URL: must start with https://"

    test_event = {
        "timestamp": time.time(),
        "server_name": "xe33Hunt",
        "channel_name": "#🌸dreamspace",
        "author_name": "Shay's Glitch Bot",
        "profile_name": "DREAMSPACE",
        "keyword": "dreamspace",
        "link_code": "9de406b3-cb36-4c4b-ae90-a1f2678dda26",
        "protocol_url": "roblox://experiences/start?placeId=15532962292&gameInstanceId=9de406b3-cb36-4c4b-ae90-a1f2678dda26",
        "latency_ms": 11.8,
        "status": "JOINED"
    }

    try:
        payload = build_snipe_payload(test_event, ping_everyone=ping_everyone)
        payload["content"] = "🧪 **[TEST WEBHOOK]** PupuSnipe webhook alerts successfully connected!"
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            clean_url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "PupuSnipe-DiscordWebhook/1.0"
            },
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status in (200, 204):
                return True, "Test webhook delivered successfully!"
            return False, f"HTTP Error {resp.status}"
    except Exception as ex:
        return False, str(ex)


def send_snipe_webhook_async(webhook_url: str, event: Dict[str, Any], ping_everyone: bool = True):
    """
    Dispatches the Discord webhook notification in a background daemon thread.
    Guarantees 0ms impact on the main Roblox join speed.
    """
    if not webhook_url:
        return

    def _worker():
        send_snipe_webhook(webhook_url, event, ping_everyone=ping_everyone)

    t = threading.Thread(target=_worker, name="WebhookSenderThread", daemon=True)
    t.start()
