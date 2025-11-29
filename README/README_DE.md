<p align="right">
  <strong>Language:</strong><br>
  <a href="../README.md" title="English">🇬🇧 English</a> ·
  <a href="README_DE.md" title="Deutsch"><strong>🇩🇪 Deutsch</strong></a> ·
  <a href="README_RU.md" title="Русский">🇷🇺 Русский</a> ·
  <a href="README_ES.md" title="Español">🇪🇸 Español</a> ·
  <a href="README_JP.md" title="日本語">🇯🇵 日本語</a>
</p>

<div align="center">

  <img src="../Custom/boshy_randomizer.png?raw=true" alt="Boshy Randomizer" width="420">

  <p><strong>Erstellt von THXel & der I Wanna Be The Boshy Speedrun Community</strong><br>
  © 2025 THXel</p>

</div>

---

<p align="center">
  <b>Moderner Randomizer für <i>I Wanna Be The Boshy</i></b><br>
  Zufällige Routen • Seed-Codes • ER/EB Masken • Live-Tracker • Aufgeräumte GUI
</p>

<p align="center">
  <a href="#-features">Features</a> •
  <a href="#-installation">Installation</a> •
  <a href="#-gameplay--modes">Gameplay & Modes</a> •
  <a href="#-seed-system">Seed-System</a> •
  <a href="#-technical">Technical</a> •
  <a href="#-support">Support</a>
</p>

---

## 🟦 Features

- 🎲 **Random Routes** – deterministische, seed-basierte Level- & Boss-Routen  
- 🧩 **Item Randomizer (Sicherer Stats-Modus)** – *gesammelte Charaktere werden zufällig*, Items bleiben im Spiel unverändert (ansonsten Spielabsturz)  
- 🧍 **Character Randomizer** – zufällig beim Start oder pro Stage, vollständig seed-deterministisch  
- 🎯 **Target Collect Mode** – versteckte Route, seed-basierte Targets  
- 📊 **Live Tracker** – verfolgt Items, Bosse, Achievements & Charaktere  
- 🔁 **Deterministische Seeds** – Runs teilen und exakt reproduzieren  
- 🧱 **ER/EB Masken** – optional aktivierte Level/Bosse in Seed gespeichert  
- 🔒 **Seed-Lock GUI** – Seed eingeben → GUI zeigt Einstellungen & wird gesperrt  
- ⚙️ **Auto-Setup** – installiert Python, Module & importiert IWBTB automatisch  

---

## 🎮 Gameplay Preview

<div align="center">
  <img src="../Custom/gameplay.gif?raw=true" width="300">
  <img src="../Custom/gameplay2.gif?raw=true" width="300">
</div>

---

## 🟧 Installation

<div align="center">

<a href="https://github.com/THXel/Boshy-Randomizer/raw/refs/heads/Boshy-Randomizer/Boshy%20Randomizer%20installer.exe">
  <img src="https://img.shields.io/badge/⬇️%20BOSHY%20RANDOMIZER%20INSTALLER%20HERUNTERLADEN-2f8cff?style=for-the-badge&logo=files&logoColor=white" width="550">
</a>

</div>

---

### ▶ Schritt 1 — Installer ausführen

**`Boshy Randomizer Installer.exe`**

⚠️ **SmartScreen-Hinweis:**  
Windows kann anzeigen:

„Windows hat Ihren PC geschützt“ / „Unbekannte App“.

Das ist normal – der Installer ist **nicht digital signiert**.

Klicke:

1. **Weitere Informationen**  
2. **Trotzdem ausführen**

Der Installer erledigt automatisch:

- Kopieren aller Randomizer-Dateien  
- Installation von Python 3 (falls nicht vorhanden)  
- Installation aller Module  
- Abfrage der **IWBTB ZIP**  
- Entpacken nach `/IWBTB`  
- Anlegen der Startmenü-Verknüpfungen  

---

### ▶ Schritt 2 — Randomizer starten

