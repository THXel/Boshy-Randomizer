"""Explicit prepare/check workflow so an older open project cannot pass unnoticed.

Prepare fingerprints maintained source and embeds that identity in the generated
project. Check reads it back from the compiled frame events before recording the
binary hash. Live and release verification remain separate gates.
"""

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from distribution.identity import source_digest, sha256

LAB = Path(__file__).resolve().parents[1]


def stamp_sections(sections):
    stamp = os.environ.get("BOSHY_BUILD_SOURCE_SHA")
    if stamp is None:
        return sections
    if not re.fullmatch(r"[0-9a-f]{64}", stamp):
        raise ValueError("Invalid source build identity")
    from gameplay.native_events import Events
    from native_menu.events import INPUT
    from transition.events import string

    e = Events(sections, low=0xDF00, high=0xDFFF)
    return [
        *sections,
        [e.row([e.start()], [e.text(INPUT, "Build", "Source", string(stamp))])],
    ]


def prepare(original, output):
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    stamp = source_digest(LAB)
    with (output / "generation.log").open("w") as log:
        subprocess.run(
            [
                sys.executable,
                str(LAB / "recover_boshy_dynamic.py"),
                str(Path(original).resolve()),
                "--out",
                str(output / "project"),
            ],
            env={
                **os.environ,
                "BOSHY_BUILD_SOURCE_SHA": stamp,
                "PYTHONDONTWRITEBYTECODE": "1",
            },
            stdout=log,
            stderr=subprocess.STDOUT,
            check=True,
        )
    project = output / "project" / "I Wanna Be The Boshy.decompiled.mfa"
    manifest = {
        "schema": 1,
        "status": "prepared",
        "source_sha256": stamp,
        "project_sha256": sha256(project),
        "project": str(project),
    }
    (output / "build.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def complete_structure(app):
    """Reject compiler output that has a title stamp but unfinished asset banks."""
    from visuals.fusion25 import image_bank, property_bank
    from music.bank import read as sound_bank

    required = (0x2256, 0x2257, 0x6666, 0x5555, 0x6667, 0x5556, 0x6668, 0x5557)
    if app.stop != "terminator" or any(app.payload(cid) is None for cid in required):
        raise ValueError("Incomplete executable: compiler has not finished all banks")
    images, _ = image_bank(app.payload(0x6666), app.payload(0x5555))
    properties = property_bank(app.payload(0x2256), app.payload(0x2257))
    sounds, _ = sound_bank(app.payload(0x6668), app.payload(0x5557))
    frames = len(app.by_id.get(0x3333, []))
    if frames != app.app_header()["numberOfFrames"]:
        raise ValueError("Incomplete executable frame count")
    return dict(images=len(images), objects=len(properties), sounds=len(sounds), frames=frames)


def check(manifest_path, executable):
    from visuals.scenery_pack import App
    from quality.compiled_events import title_events

    manifest_path = Path(manifest_path)
    manifest = json.loads(manifest_path.read_text())
    if (
        source_digest(LAB) != manifest["source_sha256"]
        or sha256(manifest["project"]) != manifest["project_sha256"]
    ):
        raise ValueError("Sources or project changed after generation")
    before = sha256(executable)
    app = App(executable)
    structure = complete_structure(app)
    events = title_events(app)
    stamp = manifest["source_sha256"]
    if stamp.encode() not in events and stamp.encode("utf-16le") not in events:
        raise ValueError(
            "Wrong or stale project compiled: expected source stamp missing"
        )
    if sha256(executable) != before:
        raise ValueError("Executable changed during validation; compiler still running")
    result = {
        **manifest,
        "status": "compiled_identity_checked",
        "game_sha256": before,
        "structure": structure,
        "executable": str(Path(executable).resolve()),
    }
    manifest_path.write_text(json.dumps(result, indent=2) + "\n")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("prepare")
    p.add_argument("original", type=Path)
    p.add_argument("output", type=Path)
    p = sub.add_parser("check")
    p.add_argument("manifest", type=Path)
    p.add_argument("executable", type=Path)
    args = parser.parse_args()
    result = (
        prepare(args.original, args.output)
        if args.command == "prepare"
        else check(args.manifest, args.executable)
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
