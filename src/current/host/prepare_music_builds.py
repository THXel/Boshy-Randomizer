"""Reproducible, private soundtrack fixtures on the verified blood builds."""

import hashlib, json
from pathlib import Path
from build_profiles import LAB, PREFIX, profile, executable
from music.soundtrack import prepare, PACKS

ROOT = LAB.parents[1]
OUT = ROOT / "outputs/Fusion-Music-20261024"
SEED = "fusion-scenery-20261023"
INSTALLED = Path("/home/thxel/.local/share/boshy-randomizer/soundpacks")


def main():
    OUT.mkdir(exist_ok=True)
    hashes = {}
    for pack in PACKS:
        previous = profile("blood-" + pack)
        base = executable("blood-" + pack)
        raw, audit = prepare(base, previous["sha256"], SEED, pack, INSTALLED / pack)
        target = PREFIX / "drive_c/BoshyTransitions" / ("Boshy-music-" + pack + ".exe")
        target.write_bytes(raw)
        (OUT / (pack + "-audit.json")).write_text(json.dumps(audit, indent=2) + "\n")
        updated = dict(
            {k: v for k, v in previous.items() if not k.startswith("live_")},
            sha256=audit["sha256"],
            music_pack=pack,
            music_seed=SEED,
            music_audit=str(OUT / (pack + "-audit.json")),
            live_verified=False,
            scope="private native routes, actor palettes, scenery, player blood and category-safe music",
        )
        # Match the profile's explicit executable identity field.
        for key in ("game_sha256", "rebuilt_sha256", "exe_sha256"):
            if key in updated:
                updated[key] = audit["sha256"]
        (LAB / ("route-build-music-" + pack + ".json")).write_text(
            json.dumps(updated, indent=2) + "\n"
        )
        hashes[pack] = audit["sha256"]
        print(
            pack,
            audit["sha256"],
            "music",
            len(audit["changed"]),
            "unchanged effects",
            audit["unchanged_sound_effects"],
            flush=True,
        )
    p = LAB / "build_profiles.py"
    text = p.read_text()
    entries = "".join(
        '    "music-'
        + pack
        + '": ("route-build-music-'
        + pack
        + '.json", "Boshy-music-'
        + pack
        + '.exe", "-music-'
        + pack
        + '"),\n'
        for pack in PACKS
    )
    if '"music-original"' not in text:
        p.write_text(text.replace("BUILDS = {\n", "BUILDS = {\n" + entries))
    p = LAB / "phase_state.py"
    text = p.read_text()
    anchor = (
        '"b13b8c524871f35f919c22b7b48a39c86312cc928e2b87a7e474858a939ff046": 0xA35DC,'
    )
    text = text.replace(
        anchor,
        anchor
        + "".join(
            '\n            "' + h + '": 0xA35DC,'
            for h in hashes.values()
            if h not in text
        ),
    )
    p.write_text(text)


if __name__ == "__main__":
    main()
