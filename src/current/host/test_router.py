"""Route coverage, original action preservation and event ABI checks."""

import unittest, struct
from collections import Counter
from recover_boshy_routes import (
    payloads,
    sections,
    changes,
    objects,
    frames,
    app,
    table,
)
from recover_boshy_transition import original_sections
from transition.router import STAGES, params, value_parameter, native_destination, GROUP
from transition.events import commands


class RouterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        changes.clear()
        cls.result = {}
        cls.original = {}
        for payload, frame in payloads.items():
            cls.original[frame] = original_sections(payload)
            cls.result[frame] = sections(payload)
        cls.audit = {r["frame"]: r for r in changes}

    def test_every_selectable_stage_and_finale_has_a_gate(self):
        covered = {e["spot"] for f in self.audit.values() for e in f["edges"]}
        self.assertEqual(covered, set(STAGES))
        self.assertEqual(len(covered), 44)

    def test_split_worlds_keep_the_confirmed_exits(self):
        edges = lambda spot: {
            e.get("native_destination")
            for f in self.audit.values()
            for e in f["edges"]
            if e["spot"] == spot and e["kind"] == "frame_exit"
        }
        self.assertEqual(edges("save2.ini"), {6})
        self.assertEqual(edges("save9.ini"), {23, 53})
        self.assertEqual(edges("save10.ini"), {24})
        self.assertEqual(edges("boss7.ini"), {12})

    def test_warcraft_both_original_exits_and_cheetah_spawn(self):
        edges = {e['native_destination'] for e in self.audit[53]['edges']
                 if e['spot'] == 'save21.ini' and e['kind'] == 'frame_exit'}
        self.assertEqual(edges, {54, 29})
        original_player = next(i for i in frames[53]['instances']
                               if objects[i['objectInfo']]['name'] == 'Player')
        self.assertEqual((STAGES['boss21.ini']['x'], STAGES['boss21.ini']['y']),
                         (original_player['x'], original_player['y']))
        self.assertEqual(objects[216]['values'][2], 29)

    def test_tower_arrival_matches_original_desert_door(self):
        # The entry event overrides the editor's Player placement with globals
        # x=319 and y=3769. The platform must be approached from above.
        from transition.router import value_parameter
        actions=[c for c in commands(self.original[35][84][2])
                 if not c[0] and c[1:3]==(-1,3)]
        entry={struct.unpack_from('<I',params(c[-1])[0][1],4)[0]:
               struct.unpack_from('<i',value_parameter(params(c[-1])[1]),6)[0]
               for c in actions}
        self.assertEqual((STAGES['save20.ini']['x'],STAGES['save20.ini']['y']),
                         (entry[1],entry[2]))
        self.assertEqual((entry[1],entry[2]),(319,3769))

    def test_original_actions_remain_in_order_in_fallbacks(self):
        for frame, original in self.original.items():
            generated = self.result[frame]
            for si, section in enumerate(original):
                originals = [
                    tuple(c[-1] for c in commands(r) if not c[0]) for r in section
                ]
                candidate = [
                    tuple(c[-1] for c in commands(r) if not c[0]) for r in generated[si]
                ]
                for acts in originals:
                    # Kracko's sole original victory row gains its receipt at the end.
                    self.assertTrue(
                        any(a[: len(acts)] == acts for a in candidate), (frame, si)
                    )

    def test_new_condition_ids_do_not_alias_original_or_each_other(self):
        for frame, sections_ in self.result.items():
            ids = [
                struct.unpack_from("<H", c[-1], 14)[0]
                for se in sections_
                for r in se
                for c in commands(r)
                if c[0]
            ]
            new = [i for i in ids if i > 0xA000]
            self.assertEqual(len(new), len(set(new)), frame)

    def test_actual_global_expression_and_portal_destination(self):
        for frame, section, row, expected in [
            (54, 101, 0, 29),
            (10, 25, 2, 11),
            (59, 85, 10, 31),
        ]:
            cmds = commands(self.original[frame][section][row])
            ci = next(
                i
                for i, c in enumerate(cmds)
                if not c[0] and c[1] == -3 and c[2] in [0, 2]
            )
            dest, tokens = native_destination(cmds[ci], cmds[:ci], frame, table)
            if frame == 54:
                self.assertIsNone(dest)
                self.assertEqual(tokens, bytes.fromhex("020010000c00800b00000200"))
                self.assertEqual(objects[2944]["values"][2], expected)
            else:
                self.assertEqual(dest, expected)
                self.assertIsNone(tokens)

    def test_restart_debug_and_previous_frame_are_untouched(self):
        for frame, original in self.original.items():
            generated = self.result[frame]
            for si in range(min(2, len(original))):
                for row in original[si]:
                    self.assertIn(row, generated[si])

    def test_every_dispatch_uses_save_local_identity_and_checkpoint(self):
        seen = 0
        for sections_ in self.result.values():
            for se in sections_:
                for row in se:
                    cs = commands(row)
                    if not any(not c[0] and b"NextId" in c[-1] for c in cs):
                        continue
                    self.assertTrue(
                        any(c[0] and b"CurrentStage\0" in c[-1] for c in cs)
                    )
                    acts = [c[-1] for c in cs if not c[0]]
                    self.assertIn(b"save\0", acts[-2])
                    self.assertEqual(cs[-1][1:3], (-3, 2))
                    seen += 1
        self.assertGreater(seen, 43)

    def test_ninja_gaiden_or_exit_is_guarded_in_every_branch(self):
        for row in self.result[31][68]:
            cs = commands(row)
            if not any(c[0] and c[1:3] in [(-1, -24), (-1, -25)] for c in cs):
                continue
            if not any(b"Handled\0" in c[-1] for c in cs if c[0]):
                continue
            branch = []
            for c in [c for c in cs if c[0]]:
                if c[1:3] in [(-1, -24), (-1, -25)]:
                    self.assertTrue(any(b"Handled\0" in b for b in branch))
                    branch = []
                else:
                    branch.append(c[-1])
            self.assertTrue(any(b"Handled\0" in b for b in branch))

    def test_integer_comparison_boundaries_use_sdk_constants(self):
        # Official Clickteam Cncf.h: >= is 4, > is 5; include rectangle boundaries.
        from transition.router import inside

        region = inside(358, (3200, 0, 3840, 480), 0x9F30)
        self.assertEqual(
            [struct.unpack_from("<H", r, 20)[0] for r in region], [4, 3, 4, 3]
        )


if __name__ == "__main__":
    unittest.main()
