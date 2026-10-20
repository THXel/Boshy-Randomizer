# Linux release candidate — 2026.10.13

**This release candidate targets Linux Mint 22.x / Ubuntu 24.04 (amd64, X11). The updated Windows version will follow.** Older Windows downloads do not contain this native-menu update.

Install the `.deb` with your package manager or `sudo apt install ./boshy-randomizer_2026.10.13-2_amd64.deb`. Wine and Lutris are installed as dependencies. On first launch, select your own Boshy folder or ZIP; setup creates a separate game copy and installs checksum-verified Wine Staging 11.2 WoW64. Internet is required for the dependencies and initial Wine download. The original game, saves and Wine prefix are not included.

The native menu supports three independent saves, Randomizer and Target Select, compact BR3 seeds (BR2 import supported), advanced routes, mixed item/character rewards, optional character/projectile randomization, comfort/training settings and a separate live tracker. Ctrl+Alt+D opens optional diagnostics and recording tools.

Automatic interface languages: English, German, Russian, Spanish and Japanese, with English fallback. Update logs remain English.

See [installation and data locations](LINUX_PACKAGE.md) and [release verification](RELEASE_PREPARATION.md). Existing development installations are not automatically migrated. Keep your current installation until you have tested the new package.

41 automated tests passed. Fresh installation, game import, new-run start and same-save resume were verified in a resource-limited Linux Mint 22.3 VM. Full gameplay and performance testing remain open.

Package revision 2 fixes first-start keyboard focus and metadata-only save stubs, and adds compact share codes with an improved seed dialog. Standard BR3 codes contain 18 characters instead of 603; customized settings may need longer codes. Update an existing Debian installation with the same apt command above; user saves remain separate from the package.
