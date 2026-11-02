"""Native slot integrity, transactions and canonical settings regression tests."""

import configparser, hashlib, io, json, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
from menu_host.draft import Draft, validate, LEVELS, BOSSES
from menu_host.store import Store, RC4, digest
from export_route_probe import plan, save_text
from run_settings import decode
from visuals.actor_palettes import settings
from transition.router import STAGES, GROUP
from gameplay.characters import selected as selected_character, profile_text
from menu_host.labels import LANGUAGES, ROWS
from gameplay.settings import settings as gameplay_settings, GROUP as GAMEPLAY_GROUP


def fake_export(shared, folder, pack, source, music):
    folder.mkdir()
    raw = b"isolated test executable"
    h = hashlib.sha256(raw).hexdigest()
    p = plan(shared, h, h)
    p.update(
        gameplay_settings=gameplay_settings(
            p["options"]["extras"], difficulty=p["options"]["difficulty"]
        ),
        start_character=selected_character(p["options"]),
        blood_pack=pack,
        music_pack=music,
        blood_settings=dict(Schema=1, Animation=0, LifeTicks=0),
        actor_settings=settings(p["seed"], False),
    )
    p.pop("binding")
    p["binding"] = hashlib.sha256(
        json.dumps(p, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    c = configparser.ConfigParser(interpolation=None)
    c.read_string(save_text(p))
    c.read_dict(
        {
            "FusionBloodV1": p["blood_settings"],
            "FusionActorsV1": p["actor_settings"],
            GAMEPLAY_GROUP: p["gameplay_settings"],
        }
    )
    buf = io.StringIO()
    c.write(buf)
    (folder / "SaveFile1.ini").write_bytes(
        RC4(b"BLOB", buf.getvalue().encode("latin1"))
    )
    if p["start_character"] is not None:
        (folder / "onlineLicense.ini").write_bytes(
            RC4(b"BLOB", profile_text(p["start_character"]).encode("latin1"))
        )
    (folder / "Boshy.exe").write_bytes(raw)
    (folder / "plan.json").write_text(json.dumps(p))


class DraftTests(unittest.TestCase):
    def test_each_settings_edit_renews_once_and_noop_keeps_seed(self):
        d = Draft()
        old = d.seed
        with patch.object(d, "consume_seed", wraps=d.consume_seed) as renew:
            d.update(music=True, sprite_scenery=True)
            self.assertEqual(renew.call_count, 1)
            self.assertNotEqual(old, d.seed)
            seed = d.seed
            d.update(music=True)
            self.assertEqual(seed, d.seed)
        d.select_pack("blood_pack", "wannafest22")
        self.assertNotEqual(seed, d.seed)
        seed = d.seed
        d.select_pack("blood_pack", "wannafest22")
        self.assertEqual(seed, d.seed)

    def test_seed_roundtrip_preserves_route_and_settings(self):
        d = Draft()
        d.update(level_count=4, route_boss_count=2, music=True)
        e = Draft()
        e.import_seed(d.shared())
        self.assertEqual(d.shared(), e.shared())
        self.assertEqual(d.options, e.options)
        old = e.seed
        e.update(difficulty=(e.options["difficulty"] + 1) % 4)
        self.assertNotEqual(old, e.seed)

    def test_unsupported_rules_rejected_without_mutating_draft(self):
        d = Draft()
        code = d.shared()
        before = d.options.copy()
        with self.assertRaises(ValueError):
            d.update(mode="unmigrated")
        self.assertEqual(d.shared(), code)
        opts = json.loads(json.dumps(d.options))
        opts["extras"]["shot_mode"] = "unmigrated"
        with self.assertRaises(ValueError):
            validate(opts)
        opts = json.loads(json.dumps(d.options))
        opts["mode"] = "unmigrated"
        with self.assertRaises(ValueError):
            validate(opts)

    def test_god_mode_renews_seed_and_roundtrips(self):
        d = Draft()
        old = d.shared()
        d.update(god_mode=True)
        self.assertNotEqual(old, d.shared())
        e = Draft()
        e.import_seed(d.shared())
        self.assertTrue(e.options["extras"]["god_mode"])
        self.assertEqual(d.shared(), e.shared())
        same = e.shared()
        e.update(god_mode=True)
        self.assertEqual(same, e.shared())

    def test_all_route_points_and_translations_present(self):
        self.assertEqual(
            set(STAGES),
            set(LEVELS) | {v[2] for v in BOSSES.values()} | {"boss_solgryn.ini"},
        )
        self.assertEqual(len(LEVELS) + len(BOSSES), 43)
        for key, row in ROWS.items():
            self.assertEqual(len(row), len(LANGUAGES))
            self.assertTrue(all(row), key)


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.store = Store(self.root / "profile", self.root / "runs", fake_export)
        self.guard = self.store.lock()
        self.guard.__enter__()
        self.draft = Draft()

    def tearDown(self):
        self.guard.__exit__(None, None, None)
        self.temp.cleanup()

    def create(self, slot=1):
        self.store.create(slot, self.draft)
        return self.store.folder(slot)

    def test_create_resume_and_second_slot_are_independent(self):
        first = self.create()
        before = (first / "SaveFile1.ini").read_bytes()
        self.store.resume(1)
        self.assertEqual(before, (first / "SaveFile1.ini").read_bytes())
        self.draft.consume_seed()
        second = self.create(2)
        self.assertNotEqual(first, second)
        self.assertNotEqual(
            self.store.summary(1)["seed"], self.store.summary(2)["seed"]
        )
        self.assertEqual(before, (first / "SaveFile1.ini").read_bytes())

    def test_occupied_slot_cannot_be_overwritten(self):
        folder = self.create()
        old = self.store.pointer(1).read_bytes()
        with self.assertRaises(FileExistsError):
            self.store.create(1, self.draft)
        self.assertEqual(old, self.store.pointer(1).read_bytes())
        self.assertTrue(folder.is_dir())

    def test_export_failure_leaves_no_committed_slot(self):
        self.store.exporter = lambda *a: (_ for _ in ()).throw(
            RuntimeError("export failed")
        )
        with self.assertRaises(RuntimeError):
            self.store.create(1, self.draft)
        self.assertIsNone(self.store.current(1))

    def test_archive_only_clears_selected_pointer_and_keeps_undo(self):
        first = self.create()
        second = self.create(2)
        before = (second / "SaveFile1.ini").read_bytes()
        self.store.archive(1)
        self.assertIsNone(self.store.current(1))
        self.assertTrue(first.is_dir())
        self.assertEqual(before, (second / "SaveFile1.ini").read_bytes())
        self.assertEqual(len(list((self.store.root / "deleted").glob("*.json"))), 1)

    def test_concurrent_host_and_active_run_block_mutations(self):
        other = Store(self.store.root, self.store.runs, fake_export)
        with self.assertRaises(BlockingIOError):
            with other.lock():
                pass
        self.create()
        self.store.active = 1
        for operation in [
            lambda: self.store.archive(1),
            lambda: self.store.create(2, self.draft),
            lambda: self.store.resume(1),
        ]:
            with self.assertRaises(RuntimeError):
                operation()

    def test_foreign_save_changed_route_and_tampered_executable_rejected(self):
        folder = self.create()
        self.draft.consume_seed()
        other = self.create(2)
        save = folder / "SaveFile1.ini"
        original = save.read_bytes()
        save.write_bytes((other / "SaveFile1.ini").read_bytes())
        with self.assertRaisesRegex(ValueError, "another run"):
            self.store.resume(1)
        save.write_bytes(original)
        c = configparser.ConfigParser()
        c.read_string(RC4(b"BLOB", original).decode("latin1"))
        key = next(k for k in c[GROUP] if k.startswith("nextid"))
        c[GROUP][key] = "999"
        buf = io.StringIO()
        c.write(buf)
        save.write_bytes(RC4(b"BLOB", buf.getvalue().encode("latin1")))
        with self.assertRaisesRegex(ValueError, "route edge"):
            self.store.resume(1)
        save.write_bytes(original)
        (folder / "Boshy.exe").write_bytes(b"bad")
        with self.assertRaisesRegex(ValueError, "integrity"):
            self.store.resume(1)

    def test_god_mode_save_cannot_silently_change_rules(self):
        self.draft.update(god_mode=True)
        folder = self.create()
        _, p, c = self.store.resume(1)
        self.assertEqual(
            p["gameplay_settings"],
            gameplay_settings(
                self.draft.options["extras"],
                difficulty=self.draft.options["difficulty"],
            ),
        )
        c[GAMEPLAY_GROUP]["HazardDeathLoops"] = "1"
        buf = io.StringIO()
        c.write(buf)
        (folder / "SaveFile1.ini").write_bytes(
            RC4(b"BLOB", buf.getvalue().encode("latin1"))
        )
        with self.assertRaisesRegex(ValueError, "Changed gameplay"):
            self.store.resume(1)

    def test_path_escape_and_symlink_rejected(self):
        self.create()
        meta = self.store.current(1)
        meta["run"] = "../escape"
        self.store.pointer(1).write_text(json.dumps(meta))
        with self.assertRaises(ValueError):
            self.store.current(1)
        self.store.pointer(1).unlink()
        self.store.pointer(1).symlink_to(self.root / "outside")
        with self.assertRaises(ValueError):
            self.store.current(1)


if __name__ == "__main__":
    unittest.main()
