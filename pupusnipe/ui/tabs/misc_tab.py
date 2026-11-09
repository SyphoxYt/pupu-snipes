"""
PupuSnipe Miscellaneous Tab
Anti-bait filtering, User & Keyword Blacklists, Global Hotkeys, and Notification Options.
Wrapped in a responsive scroll container to prevent scaling/overflow bugs.
"""
from PySide6 import QtCore, QtGui, QtWidgets
from ...core.storage import StorageManager


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

        # 3. Notifications & Audio
        notif_group = QtWidgets.QGroupBox("Notifications & Audio Alerts")
        notif_layout = QtWidgets.QVBoxLayout(notif_group)
        notif_layout.setSpacing(10)
        notif_layout.setContentsMargins(16, 22, 16, 16)

        self.chk_toast = QtWidgets.QCheckBox("Enable Windows Desktop Toast Notifications on successful snipe")
        self.chk_toast.setChecked(True)
        self.chk_toast.toggled.connect(lambda v: self.sig_setting_changed.emit("enable_notifications", v))

        self.chk_sound = QtWidgets.QCheckBox("Play Audio Chime Sound on Link Sniped")
        self.chk_sound.setChecked(True)
        self.chk_sound.toggled.connect(lambda v: self.sig_setting_changed.emit("play_sound", v))

        notif_layout.addWidget(self.chk_toast)
        notif_layout.addWidget(self.chk_sound)
        main_layout.addWidget(notif_group)

        scroll.setWidget(content)
        outer_layout.addWidget(scroll)

    def load_settings(self):
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
