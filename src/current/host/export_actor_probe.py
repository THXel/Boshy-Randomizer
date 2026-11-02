"""Export a private actor-palette fixture, explicitly separate from other extras."""

import configparser
import hashlib
import io
import json
import runpy
from pathlib import Path
from build_profiles import profile, executable
from export_route_probe import plan, save_text, ROOT, REPO
from visuals.actor_palettes import settings, GROUP
from run_settings import encode, normalize

OUT = ROOT / "outputs/Fusion-Actors-20261023"


def export_actor(shared, out, source, build="actors"):
    game = executable(build)
    digest = hashlib.sha256(game.read_bytes()).hexdigest()
    p = plan(shared, digest, profile(build)["sha256"], source)
    ex = p["options"]["extras"]
    p["actor_settings"] = settings(
        p["seed"], ex.get("sprite_scenery", False) and ex.get("sprite_actors", False)
    )
    p["scope"] = (
        "native_actor_palette_test; scenery, music, custom blood and other extras are NOT applied"
    )
    pack = profile(build).get("visual_pack")
    if pack:
        if p["seed"] != pack["seed"] or any(
            ex.get(k) != v for k, v in pack["options"].items()
        ):
            raise ValueError("Save settings do not match seed-local graphics pack")
        p["visual_pack"] = pack
        p["scope"] = (
            "native actor palettes and cloned scenery; music/custom blood are NOT applied"
        )
    blood = profile(build).get("blood_pack")
    if blood:
        p["blood_settings"] = blood["settings"]
        p["blood_pack"] = blood["pack"]
        p["scope"] = (
            "private native routes, actors, scenery and player-owned blood; original game audio"
        )
    music = profile(build).get("music_pack")
    if music:
        if p["seed"] != profile(build)["music_seed"] or not ex.get("music"):
            raise ValueError("Save settings do not match seed-local music")
        p["music_pack"] = music
        p["scope"] = (
            "private native routes, actors, scenery, player blood and category-safe music"
        )
    del p["binding"]
    p["binding"] = hashlib.sha256(
        json.dumps(p, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    c = configparser.ConfigParser(interpolation=None)
    c.optionxform = str
    c.read_string(save_text(p))
    c.read_dict({GROUP: p["actor_settings"]})
    if blood:
        c.read_dict({"FusionBloodV1": p["blood_settings"]})
    buf = io.StringIO()
    c.write(buf, space_around_delimiters=False)
    rc4 = runpy.run_path(str(REPO / "src/shared/PY/rc4_utils.py"))["rc4_crypt"]
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    (out / "SaveFile1.ini").write_bytes(
        rc4(b"BLOB", buf.getvalue().replace("\n", "\r\n").encode("latin1"))
    )
    (out / "plan.json").write_text(json.dumps(p, indent=2))
    return p


if __name__ == "__main__":
    scenes = [
        "prehistorik-routes",
        "castlevania-routes",
        "secret-mario-routes",
        "hellokitty-routes",
        "dedede-fight-routes",
        "sonic-routes",
        "oldsonic-routes",
        "finale-routes",
    ]
    for scene in scenes:
        source_plan = json.loads(
            (
                ROOT
                / "outputs/Fusion-RouteCoverage-20261023"
                / ("seed-guards-" + scene)
                / "plan.json"
            ).read_text()
        )
        for enabled in [False, True]:
            options = normalize(
                {
                    **source_plan["options"],
                    "extras": {
                        **source_plan["options"]["extras"],
                        "sprite_scenery": enabled,
                        "sprite_actors": enabled,
                    },
                }
            )
            mode = "on" if enabled else "off"
            p = export_actor(
                encode(source_plan["seed"], options),
                OUT / ("seed-" + scene + "-" + mode),
                source_plan["source"],
            )
            print(scene, mode, p["actor_settings"]["Enabled"])
