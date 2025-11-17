==============================================================
🧩 BOSHY RANDOMIZER
Erstellt von THXel & der I Wanna Be The Boshy Speedrun Community
© 2025 THXel
==============================================================

ÜBER:
--------------------------------------------------------------
Der Boshy Randomizer ist ein von Fans entwickeltes Zusatz-Tool
für das Spiel "I Wanna Be The Boshy" von Solgryn.

Das Programm mischt Level, Bosse, Items, Zielobjekte und Charaktere
zufällig neu und erweitert das Spiel um automatische Trigger,
Overlays, Statistiken, Seed-System und diverse Komfortfunktionen.

Entwickelt wurde es von THXel in Zusammenarbeit mit der
Boshy Speedrun Community.

⚠️ Hinweis:
Dies ist nicht das Originalspiel, sondern nur das Randomizer-Tool.
Das Spiel muss manuell hinzugefügt werden (siehe unten).


--------------------------------------------------------------
VORAUSSETZUNGEN:
--------------------------------------------------------------
• Windows 10 oder neuer
• Internetzugang (für automatische Installation beim ersten Start)


--------------------------------------------------------------
INSTALLATION UND START:
--------------------------------------------------------------
1️⃣ Lade das Originalspiel "I Wanna Be The Boshy" von:
    https://grynsoft.com/old-games

2️⃣ Starte den Boshy Randomizer Installer.
    Danach wird automatisch eine **Boshy Randomizer.exe** erstellt.

3️⃣ Starte das Tool anschließend über diese **Boshy Randomizer.exe**.

    Der Launcher prüft automatisch:
    • ob das Spiel vorhanden ist
    • ob Python und alle Module installiert sind
    • ob alle benötigten Dateien vorhanden sind

4️⃣ Fehlt das Spiel, öffnet sich ein Auswahlfenster.
    Wähle dort die ZIP-Datei des Spiels aus – sie wird automatisch
    entpackt und eingerichtet.


--------------------------------------------------------------
SPIELINFORMATIONEN
--------------------------------------------------------------

• Der Run startet immer mit dem **Tutorial**. Danach folgt –
  abhängig von den GUI-Einstellungen – eine zufällige Route
  oder der Target Collect Mode.

• Standardcharakter ist **Dark Boshy**.  
  Mit der Option „Random Character“ startet der Run mit einem
  zufälligen Charakter (optional Wechsel nach jeder Stage).

• **Wichtig:**  
  Wenn „Random Character“ aktiviert ist, wird das **Charakter-Menü (F3)
  komplett gesperrt**, damit der festgelegte Charakter nachvollziehbar bleibt.

• Beim ersten Start erscheint ein Hinweisfenster:
      – Drücke mehrmals **Strg + R**, um einen neuen Run zu starten.
      – Es wird ausschließlich **SaveFile1** verwendet.
      – SaveFile2 und SaveFile3 bleiben deaktiviert.
      – Beim Schließen des Spiels endet der Run.

• Achievements, Collectables und Unlockables bleiben über den gesamten
  Run erhalten und werden vom Randomizer nicht entfernt.

• Der Live Tracker zeigt während des Runs:
      – Achievements
      – Collectables
      – Bosse
      – Charaktere
      – Zielobjekte (Target Mode)
  und aktualisiert sich automatisch.

⚠️ **Hinweis zur Synchronität:**  
   Werte wie Items, Stats, Boss-Tode oder Target-Fortschritt können
   aus technischen Gründen **leicht verzögert** erscheinen
   (typisch 0.3–1.0 Sekunden).

• Im Target Collect Mode:
      – Die Route wird ausgeblendet.
      – Der Spieler sammelt eine festgelegte Anzahl an Zielen.
      – Alle optionalen Level werden automatisch aktiviert.
      – Gastly & Cheetahman werden verpflichtend eingeschaltet.
      – Beim Erreichen aller Ziele erscheint automatisch Solgryn.

--------------------------------------------------------------
SEED-SYSTEM
--------------------------------------------------------------
Der Randomizer unterstützt ein vollständiges **Seed-System**:

• In der GUI kann ein Seed manuell eingegeben werden.
• Alternativ erzeugt der Randomizer automatisch einen neuen Seed.
• Der Seed definiert:
      – die komplette Route (Ebenen & Bosse)
      – optional die Charakter-Reihenfolge
      – Zielobjekte (Target Collect Mode)
• Seeds lassen sich an andere Spieler weitergeben,
  damit exakt der gleiche Run erneut spielbar ist.
• Der Seed wird angezeigt:
      – beim Reset-Overlay
      – nach dem Run im Endscreen
      – im Debug-Log

--------------------------------------------------------------
BEKANNTE HINWEISE:
--------------------------------------------------------------
• Einige Triggerpunkte sind absichtlich versetzt gesetzt,
  um den Ablauf stabil zu halten.

• Mods oder externe Savefiles können überschrieben werden –
  nutze daher am besten frische Dateien.

--------------------------------------------------------------
TECHNISCHE DETAILS:
--------------------------------------------------------------
• Programmiert in Python 3.11
• Bibliotheken:
  pygetwindow, pyautogui, pillow, numpy, tkinter

• Automatische Log-Datei:
  **INI/randomizer_debug.log**

Bitte sende bei Bugs immer **deinen Debug-Log mit**, sonst kann ich
den Fehler nicht zuverlässig analysieren.

--------------------------------------------------------------
SUPPORT & COMMUNITY:
--------------------------------------------------------------
Bei Fragen, Feedback oder Bugs:
• Twitch:   https://twitch.tv/THXel
• Discord:  https://discord.gg/ZXgTFjGw  (Boshy Speedrun Discord)

--------------------------------------------------------------
HAFTUNGSAUSSCHLUSS:
--------------------------------------------------------------
Dieses Projekt ist inoffiziell und steht in keiner Verbindung zu Solgryn
oder offiziellen "I Wanna Be The Boshy"-Veröffentlichungen.

Verwendung auf eigene Gefahr.
Viel Spaß – it´s Boshy Time !
