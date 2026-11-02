"""Old menu choreography and selection must survive presentation migration."""

import struct
import unittest
import tempfile
from pathlib import Path
from PIL import Image, ImageChops
from unittest.mock import Mock
from native_menu.classic import ClassicModel, ClassicRenderer
from native_menu.classic_art import VARIANTS, layout
from native_menu.classic_events import transform
from menu_host.store import Store
from transition.events import commands
import recover_boshy_targets as source


class ClassicMenuTests(unittest.TestCase):
    def test_old_selector_and_intro_objects_are_not_hidden_by_overlay(self):
        payload = next(p for p, n in source.routes.payloads.items() if n == 2)
        before = source.sections(payload)
        after, audit = transform(before)
        self.assertTrue(audit["classic_selector"])
        # The replacement overlay events no longer hide the original logo/digits/cursor.
        for row in after[-2]:
            self.assertFalse(
                any(
                    not c and k == 2 and code == 26 and oi in (41, 43, 44, 45, 46)
                    for c, k, code, oi, raw in commands(row)
                )
            )
        self.assertTrue(
            any(
                not c and (k, code, oi) == (2, 24, 70)
                for row in after[-1]
                for c, k, code, oi, raw in commands(row)
            )
        )
        self.assertEqual(len(layout()), 32)
        self.assertEqual(audit["independent_intro_variants"], VARIANTS)
        # Character frame geometry is recovered directly from the original animation.
        self.assertEqual({r[0] for r in layout()}, {18, 21, 23})

    def test_native_arrows_stay_native_but_save_confirmation_is_intercepted(self):
        payload = next(p for p, n in source.routes.payloads.items() if n == 2)
        after, _ = transform(source.sections(payload))
        # Rows in the original MenuTrigger behaviour still change its selection.
        movements = []
        for sec in after[:-2]:
            for row in sec:
                cs = commands(row)
                if any(
                    not c and k == 2 and code in (32, 33) and oi == 46
                    for c, k, code, oi, raw in cs
                ):
                    movements.append(row)
        self.assertGreaterEqual(len(movements), 4)
        self.assertTrue(
            all(
                b"Modal\0" in row
                for row in movements
                if any(c and k == -6 for c, k, code, oi, raw in commands(row))
            )
        )

    def test_empty_slot_opens_options_and_saved_slot_resumes(self):
        with tempfile.TemporaryDirectory() as t:
            m = ClassicModel(Store(Path(t) / "p", runs=Path(t) / "r"))
            seed = m.draft.seed
            m.key(39)
            self.assertEqual(
                m.slot, 1
            )  # Fusion, rather than Python, moves the selector.
            m.key(13)
            self.assertEqual(m.page, "settings")
            self.assertEqual(m.rows()[0].key, "new")
            self.assertEqual(m.draft.seed, seed)
            m.go("home")
            m.saved = Mock(return_value=True)
            m.key(13)
            self.assertEqual(m.action, "resume")

    def test_submenu_edges_show_native_scene_instead_of_a_second_background(self):
        with tempfile.TemporaryDirectory() as t:
            m = ClassicModel(Store(Path(t) / "p", runs=Path(t) / "r"))
            renderer = ClassicRenderer(t)
            for language in ("de", "en", "es", "ru", "ja"):
                m.language = language
                for page in ("settings", "cosmetics", "route"):
                    m.go(page)
                    image = renderer.render(m)
                    for point in (
                        (11, 200),
                        (400, 195),
                        (635, 300),
                        (400, 458),
                        (12, 196),
                    ):
                        self.assertEqual(
                            image.getpixel(point)[3], 0, (language, page, point)
                        )
                    self.assertEqual(image.getpixel((220, 235))[3], 255)
                    self.assertEqual(image.getpixel((300, 470))[3], 255)

    def test_supplementary_panels_leave_logo_and_large_save_digits_transparent(self):
        with tempfile.TemporaryDirectory() as t:
            m = ClassicModel(Store(Path(t) / "p", runs=Path(t) / "r"))
            renderer = ClassicRenderer(t)
            for language in ("de", "en", "es", "ru", "ja"):
                m.language = language
                image = renderer.render(m)
                updates = Image.open(Path(t) / "classic-updates.png").convert("RGBA")
                # The first Game/Options screen must show the same author link
                # as the later save page; this previously existed only there.
                footer = (90, 432, 226, 464)
                self.assertIsNone(
                    ImageChops.difference(
                        updates.crop(footer), image.crop(footer)
                    ).getbbox()
                )
                self.assertEqual(updates.getpixel((107, 448))[3], 0)
                self.assertTrue(
                    any(
                        r > 200 and g > 200 and b > 200 and a > 200
                        for r, g, b, a in updates.crop((130, 440, 226, 455)).getdata()
                    )
                )
                self.assertEqual(image.getpixel((300, 100))[3], 0)
                for x in (246, 317, 396):
                    self.assertEqual(image.getpixel((x, 351))[3], 0)


if __name__ == "__main__":
    unittest.main()
