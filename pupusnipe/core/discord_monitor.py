"""
Real-Time Discord Monitoring Engine
Runs an authorized Discord Bot client in a dedicated asynchronous background thread.
Delivers zero-latency message inspection, embed parsing, keyword matching, microsecond timing, and instant Roblox launching.
"""
import sys
if hasattr(sys, "lazy_modules"):
    try:
        sys.lazy_modules.clear()
    except Exception:
        pass

import warnings
import traceback
import locale
import pkgutil

import asyncio
import threading
import time
from typing import List, Set, Dict, Any, Optional, Callable
import discord

from .detector import LinkDetector, ExtractedLink
from .matcher import KeywordMatcher, KeywordProfile, MatchResult
from .launcher import RobloxLauncher, LaunchResult
from .storage import StorageManager
from .config import AppConfig
from .logger import get_logger

logger = get_logger()


class DiscordMonitor:
    """Threaded Discord Bot event listener for private server link sniping."""

    def __init__(
        self,
        config: AppConfig,
        storage: StorageManager,
        detector: LinkDetector,
        matcher: KeywordMatcher,
        launcher: RobloxLauncher,
        on_status_change: Optional[Callable[[str, str], None]] = None,
        on_snipe_event: Optional[Callable[[Dict[str, Any]], None]] = None,
        on_message_scanned: Optional[Callable[[], None]] = None,
        on_channel_resolved: Optional[Callable[[str, str, str, str], None]] = None
    ):
        self.config = config
        self.storage = storage
        self.detector = detector
        self.matcher = matcher
        self.launcher = launcher

        # Callbacks to UI
        self.on_status_change = on_status_change
        self.on_snipe_event = on_snipe_event
        self.on_message_scanned = on_message_scanned
        self.on_channel_resolved = on_channel_resolved

        # State
        self.is_running = False
        self.is_paused = False
        self.is_locked = False
        self.monitored_channel_ids: Set[str] = set()
        self._resolved_channels: Set[str] = set()

        self._thread: Optional[threading.Thread] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._client: Optional[discord.Client] = None

        # Turnstile-protected gateway resolution state. Only one browser profile
        # can be used at a time, so resolution attempts are serialized.
        self._gateway_lock = threading.Lock()
        self._gateway_active_link: Optional[str] = None

    def set_monitored_channels(self, channel_ids: List[str]):
        """Updates the set of monitored channel IDs dynamically without restarting."""
        new_set = {str(cid).strip() for cid in channel_ids if str(cid).strip()}
        if new_set == self.monitored_channel_ids:
            return  # No change, prevent duplicate subscriptions and recursive UI loops
        self.monitored_channel_ids = new_set
        self._resolved_channels.clear()
        if self._client and self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(self._subscribe_monitored_channels(), self._loop)

    def _is_channel_monitored(self, channel_id: int, channel_obj: Optional[Any] = None, guild_obj: Optional[Any] = None) -> bool:
        """
        Determines if an incoming event channel is allowed.
        Supports direct channel IDs, thread parent channel IDs, and guild/server IDs.
        """
        if not self.monitored_channel_ids:
            return True  # No channel restrictions: monitor all visible channels

        cid_str = str(channel_id)
        if cid_str in self.monitored_channel_ids:
            return True

        if channel_obj:
            parent_id = getattr(channel_obj, "parent_id", None)
            if parent_id and str(parent_id) in self.monitored_channel_ids:
                return True

        guild = guild_obj or (getattr(channel_obj, "guild", None) if channel_obj else None)
        if guild and str(guild.id) in self.monitored_channel_ids:
            return True

        return False

    async def _subscribe_monitored_channels(self):
        """
        Subscribes to all connected guilds and specific monitored channels on Discord's gateway.
        Guarantees that large servers (>75,000 members) and channels stream MESSAGE_CREATE events in real time
        even when Discord Desktop is not open in the background.
        """
        if not self._client or not getattr(self._client, "_connection", None):
            return

        subs = getattr(self._client._connection, "subscriptions", None)
        if not subs:
            return

        # 1. Subscribe to all user guilds so large servers do not throttle messages
        for guild in list(self._client.guilds):
            try:
                await subs.subscribe_to(guild, typing=True, threads=True, activities=False, member_updates=False)
            except Exception:
                pass

        # 2. For each configured channel ID, ensure channel message streaming [0, 99] is active
        if self.monitored_channel_ids:
            subscribed_count = 0
            for cid_str in list(self.monitored_channel_ids):
                try:
                    cid = int(cid_str)
                    ch = self._client.get_channel(cid)
                    if not ch:
                        try:
                            ch = await self._client.fetch_channel(cid)
                        except Exception:
                            ch = None
                    if ch and hasattr(ch, "guild") and ch.guild:
                        guild = ch.guild
                        try:
                            await subs.subscribe_to(guild, typing=True, threads=True)
                        except Exception:
                            pass
                        await subs.subscribe_to_channels(guild, {cid: [(0, 99)]})
                        subscribed_count += 1
                        s_name = str(guild.name)
                        s_id = str(guild.id)
                        c_name = f"#{ch.name}" if hasattr(ch, "name") else f"channel-{cid_str[-4:]}"
                        try:
                            self.storage.update_channel_metadata(
                                channel_id=cid_str,
                                server_id=s_id,
                                server_name=s_name,
                                channel_name=c_name
                            )
                        except Exception:
                            pass
                        self._resolved_channels.add(cid_str)
                        if self.on_channel_resolved:
                            self.on_channel_resolved(cid_str, s_id, s_name, c_name)
                        logger.info(f"[Discord] Live channel stream active for {c_name} in '{s_name}'")
                except Exception as ex:
                    logger.debug(f"[Discord] Subscribed channel ping: {ex}")
            if subscribed_count > 0:
                logger.info(f"[Discord] Successfully subscribed to {subscribed_count} target channel(s) on Discord Gateway.")

    def start(self, token: str):
        """Starts Discord monitoring in a dedicated background thread."""
        if self.is_running:
            return

        self.is_running = True
        self.is_paused = False
        self.is_locked = False

        self._thread = threading.Thread(target=self._run_bot_thread, args=(token,), daemon=True, name="DiscordMonitorThread")
        self._thread.start()

    def pause(self):
        """Pauses processing incoming links without disconnecting from Discord."""
        self.is_paused = True
        if self.on_status_change:
            self.on_status_change("PAUSED", "Monitoring paused")
        logger.info("[Discord] Monitoring paused.")

    def resume(self, force: bool = False):
        """Resumes link processing unless locked by biome camping."""
        if self.is_locked and not force:
            logger.info("[Discord] Resume suppressed: Biome camping lock is active.")
            return
        self.is_paused = False
        if self.on_status_change:
            self.on_status_change("MONITORING", "Monitoring active")
        logger.info("[Discord] Monitoring resumed.")

    def lock_for_camping(self):
        """Locks sniper to prevent any automatic hopping while fishing in target biome."""
        self.is_locked = True
        self.pause()
        logger.info("[Discord] Sniper locked in target biome. Server hops disabled until biome expires.")

    def unlock_from_camping(self):
        """Unlocks sniper when target biome expires, immediately resuming hunt."""
        self.is_locked = False
        self.resume(force=True)
        logger.info("[Discord] Sniper unlocked. Resumed hunting for next target biome.")

    def stop(self):
        """Stops the Discord bot and closes the background loop."""
        self.is_running = False
        self.is_paused = False

        if self._client and self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(self._client.close(), self._loop)

        if self.on_status_change:
            self.on_status_change("STOPPED", "Sniper stopped")
        logger.info("[Discord] Bot disconnected & sniper stopped.")

    def _run_bot_thread(self, token: str):
        """Dedicated asyncio event loop thread for discord.py."""
        # Ensure ThreadPoolExecutor is resolved and patched before asyncio creates any executor
        try:
            import concurrent.futures.thread
            import concurrent.futures
            concurrent.futures.ThreadPoolExecutor = concurrent.futures.thread.ThreadPoolExecutor
        except Exception:
            pass

        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)

        # Pre-assign default ThreadPoolExecutor to prevent asyncio from calling unresolved lazy ThreadPoolExecutor
        try:
            import concurrent.futures.thread
            self._default_executor = concurrent.futures.thread.ThreadPoolExecutor(thread_name_prefix="asyncio")
            self._loop.set_default_executor(self._default_executor)
        except Exception:
            pass

        # Initialize discord.py-self client matching Sol Sniper V3
        self._client = discord.Client(
            chunk_guilds_at_startup=False,
            member_cache_flags=discord.MemberCacheFlags.none(),
            fetch_offline_members=False
        )

        @self._client.event
        async def on_ready():
            user_tag = f"{self._client.user.name}" if self._client.user else "User"
            guild_count = len(self._client.guilds)
            logger.info(f"[Discord] Connected as {user_tag} across {guild_count} server(s).")
            if self.on_status_change:
                self.on_status_change("CONNECTED", f"Connected as {user_tag} ({guild_count} servers)")
            # Asynchronously subscribe to guilds and target channels immediately
            asyncio.create_task(self._subscribe_monitored_channels())

        @self._client.event
        async def on_guild_join(guild: discord.Guild):
            if hasattr(self._client._connection, "subscriptions"):
                try:
                    await self._client._connection.subscriptions.subscribe_to(guild, typing=True, threads=True)
                except Exception:
                    pass

        @self._client.event
        async def on_disconnect():
            if self.is_running and self.on_status_change:
                self.on_status_change("RECONNECTING", "Connection lost, auto-reconnecting...")
            logger.warning("[Discord] Connection lost. Attempting auto-reconnect...")

        @self._client.event
        async def on_resumed():
            if self.is_running and self.on_status_change:
                self.on_status_change("CONNECTED", "Discord session resumed")
            logger.info("[Discord] Gateway session resumed successfully.")
            asyncio.create_task(self._subscribe_monitored_channels())

        @self._client.event
        async def on_message(message: discord.Message):
            if not self.is_running:
                return

            if not self._is_channel_monitored(message.channel.id, message.channel, message.guild):
                return

            if message.author == self._client.user:
                return

            # T0: Timestamp message reception immediately
            t_recv = time.time()

            if self.on_message_scanned:
                self.on_message_scanned()

            if self.is_paused:
                return

            # Ultra-low latency synchronous execution
            self._process_message_instant(message, t_recv)

        @self._client.event
        async def on_message_edit(before: discord.Message, after: discord.Message):
            if not self.is_running:
                return

            if not self._is_channel_monitored(after.channel.id, after.channel, after.guild):
                return

            if after.author == self._client.user:
                return

            t_recv = time.time()
            if self.on_message_scanned:
                self.on_message_scanned()

            if self.is_paused:
                return

            # Process updated embed or button components
            self._process_message_instant(after, t_recv)

        @self._client.event
        async def on_raw_message_edit(payload: discord.RawMessageUpdateEvent):
            if not self.is_running or self.is_paused:
                return

            guild_obj = self._client.get_guild(payload.guild_id) if getattr(payload, "guild_id", None) else None
            channel_obj = self._client.get_channel(payload.channel_id)
            if not self._is_channel_monitored(payload.channel_id, channel_obj, guild_obj):
                return

            # If cached message was already dispatched in on_message_edit, skip redundant call
            if getattr(payload, "cached_message", None):
                return

            try:
                channel = channel_obj or self._client.get_channel(payload.channel_id)
                if channel:
                    msg = await channel.fetch_message(payload.message_id)
                    if msg and msg.author != self._client.user:
                        self._process_message_instant(msg, time.time())
            except Exception:
                pass

        try:
            self._loop.run_until_complete(self._client.start(token.strip()))
        except Exception as ex:
            import traceback
            tb = traceback.format_exc()
            if self.is_running and self.on_status_change:
                self.on_status_change("ERROR", f"Bot error: {str(ex)}")
            logger.error(f"[Discord] Bot error: {str(ex)}\n{tb}")
        finally:
            self.is_running = False
            if hasattr(self, "_default_executor") and self._default_executor:
                try:
                    self._default_executor.shutdown(wait=False, cancel_futures=True)
                except Exception:
                    pass

    def _process_message_instant(self, message: discord.Message, t_recv: float):
        """
        Ultra-low latency message evaluation and launching pipeline.
        Measures and logs exact timestamps for:
          - Message reception
          - URL extraction
          - Keyword matching
          - Launch initiation
          - Actual measured detection-to-launch time
        """
        # Dynamically record resolved channel and server metadata for the Servers tab
        if message.channel and hasattr(message.channel, "id"):
            cid_str = str(message.channel.id)
            if cid_str in self.monitored_channel_ids and cid_str not in self._resolved_channels:
                s_name = str(message.guild.name) if message.guild else "Direct"
                s_id = str(message.guild.id) if message.guild else "0"
                c_name = f"#{message.channel.name}" if hasattr(message.channel, "name") else f"channel-{cid_str[-4:]}"
                try:
                    self.storage.update_channel_metadata(cid_str, s_id, s_name, c_name)
                    self._resolved_channels.add(cid_str)
                    if self.on_channel_resolved:
                        self.on_channel_resolved(cid_str, s_id, s_name, c_name)
                except Exception:
                    pass

        # Step 1: URL Extraction (from Content, Embeds, Fields, and Component Buttons)
        embeds_data = [e.to_dict() for e in message.embeds] if message.embeds else []
        components_data = getattr(message, "components", [])
        attachments_data = getattr(message, "attachments", [])
        extracted_link, combined_text = self.detector.extract_from_message(
            content=message.content,
            embeds=embeds_data,
            components=components_data,
            attachments=attachments_data,
            raw_message=message
        )
        t_extracted = time.time()
        extract_latency_ms = (t_extracted - t_recv) * 1000.0

        if not extracted_link or not extracted_link.is_valid:
            if extracted_link and extracted_link.is_phishing:
                logger.warning(
                    f"[ANTI-BAIT] Phishing / Malicious redirect blocked from {message.author} "
                    f"in #{getattr(message.channel, 'name', 'direct')}: {extracted_link.error_reason}"
                )
                self._record_event(
                    server_name=message.guild.name if message.guild else "DM",
                    channel_name=message.channel.name if hasattr(message.channel, "name") else "Direct",
                    author_name=str(message.author),
                    profile_name="ANTI-BAIT",
                    keyword="PHISHING_ATTEMPT",
                    link_code="",
                    protocol_url="",
                    latency_ms=extract_latency_ms,
                    breakdown={"extract_ms": extract_latency_ms},
                    status="BLOCKED",
                    error_reason=extracted_link.error_reason,
                    timestamps={"received": t_recv, "extracted": t_extracted}
                )
            return

        # Step 2: Keyword Profile Matching & Anti-Bait Evaluation
        match: MatchResult = self.matcher.evaluate(
            text=combined_text,
            author_id=str(message.author.id),
            author_name=str(message.author.name)
        )
        t_matched = time.time()
        match_latency_ms = (t_matched - t_extracted) * 1000.0

        if not match.matched:
            if match.is_blacklisted:
                logger.info(f"[ANTI-BAIT] Ignored message from blacklisted author or containing bait word ({match.reason})")
                self._record_event(
                    server_name=message.guild.name if message.guild else "DM",
                    channel_name=message.channel.name if hasattr(message.channel, "name") else "Direct",
                    author_name=str(message.author),
                    profile_name="ANTI-BAIT",
                    keyword=match.matched_keyword or "BLACKLISTED",
                    link_code=extracted_link.link_code,
                    protocol_url=extracted_link.protocol_url,
                    latency_ms=(t_matched - t_recv) * 1000.0,
                    breakdown={"extract_ms": extract_latency_ms, "match_ms": match_latency_ms},
                    status="BLOCKED",
                    error_reason=match.reason,
                    timestamps={"received": t_recv, "extracted": t_extracted, "matched": t_matched}
                )
                return

            # If join_all_in_monitored_channels is enabled, accept any valid Sol's RNG private server link
            # in monitored channel(s) or across all channels if no specific channel restriction is set.
            if getattr(self.config, "join_all_in_monitored_channels", True):
                match = MatchResult(
                    matched=True,
                    profile=KeywordProfile(id="direct_link", name="Direct Link", priority=10),
                    matched_keyword="DIRECT_LINK",
                    reason="Direct private server link snipe"
                )
            else:
                return

        # Step 2.5: Global 10-minute Post-Join Cooldown Check
        if self.launcher.is_on_global_cooldown():
            rem = self.launcher.get_cooldown_remaining()
            mins = int(rem // 60)
            secs = int(rem % 60)
            logger.info(
                f"[SNIPER] Private server link detected from {message.author} in #{getattr(message.channel, 'name', 'direct')}, "
                f"but 10-minute join cooldown is ACTIVE ({mins}m {secs:02d}s remaining). Server hop prevented. (Click 'Reset Cooldown' to bypass)"
            )
            self._record_event(
                server_name=message.guild.name if message.guild else "DM",
                channel_name=message.channel.name if hasattr(message.channel, "name") else "Direct",
                author_name=str(message.author),
                profile_name=match.profile.name if match.profile else "Match",
                keyword=match.matched_keyword or "",
                link_code=extracted_link.link_code,
                protocol_url=extracted_link.protocol_url,
                latency_ms=(t_matched - t_recv) * 1000.0,
                breakdown={"extract_ms": extract_latency_ms, "match_ms": match_latency_ms},
                status="COOLDOWN",
                error_reason=f"10m join cooldown ({mins}m {secs:02d}s remaining)",
                timestamps={"received": t_recv, "extracted": t_extracted, "matched": t_matched}
            )
            return

        # Step 3: Duplicate Cooldown Check
        if self.launcher.is_duplicate(extracted_link.link_code):
            logger.info(f"[SNIPER] Duplicate link ignored (code: {extracted_link.link_code[:8]}...) - Active cooldown")
            self._record_event(
                server_name=message.guild.name if message.guild else "DM",
                channel_name=message.channel.name if hasattr(message.channel, "name") else "Direct",
                author_name=str(message.author),
                profile_name=match.profile.name if match.profile else "Match",
                keyword=match.matched_keyword or "",
                link_code=extracted_link.link_code,
                protocol_url=extracted_link.protocol_url,
                latency_ms=(t_matched - t_recv) * 1000.0,
                breakdown={"extract_ms": extract_latency_ms, "match_ms": match_latency_ms},
                status="DUPLICATE",
                error_reason="Link previously joined (cooldown active)",
                timestamps={"received": t_recv, "extracted": t_extracted, "matched": t_matched}
            )
            return

        # Step 3.5: Turnstile-protected join page (xe33hunt)
        #
        # These pages hide the real Roblox URL behind Cloudflare. Resolve them in
        # an off-screen Chromium browser on a background thread, then hand the
        # captured roblox:// URL to the same native launcher used for every other
        # link. Never run this on Discord's event loop.
        if (
            extracted_link.link_type == "webgateway"
            and getattr(self.config, "auto_join", True)
            and getattr(self.config, "gateway_resolver_enabled", True)
        ):
            snapshot = {
                "server_name": message.guild.name if message.guild else "DM",
                "channel_name": message.channel.name if hasattr(message.channel, "name") else "Direct",
                "author_name": str(message.author),
                "profile_name": match.profile.name if match.profile else "Match",
                "keyword": match.matched_keyword or "",
                "link_code": extracted_link.link_code,
                "gateway_url": extracted_link.protocol_url,
            }
            if self._begin_gateway_resolution(extracted_link.link_code):
                logger.info(
                    f"[GatewayResolver] Protected link detected from {snapshot['author_name']} "
                    f"in #{snapshot['channel_name']}. Resolving off-screen..."
                )
                threading.Thread(
                    target=self._resolve_web_gateway_worker,
                    args=(
                        snapshot,
                        match,
                        t_recv,
                        t_extracted,
                        t_matched,
                        extract_latency_ms,
                        match_latency_ms,
                    ),
                    daemon=True,
                    name="PupuSnipeGatewayResolver",
                ).start()
            else:
                logger.info(
                    "[GatewayResolver] Another protected link is already resolving; "
                    f"skipping {extracted_link.link_code[:8]}..."
                )
            return

        # Step 4: Instant Launch Initiation
        launch_result: Optional[LaunchResult] = None
        if self.config.auto_join:
            launch_result = self.launcher.launch(
                protocol_url=extracted_link.protocol_url,
                link_code=extracted_link.link_code,
                method=self.config.launch_method,
                client=getattr(self.config, "roblox_client", "voidstrap"),
                recv_time=t_recv,
                extract_time=t_extracted,
                match_time=t_matched,
                close_roblox_before=getattr(self.config, "close_roblox_before_joining", False),
                leave_game_before=getattr(self.config, "leave_game_before_joining", False),
                minimize_other=getattr(self.config, "minimize_other_windows", False)
            )

            # Auto Pause Sniper upon snipe if configured (Sol Sniper V3 feature)
            if getattr(self.config, "auto_pause_sniper", False) and match.profile and match.profile.pause_duration > 0:
                self.pause()
                logger.info(f"[SNIPER] Auto-paused sniper for {match.profile.pause_duration}s after sniping {match.profile.name}")
                threading.Timer(match.profile.pause_duration, self.resume).start()

        total_latency = launch_result.latency_ms if launch_result else (time.time() - t_recv) * 1000.0
        breakdown = launch_result.breakdown if launch_result else {
            "extract_ms": extract_latency_ms,
            "match_ms": match_latency_ms,
            "total_ms": total_latency
        }
        status_str = "JOINED" if (launch_result and launch_result.success) else ("DETECTED" if not self.config.auto_join else "ERROR")
        err_str = launch_result.error_message if launch_result and not launch_result.success else ""

        # Immediately lock sniper upon launch so we never spam hop while Roblox is opening and loading
        if status_str == "JOINED":
            self.lock_for_camping()

        # Rich Diagnostic Logging exactly as specified in prompt
        t_recv_str = time.strftime("%H:%M:%S", time.localtime(t_recv)) + f".{int((t_recv % 1) * 1000):03d}"
        logger.info(
            f"\n"
            f"================================================================================\n"
            f"⚡ [SNIPER EVENT] {status_str} | Target Profile: {match.profile.name if match.profile else 'Unknown'}\n"
            f"  ├─ Message Recv Time:  {t_recv_str} ({t_recv:.6f})\n"
            f"  ├─ Origin:             {message.guild.name if message.guild else 'DM'} / #{getattr(message.channel, 'name', 'direct')} by {message.author}\n"
            f"  ├─ Matched Keyword:    '{match.matched_keyword}' (Priority: {match.profile.priority if match.profile else 0})\n"
            f"  ├─ Protocol URL:       {extracted_link.protocol_url}\n"
            f"  ├─ Timing Breakdown:\n"
            f"  │    ├─ URL Extraction:   {breakdown.get('extract_ms', 0.0):.2f} ms\n"
            f"  │    ├─ Keyword Matching: {breakdown.get('match_ms', 0.0):.2f} ms\n"
            f"  │    └─ Launch Execution: {breakdown.get('launch_exec_ms', 0.0):.2f} ms ({self.config.launch_method})\n"
            f"  └─ TOTAL DETECT-TO-LAUNCH TIME: {total_latency:.2f} ms [{'SUCCESS' if status_str == 'JOINED' else status_str}]\n"
            f"================================================================================"
        )

        self._record_event(
            server_name=message.guild.name if message.guild else "DM",
            channel_name=message.channel.name if hasattr(message.channel, "name") else "Direct",
            author_name=str(message.author),
            profile_name=match.profile.name if match.profile else "Match",
            keyword=match.matched_keyword or "",
            link_code=extracted_link.link_code,
            protocol_url=extracted_link.protocol_url,
            latency_ms=total_latency,
            breakdown=breakdown,
            status=status_str,
            error_reason=err_str,
            timestamps=launch_result.timestamps if launch_result else {"received": t_recv}
        )

    def _begin_gateway_resolution(self, link_code: str) -> bool:
        """Claims the single off-screen browser slot for a protected link."""
        with self._gateway_lock:
            if self._gateway_active_link is not None:
                return False
            self._gateway_active_link = link_code
            return True

    def _end_gateway_resolution(self):
        with self._gateway_lock:
            self._gateway_active_link = None

    def _resolve_web_gateway_worker(
        self,
        snapshot: Dict[str, str],
        match: MatchResult,
        t_recv: float,
        t_extracted: float,
        t_matched: float,
        extract_latency_ms: float,
        match_latency_ms: float,
    ):
        """Background worker: resolve Turnstile, then use the native launcher."""
        launch_result: Optional[LaunchResult] = None
        resolution = None
        try:
            try:
                launch_result, resolution = self.launcher.resolve_and_launch_web_gateway(
                    gateway_url=snapshot["gateway_url"],
                    link_code=snapshot["link_code"],
                    method=self.config.launch_method,
                    client=getattr(self.config, "roblox_client", "voidstrap"),
                    recv_time=t_recv,
                    extract_time=t_extracted,
                    match_time=t_matched,
                    close_roblox_before=getattr(self.config, "close_roblox_before_joining", False),
                    leave_game_before=getattr(self.config, "leave_game_before_joining", False),
                    minimize_other=getattr(self.config, "minimize_other_windows", False),
                )
            except Exception:
                logger.error(
                    "[GatewayResolver] Unhandled resolution error:\n"
                    f"{traceback.format_exc()}"
                )

            resolve_status = getattr(resolution, "status", "error") if resolution else "error"
            resolve_message = getattr(resolution, "message", "") if resolution else ""
            success = bool(launch_result and launch_result.success)
            error_text = (
                launch_result.error_message
                if launch_result and launch_result.error_message
                else resolve_message
            )

            if success:
                status_str = "JOINED"
            elif resolve_status == "expired":
                status_str = "EXPIRED"
            elif resolve_status == "not_found":
                status_str = "NOT_FOUND"
            elif "cooldown" in error_text.lower():
                status_str = "COOLDOWN"
            elif "duplicate" in error_text.lower():
                status_str = "DUPLICATE"
            else:
                status_str = "ERROR"

            err_str = "" if success else (error_text or "Protected link resolution failed")
            total_latency = (
                launch_result.latency_ms
                if launch_result
                else (time.time() - t_recv) * 1000.0
            )
            if launch_result:
                breakdown = dict(launch_result.breakdown)
            else:
                breakdown = {
                    "extract_ms": extract_latency_ms,
                    "match_ms": match_latency_ms,
                    "total_ms": total_latency,
                }
            if resolution is not None and "resolve_ms" not in breakdown:
                breakdown["resolve_ms"] = 0.0

            logger.info(
                f"\n"
                f"================================================================================\n"
                f"⚡ [SNIPER EVENT] {status_str} | Protected Join Page ({resolve_status})\n"
                f"  ├─ Origin:             {snapshot['server_name']} / #{snapshot['channel_name']} by {snapshot['author_name']}\n"
                f"  ├─ Target Profile:     {snapshot['profile_name']} (Keyword: '{snapshot['keyword']}')\n"
                f"  ├─ Protected URL:      {snapshot['gateway_url']}\n"
                f"  ├─ Captured Native:    {getattr(resolution, 'roblox_url', '') or '—'}\n"
                f"  ├─ Resolver Status:    {resolve_status}"
                + (f" ({resolve_message})" if resolve_message else "")
                + "\n"
                f"  └─ TOTAL DETECT-TO-LAUNCH TIME: {total_latency:.2f} ms "
                f"[{'SUCCESS' if success else status_str}]\n"
                f"================================================================================"
            )

            if success:
                # Same post-join behavior as a direct link.
                if (
                    getattr(self.config, "auto_pause_sniper", False)
                    and match.profile
                    and match.profile.pause_duration > 0
                ):
                    self.pause()
                    logger.info(
                        f"[SNIPER] Auto-paused sniper for {match.profile.pause_duration}s "
                        f"after sniping {match.profile.name}"
                    )
                    threading.Timer(match.profile.pause_duration, self.resume).start()
                self.lock_for_camping()

            self._record_event(
                server_name=snapshot["server_name"],
                channel_name=snapshot["channel_name"],
                author_name=snapshot["author_name"],
                profile_name=snapshot["profile_name"],
                keyword=snapshot["keyword"],
                link_code=snapshot["link_code"],
                # Keep the original protected URL in the event so the Discord
                # webhook renders a clickable page instead of a bogus code link.
                protocol_url=snapshot["gateway_url"],
                latency_ms=total_latency,
                breakdown=breakdown,
                status=status_str,
                error_reason=err_str,
                timestamps=(
                    launch_result.timestamps
                    if launch_result
                    else {
                        "received": t_recv,
                        "extracted": t_extracted,
                        "matched": t_matched,
                    }
                ),
            )
        finally:
            self._end_gateway_resolution()

    def _record_event(
        self,
        server_name: str,
        channel_name: str,
        author_name: str,
        profile_name: str,
        keyword: str,
        link_code: str,
        protocol_url: str,
        latency_ms: float,
        breakdown: Dict[str, float],
        status: str,
        error_reason: str = "",
        timestamps: Dict[str, float] = None
    ):
        self.storage.add_history_entry(
            server_name=server_name,
            channel_name=channel_name,
            author_name=author_name,
            profile_name=profile_name,
            keyword=keyword,
            link_code=link_code,
            protocol_url=protocol_url,
            latency_ms=latency_ms,
            status=status,
            error_reason=error_reason
        )

        if self.on_snipe_event:
            event_data = {
                "timestamp": timestamps.get("received", time.time()) if timestamps else time.time(),
                "server_name": server_name,
                "channel_name": channel_name,
                "author_name": author_name,
                "profile_name": profile_name,
                "keyword": keyword,
                "link_code": link_code,
                "protocol_url": protocol_url,
                "latency_ms": latency_ms,
                "breakdown": breakdown,
                "status": status,
                "error_reason": error_reason,
                "timestamps": timestamps or {}
            }
            self.on_snipe_event(event_data)
