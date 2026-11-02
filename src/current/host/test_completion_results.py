"""Completion display is gated by an actual receipt and the post-credits room."""

import configparser
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
from native_menu import results
from native_menu.classic import ClassicModel
from native_menu.transport import write, read
from menu_host.store import Store, RC4
from transition.events import commands
from transition.router import GROUP
from tracker.details import present as details
import recover_boshy_classic as source


class CompletionTests(unittest.TestCase):
    def test_early_ending_has_one_unconditional_f2_restart(self):
        from transition.router import params
        import struct

        for number in results.ENDING_FRAMES:
            payload = next(p for p, n in source.routes.payloads.items() if n == number)
            before = source.sections(payload)
            after, audit = results.transform(number, before)
            additions = after[len(before) :]
            restarts = [
                row
                for rows in additions
                for row in rows
                if any(not c[0] and c[1:3] == (-3, 5) for c in commands(row))
            ]
            self.assertEqual(len(restarts), int(number == 47))
            self.assertEqual(audit[0]["early_restart"], number == 47)
            if restarts:
                conditions = [c for c in commands(restarts[0]) if c[0]]
                self.assertEqual(len(conditions), 1)
                self.assertEqual(conditions[0][1:3], (-6, -1))
                self.assertEqual(
                    struct.unpack_from("<H", params(conditions[0][-1], True)[0][1], 4)[
                        0
                    ],
                    113,
                )

    def test_no_summary_over_boss_animation_or_credits_or_unfinished_run(self):
        cfg = configparser.ConfigParser()
        cfg.read_dict({GROUP: {"Completed": "1"}})
        for name in ("Eleventh Boss - Solgryn", "Title Screen"):
            self.assertFalse(results.eligible(name, cfg))
        for frame in results.ENDING_NAMES:
            self.assertTrue(results.eligible(frame, cfg))
        cfg[GROUP]["Completed"] = "0"
        self.assertFalse(results.eligible("Prize Room", cfg))

    def test_native_summary_adds_no_transition_audio_or_save_writes(self):
        p = next(p for p, n in source.routes.payloads.items() if n == 49)
        before = source.sections(p)
        after, _ = results.transform(49, before)
        self.assertEqual(
            after[:-1],
            [[r for r in rows if not results.original_score_row(r)] for rows in before],
        )
        self.assertEqual(
            sum(results.original_score_row(r) for rows in before for r in rows), 9
        )
        self.assertFalse(
            any(results.original_score_row(r) for rows in after for r in rows)
        )
        acts = [c for row in after[-1] for c in commands(row) if not c[0]]
        self.assertFalse(any(c[1] in (-3, -2) for c in acts))
        self.assertFalse(any(b"SaveFile" in c[-1] for c in acts))
        self.assertEqual(results.transform(46, before), (before, []))

    def test_result_all_languages_and_exact_seed_copy_without_save_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            working = root / "working"
            working.mkdir()
            saved = root / "saved"
            saved.mkdir()
            model = ClassicModel(Store(root / "profile", runs=root / "runs"))
            plan = dict(
                seed="RESULTS",
                shared_seed=model.draft.shared(),
                options={"mode": "randomizer"},
            )
            (saved / "plan.json").write_text(json.dumps(plan))
            cfg = configparser.ConfigParser()
            cfg.read_dict(
                {
                    GROUP: {"Completed": "1"},
                    "Stats": {"Deaths": "15"},
                    "Collectables": {"Cake": "1"},
                }
            )
            import io

            stream = io.StringIO()
            cfg.write(stream)
            path = working / "SaveFile1.ini"
            path.write_bytes(RC4(b"BLOB", stream.getvalue().encode("latin1")))
            original = path.read_bytes()
            store = SimpleNamespace(
                current=lambda slot: {"run": "rebuilt-menu-" + "a" * 32},
                folder=lambda slot: saved,
            )
            c = SimpleNamespace(
                folder=working,
                model=model,
                store=store,
                tracker=SimpleNamespace(finish_run=Mock(return_value=65.4)),
                active_slot=1,
                phase="playing",
                closed=False,
                clipboard=Mock(),
                window=SimpleNamespace(
                    reader=SimpleNamespace(frame=lambda: "Prize Room")
                ),
            )
            summary = results.Completion(c)
            summary.tick()
            self.assertEqual(read(working / "results-view.ini")["ready"], 0)
            write(working / "results-input.ini", dict(EndingReady=1, Copy=0, Dismiss=0))
            summary.last = 0
            summary.tick()
            self.assertEqual(read(working / "results-view.ini")["ready"], 1)
            self.assertEqual(
                json.loads((saved / "result.json").read_text())["deaths"], 15
            )
            for language in results.LANGUAGES:
                model.language = language
                summary.publish()
            write(working / "results-input.ini", {"Copy": 1})
            summary.last = 0
            summary.tick()
            c.clipboard.put.assert_called_once_with(plan["shared_seed"])
            self.assertEqual(path.read_bytes(), original)
            write(working / "results-input.ini", dict(Dismiss=1, Copy=1, EndingReady=1))
            summary.last = 0
            summary.tick()
            self.assertTrue(summary.dismissed)
            self.assertEqual(read(working / "results-view.ini")["ready"], 0)
            summary.publish()
            self.assertEqual(read(working / "results-view.ini")["ready"], 0)
            summary.reset()
            self.assertFalse(summary.dismissed)
            self.assertEqual(read(working / "results-view.ini")["ready"], 0)

    def test_active_clock_is_frozen_even_between_publisher_ticks(self):
        from tracker.publisher import Publisher
        from unittest.mock import patch

        publisher = Publisher(None)
        publisher.identity = "run"
        publisher.clock = 20
        publisher.anchor = 100
        publisher.tick = Mock()  # the completed receipt was just observed by Completion
        with patch("tracker.publisher.time.monotonic", return_value=150):
            self.assertEqual(publisher.finish_run(object(), "run"), 70)
        self.assertIsNone(publisher.anchor)
        with patch("tracker.publisher.time.monotonic", return_value=200):
            self.assertEqual(publisher.finish_run(object(), "run"), 70)
        with self.assertRaises(RuntimeError):
            publisher.finish_run(object(), "another-run")

    def test_completed_run_restores_frozen_clock_not_later_native_counter(self):
        from tracker.publisher import Publisher
        from unittest.mock import patch
        from test_tracker import plan

        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            (folder / "plan.json").write_text(json.dumps(plan("target")))
            (folder / "tracker-clock.json").write_text(
                json.dumps(dict(schema=1, run_id="run", elapsed=571.64))
            )
            cfg = configparser.ConfigParser()
            cfg.read_dict({GROUP: {"Completed": "1"}, "Stats": {"TimeSeconds": "797"}})
            store = SimpleNamespace(
                current=lambda slot: {"run": "rebuilt-menu-run"},
                folder=lambda slot: folder,
            )
            pub = Publisher(store, folder / "feed.json")
            pub.snapshots = Mock(return_value=cfg)
            pub.emit = Mock()
            c = SimpleNamespace(
                closed=False,
                phase="playing",
                active_slot=1,
                folder=folder,
                window=SimpleNamespace(
                    pid=1, reader=SimpleNamespace(frame=lambda: "Credits")
                ),
            )
            self.assertEqual(pub.finish_run(c, "run"), 571.64)
            self.assertIsNone(pub.anchor)
            self.assertEqual(pub.emit.call_args.args[1]["elapsed"], 571.64)

    def test_target_summary_counts_only_actual_goal_receipts(self):
        cfg = configparser.ConfigParser()
        cfg.read_dict({"Collectables": {"Sexy Sax CD": "1"}, GROUP: {"Completed": "1"}})
        plan = dict(
            seed="TARGET",
            shared_seed="code",
            options={"mode": "target"},
            targets={"items": ["Sexy Sax CD", "Cake"], "bosses": []},
        )
        data = results.snapshot(plan, cfg, 571.64, 1, "run")
        self.assertEqual(data["elapsed"], 571.64)
        self.assertEqual(
            data["goals"],
            [{"name": "Sexy Sax CD", "done": True}, {"name": "Cake", "done": False}],
        )
        self.assertEqual(data["bosses"], 1)

    def test_tracker_preserves_real_pack_identifiers(self):
        for pack in ("original", "kamilia3", "wannafest22"):
            shown = details({"run_settings": {"music_pack": pack, "blood_pack": pack}})
            self.assertEqual(shown["run_settings"]["music_pack"], pack)
            self.assertEqual(shown["run_settings"]["blood_pack"], pack)

    def test_tracker_details_translate_and_ignore_malformed_values(self):
        data = details(
            dict(
                active_extras=[
                    {"key": "god_mode", "icon": "G"},
                    {"key": "god_mode"},
                    {"key": []},
                ],
                run_settings={
                    "music_pack": {},
                    "blood_pack": [],
                    "shot_mode": False,
                    "music_enabled": "true",
                },
            )
        )
        self.assertEqual(len(data["active_extras"]), 1)
        self.assertEqual(
            set(data["active_extras"][0]["labels"]), set(results.LANGUAGES)
        )
        self.assertFalse(data["run_settings"]["music_enabled"])
        self.assertEqual(data["run_settings"]["music_pack"], "original")


if __name__ == "__main__":
    unittest.main()
