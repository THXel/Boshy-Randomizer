"""Death-cycle persistence and native mirror settings regression tests."""

import tempfile, unittest
from pathlib import Path
from functools import partial
from gameplay import native_extras as extras
from gameplay.characters import ROSTER
from gameplay.cycle_plan import STARTERS
from menu_host.draft import Draft
from menu_host.store import Store
from export_native_run import export
from native_menu.builds import DYNAMIC_SHA, EXTRAS_SHA
from transition.events import commands
import recover_boshy_targets as source


class NativeExtrasTests(unittest.TestCase):
    def test_sequence_is_unbounded_deterministic_unlocked_and_no_repeat(self):
        d = Draft()
        d.update(death_character=True, mirror=True)
        setup = extras.settings("12345678", d.options["extras"])
        rng = setup["InitialState"]
        previous = "Kirby"
        seen = set()
        for count in range(1, 10001):
            rng = extras.advance(rng)
            self.assertEqual(rng, extras.advance(setup["InitialState"], count))
            name = extras.choose(setup, rng, {}, previous)
            self.assertIn(name, STARTERS)
            self.assertNotEqual(name, previous)
            seen.add(name)
            previous = name
        self.assertEqual(seen, STARTERS)
        unlocks = {name.lower(): 1 for name in ROSTER}
        self.assertTrue(
            any(
                extras.choose(
                    setup, extras.advance(setup["InitialState"], i), unlocks, "Kirby"
                )
                not in STARTERS
                for i in range(1, 300)
            )
        )

    def test_source_keeps_original_events_and_has_no_new_death_calls(self):
        found = set()
        for payload, frame in source.routes.payloads.items():
            before = source.sections(payload)
            after, audit = extras.transform(
                frame,
                before,
                source.routes.objects,
                source.routes.frames[frame - 1]["instances"],
            )
            if frame == 2:
                self.assertEqual(before[0], after[0][1:])
                self.assertEqual(before[1:], after[1:])
                continue
            if not audit:
                self.assertEqual(before, after)
                continue
            found.add(frame)
            self.assertEqual(before[0], after[0][:2] + after[0][4:])
            self.assertEqual(before[1:], after[1:-1])
            acts = [c for row in after[-1] for c in commands(row) if not c[0]]
            self.assertTrue(all(c[1] == 33 for c in acts))
        self.assertEqual(found, set(extras.FRAMES))

    def test_export_and_saved_state_binding_in_both_builds(self):
        for dynamic in (False, True):
            with self.subTest(dynamic=dynamic), tempfile.TemporaryDirectory() as t:
                root = Path(t)
                store = Store(
                    root / "p", root / "r", exporter=partial(export, dynamic=dynamic)
                )
                with store.lock():
                    d = Draft()
                    d.update(mirror=True, death_character=True)
                    d.seed = "12345678"
                    store.create(1, d)
                    folder, plan, cfg = store.resume(1)
                    self.assertEqual(
                        plan["game_sha256"], DYNAMIC_SHA if dynamic else EXTRAS_SHA
                    )
                    from menu_host.store import save

                    profile = save(folder / "onlineLicense.ini")
                    extras.validate(plan, cfg, profile)
                    profile[extras.STATE]["Sequence"] = "1"
                    with self.assertRaisesRegex(ValueError, "progress"):
                        extras.validate(plan, cfg, profile)
                    profile[extras.STATE]["Sequence"] = "0"
                    cfg[extras.GROUP]["Mirror"] = "0"
                    with self.assertRaisesRegex(ValueError, "settings"):
                        extras.validate(plan, cfg, profile)


if __name__ == "__main__":
    unittest.main()
