"""
PupuSnipe Keyword & Detection Profiles Tab
Categorized keyword profiles (Biomes, Merchants, Items, Custom) with priority and regex rules.
Wrapped in a responsive scroll container to prevent scaling/overflow bugs.
"""
import json
from PySide6 import QtCore, QtGui, QtWidgets
from ...core.matcher import KeywordProfile
from ...core.storage import StorageManager


class ProfileEditDialog(QtWidgets.QDialog):
    def __init__(self, profile: KeywordProfile = None, parent=None):
        super().__init__(parent)
        self.profile = profile
        self.setWindowTitle("Edit Keyword Profile" if profile else "Add Keyword Profile")
        self.setMinimumSize(500, 480)
        self._init_ui()

    def _init_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        form = QtWidgets.QFormLayout()
        form.setSpacing(12)

        self.edit_name = QtWidgets.QLineEdit()
        self.edit_name.setPlaceholderText("e.g. Glitched / Jester / Void Coin")
        if self.profile:
            self.edit_name.setText(self.profile.name)
        form.addRow("Profile Name*:", self.edit_name)

        self.combo_cat = QtWidgets.QComboBox()
        self.combo_cat.setEditable(True)
        self.combo_cat.addItems(["Biomes", "Merchants", "Items", "Custom"])
        if self.profile:
            self.combo_cat.setCurrentText(self.profile.category)
        form.addRow("Category:", self.combo_cat)

        self.edit_keywords = QtWidgets.QPlainTextEdit()
        self.edit_keywords.setPlaceholderText("Enter keywords separated by comma (or RegEx patterns if RegEx enabled)\ne.g. glitched, glitch biome")
        self.edit_keywords.setMinimumHeight(70)
        self.edit_keywords.setMaximumHeight(100)
        if self.profile:
            self.edit_keywords.setPlainText(", ".join(self.profile.keywords))
        form.addRow("Keywords*:", self.edit_keywords)

        self.chk_regex = QtWidgets.QCheckBox("Enable Regular Expressions (RegEx)")
        if self.profile:
            self.chk_regex.setChecked(self.profile.is_regex)
        form.addRow("RegEx Matching:", self.chk_regex)

        self.spin_priority = QtWidgets.QSpinBox()
        self.spin_priority.setRange(1, 100)
        self.spin_priority.setValue(self.profile.priority if self.profile else 5)
        form.addRow("Priority (Higher = 1st):", self.spin_priority)

        self.spin_pause = QtWidgets.QSpinBox()
        self.spin_pause.setRange(0, 3600)
        self.spin_pause.setValue(self.profile.pause_duration if self.profile else 0)
        self.spin_pause.setSuffix(" sec cooldown")
        form.addRow("Post-Match Pause:", self.spin_pause)

        self.edit_exclude = QtWidgets.QLineEdit()
        self.edit_exclude.setPlaceholderText("e.g. fake, expired, scam (comma separated)")
        if self.profile and self.profile.exclude_keywords:
            self.edit_exclude.setText(", ".join(self.profile.exclude_keywords))
        form.addRow("Exclude Keywords:", self.edit_exclude)

        layout.addLayout(form)

        btn_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        btn_box.accepted.connect(self._validate)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def _validate(self):
        if not self.edit_name.text().strip():
            QtWidgets.QMessageBox.warning(self, "Validation Error", "Profile name is required.")
            return
        if not self.edit_keywords.toPlainText().strip():
            QtWidgets.QMessageBox.warning(self, "Validation Error", "At least one keyword is required.")
            return
        self.accept()

    def get_profile(self) -> KeywordProfile:
        name = self.edit_name.text().strip()
        prof_id = self.profile.id if self.profile else name.lower().replace(" ", "_")
        kws = [k.strip() for k in self.edit_keywords.toPlainText().split(",") if k.strip()]
        ex_kws = [k.strip() for k in self.edit_exclude.text().split(",") if k.strip()]

        return KeywordProfile(
            id=prof_id,
            name=name,
            category=self.combo_cat.currentText().strip() or "Custom",
            keywords=kws,
            is_regex=self.chk_regex.isChecked(),
            priority=self.spin_priority.value(),
            enabled=self.profile.enabled if self.profile else True,
            pause_duration=self.spin_pause.value(),
            exclude_keywords=ex_kws
        )


