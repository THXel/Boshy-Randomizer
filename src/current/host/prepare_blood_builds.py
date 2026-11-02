"""Build and register hash-pinned private scenery/blood test variants."""

import hashlib, json, shutil
from pathlib import Path
from visuals.scenery_pack import prepare as scenery, BLOOD_BASE_SHA
from visuals.blood_pack import prepare as blood
from live_route_session import ROOT, PREFIX
from build_profiles import LAB

OUT = ROOT / "outputs/Fusion-Blood-20261024"
base = PREFIX / "drive_c/BoshyTransitions/Boshy-blood-base.exe"
original = Path(
    "/home/thxel/.local/share/boshy-randomizer/IWBTB/I Wanna Be The Boshy.exe"
)
previous = json.loads((ROOT / "outputs/Fusion-Scenery-20261023/audit.json").read_text())
raw, sa = scenery(base, original, previous["seed"], previous["options"])
source = OUT / "Boshy-blood-scenery.exe"
source.write_bytes(raw)
(OUT / "scenery-audit.json").write_text(json.dumps(sa, indent=2))
profiles = {}
for pack in ("original", "kamilia3", "wannafest22"):
    if pack == "original":
        data = raw
        audit = dict(
            pack=pack,
            sha256=sa["sha256"],
            settings=dict(Schema=1, Animation=0, LifeTicks=0),
            frames=0,
        )
    else:
        data, audit = blood(
            source, original, original.parents[1] / "soundpacks" / pack, sa["sha256"]
        )
    name = "blood-" + pack
    target = PREFIX / "drive_c/BoshyTransitions" / ("Boshy-" + name + ".exe")
    target.write_bytes(data)
    (OUT / (pack + "-audit.json")).write_text(json.dumps(audit, indent=2))
    profile = dict(
        sha256=audit["sha256"],
        runtime_root_rva=0xA35DC,
        text_sha256="d3ea604cfedac000b9b6b6ec01ad6ff966efa9a2aa7ca2abef84b3624f9947a4",
        scope="private native player blood, actor palettes and scenery; original game audio",
        visual_pack=dict(seed=previous["seed"], options=previous["options"]),
        blood_pack=audit,
    )
    (LAB / ("route-build-" + name + ".json")).write_text(json.dumps(profile, indent=2))
    profiles[name] = profile
    print(name, audit["sha256"], flush=True)
# Add exact output hashes only, never accept arbitrary modified builds.
p = LAB / "phase_state.py"
s = p.read_text()
mark = "        profiles = {\n"
for profile in profiles.values():
    entry = '            "' + profile["sha256"] + '": 0xA35DC,\n'
    if entry not in s:
        s = s.replace(mark, mark + entry)
p.write_text(s)
p = LAB / "build_profiles.py"
s = p.read_text()
mark = "BUILDS = {\n"
for name in profiles:
    entry = (
        '    "'
        + name
        + '": ("route-build-'
        + name
        + '.json", "Boshy-'
        + name
        + '.exe", "-'
        + name
        + '"),\n'
    )
    if entry not in s:
        s = s.replace(mark, mark + entry)
p.write_text(s)
