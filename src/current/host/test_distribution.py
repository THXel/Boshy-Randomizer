"""Untrusted input, transaction failures, portable config and package gates."""

import copy
import hashlib
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch
from distribution import original, transaction, lutris, gates
from distribution.identity import source_digest, sha256, verify_receipt


def digest(data):
    return hashlib.sha256(data).hexdigest()


class ImportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / "original"
        self.source.mkdir()
        (self.source / original.ORIGINAL_NAME).write_bytes(b"original")
        (self.source / "Music").mkdir()
        (self.source / "Music/music.ogg").write_bytes(b"music")
        (self.source / "SaveFile1.ini").write_bytes(b"private save")
        (self.source / "launch.exe").write_bytes(b"unrelated")
        self.expected = digest(b"original")

    def test_folder_import_keeps_source_and_excludes_old_saves_and_wrappers(self):
        p = original.import_original(
            self.source, self.root / "copy", expected=self.expected
        )
        self.assertEqual(p.read_bytes(), b"original")
        self.assertEqual((self.root / "copy/Music/music.ogg").read_bytes(), b"music")
        self.assertFalse((self.root / "copy/SaveFile1.ini").exists())
        self.assertFalse((self.root / "copy/launch.exe").exists())
        self.assertEqual((self.source / "SaveFile1.ini").read_bytes(), b"private save")

    def archive(self, entries):
        p = self.root / "source.zip"
        with zipfile.ZipFile(p, "w") as z:
            for name, data in entries:
                item = zipfile.ZipInfo(name)
                # Retain intentionally malformed raw names on Windows too.
                item.filename = item.orig_filename = name
                z.writestr(item, data)
        return p

    def test_nested_zip_and_case_normalized_original(self):
        z = self.archive(
            [
                ("Boshy/" + original.ORIGINAL_NAME.upper(), b"original"),
                ("Boshy/Music/song.ogg", b"music"),
            ]
        )
        p = original.import_original(z, self.root / "copy", expected=self.expected)
        self.assertEqual(p.name, original.ORIGINAL_NAME)
        self.assertTrue((p.parent / "Music/song.ogg").exists())

    def test_rejects_bad_paths_links_duplicates_ambiguity_and_limits(self):
        for bad in [
            "../outside",
            "C:/outside",
            "/outside",
            "a\\outside",
            "CON.txt",
            "x:ads",
            "tail.",
        ]:
            with self.subTest(path=bad):
                z = self.archive([(original.ORIGINAL_NAME, b"original"), (bad, b"bad")])
                with self.assertRaises(ValueError):
                    original.import_original(
                        z, self.root / "copy", expected=self.expected
                    )
                self.assertFalse((self.root / "copy").exists())
        z = self.archive(
            [
                (original.ORIGINAL_NAME, b"original"),
                ("x/A.txt", b"a"),
                ("x/a.txt", b"b"),
            ]
        )
        with self.assertRaisesRegex(ValueError, "colliding"):
            original.import_original(z, self.root / "copy", expected=self.expected)
        import os
        import subprocess

        link = self.source / "link"
        if os.name == "nt":
            subprocess.run(
                ["cmd.exe", "/c", "mklink", "/J", str(link), str(self.root)],
                check=True,
                capture_output=True,
            )
        else:
            link.symlink_to(self.root, target_is_directory=True)
        try:
            with self.assertRaisesRegex(ValueError, "Links"):
                original.import_original(
                    self.source, self.root / "copy", expected=self.expected
                )
        finally:
            if os.name == "nt":
                link.rmdir()
            else:
                link.unlink()
        z = self.archive(
            [
                (original.ORIGINAL_NAME, b"original"),
                ("another/" + original.ORIGINAL_NAME, b"original"),
            ]
        )
        with self.assertRaisesRegex(ValueError, "exactly one"):
            original.import_original(z, self.root / "copy", expected=self.expected)
        with (
            patch.object(original, "MAX_FILE", 2),
            self.assertRaisesRegex(ValueError, "limits"),
        ):
            original.import_original(
                self.source, self.root / "copy", expected=self.expected
            )

    def test_bad_original_never_leaves_partial_import_and_source_is_not_target(self):
        with self.assertRaisesRegex(ValueError, "Unsupported"):
            original.import_original(self.source, self.root / "copy", expected="0" * 64)
        self.assertFalse((self.root / "copy").exists())
        with self.assertRaises(ValueError):
            original.import_original(
                self.source, self.source / "copy", expected=self.expected
            )
        self.assertFalse((self.source / "copy").exists())

    def test_interrupted_patch_and_corrupt_update_preserve_active_then_rollback(self):
        root = self.root / "installation"

        def write(data):
            return lambda source, target: target.write_bytes(data)

        transaction.install(
            self.source,
            root,
            "v1",
            digest(b"v1"),
            write(b"v1"),
            expected_source=self.expected,
        )
        first = (root / "active.json").read_bytes()

        def crash(source, target):
            target.write_bytes(b"partial")
            raise RuntimeError("power interruption simulation")

        with self.assertRaises(RuntimeError):
            transaction.install(
                self.source,
                root,
                "v2",
                digest(b"v2"),
                crash,
                expected_source=self.expected,
            )
        with self.assertRaisesRegex(ValueError, "checksum"):
            transaction.install(
                self.source,
                root,
                "v2",
                digest(b"v2"),
                write(b"bad"),
                expected_source=self.expected,
            )
        self.assertEqual((root / "active.json").read_bytes(), first)
        self.assertFalse((root / "versions/v2").exists())
        transaction.install(
            self.source,
            root,
            "v2",
            digest(b"v2"),
            write(b"v2"),
            expected_source=self.expected,
        )
        self.assertEqual(transaction.active(root)["version"], "v2")
        restored = transaction.rollback(root)
        self.assertEqual(restored.read_bytes(), b"v1")
        self.assertEqual(transaction.active(root)["version"], "v1")
        self.assertEqual(
            (self.source / original.ORIGINAL_NAME).read_bytes(), b"original"
        )

    def test_activation_failure_does_not_publish_new_version(self):
        root = self.root / "installation"
        real = transaction.atomic_json

        def fail(path, data):
            if Path(path).name == "active.json":
                raise OSError("activation failure")
            return real(path, data)

        with (
            patch.object(transaction, "atomic_json", side_effect=fail),
            self.assertRaises(OSError),
        ):
            transaction.install(
                self.source,
                root,
                "v1",
                digest(b"v1"),
                lambda a, b: b.write_bytes(b"v1"),
                expected_source=self.expected,
            )
        self.assertIsNone(transaction.active(root))
        self.assertFalse((root / "versions/v1").exists())

    def test_prepared_payload_waits_for_activation_and_rollback_checks_host(self):
        from distribution.identity import sha256

        package = self.root / "package"
        (package / "app").mkdir(parents=True)
        (package / "app/main.py").write_text("print('v1')")
        manifest = {
            "schema": 1,
            "files": {"app/main.py": sha256(package / "app/main.py")},
        }
        (package / "package.json").write_text(json.dumps(manifest))
        root = self.root / "installed"
        transaction.install(
            self.source,
            root,
            "v1",
            digest(b"v1"),
            lambda a, b: b.write_bytes(b"v1"),
            expected_source=self.expected,
            payload=package,
            activate_now=False,
        )
        self.assertIsNone(transaction.active(root))
        transaction.activate(root, "v1")
        transaction.install(
            self.source,
            root,
            "v2",
            digest(b"v2"),
            lambda a, b: b.write_bytes(b"v2"),
            expected_source=self.expected,
        )
        (root / "versions/v1/app/main.py").write_text("damaged")
        with self.assertRaisesRegex(ValueError, "damaged"):
            transaction.rollback(root)
        self.assertEqual(transaction.active(root)["version"], "v2")
        (package / "app/main.py").write_text("damaged package")
        with self.assertRaisesRegex(ValueError, "Damaged application"):
            transaction.install(
                self.source,
                root,
                "v3",
                digest(b"v3"),
                lambda a, b: b.write_bytes(b"v3"),
                expected_source=self.expected,
                payload=package,
            )
        self.assertFalse((root / "versions/v3").exists())
        self.assertEqual(transaction.active(root)["version"], "v2")


