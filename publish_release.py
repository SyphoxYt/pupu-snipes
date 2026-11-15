import subprocess
import urllib.request
import urllib.parse
import json
import os
import zipfile

def get_git_token():
    p = subprocess.Popen(['git', 'credential', 'fill'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    out, _ = p.communicate('protocol=https\nhost=github.com\n')
    lines = dict(line.split('=', 1) for line in out.splitlines() if '=' in line)
    return lines.get('password')

def zip_dist(source_dir, output_zip):
    print(f"[*] Creating zip archive: {output_zip} ...")
    with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(source_dir):
            for file in files:
                abs_file = os.path.join(root, file)
                rel_file = os.path.relpath(abs_file, os.path.dirname(source_dir))
                zf.write(abs_file, rel_file)
    print(f"[+] Zip created successfully: {os.path.getsize(output_zip)} bytes")

def create_or_update_release(token, repo, tag, name, body, zip_path):
    headers = {
        'Authorization': f'token {token}',
        'Accept': 'application/vnd.github.v3+json',
        'User-Agent': 'PupuSnipe-Release-Bot'
    }

    # 1. Check if release already exists for tag
    print(f"[*] Checking release for tag {tag} in {repo}...")
    release_url = f"https://api.github.com/repos/{repo}/releases/tags/{tag}"
    req = urllib.request.Request(release_url, headers=headers)
    release_data = None
    try:
        with urllib.request.urlopen(req) as resp:
            release_data = json.loads(resp.read().decode())
            print(f"[+] Found existing release ID: {release_data['id']}")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            print(f"[*] Release {tag} does not exist yet. Creating...")
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
            print(f"[+] Created release {tag} with ID: {release_data['id']}")
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
            print(f"[+] Updated release {tag} body and title.")

    release_id = release_data['id']
    upload_url = release_data['upload_url'].split('{')[0]

    # Delete existing asset with same name if present
    zip_name = os.path.basename(zip_path)
    for asset in release_data.get('assets', []):
        if asset['name'] == zip_name:
            print(f"[*] Deleting previous asset ID {asset['id']} ({asset['name']})...")
            del_req = urllib.request.Request(asset['url'], headers=headers, method="DELETE")
            urllib.request.urlopen(del_req)
            print("[+] Previous asset deleted.")
            break

    # Upload new asset
    print(f"[*] Uploading {zip_name} to GitHub Releases...")
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
        print(f"[+] Asset uploaded successfully! URL: {upload_resp.get('browser_download_url')}")
    
    return release_data.get('html_url')

if __name__ == "__main__":
    token = get_git_token()
    if not token:
        print("[-] Error: Could not get GitHub token from git credentials.")
        exit(1)

    repo = "SyphoxYt/pupu-snipes"
    tag = "1.1.4"
    name = "PupuSnipe v1.1.4 — Strict Normal Roblox Isolation & Discord Clickable Hyperlinks"
    body = """## 🎯 PupuSnipe v1.1.4 — Strict Normal Roblox Isolation & Discord Clickable Hyperlinks

PupuSnipe v1.1.4 fixes two critical issues: strictly enforcing Normal Roblox (`RobloxPlayerBeta.exe`) launch isolation so it never accidentally invokes Voidstrap, and fixing Discord Webhook join links so they are 100% clickable across all devices (PC, Mobile, and Web).

---

### 🚀 Strict Normal Roblox Isolation
- **Strict Client Routing**: When the user selects **"Normal Roblox (RobloxPlayerBeta.exe)"**, PupuSnipe exclusively resolves and spawns official Roblox (`RobloxPlayerBeta.exe`).
- **Never Triggers Voidstrap**: Fixed a logic bug where selecting "Direct Bootstrapper / Client Launch" while having Normal Roblox selected previously fell into Voidstrap launch routines. Voidstrap/Bloxstrap detection is now strictly bypassed when set to Normal Roblox.
- **Fast In-Game Server Hopping**: When Roblox is already running, launching `RobloxPlayerBeta.exe <protocol_url>` directs the active Roblox client to hop servers instantly without closing and reopening the game window.
- **Independent Scanner Caches**: Vanilla Roblox and custom bootstrappers now maintain independent cache entries to avoid path cross-contamination.

### 🔗 100% Clickable Discord Webhook Links
- **Fixed Broken Discord Markdown**: Fixed the issue where raw URLs wrapped in markdown brackets `[**👉 https://... 👈**](https://...)` broke Discord's markdown parser, rendering unclickable raw text.
- **Prominent Clickable Headline**: Clean `# 🚀 [CLICK HERE TO JOIN VIP SERVER NOW](https://...)` header button.
- **Dual Direct Join Link**: The Direct Join Link field now provides both a clean clickable label `[👉 Click Here to Open VIP Server 👈](https://...)` AND the bare URL on its own line, ensuring 100% clickability across desktop, browser, iOS, and Android clients.
- **Clean Windows Run (Win + R) Protocol**: Removed the broken `roblox://` markdown link (which Discord security policies disallow and render as raw text) and replaced it with a clean, single-click copyable code block ` ```roblox://...``` ` specifically intended for Windows Run (`Win + R`).

### 🛠️ Additional Polish
- **Updated UI Combos**: Clarified launcher method dropdown to explicitly show `Direct Client / Bootstrapper Launch (RobloxPlayerBeta / Voidstrap)`.
- **56 Comprehensive Unit Tests**: Added unit tests verifying strict vanilla client isolation and bootstrapper decoupling.

---

### 📦 Installation & Quick Start
1. Download **`PupuSnipe-v1.1.4-win64.zip`** below.
2. Extract the archive anywhere on your PC.
3. Run **`PupuSnipe.exe`**!
"""

    dist_folder = r"C:\Users\botak\Downloads\pupusnipes\dist\PupuSnipe"
    zip_dest = r"C:\Users\botak\Downloads\pupusnipes\dist\PupuSnipe-v1.1.4-win64.zip"

    if not os.path.exists(zip_dest):
        zip_dist(dist_folder, zip_dest)

    rel_url = create_or_update_release(token, repo, tag, name, body, zip_dest)
    print(f"\n[🎉] Release published successfully at: {rel_url}")
