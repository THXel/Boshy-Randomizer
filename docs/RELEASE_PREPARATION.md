# Release verification — Boshy, Reborn · 2026-10-15

## Build and automated checks

Linux package `2026.10.15-1`, amd64, Linux Mint 22.x / Ubuntu 24.04 with X11. All four native DLLs, two hook payloads and two launch helpers were rebuilt from source. The deterministic PE build differs from the live-tested binaries only in timestamps/checksum; executable and data bytes were compared. Exact launch-time hashes remain enforced.

**180 automated tests passed** against the release source. This includes import safety, independent saves, language fallback, seed round trips, menu controls, intro themes, music mappings, spider lifecycle, reset/save read recovery and ending-state handling. The documented test command now also works for the complete native-exit test without an externally supplied Python path.

The offline trigger audit exercised **99,108 assertions**, 45 spots, both modes and 16 hack combinations. All 45 configured native room-exit pairs were exercised in the C interception harness. These are simulations, not completed playthroughs.

The DEB contains required diagnostic fingerprint resources as well as the runtime. No game executable, Wine prefix, personal save, profile or private diagnostic recording is packaged. Payload hashes and the public DEB are checked separately.

## Package launch and resume

The release payload was applied to a separate copy of the earlier package test installation. An original “Playable characters” information dialog blocked loading focus; the release now closes only that exact visible notice owned by the active game. Two tests cover process/title/visibility scoping. The host lacks the system ImageTk library, so this local check used the existing complete Python environment; `python3-pil.imagetk` is explicitly required by the DEB. No new APT/VM install is claimed.

After that correction, a managed test run loaded through the normal native menu, survived R, and resumed the same run ID after closing and reopening the application. Boshy held keyboard focus. All 45 diagnostic rows loaded from the packaged resources. Old copied test bundles were explicitly rebound to the isolated copy before testing; user save migration is not implied.

## Actual game tests

- All **45 spots loaded and reset** in the actual game with combined hacks.
- **Questionmark and Ridley:** actual shooting victories with intro skip on and off; HP remained protected during the intro before manual S skip.
- **Old Sonic:** movement to the shrinking platform's center, actual HP 1 → 0 from a shot, then the full three-second death-animation cooldown before the route advanced.
- **Solgryn:** actual multi-phase combat and climbing sections, victory after 117 seconds. Reopening that completed slot showed the stored results without restarting the game.
- Boss combat checks used **God Mode, one-HP bosses and autofire**. HP and victory were not written directly. These checks do not claim ordinary full-difficulty boss completion.
- **Spider:** a natural initial interval of 300,371 ms elapsed without shortening the countdown, plus spawn grace. Real lethal contact, God Mode protection and the original roar were checked separately. Pause and reset handling were checked; a decremented timer of 1,297,220 ms and its RNG state survived a full application restart exactly.
- **Items/saves:** a real chest awarded Hamster CD; inventory, collected checks, character, unlocks, position and route survived close/resume.
- **Music:** game-stream mute/unmute, R and resume were checked; muted recording was silent and music returned afterward. Multi-phase Solgryn retained valid native music state.

Existing occupied saves and settings were protected and compared byte-for-byte after the tests. The temporary test slot was restored.

## Media

New native-menu captures dated 2026-10-15 show an unsaved demonstration configuration in all five languages. `rediscover-intro.gif` is a real animation capture; `rediscover-menu-tour.gif` is a timed sequence of captured native menu pages. Screenshots are not interface mockups. The older first-run image remains from the original Mint VM installation check.

## Limits

Not every natural level exit, complete route, Target Select finale or every hack combination has been played through. The maximum 30-minute spider interval was not waited out. Test successes are listed by scope in the debug overview; simulation results are not labelled as natural gameplay completion.

The [earlier Mint 22.3 VM test](VERIFICATION_2026.10.13.md) remains the fresh-machine installation baseline. It is not a new VM test of this release and not a performance benchmark. Development installations are not automatically migrated.

**The updated Windows version will follow.** Legacy Windows executables are not the current native-menu version.
