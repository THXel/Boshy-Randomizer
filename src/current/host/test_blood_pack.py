"""Exact-data checks for both locally supplied native blood packs."""

import hashlib, json, struct, tempfile, unittest
from pathlib import Path
from visuals.scenery_pack import App
from visuals.fusion25 import image_bank, property_bank
from visuals.blood_pack import load_pack

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs/Fusion-Blood-20261024"
INSTALLED = Path("/home/thxel/.local/share/boshy-randomizer/soundpacks")
BUILDS = Path("/home/thxel/Games/clickteam-fusion-developer/drive_c/BoshyTransitions")


class BloodPackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = App(OUT / "Boshy-blood-scenery.exe")
        cls.before, _ = image_bank(cls.base.payload(0x6666), cls.base.payload(0x5555))
        cls.props = property_bank(cls.base.payload(0x2256), cls.base.payload(0x2257))
        cls.packs = []
        for name in ("kamilia3", "wannafest22"):
            app = App(BUILDS / ("Boshy-blood-" + name + ".exe"))
            audit = json.loads((OUT / (name + "-audit.json")).read_text())
            images, _ = image_bank(app.payload(0x6666), app.payload(0x5555))
            cls.packs.append((name, app, audit, images))

    def test_every_vanilla_and_scenery_image_stays_byte_identical(self):
        self.assertEqual(len(self.before), 7087)
        for name, app, audit, images in self.packs:
            self.assertEqual(hashlib.sha256(app.data).hexdigest(), audit["sha256"])
            for handle, im in self.before.items():
                self.assertEqual(im.bytes(), images[handle].bytes(), (name, handle))

    def test_imported_images_exactly_match_pack_pixels_and_origins(self):
        for name, _, audit, images in self.packs:
            frames, origin, fps = load_pack(INSTALLED / name)
            self.assertEqual(len(frames), len(audit["handles"]))
            for frame, handle in zip(frames, audit["handles"]):
                stored = images[handle]
                self.assertEqual(frame.tobytes(), stored.rgba().tobytes())
                self.assertEqual(
                    tuple(origin), struct.unpack_from("<2h", stored.header, 28)
                )

    def test_only_custom_animation_images_and_speed_change(self):
        for name, app, audit, _ in self.packs:
            props = [
                bytearray(p)
                for p in property_bank(app.payload(0x2256), app.payload(0x2257))
            ]
            self.assertEqual({r["source_oi"] for r in audit["changed"]}, {105, 1032})
            for row in audit["changed"]:
                oi = row["compiled_oi"]
                for offset in [*row["image_offsets"], row["speed_offset"]]:
                    props[oi][offset : offset + 2] = self.props[oi][offset : offset + 2]
            self.assertEqual([bytes(p) for p in props], self.props)
            self.assertEqual(
                app.data[: app.chunks[0].offset],
                self.base.data[: self.base.chunks[0].offset],
            )
            for before, after in zip(self.base.chunks, app.chunks):
                self.assertEqual(before.id, after.id)
                if before.id not in (0x2256, 0x2257, 0x6666, 0x5555, 0x2242):
                    self.assertEqual(
                        self.base.data[before.offset : before.offset + 8 + before.size],
                        app.data[after.offset : after.offset + 8 + after.size],
                    )

    def test_invalid_pack_paths_and_dimensions_are_rejected(self):
        data = json.loads((INSTALLED / "kamilia3/pack.json").read_text())
        for field, value in [("size", [999, 31]), ("origin", [-1, 15]), ("fps", 0)]:
            with tempfile.TemporaryDirectory() as folder:
                copy = json.loads(json.dumps(data))
                copy["death_visuals"]["blood"][field] = value
                (Path(folder) / "pack.json").write_text(json.dumps(copy))
                with self.assertRaises(ValueError):
                    load_pack(folder)
        with tempfile.TemporaryDirectory() as folder:
            data["death_visuals"]["blood"]["frames"][0]["file"] = "../outside.png"
            (Path(folder) / "pack.json").write_text(json.dumps(data))
            with self.assertRaises(ValueError):
                load_pack(folder)


if __name__ == "__main__":
    unittest.main()
