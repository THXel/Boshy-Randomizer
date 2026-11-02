"""Native/global preference boundaries, persistence and stable menu artwork."""

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch
from native_menu.presentation import Presentation, PACKS, artwork, write_config
from native_menu.presentation_events import (
    GROUP,
    INPUT_FILE,
    VIEW_FILE,
    VIEW,
    LANGUAGE,
    PACKAGE,
    transform,
    convert_frame,
)
from native_menu.preferences import load_language
from native_menu.classic import ClassicModel, ClassicRenderer
from menu_host.store import Store, save
from transition.events import ini_value
import recover_boshy_dynamic as source


class PresentationTests(unittest.TestCase):
    def test_persistent_global_changes_never_touch_seed_or_plan(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = Store(root / "profile", runs=root / "runs")
            model = ClassicModel(store)
            folder = root / "working"
            folder.mkdir()
            c = SimpleNamespace(
                folder=folder, store=store, model=model, mail=Mock(), active_slot=None
            )
            before = model.draft.shared()
            with patch("native_menu.preferences.system_language", return_value="en"):
                p = Presentation(c)
            write_config(folder / INPUT_FILE, {GROUP: dict(Language=4, Pack=1)})
            p.tick()
            self.assertEqual(model.language, "ja")
            self.assertEqual(p.pack, "kamilia3")
            self.assertEqual(model.draft.shared(), before)
            self.assertEqual(load_language(store.root), "ja")
            data = json.loads((store.root / "native-preferences.json").read_text())
            self.assertEqual(data["presentation_pack"], "kamilia3")
            with patch("native_menu.preferences.system_language", return_value="de"):
                restored = Presentation(c)
            self.assertEqual((restored.language, restored.pack), ("ja", "kamilia3"))
            self.assertEqual(
                save(folder / VIEW_FILE).getint("FusionBloodV1", "Animation"), 16
            )
            for page, keys in (
                ("settings", {"language"}),
                ("cosmetics", {"music_pack", "blood_pack"}),
            ):
                model.go(page)
                self.assertFalse(keys & {r.key for r in model.rows()})
            self.assertEqual(model.draft.shared(), before)

    def test_switching_soundtrack_prepares_assets_without_rewriting_run_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = Store(root / "profile", runs=root / "runs")
            folder = root / "working"
            folder.mkdir()
            model = ClassicModel(store)
            c = SimpleNamespace(
                folder=folder, store=store, model=model, mail=Mock(), active_slot=None
            )
            p = Presentation(c)
            plan = {"seed": "TEST", "options": {"extras": {"music": False}}}
            seed = model.draft.shared()
            for pack, animation in (
                ("kamilia3", 16),
                ("wannafest22", 17),
                ("undertale", 18),
                ("original", 0),
            ):
                p.pack = pack
                p.prepare(plan)
                cfg = save(folder / VIEW_FILE)
                self.assertEqual(
                    cfg.getint("FusionMusicV1", "Enabled"), int(pack != "original")
                )
                self.assertEqual(cfg.getint("FusionBloodV1", "Animation"), animation)
                for key, path in cfg["FusionMusicV1"].items():
                    if key.startswith("cue"):
                        self.assertTrue(
                            (folder / Path(path.replace("\\", "/"))).is_file()
                        )
                self.assertEqual(model.draft.shared(), seed)
            self.assertFalse((folder / "SaveFile1.ini").exists())

    def test_native_rows_surround_original_volume_controls(self):
        original = source.routes.frames[19]
        f, objects = convert_frame(20, original, source.routes.objects)
        positions = {i["objectInfo"]: i["y"] for i in f["instances"]}
        self.assertEqual(
            [positions[n] for n in (LANGUAGE[0], 1337, 1339, PACKAGE[0], 1363)],
            [128, 177, 226, 275, 324],
        )
        self.assertEqual(
            len({i["handle"] for i in f["instances"]}), len(f["instances"])
        )
        self.assertEqual(
            objects[LANGUAGE[0]]["animations"],
            source.routes.objects[1337]["animations"],
        )

    def test_presentation_expressions_use_global_view_not_mutable_save(self):
        for no in (3, 23, 45):
            payload = next(p for p, n in source.routes.payloads.items() if n == no)
            sections = source.sections(payload)
            blob = b"".join(row for rows in sections for row in rows)
            self.assertIn(ini_value("FusionBloodV1", "Animation", 0, oi=VIEW), blob)
            self.assertIn(b"presentation-view.ini", blob)
            for oi in (47, 109):
                self.assertNotIn(
                    ini_value("FusionBloodV1", "Animation", 0, oi=oi), blob
                )

    def test_menu_art_is_stable_across_run_edits_and_changes_on_restart(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            m = ClassicModel(Store(root / "p", runs=root / "r"))
            r = ClassicRenderer(root)
            m.go("cosmetics")
            r.render(m)
            initial = (r.theme, r.cast, r.art_generation)
            for i in range(4):
                m.draft.consume_seed()
                r.render(m)
                self.assertEqual((r.theme, r.cast, r.art_generation), initial)
            r.presentation_seed = "another-application-start"
            r.render(m)
            self.assertEqual(r.art_generation, initial[2] + 1)

    def test_five_language_new_row_art_fits(self):
        with tempfile.TemporaryDirectory() as tmp:
            for language in ("de", "en", "es", "ru", "ja"):
                for pack in PACKS:
                    artwork(tmp, language, pack)


if __name__ == "__main__":
    unittest.main()
