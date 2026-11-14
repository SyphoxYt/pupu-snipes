"""
PupuSnipe Discord Webhook Alerts
Sends a polished embed (with an optional @everyone ping) whenever a private
server link is sniped, and patches the message once the live biome is confirmed.
"""
from __future__ import annotations

import json
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from .config import APP_VERSION
from .logger import get_logger

logger = get_logger()

SNIPE_COLOR = 0x00F0FF
TEST_COLOR = 0x00FF88
WEBHOOK_HOSTS = {
    "discord.com",
    "discordapp.com",
    "canary.discord.com",
    "ptb.discord.com",
}
GENERIC_PROFILES = {
    "",
    "DIRECT LINK",
    "MATCH",
    "DEDICATED CHANNEL",
    "UNKNOWN",
    "MANUAL",
    "TEST JOIN",
}


def _normalized_name(value: Any) -> str:
    return str(value or "").strip().upper().replace("_", " ")
PLACEHOLDER_BIOMES = {"", "NORMAL", "DEFAULT", "UNKNOWN", "NONE", "-"}


def is_valid_webhook_url(url: str) -> bool:
    """Validates a Discord webhook URL without performing any network request."""
    try:
        parsed = urllib.parse.urlsplit(str(url or "").strip())
    except Exception:
        return False
    if parsed.scheme.lower() != "https":
        return False
    if (parsed.hostname or "").lower() not in WEBHOOK_HOSTS:
        return False
    segments = [part for part in parsed.path.split("/") if part]
    return (
        len(segments) >= 4
        and segments[0] == "api"
        and segments[1] == "webhooks"
        and bool(segments[2])
        and bool(segments[3])
    )


def _base_webhook_url(url: str) -> str:
    """Removes query parameters so the endpoint can also be used for PATCH requests."""
    parsed = urllib.parse.urlsplit(str(url or "").strip())
    return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", "")).rstrip("/")


def _with_wait(url: str) -> str:
    separator = "&" if "?" in url else "?"
    return f"{url}{separator}wait=true"


def build_server_link(link_code: str) -> str:
    """Builds the official Roblox private-server share link for a link code."""
    code = urllib.parse.quote(str(link_code or "").strip(), safe="")
    if not code:
        return ""
    return f"https://www.roblox.com/share?code={code}&type=Server"


def _trim(value: Any, limit: int = 1024, fallback: str = "—") -> str:
    text = str(value or "").strip()
    if not text:
        return fallback
    if len(text) > limit:
        text = text[: limit - 1] + "…"
    return text


def _is_generic_profile(profile: str) -> bool:
    return _normalized_name(profile) in GENERIC_PROFILES


def _biome_candidate(event: Dict[str, Any], biome: Optional[str]) -> str:
    live = _trim(biome, 120, fallback="")
    if live and _normalized_name(live) not in PLACEHOLDER_BIOMES:
        return live
    profile = _trim(event.get("profile_name"), 120, fallback="")
    if profile and not _is_generic_profile(profile):
        return profile
    keyword = _trim(event.get("keyword"), 120, fallback="")
    if keyword and _normalized_name(keyword) not in PLACEHOLDER_BIOMES and _normalized_name(keyword) not in GENERIC_PROFILES:
        return keyword
    return ""


def _iso_timestamp(event: Dict[str, Any]) -> str:
    try:
        stamp = float(event.get("timestamp") or time.time())
    except Exception:
        stamp = time.time()
    return datetime.fromtimestamp(stamp, tz=timezone.utc).isoformat().replace("+00:00", "Z")


