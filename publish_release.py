import subprocess
import urllib.request
import urllib.parse
import json
import os
import sys
import zipfile

def get_git_token():
    try:
        p = subprocess.Popen(['git', 'credential', 'fill'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        out, _ = p.communicate('protocol=https\nhost=github.com\n')
        lines = dict(line.split('=', 1) for line in out.splitlines() if '=' in line)
        return lines.get('password')
    except Exception as ex:
        print(f"[-] Could not query git credential helper: {ex}", flush=True)
        return None

def zip_dist(source_dir, output_zip):
    print(f"[*] Creating zip archive: {output_zip} ...", flush=True)
    if os.path.exists(output_zip):
        try:
            os.remove(output_zip)
        except Exception:
            pass
    with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(source_dir):
            for file in files:
                abs_file = os.path.join(root, file)
                rel_file = os.path.relpath(abs_file, os.path.dirname(source_dir))
                zf.write(abs_file, rel_file)
    sz = os.path.getsize(output_zip)
    print(f"[+] Zip created successfully: {sz:,} bytes ({sz / (1024*1024):.2f} MB)", flush=True)

def create_or_update_release(token, repo, tag, name, body, zip_path):
    headers = {
        'Authorization': f'token {token}',
        'Accept': 'application/vnd.github.v3+json',
        'User-Agent': 'PupuSnipe-Release-Bot'
    }

    # 1. Check if release already exists for tag
    print(f"[*] Checking release for tag {tag} in {repo}...", flush=True)
    release_url = f"https://api.github.com/repos/{repo}/releases/tags/{tag}"
    req = urllib.request.Request(release_url, headers=headers)
    release_data = None
    try:
        with urllib.request.urlopen(req) as resp:
            release_data = json.loads(resp.read().decode())
            print(f"[+] Found existing release ID: {release_data['id']}", flush=True)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            print(f"[*] Release {tag} does not exist yet. Creating...", flush=True)
        else:
            raise

    if not release_data:
        # Create release
        create_url = f"https://api.github.com/repos/{repo}/releases"
        payload = {
            "tag_name": tag,
            "target_commitish": "main",
            "name": name,
            "body": body,
            "draft": False,
            "prerelease": False
        }
        req = urllib.request.Request(create_url, data=json.dumps(payload).encode('utf-8'), headers=headers, method="POST")
        with urllib.request.urlopen(req) as resp:
            release_data = json.loads(resp.read().decode())
            print(f"[+] Created release {tag} with ID: {release_data['id']}", flush=True)
    else:
        # Update release title and body
        update_url = f"https://api.github.com/repos/{repo}/releases/{release_data['id']}"
        payload = {
            "name": name,
            "body": body
        }
        req = urllib.request.Request(update_url, data=json.dumps(payload).encode('utf-8'), headers=headers, method="PATCH")
        with urllib.request.urlopen(req) as resp:
            release_data = json.loads(resp.read().decode())
            print(f"[+] Updated release {tag} body and title.", flush=True)

    release_id = release_data['id']
    upload_url = release_data['upload_url'].split('{')[0]

    # Delete existing asset with same name if present
    zip_name = os.path.basename(zip_path)
    for asset in release_data.get('assets', []):
        if asset['name'] == zip_name:
            print(f"[*] Deleting previous asset ID {asset['id']} ({asset['name']})...", flush=True)
            del_req = urllib.request.Request(asset['url'], headers=headers, method="DELETE")
            urllib.request.urlopen(del_req)
            print("[+] Previous asset deleted.", flush=True)
            break

    # Upload new asset
    print(f"[*] Uploading {zip_name} to GitHub Releases...", flush=True)
    upload_target = f"{upload_url}?name={urllib.parse.quote(zip_name)}"
    with open(zip_path, 'rb') as f:
        file_bytes = f.read()

    upload_headers = {
        'Authorization': f'token {token}',
        'Content-Type': 'application/zip',
        'User-Agent': 'PupuSnipe-Release-Bot',
        'Content-Length': str(len(file_bytes))
    }
    upload_req = urllib.request.Request(upload_target, data=file_bytes, headers=upload_headers, method="POST")
    with urllib.request.urlopen(upload_req) as resp:
        upload_resp = json.loads(resp.read().decode())
        print(f"[+] Asset uploaded successfully! URL: {upload_resp.get('browser_download_url')}", flush=True)
    
    return release_data.get('html_url')

if __name__ == "__main__":
    token = os.environ.get("GITHUB_TOKEN") or (sys.argv[1] if len(sys.argv) > 1 and sys.argv[1].startswith(("ghp_", "github_pat_")) else None) or get_git_token()
    if not token:
        print("[-] Error: Could not get GitHub token from git credentials or arguments.", flush=True)
        print("    Usage: python publish_release.py [TOKEN]", flush=True)
        exit(1)

    repo = "SyphoxYt/pupu-snipes"
    tag = "1.1.5"
    name = "PupuSnipe v1.1.5 — xe33Hunt Protocol Sync & Web Gateway Client Routing"
    body = """## 🎯 PupuSnipe v1.1.5 — xe33Hunt Protocol Sync & Web Gateway Client Routing

PupuSnipe v1.1.5 ensures that `xe33hunt.com` web gateway links always launch through the **correct Roblox client** you selected (Normal Roblox vs Voidstrap). Previously, xe33hunt links opened in the browser and always triggered Voidstrap regardless of your PupuSnipe setting — this is now fixed.

---

### 🔧 Web Gateway Protocol Handler Sync (NEW)
- **Respects Your Client Selection**: Before opening an xe33hunt link in the browser, PupuSnipe now temporarily sets the Windows `roblox://` protocol handler to match your selected client.
- **Normal Roblox selected** → registry set to `RobloxPlayerBeta.exe` → Turnstile passes → vanilla Roblox launches ✅
- **Voidstrap selected** → registry set to `Voidstrap.exe` → Turnstile passes → Voidstrap launches ✅
- **No more accidental Voidstrap launches** when you have Normal Roblox selected and an xe33hunt link fires.

### 🌐 `xe33hunt.com` Private Server Gateway Support
- **Full xe33Hunt Link Detection**: High-speed regex parsing for `https://xe33hunt.com/j/<token>` and `https://xe33hunt.com/join/<token>`.
- **Automatic Browser Gateway Dispatch**: Web gateway links are routed to your default browser for Cloudflare Turnstile verification, then the correct client launches automatically.
- **Anti-Phishing Whitelisting**: `xe33hunt.com` whitelisted in the anti-phishing module — legitimate join tokens pass instantly, malicious domains stay blocked.

### 🚀 Strict Normal Roblox Isolation
- **Strict Client Routing**: Selecting "Normal Roblox" exclusively spawns `RobloxPlayerBeta.exe` — Voidstrap is never touched.
- **Fast In-Game Server Hopping**: If Roblox is already running, the new join arguments route to the active process for an instant in-game hop.

### 🔗 100% Clickable Discord Webhook Links
- **Prominent Clickable Headline**: Clean `# 🚀 [CLICK HERE TO JOIN VIP SERVER NOW](https://...)` header.
- **Dual Direct Join Link**: Clickable label + bare URL on its own line — 100% clickable across desktop, mobile, and browser.
- **Windows Run (Win + R) Protocol**: Clean copyable code block for `roblox://` URIs.

### 📖 README & LICENSE
- **Professional GitHub README** with shields, architecture overview, link format reference, and hotkey table.
- **Strict Proprietary LICENSE** — no copying, stealing, decompiling, or redistribution allowed.

### 🧪 57 Passing Unit Tests
- Comprehensive automated coverage across link detection, client isolation, webhook payloads, and Discord gateway streaming.

---

### 📦 Installation & Quick Start
1. Download **`PupuSnipe-v1.1.5-win64.zip`** below.
2. Extract the archive anywhere on your PC.
3. Run **`PupuSnipe.exe`**!
"""

    dist_folder = r"C:\Users\botak\Downloads\pupusnipes\dist\PupuSnipe"
    zip_dest = r"C:\Users\botak\Downloads\pupusnipes\dist\PupuSnipe-v1.1.5-win64.zip"

    zip_dist(dist_folder, zip_dest)
    rel_url = create_or_update_release(token, repo, tag, name, body, zip_dest)
    print(f"\n[🎉] Release published successfully at: {rel_url}", flush=True)
