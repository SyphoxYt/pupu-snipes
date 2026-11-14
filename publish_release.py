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
    tag = "v1.1.1"
    name = "PupuSnipe v1.1.1 — Clickable Join Links, Biome Images & Engine Webhooks"
    body = """# 🎯 PupuSnipe v1.1.1 — The Ultimate Sol's RNG Private Server Sniper & Macro

### 🚀 What's New in v1.1.1:
- **Prominent Clickable VIP Join Links in Discord**:
  - Discord's markdown limitation where protocol links (`roblox://`) were unclickable has been solved.
  - Large banner headline `# 🚀 [👉 CLICK HERE TO JOIN VIP SERVER NOW 👈](https://...)` directly inside the embed description.
  - Clickable direct link embedded in the `@everyone` notification message.
  - Dedicated clickable join field supporting UUID gateway instances (`https://xe33cc.github.io/join/?s=...`), share links, and private server links.
  - Isolated code block ` ```roblox://...``` ` for clean copy-pasting into Windows Run or terminal.
- **Live Biome Image Forwarding & Fallbacks**:
  - Automatically fetches and displays biome preview images from incoming Discord embeds and attachments sent by forwarding bots (e.g. Astrald's Hunters, Shay's Glitch Bot in `#🌸dreamspace`, `#🔥glitched`, `#🌐cyberspace-forwarding`).
  - High-resolution fallback neon banners bundled for all biomes (Dreamspace, Glitched, Cyberspace, Singularity, Corruption, Starfall, Sandstorm, Hell, Rain, Snow).
- **Engine Start & Stop Webhook Lifecycle Alerts**:
  - **🟢 STARTED Notification**: Dispatches an alert with the full list of connected channels, target place ID (`15532962292`), launch pipeline, and 10-minute cooldown protection.
  - **🔴 STOPPED Notification**: Dispatches a session summary embed with total scanned messages, sniped servers, and fastest detect latency.
- **Webhook Test Button Hanging Fix**:
  - Replaced thread-unsafe meta-calls with a native Qt Signal (`sig_webhook_tested`) so the "Test Webhook" button immediately re-enables with success/error status and never freezes on *"Sending test ping..."*.

### 📥 Download & Quick Start:
1. Download `PupuSnipe-v1.1.1-win64.zip` below.
2. Extract the folder anywhere.
3. Run `PupuSnipe.exe`!
"""

    dist_folder = r"C:\Users\botak\Downloads\pupusnipes\dist\PupuSnipe"
    zip_dest = r"C:\Users\botak\Downloads\pupusnipes\dist\PupuSnipe-v1.1.1-win64.zip"

    zip_dist(dist_folder, zip_dest)
    rel_url = create_or_update_release(token, repo, tag, name, body, zip_dest)
    print(f"\n[🎉] Release published successfully at: {rel_url}")
