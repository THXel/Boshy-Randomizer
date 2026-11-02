"""Compiled pack fidelity and save-local switching without replacing the EXE."""

import struct
import tempfile
import unittest
from functools import partial
from pathlib import Path
from visuals.embedded_blood import assets, settings
from visuals.scenery_pack import App, object_mapping
from visuals.fusion25 import image_bank, property_bank, animation_slot
from export_native_run import ORIGINAL, export
from native_menu.builds import DYNAMIC_BASE, DYNAMIC_SHA
from menu_host.store import Store, digest, save
from menu_host.draft import Draft
from native_menu.session_store import WorkingSession


class EmbeddedBloodTests(unittest.TestCase):
    def test_compiled_images_and_native_animation_speed_match_audited_packs(self):
        app = App(DYNAMIC_BASE)
        images, _ = image_bank(app.payload(0x6666), app.payload(0x5555))
        props = property_bank(app.payload(0x2256), app.payload(0x2257))
        ids = object_mapping(app, App(ORIGINAL).objects()[0], active_only=True)
        for pack, data in assets().items():
            for handle, source in zip(data["handles"], data["images"]):
                im = images[handle].rgba()
                self.assertEqual(im.size, source.size)
                self.assertEqual(
                    im.getchannel("A").tobytes(), source.getchannel("A").tobytes()
                )
                self.assertTrue(
                    all(a == b for a, b in zip(im.getdata(), source.getdata()) if b[3])
                )
                self.assertEqual(
                    struct.unpack_from("<hh", images[handle].header, 28),
                    tuple(data["origin"]),
                )
            for oi in (105, 1032):
                body = props[ids[oi]]
                for i, handle in enumerate(data["handles"]):
                    at = animation_slot(body, data["animation"], 0, i)
                    self.assertEqual(struct.unpack_from("<H", body, at)[0], handle)
                at = animation_slot(body, data["animation"], 0, 0)
                self.assertEqual(body[at - 8 : at - 6], bytes([2 * data["fps"]] * 2))

    def test_three_packs_share_executable_and_stage_without_cross_slot_leakage(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            store = Store(
                root / "profile",
                runs=root / "runs",
                exporter=partial(export, dynamic=True),
            )
            with store.lock():
                for slot, pack in enumerate(("original", "kamilia3", "wannafest22"), 1):
                    draft = Draft()
                    draft.select_pack("blood_pack", pack)
                    store.create(slot, draft)
                    self.assertEqual(
                        digest(store.folder(slot) / "Boshy.exe"), DYNAMIC_SHA
                    )
                working = root / "working"
                working.mkdir()
                session = WorkingSession(working, store, DYNAMIC_SHA)
                for slot, pack in [
                    (2, "kamilia3"),
                    (3, "wannafest22"),
                    (1, "original"),
                    (2, "kamilia3"),
                ]:
                    session.stage(slot)
                    cfg = save(working / "SaveFile1.ini")
                    for key, value in settings(pack).items():
                        self.assertEqual(cfg.getint("FusionBloodV1", key), value)
                    session.commit()


if __name__ == "__main__":
    unittest.main()
