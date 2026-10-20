# Changelog

All update logs remain in English, regardless of the UI language.

## 2026.10.20 — Soundpack death screens

- Support locally imported Kamilia 3 and WannaFest22 death screens, blood sprites and matching death audio. Optional game assets remain outside the distributed packages.
- Fade in Kamilia's translucent red screen before its Game Over title. Let its animated blood finish instead of disappearing on first floor contact.
- Reproduce WannaFest's fast left/right Game Over title impacts, animated VHS noise and rotating red death cubes using its local original texture. Remove the original Boshy bouncing scale only for imported death displays.
- Stop the imported death cue on reset and scene changes, keeping Boshy's original reset behavior in all three packs. No extra reset sound is added.
- Imported death audio now plays alone: ongoing music and native effects stop at death, duplicate cues are suppressed, and R restores normal game audio without changing volume settings.
- Validate image checksums, dimensions and animation timelines before activating a pack; switching back to Original restores the native death display.

## 2026.10.18 — Boshy, Reborn: Windows & Linux

- Bring the Linux DEB and tested Windows installer preview into one release with a shared download page and checksums.
- Replace the project landing page with a responsive five-language website, animated game previews, mode cards, feature groups and installation guides.
- Rewrite all five READMEs around the current five modes, seeds, independent saves, trackers, graphics, music, shot styles and optional hacks.

### Windows installer and display options

- Add a five-language per-user setup wizard, Start-menu and optional desktop shortcuts, upgrade support and an uninstaller that preserves separate game/save data. Shortcuts launch directly without a CMD window.
- Add a Windows backend for native saves, loading audio, focus, tracker and debug windows, using native Windows APIs.
- Package the preview with signed CPython runtime files and visible application sources. Keep Defender enabled; the quarantined PyInstaller prototype is not a release artifact.
- Extend the original Screen size option with monitor-fitting 4:3 presets up to a 2160-pixel content height. Preserve the final stretched fullscreen option and keep resized windows inside the current work area.
- Add display-size guidance in all five languages. Physical 4K and mixed-DPI verification remain open.

### Included playtest fixes

- Confirm native checkpoint settling within eight pixels only when the actual player is equally close in the requested frame. This handles the VVVVVV entrance save changing Y=140 to Y=143; final wrong-warp validation and the single target reset remain intact.

- Retry transient active-save reads for up to 200 ms during checkpoint writes, requiring complete successful validation and retaining strict rejection of foreign saves and integrity errors.

- Fixed native object-index relocation in mixed chest rewards and Kracko/Kid Icarus validation when whole background sets are shuffled; existing saved assignments remain unchanged.

- Fix a freeze when complete backgrounds and fast chest animations are enabled together: tolerate MMF's relocated object-list cache index while still validating object IDs, opcodes and parameters before any patch. Apply the ABI-compatible fix to both known older native builds without changing saved run rules.

- Add independent temporary graphics switches to diagnostics. Changes apply at the next level resource load and reset when loading a save; seeded rules remain unchanged. Problem reports include a game-window-only screenshot when available, the active background and bounded graphics history. All five UI languages are supported.
- Draw imported scenery behind retained original decoration and collision tiles, fixing a missing lower background detail in World 3.

- Restore World 3 cloud perspective by preserving the native colour-key mask instead of alpha transparency. Compare every native scanline with the original, including resets and save switches; repair the texture output of existing saved runs without changing their seeded mappings.

- Shuffle nine reviewed world backgrounds as complete sets, including their clouds and native parallax animation. Preserve collision geometry and restrict incompatible scroll combinations. Rebind animated objects after reset and refresh Parallaxer's texture when switching runs without restarting. Keep background dimming and all five UI languages.

- Create, delete, load and switch compatible native saves without restarting Boshy. A game-thread menu transaction reloads the selected save/profile and resets per-run reward, hack, music, shot, spider, graphics and trigger state. Incompatible archived native patches retain the cold-start fallback.
- F2 dismisses the victory presentation and returns to the menu without reopening the old result over the intro. Saved victory summaries remain available on demand.
- Extend Kracko's confirmed zero-HP animation window to four seconds; verified in a real isolated fight.
- Add Boss Rush and Level Rush with configurable pools/counts, seven by default, followed by Solgryn. Exclude Tutorial from new routes and encode the new modes in BR12 share codes.
- Group and highlight Target Select goals, and show Rush routes in the internal and OBS trackers. Preserve ordinary speedrun categories.

- Menu: corrected direct slot 1/3 selection, recoverable selection feedback, automatic layout for smaller windows, and locally saved text size through Aa.
- Normal mode: optional seeded character rotation between levels and boss rooms, persistent across saves, with new unlocks included and F3 locked while enabled.
- Add Normal mode with original progression and chest rewards, optional starting character and hacks, localized menu controls, portable settings and save-local tracking. Teleport Room restrictions and randomized routes stay disabled in this mode.

