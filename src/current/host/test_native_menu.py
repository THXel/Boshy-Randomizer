"""Native event isolation, menu completeness, seeds and mailbox commits."""

import json
import tempfile, unittest
from pathlib import Path
from unittest.mock import Mock
from native_menu.model import Model, LANGUAGES, RULES
from native_menu.transport import Mailbox, write
from native_menu.render import Renderer
from native_menu.events import transform
from menu_host.store import Store
from transition.events import commands
import recover_boshy_routes as source


class NativeMenuTests(unittest.TestCase):
    def model(self, folder):
        return Model(Store(folder, runs=Path(folder) / "runs"))

    def test_all_choices_are_available_and_translated(self):
        with tempfile.TemporaryDirectory() as d:
            m = self.model(d)
            from menu_host.draft import LEVELS, BOSSES
            from transition.router import STAGES

            self.assertEqual(
                set(STAGES) - set(LEVELS) - {boss[2] for boss in BOSSES.values()},
                {"boss_solgryn.ini"},
            )
            for lang in LANGUAGES:
                m.language = lang
                for page, count in [
                    ("levels", 21),
                    ("bosses", 22),
                    ("gameplay", 10),
                    ("loadout", 4),
                    ("tools", 4),
                    ("cosmetics", 8),
                    ("shots", 7),
                ]:
                    m.go(page)
                    self.assertEqual(len(m.rows()), count)
                    self.assertTrue(all(r.label for r in m.rows()))
                m.go("bosses")
                self.assertTrue(any("Gravitron" in r.label for r in m.rows()))

    def test_edits_renew_seed_and_navigation_does_not(self):
        with tempfile.TemporaryDirectory() as d:
            m = self.model(d)
            seed = m.draft.seed
            m.go("gameplay")
            self.assertEqual(seed, m.draft.seed)
            for key in RULES:
                old = m.draft.seed
                previous = m.draft.options["extras"][key]
                m.select(key)
                self.assertNotEqual(old, m.draft.seed)
                self.assertIs(m.draft.options["extras"][key], not previous)
            m.go("levels")
            before = m.draft.seed
            m.select(m.rows()[0].key)
            self.assertNotEqual(before, m.draft.seed)
            m.go("settings")
            before = m.draft.seed
            m.select("language")
            self.assertEqual(before, m.draft.seed)

    def test_native_input_committed_once_and_invalid_sequence_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            m = self.model(d)
            renderer = Mock(art_generation=1)
            mail = Mailbox(Path(d), renderer, m)
            write(Path(d) / "native-input.ini", dict(Sequence=1, Key=40))
            self.assertTrue(mail.poll())
            self.assertEqual(m.focus, 1)
            self.assertFalse(mail.poll())
            write(Path(d) / "native-input.ini", dict(Sequence=3, Key=40))
            with self.assertRaises(ValueError):
                mail.poll()

    def test_source_only_guards_input_and_adds_separate_title_events(self):
        payload = next(p for p, n in source.payloads.items() if n == 2)
        original = source.original_sections(payload)
        changed, audit = transform(original)
        self.assertGreater(audit["guarded_input_rows"], 0)
        for oldsec, newsec in zip(original, changed):
            for old, new in zip(oldsec, newsec):
                a = commands(old)
                b = commands(new)
                self.assertEqual([v for v in a if not v[0]], [v for v in b if not v[0]])
                if any(c and k in (-6, -7) for c, k, code, oi, raw in a):
                    self.assertEqual(sum(v[0] for v in b), sum(v[0] for v in a) + 1)
                else:
                    self.assertEqual(old, new)
        self.assertFalse(
            any(k == -2 for row in changed[-1] for c, k, code, oi, raw in commands(row))
        )

    def test_saved_run_controls_are_immutable(self):
        with tempfile.TemporaryDirectory() as d:
            m = self.model(d)
            m.store.current = Mock(return_value={"run": "owned"})
            m.go("gameplay")
            seed, options = m.draft.seed, json.loads(json.dumps(m.draft.options))
            m.key(13)
            m.key(116)
            self.assertEqual(m.draft.seed, seed)
            self.assertEqual(m.draft.options, options)
            self.assertTrue(all(not row.enabled for row in m.rows()))

    def test_refresh_and_mouse_event_use_native_parameter_types(self):
        payload = next(p for p, n in source.payloads.items() if n == 2)
        changed, _ = transform(source.original_sections(payload))
        extra = changed[-1]
        self.assertTrue(all(row[2] > 0 for row in extra))
        refresh = commands(extra[1])
        self.assertEqual(refresh[0][1:4], (-1, -1, 0))
        click = next(
            c for row in extra for c in commands(row) if c[0] and c[1:3] == (-6, -5)
        )
        self.assertEqual(click[-1][16:20], bytes.fromhex("0a002000"))

    def test_panels_render_all_languages(self):
        with tempfile.TemporaryDirectory() as d:
            m = self.model(d)
            r = Renderer(d)
            for lang in LANGUAGES:
                m.language = lang
                for page in (
                    "home",
                    "settings",
                    "route",
                    "levels",
                    "bosses",
                    "gameplay",
                    "cosmetics",
                    "seed",
                ):
                    m.go(page)
                    self.assertEqual(r.render(m).size, (640, 480))
            m.busy = True
            r.render(m)

    def test_entry_return_does_not_change_selected_save_slot(self):
        with tempfile.TemporaryDirectory() as d:
            m = self.model(d)
            m.slot = 2
            mail = Mailbox(Path(d), Mock(art_generation=1), m)
            write(Path(d) / "native-input.ini", dict(Sequence=1, Key=13))
            mail.discard_entry()
            self.assertEqual(m.slot, 2)
            self.assertEqual(mail.sequence, 1)
            self.assertFalse(mail.poll())
            write(Path(d) / "native-input.ini", dict(Sequence=2, Key=40))
            self.assertTrue(mail.poll())
            self.assertEqual(m.focus, 1)

    def test_native_cast_reproduces_the_run_seed(self):
        from native_menu.art import choose

        first = choose("12345678")
        self.assertEqual(first, choose("12345678"))
        self.assertNotEqual(first, choose("ABCD9876"))

    def test_horizontal_arrows_never_start_or_delete_a_run(self):
        with tempfile.TemporaryDirectory() as d:
            m = self.model(d)
            for focus in (3, 4, 5, 7):
                m.focus = focus
                for key in (37, 39):
                    m.key(key)
                    self.assertIsNone(m.action)
            m.focus = 3
            m.key(13)
            self.assertEqual(m.action, "new")
