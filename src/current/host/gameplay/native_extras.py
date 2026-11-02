"""Native mirror mode and persisted character selection after an actual death.

The death cycle uses a versioned small integer generator and seeded character
priorities. It never chooses a locked character or immediately repeats the
previous one. Scene reloads without a new death do not consume a choice.
"""

import hashlib
import struct
from gameplay.characters import ROSTER
from gameplay.cycle_plan import STARTERS
from gameplay.normal_plan import FRAMES
from gameplay.native_events import Events
from gameplay import profile_batch
from gameplay.rewards import ini_string
from transition.events import integer, ini_value, set_ini, string
from transition.router import frame_metadata, ini_expression

GROUP = "FusionExtrasV1"
STATE = "FusionDeathCycleV1"
MODULUS = 32749


def settings(seed, extras):
    state = 1 + int.from_bytes(
        hashlib.sha256(("fusion-death-v1\0" + seed).encode()).digest()[:4], "little"
    ) % (MODULUS - 1)
    order = sorted(
        ROSTER,
        key=lambda name: hashlib.sha256(
            (seed + "\0death-priority-v1\0" + name).encode()
        ).digest(),
    )
    return dict(
        Schema=1,
        Mirror=int(extras["mirror"]),
        DeathCharacter=int(extras["death_character"]),
        InitialState=state,
        **{
            "Offset" + str(ROSTER[name]): (rank * MODULUS) // len(order)
            for rank, name in enumerate(order)
        }
    )


def advance(rng, count=1):
    # Composition/exponentiation also validates long runs without a linear loop.
    mul, add, factor, offset = 1, 0, 109, 1021
    while count:
        if count & 1:
            mul, add = (factor * mul) % MODULUS, (factor * add + offset) % MODULUS
        factor, offset = (factor * factor) % MODULUS, (
            factor * offset + offset
        ) % MODULUS
        count >>= 1
    return (mul * rng + add) % MODULUS


def choose(config, rng, unlocks, previous):
    candidates = [
        name
        for name in ROSTER
        if name != previous
        and (name in STARTERS or str(unlocks.get(name.lower(), 0)) == "1")
    ]
    return min(
        candidates,
        key=lambda name: (rng + config["Offset" + str(ROSTER[name])]) % MODULUS,
    )


def profile(config):
    return {STATE: dict(Schema=1, Observed=0, Sequence=0, Rng=config["InitialState"])}


def validate(plan, config, license):
    enabled = any(plan["options"]["extras"][k] for k in ("mirror", "death_character"))
    if plan.get("native_extras_schema") is None:
        if enabled:
            raise ValueError("Native extras require a newer build")
        return
    if plan["native_extras_schema"] != 1:
        raise ValueError("Native extras schema")
    expected = settings(plan["seed"], plan["options"]["extras"])
    if not config.has_section(GROUP) or dict(config[GROUP]) != {
        k.lower(): str(v) for k, v in expected.items()
    }:
        raise ValueError("Changed native extras settings")
    if not expected["DeathCharacter"]:
        return
    if license is None or license.getint(STATE, "Schema", fallback=0) != 1:
        raise ValueError("Missing death cycle profile")
    observed = license.getint(STATE, "Observed")
    sequence = license.getint(STATE, "Sequence")
    rng = license.getint(STATE, "Rng")
    deaths = config.getint("Stats", "Deaths", fallback=0)
    if not 0 <= sequence <= observed <= deaths or rng != advance(
        expected["InitialState"], sequence
    ):
        raise ValueError("Invalid death cycle progress")
    if sequence:
        name = license.get(STATE, "LastName")
        cid = license.getint(STATE, "LastId")
        if ROSTER.get(name) != cid or (
            name not in STARTERS
            and license.getint("Unlockables", name, fallback=0) != 1
        ):
            raise ValueError("Invalid death cycle character")


def operator(code):
    return struct.pack("<hhH", 0, code, 6)


def group(tokens):
    return struct.pack("<hhH", -1, -1, 6) + tokens + struct.pack("<hhH", -1, -2, 6)


def modulo(tokens):
    return group(tokens) + operator(10) + integer(MODULUS)


def transform(frame, sections, objects, instances):
    if frame == 2:
        e = Events(sections, low=0xA000, high=0xA100)
        result = [list(s) for s in sections]
        result[0].insert(0, e.row([e.start()], [set_ini("Options", "Mirror", 0, oi=4)]))
        return result, [dict(frame=frame, menu_mirror_reset=True)]
    if frame not in FRAMES:
        return sections, []
    save, _, _ = frame_metadata(frame, sections, objects, instances)
    e = Events(sections, low=0xA000, high=0xB000)
    license = e.profile(sections)
    rows = [
        e.row([e.start()], [e.load(save, "SaveFile1.ini")]),
        e.row(
            [e.start(), e.eq(save, GROUP, "Schema", 1)],
            [
                ini_expression(
                    "Options", "Mirror", ini_value(GROUP, "Mirror", oi=save), 4
                )
            ],
        ),
    ]
    result = [list(s) for s in sections]
    result[0][2:2] = rows

    def state(key, default=0):
        return ini_value(STATE, key, default, oi=license)

    def changed():
        return [
            e.eq(save, GROUP, "Schema", 1),
            e.eq(save, GROUP, "DeathCharacter", 1),
            e.eq(license, STATE, "Schema", 1),
            e.cmp(ini_value("Stats", "Deaths", oi=save), state("Observed"), 5),
        ]

    late = [
        e.row(
            changed(),
            [
                profile_batch.begin(license),
                ini_expression(
                    STATE,
                    "Rng",
                    modulo(
                        state("Rng")
                        + operator(6)
                        + integer(109)
                        + operator(2)
                        + integer(1021)
                    ),
                    license,
                ),
                set_ini(STATE, "BestScore", MODULUS, oi=license),
                ini_expression(
                    STATE,
                    "Previous",
                    ini_value("License", "Character", oi=license),
                    license,
                ),
            ],
        )
    ]
    for name, cid in ROSTER.items():
        score = modulo(
            state("Rng") + operator(2) + ini_value(GROUP, "Offset" + str(cid), oi=save)
        )
        guards = changed() + [
            e.eq(license, STATE, "Previous", cid, comparison=1),
            e.cmp(score, state("BestScore", MODULUS), 3),
        ]
        if name not in STARTERS:
            guards.append(e.eq(license, "Unlockables", name, 1))
        late.append(
            e.row(
                guards,
                [
                    ini_expression(STATE, "BestScore", score, license),
                    set_ini(STATE, "LastId", cid, oi=license),
                    e.text(license, STATE, "LastName", string(name)),
                ],
            )
        )
    late.append(
        e.row(
            changed() + [e.cmp(state("BestScore"), integer(MODULUS), 3)],
            [
                ini_expression("License", "Character", state("LastId"), license),
                e.text(
                    license,
                    "License",
                    "CharacterName",
                    ini_string(STATE, "LastName", "", license),
                ),
                ini_expression(
                    STATE, "Sequence", e.add(state("Sequence"), integer(1)), license
                ),
                ini_expression(
                    STATE, "Observed", ini_value("Stats", "Deaths", oi=save), license
                ),
                *profile_batch.finish(license),
            ],
        )
    )
    result.append(late)
    return result, [
        dict(
            frame=frame,
            save=save,
            license=license,
            death_rows=len(late),
            mirror_original_option=True,
        )
    ]
