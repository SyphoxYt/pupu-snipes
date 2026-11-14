"""
PupuSnipe Main Application Window
Modern cyberpunk dark themed desktop GUI with sidebar navigation, stats, and real-time event pipeline.
Features animated tab transitions, pulsing status indicators, and responsive scrollable layout.
"""
import os
import sys
import time
from PySide6 import QtCore, QtGui, QtWidgets

from ..core.config import APP_NAME, APP_VERSION, AppConfig, DEFAULT_SOLS_RNG_PLACE_ID
from ..core.storage import StorageManager
from ..core.detector import LinkDetector
from ..core.matcher import KeywordMatcher
from ..core.launcher import RobloxLauncher
from ..core.discord_monitor import DiscordMonitor
from ..core.hotkeys import HotkeyManager
from ..core.fishsol import FishSolEngine
from ..core.log_watcher import RobloxLogWatcher
from ..core.sounds import SoundManager
from ..core.webhook import WebhookNotifier
from ..core.logger import setup_logger, get_logger

from .theme import DARK_THEME_QSS
from .tabs.dashboard_tab import DashboardTab
from .tabs.sniper_tab import SniperTab
from .tabs.fishing_tab import FishingTab
from .tabs.servers_tab import ServersTab
from .tabs.keywords_tab import KeywordsTab
from .tabs.misc_tab import MiscTab
from .tabs.settings_tab import SettingsTab

logger = get_logger()


