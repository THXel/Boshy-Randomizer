"""Assemble the DEB that provisions the reviewed Wine runner as its user."""

import argparse
import json
import os
import shutil
import subprocess
from pathlib import Path
from distribution.identity import VERSION, sha256
from distribution.artwork import build_artwork

DEB_REVISION = 1
# Semantic releases must sort after the earlier date-numbered test packages.
DEB_EPOCH = 1


def build(lab, shared, setup, output):
    lab, shared, setup, output = map(Path, (lab, shared, setup, output))
    root = output / "deb-root"
    if root.exists():
        raise FileExistsError(root)
    app = root / "usr/share/boshy-randomizer-native"
    app.mkdir(parents=True)
    shutil.copy2(lab / "distribution/linux/launcher.py", app / "launcher.py")
    for name in ("setup_window.py", "lifecycle.py", "language.py", "translations.json"):
        shutil.copy2(lab / "distribution/linux" / name, app / name)
    shutil.copy2(
        lab / "distribution/linux/lutris_artwork.py", app / "lutris_artwork.py"
    )
    build_artwork(shared / "assets/Custom/boshy_randomizer.png", app / "artwork")
    icon = root / "usr/share/icons/hicolor/128x128/apps/boshy-randomizer-native.png"
    icon.parent.mkdir(parents=True)
    shutil.copy2(app / "artwork/icon.png", icon)
    shutil.copy2(
        lab / "distribution/lutris-settings.json", app / "lutris-settings.json"
    )
    shutil.copy2(shared / "src/python/app/wine_setup.py", app / "wine_setup.py")
    shutil.copy2(
        shared / "assets/catalogues/wine-runner-manifest.json",
        app / "wine-runner-manifest.json",
    )
    shutil.copy2(setup, app / "BoshyRandomizer-Setup.exe")
    (app / "package-info.json").write_text(
        json.dumps({"version": VERSION, "setup_sha256": sha256(setup)}, indent=2)
    )
    binary = root / "usr/bin/boshy-randomizer-native"
    binary.parent.mkdir(parents=True)
    binary.write_text(
        '#!/bin/sh\nexec /usr/bin/python3 -B /usr/share/boshy-randomizer-native/launcher.py "$@"\n'
    )
    binary.chmod(0o755)
    desktop = root / "usr/share/applications/boshy-randomizer-native.desktop"
    desktop.parent.mkdir(parents=True)
    desktop.write_text("""[Desktop Entry]
Type=Application
Name=Boshy Randomizer
Comment=Play and configure Boshy Randomizer
Comment[de]=Boshy Randomizer spielen und einrichten
Exec=boshy-randomizer-native
Icon=boshy-randomizer-native
Terminal=false
Categories=Game;
Actions=Setup;Remove;

[Desktop Action Setup]
Name=Install or update
Name[de]=Einrichten oder aktualisieren
Exec=boshy-randomizer-native --setup

[Desktop Action Remove]
Name=Uninstall game
Name[de]=Spiel deinstallieren
Exec=boshy-randomizer-native --remove
""")
    control = root / "DEBIAN/control"
    control.parent.mkdir()
    control.write_text(f"""Package: boshy-randomizer-native
Version: {DEB_EPOCH}:{VERSION.replace("-preview.", "~preview.")}-{DEB_REVISION}
Section: games
Priority: optional
Architecture: amd64
Maintainer: THXel
Depends: lutris, python3 (>= 3.12), python3-tk, python3-yaml, wmctrl, ca-certificates, libasound2t64 | libasound2, libpulse0, libgl1, libvulkan1, libfreetype6, libx11-6, libxext6, libxrandr2
Description: Boshy Randomizer
 Imports an original Boshy ZIP or folder and applies the randomizer patch.
 First normal-user setup provisions verified Wine Staging 11.2 and opens
 Lutris registration with the reviewed game settings. No root-side downloads.
""")
    target = output / (
        "boshy-randomizer_" + VERSION + "-" + str(DEB_REVISION) + "_amd64.deb"
    )
    subprocess.run(
        [
            "dpkg-deb",
            "--root-owner-group",
            "--build",
            "-Zxz",
            "-z1",
            str(root),
            str(target),
        ],
        check=True,
        env={**os.environ, "TMPDIR": str(output.resolve())},
    )
    return target


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("lab", "shared", "setup", "output"):
        parser.add_argument("--" + key, type=Path, required=True)
    print(build(**vars(parser.parse_args())))
