"""Native exit fixtures, kept separate from the gameplay route implementation.

Contacts exercise original collision events. Values advance documented native
ending phases; they do not write routing, achievements, or completion receipts.
"""

# scene: (source station, boss key or None, native fixture operations)
MATRIX = {
    "prehistorik-routes": ("save1.ini", None, [("contact", "Active 39")]),
    "hellokitty-routes": ("boss1.ini", "hellokitty", [("contact", "Active 28")]),
    "greens-after-routes": ("save23.ini", None, [("contact", "Active 52")]),
    "ryu-fight-routes": ("boss4.ini", "ryu", [("contact", "Active 36")]),
    "cheetah-world-routes": ("save3.ini", None, [("value", "Active 15", 0, 50)]),
    "biollante-routes": (
        "boss8.ini",
        "biollante",
        [("value", "Classic Mario", 7, -15)],
    ),
    "wario-routes": ("save6.ini", None, [("contact", "Active 39")]),
    "sonic-routes": ("boss9.ini", "sonic", [("value", "Active 4sonic", 1, 0)]),
    "oldsonic-routes": ("boss23.ini", "oldsonic", [("value", "Active 4sonic", 1, 0)]),
    "castlevania-routes": ("save7.ini", None, [("contact-offset", "Active 36", 8, 16)]),
    "skeletonking-routes": (
        "boss11.ini",
        "skeletonking",
        [("value", "Characters - Blob", 0, 1500)],
    ),
    "megaman-routes": ("boss12.ini", "megaman", [("value", "Active 4", 24, 750)]),
    "shangtsung-routes": ("boss13.ini", "shangtsung", [("value", "Player", 19, 600)]),
    "megaman-world-routes": ("save11.ini", None, [("contact", "Active 23")]),
    "missingno-routes": (
        "boss17.ini",
        "missingno",
        [("value", "randomness", 3, 0), ("value", "randomness", 5, 599)],
    ),
    "secret-mario-routes": (
        "save14.ini",
        None,
        [("contact-offset", "Active 5", 16, 32)],
    ),
    "desert-routes": ("save15.ini", None, [("value", "Active 59", 0, 40)]),
    "final-path-routes": ("save18.ini", None, [("contact", "Active 16")]),
    "pokemon-routes": ("save19.ini", None, [("contact", "Active 23")]),
    "tower-routes": ("save20.ini", None, [("value", "Active 61", 0, 40)]),
    "wow-routes": (
        "save21.ini",
        None,
        [("position", 1700, 1500), ("value", "Active 23", 0, 70)],
    ),
    "ganon-routes": ("boss22.ini", "ganon", [("value", "Ganon", 0, 0)]),
    "cheetah-fight-routes": ("boss21.ini", "cheetahman", [("cheetah",)]),
}

MATRIX.update(
    {
        "dedede-fight-routes": ("boss3.ini", "kingdedede", [("dedede",)]),
        "gradius-routes": ("boss10.ini", "gradius", [("gradius",)]),
        "gravitron-routes": ("boss7.ini", "gravitron", [("teleport-region", 145)]),
        "bomberman-routes": ("boss15.ini", "bomberman", [("bomberman",)]),
    }
)


def target_for(source):
    return "save7.ini" if source == "save1.ini" else "save1.ini"