class PackagingTests(unittest.TestCase):
    def test_uninstall_preserves_untracked_files_and_original_source(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            source = root / "source"
            source.mkdir()
            (source / original.ORIGINAL_NAME).write_bytes(b"original")
            destination = root / "installed"
            with transaction.installation_lock(destination):
                installed = transaction.install(
                    source,
                    destination,
                    "v1",
                    digest(b"modded"),
                    lambda original, output: output.write_bytes(b"modded"),
                    expected_source=digest(b"original"),
                )
                (installed / "personal-note.txt").write_text("keep")
                preserved = transaction.uninstall(destination)
            self.assertTrue(preserved)
            self.assertEqual((installed / "personal-note.txt").read_text(), "keep")
            self.assertFalse((installed / "game" / original.ORIGINAL_NAME).exists())
            self.assertEqual(
                (source / original.ORIGINAL_NAME).read_bytes(), b"original"
            )
            self.assertIsNone(transaction.active(destination))

    def test_runtime_paths_require_complete_absolute_configuration(self):
        import os
        import app_paths

        with tempfile.TemporaryDirectory() as name:
            config = Path(name) / "runtime.json"
            data = {
                k: str(Path(name) / k)
                for k in (
                    "prefix",
                    "original",
                    "soundpacks",
                    "game",
                    "wine",
                    "repository",
                )
            }
            data["schema"] = 1
            config.write_text(json.dumps(data))
            with patch.dict(os.environ, {"BOSHY_RUNTIME_CONFIG": str(config)}):
                self.assertEqual(app_paths.load_config(), data)
                data["game"] = "relative.exe"
                config.write_text(json.dumps(data))
                with self.assertRaisesRegex(ValueError, "absolute"):
                    app_paths.load_config()

    def test_lutris_settings_have_no_developer_paths_and_keep_reviewed_flags(self):
        cfg = lutris.installer(Path("/users/new/game.exe"), Path("/users/new/prefix"))
        self.assertNotIn("thxel", json.dumps(cfg))
        self.assertEqual(cfg["script"]["wine"]["version"], "wine-staging-11.2-x86_64")
        for key in ["dxvk", "vkd3d", "esync", "fsync"]:
            self.assertIs(cfg["script"]["wine"][key], False)
        self.assertEqual(cfg["script"]["game"]["exe"], "/users/new/game.exe")
        self.assertEqual(cfg["script"]["wine"]["MouseWarpOverride"], "enable")

    def test_missing_and_stale_release_evidence_rejects_package(self):
        manifest = {"schema": 1, "game_sha256": "a" * 64, "gates": {}}
        with self.assertRaisesRegex(ValueError, "not verified"):
            gates.validate(manifest, platform="linux")
        manifest["gates"] = {
            k: {"status": "passed", "game_sha256": "a" * 64, "report": "evidence.json"}
            for k in gates.REQUIRED
        }
        self.assertTrue(gates.validate(manifest, platform="windows"))
        manifest["gates"]["original_resource_patch"]["game_sha256"] = "b" * 64
        with self.assertRaisesRegex(ValueError, "original_resource_patch"):
            gates.validate(manifest, platform="windows")

    def test_build_receipt_rejects_source_changes_or_wrong_selected_project(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            src = root / "src"
            src.mkdir()
            (src / "app.py").write_text("pass\n")
            project = root / "game.mfa"
            project.write_bytes(b"project")
            exe = root / "game.exe"
            exe.write_bytes(b"game")
            receipt = {
                "schema": 1,
                "status": "verified",
                "source_sha256": source_digest(src),
                "project_sha256": sha256(project),
                "game_sha256": sha256(exe),
            }
            verify_receipt(receipt, src, project, exe)
            project.write_bytes(b"older project")
            with self.assertRaisesRegex(ValueError, "changed"):
                verify_receipt(receipt, src, project, exe)
            project.write_bytes(b"project")
            (src / "app.py").write_text("print(1)\n")
            with self.assertRaisesRegex(ValueError, "changed"):
                verify_receipt(receipt, src, project, exe)

    def test_all_stations_have_regression_cases_and_no_pending_case_passes(self):
        from quality.exit_catalogue import checklist, verify_evidence
        from transition.router import NAMED_STAGES

        matrix = checklist()
        self.assertEqual({r["position"] for r in matrix["stations"]}, set(NAMED_STAGES))
        self.assertGreater(len(verify_evidence(matrix, "a" * 64)), len(NAMED_STAGES))
        duplicate = copy.deepcopy(matrix)
        duplicate["stations"].append(duplicate["stations"][0])
        with self.assertRaises(ValueError):
            verify_evidence(duplicate, "a" * 64)

    def test_user_update_history_does_not_name_development_engine(self):
        from native_menu.history import ENTRIES, TITLE_CARD

        text = json.dumps([ENTRIES, TITLE_CARD]).casefold()
        self.assertNotIn("clickteam", text)
        self.assertNotIn("fusion", text)


if __name__ == "__main__":
    unittest.main()
