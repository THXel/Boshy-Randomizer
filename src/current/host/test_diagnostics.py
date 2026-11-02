"""Diagnostics expose selected game facts, never arbitrary saves or paths."""

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace as S
from native_menu.diagnostics import snapshot, Diagnostics, LANGS, TEXT
from native_menu.display import Settings
from menu_host.draft import initial
from menu_host.store import RC4
from transition.router import GROUP


class DiagnosticsTests(unittest.TestCase):
    def controller(self, folder, phase="menu"):
        return S(
            base=Path("/private/secret/game.exe"),
            phase=phase,
            active_slot=2,
            folder=folder,
            store=S(folder=lambda slot: folder),
            window=S(reader=S(frame=lambda: "First World - Prehistorik")),
            model=S(
                draft=S(seed="DRAFT", options=initial()),
                display=Settings(),
                language="de",
            ),
            completion=S(data=None),
            secret="MUST NOT APPEAR",
        )

    def test_snapshot_is_allowlisted_and_does_not_expose_private_paths(self):
        c = self.controller(Path("/private/secret"))
        c.model.draft.options["secret"] = "MUST NOT APPEAR"
        data = snapshot(c)
        text = json.dumps(data)
        self.assertNotIn("private", text)
        self.assertNotIn("MUST NOT", text)
        self.assertEqual(data["build"], "game.exe")
        self.assertEqual(data["slot"], 2)
        self.assertEqual(data["seed"], "DRAFT")
        for captions in TEXT.values():
            self.assertEqual(len(captions), len(LANGS))

    def test_active_run_identity_comes_from_plan_not_menu_draft(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            c = self.controller(p, "playing")
            self.assertIsNone(snapshot(c)["seed"])
            (p / "plan.json").write_text(
                json.dumps(
                    {
                        "seed": "ACTIVE",
                        "options": {"mode": "boss_rush", "secret": "PRIVATE"},
                    }
                )
            )
            d = snapshot(c)
            self.assertEqual(d["seed"], "ACTIVE")
            self.assertEqual(d["options"], {"mode": "boss_rush"})

    def test_transition_history_is_bounded_and_contains_only_route_receipts(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            c = self.controller(p, "playing")
            c.diagnostics = Diagnostics(c)
            for n in range(25):
                text = f"[{GROUP}]\nCurrentStage={n}\nNextId={n + 1}\nSecret=/private/path\n"
                (p / "SaveFile1.ini").write_bytes(RC4(b"BLOB", text.encode("latin1")))
                c.diagnostics.observe_route()
            rows = snapshot(c)["recent_transitions"]
            self.assertEqual(len(rows), 20)
            self.assertEqual(rows[-1]["CurrentStage"], 24)
            self.assertNotIn("private", json.dumps(rows))
            c.diagnostics.observe_route()
            self.assertEqual(len(c.diagnostics.transitions), 20)

    def test_recent_errors_are_bounded_exportable_and_do_not_copy_exception_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            c = self.controller(folder)
            c.store.root = folder
            c.diagnostics = Diagnostics(c)
            for n in range(15):
                c.diagnostics.record_error(
                    "resume", ValueError("SECRET /private/path token=123")
                )
            data = snapshot(c)
            self.assertEqual(len(data["recent_errors"]), 10)
            self.assertEqual(data["recent_errors"][-1]["reason"], "validation_failed")
            report = json.loads((folder / "reports/last-error.json").read_text())
            self.assertEqual(report["recent_errors"], data["recent_errors"])
            self.assertNotIn("SECRET", json.dumps(report))
            self.assertNotIn("/private", json.dumps(report))

    def test_unavailable_optional_window_does_not_abort_or_repeat_request(self):
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            c = self.controller(folder)
            c.store.root = folder
            c.diagnostics = Diagnostics(c)
            (folder / "options.ini").write_bytes(
                RC4(b"BLOB", b"[Options]\nDiagnosticRequest=1\n")
            )
            with patch.object(
                c.diagnostics,
                "toggle",
                side_effect=ImportError("missing optional window"),
            ) as toggle:
                c.diagnostics.tick()
                c.diagnostics.tick()
                toggle.assert_called_once()
            self.assertIsNone(c.diagnostics.root)
            self.assertEqual(c.diagnostics.sequence, 1)
            report = json.loads((folder / "reports/last-error.json").read_text())
            self.assertEqual(
                report["recent_errors"][-1]["operation"], "diagnostics-window"
            )


if __name__ == "__main__":
    unittest.main()
