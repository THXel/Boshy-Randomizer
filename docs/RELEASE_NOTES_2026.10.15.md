# Boshy, Reborn — Linux 2026.10.15

**Rediscover Boshy. A new adventure with every seed.**

Dust off I Wanna Be The Boshy: shuffle its worlds and bosses, chase a random target list, and share a compact seed with friends.

**Linux Mint 22.x / Ubuntu 24.04 · amd64 · X11**
**The updated Windows version will follow.** Old Windows downloads belong to the legacy randomizer.

![Boshy, Reborn](https://raw.githubusercontent.com/THXel/Boshy-Randomizer/v2026.10.15/docs/media/rediscover-intro.gif)

## What is new

- **45 selectable route points** with split stages, minibosses and beta encounters. Faster engine-state transitions, safer save/reset handling, Old Sonic's death-animation delay and a corrected Solgryn ending.
- A more comfortable **native menu**: mouse hover, consistent keyboard navigation, context help, Advanced settings and seed-import previews.
- **Compact share seeds**, independent save profiles and an improved completed-run summary.
- Randomized intro characters, backgrounds and floor art with subtle effects.
- Optional music shuffle across 45 level/boss tracks, character changes and projectile/effect styles by spot, death or a configurable random interval.
- The original **spider surprise**, initially enabled for new runs, with unannounced attacks every 5–30 active gameplay minutes. Disable it in Advanced → Hacks and apply to remember that preference for future runs. Saved runs and imported seeds retain their own settings.
- Separate live tracker, music information, copy-seed button and optional Ctrl+Alt+D diagnostics.
- Fresh screenshots, two GIFs and documentation in **English, German, Russian, Spanish and Japanese**. The UI follows the system language with English fallback; update logs remain English.

## Install or update

Close the randomizer. Download the DEB and install it with your graphical package manager or:

```sh
sudo apt install ./boshy-randomizer_2026.10.15-1_amd64.deb
```

Wine and Lutris are dependencies. On first launch, select your own supported **Boshy folder or ZIP**. Setup creates a private game copy and provisions checksum-verified Wine Staging 11.2 WoW64. Internet is needed for dependencies and the initial runner download. **The original game is not included.** User saves are kept separately and preserved by package updates/removal; development installs are not automatically migrated.

## Verification

180 automated tests passed. The release payload was also checked in an isolated local installation: start, R reset, correct game focus and resuming the same run after an application restart. All 45 spots were loaded/reset in-game; Questionmark, Ridley, Old Sonic and Solgryn were additionally defeated with training hacks enabled. Natural spider timing, save/resume, music mute/resume and reopening completed results were checked. Not all complete routes or hack combinations have been played through. The older Mint VM check remains the fresh-install baseline.

[English](https://github.com/THXel/Boshy-Randomizer/blob/v2026.10.15/README/README_EN.md) · [Deutsch](https://github.com/THXel/Boshy-Randomizer/blob/v2026.10.15/README/README_DE.md) · [Русский](https://github.com/THXel/Boshy-Randomizer/blob/v2026.10.15/README/README_RU.md) · [Español](https://github.com/THXel/Boshy-Randomizer/blob/v2026.10.15/README/README_ES.md) · [日本語](https://github.com/THXel/Boshy-Randomizer/blob/v2026.10.15/README/README_JP.md)

[Installation details](https://github.com/THXel/Boshy-Randomizer/blob/v2026.10.15/docs/LINUX_PACKAGE.md) · [Verification scope](https://github.com/THXel/Boshy-Randomizer/blob/v2026.10.15/docs/RELEASE_PREPARATION.md)

Original game by **Solgryn / Grynsoft**. Fan project by **THXel and the Boshy speedrunning community**.
