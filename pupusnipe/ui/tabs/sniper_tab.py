"""
PupuSnipe Sniper Configuration & Controls Tab
Comprehensive sniper controls matching and exceeding Sol Sniper V3:
Direct Bot Token & Multi-Channel ID setup, Base Categories with Pause Durations,
Advanced Settings (leave game, close roblox, minimize windows), Custom Links, and Benchmark Tester.
"""
import re
import webbrowser
from typing import List, Dict, Any
from PySide6 import QtCore, QtGui, QtWidgets
from ...core.config import DEFAULT_SOLS_RNG_PLACE_ID, DEFAULT_SNIPER_CHANNEL_PRESETS
from ...core.storage import StorageManager
from ..widgets import GlowCard, CategoryRow


class SniperTab(QtWidgets.QWidget):
    sig_start_sniper = QtCore.Signal()
    sig_toggle_sniper = QtCore.Signal()
    sig_stop_sniper = QtCore.Signal()
    sig_pause_sniper = QtCore.Signal()
    sig_resume_sniper = QtCore.Signal()
    sig_reset_cooldown = QtCore.Signal()
    sig_prewarm = QtCore.Signal()
    sig_test_join = QtCore.Signal(str)
    sig_setting_changed = QtCore.Signal(str, object)
    sig_token_saved = QtCore.Signal(str)
    sig_channels_saved = QtCore.Signal(list)

    def __init__(self, storage: StorageManager, parent=None):
        super().__init__(parent)
        self.storage = storage
        self.category_rows: Dict[str, CategoryRow] = {}
        self._init_ui()
        self.load_token()
        self.load_channels()
        self.load_categories()

    def _init_ui(self):
        # Outer scroll area prevents scaling/DPI clipping on all monitor resolutions
        outer_layout = QtWidgets.QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        content = QtWidgets.QWidget()
        main_layout = QtWidgets.QVBoxLayout(content)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(16)

        # -------------------------------------------------------------
        # 1. CREDENTIALS & MONITORED CHANNEL IDS (Sol Sniper V3 Layout)
        # -------------------------------------------------------------
        cred_card = GlowCard(
            title="Discord Credentials & Monitored Channel IDs",
            subtitle="Configure your Discord User Account token (Selfbot) and target Discord channel ID(s) to scan for private server links.",
            accent_color="#00f0ff"
        )

        # Token Row
        token_header = QtWidgets.QLabel("Discord Account Token (User Token - Selfbot):")
        token_header.setStyleSheet("font-size: 12px; font-weight: 700; color: #cbd5e1;")
        cred_card.add_widget(token_header)

        token_row = QtWidgets.QHBoxLayout()
        token_row.setSpacing(8)

        self.edit_token = QtWidgets.QLineEdit()
        self.edit_token.setEchoMode(QtWidgets.QLineEdit.Password)
        self.edit_token.setPlaceholderText("Paste your Discord User Account Token here...")
        self.edit_token.setMinimumHeight(38)

        self.btn_toggle_token = QtWidgets.QPushButton("Show")
        self.btn_toggle_token.setProperty("class", "btn-secondary")
        self.btn_toggle_token.setMinimumHeight(38)
        self.btn_toggle_token.clicked.connect(self._toggle_token_visibility)

        self.btn_save_token = QtWidgets.QPushButton("💾 Save Token")
        self.btn_save_token.setProperty("class", "btn-primary")
        self.btn_save_token.setMinimumHeight(38)
        self.btn_save_token.clicked.connect(self._save_token)

        self.btn_open_portal = QtWidgets.QPushButton("❓ How to Get Token")
        self.btn_open_portal.setProperty("class", "btn-secondary")
        self.btn_open_portal.setMinimumHeight(38)
        self.btn_open_portal.setToolTip("Instructions on finding your Discord user token in browser or desktop app")
        self.btn_open_portal.clicked.connect(self._show_token_help)

        token_row.addWidget(self.edit_token)
        token_row.addWidget(self.btn_toggle_token)
        token_row.addWidget(self.btn_save_token)
        token_row.addWidget(self.btn_open_portal)
        cred_card.add_layout(token_row)

        self.lbl_token_status = QtWidgets.QLabel("⚠️ No account token configured yet.")
        self.lbl_token_status.setStyleSheet("color: #fbbf24; font-weight: 700; font-size: 11px;")
        cred_card.add_widget(self.lbl_token_status)

        # Channel IDs Row (Sol Sniper V3 Multi-Channel Configuration)
        ch_header = QtWidgets.QHBoxLayout()
        lbl_ch_title = QtWidgets.QLabel("Monitored Discord Channel ID(s):")
        lbl_ch_title.setStyleSheet("font-size: 12px; font-weight: 700; color: #cbd5e1;")
        ch_header.addWidget(lbl_ch_title)
        ch_header.addStretch()

        self.lbl_channel_count = QtWidgets.QLabel("Channels: Monitoring All (0 specific)")
        self.lbl_channel_count.setStyleSheet("color: #00f0ff; font-weight: 700; font-size: 11px;")
        ch_header.addWidget(self.lbl_channel_count)
        cred_card.add_layout(ch_header)

        self.edit_channels = QtWidgets.QPlainTextEdit()
        self.edit_channels.setPlaceholderText(
            "Enter Channel IDs separated by comma, space, or newline (e.g. 1271189513619902515, 1337886908251902114)...\n"
            "If left empty, PupuSnipe monitors all incoming messages across all server channels your bot can see."
        )
        self.edit_channels.setMinimumHeight(64)
        self.edit_channels.setMaximumHeight(85)
        self.edit_channels.textChanged.connect(self._on_channels_text_changed)
        cred_card.add_widget(self.edit_channels)

        ch_btn_row = QtWidgets.QHBoxLayout()
        ch_btn_row.setSpacing(8)

        self.btn_save_channels = QtWidgets.QPushButton("💾 Save & Apply Channels")
        self.btn_save_channels.setProperty("class", "btn-primary")
        self.btn_save_channels.setMinimumHeight(34)
        self.btn_save_channels.clicked.connect(self._save_channels)

        self.btn_load_preset = QtWidgets.QPushButton("⚡ Load Biome Hunt Preset")
        self.btn_load_preset.setProperty("class", "btn-secondary")
        self.btn_load_preset.setMinimumHeight(34)
        self.btn_load_preset.setToolTip("Loads default high-volume Sol's RNG private server hunt channels")
        self.btn_load_preset.clicked.connect(self._load_channel_preset)

        self.btn_clear_channels = QtWidgets.QPushButton("Clear Channels")
        self.btn_clear_channels.setProperty("class", "btn-secondary")
        self.btn_clear_channels.setMinimumHeight(34)
        self.btn_clear_channels.clicked.connect(self._clear_channels)

        ch_btn_row.addWidget(self.btn_save_channels)
        ch_btn_row.addWidget(self.btn_load_preset)
        ch_btn_row.addWidget(self.btn_clear_channels)
        ch_btn_row.addStretch()
        cred_card.add_layout(ch_btn_row)

        self.chk_direct_channel = QtWidgets.QCheckBox(
            "⚡ Dedicated Channel Mode: Join ALL valid links in monitored channels (no keywords required)"
        )
        self.chk_direct_channel.setChecked(True)
        self.chk_direct_channel.setStyleSheet("color: #00ff88; font-weight: 700; font-size: 11px; margin-top: 4px;")
        self.chk_direct_channel.setToolTip(
            "Recommended for dedicated channels (like Corruption-only channels or VIP pings). "
            "PupuSnipe immediately joins any valid private server link posted in your channel, even without text or keyword tags."
        )
        self.chk_direct_channel.toggled.connect(lambda v: self.sig_setting_changed.emit("join_all_in_monitored_channels", v))
        cred_card.add_widget(self.chk_direct_channel)

        main_layout.addWidget(cred_card)

        # -------------------------------------------------------------
        # 2. SNIPER CONTROLS & LIVE ENGINE STATUS
        # -------------------------------------------------------------
        ctrl_card = GlowCard(
            title="Sniper Engine Status & Primary Controls",
            subtitle="Start or pause automated Discord private server detection and high-speed Roblox launching.",
            accent_color="#00ff88"
        )

        # Live engine status & cooldown indicators
        self.lbl_engine_banner = QtWidgets.QLabel("● SNIPER IS STOPPED — Click 'START SNIPING (F4)' to begin")
        self.lbl_engine_banner.setStyleSheet("color: #94a3b8; font-size: 13px; font-weight: 700; padding: 4px;")
        ctrl_card.add_widget(self.lbl_engine_banner)

        self.lbl_cooldown_banner = QtWidgets.QLabel("✓ Cooldown: Ready to Join Next Server")
        self.lbl_cooldown_banner.setStyleSheet("color: #00ff88; font-size: 12px; font-weight: 700; padding: 4px;")
        ctrl_card.add_widget(self.lbl_cooldown_banner)

        ctrl_row = QtWidgets.QHBoxLayout()
        ctrl_row.setSpacing(10)

        self.btn_start = QtWidgets.QPushButton("▶ START SNIPING (F4)")
        self.btn_start.setProperty("class", "btn-primary")
        self.btn_start.setMinimumHeight(48)
        self.btn_start.clicked.connect(self.sig_toggle_sniper.emit)

        self.btn_pause = QtWidgets.QPushButton("⏸ PAUSE SNIPER (F5)")
        self.btn_pause.setProperty("class", "btn-accent")
        self.btn_pause.setMinimumHeight(48)
        self.btn_pause.setEnabled(False)
        self.btn_pause.clicked.connect(self._toggle_pause)

        self.btn_stop = QtWidgets.QPushButton("⏹ STOP SNIPER (F7)")
        self.btn_stop.setProperty("class", "btn-danger")
        self.btn_stop.setMinimumHeight(48)
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self.sig_stop_sniper.emit)

        self.btn_reset_cooldown = QtWidgets.QPushButton("🔄 RESET 10M COOLDOWN (F9)")
        self.btn_reset_cooldown.setProperty("class", "btn-secondary")
        self.btn_reset_cooldown.setMinimumHeight(48)
        self.btn_reset_cooldown.clicked.connect(self.sig_reset_cooldown.emit)

        self.btn_launch_roblox = QtWidgets.QPushButton("🚀 LAUNCH ROBLOX")
        self.btn_launch_roblox.setProperty("class", "btn-secondary")
        self.btn_launch_roblox.setMinimumHeight(48)
        self.btn_launch_roblox.clicked.connect(self.sig_prewarm.emit)

        ctrl_row.addWidget(self.btn_start)
        ctrl_row.addWidget(self.btn_pause)
        ctrl_row.addWidget(self.btn_stop)
        ctrl_row.addWidget(self.btn_reset_cooldown)
        ctrl_row.addWidget(self.btn_launch_roblox)
        ctrl_card.add_layout(ctrl_row)

        main_layout.addWidget(ctrl_card)

        # -------------------------------------------------------------
        # 3. BASE CATEGORIES (Keyword Filters & Pause Durations)
        # -------------------------------------------------------------
        cat_card = GlowCard(
            title="Optional Keyword Filters & Pause Durations",
            subtitle="Optional: Only needed when monitoring mixed multi-topic channels. If using dedicated channels, all links are joined automatically. (Full fishing controls are in the Fishing tab).",
            accent_color="#a855f7"
        )

        cat_grid = QtWidgets.QGridLayout()
        cat_grid.setHorizontalSpacing(14)
        cat_grid.setVerticalSpacing(8)

        base_cats = [
            ("corruption", "Corruption Sniping", True, 300, "🔮"),
            ("glitched", "Glitch Sniping", True, 180, "🌀"),
            ("dreamspace", "Dreamspace Sniping", True, 180, "🌌"),
            ("cyberspace", "Cyberspace Sniping", True, 720, "🌐"),
            ("singularity", "Singularity Sniping", True, 1200, "💫"),
            ("jester", "Jester Merchant", True, 180, "🃏"),
            ("mari", "Mari Merchant", True, 60, "🌸"),
            ("rin", "Rin Merchant", True, 60, "🦊"),
            ("void_coin", "Void Coin Sniping", True, 120, "🪙"),
            ("oblivion_potion", "Oblivion Potion Sniping", True, 180, "🧪"),
        ]

        for i, (cid, label, chk_def, pause_def, icon) in enumerate(base_cats):
            row_w = CategoryRow(cid, label, chk_def, pause_def, icon)
            row_w.sig_changed.connect(self._on_category_changed)
            self.category_rows[cid] = row_w
            cat_grid.addWidget(row_w, i // 2, i % 2)

        cat_card.add_layout(cat_grid)
        main_layout.addWidget(cat_card)

        # -------------------------------------------------------------
        # 4. ADVANCED SETTINGS (Sol Sniper V3 Feature Match)
        # -------------------------------------------------------------
        adv_card = GlowCard(
            title="Advanced Joining & Performance Options",
            subtitle="Automated leave-game handling, process termination, window focus, and anti-duplicate TTL.",
            accent_color="#fbbf24"
        )
        adv_form = QtWidgets.QFormLayout()
        adv_form.setSpacing(12)

        self.chk_leave_game = QtWidgets.QCheckBox("Leave Game Before Joining a Snipe (Sends Esc -> L -> Enter sequence if in game)")
        self.chk_leave_game.setChecked(False)
        self.chk_leave_game.toggled.connect(lambda v: self.sig_setting_changed.emit("leave_game_before_joining", v))
        adv_form.addRow("Leave Game:", self.chk_leave_game)

        self.chk_close_roblox = QtWidgets.QCheckBox("Close Roblox Before Joining a Snipe (Terminates existing client)")
        self.chk_close_roblox.setChecked(False)
        self.chk_close_roblox.toggled.connect(lambda v: self.sig_setting_changed.emit("close_roblox_before_joining", v))
        adv_form.addRow("Close Roblox:", self.chk_close_roblox)

        self.chk_minimize_other = QtWidgets.QCheckBox("Minimize Other Windows on Snipe (Gives Roblox exclusive foreground focus)")
        self.chk_minimize_other.setChecked(False)
        self.chk_minimize_other.toggled.connect(lambda v: self.sig_setting_changed.emit("minimize_other_windows", v))
        adv_form.addRow("Window Focus:", self.chk_minimize_other)

        self.chk_auto_pause = QtWidgets.QCheckBox("Auto-Pause Sniper Upon Snipe (Pauses for category's configured duration)")
        self.chk_auto_pause.setChecked(False)
        self.chk_auto_pause.toggled.connect(lambda v: self.sig_setting_changed.emit("auto_pause_sniper", v))
        adv_form.addRow("Auto-Pause:", self.chk_auto_pause)

        self.chk_only_sols = QtWidgets.QCheckBox("Only Join Sol's RNG Servers When Sniping (Place ID: 15532314909)")
        self.chk_only_sols.setChecked(True)
        self.chk_only_sols.toggled.connect(lambda v: self.sig_setting_changed.emit("only_join_sols_links", v))
        adv_form.addRow("Filter Target:", self.chk_only_sols)

        self.combo_roblox_client = QtWidgets.QComboBox()
        self.combo_roblox_client.addItems([
            "Voidstrap (D:\\Void Strap 67\\Voidstrap.exe)",
            "Normal Roblox (RobloxPlayerBeta.exe)",
            "Windows Default (System Protocol Association)"
        ])
        self.combo_roblox_client.currentIndexChanged.connect(self._on_roblox_client_changed)
        adv_form.addRow("Roblox Client / App:", self.combo_roblox_client)

        self.combo_launch_method = QtWidgets.QComboBox()
        self.combo_launch_method.addItems([
            "Direct Windows Protocol (roblox://) [Instant & Recommended]",
            "Direct Bootstrapper Launch (Voidstrap / Bloxstrap)",
            "System Browser / Shell Start"
        ])
        self.combo_launch_method.currentIndexChanged.connect(self._on_launch_method_changed)
        adv_form.addRow("Launch Method:", self.combo_launch_method)

        self.spin_cooldown = QtWidgets.QSpinBox()
        self.spin_cooldown.setRange(10, 3600)
        self.spin_cooldown.setValue(180)
        self.spin_cooldown.setSuffix(" seconds")
        self.spin_cooldown.valueChanged.connect(lambda v: self.sig_setting_changed.emit("duplicate_cooldown_sec", v))
        adv_form.addRow("Duplicate Link Cooldown:", self.spin_cooldown)

        adv_card.add_layout(adv_form)
        main_layout.addWidget(adv_card)

        # -------------------------------------------------------------
        # 5. CUSTOM LINK SNIPING (Sol Sniper V3 Feature Match)
        # -------------------------------------------------------------
        links_card = GlowCard(
            title="Custom Link Sniping Support",
            subtitle="Automatically resolve and launch third-party private server links and share codes.",
            accent_color="#38bdf8"
        )
        links_layout = QtWidgets.QVBoxLayout()
        links_layout.setSpacing(8)

        self.chk_ropro = QtWidgets.QCheckBox("Snipe RoPro Links (ro.pro & ropro.io)")
        self.chk_ropro.setChecked(True)
        self.chk_ropro.toggled.connect(lambda v: self.sig_setting_changed.emit("snipe_ropro_links", v))
        links_layout.addWidget(self.chk_ropro)

        self.chk_joinrbx = QtWidgets.QCheckBox("Snipe JoinRBX Links (join-rbx.vexsys.site)")
        self.chk_joinrbx.setChecked(True)
        self.chk_joinrbx.toggled.connect(lambda v: self.sig_setting_changed.emit("snipe_joinrbx_links", v))
        links_layout.addWidget(self.chk_joinrbx)

        self.chk_roseal = QtWidgets.QCheckBox("Snipe RoSeal Links (roseal.live)")
        self.chk_roseal.setChecked(True)
        self.chk_roseal.toggled.connect(lambda v: self.sig_setting_changed.emit("snipe_roseal_links", v))
        links_layout.addWidget(self.chk_roseal)

        self.chk_fishstrap = QtWidgets.QCheckBox("Snipe FishStrap Links (fishstrap.app)")
        self.chk_fishstrap.setChecked(True)
        self.chk_fishstrap.toggled.connect(lambda v: self.sig_setting_changed.emit("snipe_fishstrap_links", v))
        links_layout.addWidget(self.chk_fishstrap)

        links_card.add_layout(links_layout)
        main_layout.addWidget(links_card)

        # -------------------------------------------------------------
        # 6. MANUAL JOIN & LATENCY BENCHMARK TESTER
        # -------------------------------------------------------------
        test_card = GlowCard(
            title="Manual Link Join & Speed Benchmark Tester",
            subtitle="Paste any Sol's RNG private server URL or raw linkCode below to test instant launching and measure exact latency. (Cooldown disabled for instant repeated testing).",
            accent_color="#00f0ff"
        )

        # Client & Method Selector Row
        sel_row = QtWidgets.QHBoxLayout()
        sel_row.setSpacing(12)

        lbl_c = QtWidgets.QLabel("Client:")
        lbl_c.setStyleSheet("font-size: 11px; font-weight: 700; color: #cbd5e1;")
        self.combo_test_client = QtWidgets.QComboBox()
        self.combo_test_client.addItems([
            "Voidstrap (D:\\Void Strap 67)",
            "Normal Roblox (Vanilla)",
            "Windows Default Protocol"
        ])
        self.combo_test_client.setMinimumHeight(32)
        self.combo_test_client.currentIndexChanged.connect(self._on_benchmark_client_changed)
        sel_row.addWidget(lbl_c)
        sel_row.addWidget(self.combo_test_client, 1)

        lbl_m = QtWidgets.QLabel("Method:")
        lbl_m.setStyleSheet("font-size: 11px; font-weight: 700; color: #cbd5e1;")
        self.combo_test_method = QtWidgets.QComboBox()
        self.combo_test_method.addItems([
            "Direct Windows Protocol (roblox://) [Recommended]",
            "Direct Bootstrapper Launch",
            "System Browser / Shell Start"
        ])
        self.combo_test_method.setMinimumHeight(32)
        self.combo_test_method.currentIndexChanged.connect(self._on_benchmark_method_changed)
        sel_row.addWidget(lbl_m)
        sel_row.addWidget(self.combo_test_method, 1)
        test_card.add_layout(sel_row)

        input_row = QtWidgets.QHBoxLayout()
        input_row.setSpacing(8)
        self.edit_test_url = QtWidgets.QLineEdit()
        self.edit_test_url.setPlaceholderText("Paste private server URL (roblox.com, ro.pro, share code, or linkCode)...")
        self.edit_test_url.setMinimumHeight(38)

        btn_test_join = QtWidgets.QPushButton("🚀 Launch / Test Join")
        btn_test_join.setProperty("class", "btn-primary")
        btn_test_join.setMinimumHeight(38)
        btn_test_join.clicked.connect(self._on_test_join_clicked)

        input_row.addWidget(self.edit_test_url)
        input_row.addWidget(btn_test_join)
        test_card.add_layout(input_row)

        self.lbl_benchmark_res = QtWidgets.QLabel("Ready for benchmark test (Cooldown disabled - test as many times as you like).")
        self.lbl_benchmark_res.setStyleSheet("color: #00f0ff; font-weight: 700; font-size: 11px;")
        test_card.add_widget(self.lbl_benchmark_res)

        main_layout.addWidget(test_card)

        scroll.setWidget(content)
        outer_layout.addWidget(scroll)

    def load_token(self):
        token = self.storage.get_bot_token()
        if token:
            self.edit_token.setText(token)
            self.lbl_token_status.setText("✓ Discord Bot Token is saved and ready in Windows Credential Manager.")
            self.lbl_token_status.setStyleSheet("color: #00ff88; font-weight: 700; font-size: 11px;")
        else:
            self.lbl_token_status.setText("⚠️ No bot token configured yet. Follow the steps above to add one.")
            self.lbl_token_status.setStyleSheet("color: #fbbf24; font-weight: 700; font-size: 11px;")

    def load_channels(self):
        cids = self.storage.get_channel_ids()
        self.edit_channels.blockSignals(True)
        if cids:
            self.edit_channels.setPlainText(", ".join(cids))
            self.lbl_channel_count.setText(f"Channels: Monitoring {len(cids)} Specific Channel(s)")
            self.lbl_channel_count.setStyleSheet("color: #00ff88; font-weight: 700; font-size: 11px;")
        else:
            self.edit_channels.clear()
            self.lbl_channel_count.setText("Channels: Monitoring All (0 specific)")
            self.lbl_channel_count.setStyleSheet("color: #00f0ff; font-weight: 700; font-size: 11px;")
        self.edit_channels.blockSignals(False)

    def load_categories(self):
        profiles = self.storage.get_profiles()
        for p in profiles:
            if p.id in self.category_rows:
                row = self.category_rows[p.id]
                row.set_checked(p.enabled)
                if p.pause_duration > 0:
                    row.set_pause(p.pause_duration)

    def _toggle_token_visibility(self):
        if self.edit_token.echoMode() == QtWidgets.QLineEdit.Password:
            self.edit_token.setEchoMode(QtWidgets.QLineEdit.Normal)
            self.btn_toggle_token.setText("Hide")
        else:
            self.edit_token.setEchoMode(QtWidgets.QLineEdit.Password)
            self.btn_toggle_token.setText("Show")

    def _show_token_help(self):
        msg = (
            "How to Get Your Discord User Account Token (Selfbot):\n\n"
            "1. Open Discord in your Web Browser (Chrome, Edge, or Firefox).\n"
            "2. Press Ctrl + Shift + I (DevTools) and switch to the 'Network' tab.\n"
            "3. Send a message or click any channel in Discord.\n"
            "4. In the Network tab filter, type 'messages' or 'science'.\n"
            "5. Click any request, look at 'Request Headers', and find 'authorization'.\n"
            "6. Copy the value and paste it here!\n\n"
            "Note: Never share your token with anyone."
        )
        QtWidgets.QMessageBox.information(self, "How to Get Your Discord Token", msg)

    def _save_token(self):
        token = self.edit_token.text().strip()
        if not token:
            QtWidgets.QMessageBox.warning(self, "Token Required", "Discord User Account token cannot be empty.")
            return
        self.storage.save_bot_token(token)
        self.lbl_token_status.setText("✓ Discord Account Token successfully saved to Windows Credential Manager!")
        self.lbl_token_status.setStyleSheet("color: #00ff88; font-weight: 700; font-size: 11px;")
        self.sig_token_saved.emit(token)
        QtWidgets.QMessageBox.information(self, "Token Saved", "Discord Account Token saved successfully! You can now start sniping.")

    def get_channel_ids(self) -> list:
        raw = self.edit_channels.toPlainText()
        # Extract Discord snowflake IDs (10 to 22 digits) handling mentions, URLs, spaces, and commas
        found = re.findall(r"\b\d{10,22}\b", raw)
        if not found:
            found = re.findall(r"\d{10,22}", raw)
        if not found:
            found = [c.strip() for c in re.split(r"[\s,;]+", raw) if c.strip().isdigit()]
        seen = set()
        cids = []
        for cid in found:
            if cid not in seen:
                seen.add(cid)
                cids.append(cid)
        return cids

    def _on_channels_text_changed(self):
        cids = self.get_channel_ids()
        if cids:
            self.lbl_channel_count.setText(f"Channels: {len(cids)} Channel(s) Detected (Click Save)")
            self.lbl_channel_count.setStyleSheet("color: #fbbf24; font-weight: 700; font-size: 11px;")
        else:
            self.lbl_channel_count.setText("Channels: Monitoring All (0 specific)")
            self.lbl_channel_count.setStyleSheet("color: #00f0ff; font-weight: 700; font-size: 11px;")

    def _save_channels(self):
        cids = self.get_channel_ids()
        self.storage.set_channel_ids(cids)
        self.sig_channels_saved.emit(cids)
        if cids:
            self.lbl_channel_count.setText(f"Channels: Monitoring {len(cids)} Specific Channel(s)")
            self.lbl_channel_count.setStyleSheet("color: #00ff88; font-weight: 700; font-size: 11px;")
        else:
            self.lbl_channel_count.setText("Channels: Monitoring All (0 specific)")
            self.lbl_channel_count.setStyleSheet("color: #00f0ff; font-weight: 700; font-size: 11px;")
        QtWidgets.QMessageBox.information(self, "Channels Applied", f"Successfully saved {len(cids)} monitored channel(s)!")

    def _load_channel_preset(self):
        self.edit_channels.setPlainText(", ".join(DEFAULT_SNIPER_CHANNEL_PRESETS))
        self._save_channels()

    def _clear_channels(self):
        self.edit_channels.clear()
        self._save_channels()

    def _on_category_changed(self, cat_id: str, enabled: bool, pause_sec: int):
        profiles = self.storage.get_profiles()
        for p in profiles:
            if p.id == cat_id:
                p.enabled = enabled
                p.pause_duration = pause_sec
                self.storage.save_profile(p)
                break
        self.sig_setting_changed.emit(f"cat_{cat_id}", {"enabled": enabled, "pause_duration": pause_sec})

    def update_sniper_status(self, is_running: bool, is_paused: bool):
        if is_running:
            if is_paused:
                self.lbl_engine_banner.setText("⏸ SNIPER IS PAUSED — Message monitoring temporarily paused (F6 to Resume)")
                self.lbl_engine_banner.setStyleSheet("color: #fbbf24; font-size: 13px; font-weight: 700; padding: 4px;")
                self.btn_start.setText("▶ RESUME SNIPER (F4)")
                self.btn_pause.setText("▶ RESUME SNIPER (F6)")
                self.btn_pause.setEnabled(True)
                self.btn_stop.setEnabled(True)
            else:
                self.lbl_engine_banner.setText("● SNIPER ACTIVE & SCANNING DISCORD — Real-time private server link monitoring active")
                self.lbl_engine_banner.setStyleSheet("color: #00ff88; font-size: 13px; font-weight: 700; padding: 4px;")
                self.btn_start.setText("⏹ STOP SNIPER (F4)")
                self.btn_start.setStyleSheet(
                    "QPushButton { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #be123c, stop:1 #f43f5e); "
                    "color: #ffffff; font-weight: 800; font-size: 13px; border: 1px solid #f43f5e; border-radius: 9px; padding: 10px 18px; } "
                    "QPushButton:hover { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #e11d48, stop:1 #fb7185); }"
                )
                self.btn_pause.setText("⏸ PAUSE SNIPER (F5)")
                self.btn_pause.setEnabled(True)
                self.btn_stop.setEnabled(True)
        else:
            self.lbl_engine_banner.setText("● SNIPER IS STOPPED — Click 'START SNIPING (F4)' to begin")
            self.lbl_engine_banner.setStyleSheet("color: #94a3b8; font-size: 13px; font-weight: 700; padding: 4px;")
            self.btn_start.setText("▶ START SNIPING (F4)")
            self.btn_start.setStyleSheet(
                "QPushButton { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4f46e5, stop:0.6 #6366f1, stop:1 #00d4ff); "
                "color: #ffffff; font-weight: 800; font-size: 13px; border: 1px solid #60a5fa55; border-radius: 9px; padding: 10px 18px; } "
                "QPushButton:hover { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #5b52f0, stop:0.6 #7477f7, stop:1 #38e1ff); }"
            )
            self.btn_pause.setText("⏸ PAUSE SNIPER (F5)")
            self.btn_pause.setEnabled(False)
            self.btn_stop.setEnabled(False)

    def update_cooldown_display(self, remaining_sec: float):
        if remaining_sec > 0:
            mins = int(remaining_sec // 60)
            secs = int(remaining_sec % 60)
            self.lbl_cooldown_banner.setText(f"⏳ 10-Minute Post-Join Cooldown: {mins}m {secs:02d}s remaining (Click 'RESET 10M COOLDOWN' to bypass)")
            self.lbl_cooldown_banner.setStyleSheet("color: #fbbf24; font-size: 12px; font-weight: 700; padding: 4px;")
            self.btn_reset_cooldown.setText(f"🔄 RESET COOLDOWN ({mins}m {secs:02d}s)")
            self.btn_reset_cooldown.setStyleSheet("background: #d97706; color: #ffffff; font-weight: 800; font-size: 12px; border-radius: 9px; padding: 10px 14px;")
        else:
            self.lbl_cooldown_banner.setText("✓ Cooldown: Ready to Join Next Server (No active cooldown)")
            self.lbl_cooldown_banner.setStyleSheet("color: #00ff88; font-size: 12px; font-weight: 700; padding: 4px;")
            self.btn_reset_cooldown.setText("🔄 RESET 10M COOLDOWN (F9)")
            self.btn_reset_cooldown.setStyleSheet("")

    def _toggle_pause(self):
        txt = self.btn_pause.text()
        if "PAUSE" in txt:
            self.btn_pause.setText("▶ RESUME SNIPER (F6)")
            self.sig_pause_sniper.emit()
        else:
            self.btn_pause.setText("⏸ PAUSE SNIPER (F5)")
            self.sig_resume_sniper.emit()

    def _on_roblox_client_changed(self, idx: int):
        clients = ["voidstrap", "vanilla", "auto"]
        if 0 <= idx < len(clients):
            if hasattr(self, "combo_test_client") and self.combo_test_client.currentIndex() != idx:
                self.combo_test_client.blockSignals(True)
                self.combo_test_client.setCurrentIndex(idx)
                self.combo_test_client.blockSignals(False)
            self.sig_setting_changed.emit("roblox_client", clients[idx])

    def _on_benchmark_client_changed(self, idx: int):
        clients = ["voidstrap", "vanilla", "auto"]
        if 0 <= idx < len(clients):
            if hasattr(self, "combo_roblox_client") and self.combo_roblox_client.currentIndex() != idx:
                self.combo_roblox_client.blockSignals(True)
                self.combo_roblox_client.setCurrentIndex(idx)
                self.combo_roblox_client.blockSignals(False)
            self.sig_setting_changed.emit("roblox_client", clients[idx])

    def _on_launch_method_changed(self, idx: int):
        modes = ["protocol", "direct_exe", "system"]
        if 0 <= idx < len(modes):
            if hasattr(self, "combo_test_method") and self.combo_test_method.currentIndex() != idx:
                self.combo_test_method.blockSignals(True)
                self.combo_test_method.setCurrentIndex(idx)
                self.combo_test_method.blockSignals(False)
            self.sig_setting_changed.emit("launch_method", modes[idx])

    def _on_test_join_clicked(self):
        url = self.edit_test_url.text().strip()
        if url:
            self.sig_test_join.emit(url)

    def _on_benchmark_method_changed(self, idx: int):
        modes = ["protocol", "direct_exe", "system"]
        if 0 <= idx < len(modes):
            if hasattr(self, "combo_launch_method") and self.combo_launch_method.currentIndex() != idx:
                self.combo_launch_method.blockSignals(True)
                self.combo_launch_method.setCurrentIndex(idx)
                self.combo_launch_method.blockSignals(False)
            self.sig_setting_changed.emit("launch_method", modes[idx])

    def set_benchmark_result(self, text: str, is_success: bool):
        color = "#00ff88" if is_success else "#f43f5e"
        self.lbl_benchmark_res.setText(text)
        self.lbl_benchmark_res.setStyleSheet(f"color: {color}; font-weight: 700; font-size: 11px;")
