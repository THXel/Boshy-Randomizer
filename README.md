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

### 1️⃣ Download the Original Game
> https://grynsoft.com/old-games

---

### 2️⃣ Install the Randomizer  
After installation, **Boshy Randomizer.exe** appears automatically.

---

### 3️⃣ Launch  
The launcher automatically checks:

- ✔ Game installed  
- ✔ Python & dependencies  
- ✔ All Randomizer files exist  

---

### 4️⃣ Missing Game?  
You will be prompted to select the game ZIP.  
It will be extracted automatically into `/IWBTB`.

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
