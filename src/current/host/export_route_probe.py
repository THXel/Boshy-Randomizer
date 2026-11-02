"""Private Fusion V4 route test saves; gameplay randomizers are not yet applied."""

import argparse, configparser, hashlib, io, json, runpy, sys
from pathlib import Path
from transition.router import STAGES, CATALOGUE_HASH, GROUP
from build_profiles import profile as build_profile

from app_paths import ROOT, REPO
sys.path.insert(0, str(REPO / "src/python/rules"))
from run_settings import decode, normalize, route
from position_names import legacy_key, position_name


def plan(shared, game_hash, expected_hash, source=None):
    if not expected_hash or game_hash != expected_hash:
        raise ValueError("Untested Fusion route build")
    if not shared.startswith("BR12-"):
        raise ValueError("An existing BR12 seed is required")
    seed, options = decode(shared)
    options = normalize(options)
    if (
        options["mode"]
        not in ("randomizer", "boss_rush", "level_rush", "normal", "target")
        or options["route_version"] != 9
    ):
        raise ValueError("Requires current native route mode")
    ordered = route(seed, options)
    if options["mode"] not in ("normal", "target") and (
        not ordered
        or len(set(ordered)) != len(ordered)
        or ordered[-1] != "boss_solgryn.ini"
    ):
        raise ValueError("Invalid route")
    if any(spot not in STAGES for spot in ordered):
        raise ValueError("Unsupported route station")
    source = legacy_key(source) if source is not None else None
    source = source or (
        "save1.ini" if options["mode"] in ("normal", "target") else ordered[0]
    )
    if source not in (ordered or ["save1.ini"]):
        raise ValueError("Probe source is not in this seed")
    result = dict(
        scope="route_test_only_no_sprite_music_or_item_randomization",
        schema=4,
        seed=seed,
        shared_seed=shared,
        options=options,
        route=ordered,
        source=source,
        source_index=ordered.index(source) if ordered else 0,
        game_sha256=game_hash,
        catalogue_sha256=CATALOGUE_HASH,
    )
    result["binding"] = hashlib.sha256(
        json.dumps(result, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return result


def save_text(p):
    origin = STAGES[p["source"]]
    values = dict(
        Schema=0 if p["options"]["mode"] == "normal" else 4,
        CurrentStage=origin["id"],
        LevelsEnabled=int(p["options"]["levels"] and p["options"]["mode"] != "boss_rush"),
        Handled=0,
        Armed=0,
        KrackoVictory=0,
        KidSeen=0,
        Completed=0,
        Binding=p["binding"],
        Catalogue=CATALOGUE_HASH,
    )
    for source, target in zip(p["route"], p["route"][1:]):
        sid = str(STAGES[source]["id"])
        dst = STAGES[target]
        for key, field in [
            ("NextId", "id"),
            ("NextFrame", "frame"),
            ("NextX", "x"),
            ("NextY", "y"),
        ]:
            values[key + sid] = dst[field]
        values["Done" + sid] = 0
    c = configparser.ConfigParser(interpolation=None)
    c.optionxform = str
    c.read_dict(
        {
            "Check": {"SaveVersion": 1},
            "Stats": {
                "Deaths": 0,
                "Difficulty": p["options"]["difficulty"],
                "TimeSeconds": 0,
            },
            "Collectables": {"Awesomesauce": 0},
            "Positions": {
                "frame": origin["frame"],
                "xPos": origin["x"],
                "yPos": origin["y"],
            },
            GROUP: values,
        }
    )
    buf = io.StringIO()
    c.write(buf, space_around_delimiters=False)
    return buf.getvalue().replace("\n", "\r\n")


def export(shared, game, out, source=None, *, build="base"):
    profile = build_profile(build)
    if profile["catalogue_sha256"] != CATALOGUE_HASH:
        raise ValueError("Station catalogue differs from the compiled test build")
    with Path(game).open("rb") as f:
        digest = hashlib.file_digest(f, "sha256").hexdigest()
    p = plan(shared, digest, profile["sha256"], source)
    rc4 = runpy.run_path(str(REPO / "src/shared/PY/rc4_utils.py"))["rc4_crypt"]
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    (out / "SaveFile1.ini").write_bytes(rc4(b"BLOB", save_text(p).encode("latin1")))
    (out / "plan.json").write_text(json.dumps(p, indent=2))
    (out / "NOTICE.txt").write_text(
        "Private route test only. Sprite, music and item randomizers are not applied. Starts at the declared station; earlier stations have NOT been completed. Not a release.\n"
    )
    return p


if __name__ == "__main__":
    a = argparse.ArgumentParser(description=__doc__)
    a.add_argument("--shared", required=True)
    a.add_argument("--game", type=Path, required=True)
    a.add_argument("--out", type=Path, required=True)
    a.add_argument(
        "--source", choices=tuple(position_name(k) for k in STAGES) + tuple(STAGES)
    )
    args = a.parse_args()
    print(json.dumps(export(args.shared, args.game, args.out, args.source), indent=2))
