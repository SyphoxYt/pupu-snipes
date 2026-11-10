"""
PupuSnipe Discord Servers & Channels Configuration Tab
Manages multi-server and multi-channel monitoring configurations.
Includes visual guide for finding Discord Channel IDs and responsive scroll layout.
"""
from PySide6 import QtCore, QtGui, QtWidgets
from ...core.storage import StorageManager


class AddChannelDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Monitored Discord Channel")
        self.setMinimumSize(460, 290)
        self._init_ui()

    def _init_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        guide = QtWidgets.QLabel(
            "<b>Need help finding IDs?</b> Enable 'Developer Mode' in Discord Settings &rarr; Advanced, "
            "then right-click any server or channel &rarr; 'Copy ID'."
        )
        guide.setStyleSheet("color: #94a3b8; font-size: 11px;")
        guide.setWordWrap(True)
        layout.addWidget(guide)

        form = QtWidgets.QFormLayout()
        form.setSpacing(10)

        self.edit_server_name = QtWidgets.QLineEdit()
        self.edit_server_name.setPlaceholderText("e.g. Sol's RNG Official")
        form.addRow("Server Name:", self.edit_server_name)

        self.edit_server_id = QtWidgets.QLineEdit()
        self.edit_server_id.setPlaceholderText("e.g. 119561000000000000 (Optional)")
        form.addRow("Server ID:", self.edit_server_id)

        self.edit_channel_name = QtWidgets.QLineEdit()
        self.edit_channel_name.setPlaceholderText("e.g. private-servers / ps-links")
        form.addRow("Channel Name:", self.edit_channel_name)

        self.edit_channel_id = QtWidgets.QLineEdit()
        self.edit_channel_id.setPlaceholderText("e.g. 120561000000000000 (Required)")
        form.addRow("Channel ID*:", self.edit_channel_id)

        layout.addLayout(form)

        btn_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        btn_box.accepted.connect(self._validate_and_accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def _validate_and_accept(self):
        if not self.edit_channel_id.text().strip():
            QtWidgets.QMessageBox.warning(self, "Validation Error", "Channel ID is required!")
            return
        self.accept()

    def get_data(self):
        return {
            "server_name": self.edit_server_name.text().strip() or "Server",
            "server_id": self.edit_server_id.text().strip() or "0",
            "channel_name": self.edit_channel_name.text().strip() or "vip-channel",
            "channel_id": self.edit_channel_id.text().strip()
        }


class ServersTab(QtWidgets.QWidget):
    sig_channels_updated = QtCore.Signal(list)

    def __init__(self, storage: StorageManager, parent=None):
        super().__init__(parent)
        self.storage = storage
        self._init_ui()
        self.load_channels()

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

        header_layout = QtWidgets.QHBoxLayout()
        title_box = QtWidgets.QVBoxLayout()
        title_box.setSpacing(2)
        title = QtWidgets.QLabel("Discord Monitored Channels")
        title.setStyleSheet("font-size: 16px; font-weight: 800; color: #f1f5f9;")
        desc = QtWidgets.QLabel("Add specific Discord channels to scan for Sol's RNG private server links in real-time.")
        desc.setStyleSheet("color: #94a3b8; font-size: 12px;")
        title_box.addWidget(title)
        title_box.addWidget(desc)
        header_layout.addLayout(title_box)

        header_layout.addStretch()

        self.btn_add = QtWidgets.QPushButton("+ Add Channel")
        self.btn_add.setProperty("class", "btn-primary")
        self.btn_add.setMinimumHeight(38)
        self.btn_add.clicked.connect(self._show_add_dialog)

        self.btn_refresh = QtWidgets.QPushButton("🔄 Refresh Server Info")
        self.btn_refresh.setProperty("class", "btn-secondary")
        self.btn_refresh.setMinimumHeight(38)
        self.btn_refresh.setToolTip("Reloads and updates live server names and channel titles")
        self.btn_refresh.clicked.connect(self.load_channels)

        self.btn_remove = QtWidgets.QPushButton("Remove Selected")
        self.btn_remove.setProperty("class", "btn-danger")
        self.btn_remove.setMinimumHeight(38)
        self.btn_remove.clicked.connect(self._remove_selected)

        self.btn_refresh.clicked.connect(lambda: self.load_channels(notify=False))

        header_layout.addWidget(self.btn_add)
        header_layout.addWidget(self.btn_refresh)
        header_layout.addWidget(self.btn_remove)
        main_layout.addLayout(header_layout)

        # Instructions Banner
        banner = QtWidgets.QFrame()
        banner.setStyleSheet("""
            background-color: #111628;
            border: 1px solid #1e2942;
            border-left: 3px solid #00f0ff;
            border-radius: 8px;
            padding: 10px 14px;
        """)
        b_layout = QtWidgets.QVBoxLayout(banner)
        b_layout.setSpacing(4)
        b_layout.setContentsMargins(4, 4, 4, 4)

        b_title = QtWidgets.QLabel("💡 How to find Discord Channel IDs:")
        b_title.setStyleSheet("color: #00f0ff; font-weight: 700; font-size: 12px;")
        b_text = QtWidgets.QLabel(
            "1. In Discord, go to <b>User Settings &rarr; Advanced &rarr; Turn ON 'Developer Mode'</b>.<br>"
            "2. Right-click the server or channel where VIP links are shared &rarr; click <b>'Copy Channel ID'</b>.<br>"
            "3. Click <b>+ Add Channel</b> above and paste the ID. <span style='color: #94a3b8;'>(If no channels are added, your bot listens to all channels it can see).</span>"
        )
        b_text.setStyleSheet("color: #cbd5e1; font-size: 11px; line-height: 1.4;")
        b_layout.addWidget(b_title)
        b_layout.addWidget(b_text)
        main_layout.addWidget(banner)

        # Table
        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Enabled", "Server Name", "Server ID", "Channel Name", "Channel ID"])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
        header.setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QtWidgets.QHeaderView.Stretch)
        header.setSectionResizeMode(4, QtWidgets.QHeaderView.ResizeToContents)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setMinimumHeight(320)
        main_layout.addWidget(self.table)

        scroll.setWidget(content)
        outer_layout.addWidget(scroll)

    def update_channel_info(self, channel_id: str, server_id: str, server_name: str, channel_name: str):
        """
        Updates the table row for a single channel in-place with zero UI overhead,
        no table rebuilding, and no recursive signals.
        """
        cid_str = str(channel_id).strip()
        found = False
        for row in range(self.table.rowCount()):
            cid_item = self.table.item(row, 4)
            if cid_item and cid_item.text().strip() == cid_str:
                found = True
                # Server Name
                is_resolved = bool(server_name and server_name not in ("0", "Sniper Channel", "Discord Server", "Direct"))
                display_sname = server_name if is_resolved else "Resolving Server..."
                item_sname = self.table.item(row, 1)
                if not item_sname:
                    item_sname = QtWidgets.QTableWidgetItem()
                    self.table.setItem(row, 1, item_sname)
                item_sname.setText(display_sname)
                item_sname.setForeground(QtGui.QBrush(QtGui.QColor("#00ff88" if is_resolved else "#fbbf24")))
                font_s = item_sname.font()
                font_s.setBold(True)
                item_sname.setFont(font_s)

                # Server ID
                display_sid = server_id if (server_id and server_id != "0") else "—"
                item_sid = self.table.item(row, 2)
                if not item_sid:
                    item_sid = QtWidgets.QTableWidgetItem()
                    self.table.setItem(row, 2, item_sid)
                item_sid.setText(display_sid)
                item_sid.setForeground(QtGui.QBrush(QtGui.QColor("#94a3b8")))

                # Channel Name
                c_name = channel_name
                if not c_name or c_name.startswith("channel-"):
                    display_cname = f"#{c_name}" if not c_name.startswith("#") else c_name
                elif not c_name.startswith("#"):
                    display_cname = f"#{c_name}"
                else:
                    display_cname = c_name
                item_cname = self.table.item(row, 3)
                if not item_cname:
                    item_cname = QtWidgets.QTableWidgetItem()
                    self.table.setItem(row, 3, item_cname)
                item_cname.setText(display_cname)
                item_cname.setForeground(QtGui.QBrush(QtGui.QColor("#00f0ff")))
                font_c = item_cname.font()
                font_c.setBold(True)
                item_cname.setFont(font_c)
                break

        if not found:
            self.load_channels(notify=False)

    def load_channels(self, notify: bool = False):
        channels = self.storage.get_channels()

        self.table.setRowCount(0)
        for ch in channels:
            row = self.table.rowCount()
            self.table.insertRow(row)

            chk_widget = QtWidgets.QWidget()
            chk_layout = QtWidgets.QHBoxLayout(chk_widget)
            chk_layout.setContentsMargins(0, 0, 0, 0)
            chk_layout.setAlignment(QtCore.Qt.AlignCenter)
            chk = QtWidgets.QCheckBox()
            chk.setChecked(bool(ch["enabled"]))
            cid = ch["channel_id"]
            chk.toggled.connect(lambda state, c=cid: self._toggle_channel(c, state))
            chk_layout.addWidget(chk)

            # Server Name formatting
            s_name = ch.get("server_name", "")
            is_resolved = bool(s_name and s_name not in ("0", "Sniper Channel", "Discord Server", "Direct"))
            display_sname = s_name if is_resolved else "Resolving Server..."
            item_sname = QtWidgets.QTableWidgetItem(display_sname)
            item_sname.setForeground(QtGui.QBrush(QtGui.QColor("#00ff88" if is_resolved else "#fbbf24")))
            font_s = item_sname.font()
            font_s.setBold(True)
            item_sname.setFont(font_s)

            # Server ID formatting
            s_id = ch.get("server_id", "")
            display_sid = s_id if (s_id and s_id != "0") else "—"
            item_sid = QtWidgets.QTableWidgetItem(display_sid)
            item_sid.setForeground(QtGui.QBrush(QtGui.QColor("#94a3b8")))

            # Channel Name formatting
            c_name = ch.get("channel_name", "")
            if not c_name or c_name.startswith("channel-"):
                display_cname = f"#{c_name}" if not c_name.startswith("#") else c_name
            elif not c_name.startswith("#"):
                display_cname = f"#{c_name}"
            else:
                display_cname = c_name
            item_cname = QtWidgets.QTableWidgetItem(display_cname)
            item_cname.setForeground(QtGui.QBrush(QtGui.QColor("#00f0ff")))
            font_c = item_cname.font()
            font_c.setBold(True)
            item_cname.setFont(font_c)

            # Channel ID formatting
            item_cid = QtWidgets.QTableWidgetItem(cid)
            item_cid.setForeground(QtGui.QBrush(QtGui.QColor("#cbd5e1")))

            self.table.setCellWidget(row, 0, chk_widget)
            self.table.setItem(row, 1, item_sname)
            self.table.setItem(row, 2, item_sid)
            self.table.setItem(row, 3, item_cname)
            self.table.setItem(row, 4, item_cid)

        if notify:
            enabled_ids = [ch["channel_id"] for ch in channels if ch["enabled"]]
            self.sig_channels_updated.emit(enabled_ids)

    def _toggle_channel(self, channel_id: str, enabled: bool):
        self.storage.toggle_channel(channel_id, enabled)
        channels = self.storage.get_channels()
        enabled_ids = [ch["channel_id"] for ch in channels if ch["enabled"]]
        self.sig_channels_updated.emit(enabled_ids)

    def _show_add_dialog(self):
        dlg = AddChannelDialog(self)
        if dlg.exec():
            data = dlg.get_data()
            self.storage.add_channel(
                server_id=data["server_id"],
                server_name=data["server_name"],
                channel_id=data["channel_id"],
                channel_name=data["channel_name"],
                enabled=True
            )
            self.load_channels(notify=True)

    def _remove_selected(self):
        row = self.table.currentRow()
        if row >= 0:
            cid_item = self.table.item(row, 4)
            if cid_item:
                cid = cid_item.text().strip()
                self.storage.delete_channel(cid)
                self.load_channels(notify=True)
