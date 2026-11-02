"""Regression coverage against every original frame, not synthetic lookalikes."""

import copy
import unittest
import recover_boshy_routes as source
from transition.events import commands, expression, integer
from transition.router import params
from visuals.player_blood import transform, extend_object, player_spawn


class PlayerBloodTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = []
        for payload, frame in source.payloads.items():
            old = source.original_sections(payload)
            new, audit = transform(
                frame, old, source.objects, source.frames[frame - 1]["instances"]
            )
            cls.cases.append((frame, old, new, audit))

    def test_all_47_player_spawn_paths_are_covered(self):
        spawns = [
            a
            for _, _, _, audit in self.cases
            for a in audit
            if a["change"] == "player_creation_only"
        ]
        self.assertEqual(len(spawns), 47)
        self.assertEqual({a["oi"] for a in spawns}, {105, 1032})
        for _, old, new, audit in self.cases:
            for a in audit:
                if a["change"] == "player_creation_only":
                    before = commands(old[a["section"]][a["row"]])
                    after = commands(new[a["section"]][a["row"]])
                    self.assertTrue(player_spawn(old[a["section"]][a["row"]]))
                    self.assertEqual(after[:-2], before)
                    self.assertEqual(
                        [c[1:4] for c in after[-2:]],
                        [(2, 17, a["oi"]), (2, 31, a["oi"])],
                    )

    def test_every_audio_command_and_its_order_are_preserved(self):
        for frame, old, new, _ in self.cases:
            for si, rows in enumerate(old):
                for ri, row in enumerate(rows):
                    audio = lambda r: [c for c in commands(r) if c[1] == -2]
                    self.assertEqual(audio(row), audio(new[si][ri]), (frame, si, ri))
            for rows in new[len(old) :]:
                self.assertFalse(any(c[1] == -2 for row in rows for c in commands(row)))

    def test_enemy_and_other_unreviewed_events_are_byte_identical(self):
        for frame, old, new, audit in self.cases:
            changed = {(a["section"], a["row"]) for a in audit}
            for si, rows in enumerate(old):
                for ri, row in enumerate(rows):
                    if (si, ri) not in changed:
                        self.assertEqual(row, new[si][ri], (frame, si, ri))

    def test_only_player_blood_objects_get_separate_animation(self):
        for oi, obj in source.objects.items():
            if oi not in (105, 1032):
                self.assertIs(extend_object(obj), obj)
            else:
                before = copy.deepcopy(obj)
                new = extend_object(obj)
                self.assertEqual(obj, before)
                self.assertEqual(new["animations"][0], obj["animations"][0])
                self.assertEqual(new["animations"][1]["slot"], 15)
                self.assertEqual(new["values"], obj["values"] + [0])

    def test_custom_blood_loop_is_only_called_by_player_death(self):
        calls = []
        for frame, old, _, _ in self.cases:
            for rows in old:
                for row in rows:
                    cs = commands(row)
                    for c in cs:
                        if (
                            not c[0]
                            and c[1:4] == (57, 80, 267)
                            and params(c[-1])[0][1] == expression(integer(3))
                        ):
                            self.assertTrue(
                                any(
                                    x[0]
                                    and x[1:3] == (-1, -16)
                                    and (b"Die\0" in x[-1] or b"Die2\0" in x[-1])
                                    for x in cs
                                ),
                                frame,
                            )
                            self.assertTrue(
                                any(
                                    x[0]
                                    and x[1:3] == (2, -32)
                                    and source.objects[x[3]]["name"] == "Player"
                                    for x in cs
                                ),
                                frame,
                            )
                            calls.append(frame)
        self.assertEqual(len(calls), 46)

    def test_occupied_lifetime_value_is_rejected(self):
        bad = copy.deepcopy(source.objects[105])
        bad["values"].append(4)
        with self.assertRaises(AssertionError):
            extend_object(bad)


if __name__ == "__main__":
    unittest.main()
