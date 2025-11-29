==============================================================
                        BOSHY RANDOMIZER
         Erstellt von THXel & der Boshy Speedrun Community
                          © 2025 THXel
==============================================================

Moderner Randomizer für "I Wanna Be The Boshy"
Zufällige Routen • Seed-Codes • ER/EB Masken • Live Tracker

--------------------------------------------------------------
FEATURES
--------------------------------------------------------------
• Zufällige Level- und Bossreihenfolge (deterministisch per Seed)
• Target Collect Mode – versteckte Route, Ziele basierend auf Seed
• Character Randomizer – zufällig beim Start oder pro Stage
• Item Randomizer – sicherer Stats-Modus (keine Game-Crashes)
• Live Tracker – Items, Bosse, Achievements, Charaktere, Targets
• Endscreen-Stats + Route-Code
• Seed-Lock – GUI-Optionen werden beim Seed-Laden automatisch gesetzt
• Vollautomatische Installation & Game-Import

--------------------------------------------------------------
SYSTEMVORAUSSETZUNGEN
--------------------------------------------------------------
• Windows 10 oder neuer
• Internetverbindung für das erste Setup
• Originale IWBTB ZIP-Datei (Grynsoft)

--------------------------------------------------------------
INSTALLATION
--------------------------------------------------------------
1) Installer herunterladen:
   https://github.com/THXel/Boshy-Randomizer/raw/refs/heads/Boshy-Randomizer/Boshy%20Randomizer%20installer.exe

2) Installationsprogramm ausführen:
      Boshy Randomizer Installer.exe

   Hinweis: SmartScreen kann warnen.
   Klicke:
      „Weitere Informationen“ → „Trotzdem ausführen“.

3) Der Installer führt automatisch aus:
   • Kopieren aller Dateien
   • Installation von Python 3 (falls nötig)
   • Installation aller Python-Module
   • Installation der Schriftart It’s-Boshy-Time
   • Import des IWBTB ZIP nach /IWBTB
   • Erstellung von Startmenü-Verknüpfungen

4) Start:
      Startmenü → Boshy Randomizer

--------------------------------------------------------------
GAMEPLAY & MODI
--------------------------------------------------------------

RUN-START
• Jeder Run beginnt im Tutorial.
• Danach abhängig von der GUI:
     - Zufällige Route
     - Target Collect Mode

SYSTEMVERHALTEN
• Es wird ausschließlich SaveFile1 verwendet.
• SaveFile1 darf NICHT gelöscht werden.
• SaveFile2/3 werden jedes Mal zurückgesetzt.
• Achievements & Unlockables bleiben für den gesamten Run erhalten.
• Awesomesauce ist immer zu Beginn verfügbar → garantiertes Gastly.
• Teleport-Raum funktioniert, aber:
     Du MUSST das Level spielen, das der Randomizer vorgibt.
     Überspringen ist nicht möglich.

--------------------------------------------------------------
CHARACTER RANDOMIZER
--------------------------------------------------------------
• Standardcharakter: Dark Boshy
• Optional:
     - Zufällig bei Run-Start
     - Zufällig pro Stage
• Wenn aktiv:
     F3-Charaktermenü ist deaktiviert (Seed-Konsistenz).

--------------------------------------------------------------
ITEM RANDOMIZER (SICHERER MODUS)
--------------------------------------------------------------
• Das Spiel stürzt ab, wenn Items direkt im Level ersetzt werden.
• Daher:
     ✔ Nur eingesammelte Charaktere werden gerandomized
     ✔ Items bleiben im Gameplay unverändert
     ✔ Randomisierung erscheint nur in den Stats
• Komplett stabil & routing-sicher.

--------------------------------------------------------------
TARGET COLLECT MODE
--------------------------------------------------------------
• Route ist versteckt
• Zielauswahl basiert auf dem Seed
• Alle Targets gesammelt → Solgryn erscheint automatisch

AUSNAHMEN (diese Level dürfen deaktiviert werden):
• Boberman
• „?“
• Ridley

Alle anderen optionalen Level müssen aktiviert sein.

--------------------------------------------------------------
LIVE TRACKER
--------------------------------------------------------------
Verfolgt in Echtzeit:
• Items
• Achievements
• Bosse
• Charaktere
• Fortschritt
• Im Target Collect Mode: die nötigen Target-Items

Automatisch – keine Eingabe erforderlich.

--------------------------------------------------------------
SEED-SYSTEM
--------------------------------------------------------------
Beispiel:
   R14-B4-T0-C2-P1-S152722-ER5-EB34C

Bedeutung:
• R  – Anzahl Level
• B  – Anzahl Bosse
• T  – Target Collect (0/1)
• C  – Charaktermodus
• P  – Item-Randomizer-Modus
• S  – Seed-Wert
• ER – Level-Maske (optional an/aus)
• EB – Boss-Maske (optional an/aus)

Mit einem Seed-Code kann jeder Spieler den Run 1:1 reproduzieren.

--------------------------------------------------------------
TECHNISCHES
--------------------------------------------------------------
• Python 3.11
• Module: pygetwindow, pyautogui, pillow, numpy, tkinter

Log-Datei:
   INI/randomizer_debug.log

--------------------------------------------------------------
SUPPORT
--------------------------------------------------------------
Twitch:   https://twitch.tv/THXel
Discord:  https://discord.gg/ZXgTFjGw

--------------------------------------------------------------
HAFTUNGSAUSSCHLUSS
--------------------------------------------------------------
Inoffizielles Projekt.
Nicht verbunden mit Solgryn (Grynsoft) oder IWBTB.
Nutzung auf eigene Gefahr.
Viel Spaß — It’s Boshy Time!
==============================================================
