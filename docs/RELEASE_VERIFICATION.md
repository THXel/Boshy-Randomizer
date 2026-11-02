# Version 1.0.1 verification

Verified on 2026-11-02.

## Window-size correction

The 1.0.0 package reproduced the reported problem: a 930 × 610 window returned to 640 × 480 after R. The correction removes saved-size actions from 52 room-start handlers. Explicit display choices still apply in Options; startup still loads the saved preference.

The compiled executable was checked across all 61 frames. The image, font and sound banks match 1.0.0 byte for byte. Game SHA-256: `db20c6a0da6662ea348288ecf6512df82472bc8e6566d07ec148930a202389db`.

## Installed-package checks

The exact 1.0.1 Windows Setup was installed in Windows 11 and in an isolated Wine installation on Linux. Both installations verified all 2,167 payload files and the reconstructed game hash.

Each platform passed 27 recorded checkpoints covering native window resizing, five R resets, death/retry, maximization with three resets, F2, Options-room entry/exit, explicit 4:3 and 16:9 resolution selection, F4 fullscreen with three resets, and saved resolution after restarting the application. Window geometry was set through the native window API; game/menu navigation used real key input. Game state was observed read-only.

The installed main-menu card and history were rendered in all five languages. The DEB metadata, upgrade ordering and embedded installer hash were verified.

## Automated checks

- 491 maintained-runtime tests passed, including the new regression covering all room transforms.
- 29 game-free current-source tests passed.
- 15 repository tooling tests and source formatting passed.

## Boundaries

These checks do not establish that every seed, route or boss combination has been completed. Full natural victory/exit checks remain incomplete for Skeleton King, Mega Man, Shang Tsung, Bomberman, Ryu Dodge, Cheetahman, King Dedede and Kid Icarus. The personal OBS display itself was not verified in the final tracker check because its local service endpoint was unavailable.

The live window regression uses representative gameplay plus menu/Options transitions. It does not claim a fresh complete playthrough of every room. Earlier gameplay evidence is recorded in the [1.0.0 verification record](https://github.com/THXel/Boshy-Randomizer/blob/v1.0.0/docs/RELEASE_VERIFICATION.md).