- Reject unlisted Teleport Room shortcuts and return to the last confirmed save, without advancing the route or rerolling characters. Keep registered hub exits available and show a brief native, non-interactive top-left notice.

- Reload each routed destination once before confirming arrival to prevent collision-related wrong warps. Verify the actual Player position in coordinate-based stages, preserve fixed boss starts, and keep reset recovery inside the pending transition.

- Add a hidden-window Ctrl+Alt+M problem marker with up to two minutes of bounded diagnostic history, seed, active hacks and positions. Background report exports leave ongoing recordings and game focus intact.
- Add separate trigger-to-request, loading and total transition measurements to diagnostics and exported reports, localized in all five supported UI languages.

- Extend Old Sonic’s zero-HP death-animation delay from three to six seconds before advancing to the next randomizer spot.

- Reduce transition latency by removing the focus delay, retaining validated object references for absent optional save groups, and counting observation work toward the polling interval. Existing trigger positions and death-animation guards remain unchanged.

- Replace nested legacy seed formats with a single compact BR9 code containing every current setting, rule identity and checksum. Old share codes are intentionally no longer supported.

- Add the ten missing original-game boss icons to the desktop and OBS trackers, including beta bosses and miniboss stages.

- Keep Kappa’s reward screen in his boss stage. Randomize only at the Teleport Room exit, including saved runs.

- Refined the victory screen with the Randomizer logo, translucent statistics, and a hoverable full-seed copy button. It appears five seconds later while the ending animation and credits continue.

- Split Justin.tv and Kappa into separate selectable stages. Start Kappa on the confirmed Speak button, require an active encounter and the native death animation, and reject death/reset false positives.
- Refine Kid Icarus and Cheetahman starts using player-confirmed positions. Keep Mario Desert at the bottom-left save hole, including return visits in Target Select.
- Keep randomized background music looping and reserve its native channel against automatic sound effects. Explicit stop, pause and volume controls remain native.
- Deliver and acknowledge timed, death and stage shot-style changes through a dedicated control command; repair the same transport for existing saved runs.
- Reload the spider image when the scene image bank changes. Preserve its saved timer and gameplay rules.
- Generate a fresh seed after preparing a new run while preserving chosen options. Include Kappa in shared seeds and all five UI languages.
- Discard captured exits from an earlier generation when a transition reloads the same room.

## 2026-10-15 — Boshy, Reborn · Linux release

- Close the original informational “Playable characters” notice only when it belongs to the active Boshy process, preventing blocked startup/loading focus. Include trigger-audit fingerprint resources in the Debian package.

- Add the original spider and roar as an optional surprise in levels and bosses, enabled for new runs. Attacks use independent random intervals of 5–30 active gameplay minutes, no warning, normal lethal contact, spawn/death grace and God Mode protection. Preserve its timer per save; remember a confirmed opt-out for future runs. Extract both assets from the user's verified game locally.
- Include the spider switch in compact BR7 seeds and all five UI languages. Existing runs retain their previous settings.
- Add optional music information to the live tracker. Cache the reward catalogue and shared seed, and shorten safe INI group reads while retaining torn-read/reset checks.
- Preserve the original music sample priority flag and use each saved run's frozen music mapping in the tracker.

- Add an optional music hack, off by default, with a combined pool of 45 level and boss tracks. A separate versioned seed permutation maps every track to another. Extract audio only from the verified user-supplied executable, play on the original music channel, and retain dialogue, item sounds and short jingles. Include the setting in compact shared seeds and all five UI languages.
- Intercept allowed native room-exit requests before the original destination loads. Arm only after the existing origin gate is established; retain death/reset checks, completion receipts, reward-dialog handling and a bounded fallback to the original exit. Tower position checks, miniboss sequences and Old Sonic's death-animation delay retain their existing gates.
- Preserve reserved shot-style and transition controls when submitting a character change. Keep the existing boss intro skip, including Questionmark and Ridley, unchanged.

- Add subtle looping cloud wisps, stars and desert dust to the four native intro themes. Preload a bounded image set and reuse it without per-frame file reads or allocations. Keep effects behind the native actors and text, pause them in modal dialogs or while unfocused, and retain static scenery if effect data is invalid. Add stable, brightness-aware shading behind the update text and top navigation hints.

- Pair intro backgrounds and floor textures from Green Greens, Wario, Ninja Gaiden and the desert. Choose a different theme on each host launch and preserve it across internal loading restarts. Keep original platform dimensions, hotspots and alpha outlines; validate the complete native image plan before applying it and retain original scenery on invalid input. Game assets are extracted locally, never included in the package.

- Randomize the native intro actor and its two side characters from 22 original game characters. Avoid consecutive repeats per role, preserve original movement and timing, and retain the cast through internal loading restarts. Graphics are extracted locally from the verified user-supplied game; cosmetic choices never change shared seeds or unlocks. Invalid intro data falls back to the original sprites.

