"""
PupuSnipe Fishing Tab (Integrated from FishSol v2.1)
Automated Sol's RNG fishing engine with collection navigation, selling path, and biome camping.
Wrapped in a responsive scroll container to prevent scaling/overflow bugs.
"""
from PySide6 import QtCore, QtGui, QtWidgets
from ..tabs.dashboard_tab import StatCard


class FishingTab(QtWidgets.QWidget):
    sig_start_fishing = QtCore.Signal()
    sig_pause_fishing = QtCore.Signal()
    sig_resume_fishing = QtCore.Signal()
    sig_stop_fishing = QtCore.Signal()
    sig_run_join_sequence = QtCore.Signal()
    sig_launch_external_ahk = QtCore.Signal()
    sig_setting_changed = QtCore.Signal(str, object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        # Outer scroll area prevents scaling/DPI clipping
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

        # 1. Main Controls & Simple Explanation
        ctrl_group = QtWidgets.QGroupBox("Sol's RNG Auto-Fishing & Biome Camping Engine")
        ctrl_layout = QtWidgets.QVBoxLayout(ctrl_group)
        ctrl_layout.setSpacing(12)
        ctrl_layout.setContentsMargins(16, 22, 16, 16)

        desc = QtWidgets.QLabel(
            "<b>How Sol's RNG Fishing Automation Works:</b><br>"
            "• <b>Real-Time Minigame Reeling:</b> Scans the catch minigame bar (757&ndash;1161px) at sub-0.2ms speed, automatically balancing and reeling your hook.<br>"
            "• <b>Auto-Selling Path:</b> When your fish inventory fills up, walks to the merchant and clicks 'Sell All'.<br>"
            "• <b>Stay in Biome Forever:</b> When PupuSnipe snipes a rare server (like <b>Corruption</b>, <b>Glitched</b>, or <b>Dreamspace</b>), "
            "it triggers character reset (<code>Esc R Enter</code>), opens the Collection menu (<code>30, 406</code>) to equip your rod & aura, and "
            "<span style='color: #00ff88; font-weight: bold;'>camps in that biome indefinitely</span> while auto-fishing and selling on a loop!"
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #cbd5e1; font-size: 12px; line-height: 1.4;")
        ctrl_layout.addWidget(desc)

        # Action Buttons
        btn_row = QtWidgets.QHBoxLayout()
        btn_row.setSpacing(10)

        self.btn_start = QtWidgets.QPushButton("▶ START FISHING (F8)")
        self.btn_start.setProperty("class", "btn-primary")
        self.btn_start.setMinimumHeight(44)
        self.btn_start.clicked.connect(self.sig_start_fishing.emit)

        self.btn_pause = QtWidgets.QPushButton("⏸ PAUSE")
        self.btn_pause.setProperty("class", "btn-accent")
        self.btn_pause.setMinimumHeight(44)
        self.btn_pause.clicked.connect(self._toggle_pause)

        self.btn_stop = QtWidgets.QPushButton("⏹ STOP")
        self.btn_stop.setProperty("class", "btn-danger")
        self.btn_stop.setMinimumHeight(44)
        self.btn_stop.clicked.connect(self.sig_stop_fishing.emit)

        self.btn_test_join_seq = QtWidgets.QPushButton("⚡ Test Selling Path")
        self.btn_test_join_seq.setProperty("class", "btn-secondary")
        self.btn_test_join_seq.setMinimumHeight(44)
        self.btn_test_join_seq.setToolTip("Runs Reset -> Collection/Equip -> Selling Path -> Walk to Pond sequence")
        self.btn_test_join_seq.clicked.connect(self.sig_run_join_sequence.emit)

        btn_row.addWidget(self.btn_start)
        btn_row.addWidget(self.btn_pause)
        btn_row.addWidget(self.btn_stop)
        btn_row.addWidget(self.btn_test_join_seq)
        ctrl_layout.addLayout(btn_row)

        main_layout.addWidget(ctrl_group)

        # 2. Live Stats (2x2 or 4-across responsive grid)
        stats_grid = QtWidgets.QGridLayout()
        stats_grid.setHorizontalSpacing(12)
        stats_grid.setVerticalSpacing(12)

        self.card_fish = StatCard("Fish Caught", "0", "#00f0ff", "Successfully reeled fish")
        self.card_cycles = StatCard("Fishing Cycles", "0", "#00ff88", "Casting & reeling rounds")
        self.card_sells = StatCard("Sell Runs Done", "0", "#fbbf24", "Trips to fish merchant")
        self.card_status = StatCard("Macro State", "Idle", "#a855f7", "Current automation status")

        stats_grid.addWidget(self.card_fish, 0, 0)
        stats_grid.addWidget(self.card_cycles, 0, 1)
        stats_grid.addWidget(self.card_sells, 1, 0)
        stats_grid.addWidget(self.card_status, 1, 1)

        stats_grid.setColumnStretch(0, 1)
        stats_grid.setColumnStretch(1, 1)
        main_layout.addLayout(stats_grid)

        # 3. Pathing & Automation Options
        settings_group = QtWidgets.QGroupBox("Fishing, Selling & Biome Camping Settings")
        form_layout = QtWidgets.QFormLayout(settings_group)
        form_layout.setSpacing(14)
        form_layout.setContentsMargins(16, 22, 16, 16)

        self.chk_auto_join_fish = QtWidgets.QCheckBox("Automatically run Selling Path and start fishing when joining a sniped server")
        self.chk_auto_join_fish.setChecked(False)
        self.chk_auto_join_fish.toggled.connect(lambda v: self.sig_setting_changed.emit("fishsol_auto_on_join", v))
        form_layout.addRow("Auto-Start on Snipe:", self.chk_auto_join_fish)

        self.chk_stay_in_biome = QtWidgets.QCheckBox("Stay & camp in target biome indefinitely while fishing (Waits until biome ends before hopping)")
        self.chk_stay_in_biome.setChecked(True)
        self.chk_stay_in_biome.toggled.connect(lambda v: self.sig_setting_changed.emit("fishsol_stay_in_biome", v))
        form_layout.addRow("Biome Camping Mode:", self.chk_stay_in_biome)

        self.combo_camping_biome = QtWidgets.QComboBox()
        self.combo_camping_biome.addItems([
            "ANY SNIPED BIOME (Dynamic)",
            "CORRUPTION",
            "GLITCHED",
            "DREAMSPACE",
            "CYBERSPACE",
            "STARFALL",
            "HELL",
            "SANDSTORM",
            "NULL",
            "HEAVEN",
            "RADIANT FOREST",
            "LOST FOREST"
        ])
        self.combo_camping_biome.currentTextChanged.connect(lambda v: self.sig_setting_changed.emit("fishsol_camping_biome", v))
        form_layout.addRow("Target Camping Biome:", self.combo_camping_biome)

        self.lbl_camping_status = QtWidgets.QLabel("Sniper Status: Idle / Ready")
        self.lbl_camping_status.setStyleSheet("color: #00f0ff; font-weight: bold; font-size: 12px;")
        form_layout.addRow("Camping Lock State:", self.lbl_camping_status)

        self.combo_pathing = QtWidgets.QComboBox()
        self.combo_pathing.addItems(["Vip Pathing", "Non Vip Pathing", "Abyssal Pathing"])
        self.combo_pathing.currentTextChanged.connect(lambda v: self.sig_setting_changed.emit("fishsol_pathing_mode", v))
        form_layout.addRow("Selling Path Mode:", self.combo_pathing)

        self.combo_res = QtWidgets.QComboBox()
        self.combo_res.addItems(["1080p (1920x1080) [Recommended]", "1440p (2560x1440)", "1366x768"])
        self.combo_res.currentTextChanged.connect(lambda v: self.sig_setting_changed.emit("fishsol_resolution", v))
        form_layout.addRow("Screen Resolution:", self.combo_res)

        self.chk_sell_all = QtWidgets.QCheckBox("Click 'Sell All' button during inventory selling")
        self.chk_sell_all.setChecked(True)
        self.chk_sell_all.toggled.connect(lambda v: self.sig_setting_changed.emit("fishsol_sell_all", v))
        form_layout.addRow("Sell All Items:", self.chk_sell_all)

        self.spin_fish_loop = QtWidgets.QSpinBox()
        self.spin_fish_loop.setRange(1, 100)
        self.spin_fish_loop.setValue(15)
        self.spin_fish_loop.setSuffix(" fish catches before walking to seller")
        self.spin_fish_loop.valueChanged.connect(lambda v: self.sig_setting_changed.emit("fishsol_loop_count", v))
        form_layout.addRow("Sell Frequency:", self.spin_fish_loop)

        # External AHK Button
        ahk_row = QtWidgets.QHBoxLayout()
        btn_ahk = QtWidgets.QPushButton("Launch External D:\\FishSol-v2.1\\FishSol-v2.1.ahk")
        btn_ahk.setProperty("class", "btn-secondary")
        btn_ahk.clicked.connect(self.sig_launch_external_ahk.emit)
        ahk_row.addWidget(btn_ahk)
        ahk_row.addStretch()
        form_layout.addRow("Original Script:", ahk_row)

        main_layout.addWidget(settings_group)

        scroll.setWidget(content)
        outer_layout.addWidget(scroll)

    def _toggle_pause(self):
        txt = self.btn_pause.text()
        if "PAUSE" in txt:
            self.btn_pause.setText("▶ RESUME")
            self.sig_pause_fishing.emit()
        else:
            self.btn_pause.setText("⏸ PAUSE")
            self.sig_resume_fishing.emit()

    def update_stats(self, stats: dict):
        self.card_fish.set_value(str(stats.get("fish_caught", 0)))
        self.card_cycles.set_value(str(stats.get("cycles_completed", 0)))
        self.card_sells.set_value(str(stats.get("total_sells", 0)))

        is_running = stats.get("is_running", False)
        is_paused = stats.get("is_paused", False)
        if is_running:
            status_txt = "Paused" if is_paused else "Fishing Active"
        else:
            status_txt = "Idle"
        self.card_status.set_value(status_txt)

    def load_settings(self, storage):
        """Restores all fishing and camping settings from storage."""
        if not storage:
            return

        # Checkboxes
        auto_join = storage.get_setting("fishsol_auto_on_join", False)
        self.chk_auto_join_fish.blockSignals(True)
        self.chk_auto_join_fish.setChecked(bool(auto_join))
        self.chk_auto_join_fish.blockSignals(False)

        stay_biome = storage.get_setting("fishsol_stay_in_biome", True)
        self.chk_stay_in_biome.blockSignals(True)
        self.chk_stay_in_biome.setChecked(bool(stay_biome))
        self.chk_stay_in_biome.blockSignals(False)

        sell_all = storage.get_setting("fishsol_sell_all", True)
        self.chk_sell_all.blockSignals(True)
        self.chk_sell_all.setChecked(bool(sell_all))
        self.chk_sell_all.blockSignals(False)

        # Camping Biome combo
        camping_biome = storage.get_setting("fishsol_camping_biome", "ANY SNIPED BIOME (Dynamic)")
        idx = self.combo_camping_biome.findText(str(camping_biome))
        if idx >= 0:
            self.combo_camping_biome.blockSignals(True)
            self.combo_camping_biome.setCurrentIndex(idx)
            self.combo_camping_biome.blockSignals(False)

        # Pathing mode combo
        pathing = storage.get_setting("fishsol_pathing_mode", "Vip Pathing")
        idx_p = self.combo_pathing.findText(str(pathing))
        if idx_p >= 0:
            self.combo_pathing.blockSignals(True)
            self.combo_pathing.setCurrentIndex(idx_p)
            self.combo_pathing.blockSignals(False)

        # Resolution combo
        res = storage.get_setting("fishsol_resolution", "1080p (1920x1080) [Recommended]")
        idx_r = self.combo_res.findText(str(res))
        if idx_r >= 0:
            self.combo_res.blockSignals(True)
            self.combo_res.setCurrentIndex(idx_r)
            self.combo_res.blockSignals(False)

        # Loop count spinbox
        loop_cnt = storage.get_setting("fishsol_loop_count", 15)
        self.spin_fish_loop.blockSignals(True)
        self.spin_fish_loop.setValue(int(loop_cnt))
        self.spin_fish_loop.blockSignals(False)

    def set_macro_status(self, text: str):
        self.card_status.set_value(text[:20])

    def set_camping_lock_state(self, is_locked: bool, biome: str):
        if is_locked:
            self.lbl_camping_status.setText(f"🔒 LOCKED in {biome} - Fishing Active (Sniper Paused)")
            self.lbl_camping_status.setStyleSheet("color: #00ff88; font-weight: bold; font-size: 12px;")
        else:
            self.lbl_camping_status.setText(f"🎯 HUNTING for {biome} servers (Sniper Active)")
            self.lbl_camping_status.setStyleSheet("color: #00f0ff; font-weight: bold; font-size: 12px;")
