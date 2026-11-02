"""Pinned compiled God Mode build and native export integration checks."""

import configparser, json, struct, tempfile, unittest
from pathlib import Path
from export_native_run import export, BASE
from menu_host.draft import Draft
from menu_host.store import RC4, digest
from menu_host.runtime import verify_engine
from visuals.scenery_pack import App, object_mapping
from native_menu.builds import EXTRAS_SHA
from export_native_run import ORIGINAL
from visuals.fusion25 import property_bank, image_bank, animation_slot
from visuals.embedded_blood import assets
from gameplay.settings import GROUP, settings


class GameplayBuildTests(unittest.TestCase):
    def test_engine_art_audio_and_active_objects_preserved(self):
        verify_engine(BASE, EXTRAS_SHA)
        old = App(BASE.with_name("Boshy-blood-base.exe"))
        new = App(BASE)
        for kind in (0x6668, 0x5557):
            self.assertEqual(old.payload(kind), new.payload(kind), hex(kind))
        old_images, _ = image_bank(old.payload(0x6666), old.payload(0x5555))
        new_images, _ = image_bank(new.payload(0x6666), new.payload(0x5555))
        # This pinned extras build predates Undertale.
        added = {handle for name in ("kamilia3", "wannafest22") for handle in assets()[name]["handles"]}
        self.assertEqual(set(new_images) - set(old_images), added)
        self.assertTrue(set(old_images) <= set(new_images))
        changed = {
            n for n in old_images if old_images[n].bytes() != new_images[n].bytes()
        }
        self.assertEqual(
            changed, {5979, 5980, 5981, 6255}
        )  # Intro wordmark and X icon only.
        a = property_bank(old.payload(0x2256), old.payload(0x2257))
        b = property_bank(new.payload(0x2256), new.payload(0x2257))
        original = App(ORIGINAL).objects()[0]
        old_ids, new_ids = object_mapping(old, original), object_mapping(new, original)
        self.assertEqual(set(old_ids), set(new_ids))
        self.assertEqual(len(b), len(a))  # Existing native intro object is reused.
        heads = new.payload(0x2253)
        active = 0
        for oi in old_ids:
            kind = struct.unpack_from("<H", heads, new_ids[oi] * 16 + 2)[0]
            if kind == 2:
                if oi in (105, 1032):
                    # New player-only pack animations may extend the object;
                    # every pre-existing direction must remain byte-identical.
                    for animation in (0, 15):
                        for direction in range(32):
                            blobs = []
                            for body in (a[old_ids[oi]], b[new_ids[oi]]):
                                try:
                                    at = animation_slot(body, animation, direction, 0)
                                except ValueError:
                                    blobs.append(None)
                                else:
                                    count = struct.unpack_from("<H", body, at - 2)[0]
                                    blobs.append(body[at - 8 : at + count * 2])
                            self.assertEqual(*blobs)
                else:
                    self.assertEqual(a[old_ids[oi]], b[new_ids[oi]], oi)
                active += 1
        self.assertEqual(active, 1686)

    def test_native_exports_bind_god_setting_without_runtime_code_patch(self):
        hashes = []
        with tempfile.TemporaryDirectory() as temp:
            for enabled in (False, True):
                d = Draft()
                d.update(god_mode=enabled)
                folder = Path(temp) / str(enabled)
                export(d.shared(), folder)
                p = json.loads((folder / "plan.json").read_text())
                c = configparser.ConfigParser(interpolation=None)
                c.read_string(
                    RC4(b"BLOB", (folder / "SaveFile1.ini").read_bytes()).decode(
                        "latin1"
                    )
                )
                self.assertEqual(
                    p["gameplay_settings"],
                    settings(d.options["extras"], difficulty=d.options["difficulty"]),
                )
                self.assertEqual(
                    c.getint(GROUP, "HazardDeathLoops"), 0 if enabled else 1
                )
                self.assertEqual(c.get("FusionRouteV4", "Binding"), p["binding"])
                self.assertEqual(digest(folder / "Boshy.exe"), p["game_sha256"])
                hashes.append(p["game_sha256"])
            self.assertEqual(hashes[0], hashes[1])

    def test_start_character_export_includes_native_profile_and_display_option(self):
        from menu_host.store import Store, save

        with tempfile.TemporaryDirectory() as temp:
            store = Store(Path(temp) / "profile", runs=Path(temp) / "runs")
            draft = Draft()
            draft.update(start_character="Kirby")
            with store.lock():
                store.create(1, draft)
                folder, plan, _ = store.resume(1)
                profile = save(folder / "onlineLicense.ini")
                options = save(folder / "options.ini")
                self.assertEqual(plan["start_character"], {"name": "Kirby", "id": 20})
                self.assertEqual(profile.get("License", "Name"), "Randomizer")
                self.assertEqual(
                    profile.getint("License", "RandomizerStartCharacter"), 1
                )
                self.assertEqual(profile.getint("License", "Character"), 20)
                self.assertEqual(options.getint("Options", "OnlineLicenseCharacter"), 1)


if __name__ == "__main__":
    unittest.main()
