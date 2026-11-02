# Current runtime source

`src/current/host/` contains the maintained menu, save transactions, route and reward rules, presentation, tracker and installation code for the first final version. `src/current/shared/` contains its shared helpers and changed textual catalogues. `source.json` records the exact files and their hashes.

The original game, compiled game patch, imported soundpacks, private saves and installer binaries are not in this source snapshot. Game artwork is read from the user's supported original copy. The parser under `host/KlikBack/` retains its upstream GNU GPL version 3 license; it is not covered by a blanket license claim for original project code.

Run `python tools/check_current.py` to check source hashes, Python syntax and the explicit game-free regression subset. These checks use temporary configuration and cannot accidentally use a developer's installed game. Tests requiring original artwork, the compiled game, Windows, Wine or interactive play remain separate checks. The test script states that boundary in its output.

The earlier flat runtime in `src/python/` and `src/native/` is retained for its saved-run contracts and existing regression tests. `tools/build.py` builds that earlier runtime; it does not produce the current game patch. The workflow checks both trees separately. Do not substitute an earlier package for the current installer.

The 1.0.0 release keeps the reviewed game executable from the final development build and updates the host, release identity, installer metadata and five-language menu history. The release verification record records the tests actually performed. A full natural playthrough of every boss/route/seed combination is not claimed.

Use the installers attached to the 1.0.0 release. This source check does not build or publish installers, and the older runtime build is not a substitute for the current game patch.
