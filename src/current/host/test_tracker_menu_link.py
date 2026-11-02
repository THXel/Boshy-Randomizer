"""Tracker access stays separate from native save selection and the author's link."""

import struct
import tempfile
import unittest
from pathlib import Path
from PIL import Image, ImageChops
from native_menu.classic import ClassicModel, ClassicRenderer
from native_menu import tracker_link
from menu_host.store import Store
from transition.events import commands
import recover_boshy_dynamic as source


class TrackerMenuLinkTests(unittest.TestCase):
    def test_native_link_only_opens_fixed_local_tracker(self):
        before = [[]]
        after, audit = tracker_link.transform(before)
        self.assertEqual(before, [[]])
        self.assertEqual(after[:-1], before)
        cs = commands(after[-1][0])
        acts = [c for c in cs if not c[0]]
        self.assertEqual(len(acts), 1)
        self.assertEqual(acts[0][1:4], (40, 80, 7))
        self.assertIn(tracker_link.URL.encode() + b"\0", acts[0][-1])
        self.assertTrue(any(c[1:3] == (-6, -5) for c in cs if c[0]))
        self.assertTrue(
            all(
                word + b"\0" in after[-1][0]
                for word in (b"Schema", b"Enabled", b"Busy")
            )
        )
        self.assertNotIn(b"Sequence\0", after[-1][0])
        self.assertEqual(audit["bounds"], tracker_link.BOUNDS)
        # Native comparisons include both bounds on both axes.
        for boundary in tracker_link.BOUNDS:
            self.assertIn(struct.pack("<hhHi", -1, 0, 10, boundary), after[-1][0])

    def test_options_hover_loads_only_when_pointer_crosses_button(self):
        result, _ = tracker_link.options_transform([[]])
        hover_rows = result[-1][2:]
        self.assertEqual(len(hover_rows), 5)
        from native_menu.events import alt
        for row in hover_rows:
            cs = commands(row)
            self.assertIn(alt(tracker_link.OPTIONS_CARD, 0), cs[0][-1])
            acts = [c for c in cs if not c[0]]
            self.assertEqual([c[1:3] for c in acts], [(2,89),(2,31)])
        self.assertEqual(tracker_link.BOUNDS, (6,22,148,50))

    def test_link_is_in_title_source_only_and_author_link_remains(self):
        for payload, frame in source.routes.payloads.items():
            if frame not in (2, 3, 20):
                continue
            rows = source.sections(payload)
            links = [
                c
                for sec in rows
                for row in sec
                for c in commands(row)
                if not c[0] and tracker_link.URL.encode() in c[-1]
            ]
            self.assertEqual(len(links), int(frame in (2, 20)))
            if frame == 2:
                self.assertTrue(
                    any(
                        b"https://x.com/soulgryn" in c[-1]
                        for sec in rows
                        for row in sec
                        for c in commands(row)
                    )
                )

    def test_card_visible_before_game_and_on_save_page_in_five_languages(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            model = ClassicModel(Store(path / "p", runs=path / "r"))
            renderer = ClassicRenderer(path)
            for language in ("de", "en", "es", "ru", "ja"):
                model.language = language
                before = (model.slot, model.draft.shared(), model.page)
                image = renderer.render(model)
                updates = Image.open(path / "classic-updates.png").convert("RGBA")
                box = tracker_link.BOUNDS
                self.assertIsNone(
                    ImageChops.difference(image.crop(box), updates.crop(box)).getbbox()
                )
                self.assertGreater(image.getpixel((8, 40))[3], 0)
                self.assertEqual(
                    image.getpixel((8, 10))[3], 0
                )  # Made by Solgryn retained
                self.assertEqual(image.getpixel((300, 100))[3], 0)  # logo retained
                self.assertEqual((model.slot, model.draft.shared(), model.page), before)
                model.busy = True
                disabled = renderer.render(model)
                self.assertIsNotNone(
                    ImageChops.difference(
                        image.crop(box).convert("RGB"),
                        disabled.crop(box).convert("RGB"),
                    ).getbbox()
                )
                model.busy = False


if __name__ == "__main__":
    unittest.main()
