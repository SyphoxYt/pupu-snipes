"""
PupuSnipe Dashboard Tab
High-level overview, status badges, Bloxstrap live biome & aura, metrics, and real-time activity feed.
Responsive grid scaling, cyberpunk glow styling, and non-clipping scrollable container.
"""
import time
from PySide6 import QtCore, QtGui, QtWidgets


class StatCard(QtWidgets.QFrame):
    """Sleek elevated card with icon, title, vibrant value, and explanatory subtext."""
    def __init__(self, title: str, initial_value: str = "0", accent_color: str = "#00f0ff", subtext: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("statCard")
        self.setProperty("class", "stat-card")
        self.setMinimumHeight(86)
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(3)

        # Header row: Title + Accent dot
        header_row = QtWidgets.QHBoxLayout()
        header_row.setSpacing(6)
        
        self.dot = QtWidgets.QLabel("●")
        self.dot.setStyleSheet(f"color: {accent_color}; font-size: 11px;")
        
        self.title_label = QtWidgets.QLabel(title)
        self.title_label.setProperty("class", "card-title")
        self.title_label.setStyleSheet("color: #94a3b8; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px;")

        header_row.addWidget(self.dot)
        header_row.addWidget(self.title_label)
        header_row.addStretch()
        layout.addLayout(header_row)

        # Value
        self.value_label = QtWidgets.QLabel(initial_value)
        self.value_label.setProperty("class", "card-value")
        self.value_label.setStyleSheet(f"color: {accent_color}; font-size: 24px; font-weight: 800;")
        layout.addWidget(self.value_label)

        self.accent_color = accent_color

        # Subtext / Helper description
        if subtext:
            self.sub_label = QtWidgets.QLabel(subtext)
            self.sub_label.setProperty("class", "card-subtext")
            self.sub_label.setStyleSheet("color: #64748b; font-size: 10px; font-weight: 500;")
            layout.addWidget(self.sub_label)

    def set_value(self, value: str):
        old_val = self.value_label.text()
        self.value_label.setText(str(value))
        if old_val != str(value) and str(value) not in ["0", "0.0 ms"]:
            self.setStyleSheet(f"#statCard {{ border: 1px solid {self.accent_color}; background-color: #172038; border-radius: 11px; }}")
            QtCore.QTimer.singleShot(350, lambda: self.setStyleSheet(""))


class DashboardTab(QtWidgets.QWidget):
    sig_toggle_sniper = QtCore.Signal()
    sig_toggle_fishsol = QtCore.Signal()
    sig_reset_cooldown = QtCore.Signal()
    sig_test_join = QtCore.Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        # Outer scroll area ensures no scaling clipping on any resolution / DPI
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

        # 1. Top Status Bar & Quick Actions
        status_bar = QtWidgets.QHBoxLayout()
        status_bar.setSpacing(8)

        self.badge_discord = self._create_badge("Discord: Disconnected", "#f43f5e")
        self.badge_sniper = self._create_badge("Sniper: Stopped", "#94a3b8")
        self.badge_roblox = self._create_badge("Roblox: Inactive", "#94a3b8")
        self.badge_cooldown = self._create_badge("Cooldown: Ready", "#00ff88")
        self.badge_fishing = self._create_badge("Fishing: Idle", "#94a3b8")
        self.badge_biome = self._create_badge("Biome: Unknown", "#a855f7")

        status_bar.addWidget(self.badge_discord)
        status_bar.addWidget(self.badge_sniper)
        status_bar.addWidget(self.badge_roblox)
        status_bar.addWidget(self.badge_cooldown)
        status_bar.addWidget(self.badge_fishing)
        status_bar.addWidget(self.badge_biome)
        status_bar.addStretch()

        self.btn_reset_cooldown = QtWidgets.QPushButton("🔄 Reset Cooldown")
        self.btn_reset_cooldown.setProperty("class", "btn-secondary")
        self.btn_reset_cooldown.setMinimumHeight(36)
        self.btn_reset_cooldown.clicked.connect(self.sig_reset_cooldown.emit)

        self.btn_quick_sniper = QtWidgets.QPushButton("⚡ Start Sniper (F4)")
        self.btn_quick_sniper.setProperty("class", "btn-primary")
        self.btn_quick_sniper.setMinimumHeight(36)
        self.btn_quick_sniper.clicked.connect(self.sig_toggle_sniper.emit)

        self.btn_quick_fish = QtWidgets.QPushButton("🎣 Toggle Fishing (F8)")
        self.btn_quick_fish.setProperty("class", "btn-secondary")
        self.btn_quick_fish.setMinimumHeight(36)
        self.btn_quick_fish.clicked.connect(self.sig_toggle_fishsol.emit)

        status_bar.addWidget(self.btn_reset_cooldown)
        status_bar.addWidget(self.btn_quick_sniper)
        status_bar.addWidget(self.btn_quick_fish)
        main_layout.addLayout(status_bar)

        # 2. Metric Cards Grid (2 rows x 3 columns - scales cleanly without squeezing)
        cards_grid = QtWidgets.QGridLayout()
        cards_grid.setHorizontalSpacing(12)
        cards_grid.setVerticalSpacing(12)

        self.card_scanned = StatCard("Messages Scanned", "0", "#38bdf8", "Live Discord gateway feed")
        self.card_detected = StatCard("Links Detected", "0", "#a855f7", "Verified VIP server links")
        self.card_joined = StatCard("Successful Joins", "0", "#00ff88", "Dispatched to Roblox client")

        self.card_latency = StatCard("Average Latency", "0.0 ms", "#00f0ff", "Rolling detect-to-launch average")
        self.card_fastest = StatCard("Fastest Snipe Record", "0.0 ms", "#fbbf24", "All-time speed benchmark")
        self.card_fish = StatCard("Fish Caught", "0", "#f97316", "Fishing loop automation count")

        cards_grid.addWidget(self.card_scanned, 0, 0)
        cards_grid.addWidget(self.card_detected, 0, 1)
        cards_grid.addWidget(self.card_joined, 0, 2)

        cards_grid.addWidget(self.card_latency, 1, 0)
        cards_grid.addWidget(self.card_fastest, 1, 1)
        cards_grid.addWidget(self.card_fish, 1, 2)

        cards_grid.setColumnStretch(0, 1)
        cards_grid.setColumnStretch(1, 1)
        cards_grid.setColumnStretch(2, 1)

        main_layout.addLayout(cards_grid)

        # 3. Live Activity Feed Header
        feed_header = QtWidgets.QHBoxLayout()
        feed_header.setSpacing(10)

        title_box = QtWidgets.QVBoxLayout()
        title_box.setSpacing(2)
        feed_title = QtWidgets.QLabel("Live Detection & Protocol Launch Feed")
        feed_title.setStyleSheet("font-size: 15px; font-weight: 800; color: #f1f5f9; letter-spacing: 0.5px;")
        feed_desc = QtWidgets.QLabel("Real-time stream of detected links, microsecond latency breakdowns, and join status.")
        feed_desc.setStyleSheet("font-size: 11px; color: #64748b;")
        title_box.addWidget(feed_title)
        title_box.addWidget(feed_desc)
        feed_header.addLayout(title_box)

        feed_header.addStretch()

        self.btn_clear_feed = QtWidgets.QPushButton("Clear Table")
        self.btn_clear_feed.setProperty("class", "btn-secondary")
        self.btn_clear_feed.clicked.connect(self._clear_table)
        feed_header.addWidget(self.btn_clear_feed)
        main_layout.addLayout(feed_header)

        # 4. Activity Table with Millisecond Timestamps
        self.activity_table = QtWidgets.QTableWidget()
        self.activity_table.setColumnCount(7)
        self.activity_table.setHorizontalHeaderLabels([
            "Recv Time (Exact)", "Server / Channel", "Author", "Target Profile", "Latency Breakdown", "Status", "Code / Link"
        ])
        header = self.activity_table.horizontalHeader()
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(6, QtWidgets.QHeaderView.Stretch)
        self.activity_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.activity_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.activity_table.setMinimumHeight(280)

        main_layout.addWidget(self.activity_table)

        scroll.setWidget(content)
        outer_layout.addWidget(scroll)

    def _create_badge(self, text: str, color: str) -> QtWidgets.QLabel:
        badge = QtWidgets.QLabel(text)
        badge.setStyleSheet(f"""
            background-color: #111628;
            color: {color};
            border: 1px solid {color}55;
            border-radius: 7px;
            padding: 6px 12px;
            font-weight: 700;
            font-size: 11px;
        """)
        return badge

    def update_discord_status(self, state: str, text: str):
        color = "#00ff88" if state == "CONNECTED" else ("#fbbf24" if state == "RECONNECTING" else "#f43f5e")
        self.badge_discord.setText(f"Discord: {text}")
        self.badge_discord.setStyleSheet(f"""
            background-color: #111628;
            color: {color};
            border: 1px solid {color}77;
            border-radius: 7px;
            padding: 6px 12px;
            font-weight: 700;
            font-size: 11px;
        """)

    def update_sniper_status(self, is_running: bool, is_paused: bool):
        if is_running:
            if is_paused:
                txt = "Sniper: Paused"
                color = "#fbbf24"
                btn_txt = "▶ Resume Sniper (F6)"
            else:
                txt = "Sniper: Active"
                color = "#00f0ff"
                btn_txt = "⏹ Stop Sniper (F4)"
        else:
            txt = "Sniper: Stopped"
            color = "#94a3b8"
            btn_txt = "⚡ Start Sniper (F4)"

        self.badge_sniper.setText(txt)
        self.badge_sniper.setStyleSheet(f"""
            background-color: #111628;
            color: {color};
            border: 1px solid {color}77;
            border-radius: 7px;
            padding: 6px 12px;
            font-weight: 700;
            font-size: 11px;
        """)
        self.btn_quick_sniper.setText(btn_txt)

    def update_roblox_status(self, is_running: bool):
        color = "#00ff88" if is_running else "#94a3b8"
        txt = "Roblox: Running" if is_running else "Roblox: Inactive"
        self.badge_roblox.setText(txt)
        self.badge_roblox.setStyleSheet(f"""
            background-color: #111628;
            color: {color};
            border: 1px solid {color}77;
            border-radius: 7px;
            padding: 6px 12px;
            font-weight: 700;
            font-size: 11px;
        """)

    def update_fishsol_status(self, text: str, is_active: bool):
        """Update fishing status in badge and quick button."""
        color = "#00ff88" if is_active else "#94a3b8"
        self.badge_fishing.setText(f"Fishing: {text}")
        self.badge_fishing.setStyleSheet(f"""
            background-color: #111628;
            color: {color};
            border: 1px solid {color}77;
            border-radius: 7px;
            padding: 6px 12px;
            font-weight: 700;
            font-size: 11px;
        """)
        self.btn_quick_fish.setText("🎣 Stop Fishing (F8)" if is_active else "🎣 Toggle Fishing (F8)")

    def update_cooldown_display(self, remaining_sec: float):
        """Update 5-minute post-join cooldown badge and quick button."""
        if remaining_sec > 0:
            mins = int(remaining_sec // 60)
            secs = int(remaining_sec % 60)
            self.badge_cooldown.setText(f"Cooldown: {mins}m {secs:02d}s")
            self.badge_cooldown.setStyleSheet("""
                background-color: #1a1608;
                color: #fbbf24;
                border: 1px solid #fbbf2488;
                border-radius: 7px;
                padding: 6px 12px;
                font-weight: 700;
                font-size: 11px;
            """)
            self.btn_reset_cooldown.setText(f"🔄 Reset Cooldown ({mins}m {secs:02d}s)")
            self.btn_reset_cooldown.setStyleSheet("QPushButton { background-color: #b45309; color: #ffffff; font-weight: 700; border-radius: 6px; padding: 6px 12px; } QPushButton:hover { background-color: #d97706; }")
        else:
            self.badge_cooldown.setText("Cooldown: Ready")
            self.badge_cooldown.setStyleSheet("""
                background-color: #0c1a14;
                color: #00ff88;
                border: 1px solid #00ff8877;
                border-radius: 7px;
                padding: 6px 12px;
                font-weight: 700;
                font-size: 11px;
            """)
            self.btn_reset_cooldown.setText("🔄 Reset Cooldown")
            self.btn_reset_cooldown.setStyleSheet("")

    def update_biome_display(self, biome: str, aura: str = ""):
        txt = f"Biome: {biome}" + (f" ({aura})" if aura else "")
        color = "#00f0ff" if "GLITCH" in biome.upper() or "DREAM" in biome.upper() or "CYBER" in biome.upper() else "#a855f7"
        self.badge_biome.setText(txt)
        self.badge_biome.setStyleSheet(f"""
            background-color: #111628;
            color: {color};
            border: 1px solid {color}77;
            border-radius: 7px;
            padding: 6px 12px;
            font-weight: 700;
            font-size: 11px;
        """)

    def add_activity_row(self, event: dict):
        row = 0
        self.activity_table.insertRow(row)

        t_val = event.get("timestamp", time.time())
        time_str = time.strftime("%H:%M:%S", time.localtime(t_val)) + f".{int((t_val % 1) * 1000):03d}"
        server_info = f"{event.get('server_name', '')} / #{event.get('channel_name', '')}"
        author = event.get("author_name", "")
        profile = f"{event.get('profile_name', '')} ({event.get('keyword', '')})"
        
        breakdown = event.get("breakdown", {})
        total_lat = event.get("latency_ms", 0.0)
        if breakdown:
            lat_str = f"{total_lat:.2f} ms (E:{breakdown.get('extract_ms', 0):.1f} | M:{breakdown.get('match_ms', 0):.1f} | L:{breakdown.get('launch_exec_ms', 0):.1f})"
        else:
            lat_str = f"{total_lat:.2f} ms"

        status = event.get("status", "DETECTED")
        code = event.get("link_code", "")

        status_colors = {
            "JOINED": "#00ff88",
            "DETECTED": "#38bdf8",
            "BLOCKED": "#f43f5e",
            "DUPLICATE": "#94a3b8",
            "ERROR": "#f43f5e"
        }
        color_hex = status_colors.get(status, "#e2e8f0")

        items = [
            QtWidgets.QTableWidgetItem(time_str),
            QtWidgets.QTableWidgetItem(server_info),
            QtWidgets.QTableWidgetItem(author),
            QtWidgets.QTableWidgetItem(profile),
            QtWidgets.QTableWidgetItem(lat_str),
            QtWidgets.QTableWidgetItem(status),
            QtWidgets.QTableWidgetItem(code)
        ]

        items[0].setForeground(QtGui.QColor("#94a3b8"))
        items[4].setForeground(QtGui.QColor("#00f0ff"))
        items[5].setForeground(QtGui.QColor(color_hex))

        for col, it in enumerate(items):
            self.activity_table.setItem(row, col, it)

        if self.activity_table.rowCount() > 300:
            self.activity_table.removeRow(self.activity_table.rowCount() - 1)

    def _clear_table(self):
        self.activity_table.setRowCount(0)
