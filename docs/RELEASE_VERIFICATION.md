# Version 1.0.2 verification

Verified on 2026-11-02.

## Language correction

Version 1.0.1 reproduced the reported mixed-language Options room in Windows 11: after switching from Japanese to German, the controls help and on/off text remained Japanese. The host published its reload signal before all translated artwork was ready, and native toggle displays only reloaded when their boolean value changed.

Version 1.0.2 prepares all Options artwork before publishing the reload signal and refreshes the toggle displays on language changes. Two new regressions failed against the previous source and passed after the correction.

The compiled executable was checked across all 61 frames. Only the Options-room event data and title build stamp changed from 1.0.1. Image, font and sound banks are byte-identical. Game SHA-256: `8813222ea61f15072d623d42b42f148ca93132333e18dad54a52fa736d7652b6`.

## Installed-package checks

The exact 1.0.2 Windows Setup was installed over 1.0.1 in Windows 11 and in an isolated Wine installation on Linux. Both verified all 2,167 payload files and the reconstructed game hash.

Each platform passed 15 recorded checkpoints: ten language/display checks and five window-geometry checks. Language checks covered all five languages, rapid left/right changes, matching LiveTracker output, F2 during gameplay, and a new game process using the saved language. Visible upper-room text was checked against the translated images; scrolled-room screenshots also covered the lower options and their on/off values. The selected language did not change the run seed. Three R resets and F2 retained a manually resized window.

Navigation used normal key input and native window APIs. Game state was observed read-only. Wine screenshots used the X11 game client because Wine's desktop capture returned a stale title image. Early test-script issues with transparent font pixels, truncated object names and F2 from the original Options room were corrected before the final full runs. The first Wine installer launch encountered a transient invalid-window-handle error; the retry installed successfully and passed the checks above.

The DEB metadata, upgrade ordering and embedded installer hash were verified. The existing personal Linux game installation was not replaced by these isolated tests.

## Automated checks

- 493 maintained-runtime tests passed, including both new language regressions.
- 29 game-free current-source tests passed.
- 15 repository tooling tests and source formatting passed.

## Boundaries

These checks do not establish that every seed, route or boss combination has been completed. Full natural victory/exit checks remain incomplete for Skeleton King, Mega Man, Shang Tsung, Bomberman, Ryu Dodge, Cheetahman, King Dedede and Kid Icarus. This language check verified tracker output, not the personal OBS scene.

Earlier gameplay and window-size evidence remains in the [1.0.0 verification record](https://github.com/THXel/Boshy-Randomizer/blob/v1.0.0/docs/RELEASE_VERIFICATION.md) and [1.0.1 verification record](https://github.com/THXel/Boshy-Randomizer/blob/v1.0.1/docs/RELEASE_VERIFICATION.md).
