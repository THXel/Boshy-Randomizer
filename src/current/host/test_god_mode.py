"""Full original-event census and invariants for the native God Mode transform."""

import unittest
import recover_boshy_routes as source
from transition.events import commands, expression, integer
from transition.router import params
from gameplay.god_mode import transform, death_call, manual_death, GROUP, settings


class GodModeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = []
        for p, f in source.payloads.items():
            old = source.original_sections(p)
            new, audit = transform(
                f, old, source.objects, source.frames[f - 1]["instances"]
            )
            cls.cases.append((f, old, new, audit))

    def test_every_death_call_classified_and_manual_q_unchanged(self):
        entries = [a for _, _, _, audit in self.cases for a in audit]
        self.assertEqual(len(entries), 383)
        manual = [a for a in entries if a["mode"] == "manual_q_unchanged"]
        self.assertEqual(len(manual), 48)
        self.assertEqual(sum(a["mode"] == "outside_native_run" for a in entries), 4)
        self.assertEqual(sum(a["mode"] == "hazard_guard" for a in entries), 331)
        self.assertEqual(len([a for a in entries if a["loop"].lower() == "die2"]), 3)
        for f, old, new, audit in self.cases:
            for a in audit:
                before = old[a["section"]][a["row"]]
                after = new[a["section"]][a["row"]]
                if a["mode"] != "hazard_guard":
                    self.assertEqual(before, after)
                else:
                    self.assertIn(GROUP.encode(), after)
                    self.assertFalse(manual_death(commands(before)))

    def test_case_insensitive_death_census_is_independent_of_transform(self):
        found = []
        for frame, old, new, audit in self.cases:
            expected = {(a["section"], a["row"]) for a in audit}
            for si, rows in enumerate(old):
                for ri, row in enumerate(rows):
                    for c in commands(row):
                        if not c[0] and c[1:3] == (-1, 14):
                            p = params(c[-1])[0][1]
                            if p[6:10] == b"\xff\xff\x03\x00":
                                name = p[12:].split(b"\0")[0].lower()
                                if name in (b"die", b"die2"):
                                    self.assertIn((si, ri), expected, (frame, si, ri))
                                    found.append(name)
        self.assertEqual(len(found), 383)
        self.assertEqual(found.count(b"die2"), 3)

    def test_only_repeat_parameter_changes_no_audio_or_enemy_edits(self):
        for f, old, new, audit in self.cases:
            changed = {
                (a["section"], a["row"]) for a in audit if a["mode"] == "hazard_guard"
            }
            self.assertEqual(len(old), len(new))
            for si, rows in enumerate(old):
                self.assertEqual(len(rows), len(new[si]))
                for ri, row in enumerate(rows):
                    after = new[si][ri]
                    if (si, ri) not in changed:
                        self.assertEqual(row, after)
                    else:
                        before_cs = commands(row)
                        after_cs = commands(after)
                        self.assertEqual(len(before_cs), len(after_cs))
                        for a, b in zip(before_cs, after_cs):
                            if death_call(a):
                                self.assertEqual(a[-1][2:14], b[-1][2:14])
                                self.assertEqual(params(a[-1])[0], params(b[-1])[0])
                                # The explicit fallback is 1: omitted settings mean normal death.
                                self.assertIn(integer(1), params(b[-1])[1][1])
                            else:
                                self.assertEqual(a, b, (f, si, ri))

    def test_all_direct_player_destruction_is_in_original_death_handler(self):
        count = 0
        for f, old, _, _ in self.cases:
            for rows in old:
                for row in rows:
                    cs = commands(row)
                    for c in cs:
                        if (
                            not c[0]
                            and c[1:3] == (2, 24)
                            and source.objects.get(c[3], {}).get("name") == "Player"
                        ):
                            self.assertTrue(
                                any(
                                    x[0] and x[1:3] == (-1, -16) and b"Die\0" in x[-1]
                                    for x in cs
                                ),
                                f,
                            )
                            count += 1
        self.assertEqual(count, 46)

    def test_strict_setting_and_original_default(self):
        self.assertEqual(settings(False), dict(Schema=1, HazardDeathLoops=1))
        self.assertEqual(settings(True), dict(Schema=1, HazardDeathLoops=0))
        with self.assertRaises(ValueError):
            settings(1)


if __name__ == "__main__":
    unittest.main()
