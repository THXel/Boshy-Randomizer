"""Original progression, native character history and Normal menu contracts."""

import unittest, tempfile
from pathlib import Path
from menu_host.draft import Draft
from menu_host.store import Store, save
from native_menu.model import Model
from gameplay import normal_plan as normal
from gameplay.cycle_plan import STARTERS
from transition.events import commands


class NormalTests(unittest.TestCase):
    def test_mode_roundtrip_preserves_custom_route_for_return(self):
        d = Draft()
        d.update(
            level_pool=["save1.ini"],
            level_count=1,
            boss_pool=["hellokitty"],
            route_boss_count=1,
            start_character="Kirby",
        )
        original = dict(d.options)
        old = d.seed
        d.set_mode("normal")
        self.assertNotEqual(old, d.seed)
        self.assertFalse(d.options["levels"])
        self.assertFalse(d.options["items"])
        other = Draft()
        other.import_seed(d.shared())
        self.assertEqual(d.shared(), other.shared())
        d.set_mode("randomizer")
        self.assertEqual(d.options, original)

    def test_menu_locks_inapplicable_route_rules(self):
        with tempfile.TemporaryDirectory() as t:
            m = Model(Store(Path(t) / "p", Path(t) / "r"))
            m.draft.set_mode("normal")
            m.go("route")
            for key in ("level_count", "route_boss_count"):
                self.assertFalse(next(r for r in m.rows() if r.key == key).enabled)
            for page in ("levels", "bosses"):
                m.go(page)
                self.assertTrue(all(not r.enabled for r in m.rows()))
            m.go("loadout")
            self.assertFalse(next(r for r in m.rows() if r.key == "items").enabled)
            self.assertTrue(
                next(r for r in m.rows() if r.key == "start_character").enabled
            )

    def test_native_scene_census_and_preserved_original_events(self):
        import recover_boshy_cycle as source
        from gameplay.normal_mode import transform

        found = []
        for payload, frame in source.routes.payloads.items():
            before = source.sections(payload)
            after, audit = transform(
                frame,
                before,
                source.routes.objects,
                source.routes.frames[frame - 1]["instances"],
            )
            found += audit
            for old, new in zip(before, after):
                # Every original event remains byte-identical in its previous order.
                at = iter(new)
                for row in old:
                    self.assertTrue(any(candidate == row for candidate in at))
            if frame in normal.FRAMES:
                additions = after[0][2 : 2 + len(after[0]) - len(before[0])]
                self.assertTrue(any(b"ResumePending\0" in row for row in additions))
                self.assertTrue(any(b"LastDeaths\0" in row for row in additions))
                for row in additions:
                    self.assertTrue(
                        any(c[1:3] == (-3, -1) for c in commands(row) if c[0])
                    )
        self.assertEqual({r["frame"] for r in found}, set(normal.FRAMES) | {2})
        self.assertEqual(sum(bool(r.get("finale")) for r in found), 1)

    def test_seeded_native_rotation_only_uses_available_characters(self):
        previous = "Kirby"
        for step in range(1, 35):
            c = normal.choose("DEADBEEF", 4, step, {}, previous)
            self.assertIn(c["name"], STARTERS)
            self.assertNotEqual(c["name"], previous)
            self.assertEqual(c, normal.choose("DEADBEEF", 4, step, {}, previous))
            previous = c["name"]

    def test_real_exports_disable_routes_and_bind_original_rewards(self):
        with tempfile.TemporaryDirectory() as t:
            for cycle in (False, True):
                d = Draft()
                d.set_mode("normal")
                d.update(characters=cycle, start_character="Kirby")
                s = Store(Path(t) / str(cycle), Path(t) / "runs")
                with s.lock():
                    s.create(1, d)
                    folder, p, c = s.resume(1)
                    self.assertEqual(p["route"], [])
                    self.assertEqual(p["source"], "save1.ini")
                    self.assertEqual(c.getint("FusionRouteV4", "Schema"), 0)
                    self.assertFalse(
                        any(k.startswith("next") for k in c["FusionRouteV4"])
                    )
                    self.assertEqual(c.getint("FusionRewardsV1", "Enabled"), 0)
                    profile = save(folder / "onlineLicense.ini")
                    self.assertEqual(profile.get("License", "CharacterName"), "Kirby")
                    normal.validate(p, c, profile)
                    from native_rewards_live import write_save

                    c["Positions"]["frame"] = "5"
                    write_save(folder / "SaveFile1.ini", c)
                    self.assertEqual(s.summary(1)["spot"], "save2.ini")
                    c[normal.GROUP]["Enabled"] = "0"
                    with self.assertRaises(ValueError):
                        normal.validate(p, c, profile)


if __name__ == "__main__":
    unittest.main()
