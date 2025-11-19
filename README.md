<div align="center">

  <img src="Custom/boshy_randomizer.png?raw=true" alt="Boshy Randomizer" width="420">

  <p><strong>Created by THXel &amp; the I Wanna Be The Boshy Speedrun Community</strong><br>
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
  <a href="#-gameplay--modes">Gameplay &amp; Modes</a> •
  <a href="#-technical">Technical</a> •
  <a href="#-support">Support</a>
</p>

---

## 🟦 Features

- 🎲 **Random Routes** – Levels & bosses shuffled every run  
- 🧩 **Item & Collectable Handling** – trigger-stable routing  
- 🧍 **Random Characters** – start or per stage  
- 🎯 **Target Collect Mode** – play until all targets are collected  
- 📊 **Live Tracker** – achievements, items, bosses & more  
- 🧾 **Endscreen Stats** – run summary with seed code  
- 🧪 **Deterministic Seeds** – share & replay routes  

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
- Internet connection (initial setup only)  
- You must provide your own copy of **I Wanna Be The Boshy**

---

## 🟧 Installation

### 1️⃣ Download the Installer

[⬇️ **Download Boshy Randomizer Installer**](https://github.com/THXel/Boshy-Randomizer/releases/latest/download/Boshy%20Randomizer%20installer.exe)

*(Windows only — requires the original “I Wanna Be The Boshy” game.)*

---

### 2️⃣ Download the Original Game  
You must download the original game from the official Grynsoft website:

👉 https://grynsoft.com/old-games  

This will give you the **I Wanna Be The Boshy ZIP file**, which the installer will import automatically.

---

### 3️⃣ Install the Randomizer  

1. Run **Boshy Randomizer installer.exe**
2. Follow the installation wizard:
   - Choose the installation directory  
   - Accept the license  
   - The installer will automatically:
     - 📁 Copy all Randomizer files  
     - 📦 Ask for your **Boshy ZIP** and extract it into `/IWBTB`  
     - 🐍 Check for **Python 3.x** (and install it if missing)  
     - 🔧 Install all required Python modules  
     - 🔤 Install the **“its-boshy-time”** font  
     - 📌 Create Start Menu shortcuts  

After installation, you will find:

- **Boshy Randomizer** (launcher)
- **Uninstall Boshy Randomizer**

in the Windows Start Menu.

---

### 4️⃣ Launch the Randomizer  

Start **Boshy Randomizer.exe** from the Start Menu.

When launched, the Randomizer automatically verifies:

- ✔ The original IWBTB game was extracted correctly  
- ✔ Python & all modules are installed  
- ✔ All necessary Randomizer files are present  

If something is missing, the launcher will show a detailed debug message.

---

### 5️⃣ Missing the Game Files? 5️⃣ 

If you haven't imported the game yet:

- The installer (or launcher) will prompt you to select your **I Wanna Be The Boshy ZIP**  
- It will automatically extract the internal `IWBTB` folder into:  
  `...\Boshy Randomizer\IWBTB\`
- The Randomizer will not start until the game is successfully imported  

Once completed, you can immediately start your first randomized run 🎮

---

## 🟪 Gameplay & Modes

### ▶ Start of a Run
- Runs always begin in the **Tutorial**
- Then either:
  - **Random Route Mode**, or  
  - **Target Collect Mode**

---

### 🧍 Character Randomizer
- Default character: **Dark Boshy**
- Optional:
  - Random at run start  
  - Random per boss/level  

> 🔒 While Random Character mode is active,  
> the in-game character menu **F3 is disabled**  
> to keep seeds 100% deterministic.

---

### 🎯 Target Collect Mode
- Hides route sliders  
- Activates all optional levels  
- Forces **Gastly** & **Cheetahman**  
- Target items are chosen deterministically via your seed  
- After all targets are collected, **Solgryn** spawns as final boss

---

### 🧠 System Behaviour
- Achievements persist for the entire run  
- Trigger zones tuned for stability  
- Awesomesauce enabled by default for full item accessibility  

If a trigger doesn’t fire immediately:
- just continue playing  
- the system will auto-resync  
- for repeated issues → please send `INI/randomizer_debug.log`

⏱ Sync of items, stats & Target Collect may lag slightly (export loop).

---

## 🎲 Seed System

Every seed encodes:

- Route structure  
- Character RNG  
- Target Collect RNG  

The seed is displayed in:

- Start overlay  
- Loading overlay  
- Endscreen  
- Debug log  

You can share the full **route code** so others can replay the exact run.

---

## 🟫 Known Notes
- Some triggers intentionally offset for stability  
- Custom mods / savefiles may conflict with Randomizer files  

---

## 🔧 Technical
- Python **3.11**  
- Libraries:
  - `pygetwindow`
  - `pyautogui`
  - `pillow`
  - `numpy`
  - `tkinter`

- Debug logs:
  - `INI/randomizer_debug.log`  

Please attach this file when reporting bugs.

---

## 🟨 Support

**Twitch**  
https://twitch.tv/THXel  

**Discord**  
https://discord.gg/ZXgTFjGw  
*(I Wanna Be The Boshy Speedrun Community)*

---

## ⚫ Disclaimer

This is an unofficial fan project and is not affiliated with  
**Solgryn (Grynsoft)** or any official *I Wanna Be The Boshy* releases.

Use at your own risk.  
**Have fun – it’s Boshy Time!** 😈
