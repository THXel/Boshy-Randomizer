<p align="right">
  <b>Language:</b>
  <a href="README.md" title="English"><span style="border:1px solid #ccc; padding:2px 7px; border-radius:999px; margin-left:4px;">🇬🇧</span></a>
  <a href="README/README_DE.md" title="Deutsch"><span style="border:1px solid #ccc; padding:2px 7px; border-radius:999px; margin-left:4px;">🇩🇪</span></a>
  <a href="README/README_RU.md" title="Русский"><span style="border:1px solid #ccc; padding:2px 7px; border-radius:999px; margin-left:4px;">🇷🇺</span></a>
  <a href="README/README_ES.md" title="Español"><span style="border:1px solid #ccc; padding:2px 7px; border-radius:999px; margin-left:4px;">🇪🇸</span></a>
  <a href="README/README_JP.md" title="日本語"><span style="border:1px solid #ccc; padding:2px 7px; border-radius:999px; margin-left:4px;">🇯🇵</span></a>
</p>

<div align="center">

  <img src="Custom/boshy_randomizer.png?raw=true" alt="Boshy Randomizer" width="420">

  <p><strong>Created by THXel & the I Wanna Be The Boshy Speedrun Community</strong><br>
  © 2025 THXel</p>

</div>

---

<p align="center">
  <b>Modern Randomizer for <i>I Wanna Be The Boshy</i></b><br>
  Random Routes • Route Seeds • ER/EB Masks • Live Tracker • Clean GUI
</p>

<p align="center">
  <a href="#-gameplay-preview">Gameplay Preview</a> •
  <a href="#-features">Features</a> •
  <a href="#-installation">Installation</a> •
  <a href="#-gameplay--modes">Gameplay & Modes</a> •
  <a href="#-seed-system">Seed System</a> •
  <a href="#-technical">Technical</a> •
  <a href="#-support">Support</a>
</p>

---

## 🎮 Gameplay Preview

<div align="center">
  <img src="Custom/gameplay.gif?raw=true" width="300">
  <img src="Custom/gameplay2.gif?raw=true" width="300">
</div>

---

## 🟦 Features

- 🎲 **Random Routes** – deterministic, seed-based routing  
- 🧩 **Item Randomizer (Safe Stats Mode)** – characters are randomized when collected; items stay original to avoid game crashes  
- 🧍 **Character Randomizer** – on start or per stage  
- 🎯 **Target Collect Mode** – hidden route, seed-defined targets  
- 📊 **Live Tracker** – achievements, items, bosses, characters  
- 🧾 **Endscreen Stats** – full route code  
- 🔁 **Deterministic Seeds** – identical replayable runs  
- 🧱 **ER/EB Masks** – optional rooms/bosses encoded inside seed  
- 🔒 **GUI Seed Lock** – entering a seed previews all settings and disables editing  
- ⚙️ **Auto-Setup System** – Python, modules, IWBTB import  

---

## 🟧 Installation

<div align="center">

<a href="https://github.com/THXel/Boshy-Randomizer/raw/refs/heads/Boshy-Randomizer/Boshy%20Randomizer%20installer.exe">
  <img src="https://img.shields.io/badge/⬇️%20DOWNLOAD%20BOSHY%20RANDOMIZER%20INSTALLER-2f8cff?style=for-the-badge&logo=files&logoColor=white" width="550" alt="Download Installer">
</a>

</div>

---

### ▶ Step 1 — Run the Installer  

**`Boshy Randomizer Installer.exe`**

⚠️ **Note:**  
Windows may show a **SmartScreen warning**:  
“Windows protected your PC” / “Unrecognized app”.

This is normal — the installer is **not digitally signed**.

To continue:

1. Click **“More information”**  
2. Click **“Run anyway”**

The installer will:

- copy Randomizer files  
- install Python 3.x (if missing)  
- install required modules  
- request your **IWBTB ZIP**  
- extract IWBTB into `/IWBTB`  
- create Start Menu shortcuts  

---

### ▶ Step 2 — Start the Randomizer  

Start via:

**Start Menu → Boshy Randomizer**

The launcher checks:

- IWBTB folder imported correctly  
- Python & modules installed  
- Randomizer files valid  

If something is missing, a detailed message appears.

---

# 🟪 Gameplay & Modes

### 🧍 Character Randomizer
- Default: Dark Boshy  
- Modes:
  - Random at start  
  - Random per stage  
- Seeded RNG ensures identical results  
- F3 menu disabled  

---

### 🧩 Item Randomizer – Detailed Explanation

IWBTB **cannot handle randomized item pickups** in-game  
→ replacing items directly causes **instant crashes**.

Therefore:

- ✔ Collected **characters ARE randomized**  
- ✔ Items stay original **in-game**  
- ✔ Items appear randomized only in **Stats Screen**  
- ✔ Ensures 100% stability  

This safe method allows predictable routing and prevents crashes.

---

### 🎯 Target Collect Mode

- Hidden routing  
- Seed-based target selection  
- Solgryn unlocks automatically when all targets collected

Optional areas you may disable:

- Boberman  
- “?” Room  
- Ridley  

All others stay enabled.

---

# 📊 Live Tracker

<div align="left">
  <img src="Custom/livetracker.gif?raw=true" width="300">
</div>

Tracks:

- items  
- achievements  
- bosses  
- characters  
- real-time state  

---

# 🎲 Seed System

Example seed:

```
R14-B4-T0-C2-P1-S152722-ER5-EB34C
```

Meaning:

- R = Rooms  
- B = Bosses  
- T = Target Collect  
- C = Character Randomizer Mode  
- P = Item Randomizer Mode  
- S = Seed  
- ER = Optional Rooms Mask  
- EB = Optional Bosses Mask  

Seed codes recreate the entire run **exactly**.

---

# 🔧 Technical

Python 3.11  
Modules:

- pillow  
- numpy  
- pyautogui  
- pygetwindow  
- tkinter  

Log file:

```
INI/randomizer_debug.log
```

---

# 🟨 Support

**Twitch:** https://twitch.tv/THXel  
**Discord:** https://discord.gg/ZXgTFjGw  

---

# ⚫ Disclaimer

Unofficial fan project.  
Not affiliated with **Solgryn / Grynsoft**.  
Use at your own risk.  
**Have fun — it’s Boshy Time!**