def build_snipe_embed(event: Dict[str, Any], biome: Optional[str] = None) -> Dict[str, Any]:
    """Builds the Discord embed for a snipe event. Safe to call from any thread."""
    profile = _trim(event.get("profile_name"), 120, fallback="Unknown")
    detected_biome = _biome_candidate(event, biome)
    biome_display = detected_biome or "⏳ Detecting live biome…"

    try:
        latency = float(event.get("latency_ms") or 0.0)
    except Exception:
        latency = 0.0

    server_name = _trim(event.get("server_name"), 250, fallback="Unknown server")
    channel_name = _trim(event.get("channel_name"), 250, fallback="Direct message")
    author_name = _trim(event.get("author_name"), 250, fallback="Unknown")
    link_code = _trim(event.get("link_code"), 80, fallback="")
    protocol_url = _trim(event.get("protocol_url"), 1000, fallback="")
    is_web_gateway = protocol_url.lower().startswith(("http://", "https://"))
    join_link = protocol_url if is_web_gateway else build_server_link(link_code)
    join_label = "Open the protected join page" if is_web_gateway else "Join the server now"

    if detected_biome:
        title = f"🎯 {detected_biome} — Server Sniped!"
    else:
        title = "🎯 Private Server Sniped!"

    description_lines = [
        "**PupuSnipe caught a fresh Sol's RNG private server.**",
    ]
    if join_link:
        description_lines.append(f"🔗 [**{join_label}**]({join_link})")
    elif protocol_url:
        description_lines.append(f"🔗 `{protocol_url}`")
    else:
        description_lines.append("The server link was captured and dispatched to the Roblox client.")

    fields = [
        {"name": "🧬 Biome", "value": biome_display, "inline": True},
        {"name": "🎯 Target", "value": profile, "inline": True},
        {"name": "⚡ Latency", "value": f"{latency:.2f} ms", "inline": True},
        {"name": "🎮 Source Server", "value": server_name, "inline": True},
        {"name": "📺 Channel", "value": f"#{channel_name.lstrip('#')}", "inline": True},
        {"name": "👤 Posted By", "value": author_name, "inline": True},
        {"name": "🧾 Link Code", "value": f"`{link_code}`" if link_code else "—", "inline": True},
    ]
    if join_link:
        fields.append({
            "name": "🔗 Join Link",
            "value": f"[{join_label}]({join_link})",
            "inline": False,
        })

    embed: Dict[str, Any] = {
        "title": title,
        "description": "\n".join(description_lines),
        "color": SNIPE_COLOR,
        "fields": fields,
        "footer": {"text": f"PupuSnipe v{APP_VERSION} • Sol's RNG Sniper"},
        "timestamp": _iso_timestamp(event),
    }
    if join_link:
        embed["url"] = join_link
    return embed


def build_snipe_payload(event: Dict[str, Any], biome: Optional[str] = None, ping_everyone: bool = True) -> Dict[str, Any]:
    """Builds the complete webhook execute payload."""
    content = (
        "@everyone 🎯 **A new Sol's RNG private server has been sniped!**"
        if ping_everyone
        else "🎯 **A new Sol's RNG private server has been sniped!**"
    )
    return {
        "content": content,
        "username": "PupuSnipe",
        "embeds": [build_snipe_embed(event, biome=biome)],
        "allowed_mentions": {
            "parse": ["everyone"] if ping_everyone else [],
            "users": [],
            "roles": [],
        },
    }


