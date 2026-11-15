"""
Discord Webhook notification dispatcher for PupuSnipe.
Sends richly formatted Discord embeds with biome styling, latency metrics,
prominent clickable join links, biome images from Discord embeds, and optional @everyone pings.
Also sends notifications when the sniper engine starts and stops.
"""
import json
import time
import urllib.request
import urllib.parse
import threading
from datetime import datetime, timezone
from typing import Dict, Any, Tuple, Optional, List

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

BIOME_FALLBACK_IMAGES: Dict[str, str] = {
    "DREAMSPACE": "https://raw.githubusercontent.com/SyphoxYt/pupu-snipes/main/pupusnipe/assets/biomes/dreamspace.png",
    "GLITCHED": "https://raw.githubusercontent.com/SyphoxYt/pupu-snipes/main/pupusnipe/assets/biomes/glitched.png",
    "CYBERSPACE": "https://raw.githubusercontent.com/SyphoxYt/pupu-snipes/main/pupusnipe/assets/biomes/cyberspace.png",
    "SINGULARITY": "https://raw.githubusercontent.com/SyphoxYt/pupu-snipes/main/pupusnipe/assets/biomes/singularity.png",
    "CORRUPTION": "https://raw.githubusercontent.com/SyphoxYt/pupu-snipes/main/pupusnipe/assets/biomes/corruption.png",
    "STARFALL": "https://raw.githubusercontent.com/SyphoxYt/pupu-snipes/main/pupusnipe/assets/biomes/starfall.png",
    "SANDSTORM": "https://raw.githubusercontent.com/SyphoxYt/pupu-snipes/main/pupusnipe/assets/biomes/sandstorm.png",
    "HELL": "https://raw.githubusercontent.com/SyphoxYt/pupu-snipes/main/pupusnipe/assets/biomes/hell.png",
    "RAIN": "https://raw.githubusercontent.com/SyphoxYt/pupu-snipes/main/pupusnipe/assets/biomes/rain.png",
    "SNOW": "https://raw.githubusercontent.com/SyphoxYt/pupu-snipes/main/pupusnipe/assets/biomes/snow.png"
}

LOGO_URL = "https://raw.githubusercontent.com/SyphoxYt/pupu-snipes/main/pupusnipe/assets/logo.png"


def _resolve_biome_info(profile_name: str, keyword: str) -> Tuple[int, str, str, str]:
    """Resolves (color_int, emoji, formatted_name, fallback_image_url) for embed styling."""
    raw = f"{profile_name} {keyword}".upper()
    for key, (color, emoji) in BIOME_COLORS.items():
        if key in raw and key != "DEFAULT":
            clean_title = key.capitalize()
            img = BIOME_FALLBACK_IMAGES.get(key, "")
            return color, emoji, f"{emoji} {clean_title}", img

    def_col, def_emoji = BIOME_COLORS["DEFAULT"]
    return def_col, def_emoji, f"{def_emoji} {profile_name.capitalize() if profile_name else 'Private Server'}", ""


def _derive_web_url(protocol_url: str, link_code: str) -> str:
    """Constructs a browser-friendly roblox.com or gateway URL from protocol join link."""
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
            return f"https://www.roblox.com/share?code={code}&type=Server"

    # 2. Game Instance (placeId=...&gameInstanceId=...)
    if "gameInstanceId=" in protocol_url:
        parsed = urllib.parse.urlparse(protocol_url)
        qs = urllib.parse.parse_qs(parsed.query)
        pid = qs.get("placeId", ["15532962292"])[0]
        gid = qs.get("gameInstanceId", [link_code])[0]
        if gid:
            # Check if UUID
            if len(gid) == 36 and "-" in gid:
                return f"https://xe33cc.github.io/join/?s={gid}"
            return f"https://www.roblox.com/games/start?placeId={pid}&gameInstanceId={gid}"

    # 3. Standard Private Server Link Code
    if "linkCode=" in protocol_url:
        parsed = urllib.parse.urlparse(protocol_url)
        qs = urllib.parse.parse_qs(parsed.query)
        pid = qs.get("placeId", ["15532962292"])[0]
        lc = qs.get("linkCode", [link_code])[0]
        if pid and lc:
            return f"https://www.roblox.com/games/{pid}/game?privateServerLinkCode={lc}"

    # 4. Fallback with link_code
    if link_code:
        if len(link_code) == 36 and "-" in link_code:  # UUID
            return f"https://xe33cc.github.io/join/?s={link_code}"
        return f"https://www.roblox.com/share-links?code={link_code}&type=Server"

    return ""


