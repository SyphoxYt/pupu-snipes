# PupuSnipe Configuration & Setup Guide

A complete reference guide for configuring **PupuSnipe** and the integrated **FishSol** auto-fishing engine.

---

## 1. Discord Bot Token Setup

PupuSnipe uses official authorized Discord Bot authentication (`discord.py`). It **never** requests or stores personal user tokens.

### Step 1: Create a Discord Application
1. Go to the [Discord Developer Portal](https://discord.com/developers/applications).
2. Click **New Application** in the top right.
3. Enter the name **PupuSnipe** and click **Create**.

### Step 2: Configure Bot Privileges & Privileged Intents
1. In the left sidebar, click **Bot**.
2. Click **Reset Token** and copy the new token.
3. Scroll down to **Privileged Gateway Intents**:
   - Turn **ON** `Message Content Intent` (Required for reading link embeds and channel text).
   - Turn **ON** `Server Members Intent`.
4. Click **Save Changes**.

### Step 3: Invite the Bot to Your Monitoring Server(s)
1. In the left sidebar, click **OAuth2** -> **URL Generator**.
2. Under **Scopes**, select `bot`.
3. Under **Bot Permissions**, select:
   - `Read Messages / View Channels`
   - `Read Message History`
4. Copy the generated URL and open it in your browser to invite the bot to the Discord server(s) where private server links are shared.

### Step 4: Add Token to PupuSnipe
1. Open **PupuSnipe**.
2. Go directly to the **Sniper** tab (or **Settings & Logs** tab).
3. Paste your Bot Token in the token field under **STEP 1** and click **Save Token**.
4. The token will be encrypted and stored securely in your local **Windows Credential Manager (DPAPI)**.

---

## 2. Channel Configuration

1. In Discord, enable **Developer Mode** (User Settings -> Advanced -> Developer Mode: ON).
2. Right-click the channel where Sol's RNG private server links are posted and select **Copy Channel ID**.
3. In PupuSnipe, go to the **Servers** tab.
4. Click **+ Add Channel**.
5. Paste the Channel ID, enter the Server Name and Channel Name, and click **OK**.
6. If no channels are added, PupuSnipe will monitor all channels the bot has access to.

---

## 3. Fast Joining Engine & Place ID Explained

PupuSnipe prioritizes sub-millisecond detection and instant launching:

- **Roblox Place ID (15532314909)**:
  - In Roblox, every game has a unique ID number called a Place ID. Sol's RNG is `15532314909`.
  - When PupuSnipe snipes a private server linkCode, it directly launches `roblox://placeId=15532314909&linkCode=...`.
  - This avoids browser confirmation prompts and opens Roblox in <1 millisecond.
- **Launch Mode**:
  - `Native Protocol Handler (roblox://)` (Default): Fastest method. Bypasses browser redirects and directly opens Roblox via Windows URI handler.
  - `Direct Executable Launch`: Executes `RobloxPlayerBeta.exe` directly with parameters.
- **Client Pre-Warming**:
  - Enable **Client Pre-Warming** so Roblox is kept running in the background. When a link is sniped, Roblox connects directly without a cold boot.
- **Duplicate Cooldown**:
  - Default is 180 seconds to prevent joining the same expired server twice.

---

## 4. Fishing Automation & Biome Camping (FishSol Integration)

PupuSnipe includes a native Python conversion of the **FishSol v2.1** macro (`D:\FishSol-v2.1`):

### How It Works:
1. **Join Sequence**: When PupuSnipe snipes a private server, it can automatically:
   - Wait for Roblox to load the private server (~12s).
   - Reset the character (`Esc` -> `R` -> `Enter`).
   - Open the Collection menu (`30, 406`) and equip your fishing rod / aura.
   - Walk the VIP Selling Path (or Abyssal / Non-VIP path) to sell all existing fish inventory.
   - Walk to the fishing pond and begin the automated fishing loop.
2. **Stay in Biome Forever**:
   - If you snipe a **Corruption**, **Glitched**, or **Dreamspace** biome, PupuSnipe keeps you in that server indefinitely while the fishing automation farms fish and sells inventory on a loop!
3. **External Macro Support**:
   - If you prefer running your original AutoHotkey script, you can click **Launch External D:\FishSol-v2.1\FishSol-v2.1.ahk** directly from the Fishing tab.

---

## 5. Global Hotkeys

All hotkeys can be pressed anywhere in Windows:

| Action | Default Key | Configurable |
|---|---|---|
| Toggle Sniper | `F4` | Yes (in Misc tab) |
| Pause Monitoring | `F5` | Yes (in Misc tab) |
| Resume Monitoring | `F6` | Yes (in Misc tab) |
| Emergency Stop | `F7` | Yes (in Misc tab) |
| Toggle Fishing Automation | `F8` | Yes (in Misc tab) |

---

## 6. Anti-Bait & Blacklists

- **User Blacklist**: Add scammer or baiter Discord User IDs or usernames in the **Miscellaneous** tab to instantly drop their messages.
- **Keyword Blacklist**: Add words like `scam`, `fake`, `expired`, `troll` to reject fake links.
- **Phishing Protection**: Automatically detects and rejects typo-squatted domains (e.g. `robl0x.com`, `roblox.com.py`, suspicious redirect shorteners).