def exercise_matrix(test, scene):
    import time
    from transition.router import GROUP, STAGES

    source, _, operations = MATRIX[scene]
    target = target_for(source)
    test.report["fixture_operations"] = operations
    # A death/retry must not accidentally consume an outgoing route.
    test.death_restart(source, "source")
    test.protect()
    assert test.saved().getint(GROUP, "Done" + str(STAGES[source]["id"])) == 0
    for operation in operations:
        kind = operation[0]
        if kind == "position":
            test.position(operation[1], operation[2])
            time.sleep(0.5)
        elif kind == "dedede":
            test.state.set_value(test.obj("Active 15"), 7, 200)
            test.wait(lambda: bool(test.objects("Active 27")))
            test.state.set_value(test.obj("Active 27"), 0, 299)
            test.wait(lambda: bool(test.objects("Active 30")))
            test.state.set_value(test.obj("Active 30"), 0, 149)
            test.wait(lambda: bool(test.objects("Active 28")))
            body = test.obj("Active 30")
            test.state.position(test.obj("Active 28"), body["x"], body["y"])
            test.wait(
                lambda: test.saved().getint("Achievements", "KingDeDeDe", fallback=0)
                >= 1
            )
            test.report["native_victory_saved"] = True
            test.position(640, 390)
        elif kind == "gradius":
            ship = test.obj("GradiusShip 2")
            test.state.set_value(ship, 0, 45)
            test.wait(lambda: test.state.frame_name() == "Midway - Gradius")
            test.protect()
            ship = test.obj("GradiusShip 2")
            values = test.state.values(ship, 2)
            test.report["gradius_native_duration"] = values
            test.snap("gradius-internal-room")
            assert test.saved().getint(GROUP, "CurrentStage") == STAGES[source]["id"]
            test.state.set_value(ship, 0, int(values[1]))
            test.position(600, 300)
            test.wait(
                lambda: test.state.frame_name() == "Sixth World - Castlevania",
                seconds=15,
            )
            test.protect()
            test.report["returned_from_gradius"] = test.station(source)
            obj = test.obj("Active 36")
            test.position(obj["x"] + 8, obj["y"] + 16)
        elif kind in ("bomberman", "teleport-region"):
            if kind == "teleport-region":
                # Gravitron is a timed survival encounter, not an HP boss.
                # Let the real engine finish all 30 seconds before approaching.
                started = time.monotonic()
                test.snap("gravitron-timer-start")
                for sample in range(6):
                    time.sleep(5.5)
                    test.station(source)
                    test.snap("gravitron-timer-" + str(sample + 1))
                test.report["native_survival_seconds"] = time.monotonic() - started
            obj = test.obj("Active 41")
            if kind == "bomberman":
                # Advance the native ending that moves the exit into reach.
                test.state.set_value(test.obj("Classic Mario"), 0, 1359)
                test.wait(lambda: not test.objects("Classic Mario"))
                obj = test.obj("Active 41")
                # Native collision awards the achievement; never forge the INI.
                test.position(obj["x"] + 16, obj["y"] + 16)
                test.wait(
                    lambda: test.saved().getint("Achievements", "Bomberman", fallback=0)
                    >= 2
                )
                test.report["native_victory_saved"] = True
                obj = test.obj("Active 41")
            test.position(
                obj["x"] + (40 if kind == "bomberman" else operation[1]),
                obj["y"] - (60 if kind == "teleport-region" else 0),
            )
        elif kind == "cheetah":
            gate = test.obj("Active 42")
            test.position(gate["x"], gate["y"])
            time.sleep(0.4)
            test.station(source)
            assert test.objects("BossActions"), "Premature route before victory"
            assert test.saved().getint(GROUP, "Done" + str(STAGES[source]["id"])) == 0
            test.report["premature_exit_blocked"] = True
            test.position(511, 376)
            test.state.set_value(test.obj("BossActions"), 0, 6499)
            test.wait(
                lambda: test.state.values(test.obj("BossActions"), 1)[0] >= 6900,
                seconds=15,
            )
            test.report["native_victory_phase"] = test.state.values(
                test.obj("BossActions"), 1
            )[0]
            gate = test.obj("Active 42")
            test.position(gate["x"], gate["y"])
        else:
            obj = test.obj(operation[1])
            test.report.setdefault("objects_before", []).append(
                dict(obj, values=test.state.values(obj, 26))
            )
            if kind in ("contact", "contact-offset"):
                dx, dy = operation[2:4] if kind == "contact-offset" else (0, 0)
                test.position(obj["x"] + dx, obj["y"] + dy)
            elif kind == "value":
                test.state.set_value(obj, operation[2], operation[3])
            else:
                raise ValueError(operation)
    # Sonic's native explosion outro and Biollante's ending audio can take time.
    test.wait(
        lambda: test.saved().getint(GROUP, "CurrentStage") == STAGES[target]["id"],
        seconds=25,
    )
    test.arrival(target, "native-exit")
    assert test.saved().getint(GROUP, "Done" + str(STAGES[source]["id"])) == 1
    test.death_restart(target, "target")
