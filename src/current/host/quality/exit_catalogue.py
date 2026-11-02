"""One complete regression checklist derived from the actual station registry.

Natural victories and fixture-assisted tests are explicitly different evidence.
An absent report remains pending; reaching a boss room is never a victory.
"""

from transition.router import NAMED_STAGES, CATALOGUE_HASH

COMMON = (
    "native_exit",
    "arrival_matches_route",
    "exactly_one_advance",
    "death_retry_at_source",
    "death_retry_at_destination",
    "saved_resume",
)
SPECIAL = {
    "old_sonic": ("complete_natural_fight", "launch_platforms", "death_screen"),
    "sonic": ("complete_natural_fight", "shrinking_platform", "fire", "death_screen"),
    "mario": ("complete_natural_fight", "final_phase_mobs", "pipe"),
    "kracko": ("complete_natural_fight", "next_screen_crossing"),
    "solgryn": (
        "complete_natural_fight",
        "climbing_fire",
        "rainbow_result",
        "credits_close_button",
        "f2_clears_result",
    ),
}


def checklist():
    return {
        "schema": 1,
        "catalogue_sha256": CATALOGUE_HASH,
        "stations": [
            {
                "position": name,
                "id": row["id"],
                "frame": row["frame"],
                "internal_frames": row["frames"],
                "original_exit_frames": row["native_exit_frames"],
                "checks": {
                    key: {"status": "pending"} for key in COMMON + SPECIAL.get(name, ())
                },
            }
            for name, row in sorted(
                NAMED_STAGES.items(), key=lambda pair: pair[1]["id"]
            )
        ],
    }


def verify_evidence(matrix, game_sha256):
    expected = checklist()
    if matrix.get("catalogue_sha256") != expected["catalogue_sha256"]:
        raise ValueError("Exit catalogue changed; coverage needs a new review")
    actual = {r["position"]: r for r in matrix["stations"]}
    if len(actual) != len(matrix["stations"]) or set(actual) != {
        r["position"] for r in expected["stations"]
    }:
        raise ValueError("Incomplete or duplicate station coverage")
    pending = []
    for row in expected["stations"]:
        for check in row["checks"]:
            evidence = actual[row["position"]]["checks"].get(check, {})
            if not (
                evidence.get("status") == "passed"
                and evidence.get("game_sha256") == game_sha256
                and evidence.get("report")
                and (
                    check != "complete_natural_fight"
                    or evidence.get("memory_writes") == 0
                )
            ):
                pending.append(row["position"] + ":" + check)
    return pending
