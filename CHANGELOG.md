# Changelog

All update logs remain in English, regardless of the UI language.

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
