"""
Custom High-Tech Cyberpunk Widgets for PupuSnipe
Features Gradient/Glow frames, Category rows with pause inputs, and animated badges.
Inspired by Sol Sniper V3 and modern AAA gaming interfaces.
"""
from PySide6 import QtCore, QtGui, QtWidgets


class GlowCard(QtWidgets.QFrame):
    """
    Sleek, rounded frame with a dark futuristic linear gradient,
    subtle glowing border, and anti-aliased geometry.
    """
    def __init__(self, title: str = "", subtitle: str = "", accent_color: str = "#00f0ff", parent=None):
        super().__init__(parent)
        self.accent_color = QtGui.QColor(accent_color)
        self.setObjectName("glowCard")
        self.setProperty("class", "glow-card")
        self.setFrameShape(QtWidgets.QFrame.StyledPanel)

        self._card_layout = QtWidgets.QVBoxLayout(self)
        self._card_layout.setContentsMargins(18, 16, 18, 18)
        self._card_layout.setSpacing(12)

        if title:
            header_layout = QtWidgets.QVBoxLayout()
            header_layout.setSpacing(2)

            title_row = QtWidgets.QHBoxLayout()
            title_row.setSpacing(8)

            dot = QtWidgets.QLabel("✦")
            dot.setStyleSheet(f"color: {accent_color}; font-size: 14px; font-weight: 800;")
            title_row.addWidget(dot)

            lbl_title = QtWidgets.QLabel(title)
            lbl_title.setStyleSheet(f"font-size: 16px; font-weight: 800; color: #f1f5f9; letter-spacing: 0.5px;")
            title_row.addWidget(lbl_title)
            title_row.addStretch()

            header_layout.addLayout(title_row)

            if subtitle:
                lbl_sub = QtWidgets.QLabel(subtitle)
                lbl_sub.setWordWrap(True)
                lbl_sub.setStyleSheet("font-size: 11px; color: #94a3b8; margin-left: 20px;")
                header_layout.addWidget(lbl_sub)

            self._card_layout.addLayout(header_layout)

    def add_widget(self, widget: QtWidgets.QWidget):
        self._card_layout.addWidget(widget)

    def add_layout(self, layout: QtWidgets.QLayout):
        self._card_layout.addLayout(layout)


class CategoryRow(QtWidgets.QWidget):
    """
    Base Category row widget with an enabled CheckBox, Category label,
    and a custom Pause Duration input in seconds. Matches Sol Sniper V3.
    """
    sig_changed = QtCore.Signal(str, bool, int)

    def __init__(self, cat_id: str, label_text: str, default_checked: bool = True, default_pause_sec: int = 180, icon: str = "🎯", parent=None):
        super().__init__(parent)
        self.cat_id = cat_id
        self.setObjectName("categoryRow")

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(10)

        # Checkbox & Label
        self.chk = QtWidgets.QCheckBox()
        self.chk.setChecked(default_checked)
        self.chk.toggled.connect(self._emit_change)
        layout.addWidget(self.chk)

        self.lbl_name = QtWidgets.QLabel(f"{icon}  {label_text}")
        self.lbl_name.setStyleSheet("font-size: 13px; font-weight: 700; color: #e2e8f0;")
        layout.addWidget(self.lbl_name)
        layout.addStretch()

        # Pause Duration input
        lbl_pause = QtWidgets.QLabel("Pause:")
        lbl_pause.setStyleSheet("font-size: 11px; font-weight: 600; color: #94a3b8;")
        layout.addWidget(lbl_pause)

        self.spin_pause = QtWidgets.QSpinBox()
        self.spin_pause.setRange(0, 7200)
        self.spin_pause.setValue(default_pause_sec)
        self.spin_pause.setSuffix("s")
        self.spin_pause.setMinimumWidth(80)
        self.spin_pause.setMinimumHeight(28)
        self.spin_pause.setStyleSheet("""
            QSpinBox {
                background-color: #0b0e1a;
                color: #00f0ff;
                border: 1px solid #222d48;
                border-radius: 5px;
                padding: 2px 2px 2px 6px;
                font-weight: 700;
                font-size: 11px;
            }
            QSpinBox:focus {
                border: 1px solid #00f0ff;
            }
        """)
        self.spin_pause.valueChanged.connect(self._emit_change)
        layout.addWidget(self.spin_pause)

    def is_checked(self) -> bool:
        return self.chk.isChecked()

    def set_checked(self, val: bool):
        self.chk.setChecked(val)

    def get_pause(self) -> int:
        return self.spin_pause.value()

    def set_pause(self, sec: int):
        self.spin_pause.setValue(sec)

    def _emit_change(self):
        self.sig_changed.emit(self.cat_id, self.chk.isChecked(), self.spin_pause.value())
