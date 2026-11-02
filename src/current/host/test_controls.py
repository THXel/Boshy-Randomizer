"""Independent census and unchanged-event checks for native input options."""

import unittest
from collections import Counter
import recover_boshy_routes as source
from transition.events import commands, expression, integer
from transition.router import params
from gameplay.controls import transform
from gameplay.settings import settings


class ControlTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = []
        for payload, frame in source.payloads.items():
            before = source.original_sections(payload)
            after, audit = transform(
                frame, before, source.objects, source.frames[frame - 1]["instances"]
            )
            cls.cases.append((frame, before, after, audit))

    def test_census_and_no_unrelated_changes(self):
        counts = Counter(a["rule"] for _, _, _, audit in self.cases for a in audit)
        self.assertEqual(counts, {"autofire": 96, "no_mouse_ghost": 48})
        for frame, before, after, audit in self.cases:
            edits = {(a["section"], a["row"], a["command"]): a for a in audit}
            for si, rows in enumerate(before):
                self.assertEqual(
                    len(after[si]) - len(rows),
                    sum(a.get("added", False) for a in audit if a["section"] == si),
                )
                for ri, row in enumerate(rows):
                    old, new = commands(row), commands(after[si][ri])
                    self.assertEqual(len(old), len(new))
                    for ci, (a, b) in enumerate(zip(old, new)):
                        edit = edits.get((si, ri, ci))
                        if not edit:
                            self.assertEqual(a, b, (frame, si, ri, ci))
                        else:
                            head = 16 if a[0] else 14
                            self.assertEqual(a[-1][2:head], b[-1][2:head])
                            self.assertEqual(
                                params(a[-1], a[0])[0], params(b[-1], b[0])[0]
                            )
                            self.assertIn(edit["ini"].to_bytes(2, "little"), b[-1])
                            self.assertIn(integer(0 if a[0] else 1), b[-1])

    def test_autofire_uses_sdk_less_or_equal_comparison(self):
        import struct

        # Cncf.h CMPOPE_LOWEQU=2. >= would accidentally enable normal mode by default.
        for frame, before, after, audit in self.cases:
            for a in audit:
                if a["rule"] == "autofire":
                    c = commands(after[a["section"]][a["row"]])[a["command"]]
                    p = params(c[-1], True)[1][1]
                    self.assertEqual(struct.unpack_from("<H", p, 4)[0], 2)
        for difficulty in range(4):
            self.assertEqual(difficulty <= 0, difficulty == 0)
            self.assertTrue(difficulty <= 3)

    def test_census_from_input_and_mouse_objects(self):
        for frame, before, after, audit in self.cases:
            rows = {(a["section"], a["row"]) for a in audit}
            for si, section in enumerate(before):
                for ri, row in enumerate(section):
                    cs = commands(row)
                    # All held-fire rows with an original Ez difficulty gate are patched.
                    if (
                        any(c[0] and c[1:3] == (-7, -6) for c in cs)
                        and any(
                            not c[0]
                            and c[1:3] == (2, 29)
                            and source.objects[c[3]]["name"] == "Player"
                            for c in cs
                        )
                        and any(c[0] and c[1:3] == (-1, -8) for c in cs)
                    ):
                        self.assertIn((si, ri), rows)
                    for c in cs:
                        if (
                            not c[0]
                            and c[1:3] == (2, 32)
                            and source.objects[c[3]]["name"] == "mouse kill"
                        ):
                            self.assertTrue(any(a.get("oi") == c[3] for a in audit))

    def test_only_mouse_object_destroyed_with_explicit_enabled_setting(self):
        for frame, before, after, audit in self.cases:
            for a in audit:
                if a["rule"] != "no_mouse_ghost":
                    continue
                cs = commands(after[a["section"]][a["row"]])
                self.assertEqual(len(cs), 2)
                self.assertEqual(cs[1][1:4], (2, 24, a["oi"]))
                self.assertEqual(source.objects[a["oi"]]["name"], "mouse kill")
                self.assertIn(b"MouseGhostDisabled", cs[0][-1])
                self.assertEqual(
                    params(cs[0][-1], True)[1][1], expression(integer(1), 23)
                )
                self.assertIn(integer(0), params(cs[0][-1], True)[0][1])
                self.assertEqual(
                    before[a["section"]][a["source_row"]],
                    after[a["section"]][a["source_row"]],
                )

    def test_settings_strict_and_legacy_compatible(self):
        ex = dict(god_mode=False, autofire=False, no_mouse_ghost=False, one_hp=False)
        self.assertEqual(
            settings(ex),
            dict(
                Schema=5,
                FastChests=0,
                QuietPickups=0,
                SkipIntro=0,
                HazardDeathLoops=1,
                AutoFireMaxDifficulty=0,
                MouseGhostDisabled=0,
                OneHit=0,
                OneHitSonicFloor=35,
            ),
        )
        self.assertEqual(settings(ex, 1), dict(Schema=1, HazardDeathLoops=1))
        self.assertEqual(settings(dict(ex, autofire=True))["AutoFireMaxDifficulty"], 3)
        self.assertEqual(
            settings(dict(ex, no_mouse_ghost=True))["MouseGhostDisabled"], 1
        )
        for key in ex:
            with self.assertRaises(ValueError):
                settings(dict(ex, **{key: 1}))
        for key in ("autofire", "no_mouse_ghost"):
            with self.assertRaises(ValueError):
                settings(dict(ex, **{key: True}), 1)
        with self.assertRaises(ValueError):
            settings(ex, 6)


class ControlMenuTests(unittest.TestCase):
    def test_controls_change_seed_roundtrip_and_bind_saved_rules(self):
        from menu_host.draft import Draft
        from menu_host.store import Store, RC4
        from test_menu_host import fake_export
        import tempfile, io
        from pathlib import Path

        for key in ("autofire", "no_mouse_ghost"):
            with self.subTest(key=key), tempfile.TemporaryDirectory() as temp:
                d = Draft()
                old = d.seed
                value = not d.options["extras"][key]
                d.update(**{key: value})
                self.assertNotEqual(old, d.seed)
                code = d.shared()
                e = Draft()
                e.import_seed(code)
                self.assertEqual(e.shared(), code)
                e.update(**{key: value})
                self.assertEqual(e.shared(), code)
                s = Store(Path(temp) / "profile", Path(temp) / "runs", fake_export)
                with s.lock():
                    s.create(1, e)
                    folder, p, c = s.resume(1)
                    self.assertEqual(
                        p["gameplay_settings"],
                        settings(
                            e.options["extras"], difficulty=e.options["difficulty"]
                        ),
                    )
                    name = (
                        "AutoFireMaxDifficulty"
                        if key == "autofire"
                        else "MouseGhostDisabled"
                    )
                    c["FusionGameplayV1"][name] = "999"
                    buf = io.StringIO()
                    c.write(buf)
                    (folder / "SaveFile1.ini").write_bytes(
                        RC4(b"BLOB", buf.getvalue().encode("latin1"))
                    )
                    with self.assertRaisesRegex(ValueError, "Changed gameplay"):
                        s.resume(1)


if __name__ == "__main__":
    unittest.main()
