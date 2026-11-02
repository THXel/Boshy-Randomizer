"""The original animated intro keeps authorship and a real website link."""

import unittest
import struct
import recover_boshy_routes as source
from native_menu import attribution, pixel_wordmark
from transition.events import commands


class AttributionTests(unittest.TestCase):
    def test_native_hyperlink_preserves_animation_and_adds_website_hit_area(self):
        payload = next(p for p, f in source.payloads.items() if f == 1)
        before = source.original_sections(payload)
        after, audit = attribution.transform(1, before)
        replacements = 0
        for si, rows in enumerate(before):
            self.assertEqual(len(after[si]), len(rows) + int(si == 4))
            for ri, row in enumerate(rows):
                old, new = commands(row), commands(after[si][ri])
                self.assertEqual(len(old), len(new))
                for a, b in zip(old, new):
                    if a[1:4] == (40, 80, 7) and b"http://www.solgryn.org" in a[-1]:
                        replacements += 1
                        self.assertIn(attribution.URL.encode() + b"\0", b[-1])
                    else:
                        self.assertEqual(a, b)
        self.assertEqual(replacements, 1)
        click = commands(after[4][-1])
        self.assertEqual(struct.unpack_from("<H", click[0][-1], 32)[0], 13)
        self.assertTrue(any(b"https://grynsoft.com/" in c[-1] for c in click))
        self.assertFalse(audit[0]["menu_credit"])
        self.assertEqual(attribution.transform(2, before), (before, []))

    def test_only_three_intro_wordmark_images_change(self):
        before = source.write_mfa.inflated_images(source.app)
        after = pixel_wordmark.update_bank(before)
        self.assertEqual(set(before), set(after))
        self.assertEqual(
            {n for n in before if before[n] != after[n]}, pixel_wordmark.IMAGE_HANDLES
        )
        self.assertEqual(before[5982], after[5982])  # Animated original emblem.
        for n in pixel_wordmark.IMAGE_HANDLES:
            raw = after[n]
            self.assertEqual(struct.unpack_from("<HH", raw, 12), (208, 63))
            self.assertEqual(struct.unpack_from("<hh", raw, 20), (104, 0))
        website, author, mod = pixel_wordmark.LINES
        self.assertEqual(website[0], "grynsoft.com")
        self.assertEqual(author[0], "Original by Solgryn")
        self.assertEqual(mod[0], "Modded by THXel")
        self.assertLess(mod[1], website[1])
        self.assertLess(mod[3], author[3])


if __name__ == "__main__":
    unittest.main()
