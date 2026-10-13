# Linux release candidate — 2026.10.13

**This release candidate targets Linux Mint 22.x / Ubuntu 24.04 (amd64, X11). The updated Windows version will follow.** Older Windows downloads do not contain this native-menu update.

Install the `.deb` with your package manager or `sudo apt install ./boshy-randomizer_2026.10.13-1_amd64.deb`. Wine and Lutris are installed as dependencies. On first launch, select your own Boshy folder or ZIP; setup creates a separate game copy and installs checksum-verified Wine Staging 11.2 WoW64. Internet is required for the dependencies and initial Wine download. The original game, saves and Wine prefix are not included.

The native menu supports three independent saves, Randomizer and Target Select, shared BR2 seeds, advanced routes, mixed item/character rewards, optional character/projectile randomization, comfort/training settings and a separate live tracker. Ctrl+Alt+D opens optional diagnostics and recording tools.

Automatic interface languages: English, German, Russian, Spanish and Japanese, with English fallback. Update logs remain English. The separate PinguLexa/OBS integration is not installed by this package.

See [installation and data locations](LINUX_PACKAGE.md) and [release verification](RELEASE_PREPARATION.md). Existing development installations are not automatically migrated. Keep your current installation until you have tested the new package.

Twenty automated tests passed. Fresh installation, game import, new-run start and same-save resume were verified in a resource-limited Linux Mint 22.3 VM. Full gameplay and performance testing remain open.
