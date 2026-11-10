"""
PupuSnipe Settings, Bot Authentication & Diagnostics Tab
Secure Windows Credential Manager token backend, color-coded live diagnostics console, and log exports.
Wrapped in a responsive scroll container to prevent scaling/overflow bugs.
"""
import os
import sys
import subprocess
from PySide6 import QtCore, QtGui, QtWidgets
from ...core.storage import StorageManager
from ...core.logger import get_in_memory_logs, clear_in_memory_logs


class SettingsTab(QtWidgets.QWidget):
    sig_token_saved = QtCore.Signal(str)
    sig_test_connection = QtCore.Signal(str)
    sig_clear_history = QtCore.Signal()
    sig_ui_scale_changed = QtCore.Signal(float)

    def __init__(self, storage: StorageManager, parent=None):
        super().__init__(parent)
        self.storage = storage
        self._all_log_lines = []
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
        main_layout.setSpacing(14)

        # 1. Discord Bot Token (Windows Credential Storage)
        token_group = QtWidgets.QGroupBox("Discord Bot Authentication & DPAPI Encryption")
        token_layout = QtWidgets.QVBoxLayout(token_group)
        token_layout.setSpacing(10)
        token_layout.setContentsMargins(16, 22, 16, 16)

        info = QtWidgets.QLabel(
            "PupuSnipe strictly uses authorized Discord Bot authentication. Tokens are securely encrypted "
            "in your local Windows Credential Manager (DPAPI). Ensure 'Message Content Intent' is turned ON in the Discord Developer Portal."
        )
        info.setStyleSheet("color: #94a3b8; font-size: 12px;")
        info.setWordWrap(True)
        token_layout.addWidget(info)

        row = QtWidgets.QHBoxLayout()
        row.setSpacing(8)
        self.edit_token = QtWidgets.QLineEdit()
        self.edit_token.setEchoMode(QtWidgets.QLineEdit.Password)
        self.edit_token.setPlaceholderText("Paste Discord Bot Token here...")
        self.edit_token.setMinimumHeight(38)

        self.btn_toggle_echo = QtWidgets.QPushButton("Show")
        self.btn_toggle_echo.setProperty("class", "btn-secondary")
        self.btn_toggle_echo.setMinimumHeight(38)
        self.btn_toggle_echo.clicked.connect(self._toggle_echo)

        self.btn_save_token = QtWidgets.QPushButton("Save Token")
        self.btn_save_token.setProperty("class", "btn-primary")
        self.btn_save_token.setMinimumHeight(38)
        self.btn_save_token.clicked.connect(self._save_token)

        self.btn_test = QtWidgets.QPushButton("Test Connection")
        self.btn_test.setProperty("class", "btn-secondary")
        self.btn_test.setMinimumHeight(38)
        self.btn_test.clicked.connect(self._test_token)

        row.addWidget(self.edit_token)
        row.addWidget(self.btn_toggle_echo)
        row.addWidget(self.btn_save_token)
        row.addWidget(self.btn_test)
        token_layout.addLayout(row)

        self.lbl_token_status = QtWidgets.QLabel("")
        self.lbl_token_status.setStyleSheet("font-weight: 700; font-size: 12px;")
        token_layout.addWidget(self.lbl_token_status)

        main_layout.addWidget(token_group)

        # 2. Live Diagnostics Log Console with Filters & Search
        log_group = QtWidgets.QGroupBox("Live System Diagnostics & High-Tech Terminal")
        log_layout = QtWidgets.QVBoxLayout(log_group)
        log_layout.setSpacing(10)
        log_layout.setContentsMargins(16, 22, 16, 16)

        log_actions = QtWidgets.QHBoxLayout()
        log_actions.setSpacing(8)

        self.combo_log_filter = QtWidgets.QComboBox()
        self.combo_log_filter.addItems(["All Logs", "Sniper & Joins", "Fishing Macro", "Bloxstrap / Biomes", "Discord", "Warnings & Errors"])
        self.combo_log_filter.setMinimumHeight(34)
        self.combo_log_filter.currentTextChanged.connect(self._refresh_console_view)
        log_actions.addWidget(QtWidgets.QLabel("Category:"))
        log_actions.addWidget(self.combo_log_filter)

        self.edit_log_search = QtWidgets.QLineEdit()
        self.edit_log_search.setPlaceholderText("Search logs...")
        self.edit_log_search.setMinimumHeight(34)
        self.edit_log_search.setMaximumWidth(200)
        self.edit_log_search.textChanged.connect(self._refresh_console_view)
        log_actions.addWidget(self.edit_log_search)

        self.chk_autoscroll = QtWidgets.QCheckBox("Auto-Scroll")
        self.chk_autoscroll.setChecked(True)
        log_actions.addWidget(self.chk_autoscroll)
        log_actions.addStretch()

        btn_export_logs = QtWidgets.QPushButton("Export Logs...")
        btn_export_logs.setProperty("class", "btn-secondary")
        btn_export_logs.setMinimumHeight(34)
        btn_export_logs.clicked.connect(self._export_logs)

        btn_clear_logs = QtWidgets.QPushButton("Clear Console")
        btn_clear_logs.setProperty("class", "btn-secondary")
        btn_clear_logs.setMinimumHeight(34)
        btn_clear_logs.clicked.connect(self._clear_logs)

        btn_open_file = QtWidgets.QPushButton("Open Log Folder")
        btn_open_file.setProperty("class", "btn-secondary")
        btn_open_file.setMinimumHeight(34)
        btn_open_file.clicked.connect(self._open_log_folder)

        log_actions.addWidget(btn_export_logs)
        log_actions.addWidget(btn_clear_logs)
        log_actions.addWidget(btn_open_file)
        log_layout.addLayout(log_actions)

        self.console = QtWidgets.QTextEdit()
        self.console.setReadOnly(True)
        self.console.setMinimumHeight(320)
        self.console.setStyleSheet("""
            background-color: #080a11;
            color: #00ff88;
            font-family: 'Cascadia Code', 'Consolas', 'Courier New', monospace;
            font-size: 12px;
            border: 1px solid #1a2238;
            border-radius: 9px;
            padding: 8px;
        """)
        log_layout.addWidget(self.console)

        main_layout.addWidget(log_group)

        # 3. Storage & Maintenance
        mgmt_group = QtWidgets.QGroupBox("Storage & Maintenance")
        mgmt_layout = QtWidgets.QHBoxLayout(mgmt_group)
        mgmt_layout.setSpacing(12)
        mgmt_layout.setContentsMargins(16, 22, 16, 16)

        btn_clear_hist = QtWidgets.QPushButton("Clear Snipe History")
        btn_clear_hist.setProperty("class", "btn-danger")
        btn_clear_hist.setMinimumHeight(38)
        btn_clear_hist.clicked.connect(self._clear_history)

        mgmt_layout.addWidget(btn_clear_hist)
        mgmt_layout.addStretch()
        main_layout.addWidget(mgmt_group)

        # 4. UI Appearance & Display Scaling
        scale_group = QtWidgets.QGroupBox("UI Appearance & Display Scaling")
        scale_layout = QtWidgets.QHBoxLayout(scale_group)
        scale_layout.setSpacing(12)
        scale_layout.setContentsMargins(16, 22, 16, 16)

        lbl_scale = QtWidgets.QLabel("Interface Display Zoom:")
        lbl_scale.setStyleSheet("color: #cbd5e1; font-weight: 700; font-size: 12px;")
        scale_layout.addWidget(lbl_scale)

        self.combo_ui_scale = QtWidgets.QComboBox()
        self.combo_ui_scale.addItems([
            "90% (Compact)",
            "100% (Default)",
            "110% (Medium)",
            "125% (Large)",
            "150% (Extra Large)"
        ])
        self.combo_ui_scale.setMinimumHeight(36)
        self.combo_ui_scale.currentIndexChanged.connect(self._on_scale_changed)
        scale_layout.addWidget(self.combo_ui_scale, 1)
        scale_layout.addStretch()
        main_layout.addWidget(scale_group)

        scroll.setWidget(content)
        outer_layout.addWidget(scroll)

    def load_settings(self):
        token = self.storage.get_bot_token()
        if token:
            self.edit_token.setText(token)
            self.lbl_token_status.setText("✓ Bot token loaded securely from Windows Credential Manager.")
            self.lbl_token_status.setStyleSheet("color: #00ff88; font-weight: 700;")
        else:
            self.lbl_token_status.setText("No bot token saved yet.")
            self.lbl_token_status.setStyleSheet("color: #94a3b8;")

        # Load UI Scale setting
        try:
            scale_val = float(self.storage.get_setting("ui_scale", 1.0))
        except (ValueError, TypeError):
            scale_val = 1.0
        scale_map = {0.9: 0, 1.0: 1, 1.1: 2, 1.25: 3, 1.5: 4}
        idx = scale_map.get(scale_val, 1)
        self.combo_ui_scale.blockSignals(True)
        self.combo_ui_scale.setCurrentIndex(idx)
        self.combo_ui_scale.blockSignals(False)

        self._all_log_lines = get_in_memory_logs()
        self._refresh_console_view()

    def _on_scale_changed(self, idx: int):
        scale_factors = [0.9, 1.0, 1.1, 1.25, 1.5]
        if 0 <= idx < len(scale_factors):
            factor = scale_factors[idx]
            self.storage.set_setting("ui_scale", factor)
            self.sig_ui_scale_changed.emit(factor)

    def append_log_line(self, line: str):
        self._all_log_lines.append(line)
        if len(self._all_log_lines) > 2000:
            self._all_log_lines.pop(0)

        # Check if line matches current filter
        if self._line_matches_filter(line):
            html = self._format_log_line_html(line)
            self.console.append(html)
            if self.chk_autoscroll.isChecked():
                self.console.verticalScrollBar().setValue(self.console.verticalScrollBar().maximum())

    def _line_matches_filter(self, line: str) -> bool:
        cat = self.combo_log_filter.currentText()
        search_txt = self.edit_log_search.text().strip().lower()

        if search_txt and search_txt not in line.lower():
            return False

        if cat == "Sniper & Joins":
            return any(k in line for k in ["[SNIPER", "JOINED", "LATENCY", "DETECTED"])
        elif cat in ("Fishing Macro", "FishSol Macro"):
            return "[FishSol]" in line or "fish" in line.lower()
        elif cat == "Bloxstrap / Biomes":
            return "[Bloxstrap]" in line or "Biome" in line
        elif cat == "Discord":
            return "[Discord]" in line
        elif cat == "Warnings & Errors":
            return "WARNING" in line or "ERROR" in line or "FAIL" in line or "BLOCKED" in line

        return True

    def _format_log_line_html(self, line: str) -> str:
        escaped = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        if "⚡ [SNIPER" in line or "JOINED" in line:
            return f"<span style='color: #00ff88; font-weight: bold;'>{escaped}</span>"
        elif "TOTAL DETECT-TO-LAUNCH" in line or "Latency" in line:
            return f"<span style='color: #00f0ff; font-weight: bold;'>{escaped}</span>"
        elif "[FishSol]" in line:
            return f"<span style='color: #fbbf24;'>{escaped}</span>"
        elif "[Bloxstrap]" in line:
            return f"<span style='color: #a855f7; font-weight: bold;'>{escaped}</span>"
        elif "ERROR" in line or "BLOCKED" in line:
            return f"<span style='color: #f43f5e; font-weight: bold;'>{escaped}</span>"
        elif "WARNING" in line:
            return f"<span style='color: #f59e0b;'>{escaped}</span>"
        elif "[Discord]" in line:
            return f"<span style='color: #38bdf8;'>{escaped}</span>"
        else:
            return f"<span style='color: #94a3b8;'>{escaped}</span>"

    def _refresh_console_view(self):
        filtered = [self._format_log_line_html(l) for l in self._all_log_lines if self._line_matches_filter(l)]
        self.console.setHtml("<br>".join(filtered))
        if self.chk_autoscroll.isChecked():
            self.console.verticalScrollBar().setValue(self.console.verticalScrollBar().maximum())

    def _toggle_echo(self):
        if self.edit_token.echoMode() == QtWidgets.QLineEdit.Password:
            self.edit_token.setEchoMode(QtWidgets.QLineEdit.Normal)
            self.btn_toggle_echo.setText("Hide")
        else:
            self.edit_token.setEchoMode(QtWidgets.QLineEdit.Password)
            self.btn_toggle_echo.setText("Show")

    def _save_token(self):
        token = self.edit_token.text().strip()
        if not token:
            QtWidgets.QMessageBox.warning(self, "Token Error", "Bot token cannot be empty.")
            return
        self.storage.save_bot_token(token)
        self.lbl_token_status.setText("✓ Token saved to Windows Credential Manager!")
        self.lbl_token_status.setStyleSheet("color: #00ff88; font-weight: 700;")
        self.sig_token_saved.emit(token)

    def _test_token(self):
        token = self.edit_token.text().strip()
        if not token:
            QtWidgets.QMessageBox.warning(self, "Token Error", "Please enter a token first.")
            return
        self.sig_test_connection.emit(token)

    def _export_logs(self):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Export PupuSnipe Logs", "pupusnipe_diagnostics.log", "Log Files (*.log *.txt)")
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write("\n".join(self._all_log_lines))
            QtWidgets.QMessageBox.information(self, "Logs Exported", f"Exported {len(self._all_log_lines)} log entries successfully!")

    def _clear_logs(self):
        clear_in_memory_logs()
        self._all_log_lines = []
        self.console.clear()

    def _open_log_folder(self):
        appdata = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
        log_dir = os.path.join(appdata, "PupuSnipe", "logs")
        if os.path.exists(log_dir):
            subprocess.Popen(["explorer", log_dir])

    def _clear_history(self):
        reply = QtWidgets.QMessageBox.question(
            self,
            "Confirm Clear History",
            "Are you sure you want to delete all sniped server history?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )
        if reply == QtWidgets.QMessageBox.Yes:
            self.storage.clear_history()
            self.sig_clear_history.emit()
            QtWidgets.QMessageBox.information(self, "Cleared", "Snipe history has been cleared.")
