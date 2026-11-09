"""
FishSol Auto-Fishing & Biome Camping Tab
Integration with FishSol v2.1 macro for automated collection, selling, and fishing.
"""
from PySide6 import QtCore, QtGui, QtWidgets
from ..tabs.dashboard_tab import StatCard


class FishSolTab(QtWidgets.QWidget):
    sig_start_fishsol = QtCore.Signal()
    sig_pause_fishsol = QtCore.Signal()
    sig_resume_fishsol = QtCore.Signal()
    sig_stop_fishsol = QtCore.Signal()
    sig_run_join_sequence = QtCore.Signal()
    sig_launch_external_ahk = QtCore.Signal()
    sig_setting_changed = QtCore.Signal(str, object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(16)

        # 1. Header & Controls
        ctrl_group = QtWidgets.QGroupBox("FishSol Auto-Fishing Engine (from FishSol v2.1)")
        ctrl_layout = QtWidgets.QVBoxLayout(ctrl_group)
        ctrl_layout.setSpacing(12)
        ctrl_layout.setContentsMargins(14, 18, 14, 14)

        desc = QtWidgets.QLabel(
            "Integrated fishing bot. Automatically resets, opens the fishing collection, equips gear, "
            "walks the VIP selling path, and plays the fishing minigame. When a biome is sniped, "
            "PupuSnipe joins the server and immediately triggers the collection + selling path so you can stay in Corruption forever!"
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #8b949e; font-size: 12px;")
        ctrl_layout.addWidget(desc)

        btn_row = QtWidgets.QHBoxLayout()
        self.btn_start = QtWidgets.QPushButton("START FISHING MACRO")
        self.btn_start.setProperty("class", "btn-primary")
        self.btn_start.setMinimumHeight(40)
        self.btn_start.clicked.connect(self.sig_start_fishsol.emit)

        self.btn_pause = QtWidgets.QPushButton("PAUSE")
        self.btn_pause.setProperty("class", "btn-secondary")
        self.btn_pause.setMinimumHeight(40)
        self.btn_pause.clicked.connect(self._toggle_pause)

        self.btn_stop = QtWidgets.QPushButton("STOP")
        self.btn_stop.setProperty("class", "btn-danger")
        self.btn_stop.setMinimumHeight(40)
        self.btn_stop.clicked.connect(self.sig_stop_fishsol.emit)

        self.btn_test_join_seq = QtWidgets.QPushButton("Run Join Sequence Now")
        self.btn_test_join_seq.setProperty("class", "btn-secondary")
        self.btn_test_join_seq.setToolTip("Tests the Reset + Collection/Equip + Selling path immediately")
        self.btn_test_join_seq.clicked.connect(self.sig_run_join_sequence.emit)

        btn_row.addWidget(self.btn_start)
        btn_row.addWidget(self.btn_pause)
        btn_row.addWidget(self.btn_stop)
        btn_row.addWidget(self.btn_test_join_seq)
        ctrl_layout.addLayout(btn_row)

        main_layout.addWidget(ctrl_group)

        # 2. Live Stats Row
        stats_row = QtWidgets.QHBoxLayout()
        stats_row.setSpacing(12)

        self.card_fish = StatCard("Fish Caught", "0", "#00d4ff")
        self.card_cycles = StatCard("Cycles Completed", "0", "#3fb950")
        self.card_sells = StatCard("Sell Runs", "0", "#f0883e")
        self.card_status = StatCard("Status", "Idle", "#a371f7")

        stats_row.addWidget(self.card_fish)
        stats_row.addWidget(self.card_cycles)
        stats_row.addWidget(self.card_sells)
        stats_row.addWidget(self.card_status)

        main_layout.addLayout(stats_row)

        # 3. Macro Settings & Pathing Configuration
        settings_group = QtWidgets.QGroupBox("Pathing & Minigame Configuration")
        form_layout = QtWidgets.QFormLayout(settings_group)
        form_layout.setSpacing(12)
        form_layout.setContentsMargins(14, 18, 14, 14)

        self.chk_auto_join_fish = QtWidgets.QCheckBox("Auto-Trigger Collection & Selling Path when joining sniped server")
        self.chk_auto_join_fish.setChecked(True)
        self.chk_auto_join_fish.toggled.connect(lambda v: self.sig_setting_changed.emit("fishsol_auto_on_join", v))
        form_layout.addRow("Sniper Hook:", self.chk_auto_join_fish)

        self.chk_stay_in_biome = QtWidgets.QCheckBox("Stay in Target Biome (e.g. Corruption) forever while fishing")
        self.chk_stay_in_biome.setChecked(True)
        self.chk_stay_in_biome.toggled.connect(lambda v: self.sig_setting_changed.emit("fishsol_stay_in_biome", v))
        form_layout.addRow("Biome Camping:", self.chk_stay_in_biome)

        self.combo_pathing = QtWidgets.QComboBox()
        self.combo_pathing.addItems(["Vip Pathing", "Non Vip Pathing", "Abyssal Pathing"])
        self.combo_pathing.currentTextChanged.connect(lambda v: self.sig_setting_changed.emit("fishsol_pathing_mode", v))
        form_layout.addRow("Pathing Mode:", self.combo_pathing)

        self.combo_res = QtWidgets.QComboBox()
        self.combo_res.addItems(["1080p (1920x1080)", "1440p (2560x1440)", "1366x768"])
        self.combo_res.currentTextChanged.connect(lambda v: self.sig_setting_changed.emit("fishsol_resolution", v))
        form_layout.addRow("Roblox Resolution:", self.combo_res)

        self.chk_sell_all = QtWidgets.QCheckBox("Enable 'Sell All' button")
        self.chk_sell_all.setChecked(True)
        self.chk_sell_all.toggled.connect(lambda v: self.sig_setting_changed.emit("fishsol_sell_all", v))
        form_layout.addRow("Selling Mode:", self.chk_sell_all)

        self.spin_fish_loop = QtWidgets.QSpinBox()
        self.spin_fish_loop.setRange(1, 100)
        self.spin_fish_loop.setValue(15)
        self.spin_fish_loop.setSuffix(" cycles before selling")
        self.spin_fish_loop.valueChanged.connect(lambda v: self.sig_setting_changed.emit("fishsol_loop_count", v))
        form_layout.addRow("Fishing Loop Count:", self.spin_fish_loop)

        # External AHK Launcher button
        ahk_row = QtWidgets.QHBoxLayout()
        btn_ahk = QtWidgets.QPushButton("Launch External D:\\FishSol-v2.1\\FishSol-v2.1.ahk")
        btn_ahk.setProperty("class", "btn-secondary")
        btn_ahk.clicked.connect(self.sig_launch_external_ahk.emit)
        ahk_row.addWidget(btn_ahk)
        ahk_row.addStretch()
        form_layout.addRow("External Macro:", ahk_row)

        main_layout.addWidget(settings_group)
        main_layout.addStretch()

    def _toggle_pause(self):
        txt = self.btn_pause.text()
        if "PAUSE" in txt:
            self.btn_pause.setText("RESUME")
            self.sig_pause_fishsol.emit()
        else:
            self.btn_pause.setText("PAUSE")
            self.sig_resume_fishsol.emit()

    def update_stats(self, stats: dict):
        self.card_fish.set_value(str(stats.get("fish_caught", 0)))
        self.card_cycles.set_value(str(stats.get("cycles_completed", 0)))
        self.card_sells.set_value(str(stats.get("total_sells", 0)))

        is_running = stats.get("is_running", False)
        is_paused = stats.get("is_paused", False)
        if is_running:
            status_txt = "Paused" if is_paused else "Fishing"
        else:
            status_txt = "Idle"
        self.card_status.set_value(status_txt)

    def set_macro_status(self, text: str):
        self.card_status.set_value(text[:18])
