# Release preparation — 2026-10-13

## Implemented and checked

- Game-free amd64 Debian package with Wine, Lutris and desktop/Python dependencies.
- First-launch folder/ZIP import, supported game hash validation and a private game copy without the source's saves/profile/settings.
- Checksum-pinned Wine Staging 11.2 WoW64. All 3,997 upstream files match the working reference runner; the installer checks symlink targets too. The reference setup disables DXVK, Esync and Fsync.
- Portable PE launch helpers and install-time runtime path rebasing, retaining executable signature and process ownership checks.
- A consolidated build for the two launch helpers, four native DLLs and two hook payloads. Package creation checks its required resource inventory before building.
- Fixed missing launch/route modules and loading icon metadata found during the package test. Fresh options use the game's encrypted format. Empty save files created by the original menu no longer make an unused slot appear occupied.
- 41 automated tests covering game import, save preservation, unsafe archives, runner verification/reuse, resource completeness, startup imports, empty slots, localization and loading cleanup.
- Updated English, German, Russian, Spanish and Japanese READMEs, actual Mint VM screenshots and a menu GIF. Update logs remain English.

## Fresh-install VM evidence

The test VM is an installed Linux Mint 22.3 X11 system with an XP appearance. A snapshot was taken before package installation. Wine was initially absent. APT installed the Debian package, Wine and Lutris; the first-run wizard imported the game ZIP, downloaded and verified the pinned runner and created a fresh prefix.

The original animated game menu, randomizer setup and separate live tracker were displayed. A new Randomizer run loaded into a randomized level with Dark Boshy and a managed slot. Closing the game also closed its tracker. After a full application restart, resuming restored the same run ID, seed, slot, level and character with an empty runtime error log. The folder-selection path was tested separately through the wizard, and source INI hashes were unchanged afterward. The folder copy did not contain the source's saves and its newly created options were encrypted correctly.

This is a fresh-install and application-start test in a running VM, not a machine-reboot test or a performance benchmark. The VM has limited resources. Complete gameplay runs, all three slots, every beta/miniboss exit, Target Select's finale and migration from a previous development install are not claimed as tested by this package check.

## Distribution status

The Linux release candidate is distributed through [GitHub Releases](https://github.com/THXel/Boshy-Randomizer/releases/tag/v2026.10.13-rc1), with the game-free `.deb` and `SHA256SUMS`. **The updated Windows version will follow** and needs its own backend integration and tests. At that time, the root Windows executables were historical downloads. They were removed from the source tree during the October 20 cleanup; current installers are on GitHub Releases.

The original game is not bundled. Keep the existing third-party attribution and review distribution permissions before public publication; the preparation itself does not add any new rights to game-derived assets.

## Source/install boundary

`native-linux/` is the current package source. The historical `source-manifest.json` inventory was removed during the October 20 cleanup because it no longer described the current tree. Git records the source; each built package has its own payload hash manifest. Generated native binaries and user data are excluded from Git. The existing host game installation was not used as the test target: all 238 protected live files matched the pre-update baseline after packaging work.

## Package revision 2

Adds the startup focus handoff, metadata-only save detection and compact BR3 seed format with BR2 import support. Seed tests cover historical option versions, every character, randomized settings and damaged inputs; startup-focus tests cover delayed tracker/game creation and bounded retries. The first revision's VM findings above remain the fresh-install baseline, not a claim of a repeated VM test for revision 2.
