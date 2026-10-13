# Changelog

All update logs remain in English, regardless of the UI language.

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
