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
    tag = "v1.1.3"
    name = "PupuSnipe v1.1.3 — Clickable VIP Join Links, Live Biome Images & Engine Webhooks"
    body = """## 🎯 PupuSnipe v1.1.3 — Clickable VIP Join Links, Live Biome Images & Engine Webhooks

PupuSnipe v1.1.3 brings a major overhaul to Discord Webhook notifications: fixing join link formatting, adding live Sol's RNG biome embed pictures, real-time sniper lifecycle tracking, and fixing UI test button freezes.

---

### 🚀 Clickable VIP Join Links in Discord
- **Prominent Join Banner**: Solves Discord's limitation where custom protocol links (`roblox://`) are unclickable in markdown. v1.1.3 introduces a prominent clickable headline banner:
  `# 🚀 [👉 CLICK HERE TO JOIN VIP SERVER NOW 👈](https://...)`
- **Clickable Pings**: The `@everyone` notification message now contains a direct clickable link to join immediately on mobile, browser, or PC.
- **Dedicated Link Field**: Displays the direct web URL for UUID gateway instances (`https://xe33cc.github.io/join/?s=...`), share links (`https://www.roblox.com/share-links?code=...`), and private server links.
- **Protocol Code Block**: The raw `roblox://` protocol link is cleanly formatted in an isolated code block ` ```roblox://...``` ` so desktop players can easily copy it into Windows Run or terminal.

### 🌸 Live Biome Image Forwarding & Fallbacks
- **Incoming Embed Extraction**: Automatically inspects incoming Discord messages from forwarding bots (such as *Astrald's Hunters* or *Shay's Glitch Bot* in `#🌸dreamspace`, `#🔥glitched`, `#🌐cyberspace-forwarding`) and extracts the original Discord CDN biome image.
- **Full-Width Embed Image**: Embeds the extracted image directly into the webhook notification (`image.url`).
- **Bundled Neon Fallback Banners**: If a message lacks an image, PupuSnipe falls back to high-resolution custom neon biome banners for *Dreamspace, Glitched, Cyberspace, Singularity, Corruption, Starfall, Sandstorm, Hell, Rain, and Snow*.

### 📡 Engine Lifecycle Notifications (Start & Stop)
- **🟢 Engine Started Alert**: Posts a vibrant green embed when the sniper engine starts, detailing:
  - Connected channels with server and channel names (e.g. `#🌸dreamspace`, `#🔥glitched`).
  - Target place ID (`15532962292` - Sol's RNG).
  - Launch pipeline client and method (e.g. `Voidstrap` via `Protocol`).
  - 10-minute cooldown protection status.
- **🔴 Engine Stopped Alert**: Posts a vibrant red embed summarizing session metrics:
  - Total messages scanned.
  - Total servers sniped.
  - Fastest detect latency in milliseconds.

### 🛠️ Bug Fixes & Improvements
- **Fixed Webhook Test Button Hanging**: Replaced the thread-unsafe meta-object call with a native PySide6 signal (`sig_webhook_tested`). The **"🧪 Test Webhook"** button now immediately re-enables with success/error status and never freezes on *"Sending test ping..."*.
- **Async Daemon Dispatch**: Webhooks and engine status alerts run on isolated daemon threads with 0ms impact on Roblox launch speed.

### 🧪 Quality & Tests
- **54 Passing Unit Tests**: Comprehensive test suite covering audio presets, webhook payload generation, engine status alerts, and regex link parsing.
- Compiled as a standalone Windows x64 onedir distribution with instant startup and embedded assets.

---

### 📦 Installation & Quick Start
1. Download **`PupuSnipe-v1.1.3-win64.zip`** below.
2. Extract the archive anywhere on your PC.
3. Run **`PupuSnipe.exe`**!
"""

    dist_folder = r"C:\Users\botak\Downloads\pupusnipes\dist\PupuSnipe"
    zip_dest = r"C:\Users\botak\Downloads\pupusnipes\dist\PupuSnipe-v1.1.3-win64.zip"

    if not os.path.exists(zip_dest):
        zip_dist(dist_folder, zip_dest)

    rel_url = create_or_update_release(token, repo, tag, name, body, zip_dest)
    print(f"\n[🎉] Release published successfully at: {rel_url}")
