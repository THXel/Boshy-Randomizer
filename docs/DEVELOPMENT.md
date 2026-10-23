# Working on Boshy Randomizer

## Source layout

Edit the maintained sources below. `build/runtime/` is generated and serves both
Linux and Windows. No game installation is needed to build or run automated tests.

| Directory | Responsibility |
| --- | --- |
| `src/python/app/` | Application entry points, first run and main controller |
| `src/python/menu/` | Menu state, rendering, navigation, loading cover and localization |
| `src/python/sessions/` | Save lifecycle, profile transactions, frozen rules and journals |
| `src/python/rules/` | Seeds, options, routes, bosses, rewards and completion rules |
| `src/python/gameplay/` | Running game, scene transitions, restart and spawn guards |
| `src/python/graphics/` | Sprite/background changes, intro and death visuals |
| `src/python/audio/` | Music, soundpacks and loading audio policy |
| `src/python/platform/` | Windows/Linux transport, process ownership and telemetry |
| `src/python/tracker/` | Separate live tracker and presentation |
| `src/python/diagnostics/` | Debug reports, graphics diagnostics and exit evidence |
| `src/shared/PY/` | Active INI, save and tracker helpers with stable import names |
| `src/native/` | C/assembly patches grouped into bridge, hooks, menu, gameplay, graphics, audio and diagnostics |
| `src/launchers/` | Linux entry scripts |
| `assets/` | Public runtime catalogues, translations, icons, font and artwork |
| `tests/runtime/` | Runtime regressions, native harnesses and historical rule fixtures |
| `tests/tooling/` | Build assembly, stale build detection and preservation checks |
| `tools/` | Source mapping and build entry point; `tools/native/` contains compiler helpers |
| `requirements/` | Development dependency lists |
| `packaging/` | Shared payload selection, Linux package, Windows installer and publication |
| `site/`, `docs/`, `README/`, `Custom/` | Website, documentation, public gallery and website branding |

See [Architecture](ARCHITECTURE.md) for the source/runtime boundary and the main
execution paths. Source modules are assembled into their stable runtime names;
the domain folders are not Python import namespaces.

## Build and test

On Ubuntu 24.04 / a compatible Linux build environment:

```sh
sudo apt-get install gcc-multilib binutils gcc-mingw-w64-x86-64 ffmpeg
python3 -m pip install pillow numpy psutil python-xlib
python3 tools/build.py
python3 -m unittest discover -s tests/tooling -v
python3 -m unittest discover -s build/runtime/tests -v
python3 packaging/build_deb.py dist
python3 packaging/export_windows.py windows-payload
```

`MINGW_CC` can select a particular MinGW compiler. `--assemble-only` prepares
Python, resources and tests on Windows without compiling native payloads; this
is not a package-ready build. Windows release jobs consume the payload compiled
on Linux and assemble source separately for their platform checks.

The build first creates a temporary sibling directory. Compilation failure keeps
the previous build intact. A successful build records source and output hashes
and replaces only the previous, verified generated tree. Local edits, unexpected
files, symlinks and private game/run directories block replacement. Move code
changes into their maintained source files before rebuilding. Never import a
game or store saves inside `build/runtime/`.

Package commands reject changed outputs, stale source and incomplete native
builds. The compiler binds generated DLL hashes to the generated integrity
checks; it does not rewrite maintained source files. Never hand-edit hashes to
bypass a failed check. `build/runtime/.build-metadata.json` stays out of installers.

`packaging/payload.py` remains the public payload boundary for both platforms.
Only the maintained `PY` helpers and three public `INI` catalogues are allowed.
Private settings, saves, downloaded soundpacks and Wine prefixes never belong in
Git or a package. For gameplay checks, use a separately imported test installation.

## Compatibility and cleanup

The source move preserves deployed filenames, module names, resource paths and
native include relationships. Saved rule bundles retain their own bytes and
hashes. Existing compatibility readers and targeted repairs remain active;
older-looking names such as `gastly_route_lab` and `lab` still have runtime callers.

The obsolete `build_menu.py` was removed: `build_runtime.py` already builds that
DLL along with the other payloads and binds their integrity hashes. Do not
reintroduce an independent partial build path. The old root GUI/Twitch modules
were removed in earlier cleanup; their history remains in Git.

An existing local `native-linux/` directory can contain private diagnostics,
imported games and frozen test runs from before this source migration. It is
ignored and is no longer a source or package input. Preserve that private data.

Source CI rebuilds and tests the runtime and exports both payloads. Publication
still requires a change to `packaging/release.json` or explicit release workflow
dispatch. A source cleanup does not replace published installers.

See [Windows packaging](WINDOWS_PACKAGE.md) and [Linux packaging](LINUX_PACKAGE.md)
for installer and first-run behavior.

## Website and translated READMEs

Edit `site/content.json` and `packaging/render_site.py`, then run:

```sh
python3 packaging/render_site.py
```

Keep public branding referenced by the generated pages. Gallery media belongs in
`docs/media/` and `site/media/`; these assets are separate from runtime resources.

Install formatting tools with `python -m pip install -r requirements/development.txt`, then run `python tools/check_style.py`. Optional soundtrack usage is documented in [MUSIC_CATEGORIES.md](MUSIC_CATEGORIES.md).