def _resolve_primary_join_url(raw_url: str, protocol_url: str, link_code: str) -> str:
    """Returns the most direct, clickable HTTPS URL for Discord users."""
    if raw_url and raw_url.startswith("http"):
        return raw_url

    web_url = _derive_web_url(protocol_url, link_code)
    if web_url and web_url.startswith("http"):
        return web_url

    if link_code:
        if len(link_code) == 36 and "-" in link_code:
            return f"https://xe33cc.github.io/join/?s={link_code}"
        return f"https://www.roblox.com/share?code={link_code}&type=Server"

    return "https://www.roblox.com/games/15532962292"


def build_snipe_payload(event: Dict[str, Any], ping_everyone: bool = True) -> Dict[str, Any]:
    """Constructs an upgraded Discord webhook payload dictionary with prominent join links and biome image."""
    profile_name = str(event.get("profile_name", "")).strip() or "Server Sniped"
    keyword = str(event.get("keyword", "")).strip()
    color, emoji, display_biome, fallback_img = _resolve_biome_info(profile_name, keyword)

    latency_ms = event.get("latency_ms", 0.0)
    lat_str = f"`{latency_ms:.2f} ms`" if latency_ms > 0 else "`< 1 ms`"

    server_name = event.get("server_name", "Unknown Server")
    channel_name = event.get("channel_name", "VIP Channel")
    source_str = f"**{server_name}** • {channel_name}"

    raw_url = str(event.get("raw_url", "")).strip()
    protocol_url = str(event.get("protocol_url", "")).strip()
    link_code = str(event.get("link_code", "")).strip()

    primary_join_url = _resolve_primary_join_url(raw_url, protocol_url, link_code)

    # Resolve image: prefer Discord embed image passed from Astrald's Hunters / forwarder, then fallback
    image_url = str(event.get("image_url", "")).strip() or fallback_img

    now_iso = datetime.now(timezone.utc).isoformat()

    desc_lines = [
        f"# 🚀 [CLICK HERE TO JOIN VIP SERVER NOW]({primary_join_url})",
        "",
        "⚡ **PupuSnipe** instantly captured a Sol's RNG private server join link and executed native launch!",
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
        },
        {
            "name": "🔗 Direct Join Link (Browser / Mobile / PC)",
            "value": f"[👉 **Click Here to Open VIP Server** 👈]({primary_join_url})\n{primary_join_url}",
            "inline": False
        }
    ]

    if protocol_url and protocol_url.startswith("roblox://"):
        fields.append({
            "name": "💻 Windows Run Protocol (Win + R)",
            "value": f"```{protocol_url}```\n*(Copy and paste into Windows Run `Win+R` to join directly)*",
            "inline": False
        })

    if link_code:
        fields.append({
            "name": "🔑 Server Link Code / Instance ID",
            "value": f"`{link_code}`",
            "inline": True
        })

    embed: Dict[str, Any] = {
        "title": f"🎯 Sol's RNG Private Server Sniped! — {display_biome}",
        "description": "\n".join(desc_lines),
        "color": color,
        "fields": fields,
        "thumbnail": {
            "url": LOGO_URL
        },
        "footer": {
            "text": "PupuSnipe v1.1.4 • Sub-20ms Sol's RNG Private Server Sniper",
            "icon_url": LOGO_URL
        },
        "timestamp": now_iso
    }

    if image_url:
        embed["image"] = {"url": image_url}

    if ping_everyone:
        content_msg = f"@everyone 🚨 **Sol's RNG VIP Server Sniped!**\n👉 **Join Server:** {primary_join_url}"
    else:
        content_msg = f"🚨 **Sol's RNG VIP Server Sniped!**\n👉 **Join Server:** {primary_join_url}"

    return {
        "username": "PupuSnipe VIP Alerts",
        "avatar_url": LOGO_URL,
        "content": content_msg,
        "embeds": [embed]
    }


