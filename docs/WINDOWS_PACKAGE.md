# Windows installer preview

The current native-menu controller now has a Windows backend. This is a preview;
the existing public Windows executables in the repository are legacy downloads.
The installed Linux copy is not modified by Windows testing.

## Starting

Download `BoshyRandomizer-2026.10.20.2-Windows-Setup-x64.exe` from the
[combined Windows & Linux release](https://github.com/THXel/Boshy-Randomizer/releases/tag/v2026.10.20.2).
Run the setup wizard, then open **Boshy Randomizer** from the Start menu or the
optional desktop shortcut. No command window is needed. A private Python runtime
is included. On first start, select a
compatible Boshy game folder or ZIP. The game itself and existing personal saves
are never included in the download or copied into a new run.

Private game data and three independent runs live in
`%LOCALAPPDATA%\BoshyRandomizer`. Keep this folder when updating the application.
The current native hooks require a short ASCII data path; `BOSHY_DATA_HOME` can
select another private local directory. Non-ASCII Windows account paths still need dedicated compatibility testing.
Windows 11 startup checks are described below.

The application installs for the current user in `%LOCALAPPDATA%\Programs\Boshy Randomizer`
without requesting administrator rights. Close the game before installing an update.
Uninstall through Windows Settings → Apps; the separate game and saves remain.
The installer prevents selecting the private data folder as the application folder.

## Security and packaging

The installer itself is not code-signed and may show an unknown-publisher or
SmartScreen reputation notice. This is distinct from an antivirus detection.
Keep Microsoft Defender enabled. The initial PyInstaller preview was quarantined
as `Trojan:Win32/Bearfoos.B!ml` and is not a release artifact. That detection is
not proof of a false positive. No protection settings or exclusions were changed.

The portable layout uses the original signed Python Software Foundation
executables and plain application files. The runtime manifest verifies application
resources before deployment. This layout was scanned with active Defender in
the Windows 10 VM; later engine updates and other antivirus products may behave
differently. Never recommend disabling protection as an installation step.

## Building

Build the native DLLs and helpers using `native-linux/build_runtime.py` on Linux.
Export only distributable runtime assets:

```sh
python3 packaging/export_windows.py dist/windows-payload
```

On Windows, use a local CPython installation with Tk and the dependencies in
`packaging/requirements-windows.txt`, then:

```powershell
python packaging/build_windows.py dist/windows-payload dist/windows-preview
```

Use empty output directories. No dependency download runs on the end user's first
start. The builder copies the Python runtime and dependency licenses, verifies
payload hashes, and creates a ZIP and SHA-256 record. The portable preview uses
[CPython 3.14.8](https://www.python.org/downloads/release/python-3148/). Its official
installer hash and Python Software Foundation signature were verified before
building, and the resulting package was scanned and started with Defender enabled.

Build the graphical installer from the verified portable directory using
[Inno Setup 7](https://jrsoftware.org/isinfo.php):

```powershell
ISCC.exe /DPackageDir="C:\build\BoshyRandomizer" /DOutputDir="C:\build\installer" packaging\windows\setup.iss
```

The stable AppId allows in-place updates. The installer never deletes the separate
user-data directory. It includes English, German, Russian, Spanish and Japanese
installer controls and uses the existing Boshy icons.

## Original display options

`Options → Screen size` still uses Boshy's original resizing and INI save path.
Left/right now cycles through standard 4:3 sizes that fit the monitor containing
the game. The maximum fitting size accounts for the work area and the original
35-pixel title-bar allowance. The last option remains the original stretched,
maximized window. Other original options are preserved.

The ceiling is 2880 × 2160 for 4:3 content; a conventional 3840 × 2160 screen
needs a slightly smaller window to leave space for its frame and taskbar.
Stretched fullscreen uses the actual monitor. Native validation and automatic
tests cover the numeric limits; the current live VM display is 2560 × 1440.
Physical 4K and mixed-DPI multi-monitor behavior are not yet verified.

## Verification scope

Windows 10 x64 VM checks completed with Defender real-time protection enabled and
no exclusions: installer scan, fresh install, in-place update, uninstall,
reinstall, Start-menu and desktop shortcuts, first-run import dialog and saved-run
resume through the installed application. A preservation marker in the separate
data folder survived update and uninstall unchanged. The installed game resumed
the same run with native error count zero and preserved its fitting window size.

Earlier portable tests covered three separate Randomizer / Normal / Target slots,
three resets per mode, the tracker and the debug hotkey. The installer packages
the same validated application payload. Natural playthroughs of every boss,
soundpack and hack combination remain outside this Windows smoke test. The
Windows build remains a preview within the combined Windows & Linux release.

## Windows 11 cold-start check (2026-10-20)

A fresh Windows 11 VirtualBox VM exposed a stale Extras DLL checksum in the
release build and a startup timeout that was too short for the first game launch.
Version 2026.10.20.2 corrects the build binding and waits up to three minutes for
the Windows game window, failing promptly if the launched process exits.

The corrected candidate passed installation, game import, native menu, a normal
run start and Q/R smoke checks. A separate regular application launch showed the
live tracker. Defender antivirus and real-time protection remained enabled.
This does not replace full playthrough, physical hardware, or mixed-DPI testing.
