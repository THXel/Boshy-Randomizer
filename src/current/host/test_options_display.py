"""Original room integration: preserve unrelated events and encrypted options."""

import tempfile
import unittest
from types import SimpleNamespace
from native_menu.controller import Controller
from pathlib import Path
from native_menu.display import Settings, prepare_options, from_options
from native_menu import options_display
from menu_host.store import RC4, save
from transition.events import commands
import recover_boshy_routes as source


class OptionsRoomTests(unittest.TestCase):
    def test_original_room_controls_and_audio_events_survive(self):
        payload = next(p for p, n in source.payloads.items() if n == 20)
        before = source.original_sections(payload)
        after, audit = options_display.transform(
            20, before, source.objects, source.frames[19]["instances"]
        )
        self.assertTrue(audit[0]["original_room"])
        self.assertEqual(len(before) + 1, len(after))
        self.assertEqual(len(after[-1]), 2)
        self.assertTrue(any(b"DiagnosticRequest" in row for row in after[-1]))
        for index, (old, new) in enumerate(zip(before, after)):
            if index in (19, 20, 21):
                continue
            if index == 0:
                self.assertEqual(len(new), len(old) + 1)
                new = new[1:]
            for old_row, new_row in zip(old, new):
                old_commands = commands(old_row)
                new_commands = commands(new_row)
                self.assertEqual(
                    [c[-1] for c in old_commands if c[0]],
                    [c[-1] for c in new_commands if c[0]],
                )
                if b"ScreenSize\0" in old_row:
                    old_commands = [c for c in old_commands if c[0] or c[1] != 44]
                self.assertEqual(old_commands, new_commands)
        self.assertTrue(any(b"16:9\0" in row for row in after[19]))
        self.assertTrue(any(b"DisplayConfigured\0" in row for row in after[19]))

    def test_options_write_in_progress_keeps_last_valid_preference(self):
        with tempfile.TemporaryDirectory() as t:
            folder = Path(t)
            controller = Controller.__new__(Controller)
            controller.name_future = None
            controller.folder = folder
            controller.window = SimpleNamespace(owned=lambda: False)
            controller.store = SimpleNamespace(active=False, root=folder)
            controller.model = SimpleNamespace(display=Settings())
            (folder / "options.ini").write_bytes(b"")
            controller.sync_display()
            self.assertEqual(controller.model.display, Settings())
            self.assertFalse(hasattr(controller, "display_signature"))
            with self.assertRaises(ValueError):
                prepare_options(folder, Settings("16:9", 720))
            self.assertEqual((folder / "options.ini").read_bytes(), b"")
            # Native writer completes its update; now merge display preferences.
            (folder / "options.ini").write_bytes(RC4(b"BLOB", b"[Options]\nMusicVolume=37\n"))
            prepare_options(folder, Settings("16:9", 720))
            self.assertEqual(save(folder / "options.ini").getint("Options", "MusicVolume"),37)
            controller.sync_display()
            self.assertEqual(controller.model.display, Settings("16:9", 720))

    def test_preferences_round_trip_preserves_original_options(self):
        with tempfile.TemporaryDirectory() as t:
            folder = Path(t)
            original = b"[Options]\nMusicVolume=37\nJumpKey=90\nOnlineLicenseCharacter=1\n[Other]\nValue=untouched\n"
            (folder / "options.ini").write_bytes(RC4(b"BLOB", original))
            for aspect in ("4:3", "16:9"):
                for height in options_display.HEIGHTS:
                    selected = Settings(aspect, height)
                    prepare_options(folder, selected)
                    self.assertEqual(from_options(folder), selected)
                    cfg = save(folder / "options.ini")
                    self.assertEqual(cfg.getint("Options", "MusicVolume"), 37)
                    self.assertEqual(cfg.getint("Options", "JumpKey"), 90)
                    self.assertEqual(cfg.get("Other", "Value"), "untouched")
                    index = options_display.HEIGHTS.index(height)
                    self.assertEqual(
                        selected.size[0],
                        options_display.WIDTHS[aspect == "16:9"][index],
                    )


if __name__ == "__main__":
    unittest.main()