**Startmenü → Boshy Randomizer**

Der Launcher prüft:

- IWBTB korrekt importiert  
- Python & Module installiert  
- Dateien vollständig  

Bei Fehlern erscheint eine Debug-Meldung.

---

# 🟪 Gameplay & Modes

<div style="display: flex; gap: 20px; align-items: flex-start;">
  <img src="../Custom/GUI1.PNG?raw=true" width="300">
  <img src="../Custom/GUI2.PNG?raw=true" width="300">
</div>

## ▶ Run-Start

• Jeder Run beginnt im **Tutorial**.  
• Danach je nach GUI-Einstellung:  
  – **Zufällige Route**  
  – **Target Collect Mode**

## ▶ Systemverhalten

• Es wird ausschließlich **SaveFile1** verwendet.  
• **SaveFile1 darf NICHT gelöscht werden.**  
• SaveFile2 und SaveFile3 werden immer überschrieben.  
• Achievements & Unlockables bleiben für den gesamten Run bestehen.  
• Das Item **Awesomesauce** ist zu Run-Beginn immer verfügbar, um den Erhalt von **Gastly** sicherzustellen.
• Der Teleport-Raum funktioniert normal, aber:  
  Um weiterzukommen, **muss das Level gespielt werden**,  
  das der Randomizer vorgibt – Überspringen ist nicht möglich.

---

## 🧍 Character Randomizer

- Standard: Dark Boshy  
- Optional:  
  - zufällig beim Run-Start  
  - zufällig pro Stage  
- Während Random Character aktiv ist:  
  **F3-Charaktermenü deaktiviert** → deterministische Seeds  

---

## 🧩 Item Randomizer – Details

IWBTB stürzt ab, wenn Items **direkt im Spiel** ersetzt werden.  
Darum funktioniert der Item Randomizer so:

- ✔ **Gesammelte Charaktere werden zufällig ersetzt**  
- ✖ **Items werden NICHT im Spiel ausgetauscht** (Crash-Schutz)  
- ✔ Items erscheinen zufällig **nur in der Stats-Anzeige**  
- ✔ Keine Gameplay-Risiken  
- ✔ Stabil und 100% kompatibel mit Routing  

---

## 🎯 Target Collect Mode

- Route verborgen  
- Targets werden per Seed bestimmt  
- Wenn alle Targets gesammelt wurden → **Solgryn erscheint automatisch**

Deaktivierbare optionale Bereiche:

- Boberman  
- „?“  
- Ridley  

Alle anderen müssen aktiv bleiben.

---

# 📊 Live Tracker

<div align="left">
  <img src="../Custom/livetracker.gif?raw=true" width="300">
</div>

Verfolgt:

- Items
- Achievements
- Bosse
- Charaktere
- Live-Fortschritt
- **Im Target Collect Mode:** die benötigten **Target-Items**

Automatisch und ohne Eingabe.

---

# 🎲 Seed-System

Ein Seed-Code wie:

```
R14-B4-T0-C2-P1-S152722-ER5-EB34C
```

bedeutet:

- **R** – Level  
- **B** – Bosse  
- **T** – Target Collect  
- **C** – Character Randomizer  
- **P** – Item Randomizer  
- **S** – Seed  
- **ER** – optionale Level  
- **EB** – optionale Bosse  

Damit lässt sich jeder Run **1:1 reproduzieren**.

---

# 🔧 Technical

- Python 3.11  
- Bibliotheken:
  - pillow  
  - numpy  
  - pyautogui  
  - pygetwindow  
  - tkinter  

Log-Datei:

```
INI/randomizer_debug.log
```

---

# 🟨 Support

**Twitch:** https://twitch.tv/THXel  
**Discord:** https://discord.gg/ZXgTFjGw  

---

# ⚫ Disclaimer

Inoffizielles Projekt, nicht verbunden mit **Solgryn (Grynsoft)**.  
Nutzung auf eigene Gefahr.  
**Viel Spaß – it’s Boshy Time!**
