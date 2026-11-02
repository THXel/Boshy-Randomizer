"""Room restarts must not undo window geometry chosen by the player."""

import unittest
from transition.events import commands
from native_menu import options_display
import recover_boshy_routes as source


def resizing(rows):
    return [
        row
        for section in rows
        for row in section
        if any(not c[0] and c[1] == 44 and c[2] in (83, 84) for c in commands(row))
    ]


class WindowResizeTests(unittest.TestCase):
    def test_room_entry_and_reset_never_reapply_saved_geometry(self):
        checked = 0
        for payload, number in source.payloads.items():
            if number == 20:
                continue
            before = source.original_sections(payload)
            after, _ = options_display.transform(
                number, before, source.objects, source.frames[number - 1]["instances"]
            )
            with self.subTest(frame=number):
                self.assertEqual(resizing(after), [])
            checked += 1
        self.assertGreaterEqual(checked, 60)

    def test_options_resize_only_after_explicit_edit_and_outside_fullscreen(self):
        payload = next(p for p, n in source.payloads.items() if n == 20)
        after, _ = options_display.transform(
            20,
            source.original_sections(payload),
            source.objects,
            source.frames[19]["instances"],
        )
        rows = resizing(after)
        self.assertEqual(len(rows), 10)
        for row in rows:
            conditions = b"".join(c[-1] for c in commands(row) if c[0])
            for key in (b"DisplayDirty\0", b"DisplayFullscreen\0"):
                self.assertIn(key, conditions)
        self.assertTrue(any(b"DisplayFullscreen\0" in row for row in after[-1]))


if __name__ == "__main__":
    unittest.main()
