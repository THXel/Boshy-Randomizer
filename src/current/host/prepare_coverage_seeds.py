"""Create explicit fresh fixture seeds with documented stage order."""

import json, sys
from pathlib import Path
from export_route_probe import export, ROOT
from route_cases import CASES
from run_settings import normalize, encode, route

OUT = ROOT / "outputs/Fusion-RouteCoverage-20261023"
GAME = Path(
    "/home/thxel/Games/clickteam-fusion-developer/drive_c/BoshyTransitions/Boshy-routes.exe"
)
CONFIG = {
    "dedede-shortcut-routes": (["save2.ini", "save1.ini"], []),
    "random1-bonus-routes": (["save9.ini", "save10.ini", "save1.ini"], []),
    "questionmark-routes": (["save7.ini", "save1.ini"], ["questionmark"]),
    "ridley-routes": (["save7.ini", "save1.ini"], ["ridley"]),
    "ninja-routes": (["save13.ini", "save22.ini", "save1.ini"], ["ninja_ryu"]),
    "kid-routes": (["save12.ini", "kid_icarus_after", "save1.ini"], ["kid_icarus"]),
    "kappa-routes": (["save17.ini", "save1.ini"], ["kappa"]),
    "random1-routes": (["save9.ini", "save10.ini", "save1.ini"], []),
    "random2-routes": (["save10.ini", "save1.ini"], []),
    "finale-routes": (["save1.ini"], []),
}
if __name__ == "__main__":
    base = json.loads(
        (ROOT / "outputs/Fusion-FrameLinks-20261023/seed-mario/plan.json").read_text()
    )["options"]
    for scene, (levels, bosses) in CONFIG.items():
        options = normalize(
            {
                **base,
                "level_pool": levels,
                "level_count": len(levels),
                "boss_pool": bosses,
                "route_boss_count": len(bosses),
            }
        )
        for i in range(1000):
            seed = "coverage-" + scene + "-" + str(i)
            actual = route(seed, options)
            if [s for s in actual if s in levels] == levels:
                break
        else:
            raise AssertionError("No fixture seed found")
        p = export(encode(seed, options), GAME, OUT / ("seed-" + scene), CASES[scene])
        print(scene, p["route"])
