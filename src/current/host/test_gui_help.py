"""User-facing contracts for context help, personal presets and native F3."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock
from PIL import ImageDraw, Image
from native_menu.classic import ClassicModel, ClassicRenderer
from native_menu.help import explanation, wrapped, summary
from native_menu.help_labels import TEXT
from native_menu.presets import Presets
from menu_host.store import Store
from menu_host.draft import Draft


class HelpTests(unittest.TestCase):
    def test_all_translations_fit_help_region_and_input_sources_match(self):
        with tempfile.TemporaryDirectory() as t:
            m = ClassicModel(Store(Path(t) / "profile", runs=Path(t) / "runs"))
            r = ClassicRenderer(t)
            d = ImageDraw.Draw(Image.new("RGBA", (640, 480)))
            for i, lang in enumerate(("de", "en", "es", "ru", "ja")):
                m.language = lang
                for key, translations in TEXT.items():
                    self.assertEqual(len(translations), 5, key)
                    self.assertLessEqual(
                        len(wrapped(d, translations[i], r.fonts(lang)[11], 580, lang)),
                        4,
                        (lang, key),
                    )
                for page in (
                    "settings",
                    "loadout",
                    "route",
                    "gameplay",
                    "cosmetics",
                    "shots",
                    "tools",
                    "seed",
                    "presets",
                ):
                    m.go(page)
                    for index, row in enumerate(m.rows()):
                        m.focus = index
                        m.visible()
                        from native_menu.layout import row_rect

                        x, y, right, bottom = row_rect(page, index % 8)
                        keyboard = explanation(m, row)
                        seed = m.draft.shared()
                        m.key(1001, x + 10, y + 10)
                        self.assertEqual(explanation(m, m.rows()[m.focus]), keyboard)
                        self.assertEqual(m.draft.shared(), seed)
                        self.assertLessEqual(
                            len(wrapped(d, keyboard, r.fonts(lang)[11], 580, lang)),
                            4,
                            (page, row.key, lang),
                        )
                m.go("settings")
                r.render(m)

    def test_disabled_reasons_follow_mode_and_saved_run(self):
        with tempfile.TemporaryDirectory() as t:
            m = ClassicModel(Store(t, runs=Path(t) / "runs"))
            m.language = "en"
            for mode, expected in [
                ("normal", "Normal mode"),
                ("target", "Target mode"),
            ]:
                m.draft.set_mode(mode)
                m.go("loadout")
                row = next(r for r in m.rows() if r.key == "items")
                self.assertFalse(row.enabled)
                self.assertIn(expected, explanation(m, row))
            m.draft.set_mode("boss_rush")
            m.go("route")
            row = next(r for r in m.rows() if r.key == "level_count")
            self.assertIn("Rush mode", explanation(m, row))
            m.store.current = Mock(return_value={"saved": True})
            self.assertEqual(explanation(m, row), m.t("locked"))

    def test_user_presets_roundtrip_fresh_seed_and_preserve_presentation(self):
        with tempfile.TemporaryDirectory() as t:
            p = Presets(t)
            d = Draft()
            d.update(start_character="Luigi", god_mode=True)
            before = d.options.copy()
            ident = p.save("Mein Stream-Run 日本語", d.options)
            raw = json.loads(p.path.read_text())
            self.assertEqual(set(raw["presets"][0]), {"id", "name", "options"})
            for banned in (
                "music_pack",
                "blood_pack",
                "language",
                "resolution",
                "seed",
            ):
                self.assertNotIn(banned, raw["presets"][0])
            d.update(start_character="Boshy", god_mode=False, spider=True)
            d.music_pack = "wannafest22"
            d.blood_pack = "kamilia3"
            for _ in range(2):
                seed = d.seed
                p.apply(ident, d)
                self.assertNotEqual(seed, d.seed)
                self.assertEqual(d.options["start_character"], "Luigi")
                self.assertTrue(d.options["extras"]["god_mode"])
                self.assertTrue(d.options["extras"]["spider"])
                self.assertEqual(
                    (d.music_pack, d.blood_pack), ("wannafest22", "kamilia3")
                )
            data = p.path.read_bytes()
            with self.assertRaises(ValueError):
                p.save("MEIN STREAM-RUN 日本語", d.options)
            self.assertEqual(p.path.read_bytes(), data)
            p.delete(ident)
            self.assertEqual(p.read(), [])

    def test_invalid_or_corrupt_presets_never_replace_existing_file(self):
        with tempfile.TemporaryDirectory() as t:
            p = Presets(t)
            d = Draft()
            for name in ("", " " * 3, "X" * 41, "bad\nname"):
                with self.assertRaises(ValueError):
                    p.save(name, d.options)
            self.assertFalse(p.path.exists())
            p.path.write_text("{ broken")
            with self.assertRaises(ValueError):
                p.save("Safe name", d.options)
            self.assertEqual(p.path.read_text(), "{ broken")

    def test_preset_delete_needs_confirmation_and_saved_run_cannot_apply(self):
        with tempfile.TemporaryDirectory() as t:
            m = ClassicModel(Store(t, runs=Path(t) / "runs"))
            ident = m.presets.save("Training", m.draft.options)
            m.go("presets")
            m.select("user_preset:" + ident)
            self.assertEqual(m.page, "preset_details")
            m.store.current = Mock(return_value={"saved": True})
            seed = m.draft.shared()
            m.select("use_preset")
            self.assertEqual(m.draft.shared(), seed)
            m.select("delete_preset")
            m.key(27)
            self.assertEqual(len(m.presets.read()), 1)
            m.select("delete_preset")
            m.select("confirm_delete_preset")
            self.assertEqual(m.presets.read(), [])


class DresserTests(unittest.TestCase):
    def test_native_selection_keeps_original_unlock_guards_and_actions(self):
        from recover_boshy_routes import objects, payloads, original_sections, frames
        from gameplay.dresser import transform, catalogue, FOCUS
        from transition.events import commands
        from transition.boss_exits import split
        import struct

        payload = next(p for p, f in payloads.items() if f == 21)
        original = original_sections(payload)
        after, audit = transform(21, original, objects, frames[20]["instances"])
        self.assertEqual(after[:-1], original)
        original_picks = []
        for rows in original:
            for row in rows:
                cs, acts = split(row)
                if any(
                    b"CharacterName\0" in a
                    and struct.unpack_from("<hh", a, 2) == (33, 95)
                    for a in acts
                ):
                    original_picks.append((cs, acts))
        copies = [split(r) for r in after[-1]]
        checked = 0
        for cs, acts in original_picks:
            matches = [cc for cc, aa in copies if aa == acts]
            if not matches:
                continue  # Off-screen/secret custom buttons are untouched.
            for guard in cs:
                if struct.unpack_from("<hh", guard, 2) == (-6, -7):
                    continue
                self.assertTrue(
                    any(
                        any(c[:14] + c[16:] == guard[:14] + guard[16:] for c in cc)
                        for cc in matches
                    )
                )
            checked += 1
        self.assertEqual(checked, 35)
        self.assertTrue(
            all(
                b"Unlockables\0" not in c[-1]
                for r in after[-1]
                for c in commands(r)
                if not c[0]
            )
        )
        nodes = catalogue(objects, frames[20]["instances"])
        self.assertIn("Luigi", [n["name"] for n in nodes])
        self.assertIn("Kirby", [n["name"] for n in nodes])

    def test_focus_navigation_reaches_all_cards_without_unlock_mutations(self):
        from recover_boshy_routes import objects, frames
        from gameplay.dresser import catalogue, neighbours

        nodes = catalogue(objects, frames[20]["instances"]) + [dict(x=320, y=408)]
        index = 0
        seen = set()
        for _ in nodes:
            seen.add(index)
            index = neighbours(nodes, index, 39)
        self.assertEqual(seen, set(range(len(nodes))))
        for i in seen:
            self.assertEqual(neighbours(nodes, neighbours(nodes, i, 39), 37), i)
            self.assertNotEqual(neighbours(nodes, i, 40), i)