class KeywordsTab(QtWidgets.QWidget):
    sig_profiles_updated = QtCore.Signal(list)

    def __init__(self, storage: StorageManager, parent=None):
        super().__init__(parent)
        self.storage = storage
        self._profiles = []
        self._init_ui()
        self.load_profiles()

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

        # Header
        header = QtWidgets.QHBoxLayout()
        title_box = QtWidgets.QVBoxLayout()
        title_box.setSpacing(2)
        title = QtWidgets.QLabel("Keyword Profiles & Target Priorities")
        title.setStyleSheet("font-size: 16px; font-weight: 800; color: #f1f5f9;")
        desc = QtWidgets.QLabel("Customize keywords for Biomes, Merchants, Items, and configure join priorities.")
        desc.setStyleSheet("color: #94a3b8; font-size: 12px;")
        title_box.addWidget(title)
        title_box.addWidget(desc)
        header.addLayout(title_box)

        header.addStretch()

        self.combo_filter = QtWidgets.QComboBox()
        self.combo_filter.addItems(["All Categories", "Biomes", "Merchants", "Items", "Custom"])
        self.combo_filter.setMinimumHeight(38)
        self.combo_filter.currentTextChanged.connect(self._apply_filter)
        header.addWidget(self.combo_filter)

        self.btn_add = QtWidgets.QPushButton("+ Add Profile")
        self.btn_add.setProperty("class", "btn-primary")
        self.btn_add.setMinimumHeight(38)
        self.btn_add.clicked.connect(self._add_profile)

        self.btn_edit = QtWidgets.QPushButton("Edit")
        self.btn_edit.setProperty("class", "btn-secondary")
        self.btn_edit.setMinimumHeight(38)
        self.btn_edit.clicked.connect(self._edit_profile)

        self.btn_delete = QtWidgets.QPushButton("Delete")
        self.btn_delete.setProperty("class", "btn-danger")
        self.btn_delete.setMinimumHeight(38)
        self.btn_delete.clicked.connect(self._delete_profile)

        self.btn_export = QtWidgets.QPushButton("Export JSON")
        self.btn_export.setProperty("class", "btn-secondary")
        self.btn_export.setMinimumHeight(38)
        self.btn_export.clicked.connect(self._export_json)

        self.btn_import = QtWidgets.QPushButton("Import JSON")
        self.btn_import.setProperty("class", "btn-secondary")
        self.btn_import.setMinimumHeight(38)
        self.btn_import.clicked.connect(self._import_json)

        header.addWidget(self.btn_add)
        header.addWidget(self.btn_edit)
        header.addWidget(self.btn_delete)
        header.addWidget(self.btn_export)
        header.addWidget(self.btn_import)
        main_layout.addLayout(header)

        # Explanation Banner
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

        b_title = QtWidgets.QLabel("💡 How Keyword Priority Works:")
        b_title.setStyleSheet("color: #00f0ff; font-weight: 700; font-size: 12px;")
        b_text = QtWidgets.QLabel(
            "• <b>Priority (1-100):</b> If multiple links are found at the same time, PupuSnipe launches the link with the highest priority first (e.g. <b>Glitched</b> at Priority 100 beats <b>Mari</b> at Priority 80).<br>"
            "• <b>Excludes:</b> Messages containing any exclude keywords (like 'fake', 'scam', 'expired') are automatically dropped by anti-bait protection.<br>"
            "• <b>RegEx:</b> Enable RegEx for advanced patterns and word boundary matching."
        )
        b_text.setStyleSheet("color: #cbd5e1; font-size: 11px; line-height: 1.4;")
        b_layout.addWidget(b_title)
        b_layout.addWidget(b_text)
        main_layout.addWidget(banner)

        # Table
        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Enabled", "Category", "Profile Name", "Keywords", "Priority", "RegEx", "Excludes"
        ])
        header_view = self.table.horizontalHeader()
        header_view.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
        header_view.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeToContents)
        header_view.setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeToContents)
        header_view.setSectionResizeMode(3, QtWidgets.QHeaderView.Stretch)
        header_view.setSectionResizeMode(4, QtWidgets.QHeaderView.ResizeToContents)
        header_view.setSectionResizeMode(5, QtWidgets.QHeaderView.ResizeToContents)
        header_view.setSectionResizeMode(6, QtWidgets.QHeaderView.ResizeToContents)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setMinimumHeight(320)
        main_layout.addWidget(self.table)

        scroll.setWidget(content)
        outer_layout.addWidget(scroll)

    def load_profiles(self):
        self._profiles = self.storage.get_profiles()
        self._apply_filter(self.combo_filter.currentText())
        self.sig_profiles_updated.emit(self._profiles)

    def _apply_filter(self, filter_cat: str):
        self.table.setRowCount(0)
        for p in self._profiles:
            if filter_cat != "All Categories" and p.category != filter_cat:
                continue

            row = self.table.rowCount()
            self.table.insertRow(row)

            chk_widget = QtWidgets.QWidget()
            chk_layout = QtWidgets.QHBoxLayout(chk_widget)
            chk_layout.setContentsMargins(0, 0, 0, 0)
            chk_layout.setAlignment(QtCore.Qt.AlignCenter)
            chk = QtWidgets.QCheckBox()
            chk.setChecked(p.enabled)
            prof_id = p.id
            chk.toggled.connect(lambda state, pid=prof_id: self._toggle_profile(pid, state))
            chk_layout.addWidget(chk)

            self.table.setCellWidget(row, 0, chk_widget)
            self.table.setItem(row, 1, QtWidgets.QTableWidgetItem(p.category))
            self.table.setItem(row, 2, QtWidgets.QTableWidgetItem(p.name))
            self.table.setItem(row, 3, QtWidgets.QTableWidgetItem(", ".join(p.keywords)))
            self.table.setItem(row, 4, QtWidgets.QTableWidgetItem(str(p.priority)))
            self.table.setItem(row, 5, QtWidgets.QTableWidgetItem("YES" if p.is_regex else "NO"))
            self.table.setItem(row, 6, QtWidgets.QTableWidgetItem(", ".join(p.exclude_keywords)))

            # Store profile object reference in item
            self.table.item(row, 2).setData(QtCore.Qt.UserRole, p)

    def _toggle_profile(self, profile_id: str, state: bool):
        for p in self._profiles:
            if p.id == profile_id:
                p.enabled = state
                self.storage.save_profile(p)
                break
        self.sig_profiles_updated.emit(self._profiles)

    def _add_profile(self):
        dlg = ProfileEditDialog(parent=self)
        if dlg.exec():
            prof = dlg.get_profile()
            self.storage.save_profile(prof)
            self.load_profiles()

    def _edit_profile(self):
        row = self.table.currentRow()
        if row < 0:
            return
        p_item = self.table.item(row, 2)
        if not p_item:
            return
        prof: KeywordProfile = p_item.data(QtCore.Qt.UserRole)
        dlg = ProfileEditDialog(profile=prof, parent=self)
        if dlg.exec():
            updated = dlg.get_profile()
            self.storage.save_profile(updated)
            self.load_profiles()

    def _delete_profile(self):
        row = self.table.currentRow()
        if row < 0:
            return
        p_item = self.table.item(row, 2)
        if p_item:
            prof: KeywordProfile = p_item.data(QtCore.Qt.UserRole)
            self.storage.delete_profile(prof.id)
            self.load_profiles()

    def _export_json(self):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Export Profiles JSON", "pupusnipe_profiles.json", "JSON Files (*.json)")
        if path:
            data = [p.to_dict() for p in self._profiles]
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            QtWidgets.QMessageBox.information(self, "Export", "Profiles exported successfully!")

    def _import_json(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Import Profiles JSON", "", "JSON Files (*.json)")
        if path:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for item in data:
                    prof = KeywordProfile.from_dict(item)
                    self.storage.save_profile(prof)
                self.load_profiles()
                QtWidgets.QMessageBox.information(self, "Import", "Profiles imported successfully!")
            except Exception as ex:
                QtWidgets.QMessageBox.critical(self, "Error", f"Failed to import: {str(ex)}")
