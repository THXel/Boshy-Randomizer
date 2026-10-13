# Boshy Randomizer — Deutsch

[Linux download — 2026.10.13 RC1](https://github.com/THXel/Boshy-Randomizer/releases/tag/v2026.10.13-rc1) · [DEB](https://github.com/THXel/Boshy-Randomizer/releases/download/v2026.10.13-rc1/boshy-randomizer_2026.10.13-1_amd64.deb)

Der Randomizer steckt direkt im originalen animierten Boshy-Hauptmenü: drei getrennte Spielstände, Randomizer und Target Select, teilbare BR2-Seeds, Advanced-Regeln, gemischte Item-/Charakterbelohnungen, optionale Hacks, Live-Tracker und Debugfenster mit Strg+Alt+D.

## Linux installieren

Das Debian-Paket richtet sich an Linux Mint 22.x / Ubuntu 24.04 auf amd64 mit X11. **Die aktualisierte Windows-Version kommt später.** Die alten Windows-Dateien im Hauptordner gehören zur früheren Version.

```sh
sudo apt install ./boshy-randomizer_2026.10.13-1_amd64.deb
```

Wine, Lutris und die benötigten Bibliotheken werden mitinstalliert. Öffne danach **Boshy Randomizer** im Anwendungsmenü und wähle deinen **Boshy-Ordner oder eine Spiel-ZIP**. Das Spiel selbst ist nicht enthalten und wird nicht heruntergeladen. Das Setup prüft die Spielversion und erstellt eine eigene Kopie, ohne vorhandene Spielstände oder Einstellungen zu übernehmen oder zu verändern.

Beim ersten Start wird die passende **Wine-Staging-11.2-WoW64-Version** automatisch heruntergeladen (ca. 72 MiB), per Prüfsumme kontrolliert und separat eingerichtet. Eine identische vorhandene Lutris-Version wird wiederverwendet. Für Abhängigkeiten und den ersten Wine-Download ist Internet nötig. Lutris muss beim Spielen nicht geöffnet bleiben.

Daten und neue Spielstände: `~/.local/share/boshy-randomizer/`. Die Deinstallation des Pakets behält diese Dateien. Eine bisherige Entwicklungsinstallation wird nicht automatisch migriert.

Die Oberfläche erkennt Englisch, Deutsch, Russisch, Spanisch und Japanisch automatisch, mit Englisch als Fallback. Update-Texte bleiben Englisch. Das originale Spielmenü und Spielgrafiken werden nicht übersetzt. Die separate PinguLexa-/OBS-Anbindung ist nicht Bestandteil dieses Pakets.

[English overview](../README.md) · [Paketdetails und Prüfstand](../docs/LINUX_PACKAGE.md) · [Release-Vorbereitung](../docs/RELEASE_PREPARATION.md)

## Aktuelle Ansichten

![Native menu](../docs/media/linux-native-menu.gif)

![Live tracker](../docs/media/linux-run-tracker.png)