class MainWindow(QtWidgets.QMainWindow):
    # Signals for thread-safe cross-thread UI updates
    sig_status_update = QtCore.Signal(str, str)
    sig_snipe_event = QtCore.Signal(dict)
    sig_message_scanned = QtCore.Signal()
    sig_log_received = QtCore.Signal(str)
    sig_fishing_status = QtCore.Signal(str)
    sig_fishing_stats = QtCore.Signal(dict)
    sig_biome_detected = QtCore.Signal(str)
    sig_aura_detected = QtCore.Signal(str)
    sig_hotkey_toggle = QtCore.Signal()
    sig_hotkey_pause = QtCore.Signal()
    sig_hotkey_resume = QtCore.Signal()
    sig_hotkey_stop = QtCore.Signal()
    sig_hotkey_fish = QtCore.Signal()
    sig_hotkey_reset_cd = QtCore.Signal()
    sig_channel_resolved = QtCore.Signal(str, str, str, str)
    sig_webhook_test_result = QtCore.Signal(bool, str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} - Sol's RNG Private Server Sniper & Fishing Macro v{APP_VERSION}")
        self.resize(1220, 780)
        self.setMinimumSize(980, 640)

        # 1. Initialize Core Engines & Load Persisted Settings
        self.config = AppConfig()
        self.storage = StorageManager()
        self._load_persisted_settings()

        # Snipe sound + Discord webhook dispatchers
        self.sound_manager = SoundManager(
            preset_id=getattr(self.config, "sound_preset", "chime"),
            custom_path=getattr(self.config, "custom_sound_path", ""),
        )
        self.webhook_notifier = WebhookNotifier()

        self.detector = LinkDetector(target_place_id=getattr(self.config, "place_id", DEFAULT_SOLS_RNG_PLACE_ID))
        self.detector.strict_place_id = bool(self.config.only_join_sols_links)
        self.detector.snipe_ropro = bool(self.config.snipe_ropro_links)
        self.detector.snipe_joinrbx = bool(self.config.snipe_joinrbx_links)
        self.detector.snipe_roseal = bool(self.config.snipe_roseal_links)
        self.detector.snipe_fishstrap = bool(self.config.snipe_fishstrap_links)
        self.detector.snipe_joingate = bool(getattr(self.config, "snipe_joingate_links", True))

        self.matcher = KeywordMatcher()
        self.launcher = RobloxLauncher(cooldown_seconds=self.config.duplicate_cooldown_sec)
        self.launcher.gateway_browser = str(getattr(self.config, "gateway_browser", "default") or "default")
        self.launcher.gateway_browser_path = str(getattr(self.config, "gateway_browser_path", "") or "")

        # Fishing Engine
        self.fishsol = FishSolEngine(
            on_status_change=lambda txt: self.sig_fishing_status.emit(txt),
            on_stats_update=lambda stats: self.sig_fishing_stats.emit(stats)
        )
        self._load_persisted_fishing_settings()

        # Discord Monitor
        self.monitor = DiscordMonitor(
            config=self.config,
            storage=self.storage,
            detector=self.detector,
            matcher=self.matcher,
            launcher=self.launcher,
            on_status_change=lambda st, txt: self.sig_status_update.emit(st, txt),
            on_snipe_event=lambda ev: self.sig_snipe_event.emit(ev),
            on_message_scanned=lambda: self.sig_message_scanned.emit(),
            on_channel_resolved=lambda cid, sid, sname, cname: self.sig_channel_resolved.emit(cid, sid, sname, cname)
        )

        # Bloxstrap & Roblox Log Watcher
        self.log_watcher = RobloxLogWatcher(
            on_biome_change=lambda b: self.sig_biome_detected.emit(b),
            on_aura_change=lambda a: self.sig_aura_detected.emit(a)
        )
        self.log_watcher.start()

        # Connect Global Hotkeys via thread-safe Qt Signals
        self.sig_hotkey_toggle.connect(self.toggle_sniper)
        self.sig_hotkey_pause.connect(self.pause_sniper)
        self.sig_hotkey_resume.connect(self.resume_sniper)
        self.sig_hotkey_stop.connect(self.stop_sniper)
        self.sig_hotkey_fish.connect(self.toggle_fishing)
        self.sig_hotkey_reset_cd.connect(self.reset_join_cooldown)

        self.hotkeys = HotkeyManager(
            on_toggle=lambda: self.sig_hotkey_toggle.emit(),
            on_pause=lambda: self.sig_hotkey_pause.emit(),
            on_resume=lambda: self.sig_hotkey_resume.emit(),
            on_emergency_stop=lambda: self.sig_hotkey_stop.emit(),
            on_fish=lambda: self.sig_hotkey_fish.emit(),
            on_reset_cooldown=lambda: self.sig_hotkey_reset_cd.emit()
        )
        self.hotkeys.start()

        # Connect internal Qt signals
        self.sig_status_update.connect(self._on_discord_status_changed)
        self.sig_snipe_event.connect(self._on_snipe_event_received)
        self.sig_message_scanned.connect(self._on_message_scanned_event)
        self.sig_log_received.connect(self._on_log_line_received)
        self.sig_fishing_status.connect(self._on_fishing_status)
        self.sig_fishing_stats.connect(self._on_fishing_stats)
        self.sig_biome_detected.connect(self._on_biome_changed)
        self.sig_aura_detected.connect(self._on_aura_changed)
        self.sig_channel_resolved.connect(self._on_channel_resolved)

        # Connect logger to UI
        setup_logger(on_log_callback=lambda line: self.sig_log_received.emit(line))

        # Metrics Tracking
        self.total_scanned = 0
        self.total_detected = 0
        self.total_joined = 0
        self.latencies = []
        self.fastest_latency = 999999.0
        self.current_biome = "Unknown"
        self.current_aura = "None"
        self._pulse_state = False
        self.is_biome_locked = False

        # 2. Setup UI
        self._set_app_icon()
        self.setStyleSheet(DARK_THEME_QSS)
        self._init_layout()

        # Connect settings tab UI scale signal
        self.tab_settings.sig_ui_scale_changed.connect(self._on_ui_scale_changed)

        # Restore window geometry & UI scaling
        self._restore_window_geometry()
        self._apply_ui_scale(getattr(self.config, "ui_scale", 1.0))

        # Push loaded settings to UI controls
        self.tab_sniper.load_settings(self.config)
        self.tab_fishing.load_settings(self.storage)
        self.tab_misc.load_settings()
        self.tab_settings.load_settings()

        # 3. Process Checker Timer
        self.proc_timer = QtCore.QTimer(self)
        self.proc_timer.setInterval(2000)
        self.proc_timer.timeout.connect(self._check_roblox_process)
        self.proc_timer.start()

        # 4. Animated Status Pulse Timer
        self.pulse_timer = QtCore.QTimer(self)
        self.pulse_timer.setInterval(650)
        self.pulse_timer.timeout.connect(self._pulse_status_animation)
        self.pulse_timer.start()

        # Initial data sync
        self._sync_profiles()
        self._sync_channels()
        self._sync_blacklists()

        logger.info(f"{APP_NAME} v{APP_VERSION} initialized successfully.")

    def _set_app_icon(self):
        assets_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets")
        ico_path = os.path.join(assets_dir, "icon.ico")
        png_path = os.path.join(assets_dir, "logo.png")
        if os.path.exists(ico_path):
            self.setWindowIcon(QtGui.QIcon(ico_path))
        elif os.path.exists(png_path):
            self.setWindowIcon(QtGui.QIcon(png_path))

    def _init_layout(self):
        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)
        root_layout = QtWidgets.QHBoxLayout(central_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # --- Sidebar ---
        sidebar = QtWidgets.QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(224)
        sidebar_layout = QtWidgets.QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(14, 20, 14, 16)
        sidebar_layout.setSpacing(8)

        # Branding Header
        brand_box = QtWidgets.QHBoxLayout()
        brand_box.setSpacing(10)

        logo_label = QtWidgets.QLabel()
        assets_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets")
        png_path = os.path.join(assets_dir, "logo.png")
        if os.path.exists(png_path):
            pix = QtGui.QPixmap(png_path).scaled(36, 36, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
            logo_label.setPixmap(pix)
        brand_box.addWidget(logo_label)

        title_box = QtWidgets.QVBoxLayout()
        title_box.setSpacing(0)
        brand_title = QtWidgets.QLabel(APP_NAME)
        brand_title.setObjectName("brandTitle")
        brand_sub = QtWidgets.QLabel("Sol's RNG Sniper & Fish")
        brand_sub.setObjectName("brandSubtitle")
        title_box.addWidget(brand_title)
        title_box.addWidget(brand_sub)
        brand_box.addLayout(title_box)
        brand_box.addStretch()

        sidebar_layout.addLayout(brand_box)
        sidebar_layout.addSpacing(16)

        # Nav Buttons
        self.nav_group = QtWidgets.QButtonGroup(self)
        self.nav_group.setExclusive(True)

        nav_items = [
            ("📊  Dashboard", 0),
            ("⚡  Sniper", 1),
            ("🎣  Fishing", 2),
            ("🌐  Servers", 3),
            ("🏷️  Keywords", 4),
            ("🛡️  Miscellaneous", 5),
            ("⚙️  Settings & Logs", 6),
        ]

        self.nav_buttons = []
        for text, index in nav_items:
            btn = QtWidgets.QPushButton(text)
            btn.setProperty("class", "nav-btn")
            btn.setCheckable(True)
            if index == 0:
                btn.setChecked(True)
            btn.clicked.connect(lambda checked, idx=index: self._switch_tab(idx))
            self.nav_group.addButton(btn, index)
            sidebar_layout.addWidget(btn)
            self.nav_buttons.append(btn)

        sidebar_layout.addStretch()

        # Engine Quick Status in Sidebar
        self.lbl_sidebar_status = QtWidgets.QLabel("● Engine: Idle")
        self.lbl_sidebar_status.setStyleSheet("color: #64748b; font-size: 11px; font-weight: 700; padding: 6px;")
        sidebar_layout.addWidget(self.lbl_sidebar_status)

        root_layout.addWidget(sidebar)

        # --- Stacked Content Tabs with Animation Effect ---
        self.tab_stack = QtWidgets.QStackedWidget()
        self.tab_opacity = QtWidgets.QGraphicsOpacityEffect(self.tab_stack)
        self.tab_opacity.setOpacity(1.0)
        self.tab_stack.setGraphicsEffect(self.tab_opacity)

        # 0. Dashboard Tab
        self.tab_dashboard = DashboardTab(self)
        self.tab_dashboard.sig_toggle_sniper.connect(self.toggle_sniper)
        self.tab_dashboard.sig_toggle_fishsol.connect(self.toggle_fishing)
        self.tab_dashboard.sig_reset_cooldown.connect(self.reset_join_cooldown)
        self.tab_dashboard.sig_test_join.connect(self.benchmark_join)
        self.tab_stack.addWidget(self.tab_dashboard)

        # 1. Sniper Tab (Comprehensive Controls matching Sol Sniper V3)
        self.tab_sniper = SniperTab(self.storage, self)
        self.tab_sniper.sig_start_sniper.connect(self.toggle_sniper)
        self.tab_sniper.sig_toggle_sniper.connect(self.toggle_sniper)
        self.tab_sniper.sig_stop_sniper.connect(self.stop_sniper)
        self.tab_sniper.sig_pause_sniper.connect(self.pause_sniper)
        self.tab_sniper.sig_resume_sniper.connect(self.resume_sniper)
        self.tab_sniper.sig_reset_cooldown.connect(self.reset_join_cooldown)
        self.tab_sniper.sig_prewarm.connect(self.prewarm_roblox)
        self.tab_sniper.sig_test_join.connect(self.benchmark_join)
        self.tab_sniper.sig_setting_changed.connect(self._on_config_changed)
        self.tab_sniper.sig_token_saved.connect(self._on_token_saved)
        self.tab_sniper.sig_channels_saved.connect(self._on_channels_saved)
        self.tab_stack.addWidget(self.tab_sniper)

        # 2. Fishing Tab (Integrated from FishSol v2.1)
        self.tab_fishing = FishingTab(self)
        self.tab_fishing.sig_start_fishing.connect(self.fishsol.start)
        self.tab_fishing.sig_pause_fishing.connect(self.fishsol.pause)
        self.tab_fishing.sig_resume_fishing.connect(self.fishsol.resume)
        self.tab_fishing.sig_stop_fishing.connect(self.fishsol.stop)
        self.tab_fishing.sig_run_join_sequence.connect(lambda: self.fishsol.trigger_join_sequence_async(self.current_biome))
        self.tab_fishing.sig_launch_external_ahk.connect(self._launch_external_ahk)
        self.tab_fishing.sig_setting_changed.connect(self._on_fishing_config_changed)
        self.tab_stack.addWidget(self.tab_fishing)

        # 3. Servers Tab
        self.tab_servers = ServersTab(self.storage, self)
        self.tab_servers.sig_channels_updated.connect(self.monitor.set_monitored_channels)
        self.tab_servers.sig_channels_updated.connect(lambda ids: self.tab_sniper.load_channels())
        self.tab_stack.addWidget(self.tab_servers)

        # 4. Keywords Tab
        self.tab_keywords = KeywordsTab(self.storage, self)
        self.tab_keywords.sig_profiles_updated.connect(self.matcher.set_profiles)
        self.tab_stack.addWidget(self.tab_keywords)

        # 5. Misc Tab
        self.tab_misc = MiscTab(self.storage, self)
        self.tab_misc.sig_blacklists_updated.connect(self.matcher.set_blacklists)
        self.tab_misc.sig_hotkeys_updated.connect(self._on_hotkeys_updated)
        self.tab_misc.sig_setting_changed.connect(self._on_config_changed)
        self.tab_misc.sig_test_webhook.connect(self._on_test_webhook)
        self.sig_webhook_test_result.connect(self.tab_misc.set_webhook_test_result)
        self.tab_stack.addWidget(self.tab_misc)

        # 6. Settings Tab
        self.tab_settings = SettingsTab(self.storage, self)
        self.tab_settings.sig_token_saved.connect(self._on_token_saved)
        self.tab_settings.sig_test_connection.connect(self._on_test_token)
        self.tab_settings.sig_clear_history.connect(self.tab_dashboard._clear_table)
        self.tab_stack.addWidget(self.tab_settings)

        root_layout.addWidget(self.tab_stack)

    def _switch_tab(self, idx: int):
        """Smooth animated fade transition between tabs."""
        if self.tab_stack.currentIndex() == idx:
            return
        self.tab_stack.setCurrentIndex(idx)
        fade_anim = QtCore.QPropertyAnimation(self.tab_opacity, b"opacity")
        fade_anim.setDuration(150)
        fade_anim.setStartValue(0.2)
        fade_anim.setEndValue(1.0)
        fade_anim.setEasingCurve(QtCore.QEasingCurve.OutCubic)
        fade_anim.start(QtCore.QAbstractAnimation.DeleteWhenStopped)
        self._current_tab_anim = fade_anim

    def _pulse_status_animation(self):
        """Pulsing glow animation for active status indicators."""
        self._pulse_state = not self._pulse_state

        # Update 10-minute cooldown timer across tabs
        rem = self.launcher.get_cooldown_remaining()
        self.tab_dashboard.update_cooldown_display(rem)
        self.tab_sniper.update_cooldown_display(rem)

        if self.monitor.is_running:
            if self.is_biome_locked:
                color = "#00ff88" if self._pulse_state else "#10b981"
                self.lbl_sidebar_status.setText(f"● Locked in {self.fishsol.camping_target_biome}")
            elif self.monitor.is_paused:
                color = "#fbbf24" if self._pulse_state else "#d97706"
                self.lbl_sidebar_status.setText("● Engine: Paused")
            else:
                color = "#00f0ff" if self._pulse_state else "#38bdf8"
                self.lbl_sidebar_status.setText("● Engine: Monitoring")
            self.lbl_sidebar_status.setStyleSheet(f"color: {color}; font-size: 11px; font-weight: 700; padding: 6px;")
        else:
            self.lbl_sidebar_status.setText("● Engine: Stopped")
            self.lbl_sidebar_status.setStyleSheet("color: #64748b; font-size: 11px; font-weight: 700; padding: 6px;")

    # --- Core Controls ---
    def start_sniper(self):
        token = self.storage.get_bot_token()
        if not token and hasattr(self, "tab_sniper"):
            token = self.tab_sniper.edit_token.text().strip()
            if token:
                self.storage.save_bot_token(token)

        if not token:
            QtWidgets.QMessageBox.warning(
                self,
                "Discord Account Token Required",
                "PupuSnipe CANNOT detect or join servers without your Discord Account Token!\n\n"
                "Please paste your User Token at the top of the 'Sniper' tab and click 'Save Token'."
            )
            self._switch_tab(1)
            self.nav_buttons[1].setChecked(True)
            return

        # Ensure channel IDs from UI are synced before launch
        cids = self.tab_sniper.get_channel_ids()
        self.storage.set_channel_ids(cids)
        self.monitor.set_monitored_channels(cids)

        # Update UI state immediately so user sees responsive feedback
        self.tab_dashboard.update_sniper_status(True, False)
        self.tab_sniper.update_sniper_status(True, False)
        self.tab_dashboard.update_discord_status("CONNECTING", "Connecting to Discord...")
        ch_desc = f"{len(cids)} specific channel(s)" if cids else "ALL channels"
        self.lbl_sidebar_status.setText("● Engine: Monitoring")
        self.lbl_sidebar_status.setStyleSheet("color: #00f0ff; font-size: 11px; font-weight: 700; padding: 6px;")
        logger.info(f"Sniper engine started. Monitored channels ({len(cids)}): {ch_desc}")

        if self.config.prewarm_roblox:
            self.prewarm_roblox()

        self.monitor.start(token)

    def reset_join_cooldown(self):
        self.launcher.reset_global_cooldown()
        self.is_biome_locked = False
        self.active_biome_confirmed = False
        self.active_camping_biome = ""
        self.tab_fishing.set_camping_lock_state(False, self.fishsol.camping_target_biome)
        if self.monitor.is_running:
            self.monitor.unlock_from_camping()
            self.lbl_sidebar_status.setText("● Engine: Monitoring")
            self.lbl_sidebar_status.setStyleSheet("color: #00f0ff; font-size: 11px; font-weight: 700; padding: 6px;")
        self.tab_dashboard.update_cooldown_display(0.0)
        self.tab_sniper.update_cooldown_display(0.0)
        logger.info("[SNIPER] 10-minute server join cooldown manually reset! Ready to join new servers.")

    def stop_sniper(self):
        self.is_biome_locked = False
        self.active_biome_confirmed = False
        self.active_camping_biome = ""
        self.tab_fishing.set_camping_lock_state(False, self.fishsol.camping_target_biome)
        self.monitor.stop()
        self.tab_dashboard.update_sniper_status(False, False)
        self.tab_sniper.update_sniper_status(False, False)
        self.lbl_sidebar_status.setText("● Engine: Stopped")
        self.lbl_sidebar_status.setStyleSheet("color: #64748b; font-size: 11px; font-weight: 700; padding: 6px;")
        logger.info("Sniper engine stopped.")

    def pause_sniper(self):
        self.monitor.pause()
        self.tab_dashboard.update_sniper_status(True, True)
        self.tab_sniper.update_sniper_status(True, True)
        self.lbl_sidebar_status.setText("● Engine: Paused")
        self.lbl_sidebar_status.setStyleSheet("color: #fbbf24; font-size: 11px; font-weight: 700; padding: 6px;")
        logger.info("Sniper engine paused.")

    def resume_sniper(self):
        self.monitor.resume()
        self.tab_dashboard.update_sniper_status(True, False)
        self.tab_sniper.update_sniper_status(True, False)
        self.lbl_sidebar_status.setText("● Engine: Monitoring")
        self.lbl_sidebar_status.setStyleSheet("color: #00f0ff; font-size: 11px; font-weight: 700; padding: 6px;")
        logger.info("Sniper engine resumed.")

    def toggle_sniper(self):
        if self.monitor.is_running:
            if self.monitor.is_paused:
                self.resume_sniper()
            else:
                self.stop_sniper()
        else:
            self.start_sniper()

    def toggle_fishing(self):
        if getattr(self, "fishing_enabled", False):
            self.stop_fishing()
        else:
            self.start_fishing()

    def start_fishing(self):
        self.fishing_enabled = True
        self.fishsol.start()
        self.tab_dashboard.update_fishsol_status("Running", True)
        self.tab_fishing.set_macro_status("FishSol Macro Running")
        logger.info("[FishSol] Auto-Fishing Macro started.")

    def stop_fishing(self):
        self.fishing_enabled = False
        self.fishsol.stop()
        self.tab_dashboard.update_fishsol_status("Idle", False)
        self.tab_fishing.set_macro_status("FishSol Macro Stopped")
        logger.info("[FishSol] Auto-Fishing Macro stopped.")

    def emergency_stop(self):
        self.stop_sniper()
        self.fishsol.stop()
        logger.warning("EMERGENCY STOP TRIGGERED.")

    def prewarm_roblox(self):
        logger.info("Pre-warming Roblox client...")
        res = self.launcher.prewarm_client()
        if res:
            logger.info("Roblox client pre-warmed successfully.")
        else:
            logger.warning("Could not pre-warm Roblox client.")

    def benchmark_join(self, url: str):
        extracted = self.detector.extract_from_text(url)
        if not extracted or not extracted.is_valid:
            msg = f"Invalid or unrecognized Roblox link: {extracted.error_reason if extracted else 'Failed regex'}"
            self.tab_sniper.set_benchmark_result(msg, False)
            logger.error(msg)
            return

        # Clear any prior cooldown for this linkCode so user can test repeatedly with different methods!
        with self.launcher._lock:
            if extracted.link_code in self.launcher._joined_links:
                del self.launcher._joined_links[extracted.link_code]

        t0 = time.time()
        result = self.launcher.launch(
            protocol_url=extracted.protocol_url,
            link_code=extracted.link_code,
            method=self.config.launch_method,
            client=getattr(self.config, "roblox_client", "voidstrap"),
            recv_time=t0,
            extract_time=t0,
            match_time=t0,
            ignore_cooldown=True
        )

        if result.success:
            msg = f"✓ Successfully launched! Measured latency: {result.latency_ms:.2f} ms ({result.launch_method})"
            self.tab_sniper.set_benchmark_result(msg, True)
            logger.info(msg)
            self.total_joined += 1
            self.tab_dashboard.card_joined.set_value(str(self.total_joined))

            if result.latency_ms < self.fastest_latency:
                self.fastest_latency = result.latency_ms
                self.tab_dashboard.card_fastest.set_value(f"{self.fastest_latency:.2f} ms")

            self.tab_dashboard.add_activity_row({
                "timestamp": time.time(),
                "server_name": "MANUAL",
                "channel_name": "Benchmark",
                "author_name": "User",
                "profile_name": "Test Join",
                "keyword": "Manual",
                "link_code": extracted.link_code,
                "protocol_url": extracted.protocol_url,
                "latency_ms": result.latency_ms,
                "breakdown": result.breakdown,
                "status": "JOINED"
            })
        else:
            msg = f"Join error: {result.error_message}"
            self.tab_sniper.set_benchmark_result(msg, False)
            logger.error(msg)

    def _launch_external_ahk(self):
        success = FishSolEngine.launch_external_fishsol_ahk(r"D:\FishSol-v2.1")
        if success:
            logger.info("Launched external FishSol-v2.1.ahk successfully.")
        else:
            QtWidgets.QMessageBox.warning(self, "AHK Error", "Could not locate D:\\FishSol-v2.1\\FishSol-v2.1.ahk or AutoHotkey is not installed.")

    # --- Slots & Events ---
    @QtCore.Slot(str, str)
    def _on_discord_status_changed(self, state: str, text: str):
        self.tab_dashboard.update_discord_status(state, text)
        logger.info(f"[Discord] {text}")

    @QtCore.Slot(dict)
    def _on_snipe_event_received(self, event: dict):
        self.total_detected += 1
        self.tab_dashboard.card_detected.set_value(str(self.total_detected))

        if event.get("status") == "JOINED":
            self.total_joined += 1
            self.tab_dashboard.card_joined.set_value(str(self.total_joined))

            lat = event.get("latency_ms", 0.0)
            if lat > 0:
                self.latencies.append(lat)
                avg = sum(self.latencies) / len(self.latencies)
                self.tab_dashboard.card_latency.set_value(f"{avg:.2f} ms")
                if lat < self.fastest_latency:
                    self.fastest_latency = lat
                    self.tab_dashboard.card_fastest.set_value(f"{self.fastest_latency:.2f} ms")

            # Audio alert (bundled/custom sound; asynchronous, never blocks the UI)
            if self.config.play_sound:
                self.sound_manager.play()

            # Desktop Notification
            if self.config.enable_notifications:
                tray = QtWidgets.QSystemTrayIcon(self)
                tray.setIcon(self.windowIcon())
                tray.show()
                tray.showMessage(
                    f"PupuSnipe Joined Server!",
                    f"Target: {event.get('profile_name')} in {lat:.2f}ms",
                    QtWidgets.QSystemTrayIcon.Information,
                    3000
                )

            # Discord webhook alert (daemon thread; UI never waits on Discord's API)
            if getattr(self.config, "webhook_enabled", False) and getattr(self.config, "webhook_url", ""):
                self.webhook_notifier.send_snipe_async(
                    event=event,
                    url=self.config.webhook_url,
                    ping_everyone=bool(getattr(self.config, "webhook_ping_everyone", True)),
                )

            # Biome Camping & Auto-Fishing Coordination (from FishSol v2.1)
            prof_name = str(event.get("profile_name", "")).strip()

            self.is_biome_locked = True
            self.server_join_time = time.time()
            self.active_biome_confirmed = False

            # Determine what biome we are looking to camp
            target_cfg = self.fishsol.camping_target_biome.strip().upper()
            if "ANY" in target_cfg or not target_cfg:
                self.active_camping_biome = prof_name.upper() if prof_name.upper() not in ["DEDICATED CHANNEL", "MATCH", "UNKNOWN", "DIRECT_LINK"] else ""
            else:
                self.active_camping_biome = target_cfg

            camp_name = self.active_camping_biome or prof_name
            self.tab_fishing.set_camping_lock_state(True, camp_name)
            self.lbl_sidebar_status.setText(f"● In Server: {camp_name} (Locked)")
            self.lbl_sidebar_status.setStyleSheet("color: #00ff88; font-size: 11px; font-weight: 700; padding: 6px;")
            logger.info(f"[Camping] Joined server for {prof_name}. Server locked! Sniper paused to inspect biome and fish.")

            # Auto-Hook Fishing (Only when explicitly enabled by user)
            if getattr(self, "fishing_enabled", False) and self.fishsol.auto_fish_on_join:
                if not self.fishsol.is_running:
                    self.fishsol.start()
                self.fishsol.trigger_join_sequence_async(prof_name)

        self.tab_dashboard.add_activity_row(event)

    @QtCore.Slot()
    def _on_message_scanned_event(self):
        self.total_scanned += 1
        self.tab_dashboard.card_scanned.set_value(str(self.total_scanned))

    @QtCore.Slot(str)
    def _on_log_line_received(self, line: str):
        self.tab_settings.append_log_line(line)

    @QtCore.Slot(str)
    def _on_fishing_status(self, text: str):
        self.tab_dashboard.update_fishsol_status(text, self.fishsol.is_running)
        self.tab_fishing.set_macro_status(text)

    @QtCore.Slot(dict)
    def _on_fishing_stats(self, stats: dict):
        self.tab_dashboard.card_fish.set_value(str(stats.get("fish_caught", 0)))
        self.tab_fishing.update_stats(stats)
        self.tab_dashboard.update_fishsol_status("Running" if stats.get("is_running") else "Idle", stats.get("is_running", False))

    @QtCore.Slot(str)
    def _on_biome_changed(self, biome: str):
        self.current_biome = biome
        self.tab_dashboard.update_biome_display(self.current_biome, self.current_aura)

        # Enrich the most recent webhook message with the confirmed in-game biome.
        if getattr(self.config, "webhook_enabled", False):
            self.webhook_notifier.update_biome_async(biome)

        current = biome.replace(" ", "").upper()
        target = (getattr(self, "active_camping_biome", "") or self.fishsol.camping_target_biome).replace(" ", "").upper()

        if self.is_biome_locked:
            # 1. Check if the biome ended (server changed back to NORMAL, DEFAULT, etc.)
            if getattr(self, "active_biome_confirmed", False):
                if current in ["NORMAL", "DEFAULT"] or (target and current != target and current not in ["UNKNOWN", "NONE", ""]):
                    logger.info(
                        f"[Camping] Biome '{getattr(self, 'active_camping_biome', '')}' has EXPIRED/ENDED (server is now {biome})! "
                        f"Target biome completed. Unlocking sniper to hop to next server link..."
                    )
                    self.is_biome_locked = False
                    self.active_biome_confirmed = False
                    self.active_camping_biome = ""
                    self.tab_fishing.set_camping_lock_state(False, self.fishsol.camping_target_biome)
                    self.monitor.unlock_from_camping()
                    self.lbl_sidebar_status.setText("● Engine: Monitoring")
                    self.lbl_sidebar_status.setStyleSheet("color: #00f0ff; font-size: 11px; font-weight: 700; padding: 6px;")
                    return

            # 2. Check if we just confirmed our target or special biome
            is_special = current not in ["NORMAL", "DEFAULT", "UNKNOWN", "NONE", ""]
            matches_target = (not target or "ANY" in target or current == target)

            if is_special and matches_target:
                self.active_biome_confirmed = True
                self.active_camping_biome = biome
                self.tab_fishing.set_camping_lock_state(True, biome)
                self.lbl_sidebar_status.setText(f"● Camping: {biome} (Locked)")
                self.lbl_sidebar_status.setStyleSheet("color: #00ff88; font-size: 11px; font-weight: 700; padding: 6px;")
                logger.info(f"[Camping] Confirmed {biome} biome active in server! Staying & fishing until it ends.")
            elif not is_special:
                # If 45s passed since join and server is still NORMAL: dead link/already expired
                elapsed = time.time() - getattr(self, "server_join_time", 0)
                if elapsed > 45:
                    logger.info(f"[Camping] Server has no special biome (currently {biome} after {int(elapsed)}s). Link was expired/empty. Hopping to next server...")
                    self.is_biome_locked = False
                    self.active_biome_confirmed = False
                    self.tab_fishing.set_camping_lock_state(False, self.fishsol.camping_target_biome)
                    self.monitor.unlock_from_camping()
                    self.lbl_sidebar_status.setText("● Engine: Monitoring")
                    self.lbl_sidebar_status.setStyleSheet("color: #00f0ff; font-size: 11px; font-weight: 700; padding: 6px;")

    @QtCore.Slot(str)
    def _on_aura_changed(self, aura: str):
        self.current_aura = aura
        self.tab_dashboard.update_biome_display(self.current_biome, self.current_aura)

    def _check_roblox_process(self):
        is_running = self.launcher.is_roblox_running()
        self.tab_dashboard.update_roblox_status(is_running)

    def _sync_profiles(self):
        profiles = self.storage.get_profiles()
        self.matcher.set_profiles(profiles)

    def _sync_channels(self):
        channels = self.storage.get_channels()
        enabled_ids = [ch["channel_id"] for ch in channels if ch["enabled"]]
        self.monitor.set_monitored_channels(enabled_ids)

    def _sync_blacklists(self):
        users = self.storage.get_blacklist("user")
        kws = self.storage.get_blacklist("keyword")
        self.matcher.set_blacklists(users, kws)

    def _on_channels_saved(self, channel_ids: list):
        self.monitor.set_monitored_channels(channel_ids)
        self.tab_servers.load_channels()
        logger.info(f"Updated monitored channels: {len(channel_ids)} specific channel(s).")

    def _on_channel_resolved(self, cid: str, s_id: str, s_name: str, c_name: str):
        if hasattr(self, "tab_servers"):
            self.tab_servers.update_channel_info(cid, s_id, s_name, c_name)

    def _load_persisted_settings(self):
        """Loads all persisted settings from SQLite storage into memory configuration."""
        try:
            saved = self.storage.get_all_settings()
            for k, v in saved.items():
                if hasattr(self.config, k):
                    orig = getattr(self.config, k)
                    if isinstance(orig, bool) and not isinstance(v, bool):
                        v = bool(v)
                    elif isinstance(orig, int) and not isinstance(v, int):
                        try: v = int(v)
                        except: pass
                    elif isinstance(orig, float) and not isinstance(v, float):
                        try: v = float(v)
                        except: pass
                    setattr(self.config, k, v)
        except Exception as ex:
            logger.warning(f"Could not load persisted configuration: {ex}")

    def _load_persisted_fishing_settings(self):
        """Loads all persisted fishing macro settings from SQLite storage."""
        try:
            saved = self.storage.get_all_settings()
            if "fishsol_auto_on_join" in saved:
                self.fishsol.auto_fish_on_join = bool(saved["fishsol_auto_on_join"])
            if "fishsol_stay_in_biome" in saved:
                self.fishsol.stay_in_target_biome = bool(saved["fishsol_stay_in_biome"])
            if "fishsol_camping_biome" in saved:
                self.fishsol.camping_target_biome = str(saved["fishsol_camping_biome"]).upper()
            if "fishsol_pathing_mode" in saved:
                self.fishsol.pathing_mode = str(saved["fishsol_pathing_mode"])
            if "fishsol_resolution" in saved:
                self.fishsol.resolution = str(saved["fishsol_resolution"]).split()[0]
            if "fishsol_sell_all" in saved:
                self.fishsol.sell_all = bool(saved["fishsol_sell_all"])
            if "fishsol_loop_count" in saved:
                self.fishsol.fishing_loop_count = int(saved["fishsol_loop_count"])
            if "hotkeys" in saved and isinstance(saved["hotkeys"], dict):
                for action, key_name in saved["hotkeys"].items():
                    self.hotkeys.update_binding(action, key_name)
        except Exception as ex:
            logger.warning(f"Could not load persisted fishing settings: {ex}")

    def _save_window_geometry(self):
        """Saves window size, position, and maximized state to SQLite storage."""
        try:
            geom_hex = self.saveGeometry().toHex().data().decode("utf-8")
            self.storage.set_setting("window_geometry", geom_hex)
            self.storage.set_setting("window_maximized", self.isMaximized())
            if not self.isMaximized():
                self.storage.set_setting("window_width", self.width())
                self.storage.set_setting("window_height", self.height())
        except Exception:
            pass

    def _restore_window_geometry(self):
        """Restores window size, position, and maximized state from SQLite storage."""
        try:
            geom_hex = self.storage.get_setting("window_geometry", "")
            if geom_hex:
                self.restoreGeometry(QtCore.QByteArray.fromHex(geom_hex.encode("utf-8")))
            else:
                w = self.storage.get_setting("window_width", 1220)
                h = self.storage.get_setting("window_height", 780)
                self.resize(int(w), int(h))

            if self.storage.get_setting("window_maximized", False):
                self.showMaximized()
        except Exception:
            pass

    def _apply_ui_scale(self, factor: float):
        """Applies dynamic font scaling across the entire application interface."""
        try:
            factor = max(0.75, min(2.0, float(factor)))
            app = QtWidgets.QApplication.instance()
            if app:
                font = app.font()
                base_pt = 9.0
                font.setPointSizeF(base_pt * factor)
                app.setFont(font)
        except Exception as ex:
            logger.warning(f"Could not apply UI scale: {ex}")

    def _on_ui_scale_changed(self, factor: float):
        self._apply_ui_scale(factor)
        self.storage.set_setting("ui_scale", factor)
        self._save_window_geometry()
        logger.info(f"UI display zoom updated and saved: {factor * 100:.0f}%")

    def _on_config_changed(self, key: str, value):
        if key.startswith("cat_"):
            self._sync_profiles()
            self.tab_keywords.load_profiles()
            logger.info(f"Category profile updated: {key} = {value}")
            return

        # Always persist setting to storage immediately
        self.storage.set_setting(key, value)

        if hasattr(self.config, key):
            setattr(self.config, key, value)
            if key == "place_id":
                self.detector.target_place_id = str(value)
            elif key == "duplicate_cooldown_sec":
                self.launcher.cooldown_seconds = int(value)
            elif key == "only_join_sols_links":
                self.detector.strict_place_id = bool(value)
            elif key == "snipe_ropro_links":
                self.detector.snipe_ropro = bool(value)
            elif key == "snipe_joinrbx_links":
                self.detector.snipe_joinrbx = bool(value)
            elif key == "snipe_roseal_links":
                self.detector.snipe_roseal = bool(value)
            elif key == "snipe_fishstrap_links":
                self.detector.snipe_fishstrap = bool(value)
            elif key == "snipe_joingate_links":
                self.detector.snipe_joingate = bool(value)
            elif key == "gateway_browser":
                self.launcher.gateway_browser = str(value or "default")
            elif key == "gateway_browser_path":
                self.launcher.gateway_browser_path = str(value or "")
            elif key == "sound_preset":
                self.sound_manager.set_selection(preset_id=str(value))
            elif key == "custom_sound_path":
                self.sound_manager.set_selection(custom_path=str(value))
            elif key == "webhook_url":
                clean_url = str(value or "").strip()
                self.config.webhook_url = clean_url
                self.storage.set_setting("webhook_url", clean_url)
            logger.info(f"Setting updated and saved to storage: {key} = {value}")

    def _on_fishing_config_changed(self, key: str, value):
        # Always persist fishing setting to storage immediately
        self.storage.set_setting(key, value)

        if key == "fishsol_auto_on_join":
            self.fishsol.auto_fish_on_join = bool(value)
        elif key == "fishsol_stay_in_biome":
            self.fishsol.stay_in_target_biome = bool(value)
        elif key == "fishsol_camping_biome":
            self.fishsol.camping_target_biome = str(value).upper()
            self.tab_fishing.set_camping_lock_state(self.is_biome_locked, self.fishsol.camping_target_biome)
        elif key == "fishsol_pathing_mode":
            self.fishsol.pathing_mode = str(value)
        elif key == "fishsol_resolution":
            self.fishsol.resolution = str(value).split()[0]
        elif key == "fishsol_sell_all":
            self.fishsol.sell_all = bool(value)
        elif key == "fishsol_loop_count":
            self.fishsol.fishing_loop_count = int(value)
        logger.info(f"Fishing setting updated and saved to storage: {key} = {value}")

    def _on_hotkeys_updated(self, hk_map: dict):
        self.storage.set_setting("hotkeys", hk_map)
        for action, key_name in hk_map.items():
            self.hotkeys.update_binding(action, key_name)
        logger.info(f"Hotkeys updated and saved to storage: {hk_map}")

    def _on_token_saved(self, token: str):
        # Sync between tabs
        self.tab_sniper.load_token()
        self.tab_settings.load_settings()
        logger.info("Discord Bot Token updated in Windows Credential Manager.")

    def _on_test_token(self, token: str):
        logger.info("Testing Discord Bot Token connection...")
        QtWidgets.QMessageBox.information(
            self,
            "Discord Bot Check",
            "Token saved! You can now click 'START SNIPING (F4)' on the Dashboard or Sniper tab to connect."
        )

    def _on_test_webhook(self, url: str, ping_everyone: bool):
        self.webhook_notifier.test_webhook_async(
            url,
            ping_everyone=ping_everyone,
            on_result=lambda ok, message: self.sig_webhook_test_result.emit(bool(ok), str(message)),
        )

    def resizeEvent(self, event: QtGui.QResizeEvent):
        super().resizeEvent(event)
        if not self.isMaximized():
            try:
                self.storage.set_setting("window_width", self.width())
                self.storage.set_setting("window_height", self.height())
            except Exception:
                pass

    def closeEvent(self, event: QtGui.QCloseEvent):
        self._save_window_geometry()
        self.stop_sniper()
        self.fishsol.stop()
        self.log_watcher.stop()
        self.sound_manager.stop()
        self.hotkeys.stop()
        super().closeEvent(event)
