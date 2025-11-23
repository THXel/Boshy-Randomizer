<p align="right">
  <strong>Language:</strong><br>
  <a href="../README.md" title="English">🇬🇧 English</a> ·
  <a href="README_DE.md" title="Deutsch"><strong>🇩🇪 Deutsch</strong></a> ·
  <a href="README_RU.md" title="Русский">🇷🇺 Русский</a> ·
  <a href="README_ES.md" title="Español">🇪🇸 Español</a> ·
  <a href="README_JP.md" title="日本語">🇯🇵 日本語</a>
</p>

<div align="center">

  <img src="Custom/boshy_randomizer.png?raw=true" alt="Boshy Randomizer" width="420">

  <p><strong>Erstellt von THXel & der I Wanna Be The Boshy Speedrun Community</strong><br>
  © 2025 THXel</p>

</div>

---

<p align="center">
  <b>Moderner Randomizer für <i>I Wanna Be The Boshy</i></b><br>
  Zufällige Routen • Live-Tracker • Routen-Seeds • Aufgeräumte GUI
</p>

<p align="center">
  <a href="#-features">Features</a> •
  <a href="#-installation">Installation</a> •
  <a href="#-gameplay--modes">Gameplay & Modes</a> •
  <a href="#-technical">Technical</a> •
  <a href="#-support">Support</a>
</p>

---

## 🟦 Features

- 🎲 **Random Routes** – Level- & Boss-Reihenfolge wird bei jedem Run neu gemischt  
- 🧩 **Item- & Collectable-Handling** – trigger-stabile Routenlogik  
- 🧍 **Random Characters** – zufällige Charaktere beim Start oder pro Stage  
- 🎯 **Target Collect Mode** – Route versteckt, sammle alle Ziel-Items  
- 📊 **Live Tracker** – Achievements, Items, Bosse, Charaktere  
- 🧾 **Endscreen Stats** – Zusammenfassung + Route-Code  
- 🔁 **Deterministische Seeds** – Runs teilen & identisch nachspielen  
- ⚙️ **Auto-Setup-System** – Python, Module, Fonts, Game-Import  

---

## 🎮 Gameplay Preview

<div align="center">
  <img src="Custom/gameplay.gif?raw=true" width="300">
</div>

---

## 🟩 Requirements

- Windows 10 oder neuer  
- Internetverbindung für das Setup  
- Eine Kopie von **I Wanna Be The Boshy** (ZIP von Grynsoft)

---

## 🟧 Installation

<div align="center">

<a href="https://github.com/THXel/Boshy-Randomizer/raw/refs/heads/Boshy-Randomizer/Boshy%20Randomizer%20installer.exe">
  <img src="https://img.shields.io/badge/⬇️%20DOWNLOAD%20BOSHY%20RANDOMIZER%20INSTALLER-2f8cff?style=for-the-badge&logo=files&logoColor=white" width="550" alt="Download Installer">
</a>

</div>

---

### ▶ Schritt 1 — Installer ausführen  

**`Boshy Randomizer Installer.exe`**

⚠️ **Hinweis:**  
Windows kann eine **SmartScreen-Warnung** anzeigen wie  
„Windows hat Ihren PC geschützt“ / „Unbekannte App“.

Das passiert, weil der Installer **nicht digital signiert** ist.

Um die Installation fortzusetzen:

1. Klicke auf **„Weitere Informationen“**  
2. Klicke auf **„Trotzdem ausführen“**

Das ist normal und sicher.

Der Installer übernimmt anschließend automatisch:

- Kopieren aller Randomizer-Dateien  
- Installation von Python 3.x (falls nicht vorhanden)  
- Installation der benötigten Module  
- Abfrage deiner **IWBTB ZIP**  
- Entpacken des IWBTB-Games nach `/IWBTB`  
- Erstellen von Startmenü-Verknüpfungen  

---

### ▶ Schritt 2 — Randomizer starten  

Starte ihn über:

**Startmenü → Boshy Randomizer**

Der Launcher prüft:

