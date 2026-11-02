"""Character cycling: seed/pool rules, complete native coverage, and persisted state."""

import configparser
import unittest
from gameplay import cycle_plan as cycle
from gameplay.characters import ROSTER
from transition.router import STAGES


class CycleTests(unittest.TestCase):
    def test_pool_priority_repeat_and_initial_choice(self):
        self.assertEqual(len(cycle.STARTERS), 17)
        for index in range(44):
            choice = cycle.choose("DEADBEEF", index, {})
            self.assertIn(choice["name"], cycle.STARTERS)
            self.assertEqual(choice, cycle.choose("DEADBEEF", index, {}))
            self.assertNotEqual(
                choice, cycle.choose("DEADBEEF", index, {}, choice["name"])
            )
            unlocked = {name.lower(): 1 for name in ROSTER}
            self.assertEqual(
                cycle.choose("DEADBEEF", index, unlocked)["name"],
                cycle.order("DEADBEEF", index)[0],
            )
        self.assertIsNone(
            cycle.initial(dict(characters=False, start_character="Auto"), "DEADBEEF")
        )
        self.assertEqual(
            cycle.initial(dict(characters=True, start_character="Auto"), "DEADBEEF"),
            cycle.choose("DEADBEEF", 0, {}),
        )
        self.assertEqual(
            cycle.initial(dict(characters=True, start_character="Kirby"), "DEADBEEF")[
                "name"
            ],
            "Kirby",
        )

    def test_native_coverage_and_existing_events_preserved(self):
        import recover_boshy_rewards as source
        from gameplay.character_cycle import transform
        from transition.events import commands
        from transition.router import params
        import struct

        audit = []
        changed_frames = set()
        for payload, frame in source.routes.payloads.items():
            before = source.sections(payload)
            after, records = transform(
                frame,
                before,
                source.routes.objects,
                source.routes.frames[frame - 1]["instances"],
            )
            audit.extend(records)
            if not records:
                self.assertEqual(before, after)
                continue
            changed_frames.add(frame)
            self.assertEqual(before[1:], after[1:])
            self.assertEqual(before[0][:2], after[0][:2])
            added = len(after[0]) - len(before[0])
            self.assertEqual(before[0][2:], after[0][2 + added :])
            rows = after[0][2 : 2 + added]
            self.assertTrue(
                any(
                    c[1:3] == (33, 123) and b"SaveFile1.ini\0" in c[-1]
                    for c in commands(rows[0])
                )
            )
            # Empty histories and unselected BestId=0 must NEVER pass restore/commit.
            positive_guards = [
                c
                for row in rows
                for c in commands(row)
                if c[0] and (b"HistoryId" in c[-1] or b"BestId\0" in c[-1])
            ]
            comparisons = [
                struct.unpack_from("<H", params(c[-1], True)[1][1], 4)[0]
                for c in positive_guards
            ]
            self.assertNotIn(4, comparisons)  # >= zero would accept missing entries
            self.assertIn(5, comparisons)  # strictly greater than zero
            for row in rows:
                conditions = [c for c in commands(row) if c[0]]
                self.assertTrue(any(c[1:3] == (-3, -1) for c in conditions))
                self.assertTrue(any(b"Enabled\0" in c[-1] for c in conditions))
        self.assertEqual(
            {a["stage"] for a in audit}, {s["id"] for s in STAGES.values()}
        )
        self.assertEqual(len(changed_frames), 37)
        self.assertTrue(all(a["candidates"] == len(ROSTER) for a in audit))

    def test_rank_binding_and_history_validation(self):
        plan = dict(
            seed="DEADBEEF",
            route=["save1.ini", "boss1.ini"],
            options={"characters": True},
            cycle_schema=1,
        )
        c = configparser.ConfigParser(interpolation=None)
        c.read_dict(cycle.settings(plan["seed"], plan["route"], True))
        profile = configparser.ConfigParser(interpolation=None)
        profile.read_string(
            cycle.profile(dict(name="Kirby", id=ROSTER["Kirby"]), True, "save1.ini")
        )
        cycle.validate(plan, c, profile)
        key = next(iter(c[cycle.RANKS]))
        c[cycle.RANKS][key] = "999"
        with self.assertRaisesRegex(ValueError, "priorities"):
            cycle.validate(plan, c, profile)
        c.read_dict(cycle.settings(plan["seed"], plan["route"], True))
        sid = STAGES["save1.ini"]["id"]
        profile[cycle.GROUP][f"HistoryName{sid}"] = "Luigi"
        with self.assertRaisesRegex(ValueError, "history"):
            cycle.validate(plan, c, profile)
        with self.assertRaisesRegex(ValueError, "newer"):
            cycle.validate(
                {k: v for k, v in plan.items() if k != "cycle_schema"}, c, profile
            )
        cycle.validate(dict(options={"characters": False}), c, None)
        with self.assertRaisesRegex(ValueError, "schema"):
            cycle.validate(dict(cycle_schema=2, options={"characters": False}), c, None)

    def test_resume_keeps_native_dresser_choice_and_cycle_history(self):
        import tempfile
        from pathlib import Path
        from menu_host.store import Store, save
        from menu_host.draft import Draft
        from native_rewards_live import write_save

        with tempfile.TemporaryDirectory() as temp:
            d = Draft()
            d.update(characters=True, start_character="Kirby")
            store = Store(Path(temp) / "profile", Path(temp) / "runs")
            with store.lock():
                store.create(1, d)
                folder, plan, _ = store.resume(1)
                saved = save(folder / "onlineLicense.ini")
                history = dict(saved[cycle.GROUP])
                # Emulate the existing dresser's profile edit with the game closed.
                saved["License"]["Character"] = str(ROSTER["Luigi"])
                saved["License"]["CharacterName"] = "Luigi"
                saved.add_section("Unlockables")
                saved["Unlockables"]["Luigi"] = "1"
                write_save(folder / "onlineLicense.ini", saved)
                store.resume(1)
                self.assertEqual(
                    dict(save(folder / "onlineLicense.ini")[cycle.GROUP]), history
                )
                self.assertEqual(
                    save(folder / "onlineLicense.ini").get("License", "CharacterName"),
                    "Luigi",
                )

    def test_menu_toggle_seed_roundtrip_and_five_languages(self):
        from menu_host.draft import Draft
        from menu_host.labels import ROWS, LANGUAGES

        d = Draft()
        old = d.seed
        d.update(characters=True)
        self.assertNotEqual(old, d.seed)
        e = Draft()
        e.import_seed(d.shared())
        self.assertTrue(e.options["characters"])
        self.assertEqual(d.shared(), e.shared())
        for key in ("characters", "characters_hint"):
            self.assertEqual(len(ROWS[key]), len(LANGUAGES))
            self.assertEqual(len(set(ROWS[key])), len(LANGUAGES))


if __name__ == "__main__":
    unittest.main()