- Preview imported seed settings before applying; compact BR5 share codes include exporter version and a game-rule fingerprint. BR2/3/4 remain readable.
- Context help follows mouse and keyboard focus. Advanced changes can be applied, discarded or edited further in all five UI languages.
- Trigger diagnostics distinguish arrival/reset guards, boss intros, death animations and confirmed exits; exported reports include structured evidence.

- Add native mouse hover and consistent keyboard focus. Arrows navigate without changing options; Enter/click confirms, Tab/Shift+Tab traverse controls, and Page Up/Down switches Advanced pages.
- Show shot-style modes in a dedicated picker: off, random interval, each spot, each death, or death and spot. Keep the editable interval limit separate.
- Add explicit pickers for difficulty, mode and numeric route/target counts.

- Protect committed transitions with an acknowledged native gameplay/input pause, released on scene change or after a two-second watchdog timeout.
- Automatically preserve recent diagnostic context in an error ZIP; add an export button in the debug window.
- Open completed saves directly in their stored run results.
- Add a per-spot debug test overview that distinguishes simulated logic checks, controlled in-game tests and natural gameplay exits.

- Keep the confirmed Solgryn result available through ending scenes without gameplay INI objects. Stop gameplay reads after the saved victory, preserve the final statistics, and show the result screen instead of restarting after an `Ini++` lookup failure.

- Dispatch validated native room exits immediately instead of waiting two seconds, preventing an avoidable fight with the destination boss when one-hit bosses are enabled. Apply the timing fix to existing saved rules without changing seed routes; retain arrival/reset guards and Old Sonic’s three-second death animation.

- Split Random World into separately selectable parts, using the live-confirmed second-part entrance at frame 23, position 16 / 1679. Route version 7 detects the native room transition with arrival/reset protection; older seeds retain the combined stage. Compact BR4 seeds also carry the new route revision.

- Detect Old Sonic’s native HP reaching zero after a living encounter, show his death animation for three seconds, then continue the route. Apply the fix to existing runs while preserving their seeds and saved rules.
- Keep Old Sonic’s confirmed native exit as a recovery path; do not discard the victory if the following Endless room immediately kills the player.
- Verify Bomberman’s fall exit leads to Ninja Gaiden, already handled by the existing route.
- Split Kid Icarus into its approach, miniboss encounter and remaining level to Ganon. The miniboss is selectable in Advanced and Target Select.
- Use native encounter and exit objects to confirm victory only after all enemy fragments are gone; arrivals and resets do not complete the stage.
- Retry interrupted INI memory observations during resets instead of terminating the run.
- Discard inconsistent INI snapshots during checkpoint saves and retry partial numeric fields instead of closing the game (including the observed invalid room value `po`).
- Add compact BR4 seeds for route version 6; existing BR2/BR3 codes and stored run rules remain compatible.

## 2026-10-13 — Linux package revision 2

- Focus the game at startup and return focus once if the live tracker appears later.
- Fix new-run startup when the game creates a metadata-only save stub; preserve real saves.
- Add compact BR3 share codes: 18 characters for the standard configuration, with settings and checksum included. Existing BR2 codes remain importable.
- Improve the seed dialog with larger text, character count, adaptive layout and invalid-code feedback.
- Verify 41 automated tests, including randomized seed compatibility checks.
- Windows support will follow. The original game remains a separate user-supplied import.

## 2026-10-13 — Linux Debian package preparation

- Add a game-free Debian package with Wine and Lutris dependencies.
- Add first-run folder/ZIP import into a private copy; keep original saves and profiles untouched.
- Provision checksum-pinned Wine Staging 11.2 WoW64, matching the reference installation.
- Replace machine-specific launch paths with checked per-user runtime paths and portable PE helpers.
- Add visible Wine setup progress and importer protection tests.
- Fix missing exported runtime modules/loading metadata, encrypted fresh options and empty engine-created save slots.
- Windows support will follow in a later release.

## 2026-10-13 — Native Linux development

- Add automatic English, German, Russian, Spanish and Japanese UI selection with English fallback.
- Localize randomizer save/setup dialogs, advanced rules, seed validation, loading cover, live tracker and optional debug window.
- Use a CJK-capable font and character wrapping for Japanese; fit longer menu labels to their cells.
- Keep the native update message and changelog in English.
- Preserve seed serialization, gameplay rules and existing run snapshots across languages.
- Prepare a source-only GitHub tree, localization CI and a release checklist; no portable package is claimed yet.

### Earlier native work

- Add the original animated menu integration, native update message and removal of the unavailable Online entry.
- Add independent saves and character profiles, BR2 sharing and advanced route pools.
- Replace pixel-trigger transitions with validated engine-state gates, including miniboss and beta boss handling.
- Add optional projectile styles, configurable random timers, presets, training/comfort hacks, run results and debug recordings.
