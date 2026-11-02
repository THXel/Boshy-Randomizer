"""Presentation changes must not alter run settings or native option actions."""

import tempfile
import unittest
from pathlib import Path
from native_menu.classic import ClassicModel, ClassicRenderer
from native_menu.options_locale import (
    prepare,
    transform,
    convert_frame,
    targets,
    helper,
)
from native_menu import history, options_labels, layout
from menu_host.store import Store
from transition.events import commands
import recover_boshy_classic as source


class MenuCompletionTests(unittest.TestCase):
    def test_hover_never_activates_settings_or_changes_seed(self):
        with tempfile.TemporaryDirectory() as tmp:
            model = ClassicModel(Store(Path(tmp) / "profile", runs=Path(tmp) / "runs"))
            model.go("gameplay")
            before = model.draft.shared()
            for i in range(len(model.visible())):
                x, y, _, _ = layout.row_rect(model.page, i)
                model.key(1001, x + 2, y + 2)
                self.assertEqual(model.focus, i)
                self.assertEqual(model.draft.shared(), before)
                self.assertIsNone(model.action)
            model.go("home")
            model.key(1001, 470, 408)
            self.assertEqual(model.page, "home")
            self.assertIsNone(model.action)

    def test_history_all_languages_readonly_and_paged(self):
        with tempfile.TemporaryDirectory() as tmp:
            model = ClassicModel(Store(Path(tmp) / "p", runs=Path(tmp) / "r"))
            for lang in ("de", "en", "es", "ru", "ja"):
                model.language = lang
                model.go("updates")
                model.focus = 0
                before = model.draft.shared()
                self.assertEqual(len(history.entries(lang)), len(history.ENTRIES))
                self.assertTrue(
                    all(date and caption for date, caption in history.entries(lang))
                )
                for row in model.rows()[:-1]:
                    model.select(row.key)
                self.assertEqual(model.draft.shared(), before)
                model.key(34)
                self.assertEqual(model.focus, layout.PAGE_SIZE % len(model.rows()))
                self.assertIn(model.rows()[model.focus], model.visible())
                model.focus = len(model.rows()) - 1
                self.assertEqual(model.rows()[model.focus].key, "back")
                model.key(13)
                self.assertEqual(model.page, "tools")

    def test_original_options_events_and_instances_preserved(self):
        payload = next(p for p, n in source.routes.payloads.items() if n == 20)
        before = source.sections(payload)
        after, audit = transform(20, before)
        self.assertEqual(after[:-1], before)
        self.assertEqual(audit[0]["translated_labels"], 17)
        conditions = [c for row in after[-1] for c in commands(row) if c[0]]
        self.assertEqual(
            sum(c[1:3] == (32, -27) for c in conditions),
            2 * len(options_labels.TOGGLES),
        )
        self.assertFalse(any(c[1] == 33 for c in conditions))
        acts = [c for row in after[-1] for c in commands(row) if not c[0]]
        self.assertFalse(
            any(c[1] == 33 for c in acts), "Localisation must never write an INI"
        )
        frame = source.routes.frames[19]
        changed, objs = convert_frame(20, frame, source.routes.objects)
        self.assertEqual(
            changed["instances"][: len(frame["instances"])], frame["instances"]
        )
        handles = [i["handle"] for i in changed["instances"]]
        self.assertEqual(len(set(handles)), len(handles))
        self.assertTrue(all(helper(oi) in objs for oi in targets()))
        self.assertEqual(transform(3, before), (before, []))

    def test_five_language_assets_fit_and_render_in_title(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for lang in ("de", "en", "es", "ru", "ja"):
                folder = root / lang
                folder.mkdir()
                prepare(folder, lang)
                for row in options_labels.ROWS:
                    self.assertTrue(
                        (folder / "native-options" / f"label-{row[0]}.png").is_file()
                    )
                model = ClassicModel(Store(folder / "p", runs=folder / "r"))
                model.language = lang
                renderer = ClassicRenderer(folder)
                for page in ("home", "updates", "gameplay"):
                    model.go(page)
                    renderer.render(model)


if __name__ == "__main__":
    unittest.main()
