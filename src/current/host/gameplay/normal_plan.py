"""Original progression with optional deterministic character cycling.

Native character order rotates through seed-ranked available characters on each
playable scene change. Restart, death, menu and dresser visits do not advance it.
This native Normal-mode ordering is distinct from old injected character cycling.
"""

from gameplay.cycle_plan import order, STARTERS
from gameplay.characters import ROSTER, profile_text
from transition.router import STAGES

GROUP = "FusionNormalV1"
RANKS = "FusionNormalRanksV1"
FRAMES = sorted({f for s in STAGES.values() for f in s["frames"]} | {9, 36})


def settings(seed, enabled):
    return {
        GROUP: dict(Schema=1, Enabled=1, Characters=int(enabled)),
        RANKS: (
            {
                f"{f}_{ROSTER[n]}": rank
                for f in FRAMES
                for rank, n in enumerate(order(seed, f), 1)
            }
            if enabled
            else {}
        ),
    }


def choose(seed, frame, step, unlocks, previous):
    names = order(seed, frame)
    candidates = [
        n
        for n in names
        if n != previous and (n in STARTERS or str(unlocks.get(n.lower(), 0)) == "1")
    ]
    name = min(candidates, key=lambda n: (names.index(n) + 1 - step) % len(ROSTER))
    return dict(name=name, id=ROSTER[name])


def profile(choice, enabled):
    result = profile_text(choice)
    if enabled:
        result += f"\r\n[{GROUP}]\r\nSchema=1\r\nCharacters=1\r\nLastFrame=3\r\nLastDeaths=0\r\nStep=1\r\n"
    return result


def validate(plan, c, license):
    if plan.get("normal_schema") != 1 or plan["route"] or plan["source"] != "save1.ini":
        raise ValueError("Invalid Normal-mode plan")
    enabled = plan["options"]["characters"]
    for group, values in settings(plan["seed"], enabled).items():
        if not c.has_section(group) or dict(c[group]) != {
            k.lower(): str(v) for k, v in values.items()
        }:
            raise ValueError("Changed Normal-mode settings")
    if enabled:
        if (
            license.getint(GROUP, "Schema", fallback=0) != 1
            or license.getint(GROUP, "Characters", fallback=0) != 1
        ):
            raise ValueError("Invalid Normal character profile")
        if (
            license.getint(GROUP, "LastFrame") not in FRAMES
            or not 1 <= license.getint(GROUP, "Step") <= len(ROSTER)
            or license.getint(GROUP, "LastDeaths") < 0
        ):
            raise ValueError("Invalid Normal character progress")
