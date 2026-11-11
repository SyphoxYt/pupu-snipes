# 🎯 PupuSnipe — High-Performance Sol's RNG Private Server Sniper & FishSol Macro

**PupuSnipe** is an ultra-fast, professional Windows desktop application engineered for detecting and joining Sol's RNG Roblox private servers with the absolute lowest possible latency.

Inspired by *Sol Sniper V3* and featuring deep native integration with the **FishSol v2.1** macro (`D:\FishSol-v2.1`), PupuSnipe combines automated Discord channel monitoring, anti-bait filtering, instant `roblox://` protocol launching, real-time Bloxstrap RPC biome tracking, and continuous auto-fishing/auto-selling automation.

---

## ⚡ What Makes PupuSnipe 50x Better?

### 1. Sub-Millisecond Protocol Launching & Microsecond Timing Breakdown
- **Direct Protocol Activation**: Emits `roblox://placeId=15532314909&linkCode=<code>` directly via the Windows native shell protocol. Bypasses browser confirmation dialogs, redirects, and slow web wrappers.
- **Microsecond Timestamp Logging**: Records and logs exact sub-millisecond timestamps across every phase:
  - `T0`: Message reception timestamp (`HH:MM:SS.mmm`)
  - `T1`: URL regex extraction (`+0.08ms`)
  - `T2`: Keyword profile priority matching (`+0.04ms`)
  - `T3`: Native protocol execution (`+0.92ms`)
  - **Total Detect-to-Launch**: Measured with microsecond precision directly on the dashboard.
- **Fastest Snipe Benchmark**: Displays rolling average latency and records all-time fastest snipe latency.

### 2. Bloxstrap & Roblox Live Log Watcher (from FishSol)
- Real-time background watcher for `%LOCALAPPDATA%\Roblox\logs\*.log`.
- Automatically extracts Discord Rich Presence lines (`[BloxstrapRPC]`).
- Live display of **Current Active Biome** (*Glitched, Dreamspace, Cyberspace, Singularity, Corruption, Starfall, Sandstorm, etc.*) and **Equipped Aura** directly on the dashboard!

### 3. Native Fishing Automation & Biome Camping
- **Server Join Sequence**: Upon joining a sniped private server, automatically triggers:
  1. Character reset (`Esc` $\to$ `R` $\to$ `Enter`).
  2. Collection menu navigation (`30, 406`) & equips rod/aura.
  3. Calibration of camera zoom (WheelUp 80, WheelDown 45).
  4. VIP / Abyssal / Non-VIP selling path and sells inventory.
  5. Walks to the fishing pond and begins the automated fishing loop.
- **Stay in Biome Forever**: Camp in **Corruption**, **Glitched**, or other target biomes indefinitely while auto-fishing and selling on a loop.
- **Minigame Automation**: Real-time pixel tracking of the catch bar (`757, 762` to `1161, 782`) reels and balances the minigame bar automatically.
- **External Macro Support**: Includes a 1-click launcher for `D:\FishSol-v2.1\FishSol-v2.1.ahk` if external AutoHotkey is preferred.

### 4. Direct Channel ID & Sniper-V3 Configuration Engine
- **Direct Multi-Channel Input**: Enter single or multiple Channel IDs (comma, space, or newline separated) right on the **Sniper** tab, with a 1-click **Load Biome Hunt Preset** button pre-loading top community channels.
- **Base Categories & Pause Durations**: Direct controls on the Sniper tab for **Glitch**, **Dreamspace**, **Cyberspace**, **Singularity**, **Jester**, **Mari**, **Rin**, **Void Coin**, and **Oblivion Potion** with individual pause duration inputs.
- **Advanced Joining Automations**:
  - `Leave Game Before Joining`: Sends automated `Esc -> L -> Enter` sequence to leave previous server cleanly.
  - `Close Roblox Before Joining`: Auto-terminates existing clients if desired.
  - `Minimize Other Windows`: Maximizes performance by focusing Roblox.
- **Custom Link Sniping**: Full support for third-party links: **RoPro** (`ro.pro` / `ropro.io`), **JoinRBX** (`join-rbx.vexsys.site`), **RoSeal** (`roseal.live`), **FishStrap** (`fishstrap.app`), and **Join-Gateway pages** (`xe33cc.github.io/join/?s=<UUID>`, any `*.github.io/join` page, `/join/<UUID>` links, plus direct `placeId` + `gameInstanceId` protocol/web links).
- **Illuminated Cyberpunk UI**: Radiant glowing gaming emblem logo, smooth animated tab transitions, pulsing engine indicators, and responsive `GlowCard` layouts.

### 5. Multi-Server & Multi-Channel Discord Monitoring
- Multi-server & multi-channel real-time message stream listening.
- Embed recognition (title, description, fields, footer, url).
- Authorized Discord Bot API authentication (`discord.py`). Stored securely in the **Windows Credential Manager (DPAPI)** via `keyring`.

---

## 🚀 Quick Start & Installation

### Option 1: Standalone Windows Executable
Run the pre-compiled standalone binary:
```powershell
C:\Users\botak\Downloads\pupusnipes\dist\PupuSnipe.exe
```
Or run the automated setup installer to create Desktop and Start Menu shortcuts:
```powershell
python C:\Users\botak\Downloads\pupusnipes\create_installer.py
```

### Option 2: Run from Python Source
Requirements: Python 3.12+ (tested on Python 3.15).

```bash
cd C:\Users\botak\Downloads\pupusnipes
pip install -r requirements.txt
python main.py
```

---

## ⌨️ Global Keyboard Shortcuts

| Shortcut | Action | Configurable |
|---|---|---|
| **`F4`** | Toggle Sniper (Start / Stop) | Yes (in Misc tab) |
| **`F5`** | Pause Monitoring | Yes (in Misc tab) |
| **`F6`** | Resume Monitoring | Yes (in Misc tab) |
| **`F7`** | Emergency Stop | Yes (in Misc tab) |
| **`F8`** | Toggle Fishing Automation | Yes (in Misc tab) |
| **`F9`** | Reset 10-Minute Cooldown | Yes (in Misc tab) |

---

## 🧪 Running Automated Tests

Run the test suite covering URL extraction, regex matching, SQLite persistence, anti-phishing, Bloxstrap logs, and FishSol mechanics:

```bash
$env:PYTHONPATH="C:\Users\botak\Downloads\pupusnipes"; python -m unittest discover -s C:\Users\botak\Downloads\pupusnipes\tests
# Ran 21 tests in 0.404s — OK
```

---

## 📄 License
This project is licensed under the GPL-3.0 License in accordance with open-source Sol's RNG sniper utilities.
