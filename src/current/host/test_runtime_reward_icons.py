"""A fixed engine must select validated reward artwork for each run."""

import tempfile
import unittest
from pathlib import Path
from functools import partial
from menu_host.store import Store, digest
from menu_host.draft import Draft
from export_native_run import export
from gameplay import runtime_reward_icons as runtime
from gameplay.reward_plan import LOCATIONS, GROUP, validate
from native_menu.builds import DYNAMIC_SHA, DYNAMIC_BASE
from native_menu.session_store import WorkingSession
from menu_host.runtime import verify_engine
from transition.events import commands, expression, integer
from transition.router import params
import recover_boshy_routes as source


class RuntimeRewardIconsTests(unittest.TestCase):
    def test_every_chest_changes_only_its_reveal_frame(self):
        seen = set()
        targets = {loc["object"] for loc in LOCATIONS}
        for payload, frame in source.payloads.items():
            before = source.original_sections(payload)
            after, audit = runtime.transform(
                frame, before, source.objects, source.frames[frame - 1]["instances"]
            )
            if not audit:
                self.assertEqual(before, after)
                continue
            inserted = after[0][2 : 2 + audit[0]["events"]]
            self.assertEqual(before[0], after[0][:2] + after[0][2 + len(inserted) :])
            self.assertEqual(before[1:], after[1:])
            seen.update(audit[0]["locations"])
            for row in inserted:
                for condition, kind, code, oi, raw in commands(row):
                    if not condition and kind == 2:
                        self.assertEqual(code, 89)
                        self.assertIn(oi, targets)
                        self.assertEqual(
                            params(raw, False)[3], (22, expression(integer(2)))
                        )
        self.assertEqual(seen, {loc["key"] for loc in LOCATIONS})

    def test_different_seeds_share_exe_but_bind_images_and_working_save(self):
        verify_engine(DYNAMIC_BASE, DYNAMIC_SHA)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = Store(
                root / "p", root / "r", exporter=partial(export, dynamic=True)
            )
            with store.lock():
                mappings = []
                for slot, seed, enabled in [
                    (1, "0000001D", True),
                    (2, "ABCDEF12", True),
                    (3, "ABCDEF12", False),
                ]:
                    d = Draft()
                    d.update(items=enabled)
                    d.seed = seed
                    store.create(slot, d)
                    folder, plan, config = store.resume(slot)
                    self.assertEqual(digest(folder / "Boshy.exe"), DYNAMIC_SHA)
                    runtime.validate_assets(folder, plan)
                    mappings.append(runtime.settings(seed, enabled))
                    config[GROUP]["IconI00A4"] = "999"
                    with self.assertRaisesRegex(ValueError, "artwork selection"):
                        validate(plan, config)
                self.assertNotEqual(mappings[0], mappings[1])
                self.assertNotEqual(mappings[1], mappings[2])
                working = root / "working"
                working.mkdir()
                session = WorkingSession(working, store, DYNAMIC_SHA)
                session.stage(1)
                session.commit()
                self.assertFalse(session.marker.exists())
                folder, plan, _ = store.resume(1)
                image = folder / "native-rewards" / "01.png"
                image.write_bytes(image.read_bytes() + b"changed")
                with self.assertRaisesRegex(ValueError, "artwork"):
                    store.resume(1)


if __name__ == "__main__":
    unittest.main()
