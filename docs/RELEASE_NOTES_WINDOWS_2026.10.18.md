# Boshy, reborn — Windows installer preview

**Rediscover Boshy. A new adventure with every seed.**

The new native-menu randomizer now has a Windows setup wizard. Download
**BoshyRandomizer-2026.10.18-Windows-Setup-x64.exe**, install it, and launch
**Boshy Randomizer** from the Start menu or the optional desktop shortcut.
No CMD window or separate Python, Wine or Lutris installation is needed.

- Setup controls in English, German, Russian, Spanish and Japanese.
- Installs for the current Windows account. Updates and uninstall preserve the
  separate game copy and saved runs in `%LOCALAPPDATA%\BoshyRandomizer`.
- Native menus, independent save slots, live tracker and optional debug window.
- Monitor-aware sizes in the original Screen size option, retaining stretched
  fullscreen as the last choice. Window position stays inside the monitor.
- On first launch, select your own compatible Boshy **folder or ZIP**.
  **The original game is not included.**

### Tested

Windows 10 x64 VM: installation, update, uninstall, data preservation, reinstall,
shortcuts, first-launch setup and saved-run resume. Defender remained enabled,
with no exclusions and no new detections for this installer/application.
Earlier portable tests covered Randomizer, Normal, Target Select, resets,
tracker and diagnostics. This does not cover every complete run or hack combination.

### Preview limits

The installer is not code-signed. Windows may display an unknown-publisher or
SmartScreen reputation notice. Antivirus detections are a different issue:
keep protection enabled and report detections rather than adding exclusions.
Windows 11, non-ASCII account paths, physical 4K and mixed-DPI monitors still
need dedicated testing. See [Windows details](https://github.com/THXel/Boshy-Randomizer/blob/Boshy-Randomizer/docs/WINDOWS_PACKAGE.md).

[Linux downloads remain available](https://github.com/THXel/Boshy-Randomizer/releases/tag/v2026.10.15).
Old Windows executables in the repository belong to the legacy randomizer.

Original game by **Solgryn / Grynsoft**. Fan project by **THXel and the Boshy speedrunning community**.