def build_engine_status_payload(
    status: str,
    channels: Optional[List[Dict[str, Any]]] = None,
    stats: Optional[Dict[str, Any]] = None,
    config_info: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Constructs a Discord webhook payload for engine START / STOP events."""
    now_iso = datetime.now(timezone.utc).isoformat()
    status_upper = status.upper()

    if status_upper == "STARTED":
        color = 0x00ff88  # Vibrant Green
        title = "🟢 PupuSnipe Sniper Engine Started"
        desc = "**PupuSnipe is now running and monitoring Discord channels in real-time.**"

        fields = []

        # Connected Channels list
        if channels and len(channels) > 0:
            ch_lines = []
            for ch in channels[:10]:
                s_name = ch.get("server_name") or "Server"
                c_name = ch.get("channel_name") or f"channel-{str(ch.get('channel_id', ''))[-4:]}"
                cid = str(ch.get("channel_id", ""))
                ch_lines.append(f"• **{s_name}** ➔ `{c_name}` (`{cid}`)")
            if len(channels) > 10:
                ch_lines.append(f"...and {len(channels) - 10} more channels")
            fields.append({
                "name": f"📡 Connected Channels ({len(channels)})",
                "value": "\n".join(ch_lines),
                "inline": False
            })
        else:
            fields.append({
                "name": "📡 Connected Channels",
                "value": "🌐 **Monitoring ALL Discord Channels** (Global Real-Time Scan)",
                "inline": False
            })

        cfg = config_info or {}
        client = str(cfg.get("client", "voidstrap")).capitalize()
        method = str(cfg.get("method", "protocol")).capitalize()
        place_id = str(cfg.get("place_id", "15532962292"))

        fields.append({
            "name": "🎯 Target Place ID",
            "value": f"`{place_id}` (Sol's RNG)",
            "inline": True
        })
        fields.append({
            "name": "⚡ Launch Pipeline",
            "value": f"`{client}` via `{method}`",
            "inline": True
        })
        fields.append({
            "name": "⏱️ Anti-Hop Cooldown",
            "value": "`10 Minutes Active` (F9 to Reset)",
            "inline": True
        })

        embed = {
            "title": title,
            "description": desc,
            "color": color,
            "fields": fields,
            "thumbnail": {"url": LOGO_URL},
            "footer": {
                "text": "PupuSnipe VIP Alerts • Sub-20ms Engine Active",
                "icon_url": LOGO_URL
            },
            "timestamp": now_iso
        }

        return {
            "username": "PupuSnipe VIP Alerts",
            "avatar_url": LOGO_URL,
            "content": "🟢 **PupuSnipe Engine is now ONLINE** — Monitoring for VIP Private Servers!",
            "embeds": [embed]
        }

    else:
        # STOPPED
        color = 0xef4444  # Vibrant Red
        title = "🔴 PupuSnipe Sniper Engine Stopped"
        desc = "**PupuSnipe sniper engine has been stopped.**"

        st = stats or {}
        scanned = st.get("scanned", 0)
        joined = st.get("joined", 0)
        fastest_ms = st.get("fastest_ms", 0.0)
        fast_str = f"`{fastest_ms:.2f} ms`" if fastest_ms > 0 else "`N/A`"

        fields = [
            {
                "name": "📊 Messages Scanned",
                "value": f"`{scanned:,}`",
                "inline": True
            },
            {
                "name": "🎯 Servers Sniped",
                "value": f"`{joined}`",
                "inline": True
            },
            {
                "name": "⚡ Fastest Detect Latency",
                "value": fast_str,
                "inline": True
            }
        ]

        embed = {
            "title": title,
            "description": desc,
            "color": color,
            "fields": fields,
            "thumbnail": {"url": LOGO_URL},
            "footer": {
                "text": "PupuSnipe VIP Alerts • Session Concluded",
                "icon_url": LOGO_URL
            },
            "timestamp": now_iso
        }

        return {
            "username": "PupuSnipe VIP Alerts",
            "avatar_url": LOGO_URL,
            "content": "🔴 **PupuSnipe Engine is now OFFLINE**",
            "embeds": [embed]
        }


def _dispatch_webhook_http(webhook_url: str, payload: Dict[str, Any], timeout: float = 5.0) -> Tuple[bool, str]:
    """Helper to dispatch HTTP POST request to a Discord webhook."""
    clean_url = str(webhook_url).strip()
    if not clean_url or not clean_url.startswith("https://"):
        return False, "Invalid webhook URL: must start with https://"

    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            clean_url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "PupuSnipe-DiscordWebhook/1.1"
            },
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status in (200, 204):
                return True, "Webhook sent successfully"
            return False, f"Unexpected response status: {resp.status}"
    except Exception as ex:
        return False, str(ex)


def send_snipe_webhook(webhook_url: str, event: Dict[str, Any], ping_everyone: bool = True, timeout: float = 5.0) -> Tuple[bool, str]:
    """Synchronously sends a snipe notification to a Discord webhook URL."""
    payload = build_snipe_payload(event, ping_everyone=ping_everyone)
    return _dispatch_webhook_http(webhook_url, payload, timeout=timeout)


def send_engine_status_webhook(
    webhook_url: str,
    status: str,
    channels: Optional[List[Dict[str, Any]]] = None,
    stats: Optional[Dict[str, Any]] = None,
    config_info: Optional[Dict[str, Any]] = None,
    timeout: float = 5.0
) -> Tuple[bool, str]:
    """Synchronously sends an engine status notification (STARTED/STOPPED) to a Discord webhook URL."""
    payload = build_engine_status_payload(status, channels=channels, stats=stats, config_info=config_info)
    return _dispatch_webhook_http(webhook_url, payload, timeout=timeout)


def send_engine_status_webhook_async(
    webhook_url: str,
    status: str,
    channels: Optional[List[Dict[str, Any]]] = None,
    stats: Optional[Dict[str, Any]] = None,
    config_info: Optional[Dict[str, Any]] = None
):
    """Dispatches the engine status notification in a background daemon thread."""
    if not webhook_url:
        return

    def _worker():
        send_engine_status_webhook(
            webhook_url,
            status,
            channels=channels,
            stats=stats,
            config_info=config_info
        )

    t = threading.Thread(target=_worker, name="EngineStatusWebhookThread", daemon=True)
    t.start()


def send_test_webhook(webhook_url: str, ping_everyone: bool = False, timeout: float = 5.0) -> Tuple[bool, str]:
    """Sends a test webhook notification to verify connectivity."""
    test_event = {
        "timestamp": time.time(),
        "server_name": "xe33Hunt",
        "channel_name": "#🌸dreamspace",
        "author_name": "Shay's Glitch Bot",
        "profile_name": "DREAMSPACE",
        "keyword": "dreamspace",
        "link_code": "9de406b3-cb36-4c4b-ae90-a1f2678dda26",
        "raw_url": "https://xe33cc.github.io/join/?s=9de406b3-cb36-4c4b-ae90-a1f2678dda26",
        "protocol_url": "roblox://experiences/start?placeId=15532962292&gameInstanceId=9de406b3-cb36-4c4b-ae90-a1f2678dda26",
        "latency_ms": 11.8,
        "status": "JOINED",
        "image_url": BIOME_FALLBACK_IMAGES.get("DREAMSPACE", "")
    }

    try:
        payload = build_snipe_payload(test_event, ping_everyone=ping_everyone)
        payload["content"] = "🧪 **[TEST WEBHOOK]** PupuSnipe webhook alerts successfully connected!"
        if ping_everyone:
            payload["content"] = "@everyone 🧪 **[TEST WEBHOOK]** PupuSnipe webhook alerts successfully connected!"
        return _dispatch_webhook_http(webhook_url, payload, timeout=timeout)
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
