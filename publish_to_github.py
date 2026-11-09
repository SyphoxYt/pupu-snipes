"""
Automated GitHub Publisher for PupuSnipe
Target repository: https://github.com/SyphoxYt/pupu-snipes
"""
import os
import sys
import shutil
import subprocess

REPO_URL = "https://github.com/SyphoxYt/pupu-snipes.git"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def find_git():
    # 1. Exact installed path
    git_installed = r"C:\Program Files\Git\cmd\git.exe"
    if os.path.isfile(git_installed):
        return git_installed

    # 2. In PATH
    git_path = shutil.which("git")
    if git_path:
        return git_path

    # 2. Well-known install paths on Windows
    candidate_paths = [
        r"C:\Program Files\Git\cmd\git.exe",
        r"C:\Program Files\Git\bin\git.exe",
        r"C:\Program Files (x86)\Git\cmd\git.exe",
        r"C:\Program Files (x86)\Git\bin\git.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Git\cmd\git.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Git\bin\git.exe"),
        os.path.expandvars(r"%PROGRAMFILES%\Git\cmd\git.exe"),
    ]
    for p in candidate_paths:
        if os.path.isfile(p):
            return p
    return None

def install_git():
    print("[*] Git not found on your system. Attempting automatic installation via winget...")
    winget = shutil.which("winget") or os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WindowsApps\winget.exe")
    if os.path.exists(winget):
        try:
            cmd = [
                winget, "install", "--id", "Git.Git",
                "-e", "--source", "winget",
                "--accept-source-agreements",
                "--accept-package-agreements",
                "--silent"
            ]
            print(f"[*] Executing: {' '.join(cmd)}")
            res = subprocess.run(cmd)
            if res.returncode == 0:
                print("[+] Git installation succeeded! Checking path...")
                return find_git()
        except Exception as e:
            print(f"[!] Winget error: {e}")

    print("[!] Could not automatically install Git. Please download & install Git from: https://git-scm.com/download/win")
    return None

def run_git(git_exe, args):
    cmd = [git_exe] + args
    print(f"[*] Running: git {' '.join(args)}")
    res = subprocess.run(cmd, cwd=BASE_DIR, capture_output=True, text=True)
    if res.stdout:
        print(res.stdout.strip())
    if res.stderr and res.returncode != 0:
        print(f"[!] {res.stderr.strip()}")
    return res

def main():
    print("=" * 70)
    print("🚀 PupuSnipe GitHub Publishing Utility")
    print(f"Target Repository: {REPO_URL}")
    print(f"Local Workspace:   {BASE_DIR}")
    print("=" * 70)

    git_exe = find_git()
    if not git_exe:
        git_exe = install_git()
    
    if not git_exe:
        print("[!] ERROR: Git executable could not be found or installed.")
        print("Please install Git from https://git-scm.com/download/win and run this script again.")
        sys.exit(1)

    print(f"[+] Found Git at: {git_exe}")

    # Check for GitHub CLI authentication helper
    gh_cli = r"C:\Program Files\GitHub CLI\gh.exe"
    if os.path.isfile(gh_cli):
        try:
            print("[*] Found GitHub CLI (gh.exe). Configuring git credentials...")
            subprocess.run([gh_cli, "auth", "setup-git"], cwd=BASE_DIR)
        except Exception:
            pass

    # 1. Initialize repository if .git doesn't exist
    if not os.path.isdir(os.path.join(BASE_DIR, ".git")):
        print("[*] Initializing local git repository...")
        run_git(git_exe, ["init"])

    # 2. Configure default branch to main
    run_git(git_exe, ["branch", "-M", "main"])

    # 3. Configure remote origin
    res_remotes = run_git(git_exe, ["remote", "-v"])
    if "origin" in res_remotes.stdout:
        run_git(git_exe, ["remote", "set-url", "origin", REPO_URL])
    else:
        run_git(git_exe, ["remote", "add", "origin", REPO_URL])

    # 4. Stage files
    print("[*] Staging project files...")
    run_git(git_exe, ["add", "."])

    # 5. Check if commit is needed
    st = run_git(git_exe, ["status", "--porcelain"])
    if st.stdout.strip():
        commit_msg = sys.argv[1] if len(sys.argv) > 1 else "feat: update PupuSnipe with 10m cooldown, context log, and engine optimizations"
        print(f"[*] Committing changes: {commit_msg}")
        run_git(git_exe, ["commit", "-m", commit_msg])
    else:
        print("[*] Working tree clean, no new changes to commit.")

    # 6. Push to GitHub
    print(f"[*] Pushing to {REPO_URL} (branch: main)...")
    push_res = run_git(git_exe, ["push", "-u", "origin", "main"])
    if push_res.returncode != 0:
        print("[*] Normal push rejected. Attempting rebase pull in case repository has remote files...")
        run_git(git_exe, ["pull", "origin", "main", "--rebase", "--allow-unrelated-histories"])
        print("[*] Retrying push...")
        push_res = run_git(git_exe, ["push", "-u", "origin", "main"])

    if push_res.returncode == 0:
        print("\n" + "=" * 70)
        print("✅ SUCCESS! PupuSnipe is successfully published to GitHub:")
        print(f"👉 https://github.com/SyphoxYt/pupu-snipes")
        print("=" * 70)
    else:
        print("\n" + "=" * 70)
        print("⚠️ Push completed with status check. If GitHub prompted for credentials,")
        print("ensure you are signed in with your GitHub account: 'gh auth login' or personal access token.")
        print("=" * 70)

if __name__ == "__main__":
    main()
