"""Exact whole-bank reconstruction and refusal tests for the private patch recipe."""

import copy
import json
import unittest
from types import SimpleNamespace
from distribution.source_audio import recipe, restore, original_sounds
from visuals.scenery_pack import App
from export_native_run import ORIGINAL
from native_menu.builds import DYNAMIC_BASE


class SourceAudioTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = App(ORIGINAL)
        cls.target = App(DYNAMIC_BASE)
        cls.recipe = recipe(cls.original, cls.target)

    def test_all_audio_reconstructed_exactly_from_original(self):
        result = restore(self.original, self.recipe)
        self.assertEqual(
            result, (self.target.payload(0x6668), self.target.payload(0x5557))
        )
        self.assertEqual(len(self.recipe["rows"]), 471)
        self.assertLess(len(json.dumps(self.recipe).encode()), 250_000)

    def test_other_original_version_is_rejected_before_parsing(self):
        with self.assertRaisesRegex(ValueError, "original game version"):
            original_sounds(SimpleNamespace(data=b"unrecognized EXE"))

    def test_modified_source_reference_and_duplicate_handles_are_rejected(self):
        bad = copy.deepcopy(self.recipe)
        bad["rows"][0]["audio_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "Source audio checksum"):
            restore(self.original, bad)
        bad = copy.deepcopy(self.recipe)
        bad["rows"][1] = bad["rows"][0]
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            restore(self.original, bad)

    def test_changed_output_checksum_is_rejected(self):
        bad = copy.deepcopy(self.recipe)
        bad["bank_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "bank checksum"):
            restore(self.original, bad)


if __name__ == "__main__":
    unittest.main()
