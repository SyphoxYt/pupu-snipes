"""Resolve Turnstile-protected join pages into native Roblox protocol URLs."""

from __future__ import annotations

import asyncio
import base64
import json
import os
import re
import socket
import subprocess
import sys
import tempfile
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import aiohttp

from .browsers import find_browser_executable
from .logger import get_logger

logger = get_logger()

_DEFAULT_TIMEOUT = 20.0
_PROFILE_DIR_NAME = "gateway-browser"
_RE_ROBLOX_URL = re.compile(r"roblox://[^\s\"'<>\\]+", re.IGNORECASE)
_RE_ROBLOX_WEB_START = re.compile(
    r"https?://(?:www\.)?roblox\.com/games/start\?[^#\s<>\)]+",
    re.IGNORECASE,
)
_RE_XE33_JOIN_PATTERN = "*xe33hunt.com/j/*"


@dataclass
class ResolveResult:
    status: str
    roblox_url: str = ""
    message: str = ""
    title: str = ""


def _find_chromium_browser(browser_id: str, custom_path: str = "") -> Optional[str]:
    choice = (browser_id or "default").strip().lower()

    if choice == "firefox":
        return None

    if choice == "custom":
        return find_browser_executable("custom", custom_path)

    if choice in ("brave", "chrome", "edge"):
        return find_browser_executable(choice)

    for candidate in ("brave", "chrome", "edge"):
        path = find_browser_executable(candidate)
        if path:
            return path
    return None


def _profile_dir() -> str:
    base = os.environ.get("LOCALAPPDATA") or tempfile.gettempdir()
    path = os.path.join(base, "PupuSnipe", _PROFILE_DIR_NAME)
    os.makedirs(path, exist_ok=True)
    return path


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _launch_browser(browser_path: str, port: int, profile_dir: str) -> subprocess.Popen:
    args = [
        browser_path,
        f"--remote-debugging-port={port}",
        f"--user-data-dir={profile_dir}",
        "--remote-allow-origins=*",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-background-networking",
        "--disable-sync",
        "--disable-extensions",
        "--disable-component-update",
        "--disable-default-apps",
        "--mute-audio",
        "--window-position=-2400,-2400",
        "--window-size=960,720",
        "about:blank",
    ]
    creationflags = subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0
    return subprocess.Popen(
        args,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=creationflags,
    )


