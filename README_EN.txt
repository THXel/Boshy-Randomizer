==============================================================
🧩 BOSHY RANDOMIZER
Created by THXel & the I Wanna Be The Boshy Speedrun Community
© 2025 THXel
==============================================================

ABOUT:
--------------------------------------------------------------
The Boshy Randomizer is a fan-made companion tool for the game
"I Wanna Be The Boshy" by Solgryn.

It shuffles stages, bosses, items, target goals and characters
into new random orders, and adds automatic triggers, overlays,
statistics, a full seed system and various quality-of-life features.

Developed by THXel in collaboration with the
Boshy Speedrun Community.

⚠️ Note:
This is NOT the original game – only the Randomizer tool.
You must manually add the game files (see below).


--------------------------------------------------------------
REQUIREMENTS:
--------------------------------------------------------------
• Windows 10 or newer  
• Internet connection (for automatic first-time setup)


--------------------------------------------------------------
INSTALLATION & STARTUP:
--------------------------------------------------------------
1️⃣ Download the original "I Wanna Be The Boshy" from:
    https://grynsoft.com/old-games

2️⃣ Run the Boshy Randomizer Installer.
    After installation, a **Boshy Randomizer.exe** will be created.

3️⃣ Launch the tool using this **Boshy Randomizer.exe**.

    The launcher automatically checks:
    • whether the game is present  
    • whether Python + required modules are installed  
    • whether all Randomizer files are correctly placed  

4️⃣ If the game is missing, a file picker will appear.
    Select the original ZIP file — it will be extracted and
    installed automatically.


--------------------------------------------------------------
GAME INFORMATION
--------------------------------------------------------------

• Runs always begin with the **Tutorial**.
  Afterwards you continue based on your GUI settings:
  either a randomized route or the Target Collect Mode.

• Default character is **Dark Boshy**.  
  Enabling “Random Character” starts you as a random character  
  (optionally switching after each stage).

• **Important:**  
  When Random Character mode is enabled, the **F3 Character Menu is locked**,  
  ensuring the run remains consistent with the selected random seed.

• On first startup you will see a small info window:
      – Press **Ctrl + R** repeatedly to start a fresh run.  
      – Only **SaveFile1** is used.  
      – SaveFile2 and SaveFile3 stay disabled.  
      – Closing the game ends the run.

• Achievements, Collectables and Unlockables remain persistent
  throughout the entire run.

• The Live Tracker automatically displays:
      – Achievements  
      – Collectables  
      – Bosses  
      – Characters  
      – Target items (if Target Mode is active)  

  Pop-up notifications appear when new items/achievements are found.

⚠️ **Synchronization Notice:**  
   Stats, items, boss deaths or target progress may update
   with a slight delay (typically 0.3–1.0 seconds)
   due to engine limitations.

• In Target Collect Mode:
      – The regular route selection is hidden  
      – All optional levels are enabled  
      – Gastly & Cheetahman are forced ON  
      – You must collect a specific amount of targets  
      – After completing all targets, Solgryn is automatically triggered
        as the final boss


--------------------------------------------------------------
SEED SYSTEM
--------------------------------------------------------------
The Randomizer features a full seed system:

• You can manually enter a seed in the GUI  
• Or let the tool generate a new seed automatically  

A seed determines:
      – the entire stage/boss route  
      – optional character order  
      – target goals in Target Collect Mode  

Seeds can be shared with other players to reproduce
the exact same run.

The seed is displayed:
      – in the reset overlay  
      – during stage loading  
      – after the run in the end screen  
      – inside the debug log  


--------------------------------------------------------------
KNOWN NOTES:
--------------------------------------------------------------
• Some trigger regions are intentionally offset to ensure
  stable and predictable behavior.

• Custom mods or external savefiles may be overwritten
  — use clean game files when possible.


--------------------------------------------------------------
TECHNICAL DETAILS:
--------------------------------------------------------------
• Written in Python 3.11  
• Libraries used:
  tkinter, pillow, numpy, pygetwindow, pyautogui  

• Automatic logging:
  **INI/randomizer_debug.log**

When reporting bugs, **please always include your debug log**,  
as issues cannot be diagnosed without it.


--------------------------------------------------------------
SUPPORT & COMMUNITY:
--------------------------------------------------------------
For questions, feedback or bug reports:
• Twitch:   https://twitch.tv/THXel  
• Discord:  https://discord.gg/ZXgTFjGw  (Boshy Speedrun Discord)  


--------------------------------------------------------------
DISCLAIMER:
--------------------------------------------------------------
This project is unofficial and not affiliated with Solgryn
or any official "I Wanna Be The Boshy" releases.

Use at your own risk.  
Have fun – it’s Boshy Time!
