"""Native rush mode contracts, pool retention and exported route/save edges."""

import copy
import tempfile
import unittest
from pathlib import Path
from menu_host.draft import Draft, LEVELS, BOSSES
from menu_host.store import Store
from native_menu.model import Model
from export_route_probe import plan, save_text
from run_settings import route


class RushTests(unittest.TestCase):
    def test_mode_cycle_preserves_custom_pools_counts_and_seed_contract(self):
        d = Draft()
        d.update(
            level_pool=["save1.ini", "save7.ini"],
            level_count=2,
            boss_pool=["hellokitty", "gravitron"],
            route_boss_count=1,
        )
        original = copy.deepcopy(d.options)
        for mode in ("boss_rush", "level_rush", "randomizer"):
            seed = d.seed
            d.set_mode(mode)
            self.assertNotEqual(d.seed, seed)
            p = plan(d.shared(), "fixture", "fixture")
            self.assertEqual(p["options"]["mode"], mode)
            self.assertEqual(p["route"][-1], "boss_solgryn.ini")
            if mode == "boss_rush":
                self.assertEqual(d.options["level_pool"], [])
                self.assertEqual(
                    p["route"][:-1],
                    [
                        BOSSES[b][2]
                        for b in d.options["boss_pool"]
                        if BOSSES[b][2] in p["route"]
                    ],
                )
            if mode == "level_rush":
                self.assertEqual(d.options["boss_pool"], [])
                self.assertTrue(set(p["route"][:-1]) <= set(LEVELS))
            self.assertIn("NextFrame", save_text(p))
        self.assertEqual(d.options, original)

    def test_imported_rush_roundtrips_and_switches_to_a_valid_other_mode(self):
        for mode in ("boss_rush", "level_rush"):
            d = Draft()
            d.set_mode(mode)
            imported = Draft()
            imported.import_seed(d.shared())
            self.assertEqual(imported.options, d.options)
            self.assertEqual(imported.seed, d.seed)
            for next_mode in ("randomizer", "level_rush", "boss_rush"):
                imported.set_mode(next_mode)
                self.assertGreater(len(route(imported.seed, imported.options)), 1)

    def test_inactive_pool_and_count_are_locked_in_native_menu(self):
        with tempfile.TemporaryDirectory() as folder:
            m = Model(Store(folder, runs=Path(folder) / "runs"))
            for mode, page, count in [
                ("boss_rush", "levels", "level_count"),
                ("level_rush", "bosses", "route_boss_count"),
            ]:
                m.draft.set_mode(mode)
                m.go(page)
                self.assertTrue(all(not row.enabled for row in m.rows()))
                seed = m.draft.seed
                m.key(13)
                self.assertEqual(m.draft.seed, seed)
                m.go("route")
                self.assertFalse(next(r for r in m.rows() if r.key == count).enabled)

    def test_entering_rush_from_an_empty_pool_uses_nonempty_defaults(self):
        d = Draft()
        d.update(boss_pool=[], route_boss_count=0)
        d.set_mode("boss_rush")
        self.assertTrue(d.options["boss_pool"])
        self.assertGreater(d.options["route_boss_count"], 0)
