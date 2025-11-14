==============================================================
🧩 BOSHY RANDOMIZER
Erstellt von THXel & der I Wanna Be The Boshy Speedrun Community
© 2025 THXel
==============================================================

ÜBER:
--------------------------------------------------------------
Der Boshy Randomizer ist ein von Fans entwickeltes Zusatz-Tool
für das Spiel "I Wanna Be The Boshy" von Solgryn.

Das Programm mischt Level, Bosse, Items und Charaktere
zufällig neu und erweitert das Spiel um automatische Trigger,
Overlays und Statistiken.  
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
1️⃣ Lade das Originalspiel "I Wanna Be The Boshy" von  
   https://grynsoft.com/old-games  

2️⃣ Starte den Boshy Randomizer Installer.  
   Nach der Installation wird im selben Ordner automatisch  
   eine **Boshy Randomizer.exe** erstellt.  

3️⃣ Starte das Tool anschließend über diese **Boshy Randomizer.exe**.  

   Der Launcher prüft automatisch:
   • ob das Spiel vorhanden ist  
   • ob Python und alle Module installiert sind  
   • und ob alle benötigten Dateien vorhanden sind  

4️⃣ Fehlt das Spiel, öffnet sich ein Auswahlfenster.  
   Du kannst dort direkt die ZIP-Datei des Spiels auswählen.  
   Sie wird automatisch in den Ordner /IWBTB entpackt.

--------------------------------------------------------------
SPIELINFORMATIONEN
--------------------------------------------------------------

• Der Run startet immer mit dem **Tutorial**. Danach folgt –
  abhängig von deinen GUI-Einstellungen – eine zufällige Route
  oder der Target Collect Mode.

• Standardmäßig spielst du als **Dark Boshy**.  
  Wenn du in der GUI „Random Character“ aktivierst, startest du stattdessen
  als zufälliger Charakter (optional: Charakterwechsel pro Level/Boss).

• Beim ersten Start erscheint ein kleines Hinweisfenster:
      – Drücke **Strg + R**, um einen neuen Run zu starten.
      – Es wird ausschließlich **SaveFile1** verwendet.
      – SaveFile2 und SaveFile3 bleiben deaktiviert.
      – Wenn du das Spiel schließt, gilt der aktuelle Run als beendet.

• **Achievements bleiben im gesamten Run erhalten.**
  Nichts wird entfernt oder zurückgesetzt – egal welche Route du spielst.

• Die Triggerpunkte sind so gesetzt, dass sie möglichst stabil feuern.
  Manche Bereiche (z. B. Miniboss-Zonen) sind daher in zwei Abschnitte
  geteilt, um den Fortschritt korrekt zu erfassen.

• Das Item **Awesomesauce** ist zu Beginn im Save aktiviert, damit
  alle Collectables – insbesondere **Gastly** – immer erreichbar sind.

• Wenn ein Trigger einmal nicht direkt auslöst:
      – Spiele einfach weiter (Boss/Level abschließen).
      – Das System fängt sich selbst, sobald der nächste Trigger
        oder Abschnitt geladen wird.
      – Falls du wiederholt etwas Auffälliges bemerkst, gib bitte Feedback.

• Der **Live Tracker** zeigt während des Runs automatisch:
      – Achievements  
      – Collectables  
      – Bosse  
      – Charaktere  
      – Target Items (falls Target Mode aktiv ist)  
  Zusätzlich erscheinen kleine Pop-up-Meldungen bei jedem neuen Fund.

• Im **Target Collect Mode**:
      – Die normale Route-Auswahl wird ausgeblendet.
      – Du sammelst die festgelegte Anzahl an Items/Charakteren.
      – Alle optionalen Levels werden automatisch aktiviert.
      – Gastly & Cheetahman werden verpflichtend eingeschaltet.
      – Sobald du alle Ziele gefunden hast, erscheint automatisch Solgryn
        als finaler Endboss.

--------------------------------------------------------------
BEKANNTE HINWEISE:
--------------------------------------------------------------
• Einige Triggerpunkte sind absichtlich leicht versetzt, um
  das Zufallssystem stabil zu halten.  

• Falls du eigene Mods oder Savefiles nutzt, achte darauf, dass sie
  nicht vom Randomizer überschrieben werden.  

--------------------------------------------------------------
TECHNISCHE DETAILS:
--------------------------------------------------------------
• Programmiert in Python 3.11  
• Verwendete Bibliotheken:
  pygetwindow, pyautogui, pillow, numpy, tkinter  

• Automatisches Logging aller Ereignisse in:
  INI/randomizer_debug.log  

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
Viel Spaß – und pass auf, dass du nicht boshy’d wirst!
