"""Publish a complete Options translation before the game reloads its images."""

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from menu_host.store import Store
from native_menu.classic import ClassicModel
from native_menu import options_locale, options_labels, presentation
from native_menu.events import value
from native_menu.presentation_events import GROUP, INPUT_FILE, VIEW_FILE
from native_menu.preferences import LANGUAGES, save_preferences
from transition.events import commands, integer
import recover_boshy_routes as source


class LanguageRefreshTests(unittest.TestCase):
    def test_every_language_is_complete_when_reload_is_published(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = Store(root / "profile", runs=root / "runs")
            save_preferences(store.root, language="ja")
            folder = root / "working"
            folder.mkdir()
            model = ClassicModel(store)
            controller = SimpleNamespace(
                folder=folder, store=store, model=model, mail=Mock(), active_slot=None
            )
            # Reproduce an existing room containing artwork from the old language.
            options_locale.prepare(folder, "ja")
            expected = {}
            for language in LANGUAGES:
                reference = root / language
                reference.mkdir()
                options_locale.prepare(reference, language)
                expected[language] = {
                    path.name: path.read_bytes()
                    for path in (reference / options_locale.DIRECTORY).iterdir()
                }
            writes = presentation.write_config
            observed = []

            def check_publish(path, groups):
                if path.name == VIEW_FILE:
                    language = LANGUAGES[groups[GROUP]["Language"]]
                    for name, content in expected[language].items():
                        self.assertEqual(
                            (folder / options_locale.DIRECTORY / name).read_bytes(),
                            content,
                            (language, name),
                        )
                    observed.append(language)
                writes(path, groups)

            with patch.object(presentation, "write_config", side_effect=check_publish):
                p = presentation.Presentation(controller)
                before = model.draft.shared()
                for language in (*LANGUAGES, *reversed(LANGUAGES)):
                    writes(folder / INPUT_FILE, {GROUP: dict(
                        Language=LANGUAGES.index(language), Pack=0)})
                    p.tick()
                    self.assertEqual(model.language, language)
                    self.assertEqual(model.draft.shared(), before)
            self.assertEqual(set(observed), set(LANGUAGES))

    def test_language_reload_invalidates_every_translated_toggle(self):
        payload = next(p for p, number in source.payloads.items() if number == 20)
        sections, _ = options_locale.transform(20, source.original_sections(payload))
        reloads = [row for row in sections[-1] if b"Generation\0" in row]
        self.assertEqual(len(reloads), 1)
        actions = [cmd[-1] for cmd in commands(reloads[0]) if not cmd[0]]
        for _, _, display, key, _ in options_labels.ROWS:
            if key in options_labels.TOGGLES:
                self.assertIn(
                    value(options_locale.helper(display), 0, integer(-1)), actions, key
                )


if __name__ == "__main__":
    unittest.main()
