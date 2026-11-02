"""Pickup event census, preserved reward actions, per-run rules and translations."""

import io, tempfile, unittest
from pathlib import Path
from collections import Counter
import recover_boshy_routes as source
from gameplay.pickups import transform
from transition.events import commands
from transition.router import params


class PickupTests(unittest.TestCase):
    def test_census_and_preserved_actions(self):
        counts = Counter()
        frames = set()
        for p, f in source.payloads.items():
            before = source.original_sections(p)
            after, audit = transform(f, before, source.objects)
            counts.update((a["rule"], a.get("old")) for a in audit)
            frames.update(a["frame"] for a in audit if a["rule"] == "quiet_pickups")
            edits = {}
            for a in audit:
                edits.setdefault((a["section"], a["source_row"]), []).append(a)
            for si, rows in enumerate(before):
                cursor = 0
                for ri, row in enumerate(rows):
                    changes = edits.get((si, ri), [])
                    old = commands(row)
                    new = commands(after[si][cursor])
                    if not changes:
                        self.assertEqual(row, after[si][cursor])
                    else:
                        self.assertEqual(
                            [c[-1] for c in old if not c[0]],
                            [c[-1] for c in new if not c[0]],
                        )
                        for ci, c in enumerate(old[: row[2]]):
                            if any(
                                a["rule"] == "fast_chests" and a["command"] == ci
                                for a in changes
                            ):
                                self.assertEqual(
                                    params(c[-1], True)[0], params(new[ci][-1], True)[0]
                                )
                                self.assertEqual(
                                    params(c[-1], True)[1][1][4:6],
                                    params(new[ci][-1], True)[1][1][4:6],
                                )
                                self.assertIn(b"FastChests\0", new[ci][-1])
                            else:
                                self.assertEqual(c, new[ci])
                    quiet = [a for a in changes if a["rule"] == "quiet_pickups"]
                    if quiet:
                        muted = commands(after[si][cursor + 1])
                        cursor += 1
                        self.assertEqual(
                            [c[-1] for c in old if not c[0] and c[1:3] != (37, 82)],
                            [c[-1] for c in muted if not c[0]],
                        )
                        self.assertIn(b"QuietPickups\0", muted[row[2]][-1])
                    cursor += 1
                self.assertEqual(cursor, len(after[si]))
        self.assertEqual(
            counts,
            {
                ("fast_chests", 200): 98,
                ("fast_chests", 250): 269,
                ("fast_chests", 315): 57,
                ("fast_chests", 330): 49,
                ("fast_chests", 360): 49,
                ("quiet_pickups", None): 4,
            },
        )
        self.assertEqual(frames, {3, 11, 15})

    def test_rule_binding_and_legacy(self):
        from menu_host.draft import Draft
        from menu_host.store import Store, RC4
        from gameplay.settings import settings
        from test_menu_host import fake_export

        for key, ini in [
            ("fast_chests", "FastChests"),
            ("quiet_pickups", "QuietPickups"),
        ]:
            d = Draft()
            d.update(quiet_pickups=False)
            old = d.seed
            d.update(**{key: True})
            self.assertNotEqual(old, d.seed)
            e = Draft()
            e.import_seed(d.shared())
            self.assertEqual(d.shared(), e.shared())
            for schema in (1, 2, 3, 4):
                with self.assertRaisesRegex(ValueError, "Pickup options"):
                    settings(e.options["extras"], schema)
            with tempfile.TemporaryDirectory() as folder:
                s = Store(Path(folder) / "profile", Path(folder) / "runs", fake_export)
                with s.lock():
                    s.create(1, d)
                    path, p, c = s.resume(1)
                    self.assertEqual(p["gameplay_settings"][ini], 1)
                    c["FusionGameplayV1"][ini] = "0"
                    buf = io.StringIO()
                    c.write(buf)
                    (path / "SaveFile1.ini").write_bytes(
                        RC4(b"BLOB", buf.getvalue().encode("latin1"))
                    )
                    with self.assertRaisesRegex(ValueError, "Changed gameplay"):
                        s.resume(1)
            ex = d.options["extras"]
            ex[key] = 1
            with self.assertRaisesRegex(ValueError, "boolean"):
                settings(ex)

    def test_translations(self):
        from menu_host.labels import ROWS, LANGUAGES
        from native_menu.model import RULES

        for key in ("fast_chests", "quiet_pickups"):
            self.assertIn(key, RULES)
            for k in (key, key + "_hint"):
                self.assertEqual(len(ROWS[k]), len(LANGUAGES))
                self.assertEqual(len(set(ROWS[k])), 5)


if __name__ == "__main__":
    unittest.main()
