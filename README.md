<div align="center">

  <img src="Custom/boshy_randomizer.png?raw=true" alt="Boshy Randomizer" width="420">

  <p><strong>Created by THXel & the I Wanna Be The Boshy Speedrun Community</strong><br>
  © 2025 THXel</p>

</div>

---

<p align="center">
  <b>Modern Randomizer for <i>I Wanna Be The Boshy</i></b><br>
  Random Routes • Live Tracker • Route Seeds • Clean GUI
</p>

<p align="center">
  <a href="#-features">Features</a> •
  <a href="#-installation">Installation</a> •
  <a href="#-gameplay--modes">Gameplay & Modes</a> •
  <a href="#-technical">Technical</a> •
  <a href="#-support">Support</a>
</p>

---

## 🟦 Features

- 🎲 **Random Routes** – Levels & bosses shuffled every run  
- 🧩 **Item & Collectable Handling** – trigger-stable routing  
- 🧍 **Random Characters** – on start or per stage  
- 🎯 **Target Collect Mode** – route hidden, collect all targets  
- 📊 **Live Tracker** – achievements, items, bosses, characters  
- 🧾 **Endscreen Stats** – summary + route code  
- 🔁 **Deterministic Seeds** – share & replay identical runs  
- ⚙️ **Auto-Setup System** – Python, modules, fonts, game import  

---

## 🖼 Screenshots

<div align="center">

<table>
<tr>
<td align="center">
  <img src="Custom/GUI1.PNG?raw=true" width="300"><br>
  <b>GUI 1</b>
</td>
<td align="center">
  <img src="Custom/GUI2.PNG?raw=true" width="300"><br>
  <b>GUI 2</b>
</td>
<td align="center">
  <img src="Custom/livetracker.PNG?raw=true" width="300"><br>
  <b>Live Tracker</b>
</td>
</tr>
</table>

</div>

---

## 🟩 Requirements
- Windows 10 or newer  
- Internet connection for setup  
- A copy of **I Wanna Be The Boshy** (ZIP from Grynsoft)

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

The installer will automatically:

- copy all Randomizer files  
- install Python 3.x (if missing)  
- install required Python modules  
- install the “its-boshy-time” font  
- ask for your **IWBTB ZIP**  
- extract the IWBTB game into `/IWBTB`  
- create Start Menu shortcuts  

---

### ▶ Step 2 — Start the Randomizer  

Launch via:

**Start Menu → Boshy Randomizer**

The launcher verifies:

- IWBTB game folder imported correctly  
- Python & required modules installed  
- all Randomizer files present  

If something is missing, a detailed debug message is shown.

---

# 🟪 Gameplay & Modes

## ▶ Run Start
Every run begins in the **Tutorial**, then continues either:

- **Random Route Mode**, or  
- **Target Collect Mode**

depending on the GUI settings.

## 🧍 Character Randomizer
- Default: **Dark Boshy**  
- Optional:
  - random on run start  
  - random per stage  
- When enabled:  
  **F3 Character Menu is disabled** → deterministic seeds

---

## 🎯 Target Collect Mode

- Hides route sliders  
- Enables all required optional levels  
- Target selection is seed-based  
- After all targets are collected: **Solgryn spawns automatically**

### Important Logic Update  
To ensure full item access, the **only optional areas that may be turned off** are:

- **Boberman**  
- **Questionmark (?)**  
- **Ridley**

All other optional areas **must remain enabled**.

---

## 🧠 System Behaviour

- Only **SaveFile1** is used  
- **Do NOT delete SaveFile1**  
- SaveFile2/3 are always overwritten with defaults  
- Achievements & unlockables persist through the entire run  
- Teleport Room works normally — but:  
  **you must play the level the Randomizer gives you**  
  → skipping progress via teleporter is not possible

---

# 🎲 Seed System

Each seed defines:
- level & boss order  
- full route structure  
- optional character RNG  
- target item selection  

Seeds appear in:
- loading overlay  
- run start overlay  
- endscreen  
- debug log  

Seeds can be shared so others can replay identical runs.

---

# 🟫 Known Notes
- Some triggers intentionally offset for stability  
- Mods or external savefiles may interfere  

---

# 🔧 Technical

- Python **3.11**  
- Uses:
  - pygetwindow  
  - pyautogui  
  - pillow  
  - numpy  
  - tkinter  

Log file:
```
INI/randomizer_debug.log
```

Include this file when reporting bugs.

---

# 🟨 Support

**Twitch:**  
https://twitch.tv/THXel  

**Discord:**  
https://discord.gg/ZXgTFjGw

---

# ⚫ Disclaimer

This project is unofficial and not affiliated with  
**Solgryn (Grynsoft)** or any official IWBTB release.

Use at your own risk.  
**Have fun — it’s Boshy Time!**
