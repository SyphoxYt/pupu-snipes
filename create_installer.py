"""
PupuSnipe Automated Windows Installer & Shortcut Setup
Deploys PupuSnipe.exe to LocalAppData, creates Desktop and Start Menu shortcuts.
"""
import os
import sys
import shutil


def create_windows_shortcut(target_exe: str, shortcut_path: str, icon_path: str, description: str):
    ps_cmd = (
        f'$ws = New-Object -ComObject WScript.Shell; '
        f'$s = $ws.CreateShortcut("{shortcut_path}"); '
        f'$s.TargetPath = "{target_exe}"; '
        f'$s.WorkingDirectory = "{os.path.dirname(target_exe)}"; '
        f'$s.IconLocation = "{icon_path}"; '
        f'$s.Description = "{description}"; '
        f'$s.Save()'
    )
    import subprocess
    res = subprocess.run(["powershell", "-Command", ps_cmd], capture_output=True)
    return res.returncode == 0


def install():
    print("=" * 60)
    print(" PupuSnipe - Automated Windows Setup Installer")
    print("=" * 60)

    base_dir = os.path.dirname(os.path.abspath(__file__))
    dist_dir = os.path.join(base_dir, "dist", "PupuSnipe")
    dist_exe = os.path.join(dist_dir, "PupuSnipe.exe")
    single_exe = os.path.join(base_dir, "dist", "PupuSnipe.exe")
    icon_src = os.path.join(base_dir, "pupusnipe", "assets", "icon.ico")

    # Target directory in LocalAppData
    appdata = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
    install_dir = os.path.join(appdata, "Programs", "PupuSnipe")
    os.makedirs(install_dir, exist_ok=True)

    target_exe = os.path.join(install_dir, "PupuSnipe.exe")
    target_icon = os.path.join(install_dir, "icon.ico")

    if os.path.isdir(dist_dir):
        print(f"[*] Deploying full application directory to: {install_dir}")
        shutil.copytree(dist_dir, install_dir, dirs_exist_ok=True)
    elif os.path.isfile(single_exe):
        print(f"[*] Copying standalone executable to: {install_dir}")
        shutil.copy2(single_exe, target_exe)
    else:
        print(f"[-] Error: Compiled binary not found at: {dist_dir} or {single_exe}")
        print("[-] Please run 'python build_exe.py' first.")
        return False

    if os.path.isfile(icon_src):
        shutil.copy2(icon_src, target_icon)

    # Create Desktop shortcut
    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    desktop_shortcut = os.path.join(desktop, "PupuSnipe.lnk")
    create_windows_shortcut(target_exe, desktop_shortcut, target_icon, "High-performance Sol's RNG Private Server Sniper")
    print(f"[+] Desktop shortcut created: {desktop_shortcut}")

    # Create Start Menu shortcut
    start_menu = os.path.join(os.environ.get("APPDATA", ""), "Microsoft", "Windows", "Start Menu", "Programs")
    if os.path.isdir(start_menu):
        start_shortcut = os.path.join(start_menu, "PupuSnipe.lnk")
        create_windows_shortcut(target_exe, start_shortcut, target_icon, "PupuSnipe")
        print(f"[+] Start Menu shortcut created: {start_shortcut}")

    print("[+] Installation complete!")
    print(f"[+] PupuSnipe is ready to launch at: {target_exe}")
    return True


if __name__ == "__main__":
    install()
