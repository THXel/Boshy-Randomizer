<div align="center">

  <img src="Custom/boshy_randomizer.png" alt="Boshy Randomizer" width="500">

  <p><strong>Created by THXel & the I Wanna Be The Boshy Speedrun Community</strong><br>
  © 2025 THXel</p>

</div>

---

# 🎮 **Boshy Randomizer**
> **Modern • Fast • Fully Automated**  
> Powerful randomizer for *I Wanna Be The Boshy*

✔️ Random Levels & Bosses  
✔️ Random Characters (with F3-lock)  
✔️ Item & Collectable Randomizer  
✔️ Live Tracker Overlay  
✔️ Route Seeds (shareable & reproducible)  
✔️ Automatic triggers, overlays & progress tracking  

---

# 🖼️ **Screenshots**

<div align="center">

### 🟦 GUI — Main Screen
<img src="Custom/GUI1.png" width="650">

### 🟩 GUI — Settings & Seed Options
<img src="Custom/GUI2.png" width="650">

### 🟪 Live Tracker
<img src="Custom/livetracker.png" width="650">

</div>

---

# 🟦 **About**
The **Boshy Randomizer** is a fan-made enhancement tool for  
**I Wanna Be The Boshy** by Solgryn.  

It randomizes gameplay elements and adds advanced automated systems:

- Segment triggers  
- Live overlays  
- Statistics & endscreen  
- Route seeds  
- Character RNG  
- Target Collect Mode  
- Automated setup & validation  

> ⚠ **Important:**  
> This is *not* the original game — only a randomizer tool.  
> You must add the game manually during setup.

---

# 🟩 **Requirements**
- Windows 10 or newer  
- Internet connection (first startup only)

---

# 🟧 **Installation & Startup**

### **1️⃣ Download the original game**
https://grynsoft.com/old-games

---

### **2️⃣ Install the Randomizer**
Run the installer → it will generate the file  
**Boshy Randomizer.exe**

---

### **3️⃣ Launch**
When opening the Randomizer, it automatically checks:

✔ Game installed  
✔ Python installed  
✔ All modules available  
✔ All Randomizer files exist  

---

### **4️⃣ If the game is missing**
A file dialog appears.  
Select the downloaded ZIP → it will auto-extract into `/IWBTB`.

---

# 🟪 **Game Information**

## ⭐ Starting the Run
Every run begins in the **Tutorial**, then proceeds based on your GUI settings:

- Random Route  
- or Target Collect Mode  

---

## ⭐ Character Randomizer
- Default character: **Dark Boshy**  
- Optionally: random character  
  - Choose once at start  
  - or new character every boss/level  

✔ When Random Character is active,  
  **the F3 in-game character menu is locked**  
  (to maintain seed reproducibility)

---

## ⭐ First-Time Notes
- Press **Ctrl + R** multiple times to start/reset a run  
- Only **SaveFile1** is used  
- SaveFile2 & SaveFile3 are disabled  
- Closing the game ends the run  

---

## ⭐ System Behavior
- Achievements persist for the entire run  
- Trigger zones are optimized for stability  
- Some areas are split for accurate detection  
- Awesomesauce is always active (for Gastly/collectables)

---

## ⭐ If a Trigger Fails
Just keep playing — the system will catch up automatically.

If you encounter bugs:  
📩 **Please send your `randomizer_debug.log`** (located in /INI).

---

## ⭐ Live Tracker Displays:
- Achievements  
- Collectables  
- Bosses  
- Characters  
- Target items  

Also includes real-time popup notifications.

⚠ Sync may be slightly delayed (0.3–1s) due to exporter timing.

---

# 🟥 **Target Collect Mode**
- Hides the standard route settings  
- Automatically activates all optional levels  
- Forces **Gastly** and **Cheetahman**  
- Generates deterministic target lists (seed-based)  
- Solgryn becomes final boss once all targets are collected  

---

# 🟦 **Seed System**
Seeds determine:

- Full level/boss route  
- Character RNG  
- Target Collect Mode RNG  
- Route reproducibility  

Seeds appear:

- In the reset overlay  
- During level loading  
- In the Endscreen  
- In the debug log  

You can share seeds with friends to compare runs 🔥

---

# 🟫 **Known Notes**
- Triggers are slightly offset intentionally for stability  
- Mods or modified savefiles may conflict with Randomizer writes  

---

# 🔧 **Technical Details**
- Python **3.11**
- Libraries:
  - `pygetwindow`
  - `pyautogui`
  - `pillow`
  - `numpy`
  - `tkinter`

- Debug log:
  **INI/randomizer_debug.log**

When reporting bugs → **attach the debug log**.

---

# 🟨 **Support & Community**

### Twitch  
https://twitch.tv/THXel  

### Discord  
https://discord.gg/ZXgTFjGw  
*(I Wanna Be The Boshy Speedrun Community)*

---

# ⚫ **Disclaimer**
This project is unofficial and not affiliated with Solgryn  
or any official *I Wanna Be The Boshy* releases.

Use at your own risk.  
**Have fun — It’s Boshy Time!** 😈
