<div align="center">

# 🎯 PupuSnipe

**The Fastest, High-Performance Sol's RNG Private Server Sniper & Fishing Macro**

[![Release](https://img.shields.io/github/v/release/SyphoxYt/pupu-snipes?color=00ff88&label=Latest%20Release)](https://github.com/SyphoxYt/pupu-snipes/releases)
[![Python](https://img.shields.io/badge/Python-3.15-3776ab?logo=python&logoColor=white)](https://python.org)
[![Qt](https://img.shields.io/badge/GUI-PySide6%20%28Qt6%29-41cd52?logo=qt&logoColor=white)](https://pyside.org)
[![Platform](https://img.shields.io/badge/Platform-Windows%2010%20%7C%2011-0078d4?logo=windows&logoColor=white)](https://microsoft.com/windows)
[![Latency](https://img.shields.io/badge/Detect%20Latency-%3C20ms-ff0055)](https://github.com/SyphoxYt/pupu-snipes)
[![License](https://img.shields.io/badge/License-Proprietary%20%7C%20All%20Rights%20Reserved-red)](LICENSE)

</div>

---

## ⚡ Overview

**PupuSnipe** is an ultra-fast, hardware-accelerated private server sniper and fishing macro engine built specifically for Roblox's **Sol's RNG** (`Place ID: 15532314909`).

Engineered with a direct C-optimized Discord WebSocket gateway and native Windows OS dispatch, PupuSnipe captures private server join links and executes client launches with **sub-20ms detect-to-launch latency** — consistently beating web browsers, public bots, and standard snipers to high-tier biomes and rare merchant spawns.

---

## 🚀 Key Features

### ⚡ Sub-20ms Detect-to-Launch Pipeline
- **Zero Browser Delay**: Bypasses browser navigation, JavaScript redirects, and "Open Roblox?" popups by dispatching directly to the OS kernel.
- **Discord Gateway Streaming**: Real-time push frames straight from Discord's WebSocket connection (`op: 14`), achieving microsecond message discovery across 9+ priority channels simultaneously.
- **Microsecond Memory Link Extraction**: Precompiled C-regex parses message content, ActionRow button components, and embed links in under `0.4 ms`.

### 🎮 Strict Client Routing & Instant In-Game Server Hopping
- **Normal Roblox Isolation**: Selecting **"Normal Roblox (RobloxPlayerBeta.exe)"** strictly launches the official client and completely bypasses Voidstrap/Bloxstrap wrappers.
- **Voidstrap & Bloxstrap Integration**: Full native support for custom bootstrappers (`Voidstrap.exe` / `Bloxstrap.exe`) using `-player` command-line IPC.
- **Instant In-Place Hopping**: If Roblox is already open, PupuSnipe routes the new join arguments to the active process, performing an instant in-game hop without closing and restarting the game window.

### 🌐 Universal Link Format Support
PupuSnipe seamlessly extracts, validates, and launches every Sol's RNG join link format:
- **Standard Web Links**: `https://www.roblox.com/games/15532314909/...?...privateServerLinkCode=XYZ`
- **Official Share Links**: `https://www.roblox.com/share?code=XYZ&type=Server`
- **Native Protocol URIs**: `roblox://placeId=15532314909&linkCode=XYZ` and `roblox://navigation/share_links?code=XYZ`
- **xe33Hunt Gateway Links**: Full support for `https://xe33hunt.com/j/<token>` and `https://xe33hunt.com/join/<token>`
- **Join-Gateway Portals**: `https://xe33cc.github.io/join/?s=<UUID>`
- **Third-Party Formats**: RoPro (`ro.pro/join/...`), JoinRBX (`join-rbx.vexsys.site`), RoSeal (`roseal.live`), and FishStrap (`fishstrap.app`).

### 🌸 Real-Time Biome & Aura Log Watcher
- Continuous background tailing of Roblox, Voidstrap, and Bloxstrap log files without memory injection.
- Instantly detects active server biomes: *Glitched, Dreamspace, Cyberspace, Singularity, Corruption, Starfall, Sandstorm, Hell, Rain, Snow*.
- Detects equipped auras (*Abyssal Hunter, Archangel, Bloodlust, Gargantua, Sovereign, Symphony, etc.*).

### 🎣 Built-in FishSol v2.1 Macro
- Automatic fishing minigame bar tracker.
- **Infinite Biome Camping**: Auto-resets character (`Esc -> R -> Enter`) on arrival, equips optimal rod and aura, navigates merchant selling paths, and auto-fishes continuously until the biome despawns.

### 📢 High-Tech Discord Webhook Alerts
- **100% Clickable Links**: Large header join button `# 🚀 [CLICK HERE TO JOIN VIP SERVER NOW](https://...)` alongside clickable mobile/PC links.
- **Windows Run Command**: Single-click copyable code block ` ```roblox://...``` ` formatted specifically for Windows Run (`Win + R`).
- **Live Biome Art**: Automatically passes forwarded embed banners and displays bundled high-resolution neon biome art.
- **Engine Lifecycle Alerts**: Automated green (ONLINE) and red (OFFLINE) session metric reports.

### ⏱️ 10-Minute Anti-Hop Protection
- Enforces an automated 10-minute cooldown after joining a server to prevent accidental hops.
- Real-time countdown status banner with instant single-key manual reset via **`F9`**.

---

## ⌨️ Global Hotkeys

| Hotkey | Action | Default | Configurable |
|:---:|---|:---:|:---:|
| **`F4`** | Toggle Sniper (Start / Stop) | `F4` | ✅ (Misc Tab) |
| **`F5`** | Pause Monitoring | `F5` | ✅ (Misc Tab) |
| **`F6`** | Resume Monitoring | `F6` | ✅ (Misc Tab) |
| **`F7`** | Emergency Stop (Sniper + Macro) | `F7` | ✅ (Misc Tab) |
| **`F8`** | Toggle FishSol Macro | `F8` | ✅ (Misc Tab) |
| **`F9`** | Reset 10-Minute Cooldown & Unlock Camping | `F9` | ✅ (Misc Tab) |

---

## 📦 Installation & Quick Start

1. Download the latest release: **[`PupuSnipe-v1.1.5-win64.zip`](https://github.com/SyphoxYt/pupu-snipes/releases)**
2. Extract the archive to any folder on your PC.
3. Run **`PupuSnipe.exe`**.
4. In the **Sniper** tab, enter your Discord Bot Token or user token (stored securely in Windows Credential Manager via DPAPI).
5. Choose your preferred Roblox Client (**Normal Roblox** or **Voidstrap**) and click **Start Sniper** (or press **`F4`**)!

---

## 🔒 Security & Anti-Phishing

PupuSnipe includes an aggressive anti-phishing engine:
- Verifies exact official domains (`roblox.com`, `xe33hunt.com`, `xe33cc.github.io`).
- Blocks typosquatting domains (`robl0x`, `roblox-link`, `grabify`, `iplogger`, `discord.gift`).
- Stored credentials are encrypted locally using Windows Data Protection API (DPAPI); tokens are never sent to external servers.

---

## 📜 License & Copyright Notice

**Copyright © 2026 SyphoxYt / PupuSnipe Project. All Rights Reserved.**

This software and its source code are **strictly proprietary**. 
- No person or organization is permitted to copy, clone, distribute, modify, reverse-engineer, decompile, sublicense, sell, or steal any portion of this codebase or binary.
- Any unauthorized copying, redistribution, re-branding, or code theft will be met with immediate DMCA takedowns and applicable legal enforcement.

See [LICENSE](LICENSE) for the full proprietary license text.
