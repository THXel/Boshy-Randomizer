==============================================================
🧩 BOSHY RANDOMIZER
Created by THXel & the I Wanna Be The Boshy Speedrun Community
© 2025 THXel
==============================================================

ABOUT:
--------------------------------------------------------------
The Boshy Randomizer is a fan-made tool for the game
"I Wanna Be The Boshy" by Solgryn.

It randomizes levels, bosses, items and characters,
and adds automatic triggers, overlays, and statistics.  
Developed by THXel in collaboration with the
Boshy Speedrun Community.

⚠️ Note:  
This is not the original game, only the Randomizer tool.
The game itself must be added manually (see below).

--------------------------------------------------------------
REQUIREMENTS:
--------------------------------------------------------------
• Windows 10 or newer  
• Internet connection (for automatic setup on first start)  

--------------------------------------------------------------
INSTALLATION & START:
--------------------------------------------------------------
1️⃣ Download the original "I Wanna Be The Boshy" from  
   https://grynsoft.com/old-games  

2️⃣ Run the Boshy Randomizer Installer.  
   After installation, a **Boshy Randomizer.exe**  
   will automatically appear in the same folder.  

3️⃣ Start the tool via **Boshy Randomizer.exe**.  

   The launcher automatically checks:  
   • if the game is installed  
   • if Python and all required modules are present  
   • and if all necessary files exist  

4️⃣ If the game is missing, a file selection window will appear.  
   Simply select the ZIP of the original game.  
   It will automatically be extracted to `/IWBTB`.

--------------------------------------------------------------
GAME INFORMATION
--------------------------------------------------------------

• The run always begins with the **Tutorial**. After that,
  depending on your GUI settings, you will either get a random route
  or the Target Collect Mode.

• By default, you play as **Dark Boshy**.
  If you enable “Random Character” in the GUI, you will instead start
  as a random character (optional: character change per level/boss).

• On first startup, a small hint window will appear:
      – Press **Ctrl + R** to start a new run.
      – Only **SaveFile1** is used.
      – SaveFile2 and SaveFile3 remain disabled.
      – Closing the game counts as ending the current run.

• **Achievements persist for the entire run.**
  Nothing is removed or reset — no matter which route you play.

• Trigger points are placed to be as stable as possible.
  Certain areas (e.g., miniboss zones) are split into two sections
  to accurately track progress.

• The item **Awesomesauce** is activated from the start to ensure
  that all collectables — especially **Gastly** — are always obtainable.

• If a trigger does not activate immediately:
      – Simply continue playing (finish the boss/level).
      – The system will recover as soon as the next trigger
        or segment is loaded.
      – If you repeatedly notice something unusual, please report it.

• The **Live Tracker** automatically shows during the run:
      – Achievements
      – Collectables
      – Bosses
      – Characters
      – Target Items (if Target Mode is active)
  Additionally, small pop-up messages appear for each new find.

• In **Target Collect Mode**:
      – The normal route selection is hidden.
      – You collect the required number of items/characters.
      – All optional levels are enabled automatically.
      – Gastly & Cheetahman are forced on.
      – After collecting all targets, Solgryn appears
        automatically as the final boss.

--------------------------------------------------------------
KNOWN NOTES:
--------------------------------------------------------------
• Some trigger points are intentionally offset to maintain  
  stability within the randomization system.  

• If you use custom mods or savefiles, make sure they are not  
  overwritten by the Randomizer.  

--------------------------------------------------------------
TECHNICAL DETAILS:
--------------------------------------------------------------
• Developed in Python 3.11  
• Libraries used:
  pygetwindow, pyautogui, pillow, numpy, tkinter  

• Automatic event logging:
  INI/randomizer_debug.log  

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
Have fun – and don’t get boshy’d!