def build_test_payload(ping_everyone: bool = False) -> Dict[str, Any]:
    """Builds a test message that verifies webhook configuration."""
    content = (
        "@everyone 🧪 **PupuSnipe webhook test**"
        if ping_everyone
        else "🧪 **PupuSnipe webhook test**"
    )
    embed = {
        "title": "✅ Webhook Connected Successfully",
        "description": (
            "Your Discord webhook is working. When PupuSnipe snipes a private server, "
            "a message like this will appear automatically with the **biome**, **latency**, "
            "**source channel**, and a **join link**."
        ),
        "color": TEST_COLOR,
        "fields": [
            {"name": "🧬 Live Biome Updates", "value": "The message is edited after joining when the real biome is confirmed.", "inline": False},
            {"name": "👥 Ping", "value": "`@everyone` is enabled." if ping_everyone else "`@everyone` is disabled.", "inline": True},
            {"name": "🛠 App", "value": f"PupuSnipe v{APP_VERSION}", "inline": True},
        ],
        "footer": {"text": "PupuSnipe Webhook Diagnostics"},
        "timestamp": datetime.now(tz=timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    return {
        "content": content,
        "username": "PupuSnipe",
        "embeds": [embed],
        "allowed_mentions": {
            "parse": ["everyone"] if ping_everyone else [],
            "users": [],
            "roles": [],
        },
    }


def _request_json(url: str, payload: Optional[Dict[str, Any]] = None, method: str = "POST", timeout: float = 8.0) -> Dict[str, Any]:
    """Performs a JSON request and returns the decoded response body."""
    data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": f"PupuSnipe/{APP_VERSION} (+https://github.com/SyphoxYt/pupu-snipes)",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        raw = response.read().decode("utf-8", "replace")
        status = int(getattr(response, "status", 200) or 200)
    if not raw.strip():
        return {"status": status}
    try:
        decoded = json.loads(raw)
        return decoded if isinstance(decoded, dict) else {"status": status, "data": decoded}
    except json.JSONDecodeError:
        return {"status": status, "raw": raw[:500]}


def _error_message(exc: Exception) -> str:
    if isinstance(exc, urllib.error.HTTPError):
        try:
            body = exc.read().decode("utf-8", "replace")
            parsed = json.loads(body)
            if isinstance(parsed, dict) and parsed.get("message"):
                return f"Discord HTTP {exc.code}: {parsed.get('message')}"
        except Exception:
            pass
        return f"Discord HTTP {exc.code}: {exc.reason}"
    if isinstance(exc, urllib.error.URLError):
        return f"Network error: {exc.reason}"
    return str(exc) or exc.__class__.__name__


class WebhookNotifier:
    """
    Non-blocking Discord webhook dispatcher.

    Sends are executed on short-lived daemon threads so the Qt UI never waits on
    Discord's API. The most recent message ID is retained so the biome can be
    updated in place once the Roblox log watcher confirms it.
    """

    BIOME_EDIT_WINDOW_SEC = 300.0

    def __init__(self):
        self._lock = threading.Lock()
        self._last_url = ""
        self._last_message_id = ""
        self._last_event: Dict[str, Any] = {}
        self._last_biome = ""
        self._last_sent_at = 0.0
        self._sending = 0
        self._pending_biome = ""

    # -- public API ---------------------------------------------------------
    def send_snipe_async(
        self,
        event: Dict[str, Any],
        url: str,
        ping_everyone: bool = True,
        on_result: Optional[Any] = None,
    ) -> bool:
        url = str(url or "").strip()
        if not is_valid_webhook_url(url):
            logger.warning("[Webhook] Sniped-server alert skipped: invalid Discord webhook URL.")
            if on_result:
                on_result(False, "Invalid Discord webhook URL")
            return False
        with self._lock:
            self._sending += 1
        thread = threading.Thread(
            target=self._send_snipe_worker,
            args=(dict(event), url, bool(ping_everyone), on_result),
            daemon=True,
            name="PupuSnipeWebhookSend",
        )
        thread.start()
        return True

    def update_biome_async(self, biome: str) -> bool:
        """Edits the most recent sniped-server message with the confirmed biome."""
        biome = str(biome or "").strip()
        if not biome or _normalized_name(biome) in PLACEHOLDER_BIOMES:
            return False

        with self._lock:
            if self._sending > 0 and (not self._last_url or not self._last_message_id):
                # The initial webhook POST is still in flight. Apply the biome once
                # the message ID is known instead of losing the update.
                self._pending_biome = biome
                return False
            if not self._last_url or not self._last_message_id or not self._last_event:
                return False
            if time.time() - self._last_sent_at > self.BIOME_EDIT_WINDOW_SEC:
                return False
            if _normalized_name(biome) == _normalized_name(self._last_biome):
                return False
            profile = str(self._last_event.get("profile_name") or "").strip()
            if _normalized_name(biome) == _normalized_name(profile) and profile:
                # The initial embed already showed this biome; no edit needed.
                self._last_biome = biome
                return False
            event = dict(self._last_event)
            url = self._last_url
            message_id = self._last_message_id
            self._last_biome = biome
            self._last_sent_at = time.time()

        thread = threading.Thread(
            target=self._patch_biome_worker,
            args=(event, url, message_id, biome),
            daemon=True,
            name="PupuSnipeWebhookBiome",
        )
        thread.start()
        return True

    def test_webhook_async(self, url: str, ping_everyone: bool = False, on_result: Optional[Any] = None) -> bool:
        url = str(url or "").strip()
        if not is_valid_webhook_url(url):
            if on_result:
                on_result(False, "Invalid Discord webhook URL")
            return False
        thread = threading.Thread(
            target=self._test_worker,
            args=(url, bool(ping_everyone), on_result),
            daemon=True,
            name="PupuSnipeWebhookTest",
        )
        thread.start()
        return True

    def reset(self):
        with self._lock:
            self._last_url = ""
            self._last_message_id = ""
            self._last_event = {}
            self._last_biome = ""
            self._last_sent_at = 0.0
            self._pending_biome = ""

    # -- workers ------------------------------------------------------------
    def _send_snipe_worker(
        self,
        event: Dict[str, Any],
        url: str,
        ping_everyone: bool,
        on_result: Optional[Any] = None,
    ):
        payload = build_snipe_payload(event, biome=None, ping_everyone=ping_everyone)
        try:
            response = _request_json(_with_wait(url), payload, method="POST")
            message_id = str(response.get("id") or "")
            with self._lock:
                self._last_url = _base_webhook_url(url)
                self._last_message_id = message_id
                self._last_event = dict(event)
                self._last_biome = _biome_candidate(event, None)
                self._last_sent_at = time.time()
                pending_biome = self._pending_biome
                self._pending_biome = ""
                self._sending = max(0, self._sending - 1)
            logger.info(
                "[Webhook] Sniped-server alert sent%s."
                % (f" (message {message_id})" if message_id else "")
            )
            if on_result:
                on_result(True, "Webhook sent successfully")
            if pending_biome:
                self.update_biome_async(pending_biome)
        except Exception as exc:
            with self._lock:
                self._pending_biome = ""
                self._sending = max(0, self._sending - 1)
            message = _error_message(exc)
            logger.warning(f"[Webhook] Failed to send sniped-server alert: {message}")
            if on_result:
                on_result(False, message)

    def _patch_biome_worker(self, event: Dict[str, Any], url: str, message_id: str, biome: str):
        payload = {
            "embeds": [build_snipe_embed(event, biome=biome)],
            "allowed_mentions": {"parse": [], "users": [], "roles": []},
        }
        try:
            _request_json(f"{url}/messages/{urllib.parse.quote(message_id, safe='')}", payload, method="PATCH")
            logger.info(f"[Webhook] Updated sniped-server message with confirmed biome: {biome}")
        except Exception as exc:
            logger.warning(f"[Webhook] Failed to update biome on sniped-server message: {_error_message(exc)}")

    def _test_worker(self, url: str, ping_everyone: bool, on_result: Optional[Any] = None):
        try:
            response = _request_json(_with_wait(url), build_test_payload(ping_everyone), method="POST")
            message_id = str(response.get("id") or "")
            logger.info("[Webhook] Test alert delivered successfully.")
            if on_result:
                detail = f" (message {message_id})" if message_id else ""
                on_result(True, f"Test sent successfully{detail}")
        except Exception as exc:
            message = _error_message(exc)
            logger.warning(f"[Webhook] Test alert failed: {message}")
            if on_result:
                on_result(False, message)
