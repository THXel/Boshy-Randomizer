"""Target goal parity, route fairness, native hooks and save/menu boundaries."""

import tempfile, unittest
from pathlib import Path
from gameplay import target_plan as target
from transition.router import STAGES, GROUP as ROUTE
from menu_host.draft import Draft
from menu_host.store import Store, save
from native_menu.model import Model


class TargetTests(unittest.TestCase):
    def test_goals_match_previous_mode_and_all_catalogue_entries(self):
        from beta_catalogue import goals
        from gameplay.reward_plan import CATALOGUE

        d = Draft()
        d.set_mode("target")
        self.assertEqual(len(target.ITEMS), 19)
        self.assertEqual(len(target.BOSS_STAGES), 22)
        for seed in ("DEADBEEF", "00000000", "0000001D", "FFFFFFFF"):
            for n, b in ((1, 0), (5, 7), (19, 22)):
                d.update(target_count=n, boss_count=b)
                self.assertEqual(
                    target.goals(seed, d.options),
                    goals(CATALOGUE.parent, seed, d.options),
                )
                self.assertEqual(len(target.goals(seed, d.options)["items"]), n)
                self.assertEqual(len(target.goals(seed, d.options)["bosses"]), b)

    def test_route_is_not_finite_and_does_not_starve_rooms_or_repeat_bosses(self):
        for seed in ("DEADBEEF", "00000000", "0000001D", "FFFFFFFF"):
            current = "save1.ini"
            done = set()
            cursors = dict(CursorRooms=1, CursorBosses=1)
            counts = {k: 0 for k in target.POOL}
            ranks = {k: i for i, k in enumerate(target.order(seed), 1)}
            for visit in range(2000):
                done.add(STAGES[current]["id"])
                nxt = target.choose(seed, current, cursors, done)
                self.assertNotEqual(nxt, current)
                self.assertNotEqual(nxt, target.FINAL)
                counts[nxt] += 1
                kind = STAGES[nxt]["category"]
                cursors["CursorRooms" if kind == "rooms" else "CursorBosses"] = (
                    ranks[nxt] % target.SIZE + 1
                )
                current = nxt
            for k, s in target.POOL.items():
                self.assertGreaterEqual(
                    counts[k], 10 if s["category"] == "rooms" else 1, k
                )
                if s["category"] == "bosses":
                    self.assertEqual(counts[k], 1, k)
            self.assertEqual(
                target.choose(seed, current, cursors, done, True), target.FINAL
            )

    def test_target_seed_controls_and_complete_menu_translation(self):
        from menu_host.labels import LANGUAGES

        d = Draft()
        d.set_mode("target")
        old = d.seed
        d.update(target_count=19, boss_count=22)
        self.assertNotEqual(old, d.seed)
        other = Draft()
        other.import_seed(d.shared())
        self.assertEqual(d.shared(), other.shared())
        self.assertFalse(d.options["items"])
        with tempfile.TemporaryDirectory() as t:
            m = Model(Store(Path(t) / "p", Path(t) / "r"))
            m.draft = d
            for lang in LANGUAGES:
                m.language = lang
                m.go("route")
                self.assertTrue(
                    next(r for r in m.rows() if r.key == "target_count").enabled
                )
                m.go("loadout")
                self.assertFalse(next(r for r in m.rows() if r.key == "items").enabled)
                m.go("targets")
                self.assertEqual(len(m.rows()), 41)
                before = m.draft.shared()
                m.select(m.rows()[0].key)
                self.assertEqual(m.draft.shared(), before)
                for key in (
                    "targets",
                    "target",
                    "target_count",
                    "boss_count",
                    "target_hint",
                ):
                    self.assertNotEqual(m.t(key), key)
            for page in ("levels", "bosses"):
                m.go(page)
                self.assertTrue(all(not r.enabled for r in m.rows()))

    def test_native_exit_coverage_and_finale_guard(self):
        import recover_boshy_modes as source
        from gameplay.target_mode import transform
        from transition.events import commands

        total = 0
        final = 0
        frames = set()
        for payload, frame in source.routes.payloads.items():
            before = source.sections(payload)
            after, audit = transform(
                frame,
                before,
                source.routes.objects,
                source.routes.frames[frame - 1]["instances"],
            )
            if not audit:
                self.assertEqual(after, before)
                continue
            total += audit[0]["exit_hooks"]
            final += audit[0]["finale_hooks"]
            frames.add(frame)
            self.assertTrue(
                all(len(row) < 32768 for section in after for row in section)
            )
            for section in after:
                for row in section:
                    cs = commands(row)
                    if any(not c[0] and b"Fusion Target next\0" in c[-1] for c in cs):
                        conditions = [c[-1] for c in cs if c[0]]
                        import struct

                        branches = [[]]
                        for condition in conditions:
                            if struct.unpack_from("<hh", condition, 2) in (
                                (-1, -24),
                                (-1, -25),
                            ):
                                branches.append([])
                            else:
                                branches[-1].append(condition)
                        self.assertTrue(
                            all(
                                any(b"FusionTargetConfigV1\0" in c for c in branch)
                                for branch in branches
                            )
                        )
                        self.assertTrue(
                            any(b"Handled\0" in c for c in conditions) or frame == 46
                        )
        self.assertEqual(total, 81)
        self.assertEqual(final, 1)
        self.assertEqual(
            frames, {f for s in STAGES.values() for f in s["frames"]} | {9}
        )

    def test_export_receipts_goal_binding_and_finale_unlock(self):
        from native_rewards_live import write_save

        for characters in (False, True):
            with tempfile.TemporaryDirectory() as t:
                d = Draft()
                d.set_mode("target")
                d.update(target_count=19, boss_count=22, characters=characters)
                s = Store(Path(t) / "p", Path(t) / "r")
                with s.lock():
                    s.create(1, d)
                    folder, p, c = s.resume(1)
                    self.assertEqual(p["route"], [])
                    self.assertFalse(p["options"]["items"])
                    self.assertEqual(c.getint("FusionCycleV1", "Enabled"), 0)
                    profile = save(folder / "onlineLicense.ini") if characters else None
                    self.assertFalse(target.ready(p["targets"], c))
                    # Stored inventory + native boss receipts, never achievement aliases.
                    for item in target.ITEMS:
                        c["Collectables"][item] = "1"
                    for sid in target.BOSS_STAGES.values():
                        c[ROUTE]["Done" + str(sid)] = "1"
                    self.assertTrue(target.ready(p["targets"], c))
                    c[target.GROUP]["Ready"] = "1"
                    c[ROUTE]["CurrentStage"] = str(STAGES[target.FINAL]["id"])
                    target.validate(p, c, profile)
                    write_save(folder / "SaveFile1.ini", c)
                    self.assertEqual(s.summary(1)["target_progress"], p["targets"])
                    s.resume(1)
                    c[ROUTE]["Done" + str(target.BOSS_STAGES["oldsonic"])] = "0"
                    with self.assertRaisesRegex(ValueError, "without goals"):
                        target.validate(p, c, profile)
                    # Sonic's own receipt must never substitute for Old Sonic.
                    self.assertNotIn(
                        "oldsonic", target.progress(p["targets"], c)["bosses"]
                    )
                    c[ROUTE]["Done" + str(target.BOSS_STAGES["oldsonic"])] = "1"
                    c[target.CONFIG]["Item0"] = "0"
                    with self.assertRaisesRegex(ValueError, "Changed Target settings"):
                        target.validate(p, c, profile)


if __name__ == "__main__":
    unittest.main()
