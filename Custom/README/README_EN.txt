==============================================================
                        BOSHY RANDOMIZER
        Created by THXel & the Boshy Speedrun Community
                          © 2025 THXel
==============================================================

Modern randomizer for "I Wanna Be The Boshy"
Random Routes • Seed Codes • ER/EB Masks • Live Tracker

--------------------------------------------------------------
FEATURES
--------------------------------------------------------------
• Randomized level & boss order (deterministic per seed)
• Target Collect Mode – hidden route, seed-based targets
• Character Randomizer – random on start or per stage
• Item Randomizer – safe stats mode (prevents game crashes)
• Live Tracker – items, bosses, achievements, characters, targets
• Endscreen stats + route code
• Seed-Lock – GUI settings automatically applied when loading a seed
• Fully automated setup & IWBTB import

--------------------------------------------------------------
REQUIREMENTS
--------------------------------------------------------------
• Windows 10 or newer
• Internet connection for first-time setup
• Original IWBTB ZIP (from Grynsoft)

--------------------------------------------------------------
INSTALLATION
--------------------------------------------------------------
1) Download the installer:
   https://github.com/THXel/Boshy-Randomizer/raw/refs/heads/Boshy-Randomizer/Boshy%20Randomizer%20installer.exe

2) Run the installer:
      Boshy Randomizer Installer.exe

   Note: SmartScreen may warn you.
   Click:
      "More information" → "Run anyway"

3) The installer automatically:
   • copies all Randomizer files
   • installs Python 3 if needed
   • installs required Python modules
   • installs the “It's-Boshy-Time” font
   • imports the IWBTB ZIP into /IWBTB
   • creates Start Menu shortcuts

4) Launch:
      Start Menu → Boshy Randomizer

--------------------------------------------------------------
GAMEPLAY & MODES
--------------------------------------------------------------

RUN START
• Every run begins in the Tutorial.
• After that, depending on GUI settings:
     - Random Route Mode
     - Target Collect Mode

SYSTEM BEHAVIOR
• Only SaveFile1 is used.
• Do NOT delete SaveFile1.
• SaveFile2/3 are reset every run.
• Achievements & unlockables persist for the entire run.
• Awesomesauce is always available from the start → ensures Gastly unlock.
• Teleport Room works, but:
     You MUST play the level assigned by the Randomizer.
     Skipping is not possible.

--------------------------------------------------------------
CHARACTER RANDOMIZER
--------------------------------------------------------------
• Default character: Dark Boshy
• Optional:
     - Random on run start
     - Random per stage
• When active:
     F3 Character Menu is disabled (to ensure deterministic seeds)

--------------------------------------------------------------
ITEM RANDOMIZER (SAFE MODE)
--------------------------------------------------------------
• IWBTB crashes if in-game items are replaced.
• Therefore:
     ✔ Only collected characters are randomized
     ✔ Items remain unchanged in gameplay
     ✔ Randomization appears only in the Stats screen
• Completely stable and safe for routing.

--------------------------------------------------------------
TARGET COLLECT MODE
--------------------------------------------------------------
• Route is hidden
• Targets are determined by the seed
• After all targets are collected → Solgryn appears automatically

OPTIONAL AREAS YOU MAY DISABLE:
• Boberman
• ?
• Ridley

All other optional areas must remain enabled.

--------------------------------------------------------------
LIVE TRACKER
--------------------------------------------------------------
Tracks in real time:
• Items
• Achievements
• Bosses
• Characters
• Progression
• In Target Collect Mode: the required Target Items

Fully automatic — no input required.

--------------------------------------------------------------
SEED SYSTEM
--------------------------------------------------------------
Example:
   R14-B4-T0-C2-P1-S152722-ER5-EB34C

Meaning:
• R  – number of levels
• B  – number of bosses
• T  – Target Collect (0/1)
• C  – Character Randomizer mode
• P  – Item Randomizer mode
• S  – seed value
• ER – optional level mask
• EB – optional boss mask

Anyone using the seed will get the exact same run.

--------------------------------------------------------------
TECHNICAL
--------------------------------------------------------------
• Python 3.11
• Modules: pygetwindow, pyautogui, pillow, numpy, tkinter

Log file:
   INI/randomizer_debug.log

--------------------------------------------------------------
SUPPORT
--------------------------------------------------------------
Twitch:   https://twitch.tv/THXel
Discord:  https://discord.gg/ZXgTFjGw

--------------------------------------------------------------
DISCLAIMER
--------------------------------------------------------------
Unofficial project.
Not affiliated with Solgryn (Grynsoft) or IWBTB.
Use at your own risk.
Have fun — It’s Boshy Time!
==============================================================
