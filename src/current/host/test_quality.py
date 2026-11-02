"""Readability guarantees and stale-editor build protection."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image
from quality.build import stamp_sections, check
from distribution.identity import source_digest, sha256
from visuals.readability import preserve_edges
from native_menu.builds import DYNAMIC_BASE


class ReadabilityTests(unittest.TestCase):
    def test_tile_edges_survive_while_interior_stays_randomized(self):
        source = Image.new("RGBA", (5, 5), "white")
        randomized = Image.new("RGBA", (5, 5), "red")
        actual = preserve_edges(source, randomized)
        for x in range(5):
            self.assertEqual(actual.getpixel((x, 0)), source.getpixel((x, 0)))
            self.assertEqual(actual.getpixel((x, 4)), source.getpixel((x, 4)))
        self.assertEqual(actual.getpixel((2, 2)), randomized.getpixel((2, 2)))

    def test_transparency_geometry_and_thin_hazards_are_preserved(self):
        source = Image.new("RGBA", (5, 5))
        source.putpixel((2, 2), (255, 255, 255, 128))
        other = source.copy()
        other.putpixel((2, 2), (0, 0, 0, 128))
        result = preserve_edges(source, other)
        self.assertEqual(result.tobytes(), source.tobytes())
        other.putpixel((2, 2), (0, 0, 0, 255))
        with self.assertRaisesRegex(ValueError, "transparency"):
            preserve_edges(source, other)


class BuildIdentityTests(unittest.TestCase):
    def test_stamp_is_embedded_and_unguarded_legacy_generation_is_unchanged(self):
        with patch.dict(os.environ, {"BOSHY_BUILD_SOURCE_SHA": "a" * 64}):
            result = stamp_sections([])
        self.assertIn(b"a" * 64, result[0][0])
        with patch.dict(os.environ, {"BOSHY_BUILD_SOURCE_SHA": "bad"}):
            with self.assertRaises(ValueError):
                stamp_sections([])
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(stamp_sections([]), [])

    def test_incomplete_compile_is_rejected_even_with_title_stamp(self):
        from types import SimpleNamespace
        from quality.build import complete_structure
        from visuals.scenery_pack import App

        app = App(DYNAMIC_BASE)
        self.assertGreater(complete_structure(app)["images"], 0)
        for incomplete in (
            SimpleNamespace(stop="truncated", payload=app.payload),
            SimpleNamespace(stop="terminator", payload=lambda cid: None if cid == 0x5555 else app.payload(cid)),
        ):
            with self.assertRaisesRegex(ValueError, "Incomplete executable"):
                complete_structure(incomplete)

    def test_previously_compiled_game_fails_new_source_identity_check(self):
        import json
        from quality.build import LAB

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "source.mfa"
            project.write_bytes(b"project")
            manifest = root / "build.json"
            manifest.write_text(
                json.dumps(
                    {
                        "schema": 1,
                        "project": str(project),
                        "project_sha256": sha256(project),
                        "source_sha256": source_digest(LAB),
                    }
                )
            )
            with self.assertRaisesRegex(ValueError, "Wrong or stale"):
                check(manifest, DYNAMIC_BASE)


if __name__ == "__main__":
    unittest.main()
