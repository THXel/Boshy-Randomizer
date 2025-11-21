==============================================================
                    BOSHY RANDOMIZER
           Created by THXel & the Boshy Community
                      © 2025 THXel
==============================================================

Modern Randomizer for "I Wanna Be The Boshy"
Random Routes • Live Tracker • Route Seeds • Clean GUI

--------------------------------------------------------------
FEATURES
--------------------------------------------------------------
• Random Routes – Levels & bosses shuffled every run
• Item & Collectable Handling – trigger-stable routing
• Random Characters – on run start or per stage
• Target Collect Mode – collect all targets, route hidden
• Live Tracker – achievements, items, bosses, characters
• Endscreen Stats – summary with route code
• Deterministic Seeds – replay the exact same run
• Auto-Setup System – Python, modules, fonts, game import

--------------------------------------------------------------
REQUIREMENTS
--------------------------------------------------------------
• Windows 10 or newer
• Internet connection for the first setup
• A legal copy of "I Wanna Be The Boshy" (ZIP from Grynsoft)

--------------------------------------------------------------
DOWNLOAD & INSTALLATION
--------------------------------------------------------------

Download ZIP:
https://github.com/THXel/Boshy-Randomizer/archive/refs/heads/Boshy-Randomizer.zip

1) Download the ZIP file above.

2) Extract the ZIP anywhere you want, for example:
   C:\Games\Boshy Randomizer\

   After extraction, your folder should look like this:

      Boshy Randomizer/
       ├─ Custom/
       ├─ INI/
       ├─ PY/
       ├─ Installer Files...
       └─ Boshy Randomizer Installer.exe

3) Run the installer:
   Boshy Randomizer Installer.exe

   The installer will:
   • copy all Randomizer files
   • install Python 3.x if missing
   • install all required modules
   • install the “its-boshy-time” font
   • ask for your IWBTB ZIP
   • extract the IWBTB game into /IWBTB
   • create Start Menu shortcuts

4) Start the Randomizer:
   Start Menu → Boshy Randomizer

   The launcher checks:
   • IWBTB folder imported correctly
   • Python installation
   • required modules
   • all Randomizer files

   If something is missing, a debug message will appear.

--------------------------------------------------------------
GAMEPLAY & MODES
--------------------------------------------------------------

RUN START
• Every run begins in the Tutorial.
• After that, depending on the GUI settings:
  – Random Route Mode
  – Target Collect Mode

CHARACTER RANDOMIZER
• Default character: Dark Boshy
• Optional:
  – random on run start
  – random per stage
• When Random Character mode is active:
  The F3 Character Menu is disabled.

--------------------------------------------------------------
TARGET COLLECT MODE
--------------------------------------------------------------

• Hides route controls.
• Enables all optional levels required for item access.
• Target selection is based on your seed.
• After all targets are collected:
  Solgryn spawns automatically.

IMPORTANT LOGIC:
Only these optional areas may be turned off:
• Boberman
• Questionmark (?)
• Ridley

All other optional areas must stay enabled to reach all items.

--------------------------------------------------------------
SYSTEM BEHAVIOUR
--------------------------------------------------------------

• Only SaveFile1 is used.
• Do NOT delete SaveFile1.
• SaveFile2 and SaveFile3 are always overwritten.
• Achievements and unlockables persist the entire run.
• The Teleport Room works normally, BUT:
  To progress the run, you must play the level the Randomizer gives you.
  Skipping parts of the route via teleporter is not possible.

--------------------------------------------------------------
SEED SYSTEM
--------------------------------------------------------------

A seed defines:
• level & boss order
• full route structure
• optional character RNG
• target item selection

Seeds are shown in:
• loading overlay
• run start overlay
• endscreen
• debug log

Seeds can be shared to replay identical runs.

--------------------------------------------------------------
KNOWN NOTES
--------------------------------------------------------------

• Some triggers are intentionally offset for stability.
• Mods or external savefiles may conflict with the Randomizer.

--------------------------------------------------------------
TECHNICAL
--------------------------------------------------------------

• Python 3.11
• Libraries used:
  pygetwindow, pyautogui, pillow, numpy, tkinter

Debug log:
INI/randomizer_debug.log

--------------------------------------------------------------
SUPPORT
--------------------------------------------------------------

Twitch:
https://twitch.tv/THXel

Discord:
https://discord.gg/ZXgTFjGw

--------------------------------------------------------------
DISCLAIMER
--------------------------------------------------------------

This project is unofficial and not affiliated with
Solgryn (Grynsoft) or any official IWBTB release.

Use at your own risk.
Have fun — it's Boshy Time!
--------------------------------------------------------------
