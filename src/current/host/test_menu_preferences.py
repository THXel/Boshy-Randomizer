import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from native_menu.preferences import language_code, load_language, system_language
from menu_host.draft import Draft


class PreferenceTests(unittest.TestCase):
    def test_supported_system_locales_and_english_fallback(self):
        for value, expected in [
            ("de_DE.UTF-8", "de"),
            ("en-US", "en"),
            ("es_ES", "es"),
            ("ru_RU", "ru"),
            ("ja-JP", "ja"),
            ("fr_FR", "en"),
            ("C.UTF-8", "en"),
        ]:
            with patch.dict("os.environ", {"LANG": value}, clear=True):
                self.assertEqual(system_language(), expected)
        self.assertIsNone(language_code(None))

    def test_saved_choice_precedes_system_and_invalid_preferences_fall_back(self):
        with (
            tempfile.TemporaryDirectory() as t,
            patch.dict("os.environ", {"LANGUAGE": "ja_JP"}, clear=True),
        ):
            path = Path(t) / "native-preferences.json"
            self.assertEqual(load_language(t), "ja")
            path.write_text(json.dumps({"language": "es"}))
            self.assertEqual(load_language(t), "es")
            for broken in ("{", "[]", '{"language":"xx"}'):
                path.write_text(broken)
                self.assertEqual(load_language(t), "ja")

    def test_new_run_defaults_and_imported_choices_are_separate(self):
        d = Draft()
        self.assertTrue(d.options["extras"]["no_mouse_ghost"])
        d.update(no_mouse_ghost=False)
        code = d.shared()
        e = Draft()
        e.import_seed(code)
        self.assertFalse(e.options["extras"]["no_mouse_ghost"])
        self.assertEqual(e.shared(), code)


if __name__ == "__main__":
    unittest.main()