def _kill_browser(proc: Optional[subprocess.Popen]) -> None:
    if not proc:
        return
    try:
        if proc.poll() is None:
            if sys.platform == "win32":
                subprocess.run(
                    ["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=5,
                )
            else:
                proc.terminate()
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass
    finally:
        try:
            proc.wait(timeout=5)
        except Exception:
            pass


def _wait_for_page_target(port: int, timeout: float = 10.0) -> Optional[str]:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(
                f"http://127.0.0.1:{port}/json/list", timeout=1.0
            ) as response:
                targets = json.load(response)
            for target in targets:
                if target.get("type") == "page" and target.get("webSocketDebuggerUrl"):
                    return str(target["webSocketDebuggerUrl"])
        except Exception:
            pass
        time.sleep(0.1)
    return None


def _header_value(headers: List[Dict[str, Any]], name: str) -> str:
    target = name.lower()
    for header in headers:
        if str(header.get("name", "")).lower() == target:
            return str(header.get("value", ""))
    return ""


def _extract_protocol_url(text: str) -> str:
    if not text:
        return ""

    decoded = urllib.parse.unquote(text)
    match = _RE_ROBLOX_URL.search(decoded)
    if match:
        return match.group(0).rstrip(".,;)]}\"'\\")

    web_match = _RE_ROBLOX_WEB_START.search(decoded)
    if web_match:
        query = urllib.parse.parse_qs(urllib.parse.urlsplit(web_match.group(0)).query)
        place_id = (query.get("placeId") or [""])[0]
        instance_id = (query.get("gameInstanceId") or [""])[0]
        if place_id and instance_id:
            return (
                f"roblox://experiences/start?placeId={place_id}"
                f"&gameInstanceId={instance_id}"
            )

    return ""


async def _continue_intercepted(cdp: "_CDP", request_id: str) -> None:
    try:
        response = await cdp.call(
            "Fetch.continueResponse", {"requestId": request_id}, timeout=2.0
        )
        if not response.get("error"):
            return
    except Exception:
        pass
    try:
        await cdp.call(
            "Fetch.continueRequest", {"requestId": request_id}, timeout=2.0
        )
    except Exception:
        pass


class _CDP:
    def __init__(self, ws):
        self.ws = ws
        self._next_id = 1
        self._pending: Dict[int, asyncio.Future] = {}
        self.events: asyncio.Queue = asyncio.Queue()
        self._reader_task: Optional[asyncio.Task] = None

    async def start(self):
        self._reader_task = asyncio.create_task(self._reader())

    async def _reader(self):
        try:
            async for msg in self.ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    try:
                        data = msg.json()
                    except Exception:
                        continue
                    msg_id = data.get("id")
                    future = self._pending.pop(msg_id, None) if msg_id is not None else None
                    if future and not future.done():
                        future.set_result(data)
                    else:
                        await self.events.put(data)
                elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                    break
        except asyncio.CancelledError:
            raise
        except Exception:
            pass
        finally:
            for future in list(self._pending.values()):
                if not future.done():
                    future.set_exception(RuntimeError("CDP connection closed"))
            self._pending.clear()

    async def send(self, method: str, params: Optional[Dict[str, Any]] = None) -> int:
        msg_id = self._next_id
        self._next_id += 1
        await self.ws.send_json({"id": msg_id, "method": method, "params": params or {}})
        return msg_id

    async def call(
        self,
        method: str,
        params: Optional[Dict[str, Any]] = None,
        timeout: float = 5.0,
    ) -> Dict[str, Any]:
        msg_id = self._next_id
        self._next_id += 1
        future = asyncio.get_running_loop().create_future()
        self._pending[msg_id] = future
        try:
            await self.ws.send_json({"id": msg_id, "method": method, "params": params or {}})
            return await asyncio.wait_for(future, timeout=timeout)
        finally:
            self._pending.pop(msg_id, None)

    async def stop(self):
        if self._reader_task:
            self._reader_task.cancel()
            try:
                await self._reader_task
            except (asyncio.CancelledError, Exception):
                pass


def _page_state_expression() -> str:
    return (
        "(() => {"
        "  const title = document.title || '';"
        "  const text = document.body ? document.body.innerText.slice(0, 700) : '';"
        "  const widget = document.querySelector('.cf-turnstile');"
        "  const frame = document.querySelector('.cf-turnstile iframe');"
        "  let rect = null;"
        "  if (frame) {"
        "    const r = frame.getBoundingClientRect();"
        "    rect = {x: r.x, y: r.y, w: r.width, h: r.height};"
        "  }"
        "  return JSON.stringify({title, text, turnstile: !!widget, rect});"
        "})()"
    )


async def _read_page_state(cdp: _CDP) -> Dict[str, Any]:
    response = await cdp.call(
        "Runtime.evaluate",
        {"expression": _page_state_expression(), "returnByValue": True},
        timeout=3.0,
    )
    raw = (
        ((response.get("result") or {}).get("result") or {}).get("value")
        if response
        else ""
    )
    try:
        return json.loads(raw) if raw else {}
    except Exception:
        return {}


def _classify_page(state: Dict[str, Any]) -> Optional[ResolveResult]:
    title = str(state.get("title", ""))
    text = str(state.get("text", ""))
    haystack = f"{title}\n{text}"

    if "This find is over" in haystack:
        return ResolveResult("expired", message="xe33hunt says this find is over", title=title)

    if "Link not found" in haystack:
        return ResolveResult("not_found", message="xe33hunt link not found", title=title)

    if "Couldn't check you're not a bot" in haystack:
        return ResolveResult(
            "challenge_failed",
            message="Cloudflare rejected the browser verification",
            title=title,
        )

    return None


async def _try_turnstile_click(cdp: _CDP, state: Dict[str, Any]) -> bool:
    rect = state.get("rect") or {}
    try:
        x = float(rect.get("x", 0)) + 30.0
        y = float(rect.get("y", 0)) + float(rect.get("h", 65)) / 2.0
    except Exception:
        return False

    if x <= 0 or y <= 0:
        return False

    try:
        await cdp.call(
            "Input.dispatchMouseEvent",
            {"type": "mousePressed", "x": x, "y": y, "button": "left", "clickCount": 1},
            timeout=2.0,
        )
        await cdp.call(
            "Input.dispatchMouseEvent",
            {"type": "mouseReleased", "x": x, "y": y, "button": "left", "clickCount": 1},
            timeout=2.0,
        )
        return True
    except Exception:
        return False


async def _resolve_async(ws_url: str, url: str, timeout: float) -> ResolveResult:
    deadline = time.time() + timeout
    last_state_check = 0.0
    clicked_turnstile = False

    async with aiohttp.ClientSession() as session:
        async with session.ws_connect(ws_url, heartbeat=10, max_msg_size=4 * 1024 * 1024) as ws:
            cdp = _CDP(ws)
            await cdp.start()
            try:
                await cdp.call("Page.enable", timeout=3.0)
                await cdp.call("Network.enable", timeout=3.0)
                await cdp.call("Runtime.enable", timeout=3.0)
                await cdp.call(
                    "Fetch.enable",
                    {
                        "patterns": [
                            {
                                "urlPattern": _RE_XE33_JOIN_PATTERN,
                                "requestStage": "Response",
                            }
                        ]
                    },
                    timeout=3.0,
                )
                try:
                    await cdp.call("Page.navigate", {"url": url}, timeout=10.0)
                except Exception:
                    pass

                while time.time() < deadline:
                    remaining = max(0.1, deadline - time.time())
                    event = None
                    try:
                        event = await asyncio.wait_for(
                            cdp.events.get(), timeout=min(2.0, remaining)
                        )
                    except asyncio.TimeoutError:
                        pass

                    if event:
                        method = event.get("method")
                        params = event.get("params") or {}

                        if method == "Fetch.requestPaused":
                            request = params.get("request") or {}
                            request_id = params.get("requestId")
                            req_method = str(request.get("method", "")).upper()
                            status = params.get("responseStatusCode")
                            headers = params.get("responseHeaders") or []
                            location = _header_value(headers, "location")

                            if req_method == "POST":
                                if status in (301, 302, 303, 307, 308):
                                    resolved = _extract_protocol_url(location)
                                    if resolved:
                                        return ResolveResult(
                                            "resolved",
                                            roblox_url=resolved,
                                            message="Captured the Roblox redirect",
                                        )
                                if status == 200:
                                    body_text = ""
                                    try:
                                        body_response = await cdp.call(
                                            "Fetch.getResponseBody",
                                            {"requestId": request_id},
                                            timeout=3.0,
                                        )
                                        body = (body_response.get("result") or {}).get("body", "")
                                        if body:
                                            if (body_response.get("result") or {}).get("base64Encoded"):
                                                body = base64.b64decode(body).decode(
                                                    "utf-8", "replace"
                                                )
                                            body_text = body
                                    except Exception:
                                        pass
                                    resolved = _extract_protocol_url(body_text)
                                    if resolved:
                                        return ResolveResult(
                                            "resolved",
                                            roblox_url=resolved,
                                            message="Captured the Roblox link from the response",
                                        )
                                if status == 403:
                                    return ResolveResult(
                                        "challenge_failed",
                                        message="Cloudflare rejected the verification",
                                    )
                            elif req_method == "GET":
                                if status == 410:
                                    return ResolveResult(
                                        "expired",
                                        message="xe33hunt says this find is over",
                                    )
                                if status == 404:
                                    return ResolveResult(
                                        "not_found",
                                        message="xe33hunt link not found",
                                    )

                            await _continue_intercepted(cdp, str(request_id))

                        elif method in (
                            "Page.frameRequestedNavigation",
                            "Page.frameScheduledNavigation",
                        ):
                            resolved = _extract_protocol_url(str(params.get("url", "")))
                            if resolved:
                                return ResolveResult(
                                    "resolved",
                                    roblox_url=resolved,
                                    message="Captured the Roblox navigation",
                                )

                        elif method == "Network.requestWillBeSent":
                            request_url = str((params.get("request") or {}).get("url", ""))
                            resolved = _extract_protocol_url(request_url)
                            if resolved:
                                return ResolveResult(
                                    "resolved",
                                    roblox_url=resolved,
                                    message="Captured the Roblox request",
                                )

                    now = time.time()
                    if now - last_state_check >= 2.0:
                        last_state_check = now
                        try:
                            state = await _read_page_state(cdp)
                        except Exception:
                            state = {}
                        if state:
                            classified = _classify_page(state)
                            if classified:
                                return classified

                            if (
                                not clicked_turnstile
                                and state.get("turnstile")
                                and state.get("rect")
                                and now > deadline - timeout + 4.0
                            ):
                                clicked_turnstile = True
                                if await _try_turnstile_click(cdp, state):
                                    logger.info(
                                        "[GatewayResolver] Attempted the Turnstile checkbox"
                                    )

                return ResolveResult(
                    "timeout",
                    message="Timed out waiting for Cloudflare to reveal the join link",
                )
            finally:
                await cdp.stop()


def resolve_gateway_url(
    gateway_url: str,
    browser_id: str = "default",
    custom_path: str = "",
    timeout: float = _DEFAULT_TIMEOUT,
) -> ResolveResult:
    browser_path = _find_chromium_browser(browser_id, custom_path)
    if not browser_path:
        return ResolveResult(
            "unsupported",
            message="No Chromium browser (Brave, Chrome, or Edge) is available.",
        )

    port = _free_port()
    profile_dir = _profile_dir()
    proc: Optional[subprocess.Popen] = None

    try:
        logger.info(
            f"[GatewayResolver] Resolving protected link with {os.path.basename(browser_path)}"
        )
        proc = _launch_browser(browser_path, port, profile_dir)
        ws_url = _wait_for_page_target(port, timeout=10.0)
        if not ws_url:
            return ResolveResult(
                "error",
                message="The browser DevTools endpoint did not start.",
            )

        result = asyncio.run(_resolve_async(ws_url, gateway_url, timeout))
        logger.info(
            f"[GatewayResolver] Result: {result.status}"
            + (f" ({result.message})" if result.message else "")
        )
        return result
    except Exception as ex:
        logger.warning(f"[GatewayResolver] Resolution failed: {ex}")
        return ResolveResult("error", message=str(ex))
    finally:
        _kill_browser(proc)
