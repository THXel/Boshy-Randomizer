"""Regression checks against the actual private compiled graphics package."""

import json
import struct
import unittest
from pathlib import Path
from visuals.scenery_pack import App, record_selection, prepare, BASE_SHA
from visuals.fusion25 import (
    image_bank,
    property_bank,
    write_images,
    integrity_sum,
    lz4_decode,
)

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs/Fusion-Scenery-20261023"
BASE = Path(
    "/home/thxel/Games/clickteam-fusion-developer/drive_c/BoshyTransitions/Boshy-actors.exe"
)
ORIGINAL = Path(
    "/home/thxel/.local/share/boshy-randomizer/IWBTB/I Wanna Be The Boshy.exe"
)


class SceneryPackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = App(BASE)
        cls.new = App(OUT / "Boshy-scenery.exe")
        cls.audit = json.loads((OUT / "audit.json").read_text())
        cls.old_images, cls.old_size = image_bank(
            cls.base.payload(0x6666), cls.base.payload(0x5555)
        )
        cls.images, cls.size = image_bank(
            cls.new.payload(0x6666), cls.new.payload(0x5555)
        )
        cls.old_props = property_bank(
            cls.base.payload(0x2256), cls.base.payload(0x2257)
        )
        cls.props = property_bank(cls.new.payload(0x2256), cls.new.payload(0x2257))

    def test_every_original_image_record_is_unchanged(self):
        self.assertEqual(len(self.old_images), 6908)
        for h, im in self.old_images.items():
            self.assertEqual(im.bytes(), self.images[h].bytes(), h)
        ib, ix = write_images(self.old_images, self.old_size)
        self.assertEqual(ib, self.base.payload(0x6666))
        self.assertEqual(ix, self.base.payload(0x5555))

    def test_all_clones_preserve_every_alpha_value_and_anchor(self):
        self.assertEqual(len(self.audit["changed"]), 179)
        for row in self.audit["changed"]:
            original = self.old_images[row["original_image"]]
            clone = self.images[row["new_image"]]
            self.assertEqual(original.size, clone.size)
            self.assertEqual(original.header[28:40], clone.header[28:40])
            self.assertEqual(
                original.rgba().getchannel("A").tobytes(),
                clone.rgba().getchannel("A").tobytes(),
                row["source_oi"],
            )

    def test_only_reviewed_image_words_change_not_collision_or_events(self):
        remaining = [bytearray(p) for p in self.props]
        for row in self.audit["changed"]:
            oi, at = row["compiled_oi"], row["image_offset"]
            self.assertEqual(
                struct.unpack_from("<H", remaining[oi], at)[0], row["new_image"]
            )
            remaining[oi][at : at + 2] = self.old_props[oi][at : at + 2]
        self.assertEqual([bytes(p) for p in remaining], self.old_props)
        self.assertEqual(
            self.base.data[: self.base.chunks[0].offset],
            self.new.data[: self.new.chunks[0].offset],
        )
        for old, new in zip(self.base.chunks, self.new.chunks):
            self.assertEqual(old.id, new.id)
            if old.id not in [0x2256, 0x2257, 0x6666, 0x5555, 0x2242]:
                self.assertEqual(
                    self.base.data[old.offset : old.offset + 8 + old.size],
                    self.new.data[new.offset : new.offset + 8 + new.size],
                    hex(old.id),
                )

    def test_integrity_is_updated_not_disabled(self):
        values = []
        for app in [self.base, self.new]:
            start = app.by_id[0x222F][0].offset
            end = app.by_id[0x2242][0]
            self.assertEqual((end.flags, end.size), (2, 4))
            ciphertext = struct.unpack_from("<I", app.data, end.offset + 8)[0]
            values.append(ciphertext ^ integrity_sum(app.data[start : end.offset]))
        self.assertEqual(values[0], values[1])
        # Independently decoded base checksum, cross-checked with loader logic.
        p = self.base.by_id[0x2242][0]
        self.assertEqual(
            integrity_sum(self.base.data[self.base.by_id[0x222F][0].offset : p.offset]),
            0x648599BE,
        )

    def test_protected_platform_and_actor_images_are_not_repointed(self):
        changed = {r["source_oi"] for r in self.audit["changed"]}
        self.assertFalse(
            changed & {1054, 1119, 1088, 1089, 153, 165, 2048, 2084, 318, 553, 561}
        )
        self.assertEqual({r["category"] for r in self.audit["changed"]}, {1, 2, 4})

    def test_off_is_byte_identical_and_invalid_settings_fail(self):
        result, audit = prepare(
            BASE, ORIGINAL, "off-fixture", {"sprite_scenery": False}
        )
        self.assertEqual(result, self.base.data)
        self.assertTrue(audit["unchanged"])
        self.assertEqual(audit["sha256"], BASE_SHA)
        for bad in [{"sprite_scenery": 1}, {"sprite_dim": 101}, {"sprite_dim": True}]:
            with self.assertRaises(ValueError):
                record_selection(bad, [])

    def test_corrupt_indices_and_lz4_lengths_fail_closed(self):
        offsets = bytearray(self.base.payload(0x5555))
        offsets[0] ^= 1
        with self.assertRaises(ValueError):
            image_bank(self.base.payload(0x6666), offsets)
        im = next(iter(self.old_images.values()))
        with self.assertRaises(ValueError):
            lz4_decode(im.packed, 1)


if __name__ == "__main__":
    unittest.main()
