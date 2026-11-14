"""
PupuSnipe Miscellaneous Tab
Anti-bait filtering, User & Keyword Blacklists, Global Hotkeys, and Notification Options.
Wrapped in a responsive scroll container to prevent scaling/overflow bugs.
"""
import os

from PySide6 import QtCore, QtGui, QtWidgets
from ...core.browsers import BROWSER_CHOICES, describe_browser, find_browser_executable
from ...core.storage import StorageManager
from ...core.sounds import (
    CUSTOM_SOUND_ID,
    DEFAULT_SOUND_ID,
    SOUND_PRESETS,
    SYSTEM_BEEP_ID,
    SoundManager,
    get_preset_label,
)


class MiscTab(QtWidgets.QWidget):
    sig_blacklists_updated = QtCore.Signal(list, list)
    sig_hotkeys_updated = QtCore.Signal(dict)
    sig_setting_changed = QtCore.Signal(str, object)
    sig_test_webhook = QtCore.Signal(str, bool)

    def __init__(self, storage: StorageManager, parent=None):
        super().__init__(parent)
        self.storage = storage
        self._custom_sound_path = ""
        self._gateway_browser_path = ""
        self._preview_sound = SoundManager()
        self._init_ui()
        self.load_settings()

    def _init_ui(self):
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

        # 1. Anti-Bait & Blacklists Group
        ab_group = QtWidgets.QGroupBox("Anti-Bait Protection & Blacklists")
        ab_layout = QtWidgets.QHBoxLayout(ab_group)
        ab_layout.setSpacing(16)
        ab_layout.setContentsMargins(16, 22, 16, 16)

        # User Blacklist Box
        user_box = QtWidgets.QVBoxLayout()
        user_box.setSpacing(8)
        u_label = QtWidgets.QLabel("Blacklisted User IDs / Names (Ignored automatically):")
        u_label.setStyleSheet("color: #94a3b8; font-weight: 600; font-size: 11px;")
        user_box.addWidget(u_label)
        self.list_users = QtWidgets.QListWidget()
        self.list_users.setMinimumHeight(140)
        user_box.addWidget(self.list_users)

        u_input_row = QtWidgets.QHBoxLayout()
        u_input_row.setSpacing(6)
        self.edit_user_input = QtWidgets.QLineEdit()
        self.edit_user_input.setPlaceholderText("User ID or Username...")
        btn_add_user = QtWidgets.QPushButton("+ Add")
        btn_add_user.setProperty("class", "btn-secondary")
        btn_add_user.clicked.connect(self._add_user_blacklist)
        btn_del_user = QtWidgets.QPushButton("Delete")
        btn_del_user.setProperty("class", "btn-danger")
        btn_del_user.clicked.connect(self._del_user_blacklist)
        u_input_row.addWidget(self.edit_user_input)
        u_input_row.addWidget(btn_add_user)
        u_input_row.addWidget(btn_del_user)
        user_box.addLayout(u_input_row)

        ab_layout.addLayout(user_box)

        # Keyword Blacklist Box
        kw_box = QtWidgets.QVBoxLayout()
        kw_box.setSpacing(8)
        k_label = QtWidgets.QLabel("Blacklisted Bait Keywords (Drops bait messages):")
        k_label.setStyleSheet("color: #94a3b8; font-weight: 600; font-size: 11px;")
        kw_box.addWidget(k_label)
        self.list_kws = QtWidgets.QListWidget()
        self.list_kws.setMinimumHeight(140)
        kw_box.addWidget(self.list_kws)

        k_input_row = QtWidgets.QHBoxLayout()
        k_input_row.setSpacing(6)
        self.edit_kw_input = QtWidgets.QLineEdit()
        self.edit_kw_input.setPlaceholderText("e.g. fake, scam, expired, troll...")
        btn_add_kw = QtWidgets.QPushButton("+ Add")
        btn_add_kw.setProperty("class", "btn-secondary")
        btn_add_kw.clicked.connect(self._add_kw_blacklist)
        btn_del_kw = QtWidgets.QPushButton("Delete")
        btn_del_kw.setProperty("class", "btn-danger")
        btn_del_kw.clicked.connect(self._del_kw_blacklist)
        k_input_row.addWidget(self.edit_kw_input)
        k_input_row.addWidget(btn_add_kw)
        k_input_row.addWidget(btn_del_kw)
        kw_box.addLayout(k_input_row)

        ab_layout.addLayout(kw_box)
        main_layout.addWidget(ab_group)

        # 2. Configurable Hotkeys
        hk_group = QtWidgets.QGroupBox("Global Hotkeys")
        hk_form = QtWidgets.QFormLayout(hk_group)
        hk_form.setSpacing(12)
        hk_form.setContentsMargins(16, 22, 16, 16)

        self.edit_hk_toggle = QtWidgets.QLineEdit("F4")
        self.edit_hk_pause = QtWidgets.QLineEdit("F5")
        self.edit_hk_resume = QtWidgets.QLineEdit("F6")
        self.edit_hk_stop = QtWidgets.QLineEdit("F7")
        self.edit_hk_fishsol = QtWidgets.QLineEdit("F8")
        self.edit_hk_reset_cd = QtWidgets.QLineEdit("F9")

        for ed in [self.edit_hk_toggle, self.edit_hk_pause, self.edit_hk_resume, self.edit_hk_stop, self.edit_hk_fishsol, self.edit_hk_reset_cd]:
            ed.setMaximumWidth(120)
            ed.setMinimumHeight(32)
            ed.textChanged.connect(self._emit_hotkeys)

        hk_form.addRow("Toggle Sniper (Start / Stop):", self.edit_hk_toggle)
        hk_form.addRow("Pause Monitoring:", self.edit_hk_pause)
        hk_form.addRow("Resume Monitoring:", self.edit_hk_resume)
        hk_form.addRow("Emergency Stop:", self.edit_hk_stop)
        hk_form.addRow("Toggle Fishing Automation:", self.edit_hk_fishsol)
        hk_form.addRow("Reset 10-Minute Cooldown:", self.edit_hk_reset_cd)

        main_layout.addWidget(hk_group)

        # 3. Notifications & Audio
        notif_group = QtWidgets.QGroupBox("Notifications & Audio Alerts")
        notif_layout = QtWidgets.QVBoxLayout(notif_group)
        notif_layout.setSpacing(10)
        notif_layout.setContentsMargins(16, 22, 16, 16)

        self.chk_toast = QtWidgets.QCheckBox("Enable Windows Desktop Toast Notifications on successful snipe")
        self.chk_toast.setChecked(True)
        self.chk_toast.toggled.connect(lambda v: self.sig_setting_changed.emit("enable_notifications", v))

        self.chk_sound = QtWidgets.QCheckBox("Play a sound effect when a link is sniped")
        self.chk_sound.setChecked(True)
        self.chk_sound.toggled.connect(lambda v: self.sig_setting_changed.emit("play_sound", v))

        sound_row = QtWidgets.QHBoxLayout()
        sound_row.setSpacing(8)
        sound_label = QtWidgets.QLabel("Snipe sound:")
        sound_label.setStyleSheet("color: #94a3b8; font-weight: 600; font-size: 11px;")
        sound_row.addWidget(sound_label)

        self.combo_sound = QtWidgets.QComboBox()
        self.combo_sound.setMinimumHeight(32)
        for preset in SOUND_PRESETS:
            self.combo_sound.addItem(preset["name"], preset["id"])
            self.combo_sound.setItemData(
                self.combo_sound.count() - 1,
                preset.get("description", ""),
                QtCore.Qt.ToolTipRole,
            )
        self.combo_sound.addItem(get_preset_label(SYSTEM_BEEP_ID), SYSTEM_BEEP_ID)
        self.combo_sound.addItem(get_preset_label(CUSTOM_SOUND_ID), CUSTOM_SOUND_ID)
        self.combo_sound.currentIndexChanged.connect(self._on_sound_preset_changed)
        sound_row.addWidget(self.combo_sound, 1)

        self.btn_browse_sound = QtWidgets.QPushButton("📂 Browse…")
        self.btn_browse_sound.setProperty("class", "btn-secondary")
        self.btn_browse_sound.clicked.connect(self._browse_custom_sound)
        sound_row.addWidget(self.btn_browse_sound)

        self.btn_preview_sound = QtWidgets.QPushButton("▶ Preview")
        self.btn_preview_sound.setProperty("class", "btn-secondary")
        self.btn_preview_sound.clicked.connect(self._preview_selected_sound)
        sound_row.addWidget(self.btn_preview_sound)

        notif_layout.addWidget(self.chk_toast)
        notif_layout.addWidget(self.chk_sound)
        notif_layout.addLayout(sound_row)

        self.lbl_custom_sound = QtWidgets.QLabel("")
        self.lbl_custom_sound.setWordWrap(True)
        self.lbl_custom_sound.setStyleSheet("color: #64748b; font-size: 10px; padding-left: 2px;")
        notif_layout.addWidget(self.lbl_custom_sound)
        main_layout.addWidget(notif_group)

        # 4. Protected Join Page Browser
        gateway_group = QtWidgets.QGroupBox("Protected Join Pages (xe33hunt)")
        gateway_layout = QtWidgets.QVBoxLayout(gateway_group)
        gateway_layout.setSpacing(10)
        gateway_layout.setContentsMargins(16, 22, 16, 16)

        gateway_hint = QtWidgets.QLabel(
            "xe33hunt hides its Roblox join link behind Cloudflare Turnstile. When native "
            "resolution is enabled, PupuSnipe opens the page off-screen, waits for the "
            "verification, captures the roblox:// redirect, and joins through the same "
            "launcher used for every other link. If Cloudflare still needs you, the page "
            "opens in the browser selected below."
        )
        gateway_hint.setWordWrap(True)
        gateway_hint.setStyleSheet("color: #64748b; font-size: 10px;")
        gateway_layout.addWidget(gateway_hint)

        self.chk_gateway_resolver = QtWidgets.QCheckBox(
            "Try native launch (resolve Cloudflare off-screen first)"
        )
        self.chk_gateway_resolver.toggled.connect(
            lambda v: self.sig_setting_changed.emit("gateway_resolver_enabled", bool(v))
        )
        gateway_layout.addWidget(self.chk_gateway_resolver)

        gateway_row = QtWidgets.QHBoxLayout()
        gateway_row.setSpacing(8)
        gateway_label = QtWidgets.QLabel("Open with:")
        gateway_label.setStyleSheet("color: #94a3b8; font-weight: 600; font-size: 11px;")
        gateway_row.addWidget(gateway_label)

        self.combo_gateway_browser = QtWidgets.QComboBox()
        self.combo_gateway_browser.setMinimumHeight(32)
        for choice in BROWSER_CHOICES:
            self.combo_gateway_browser.addItem(choice["name"], choice["id"])
        self.combo_gateway_browser.currentIndexChanged.connect(self._on_gateway_browser_changed)
        gateway_row.addWidget(self.combo_gateway_browser, 1)

        self.btn_browse_gateway_browser = QtWidgets.QPushButton("📂 Browse…")
        self.btn_browse_gateway_browser.setProperty("class", "btn-secondary")
        self.btn_browse_gateway_browser.clicked.connect(self._browse_gateway_browser)
        gateway_row.addWidget(self.btn_browse_gateway_browser)
        gateway_layout.addLayout(gateway_row)

        self.edit_gateway_browser_path = QtWidgets.QLineEdit()
        self.edit_gateway_browser_path.setReadOnly(True)
        self.edit_gateway_browser_path.setPlaceholderText("Custom browser executable path")
        self.edit_gateway_browser_path.setMinimumHeight(32)
        self.edit_gateway_browser_path.setVisible(False)
        gateway_layout.addWidget(self.edit_gateway_browser_path)

        self.lbl_gateway_browser_status = QtWidgets.QLabel("")
        self.lbl_gateway_browser_status.setWordWrap(True)
        self.lbl_gateway_browser_status.setStyleSheet("color: #94a3b8; font-size: 10px;")
        gateway_layout.addWidget(self.lbl_gateway_browser_status)

        main_layout.addWidget(gateway_group)

        # 5. Discord Webhook Alerts
        webhook_group = QtWidgets.QGroupBox("Discord Webhook Alerts")
        webhook_layout = QtWidgets.QVBoxLayout(webhook_group)
        webhook_layout.setSpacing(10)
        webhook_layout.setContentsMargins(16, 22, 16, 16)

        self.chk_webhook = QtWidgets.QCheckBox("Send a webhook alert when a server is sniped")
        self.chk_webhook.toggled.connect(lambda v: self.sig_setting_changed.emit("webhook_enabled", bool(v)))
        webhook_layout.addWidget(self.chk_webhook)

        webhook_row = QtWidgets.QHBoxLayout()
        webhook_row.setSpacing(8)
        self.edit_webhook_url = QtWidgets.QLineEdit()
        self.edit_webhook_url.setPlaceholderText("https://discord.com/api/webhooks/…")
        self.edit_webhook_url.setEchoMode(QtWidgets.QLineEdit.Password)
        self.edit_webhook_url.setMinimumHeight(34)
        self.edit_webhook_url.editingFinished.connect(self._on_webhook_url_edited)
        webhook_row.addWidget(self.edit_webhook_url, 1)

        self.btn_show_webhook = QtWidgets.QPushButton("Show")
        self.btn_show_webhook.setProperty("class", "btn-secondary")
        self.btn_show_webhook.setCheckable(True)
        self.btn_show_webhook.setMaximumWidth(64)
        self.btn_show_webhook.toggled.connect(self._toggle_webhook_visibility)
        webhook_row.addWidget(self.btn_show_webhook)

        self.btn_test_webhook = QtWidgets.QPushButton("🚀 Send Test")
        self.btn_test_webhook.setProperty("class", "btn-secondary")
        self.btn_test_webhook.clicked.connect(self._test_webhook)
        webhook_row.addWidget(self.btn_test_webhook)
        webhook_layout.addLayout(webhook_row)

        self.chk_ping_everyone = QtWidgets.QCheckBox("Ping @everyone in the webhook message")
        self.chk_ping_everyone.setChecked(True)
        self.chk_ping_everyone.toggled.connect(lambda v: self.sig_setting_changed.emit("webhook_ping_everyone", bool(v)))
        webhook_layout.addWidget(self.chk_ping_everyone)

        hint = QtWidgets.QLabel(
            "The alert includes the sniped biome, source server/channel, latency, "
            "and a clickable Roblox join link. The biome is updated automatically once confirmed in-game."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #64748b; font-size: 10px;")
        webhook_layout.addWidget(hint)

        self.lbl_webhook_status = QtWidgets.QLabel("")
        self.lbl_webhook_status.setWordWrap(True)
        self.lbl_webhook_status.setStyleSheet("color: #94a3b8; font-size: 10px;")
        self.lbl_webhook_status.setVisible(False)
        webhook_layout.addWidget(self.lbl_webhook_status)

        main_layout.addWidget(webhook_group)

        scroll.setWidget(content)
        outer_layout.addWidget(scroll)

    def load_settings(self):
        # Load notification & sound toggles
        toast_val = self.storage.get_setting("enable_notifications", True)
        self.chk_toast.blockSignals(True)
        self.chk_toast.setChecked(bool(toast_val))
        self.chk_toast.blockSignals(False)

        sound_val = self.storage.get_setting("play_sound", True)
        self.chk_sound.blockSignals(True)
        self.chk_sound.setChecked(bool(sound_val))
        self.chk_sound.blockSignals(False)

        # Load snipe sound preset + optional custom WAV
        self._custom_sound_path = str(self.storage.get_setting("custom_sound_path", "") or "")
        sound_preset = str(self.storage.get_setting("sound_preset", DEFAULT_SOUND_ID) or DEFAULT_SOUND_ID)
        valid_ids = {p["id"] for p in SOUND_PRESETS} | {SYSTEM_BEEP_ID, CUSTOM_SOUND_ID}
        if sound_preset not in valid_ids:
            sound_preset = DEFAULT_SOUND_ID
        self._set_sound_combo(sound_preset)
        self._update_sound_controls()

        # Load protected join-page browser
        self._gateway_browser_path = str(self.storage.get_setting("gateway_browser_path", "") or "")
        gateway_browser = str(self.storage.get_setting("gateway_browser", "default") or "default")
        valid_browsers = {choice["id"] for choice in BROWSER_CHOICES}
        if gateway_browser not in valid_browsers:
            gateway_browser = "default"
        self._set_gateway_browser_combo(gateway_browser)
        self._update_gateway_browser_controls()

        resolver_enabled = self.storage.get_setting("gateway_resolver_enabled", True)
        self.chk_gateway_resolver.blockSignals(True)
        self.chk_gateway_resolver.setChecked(bool(resolver_enabled))
        self.chk_gateway_resolver.blockSignals(False)

        # Load webhook settings
        webhook_enabled = self.storage.get_setting("webhook_enabled", False)
        webhook_url = str(self.storage.get_setting("webhook_url", "") or "")
        ping_everyone = self.storage.get_setting("webhook_ping_everyone", True)

        self.chk_webhook.blockSignals(True)
        self.chk_webhook.setChecked(bool(webhook_enabled))
        self.chk_webhook.blockSignals(False)

        self.edit_webhook_url.blockSignals(True)
        self.edit_webhook_url.setText(webhook_url)
        self.edit_webhook_url.blockSignals(False)

        self.chk_ping_everyone.blockSignals(True)
        self.chk_ping_everyone.setChecked(bool(ping_everyone))
        self.chk_ping_everyone.blockSignals(False)

        # Load hotkeys
        saved_hk = self.storage.get_setting("hotkeys", {})
        if isinstance(saved_hk, dict):
            if "toggle" in saved_hk:
                self.edit_hk_toggle.setText(saved_hk["toggle"].upper())
            if "pause" in saved_hk:
                self.edit_hk_pause.setText(saved_hk["pause"].upper())
            if "resume" in saved_hk:
                self.edit_hk_resume.setText(saved_hk["resume"].upper())
            if "emergency_stop" in saved_hk:
                self.edit_hk_stop.setText(saved_hk["emergency_stop"].upper())
            if "fish" in saved_hk:
                self.edit_hk_fishsol.setText(saved_hk["fish"].upper())
            if "reset_cooldown" in saved_hk:
                self.edit_hk_reset_cd.setText(saved_hk["reset_cooldown"].upper())

        # Load blacklists
        self.list_users.clear()
        users = self.storage.get_blacklist("user")
        for u in users:
            self.list_users.addItem(u)

        self.list_kws.clear()
        kws = self.storage.get_blacklist("keyword")
        for k in kws:
            self.list_kws.addItem(k)

        self.sig_blacklists_updated.emit(users, kws)

    def _add_user_blacklist(self):
        val = self.edit_user_input.text().strip()
        if val:
            self.storage.add_blacklist_item("user", val)
            self.edit_user_input.clear()
            self.load_settings()

    def _del_user_blacklist(self):
        item = self.list_users.currentItem()
        if item:
            self.storage.remove_blacklist_item("user", item.text())
            self.load_settings()

    def _add_kw_blacklist(self):
        val = self.edit_kw_input.text().strip()
        if val:
            self.storage.add_blacklist_item("keyword", val)
            self.edit_kw_input.clear()
            self.load_settings()

    def _del_kw_blacklist(self):
        item = self.list_kws.currentItem()
        if item:
            self.storage.remove_blacklist_item("keyword", item.text())
            self.load_settings()

    def _emit_hotkeys(self):
        hk_map = {
            "toggle": self.edit_hk_toggle.text().strip().lower(),
            "pause": self.edit_hk_pause.text().strip().lower(),
            "resume": self.edit_hk_resume.text().strip().lower(),
            "emergency_stop": self.edit_hk_stop.text().strip().lower(),
            "fish": self.edit_hk_fishsol.text().strip().lower(),
            "reset_cooldown": self.edit_hk_reset_cd.text().strip().lower()
        }
        self.sig_hotkeys_updated.emit(hk_map)

    # --- Snipe Sound Selection ---
    def _set_sound_combo(self, preset_id: str):
        index = self.combo_sound.findData(preset_id)
        if index < 0:
            index = self.combo_sound.findData(DEFAULT_SOUND_ID)
        self.combo_sound.blockSignals(True)
        self.combo_sound.setCurrentIndex(max(0, index))
        self.combo_sound.blockSignals(False)

    def _update_sound_controls(self):
        preset_id = self.combo_sound.currentData()
        is_custom = preset_id == CUSTOM_SOUND_ID
        self.btn_browse_sound.setEnabled(is_custom)
        if is_custom:
            valid_custom = (
                bool(self._custom_sound_path)
                and os.path.isfile(self._custom_sound_path)
                and self._custom_sound_path.lower().endswith(".wav")
            )
            if valid_custom:
                self.lbl_custom_sound.setText(f"Using custom file: {os.path.basename(self._custom_sound_path)}")
                self.lbl_custom_sound.setStyleSheet("color: #00ff88; font-size: 10px; padding-left: 2px;")
            elif self._custom_sound_path:
                self.lbl_custom_sound.setText(f"Custom file missing or not a .wav: {self._custom_sound_path}")
                self.lbl_custom_sound.setStyleSheet("color: #ff6b6b; font-size: 10px; padding-left: 2px;")
            else:
                self.lbl_custom_sound.setText("No custom .wav selected — click Browse… to choose one.")
                self.lbl_custom_sound.setStyleSheet("color: #64748b; font-size: 10px; padding-left: 2px;")
            self.lbl_custom_sound.setVisible(True)
        else:
            self.lbl_custom_sound.setVisible(False)

    def _on_sound_preset_changed(self, _index: int):
        preset_id = self.combo_sound.currentData()
        self.sig_setting_changed.emit("sound_preset", preset_id)
        if preset_id == CUSTOM_SOUND_ID and (
            not self._custom_sound_path or not os.path.isfile(self._custom_sound_path)
        ):
            self._browse_custom_sound()
        self._update_sound_controls()

    def _browse_custom_sound(self):
        start_dir = os.path.dirname(self._custom_sound_path) if self._custom_sound_path else ""
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Select Snipe Sound (.wav)",
            start_dir,
            "WAV audio (*.wav)",
        )
        if path:
            if not path.lower().endswith(".wav"):
                QtWidgets.QMessageBox.warning(
                    self,
                    "Unsupported Sound File",
                    "PupuSnipe can only play uncompressed .wav files for snipe alerts.\n\n"
                    "Please choose a .wav file (or convert your sound to WAV first).",
                )
                return
            self._custom_sound_path = path
            self.sig_setting_changed.emit("custom_sound_path", path)
            self._set_sound_combo(CUSTOM_SOUND_ID)
            self.sig_setting_changed.emit("sound_preset", CUSTOM_SOUND_ID)
        self._update_sound_controls()

    def _preview_selected_sound(self):
        self._preview_sound.set_selection(
            self.combo_sound.currentData(),
            self._custom_sound_path,
        )
        self._preview_sound.play()

    # --- Protected Join Page Browser ---
    def _set_gateway_browser_combo(self, browser_id: str):
        index = self.combo_gateway_browser.findData(browser_id)
        if index < 0:
            index = self.combo_gateway_browser.findData("default")
        self.combo_gateway_browser.blockSignals(True)
        self.combo_gateway_browser.setCurrentIndex(max(0, index))
        self.combo_gateway_browser.blockSignals(False)

    def _on_gateway_browser_changed(self, _index: int):
        browser_id = self.combo_gateway_browser.currentData() or "default"
        self.sig_setting_changed.emit("gateway_browser", browser_id)
        if browser_id == "custom" and (
            not self._gateway_browser_path
            or not os.path.isfile(self._gateway_browser_path)
        ):
            self._browse_gateway_browser()
        self._update_gateway_browser_controls()

    def _browse_gateway_browser(self):
        start_dir = (
            os.path.dirname(self._gateway_browser_path)
            if self._gateway_browser_path
            else os.environ.get("PROGRAMFILES", "")
        )
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Select Browser Executable",
            start_dir,
            "Browser executable (*.exe)",
        )
        if path:
            self._gateway_browser_path = path
            self.sig_setting_changed.emit("gateway_browser_path", path)
            self._set_gateway_browser_combo("custom")
            self.sig_setting_changed.emit("gateway_browser", "custom")
        self._update_gateway_browser_controls()

    def _update_gateway_browser_controls(self):
        browser_id = self.combo_gateway_browser.currentData() or "default"
        is_custom = browser_id == "custom"
        self.edit_gateway_browser_path.setVisible(is_custom)
        self.edit_gateway_browser_path.setText(self._gateway_browser_path)

        if is_custom:
            if self._gateway_browser_path and os.path.isfile(self._gateway_browser_path):
                status = f"Launching: {self._gateway_browser_path}"
                color = "#00ff88"
            elif self._gateway_browser_path:
                status = f"Custom browser not found: {self._gateway_browser_path}"
                color = "#ff6b6b"
            else:
                status = "No custom browser selected — click Browse… to choose one."
                color = "#64748b"
        elif browser_id == "default":
            status = describe_browser("default")
            color = "#94a3b8"
        else:
            path = find_browser_executable(browser_id)
            status = describe_browser(browser_id)
            color = "#00ff88" if path else "#ffb86b"

        self.lbl_gateway_browser_status.setText(status)
        self.lbl_gateway_browser_status.setStyleSheet(f"color: {color}; font-size: 10px;")

    # --- Discord Webhook ---
    def _on_webhook_url_edited(self):
        url = self.edit_webhook_url.text().strip()
        self.edit_webhook_url.blockSignals(True)
        self.edit_webhook_url.setText(url)
        self.edit_webhook_url.blockSignals(False)
        self.sig_setting_changed.emit("webhook_url", url)

    def _toggle_webhook_visibility(self, shown: bool):
        self.edit_webhook_url.setEchoMode(
            QtWidgets.QLineEdit.Normal if shown else QtWidgets.QLineEdit.Password
        )
        self.btn_show_webhook.setText("Hide" if shown else "Show")

    def _test_webhook(self):
        url = self.edit_webhook_url.text().strip()
        if not url:
            self.set_webhook_status("Paste a Discord webhook URL first.", False)
            return
        self.sig_setting_changed.emit("webhook_url", url)
        self.set_webhook_status("Sending test message to Discord…", None)
        self.sig_test_webhook.emit(url, self.chk_ping_everyone.isChecked())

    @QtCore.Slot(bool, str)
    def set_webhook_test_result(self, ok: bool, message: str):
        self.set_webhook_status(message, ok)

    def set_webhook_status(self, message: str, ok=None):
        color = "#94a3b8" if ok is None else ("#00ff88" if ok else "#ff6b6b")
        self.lbl_webhook_status.setText(str(message or ""))
        self.lbl_webhook_status.setStyleSheet(f"color: {color}; font-size: 10px;")
        self.lbl_webhook_status.setVisible(bool(message))
