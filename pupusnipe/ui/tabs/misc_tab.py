"""
PupuSnipe Miscellaneous Tab
Anti-bait filtering, User & Keyword Blacklists, Global Hotkeys, and Notification Options.
Wrapped in a responsive scroll container to prevent scaling/overflow bugs.
"""
from PySide6 import QtCore, QtGui, QtWidgets
import os
import threading
from ...core.storage import StorageManager
from ...core.audio import get_available_sounds, play_sound
from ...core.webhook import send_test_webhook


class MiscTab(QtWidgets.QWidget):
    sig_blacklists_updated = QtCore.Signal(list, list)
    sig_hotkeys_updated = QtCore.Signal(dict)
    sig_setting_changed = QtCore.Signal(str, object)

    def __init__(self, storage: StorageManager, parent=None):
        super().__init__(parent)
        self.storage = storage
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

        # 3. Notifications & Audio Alerts
        notif_group = QtWidgets.QGroupBox("Notifications & Custom Sound Effects")
        notif_layout = QtWidgets.QVBoxLayout(notif_group)
        notif_layout.setSpacing(12)
        notif_layout.setContentsMargins(16, 22, 16, 16)

        self.chk_toast = QtWidgets.QCheckBox("Enable Windows Desktop Toast Notifications on successful snipe")
        self.chk_toast.setChecked(True)
        self.chk_toast.toggled.connect(lambda v: self.sig_setting_changed.emit("enable_notifications", v))
        notif_layout.addWidget(self.chk_toast)

        self.chk_sound = QtWidgets.QCheckBox("Play Audio Sound Effect on Link Sniped")
        self.chk_sound.setChecked(True)
        self.chk_sound.toggled.connect(lambda v: self.sig_setting_changed.emit("play_sound", v))
        notif_layout.addWidget(self.chk_sound)

        # Sound Selector Row
        sound_row = QtWidgets.QHBoxLayout()
        sound_row.setSpacing(10)
        lbl_sfx = QtWidgets.QLabel("Snipe Sound Effect:")
        lbl_sfx.setStyleSheet("color: #cbd5e1; font-weight: 600; font-size: 11px;")
        lbl_sfx.setFixedWidth(140)

        self.combo_sound = QtWidgets.QComboBox()
        self.combo_sound.setMinimumHeight(32)
        for key, name in get_available_sounds():
            self.combo_sound.addItem(name, key)
        self.combo_sound.currentIndexChanged.connect(self._on_sound_selected)

        self.btn_test_sound = QtWidgets.QPushButton("🔊 Test Sound")
        self.btn_test_sound.setMinimumHeight(32)
        self.btn_test_sound.setFixedWidth(110)
        self.btn_test_sound.clicked.connect(self._test_sound)

        sound_row.addWidget(lbl_sfx)
        sound_row.addWidget(self.combo_sound, 1)
        sound_row.addWidget(self.btn_test_sound)
        notif_layout.addLayout(sound_row)

        # Custom Audio File Row (hidden unless "Custom" is selected)
        self.custom_file_widget = QtWidgets.QWidget()
        custom_layout = QtWidgets.QHBoxLayout(self.custom_file_widget)
        custom_layout.setContentsMargins(0, 0, 0, 0)
        custom_layout.setSpacing(10)

        lbl_custom = QtWidgets.QLabel("Custom File (.mp3/.wav):")
        lbl_custom.setStyleSheet("color: #94a3b8; font-size: 11px;")
        lbl_custom.setFixedWidth(140)

        self.edit_custom_path = QtWidgets.QLineEdit()
        self.edit_custom_path.setPlaceholderText("Select a local .mp3 or .wav audio file...")
        self.edit_custom_path.setMinimumHeight(30)
        self.edit_custom_path.textChanged.connect(lambda p: self.sig_setting_changed.emit("sound_custom_path", p.strip()))

        self.btn_browse_sound = QtWidgets.QPushButton("📂 Browse...")
        self.btn_browse_sound.setMinimumHeight(30)
        self.btn_browse_sound.setFixedWidth(90)
        self.btn_browse_sound.clicked.connect(self._browse_custom_sound)

        custom_layout.addWidget(lbl_custom)
        custom_layout.addWidget(self.edit_custom_path, 1)
        custom_layout.addWidget(self.btn_browse_sound)
        self.custom_file_widget.setVisible(False)
        notif_layout.addWidget(self.custom_file_widget)

        # Volume Slider Row
        vol_row = QtWidgets.QHBoxLayout()
        vol_row.setSpacing(10)
        lbl_vol = QtWidgets.QLabel("Sound Volume:")
        lbl_vol.setStyleSheet("color: #cbd5e1; font-weight: 600; font-size: 11px;")
        lbl_vol.setFixedWidth(140)

        self.slider_volume = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.slider_volume.setRange(0, 100)
        self.slider_volume.setValue(100)
        self.slider_volume.valueChanged.connect(self._on_volume_changed)

        self.lbl_volume_val = QtWidgets.QLabel("100%")
        self.lbl_volume_val.setStyleSheet("color: #00f0ff; font-weight: 700; font-size: 11px;")
        self.lbl_volume_val.setFixedWidth(50)

        vol_row.addWidget(lbl_vol)
        vol_row.addWidget(self.slider_volume, 1)
        vol_row.addWidget(self.lbl_volume_val)
        notif_layout.addLayout(vol_row)

        main_layout.addWidget(notif_group)

        # 4. Discord Webhook Alerts
        webhook_group = QtWidgets.QGroupBox("Discord Webhook Alerts (Send Private Server Links to Discord)")
        webhook_layout = QtWidgets.QVBoxLayout(webhook_group)
        webhook_layout.setSpacing(12)
        webhook_layout.setContentsMargins(16, 22, 16, 16)

        self.chk_webhook = QtWidgets.QCheckBox("Enable Discord Webhook Notifications on successful snipe")
        self.chk_webhook.setChecked(False)
        self.chk_webhook.toggled.connect(lambda v: self.sig_setting_changed.emit("webhook_enabled", v))
        webhook_layout.addWidget(self.chk_webhook)

        # Webhook URL Row
        url_row = QtWidgets.QHBoxLayout()
        url_row.setSpacing(10)
        lbl_wh_url = QtWidgets.QLabel("Webhook URL:")
        lbl_wh_url.setStyleSheet("color: #cbd5e1; font-weight: 600; font-size: 11px;")
        lbl_wh_url.setFixedWidth(120)

        self.edit_webhook_url = QtWidgets.QLineEdit()
        self.edit_webhook_url.setPlaceholderText("https://discord.com/api/webhooks/ID/TOKEN")
        self.edit_webhook_url.setMinimumHeight(32)
        self.edit_webhook_url.textChanged.connect(lambda u: self.sig_setting_changed.emit("webhook_url", u.strip()))

        url_row.addWidget(lbl_wh_url)
        url_row.addWidget(self.edit_webhook_url, 1)
        webhook_layout.addLayout(url_row)

        # Ping Everyone & Test Button Row
        actions_row = QtWidgets.QHBoxLayout()
        actions_row.setSpacing(12)

        self.chk_webhook_ping = QtWidgets.QCheckBox("Ping @everyone on Snipe")
        self.chk_webhook_ping.setChecked(True)
        self.chk_webhook_ping.toggled.connect(lambda v: self.sig_setting_changed.emit("webhook_ping_everyone", v))

        self.btn_test_webhook = QtWidgets.QPushButton("🧪 Test Webhook")
        self.btn_test_webhook.setMinimumHeight(32)
        self.btn_test_webhook.setFixedWidth(130)
        self.btn_test_webhook.clicked.connect(self._test_webhook)

        self.lbl_webhook_status = QtWidgets.QLabel("")
        self.lbl_webhook_status.setStyleSheet("font-size: 11px; font-weight: 600;")

        actions_row.addWidget(self.chk_webhook_ping)
        actions_row.addStretch(1)
        actions_row.addWidget(self.lbl_webhook_status)
        actions_row.addWidget(self.btn_test_webhook)
        webhook_layout.addLayout(actions_row)

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

        sound_key = self.storage.get_setting("sound_effect", "vine_boom")
        self.combo_sound.blockSignals(True)
        for i in range(self.combo_sound.count()):
            if self.combo_sound.itemData(i) == sound_key:
                self.combo_sound.setCurrentIndex(i)
                break
        self.combo_sound.blockSignals(False)

        custom_p = self.storage.get_setting("sound_custom_path", "")
        self.edit_custom_path.blockSignals(True)
        self.edit_custom_path.setText(str(custom_p))
        self.edit_custom_path.blockSignals(False)
        self.custom_file_widget.setVisible(sound_key == "custom")

        vol_val = self.storage.get_setting("sound_volume", 100)
        try:
            vol_int = int(vol_val)
        except Exception:
            vol_int = 100
        self.slider_volume.blockSignals(True)
        self.slider_volume.setValue(max(0, min(100, vol_int)))
        self.lbl_volume_val.setText(f"{vol_int}%")
        self.slider_volume.blockSignals(False)

        # Load Webhook settings
        wh_enabled = self.storage.get_setting("webhook_enabled", False)
        self.chk_webhook.blockSignals(True)
        self.chk_webhook.setChecked(bool(wh_enabled))
        self.chk_webhook.blockSignals(False)

        wh_url = self.storage.get_setting("webhook_url", "")
        self.edit_webhook_url.blockSignals(True)
        self.edit_webhook_url.setText(str(wh_url))
        self.edit_webhook_url.blockSignals(False)

        wh_ping = self.storage.get_setting("webhook_ping_everyone", True)
        self.chk_webhook_ping.blockSignals(True)
        self.chk_webhook_ping.setChecked(bool(wh_ping))
        self.chk_webhook_ping.blockSignals(False)

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

    def _on_sound_selected(self, index: int):
        key = self.combo_sound.itemData(index)
        self.custom_file_widget.setVisible(key == "custom")
        self.sig_setting_changed.emit("sound_effect", key)

    def _browse_custom_sound(self):
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Select Audio File",
            "",
            "Audio Files (*.mp3 *.wav *.wma);;All Files (*.*)"
        )
        if file_path:
            self.edit_custom_path.setText(file_path)
            self.sig_setting_changed.emit("sound_custom_path", file_path)

    def _on_volume_changed(self, val: int):
        self.lbl_volume_val.setText(f"{val}%")
        self.sig_setting_changed.emit("sound_volume", val)

    def _test_sound(self):
        key = self.combo_sound.currentData() or "vine_boom"
        custom_p = self.edit_custom_path.text().strip()
        vol = self.slider_volume.value()
        play_sound(key, custom_p, vol)

    def _test_webhook(self):
        url = self.edit_webhook_url.text().strip()
        if not url:
            self.lbl_webhook_status.setText("⚠️ Please enter a Webhook URL first!")
            self.lbl_webhook_status.setStyleSheet("color: #fbbf24; font-size: 11px; font-weight: 600;")
            return

        self.lbl_webhook_status.setText("Sending test ping...")
        self.lbl_webhook_status.setStyleSheet("color: #00f0ff; font-size: 11px; font-weight: 600;")
        self.btn_test_webhook.setEnabled(False)

        ping = self.chk_webhook_ping.isChecked()

        def _worker():
            success, msg = send_test_webhook(url, ping_everyone=ping)
            def _update_ui():
                self.btn_test_webhook.setEnabled(True)
                if success:
                    self.lbl_webhook_status.setText("✓ Webhook delivered successfully!")
                    self.lbl_webhook_status.setStyleSheet("color: #00ff88; font-size: 11px; font-weight: 700;")
                else:
                    self.lbl_webhook_status.setText(f"❌ Failed: {msg[:40]}")
                    self.lbl_webhook_status.setStyleSheet("color: #f87171; font-size: 11px; font-weight: 600;")
            QtCore.QMetaObject.invokeMethod(self, "_run_in_main", QtCore.Qt.QueuedConnection, QtCore.Q_ARG(object, _update_ui))

        threading.Thread(target=_worker, daemon=True).start()

    @QtCore.Slot(object)
    def _run_in_main(self, callback):
        callback()
