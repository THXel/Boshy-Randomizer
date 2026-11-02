"""Native checklist input and receipts must not add save traffic or change gameplay."""

import tempfile
import unittest
from pathlib import Path
from native_menu import target_hud as hud
from transition.events import commands
import recover_boshy_routes as source


class TargetHudTests(unittest.TestCase):
    def test_target_receipts_and_bounded_two_column_layout(self):
        self.assertEqual(len(hud.ROWS), 41)
        self.assertLessEqual(len(hud.ROWS), 2 * hud.ROWS_PER_COLUMN)
        self.assertEqual(len({row[0] for row in hud.ROWS}), len(hud.ROWS))
        self.assertTrue(all(row[1] == "Collectables" for row in hud.ROWS[:19]))
        self.assertTrue(all(row[1] == "FusionRouteV4" for row in hud.ROWS[19:]))
        self.assertLess(36 + hud.ROWS_PER_COLUMN * 20, 480)
        self.assertLess(8 + 232 + 230, 640)

    def test_original_events_untouched_and_no_polling_or_save_actions(self):
        for payload, frame in source.payloads.items():
            before = source.original_sections(payload)
            after, audit = hud.transform(
                frame, before, source.objects, source.frames[frame - 1]["instances"]
            )
            if frame not in hud.FRAMES:
                self.assertIs(after, before)
                self.assertFalse(audit)
                continue
            self.assertEqual(after[:-1], before)
            added = [c for row in after[-1] for c in commands(row)]
            self.assertFalse(any(not c[0] and c[1] in (33, -3, -2) for c in added))
            self.assertTrue(any(c[0] and c[1:3] == (-6, -5) for c in added))
            self.assertTrue(any(b"Collectables\0" in c[-1] for c in added))
            self.assertTrue(any(b"FusionRouteV4\0" in c[-1] for c in added))

    def test_artwork_in_all_languages_is_cached_and_complete(self):
        from PIL import Image

        with tempfile.TemporaryDirectory() as t:
            for language in hud.LABEL:
                hud.prepare(t, language)
                root = Path(t) / "native-targets"
                paths = list(root.glob("*.png"))
                self.assertEqual(len(paths), 86)
                stamps = {p.name: p.stat().st_mtime_ns for p in paths}
                hud.prepare(t, language)
                self.assertEqual(stamps, {p.name: p.stat().st_mtime_ns for p in paths})
                for p in paths:
                    with Image.open(p) as im:
                        self.assertEqual(
                            im.size,
                            (22, 22) if p.name.startswith("button") else (230, 20),
                        )
                with Image.open(root / "button-0-0.png") as icon:
                    self.assertEqual(icon.getpixel((0, 0))[3], 0)
                    self.assertEqual(icon.getpixel((21, 21))[3], 0)
                    self.assertLess(
                        sum(a > 0 for a in icon.getchannel("A").getdata()), 340
                    )
                self.assertNotEqual(
                    (root / "button-0-0.png").read_bytes(),
                    (root / "button-0-1.png").read_bytes(),
                )
                self.assertNotEqual(
                    (root / "row-0-0.png").read_bytes(),
                    (root / "row-0-1.png").read_bytes(),
                )

    def test_helper_objects_have_no_gameplay_qualifiers(self):
        frame = source.frames[2]
        result, objects = hud.convert_frame(3, frame, source.objects)
        self.assertEqual(len(result["instances"]) - len(frame["instances"]), 42)
        for oi in range(hud.BUTTON, hud.FIRST + len(hud.ROWS)):
            self.assertEqual(objects[oi]["qualifiers"], [])
        self.assertNotIn(hud.BUTTON, source.objects)
