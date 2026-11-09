"""
PupuSnipe Theme & Stylesheet Definition
Ultra-modern cyberpunk dark theme inspired by Sol's RNG aesthetic and Sol Sniper V3.
Vibrant neon accents, glowing borders, smooth card elevation, and responsive typography.
"""

DARK_THEME_QSS = """
/* Global Window & Typography */
QMainWindow {
    background-color: #080a12;
    color: #e2e8f0;
}

QWidget {
    font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
    font-size: 13px;
    color: #e2e8f0;
    selection-background-color: #3b82f6;
    selection-color: #ffffff;
}

/* Scroll Areas */
QScrollArea {
    background-color: transparent;
    border: none;
}

QScrollArea > QWidget > QWidget {
    background-color: transparent;
}

/* Sidebar navigation */
#sidebar {
    background-color: #0c101c;
    border-right: 1px solid #1a2238;
}

#brandTitle {
    font-size: 21px;
    font-weight: 900;
    color: #00f0ff;
    letter-spacing: 1.5px;
}

#brandSubtitle {
    font-size: 11px;
    font-weight: 700;
    color: #a855f7;
    letter-spacing: 0.5px;
}

/* Nav Buttons */
QPushButton.nav-btn {
    text-align: left;
    padding: 11px 16px;
    border: 1px solid transparent;
    border-radius: 9px;
    background-color: transparent;
    color: #94a3b8;
    font-size: 13px;
    font-weight: 600;
}

QPushButton.nav-btn:hover {
    background-color: #151d30;
    color: #f1f5f9;
    border: 1px solid #283756;
}

QPushButton.nav-btn:checked {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1a2342, stop:1 #11172e);
    color: #00f0ff;
    border: 1px solid #00f0ff55;
    border-left: 3px solid #00f0ff;
    font-weight: 700;
}

/* Glow Cards & Frames */
QFrame.glow-card, #glowCard {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #11172a, stop:1 #0d1222);
    border: 1px solid #1e2a47;
    border-radius: 12px;
    margin-top: 6px;
}

QFrame.glow-card:hover, #glowCard:hover {
    border: 1px solid #00f0ff44;
}

/* Base Category Row */
#categoryRow {
    background-color: #0f1526;
    border: 1px solid #1a233a;
    border-radius: 8px;
}

#categoryRow:hover {
    border: 1px solid #00f0ff44;
    background-color: #131b30;
}

/* Stat Cards */
QFrame.stat-card {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #12182b, stop:1 #0e1324);
    border: 1px solid #1e2a47;
    border-radius: 11px;
    padding: 14px 16px;
}

QFrame.stat-card:hover {
    border: 1px solid #00f0ff66;
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #172038, stop:1 #10172c);
}

QLabel.card-title {
    color: #94a3b8;
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.8px;
}

QLabel.card-value {
    font-size: 24px;
    font-weight: 800;
}

QLabel.card-subtext {
    color: #64748b;
    font-size: 10px;
    font-weight: 500;
}

/* Primary Action Buttons */
QPushButton.btn-primary {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4f46e5, stop:0.6 #6366f1, stop:1 #00d4ff);
    color: #ffffff;
    font-weight: 700;
    font-size: 13px;
    border: 1px solid #60a5fa55;
    border-radius: 9px;
    padding: 10px 18px;
}

QPushButton.btn-primary:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #5b52f0, stop:0.6 #7477f7, stop:1 #38e1ff);
    border: 1px solid #00f0ffcc;
}

QPushButton.btn-primary:pressed {
    background: #3730a3;
}

/* Danger / Stop Buttons */
QPushButton.btn-danger {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #be123c, stop:1 #f43f5e);
    color: #ffffff;
    font-weight: 700;
    font-size: 13px;
    border: 1px solid #f43f5e66;
    border-radius: 9px;
    padding: 10px 18px;
}

QPushButton.btn-danger:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #e11d48, stop:1 #fb7185);
    border: 1px solid #f43f5ecc;
}

QPushButton.btn-danger:pressed {
    background: #9f1239;
}

/* Standard Secondary Buttons */
QPushButton.btn-secondary {
    background-color: #141c2e;
    color: #cbd5e1;
    border: 1px solid #23304d;
    border-radius: 9px;
    padding: 8px 14px;
    font-weight: 600;
    font-size: 12px;
}

QPushButton.btn-secondary:hover {
    background-color: #1c2740;
    color: #ffffff;
    border: 1px solid #384d7a;
}

QPushButton.btn-secondary:pressed {
    background-color: #0f1524;
}

/* Warning / Accent Buttons */
QPushButton.btn-accent {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #b45309, stop:1 #f59e0b);
    color: #ffffff;
    font-weight: 700;
    font-size: 13px;
    border: 1px solid #f59e0b66;
    border-radius: 9px;
    padding: 10px 18px;
}

QPushButton.btn-accent:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #d97706, stop:1 #fbbf24);
    border: 1px solid #fbbf24cc;
}

/* Tables */
QTableWidget {
    background-color: #0f1526;
    border: 1px solid #1c263e;
    border-radius: 10px;
    gridline-color: #182034;
    color: #e2e8f0;
    selection-background-color: #1e3a66;
    selection-color: #ffffff;
    outline: none;
}

QHeaderView::section {
    background-color: #090d18;
    color: #94a3b8;
    font-weight: 700;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    padding: 10px 8px;
    border: none;
    border-bottom: 2px solid #1c263e;
}

/* LineEdits and Combos */
QLineEdit, QComboBox, QSpinBox, QPlainTextEdit {
    background-color: #0b0f1d;
    border: 1px solid #202b46;
    border-radius: 8px;
    padding: 8px 12px;
    color: #f1f5f9;
    font-size: 13px;
}

QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QPlainTextEdit:focus {
    border: 1px solid #00f0ff;
    background-color: #0f1528;
}

QComboBox::drop-down {
    border: none;
    padding-right: 10px;
}

/* Checkboxes */
QCheckBox {
    spacing: 8px;
    color: #cbd5e1;
    font-size: 13px;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 5px;
    border: 1px solid #334155;
    background-color: #0b0f1d;
}

QCheckBox::indicator:hover {
    border: 1px solid #00f0ff;
}

QCheckBox::indicator:checked {
    background-color: #00f0ff;
    border: 1px solid #00f0ff;
    image: none;
}

/* GroupBox */
QGroupBox {
    background-color: #0f1526;
    border: 1px solid #1e2942;
    border-radius: 12px;
    margin-top: 18px;
    padding-top: 20px;
    font-weight: 700;
    font-size: 13px;
    color: #f1f5f9;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 3px 12px;
    background-color: #172038;
    border: 1px solid #2a3a60;
    border-radius: 6px;
    color: #00f0ff;
    font-size: 12px;
    font-weight: 700;
}

/* List Widgets */
QListWidget {
    background-color: #0b0f1d;
    border: 1px solid #202b46;
    border-radius: 8px;
    color: #e2e8f0;
    padding: 4px;
}

QListWidget::item {
    padding: 6px 10px;
    border-radius: 6px;
}

QListWidget::item:hover {
    background-color: #151d32;
}

QListWidget::item:selected {
    background-color: #1e3a66;
    color: #00f0ff;
}

/* ScrollBars */
QScrollBar:vertical {
    background: #06080e;
    width: 8px;
    border-radius: 4px;
    margin: 2px;
}

QScrollBar::handle:vertical {
    background: #202b46;
    min-height: 24px;
    border-radius: 4px;
}

QScrollBar::handle:vertical:hover {
    background: #00f0ffaa;
}

QScrollBar:horizontal {
    background: #06080e;
    height: 8px;
    border-radius: 4px;
    margin: 2px;
}

QScrollBar::handle:horizontal {
    background: #202b46;
    min-width: 24px;
    border-radius: 4px;
}

QScrollBar::handle:horizontal:hover {
    background: #00f0ffaa;
}

/* TextEdit Logs / Terminal */
QTextEdit, QPlainTextEdit {
    background-color: #060810;
    border: 1px solid #161e33;
    border-radius: 9px;
    color: #00ff88;
    font-family: 'Cascadia Code', 'Consolas', monospace;
    font-size: 12px;
    line-height: 1.4;
    padding: 8px;
}

/* Tooltips */
QToolTip {
    background-color: #12182b;
    color: #f8fafc;
    border: 1px solid #00f0ff88;
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 12px;
}
"""
