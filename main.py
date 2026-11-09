"""
PupuSnipe Main Desktop Application Entry Point
High-performance Sol's RNG Private Server Sniper & Fishing Macro Engine
"""
import os
import sys

# Python 3.15 PEP 810 lazy imports compatibility with PyInstaller frozen environment:
# Clear lazy_modules so CPython does not generate unresolved 'lazy_import' proxy objects
if hasattr(sys, "lazy_modules"):
    try:
        sys.lazy_modules.clear()
    except Exception:
        pass
if hasattr(sys, "set_lazy_imports"):
    try:
        sys.set_lazy_imports("normal")
    except Exception:
        pass
if hasattr(sys, "set_lazy_imports_filter"):
    try:
        sys.set_lazy_imports_filter(None)
    except Exception:
        pass

# Force eager import of modules that Python 3.15 marks as lazy
import warnings
import traceback
import locale
import pkgutil

# Eagerly resolve and patch concurrent.futures executors for Python 3.15 PyInstaller
try:
    import concurrent.futures.thread
    import concurrent.futures.process
    import concurrent.futures
    concurrent.futures.ThreadPoolExecutor = concurrent.futures.thread.ThreadPoolExecutor
    concurrent.futures.ProcessPoolExecutor = concurrent.futures.process.ProcessPoolExecutor
except Exception:
    pass

import ctypes

# Add package directory to path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Register DLL directories for bundled libraries (curl_cffi, PySide6, Windows C runtimes)
if sys.platform == "win32":
    meipass = getattr(sys, "_MEIPASS", None)
    dll_dirs = [
        meipass,
        BASE_DIR,
        os.path.join(BASE_DIR, "_internal"),
        os.path.join(BASE_DIR, "_internal", "curl_cffi.libs"),
    ]
    if meipass:
        dll_dirs.extend([
            os.path.join(meipass, "_internal"),
            os.path.join(meipass, "curl_cffi.libs"),
            os.path.join(meipass, "_internal", "curl_cffi.libs"),
        ])
    for d in dll_dirs:
        if d and os.path.isdir(d):
            try:
                os.add_dll_directory(d)
            except Exception:
                pass
            try:
                ctypes.windll.kernel32.SetDllDirectoryW(d)
            except Exception:
                pass

# Set Windows Per-Monitor v2 DPI awareness to avoid scaling bugs across different monitors & 125%/150% scaling
if sys.platform == "win32":
    try:
        # 2 = PROCESS_PER_MONITOR_DPI_AWARE
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

from PySide6 import QtCore, QtGui, QtWidgets
from pupusnipe.core.config import APP_NAME, APP_VERSION
from pupusnipe.ui.main_window import MainWindow


def main():
    # Pass-through high DPI scale policy prevents pixelated/jumping scaling glitches
    if hasattr(QtCore.Qt, "HighDpiScaleFactorRoundingPolicy"):
        QtGui.QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
            QtCore.Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )

    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName("PupuSnipe")

    # Set default modern font
    font = QtGui.QFont("Segoe UI", 10)
    font.setStyleHint(QtGui.QFont.SansSerif)
    app.setFont(font)

    # Set Application Icon
    assets_dir = os.path.join(BASE_DIR, "pupusnipe", "assets")
    ico_path = os.path.join(assets_dir, "icon.ico")
    if os.path.exists(ico_path):
        app.setWindowIcon(QtGui.QIcon(ico_path))

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
