"""Native music events, category-safe assets and isolated persistent slot handoff."""

import copy
import json
import tempfile
import unittest
from functools import partial
from pathlib import Path
from music import runtime
from music.soundtrack import mapping, pack_rows, cue_kind
from native_menu.builds import DYNAMIC_SHA
from native_menu.session_store import WorkingSession
from menu_host.store import Store, digest, save
from menu_host.draft import Draft
from export_native_run import export, ORIGINAL
from transition.events import commands
from transition.router import params
import recover_boshy_routes as source


class RuntimeMusicTests(unittest.TestCase):
    def test_music_uses_dynamic_build_and_resume_still_rejects_incompatible_assets(
        self,
    ):
        from types import SimpleNamespace
        from native_menu.combined import CombinedController

        controller = CombinedController.__new__(CombinedController)
        controller.model = SimpleNamespace(draft=Draft())
        controller.dynamic = True
        self.assertTrue(controller.compatible_draft())
        controller.model.draft.update(music=True)
        self.assertTrue(controller.compatible_draft())
        controller.dynamic = False
        self.assertFalse(controller.compatible_draft())
        # A resume must reject incompatible assets before touching saved slots.
        with self.assertRaisesRegex(ValueError, "noch nicht verfügbar"):
            controller.begin()
        controller.dynamic = True
        from unittest.mock import patch
        from native_menu import builds

        controller.model.draft.update(sprite_scenery=True)
        with patch.object(builds, "DYNAMIC_SCENERY", False):
            self.assertFalse(controller.compatible_draft())
            with self.assertRaisesRegex(ValueError, "noch nicht verfügbar"):
                controller.begin()
        with patch.object(builds, "DYNAMIC_SCENERY", True):
            self.assertTrue(controller.compatible_draft())

    def test_only_music_playback_changes_and_channels_loops_effects_are_preserved(self):
        affected = 0
        for payload, frame in source.payloads.items():
            before = source.original_sections(payload)
            after, audit = runtime.transform(
                frame, before, source.objects, source.frames[frame - 1]["instances"]
            )
            if not audit:
                self.assertEqual(after, before)
                continue
            for si, (oldrows, newrows) in enumerate(zip(before, after)):
                it = iter(newrows[2:] if si == 0 else newrows)
                for row in oldrows:
                    cs = commands(row)
                    original = next(it)
                    if not any(runtime.cue(c) for c in cs):
                        self.assertEqual(row, original)
                        continue
                    replacement = next(it)
                    self.assertIn(b"Enabled\0", original)
                    self.assertIn(b"Enabled\0", replacement)
                    acts = [c for c in cs if not c[0]]
                    fallback = [c for c in commands(original) if not c[0]]
                    changed = [c for c in commands(replacement) if not c[0]]
                    self.assertEqual(fallback, acts)
                    self.assertEqual(len(changed), len(acts))
                    for a, b in zip(acts, changed):
                        if runtime.cue(a):
                            affected += 1
                            self.assertEqual(b[1:3], (-2, 28 if a[2] == 11 else 29))
                            self.assertEqual(params(a[-1])[1:], params(b[-1])[1:])
                        else:
                            self.assertEqual(a, b)
                self.assertEqual(list(it), [])
        self.assertGreater(affected, 80)

    def test_each_pack_has_category_safe_files_and_rejects_changes(self):
        with tempfile.TemporaryDirectory() as t:
            for pack in ("original", "kamilia3", "wannafest22", "undertale"):
                folder = Path(t) / pack
                folder.mkdir()
                root = ORIGINAL.parents[1] / "soundpacks" / pack
                rows, settings = runtime.prepare(
                    folder, "native-test", pack, root, True
                )
                plan = dict(
                    runtime_music_schema=1,
                    runtime_music_assets=rows,
                    runtime_music_settings=settings,
                    music_enabled=True,
                )
                runtime.validate_assets(folder, plan)
                catalogue = pack_rows(root, pack) if pack != "original" else None
                expected = mapping("native-test", pack, catalogue)
                kinds = (
                    {r["file"]: r["kind"] for r in catalogue}
                    if catalogue
                    else {n: cue_kind(n) for n in runtime.NAMES}
                )
                for r in rows:
                    self.assertEqual(r["target"], expected[r["cue"]])
                    self.assertEqual(r["kind"], kinds[r["target"]])
                bad = copy.deepcopy(plan)
                bad["runtime_music_assets"][0]["file"] = "../outside.ogg"
                with self.assertRaises(ValueError):
                    runtime.validate_assets(folder, bad)
                path = folder / runtime.DIRECTORY / rows[0]["file"]
                path.write_bytes(b"changed")
                with self.assertRaises(ValueError):
                    runtime.validate_assets(folder, plan)

    def test_slot_music_changes_without_executable_change_and_off_clears_assets(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            store = Store(
                root / "profile",
                runs=root / "runs",
                exporter=partial(export, dynamic=True),
            )
            with store.lock():
                for slot, pack in (
                    (1, "kamilia3"),
                    (2, "wannafest22"),
                    (3, "original"),
                ):
                    draft = Draft()
                    draft.set_mode("normal")
                    draft.update(music=slot != 3)
                    draft.select_pack("music_pack", pack)
                    store.create(slot, draft)
                    self.assertEqual(
                        digest(store.folder(slot) / "Boshy.exe"), DYNAMIC_SHA
                    )
                working = root / "working"
                working.mkdir()
                session = WorkingSession(working, store, DYNAMIC_SHA)
                for slot in (1, 2, 3, 1):
                    session.stage(slot)
                    plan = json.loads((store.folder(slot) / "plan.json").read_text())
                    runtime.validate_assets(working, plan)
                    self.assertEqual(
                        len(list((working / runtime.DIRECTORY).iterdir())),
                        45 if slot != 3 else 0,
                    )
                    self.assertEqual(
                        save(working / "SaveFile1.ini").getint(
                            runtime.GROUP, "Enabled"
                        ),
                        int(slot != 3),
                    )
                    session.commit()


if __name__ == "__main__":
    unittest.main()
