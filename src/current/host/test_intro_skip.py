"""Native intro-skip coverage, phase preservation and save/seed integrity."""

import io
import tempfile
import unittest
from pathlib import Path
import recover_boshy_routes as source
from transition.events import commands
from gameplay.intro_skip import transform, FRAMES, is_skip
from gameplay.settings import settings


class IntroSkipTests(unittest.TestCase):
    def test_source_census_guards_actions_and_exclusions(self):
        census = []
        for payload, frame in source.payloads.items():
            before = source.original_sections(payload)
            after, audit = transform(frame, before)
            census.extend(audit)
            mapped = {(a["section"], a["source_row"]): a for a in audit}
            for si, rows in enumerate(before):
                cursor = 0
                for ri, row in enumerate(rows):
                    a = mapped.get((si, ri))
                    if a is None:
                        self.assertEqual(row, after[si][cursor], (frame, si, ri))
                        cursor += 1
                        continue
                    old = commands(row)
                    manual, auto = (commands(r) for r in after[si][cursor : cursor + 2])
                    # Every original action remains byte-identical in original order.
                    for branch in (manual, auto):
                        self.assertEqual(
                            [c for c in old if not c[0]],
                            [c for c in branch if not c[0]],
                        )
                    self.assertEqual(manual[: row[2]], old[: row[2]])
                    self.assertIn(b"SkipIntro\0", manual[row[2]][-1])
                    for i, c in enumerate(old[: row[2]]):
                        if is_skip(c):
                            self.assertIn(b"SkipIntro\0", auto[i][-1])
                        else:
                            self.assertEqual(
                                c[-1][:14] + c[-1][16:],
                                auto[i][-1][:14] + auto[i][-1][16:],
                            )
                    cursor += 2
                self.assertEqual(cursor, len(after[si]))
            if frame in (31, 56):
                self.assertTrue(
                    any(
                        is_skip(c)
                        for rows in before
                        for row in rows
                        for c in commands(row)
                    )
                )
                self.assertEqual(before, after)
        self.assertEqual(len(census), 13)
        self.assertEqual({a["frame"] for a in census}, FRAMES)

    def test_seed_save_binding_and_older_schemas(self):
        from menu_host.draft import Draft
        from menu_host.store import Store, RC4
        from test_menu_host import fake_export

        d = Draft()
        before = d.seed
        d.update(skip_intro=True)
        self.assertNotEqual(before, d.seed)
        e = Draft()
        e.import_seed(d.shared())
        self.assertEqual(e.shared(), d.shared())
        self.assertEqual(settings(e.options["extras"])["SkipIntro"], 1)
        for schema in (1, 2, 3):
            with self.assertRaisesRegex(ValueError, "Intro skip"):
                settings(e.options["extras"], schema)
        with tempfile.TemporaryDirectory() as temp:
            s = Store(Path(temp) / "profile", Path(temp) / "runs", fake_export)
            with s.lock():
                s.create(1, e)
                folder, plan, c = s.resume(1)
                self.assertEqual(plan["gameplay_settings"]["SkipIntro"], 1)
                c["FusionGameplayV1"]["SkipIntro"] = "0"
                buf = io.StringIO()
                c.write(buf)
                (folder / "SaveFile1.ini").write_bytes(
                    RC4(b"BLOB", buf.getvalue().encode("latin1"))
                )
                with self.assertRaisesRegex(ValueError, "Changed gameplay"):
                    s.resume(1)
        e.update(skip_intro=False, quiet_pickups=False, no_mouse_ghost=False)
        for schema in (1, 2, 3):
            self.assertNotIn("SkipIntro", settings(e.options["extras"], schema))

    def test_menu_translation_and_selection(self):
        from menu_host.labels import LANGUAGES, ROWS, text
        from native_menu.model import RULES

        self.assertIn("skip_intro", RULES)
        for key in ("skip_intro", "skip_intro_hint"):
            self.assertEqual(len(ROWS[key]), len(LANGUAGES))
            self.assertEqual(len(set(ROWS[key])), len(LANGUAGES))
            for lang in LANGUAGES:
                self.assertTrue(text(key, lang))


if __name__ == "__main__":
    unittest.main()
