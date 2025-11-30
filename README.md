<p align="right">
  <strong>Language:</strong><br>
  <a href="README.md" title="English"><strong>🇬🇧 English</strong></a> ·
  <a href="README/README_DE.md" title="Deutsch">🇩🇪 Deutsch</a> ·
  <a href="README/README_RU.md" title="Русский">🇷🇺 Русский</a> ·
  <a href="README/README_ES.md" title="Español">🇪🇸 Español</a> ·
  <a href="README/README_JP.md" title="日本語">🇯🇵 日本語</a>
</p>

<div align="center">

  <img src="Custom/boshy_randomizer.png?raw=true" alt="Boshy Randomizer" width="420">

  <p><strong>Created by THXel & the I Wanna Be The Boshy Speedrun Community</strong><br>
  © 2025 THXel</p>

</div>

---

<p align="center">
  <b>Modern Randomizer for <i>I Wanna Be The Boshy</i></b><br>
  Random Routes • Seed Codes • ER/EB Masks • Live Tracker • Clean GUI
</p>

<p align="center">
  <a href="#-features">Features</a> •
  <a href="#-installation">Installation</a> •
  <a href="#-gameplay--modes">Gameplay & Modes</a> •
  <a href="#-seed-system">Seed System</a> •
  <a href="#-technical">Technical</a> •
  <a href="#-support">Support</a>
</p>

---

## 🟦 Features

- 🎲 **Random Routes** – deterministic, seed‑based level & boss routing  
- 🧩 **Item Randomizer (Safe Stats Mode)** – *collected characters get randomized*, but in‑game items stay unchanged (avoids game crashes)  
- 🧍 **Character Randomizer** – random on run start or per stage, fully deterministic  
- 🎯 **Target Collect Mode** – hidden route, seed‑based targets  
- 📊 **Live Tracker** – tracks items, bosses, achievements, characters, and target items  
- 🔁 **Deterministic Seeds** – share & replay identical runs  
- 🧱 **ER/EB Masks** – optional stages and bosses stored inside the seed  
- 🔒 **Seed‑Lock GUI** – entering a seed locks the GUI and shows the settings  
- ⚙️ **Auto‑Setup** – installs Python, modules, fonts, and imports IWBTB automatically  

---

## 🎮 Gameplay Preview

<div align="center">
  <img src="Custom/gameplay.gif?raw=true" width="300">
  <img src="Custom/gameplay2.gif?raw=true" width="300">
</div>

---

## 🟧 Installation

<div align="center">

<a href="https://github.com/THXel/Boshy-Randomizer/raw/refs/heads/Boshy-Randomizer/Boshy%20Randomizer%20installer.exe">
  <img src="https://img.shields.io/badge/⬇️%20DOWNLOAD%20BOSHY%20RANDOMIZER%20INSTALLER-2f8cff?style=for-the-badge&logo=files&logoColor=white" width="550">
</a>

</div>

---

### ▶ Step 1 — Run the Installer

**`Boshy Randomizer Installer.exe`**

⚠️ **SmartScreen Notice:**  
Windows may display:

“Windows protected your PC” / “Unrecognized app”.

This is normal — the installer is **not digitally signed**.

Click:

1. **More information**  
2. **Run anyway**

The installer will automatically:

- copy all Randomizer files  
- install Python 3 (if missing)  
- install all required modules  
- ask for your **IWBTB ZIP**  
- extract the game into `/IWBTB`  
- create Start Menu shortcuts  

---

### ▶ Step 2 — Start the Randomizer

Launch via:

**Start Menu → Boshy Randomizer**

The launcher verifies:

- IWBTB imported correctly  
- Python & modules installed  
- all files present  

If something is missing, a debug message is shown.

---

# 🟪 Gameplay & Modes

<div style="display: flex; gap: 20px; align-items: flex-start;">
  <img src="Custom/GUI1.PNG?raw=true" width="300">
  <img src="Custom/GUI2.PNG?raw=true" width="300">
</div>

## ▶ Run Start

• Every run begins in the **Tutorial**.  
• After that, depending on GUI settings:  
  – **Random Route Mode**  
  – **Target Collect Mode**

## ▶ System Behavior

• Only **SaveFile1** is used.  
• **Do NOT delete SaveFile1.**  
• SaveFile2 and SaveFile3 are overwritten on every run.  
• Achievements & unlockables persist through the entire run.  
• **Awesomesauce** is always available at the start to guarantee unlocking **Gastly**.  
• The Teleport Room works normally, but:  
  To progress, you **must play the stage given by the Randomizer** — skipping is not possible.

---

## 🧍 Character Randomizer

- Default: Dark Boshy  
- Optional:  
  - random on run start  
  - random per stage  
- While active:  
  **F3 Character Menu is disabled** → deterministic seeds  

---

## 🧩 Item Randomizer – Details

The game crashes if items are replaced **in‑game**.  
So the Item Randomizer works like this:

- ✔ **Collected characters are randomized**  
- ✖ **Items are NOT replaced in‑game** (crash protection)  
- ✔ Items appear randomized **in the Stats screen only**  
- ✔ No gameplay risk  
- ✔ Stable & 100% routing‑safe  

---

## 🎯 Target Collect Mode

- Route hidden  
- Targets determined by seed  
- When all targets are collected → **Solgryn appears automatically**

Optional areas you may disable:

- Boberman  
- “?”  
- Ridley  

All others must remain enabled.

---

# 📊 Live Tracker

<div align="left">
  <img src="Custom/livetracker.gif?raw=true" width="300">
</div>

Tracks:

- Items  
- Achievements  
- Bosses  
- Characters  
- Live progression  
- **In Target Collect Mode:** the required **Target Items**

Fully automatic — no input required.

---

# 🎲 Seed System

<div align="left">
  <img src="Custom/route_overlay.gif?raw=true" width="300">
</div>

A seed code like:

```
R14-B4-T0-C2-P1-D1-S152722-ER5-EB34C
```

means:

- **R** – rooms  
- **B** – bosses  
- **T** – target mode (0 = off, 1 = Target Collect)  
- **C** – character randomizer  
  - 0 = off  
  - 1 = random on run start  
  - 2 = random per stage  
- **P** – item randomizer (0 = off, 1 = on – characters randomized, items stay in-game)  
- **D** – difficulty  
  - 0 = Ez  
  - 1 = Average  
  - 3 = Rage  
- **S** – seed  
- **ER** – optional rooms enable mask  
- **EB** – optional bosses enable mask  

Anyone using this code will get the **exact same route, difficulty, and character RNG**.

---

# 🔧 Technical

- Python 3.11  
- Uses:
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

Unofficial project, not affiliated with **Solgryn (Grynsoft)**.  
Use at your own risk.  
**Have fun — it’s Boshy Time!**
