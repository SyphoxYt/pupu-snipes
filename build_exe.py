"""
PupuSnipe Executable Packaging Script
Builds standalone PupuSnipe.exe using PyInstaller
"""
import os
import sys
import subprocess
import shutil

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "pupusnipe", "assets")
ICON_PATH = os.path.join(ASSETS_DIR, "icon.ico")
DIST_DIR = os.path.join(BASE_DIR, "dist")
BUILD_DIR = os.path.join(BASE_DIR, "build")


def build():
    print(f"[*] Building PupuSnipe Robust Windows Distribution...")

    # Locate python3t.dll and curl_cffi native libraries
    py_dir = os.path.dirname(sys.executable)
    python3t_dll = os.path.join(py_dir, "abi3t-compat", "python3t.dll")
    
    extra_binaries = []
    if os.path.isfile(python3t_dll):
        extra_binaries.append(f"--add-binary={python3t_dll};.")

    # Build onedir distribution (prevents decompression code -3 and unlocks instant startup)
    pyinstaller_args = [
        sys.executable,
        "-m", "PyInstaller",
        "--name=PupuSnipe",
        "--onedir",
        "--noconsole",
        f"--icon={ICON_PATH}",
        f"--add-data={ASSETS_DIR};pupusnipe/assets",
        "--hidden-import=keyring.backends.Windows",
        "--hidden-import=pynput.keyboard._win32",
        "--hidden-import=pynput.mouse._win32",
        "--hidden-import=PySide6.QtCore",
        "--hidden-import=PySide6.QtGui",
        "--hidden-import=PySide6.QtWidgets",
        "--collect-all=discord",
        "--collect-all=curl_cffi",
        "--collect-all=discord_protos",
        f"--runtime-hook={os.path.join(BASE_DIR, 'pupusnipe', 'rthook_lazy_imports.py')}",
    ] + extra_binaries + [
        "--clean",
        "-y",
        os.path.join(BASE_DIR, "main.py")
    ]

    print("[*] Running command:", " ".join(pyinstaller_args))
    result = subprocess.run(pyinstaller_args, cwd=BASE_DIR)
    
    if result.returncode == 0:
        exe_path = os.path.join(DIST_DIR, "PupuSnipe", "PupuSnipe.exe")
        dist_internal = os.path.join(DIST_DIR, "PupuSnipe", "_internal")
        if os.path.exists(exe_path):
            print(f"[+] Build SUCCESS! Executable created at: {exe_path}")

            # Ensure all native DLL dependencies for curl_cffi and python3t are in place
            try:
                import curl_cffi
                cffi_parent = os.path.dirname(os.path.dirname(curl_cffi.__file__))
                curl_libs_dir = os.path.join(cffi_parent, "curl_cffi.libs")
                
                dll_destinations = [
                    os.path.join(DIST_DIR, "PupuSnipe"),
                    dist_internal,
                    os.path.join(dist_internal, "curl_cffi"),
                    os.path.join(dist_internal, "curl_cffi.libs")
                ]
                for dest in dll_destinations:
                    os.makedirs(dest, exist_ok=True)
                    if os.path.isfile(python3t_dll):
                        shutil.copy2(python3t_dll, os.path.join(dest, "python3t.dll"))
                    if os.path.isdir(curl_libs_dir):
                        for f in os.listdir(curl_libs_dir):
                            if f.endswith(".dll"):
                                shutil.copy2(os.path.join(curl_libs_dir, f), os.path.join(dest, f))
            except Exception as e:
                print(f"[!] Warning copying extra DLLs: {e}")

            # Clean temporary intermediate build cache to prevent confusing broken files
            if os.path.exists(BUILD_DIR):
                shutil.rmtree(BUILD_DIR, ignore_errors=True)
                print("[*] Cleaned temporary build directory.")

            # Deploy to root folder for instant 1-click launch from Downloads/pupusnipes
            root_exe = os.path.join(BASE_DIR, "PupuSnipe.exe")
            root_internal = os.path.join(BASE_DIR, "_internal")
            print("[*] Deploying PupuSnipe.exe and dependencies to root directory...")
            shutil.copy2(exe_path, root_exe)
            if os.path.exists(dist_internal):
                shutil.copytree(dist_internal, root_internal, dirs_exist_ok=True)
            print(f"[+] Root executable ready at: {root_exe}")

            # Also deploy to AppData and create Desktop shortcuts
            installer_script = os.path.join(BASE_DIR, "create_installer.py")
            if os.path.isfile(installer_script):
                subprocess.run([sys.executable, installer_script], cwd=BASE_DIR)

            return True
    print("[-] Build failed with return code:", result.returncode)
    return False


if __name__ == "__main__":
    success = build()
    sys.exit(0 if success else 1)