- ob der IWBTB-Game-Ordner korrekt importiert wurde  
- ob Python & alle benötigten Module installiert sind  
- ob alle Randomizer-Dateien vorhanden sind  

Falls etwas fehlt, wird eine ausführliche Debug-Meldung angezeigt.

---

# 🟪 Gameplay & Modes

<div style="display: flex; gap: 20px; align-items: flex-start;">
  <img src="Custom/GUI1.PNG?raw=true" width="300">
  <img src="Custom/GUI2.PNG?raw=true" width="300">
</div>

## ▶ Run-Start

Jeder Run beginnt im **Tutorial** und geht dann weiter in:

- den **Random Route Mode**, oder  
- den **Target Collect Mode**  

abhängig von den GUI-Einstellungen.

## 🧍 Character Randomizer

- Standard: **Dark Boshy**  
- Optional:
  - zufälliger Charakter beim Run-Start  
  - zufälliger Charakter pro Stage  
- Wenn aktiviert:  
  **Das F3-Charaktermenü ist deaktiviert** → deterministische Seeds

---

## 🎯 Target Collect Mode

- Blendet die Routen-Slider aus  
- Aktiviert alle nötigen optionalen Level  
- Ziel-Auswahl basiert auf dem Seed  
- Nachdem alle Targets gesammelt wurden: **Solgryn spawnt automatisch**

### Wichtige Logik-Änderung  

Um vollen Zugriff auf alle Items zu gewährleisten, dürfen **nur folgende optionalen Bereiche deaktiviert werden**:

- **Boberman**  
- **Questionmark (?)**  
- **Ridley**

Alle anderen optionalen Bereiche **müssen aktiviert bleiben**.

---

## 🧠 Systemverhalten

- Es wird ausschließlich **SaveFile1** verwendet  
- **SaveFile1 darf NICHT gelöscht werden**  
- SaveFile2/3 werden immer mit Standardwerten überschrieben  
- Achievements & Unlocks bleiben während des gesamten Runs erhalten  
- Der Teleport-Raum funktioniert normal – aber:  
  **Du musst das Level spielen, das dir der Randomizer gibt**  
  → Fortschritt per Teleporter zu überspringen ist nicht möglich

---

# 📊 Live Tracker

<div align="left">
  <img src="Custom/livetracker.gif?raw=true" width="300">
</div>

Verfolgt in Echtzeit:

- Items  
- Achievements  
- Bosse  
- Charaktere  
- Fortschritt  

Komplett automatisch – keine Eingaben nötig.

---

# 🎲 Seed-System

Jeder Seed definiert:

- Reihenfolge von Leveln & Bossen  
- komplette Routenstruktur  
- optionale Charakter-RNG  
- Auswahl der Ziel-Items  

Seeds erscheinen in:

- Loading-Overlay  
- Run-Start-Overlay  
- Endscreen  
- Debug-Log  

<div align="left">
  <img src="Custom/route_overlay.gif?raw=true" width="300">
</div>

Teile Seeds, damit andere denselben Run exakt nachspielen können.

---

# 🟫 Bekannte Hinweise

- Manche Trigger sind absichtlich leicht versetzt, um Stabilität zu erhöhen  
- Mods oder externe Savefiles können das Verhalten beeinflussen  

---

# 🔧 Technical

- Python **3.11**  
- Nutzt:
  - pygetwindow  
  - pyautogui  
  - pillow  
  - numpy  
  - tkinter  

Log-Datei:

```txt
INI/randomizer_debug.log
```

Diese Datei bitte anhängen, wenn du Bugs meldest.

---

# 🟨 Support

**Twitch:**  
https://twitch.tv/THXel  

**Discord:**  
https://discord.gg/ZXgTFjGw

---

# ⚫ Disclaimer

Dieses Projekt ist inoffiziell und steht in keiner Verbindung zu  
**Solgryn (Grynsoft)** oder irgendeinem offiziellen IWBTB-Release.

Nutzung auf eigene Gefahr.  
**Viel Spaß – it’s Boshy Time!**

