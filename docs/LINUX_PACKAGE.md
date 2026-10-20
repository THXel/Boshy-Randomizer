# Linux packaging

## Target and install

Linux Mint 22.x / Ubuntu 24.04, amd64, Python 3.12, X11. Install with `sudo apt install ./boshy-randomizer_2026.10.18-1_amd64.deb` so APT resolves dependencies, including Wine and Lutris. Installing a `.deb` with `dpkg -i` alone does not fetch missing dependencies.

The package ships the randomizer and its native helper binaries, **not the original game, player saves, credentials or a Wine prefix**. The first-run wizard accepts a game folder or ZIP, verifies the supported EXE hash and creates a separate copy. Unsafe archives, ambiguous game copies and unsupported executables are rejected. Existing destinations are not overwritten.

## Pinned Wine

The reference installation uses Wine Staging 11.2 WoW64, with DXVK, Esync and Fsync off. System Wine supplies the distribution libraries; Boshy launches explicitly through the pinned runner, never silently through system Wine.

- Upstream: [Kron4ek Wine Builds 11.2](https://github.com/Kron4ek/Wine-Builds/releases/tag/11.2)
- Archive: `wine-11.2-staging-amd64-wow64.tar.xz`
- SHA-256: `edd598a710b3738bd0183bbb393b26d91179a0d0d421b51dd9df001aa7b1eeb9`
- [Upstream source and build scripts](https://github.com/Kron4ek/Wine-Builds/tree/11.2)

First launch downloads the archive over HTTPS, checks its pinned hash before extraction, verifies the extracted files and atomically installs it under the user's Lutris runner directory. An existing runner is reused only if its file hashes and symlink targets match. Existing modified runners are preserved. Wine is fetched from upstream, not bundled or redistributed inside this package. Normal later starts do not need another download.

## Data locations and boundaries

- Immutable package: `/usr/lib/boshy-randomizer/`
- User runtime, private game, prefix and run snapshots: `~/.local/share/boshy-randomizer/`
- Lutris runner: `~/.local/share/lutris/runners/wine/`
- Runtime log: `~/.local/share/boshy-randomizer/linux-runtime.log`
- First Wine setup log: `~/.local/share/boshy-randomizer/evidence/wine-setup.log`

`XDG_DATA_HOME` is respected. `BOSHY_DATA_HOME` can override the randomizer's root; this path must use ASCII and be at most 180 characters because native game hooks use fixed-size ANSI paths. Selecting a game source folder with non-ASCII characters is supported. Launch as a normal desktop user, not root. Do not share a runtime root between simultaneous instances.

Package removal leaves user data in place. Existing development installations are not automatically migrated. The original game's EXE signature checks, per-prefix process ownership, run bindings and rule snapshots remain enforced.

## Building

Build on the target Ubuntu/Mint generation with Python 3.12, Pillow, GCC multilib, binutils and the x86_64 MinGW compiler. Runtime dependencies are listed in `packaging/build_deb.py`.

```sh
sudo apt install gcc-multilib binutils gcc-mingw-w64-x86-64 python3-pil
python3 native-linux/build_runtime.py
python3 -m unittest discover -s native-linux/tests -v
python3 packaging/build_deb.py dist
```

`MINGW_CC` may select another x86_64 MinGW compiler. The build creates four native DLLs, two hook payloads and two PE64 helper programs. Install-time rebasing inserts the user's private runtime path into the hook context. The package builder writes a payload manifest and `SHA256SUMS`; no game directory or runtime saves enter its allowlist.

## Verification

Automated importer tests cover folder/ZIP import, original-save preservation, version rejection, path traversal, duplicate names, symlinks, size limits and existing destination protection. Wine tests cover modified-runner rejection and verified reuse without a download. Localization and loading cleanup tests remain included. These tests do not replace full gameplay runs across all five modes.

The fresh Mint 22.3 VM installation, ZIP import, folder import, pinned runner download a new managed run and resuming that same run after an application restart were checked. The first-run screenshot is retained from that VM test. The 2026-10-15 menu screenshots and GIFs are new captures from the current native menu on the host. See [release verification](RELEASE_PREPARATION.md) for scope and remaining checks. The [combined release](https://github.com/THXel/Boshy-Randomizer/releases/tag/v2026.10.18) includes the Linux package and a Windows installer preview.

## Game and assets

Supply your own copy of I Wanna Be The Boshy. The supported executable has SHA-256 `dc6a1a551254f1d1003d14c0bf58f639a7ea94f99f74b5c635ddaf9bc4ec0806`; other versions are rejected before installation. Original game by Solgryn / Grynsoft. Existing attribution in [Custom/License.txt](../Custom/License.txt) remains applicable. The randomizer does not grant rights to original game or third-party artwork. Music, intro scenery and spider assets are extracted from the verified local game during setup and are not bundled as game files.

The 2026.10.18 runtime was also checked in an isolated host game copy: start, reset, foreground focus and same-run resume passed with zero native hook errors. Release packages are built from source on GitHub Actions and pass the native test suite before publication.
