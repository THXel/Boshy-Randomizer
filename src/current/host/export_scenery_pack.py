"""Export one private reproducible Fusion visual run from its complete BR12 seed.

Does not replace installations, launch games, or require recompiling in Fusion.
The full menu/music/custom-blood migration remains outside this prototype.
"""

import argparse
import configparser
import hashlib
import io
import json
import runpy
import tempfile
from pathlib import Path
from export_route_probe import plan, save_text, REPO
from run_settings import decode, normalize
from visuals.actor_palettes import settings, GROUP
from visuals.scenery_pack import prepare
from build_profiles import executable

ORIGINAL = Path(
    "/home/thxel/.local/share/boshy-randomizer/IWBTB/I Wanna Be The Boshy.exe"
)


def export(shared, out, source=None):
    seed, options = decode(shared)
    options = normalize(options)
    out = Path(out).resolve()
    if out.exists():
        raise FileExistsError(
            "Refusing to overwrite an existing visual run: " + str(out)
        )
    raw, audit = prepare(executable("actors"), ORIGINAL, seed, options["extras"])
    p = plan(shared, audit["sha256"], audit["sha256"], source)
    p["actor_settings"] = settings(
        seed,
        options["extras"].get("sprite_scenery", False)
        and options["extras"].get("sprite_actors", False),
    )
    p["scope"] = (
        "Private native route/actor/scenery run; music, custom blood and other extras are not applied"
    )
    p["visual_pack"] = {
        "seed": seed,
        "cloned_images": len(audit["changed"]),
        "game_sha256": audit["sha256"],
    }
    del p["binding"]
    p["binding"] = hashlib.sha256(
        json.dumps(p, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    c = configparser.ConfigParser(interpolation=None)
    c.optionxform = str
    c.read_string(save_text(p))
    c.read_dict({GROUP: p["actor_settings"]})
    buf = io.StringIO()
    c.write(buf, space_around_delimiters=False)
    rc4 = runpy.run_path(str(REPO / "src/shared/PY/rc4_utils.py"))["rc4_crypt"]
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".visual-export-", dir=out.parent) as tmp:
        folder = Path(tmp) / "run"
        folder.mkdir()
        (folder / "Boshy.exe").write_bytes(raw)
        (folder / "SaveFile1.ini").write_bytes(
            rc4(b"BLOB", buf.getvalue().replace("\n", "\r\n").encode("latin1"))
        )
        (folder / "plan.json").write_text(json.dumps(p, indent=2) + "\n")
        (folder / "visual-audit.json").write_text(json.dumps(audit, indent=2) + "\n")
        folder.rename(out)
    return {
        "path": str(out),
        "game_sha256": audit["sha256"],
        "cloned_images": len(audit["changed"]),
        "scope": p["scope"],
    }


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--shared-seed", required=True)
    p.add_argument("--out", required=True, type=Path)
    p.add_argument("--source")
    a = p.parse_args()
    print(json.dumps(export(a.shared_seed, a.out, a.source), indent=2))
