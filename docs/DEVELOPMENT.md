# Working on Boshy Randomizer

## Source layout

| Directory | Purpose |
| --- | --- |
| `native-linux/` | Current shared runtime for **both Linux and Windows**, native patches and tests. The directory name is historical. |
| `native-linux/PY/` | Shared save/INI helpers, platform access and the live tracker. These modules remain active dependencies. |
| `packaging/` | Linux package, Windows installer, shared payload selection, website generation and release publication. |
| `site/` | Website translations, styles, scripts and public gallery media. |
| `docs/` and `README/` | Build/verification notes and translated project documentation. |
| `Custom/` | Public website branding and credits only. Runtime assets are in `native-linux/Custom/`. |

The old root GUI, Twitch chat listener, pixel-trigger engine, installer EXEs,
bytecode caches and outdated GUI media have been removed. Their history remains
in Git. Release installers belong in **GitHub Releases**, not the source tree.

Do not remove a module solely because its name looks old: frozen run rules,
compatibility readers and shared tracker/save helpers still have callers.
Existing player saves, local game copies and downloaded soundpacks are not source
files and must not be added to Git or altered during repository cleanup.

## Build and test

On Ubuntu 24.04 / a compatible Linux build environment:

```sh
sudo apt-get install gcc-multilib binutils gcc-mingw-w64-x86-64 ffmpeg
python3 -m pip install pillow numpy psutil python-xlib
python3 native-linux/build_runtime.py
python3 -m unittest discover -s native-linux/tests -v
python3 packaging/build_deb.py dist
python3 packaging/export_windows.py windows-payload
```

The native build binds the generated DLL hashes to the runtime checks. Never
hand-edit those hashes to bypass a failed integrity check. No original Boshy
installation is needed for these automated checks; gameplay testing requires a
separate imported game copy.

`packaging/payload.py` selects the public assets for both platforms. It explicitly
lists maintained `PY` helpers and the three public `INI` catalogues. Private
configuration, live tracker state and retired Twitch modules are excluded even
if they exist in a developer's directory. Update the allowlist and tests when
adding a shared helper.

Source CI rebuilds the native payloads, runs tests and exports both package
formats. A release is published only when `packaging/release.json` changes or
when the release workflow is explicitly dispatched. Regular source cleanup does
not replace already published installers.

See [Windows packaging](WINDOWS_PACKAGE.md) for the Windows installer build and
[Linux packaging](LINUX_PACKAGE.md) for first-run setup and platform requirements.

## Website and translated READMEs

Edit `site/content.json` and `packaging/render_site.py`, then run:

```sh
python3 packaging/render_site.py
```

Keep `Custom/` branding files referenced by the generated pages. Gallery media
belongs in `docs/media/` and `site/media/`; old GUI recordings are no longer used.
