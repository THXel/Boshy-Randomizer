"""Start-character seed, profile isolation, catalogue and resume contracts."""

import tempfile, unittest
from pathlib import Path
from menu_host.draft import Draft
from menu_host.store import Store, RC4
from native_menu.model import Model
from gameplay.characters import CHOICES, ROSTER, selected, profile_text
from test_menu_host import fake_export


class CharacterTests(unittest.TestCase):
    def test_every_menu_choice_renews_seed_and_roundtrips(self):
        with tempfile.TemporaryDirectory() as tmp:
            m = Model(Store(tmp, runs=Path(tmp) / "runs"))
            m.go("loadout")
            for name in (*CHOICES[1:], "Auto"):
                before = m.draft.seed
                m.select("start_character")
                m.focus = CHOICES.index(name)
                m.key(13)
                self.assertEqual(m.page, "loadout")
                self.assertEqual(m.draft.options["start_character"], name)
                self.assertNotEqual(m.draft.seed, before)
                imported = Draft()
                imported.import_seed(m.draft.shared())
                self.assertEqual(imported.options, m.draft.options)

    def test_invalid_name_is_transactional_and_auto_preserves_original(self):
        d = Draft()
        original = d.shared()
        with self.assertRaises(ValueError):
            d.update(start_character="Missing character")
        self.assertEqual(d.shared(), original)
        self.assertEqual(selected(d.options), {"name": "Dark Boshy", "id": 84})
        d.update(start_character="Auto")
        self.assertIsNone(profile_text(selected(d.options)))
        for name, char_id in ROSTER.items():
            self.assertIn(
                "Character=" + str(char_id) + "\r\n",
                profile_text(selected({"start_character": name})),
            )

    def test_profile_is_run_local_and_resume_preserves_native_dresser_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = Store(tmp, runs=Path(tmp) / "runs", exporter=fake_export)
            d = Draft()
            d.update(start_character="Kirby")
            with store.lock():
                store.create(1, d)
                folder, plan, _ = store.resume(1)
                self.assertEqual(plan["start_character"], {"name": "Kirby", "id": 20})
                profile = folder / "onlineLicense.ini"
                self.assertTrue(profile.is_file())
                self.assertFalse((Path(tmp) / "onlineLicense.ini").exists())
                # A later native dresser change belongs to the run and is retained.
                changed = RC4(
                    b"BLOB",
                    profile_text(selected({"start_character": "Link"})).encode(
                        "latin1"
                    ),
                )
                profile.write_bytes(changed)
                store.resume(1)
                self.assertEqual(profile.read_bytes(), changed)
                profile.write_bytes(
                    RC4(b"BLOB", b"[License]\nCharacter=20\nCharacterName=Link\n")
                )
                with self.assertRaisesRegex(ValueError, "saved character"):
                    store.resume(1)
                profile.unlink()
                with self.assertRaises(ValueError):
                    store.resume(1)

    def test_original_native_game_reads_the_same_local_ini_and_character_key(self):
        from recover_boshy_routes import objects, payloads, original_sections
        from transition.events import commands

        self.assertIn(b"onlineLicense.ini\0", objects[83]["properties"])
        self.assertIn(b"BLOB\0", objects[83]["properties"])
        gameplay = next(p for p, f in payloads.items() if f == 3)
        rows = [row for section in original_sections(gameplay) for row in section]
        readers = [
            row
            for row in rows
            if b"License\0" in row
            and b"Character\0" in row
            and any(c[1:3] == (-3, -1) for c in commands(row))
        ]
        self.assertGreater(len(readers), 20)

    def test_profile_load_precedes_all_readers_without_changing_existing_events(self):
        from recover_boshy_routes import objects, payloads, original_sections
        from gameplay.character_profile import transform
        from transition.events import commands

        changed = []
        for payload, frame in payloads.items():
            before = original_sections(payload)
            after, audit = transform(frame, before, objects)
            if audit:
                changed.append(frame)
                self.assertEqual(after[0][4:], before[0])
                self.assertEqual(after[1:], before[1:])
                cs = commands(after[0][0])
                self.assertEqual(cs[0][1:3], (-3, -1))
                self.assertEqual(cs[1][1:3], (33, 123))
                self.assertIn(b"onlineLicense.ini\0", cs[1][-1])
                from transition.router import params
                from transition.events import expression, integer

                self.assertEqual(params(cs[1][-1])[-1][1], expression(integer(0)))
                self.assertEqual(cs[2][1:3], (33, 129))
                self.assertEqual(params(cs[2][-1])[0][1], expression(integer(1)))
                self.assertEqual(params(cs[2][-1])[1][1], expression(integer(0)))
                identity = commands(after[0][1])
                self.assertIn(b"Name\0", identity[1][-1])
                self.assertIn(b"Randomizer\0", identity[2][-1])
                self.assertIn(b"NeverDoneItBefore\0", identity[3][-1])
                self.assertIn(b"RandomizerStartCharacter\0", identity[4][-1])
                self.assertNotIn(b"Unlockables\0", after[0][1])
                self.assertEqual(len(identity), 5)
                enabled = commands(after[0][2])
                self.assertIn(b"RandomizerStartCharacter\0", enabled[1][-1])
                self.assertIn(b"OnlineLicenseCharacter\0", enabled[2][-1])
                fallback = commands(after[0][3])
                self.assertEqual(fallback[0][1:3], (-3, -1))
                self.assertIn(b"Character\0", fallback[1][-1])
                self.assertEqual(
                    params(fallback[1][-1], True)[1][1], expression(integer(0), 23)
                )
                self.assertEqual(
                    params(fallback[2][-1])[-1][1], expression(integer(12))
                )
                self.assertIn(b"CharacterName\0", fallback[3][-1])
                self.assertIn(b"Boshy\0", fallback[3][-1])
            else:
                self.assertEqual(after, before)
        self.assertIn(2, changed)
        self.assertIn(3, changed)
        self.assertIn(60, changed)
        self.assertGreaterEqual(len(changed), 48)


if __name__ == "__main__":
    unittest.main()
