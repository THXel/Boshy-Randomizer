"""Export fresh BR12 saves for the bounded native-exit matrix."""

import json
from pathlib import Path
from exit_matrix import MATRIX, target_for
from export_route_probe import export, ROOT
from run_settings import normalize, encode, route

OUT = ROOT / "outputs/Fusion-RouteCoverage-20261023"
GAME = Path(
    "/home/thxel/Games/clickteam-fusion-developer/drive_c/BoshyTransitions/Boshy-route-guards.exe"
)


def main():
    base = json.loads(
        (ROOT / "outputs/Fusion-FrameLinks-20261023/seed-mario/plan.json").read_text()
    )["options"]
    for scene, (source, boss, _) in MATRIX.items():
        out = OUT / ("seed-guards-" + scene)
        if out.exists():
            continue
        target = target_for(source)
        levels = ["save7.ini", target] if boss else [source, target]
        options = normalize(
            {
                **base,
                "level_pool": levels,
                "level_count": len(levels),
                "boss_pool": [boss] if boss else [],
                "route_boss_count": int(bool(boss)),
            }
        )
        for i in range(1000):
            seed = "exit-matrix-" + scene + "-" + str(i)
            ordered = route(seed, options)
            if source in ordered and ordered[ordered.index(source) + 1] == target:
                break
        else:
            raise AssertionError((scene, options, ordered))
        p = export(encode(seed, options), GAME, out, source, build="guards")
        print(scene, p["route"], flush=True)


if __name__ == "__main__":
    main()
