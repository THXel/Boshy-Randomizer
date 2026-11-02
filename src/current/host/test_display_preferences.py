"""Display options must preserve seeds, language and complete game geometry."""

import tempfile
import unittest
from pathlib import Path
from native_menu.display import Settings, load
from native_menu.classic import ClassicModel
from menu_host.store import Store


class DisplayTests(unittest.TestCase):
    def test_native_menu_selection_persists_without_modifying_seed_or_language(self):
        with tempfile.TemporaryDirectory() as t:
            store = Store(Path(t) / "profile", runs=Path(t) / "runs")
            m = ClassicModel(store)
            m.language = "de"
            m.go("display")
            seed = m.draft.shared()
            self.assertEqual(m.display, Settings("4:3", 480))
            m.select("aspect")
            m.select("resolution")
            self.assertEqual(m.display, Settings("16:9", 720))
            self.assertEqual(m.action, "display")
            self.assertEqual(m.draft.shared(), seed)
            from native_menu.preferences import save_preferences

            save_preferences(store.root, language="en")
            reloaded = ClassicModel(store)
            self.assertEqual(reloaded.display, Settings("16:9", 720))
            self.assertEqual(reloaded.language, "en")
            reloaded.go("display")
            reloaded.select("aspect")
            self.assertEqual(ClassicModel(store).language, "en")

    def test_up_to_4k_fits_one_monitor_without_cropping_or_changing_aspect(self):
        self.assertEqual(Settings("16:9", 2160).size, (3840, 2160))
        self.assertEqual(Settings("4:3", 2160).size, (2880, 2160))
        for aspect in ("4:3", "16:9"):
            for screen in [
                (800, 600),
                (1280, 720),
                (1920, 1080),
                (2560, 1440),
                (3840, 2160),
            ]:
                w, h = Settings(aspect, 2160).fit(screen)
                self.assertLessEqual(w, screen[0])
                self.assertLessEqual(h, screen[1])
                n, d = map(int, aspect.split(":"))
                self.assertLessEqual(abs(w - h * n / d), 1)

    def test_death_counter_default_matches_original_display_and_respects_saved_off(
        self,
    ):
        from native_menu.display import prepare_options
        from menu_host.store import save as read_save, RC4

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            prepare_options(root, Settings())
            self.assertEqual(
                read_save(root / "options.ini").getint("Options", "ShowDeaths"), 1
            )
            (root / "options.ini").write_bytes(
                RC4(b"BLOB", b"[Options]\r\nshowdeaths=0\r\n")
            )
            prepare_options(root, Settings())
            self.assertEqual(
                read_save(root / "options.ini").getint("Options", "ShowDeaths"), 0
            )

    def test_music_restart_default_off_and_explicit_choice_preserved(self):
        from native_menu.display import prepare_options
        from menu_host.store import save as read_save, RC4
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            prepare_options(root, Settings())
            self.assertEqual(read_save(root/'options.ini').getint('Options','MusicRestart'), 0)
            (root/'options.ini').write_bytes(RC4(b'BLOB', b'[Options]\nmusicrestart=1\nmusicvolume=37\n'))
            prepare_options(root, Settings())
            cfg = read_save(root/'options.ini')
            self.assertEqual(cfg.getint('Options','MusicRestart'), 1)
            self.assertEqual(cfg.getint('Options','MusicVolume'), 37)

    def test_fullscreen_keeps_aspect_and_windowed_choice(self):
        from native_menu.display import prepare_options, from_options

        for aspect, expected in (("4:3", (1440, 1080)), ("16:9", (1920, 1080))):
            settings = Settings(aspect, 480, True)
            self.assertEqual(settings.fit((1920, 1080)), expected)
            self.assertTrue(settings.changed("height", 1).fullscreen)
            self.assertFalse(settings.changed("fullscreen", 1).fullscreen)
            with tempfile.TemporaryDirectory() as tmp:
                prepare_options(Path(tmp), settings)
                self.assertEqual(from_options(Path(tmp)), settings)

    def test_native_lowercase_keys_do_not_restore_old_aspect(self):
        from native_menu.display import prepare_options, from_options
        from menu_host.store import RC4

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "options.ini").write_bytes(
                RC4(
                    b"BLOB",
                    b"[Options]\n displayaspect=0\n displayfullscreen=1\n musicvolume=37\n",
                )
            )
            expected = Settings("16:9", 720, True)
            prepare_options(root, expected)
            self.assertEqual(from_options(root), expected)
            raw = (
                RC4(b"BLOB", (root / "options.ini").read_bytes())
                .decode("latin1")
                .lower()
            )
            self.assertEqual(raw.count("displayaspect"), 1)
            self.assertIn("musicvolume = 37", raw)

    def test_invalid_saved_preferences_fall_back_to_original(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "native-preferences.json"
            for data in [
                "[]",
                '{"display":null}',
                '{"display":{"aspect":"21:9","height":2160}}',
                '{"display":{"aspect":"16:9","height":true}}',
            ]:
                p.write_text(data)
                self.assertEqual(load(t), Settings())


if __name__ == "__main__":
    unittest.main()
