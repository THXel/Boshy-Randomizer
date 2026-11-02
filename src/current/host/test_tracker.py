"""Native awards, run identity, stale feeds and original/Randomizer isolation."""

import configparser
import importlib.util
import json
import os
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from tracker.publisher import Publisher, run_data, process_start
from menu_host.store import atomic, RC4
from menu_host.draft import Draft
from transition.router import GROUP
from gameplay.reward_plan import LOCATIONS

ADAPTER = (
    Path(__file__).resolve().parent / "integrations/pingulexa_boshy_randomizer.py"
)
spec = importlib.util.spec_from_file_location("tracker_adapter_test", ADAPTER)
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)


def config(data=None):
    c = configparser.ConfigParser(interpolation=None)
    c.read_dict(data or {})
    return c


def plan(mode="randomizer"):
    d = Draft()
    d.set_mode(mode)
    return dict(
        seed="TRACKER",
        shared_seed=d.shared(),
        options=d.options,
        route=["boss1.ini", "boss_solgryn.ini"],
        targets=dict(items=["Cake"], bosses=["hellokitty"]),
    )


def snapshot(mode="randomizer", c=None, p=None):
    return run_data(
        plan(mode),
        c or config(),
        p or config(),
        run_id="a" * 32,
        slot=1,
        frame="First Boss - Hello Kitty",
        elapsed=3,
    )


class TrackerTests(unittest.TestCase):
    def test_translated_boss_name_does_not_replay_award(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pub = Publisher(None, root / "feed.json")
            c = SimpleNamespace(window=SimpleNamespace(pid=os.getpid()), folder=root,
                                model=SimpleNamespace(language="de"))
            data = snapshot()
            boss = next(r for r in data["bosses"] if r["key"] == "ninja_ryu")
            pub.emit(c, data)
            boss["done"] = True
            pub.emit(c, data)
            original_events = json.loads(pub.path.read_text())["events"]
            self.assertEqual(len(original_events), 1)
            for language in ("en", "es", "ru", "ja", "de"):
                c.model.language = language
                pub.emit(c, data)
                self.assertEqual(json.loads(pub.path.read_text())["events"], original_events)

    def test_language_changes_only_presentation_not_receipts_or_run_identity(self):
        from tracker.localization import present
        from menu_host.labels import LANGUAGES, text

        raw = snapshot()
        raw["location"] = "Spielstand wählen"
        raw["active_extras"] = [dict(key="quiet_pickups", icon="P", label="old", hint="old")]
        for language in LANGUAGES:
            translated = present(raw, language)
            self.assertEqual(translated["run_id"], raw["run_id"])
            self.assertEqual(translated["items"], raw["items"])
            self.assertEqual([r["done"] for r in translated["bosses"]], [r["done"] for r in raw["bosses"]])
            self.assertEqual(translated["active_extras"][0]["hint"], text("quiet_pickups_hint", language))
        self.assertEqual(raw["active_extras"][0]["hint"], "old")
        self.assertEqual(present(raw, "unsupported"), present(raw, "en"))

    def test_only_original_receipts_award_items_characters_and_bosses(self):
        c = config(
            {
                GROUP: {"CurrentStage": 1},
                "Collectables": {"Cake": 1},
                "RandoChecks": {LOCATIONS[0]["key"]: 1},
            }
        )
        s = snapshot(c=c)
        self.assertFalse(any(r["done"] for r in s["bosses"]))
        self.assertFalse(any(r["done"] for r in s["characters"]))
        self.assertEqual([r["name"] for r in s["items"] if r["done"]], ["Cake"])
        self.assertEqual(s["checks_done"], 1)
        c[GROUP]["Done1"] = "1"
        s = snapshot(c=c)
        self.assertEqual([r["key"] for r in s["bosses"] if r["done"]], ["hellokitty"])
        self.assertEqual(s["route_stages"][1]["done"], False)

    def test_target_goal_completion_is_not_room_entry(self):
        c = config({GROUP: {"CurrentStage": 1}, "Collectables": {"Cake": 1}})
        s = snapshot("target", c)
        self.assertFalse(s["solgryn_unlocked"])
        self.assertEqual([r["done"] for r in s["goals"]], [True, False])
        c[GROUP]["Done1"] = "1"
        self.assertTrue(snapshot("target", c)["solgryn_unlocked"])

    def test_normal_mode_is_still_randomizer_and_requires_real_boss_achievement(self):
        c = config({GROUP: {"Done1": 1}, "Stats": {"Deaths": 4}})
        s = snapshot("normal", c)
        self.assertFalse(any(r["done"] for r in s["bosses"]))
        s.update(updated_at=time.time(), game_running=True)
        presented = adapter.present(s)
        self.assertEqual(presented["display_mode"], "randomizer")
        self.assertEqual(presented["deaths_run"], 4)
        self.assertEqual(presented["lss_path"], "")
        self.assertFalse(presented["personal_bests"])

    def test_original_game_has_priority_and_input_is_unchanged(self):
        normal = {"game_running": True, "lss_path": "real.lss", "splits": [1]}
        self.assertIs(adapter.select(normal, snapshot()), normal)
        self.assertEqual(
            normal, {"game_running": True, "lss_path": "real.lss", "splits": [1]}
        )
        self.assertIs(adapter.select(normal, None), normal)

    def test_schema_modes_expiry_and_malformed_payloads(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "live.json"
            base = dict(
                schema=2,
                application="boshy-randomizer",
                producer="boshy-fusion",
                updated_at=100,
                game_running=True,
                **snapshot(),
            )

            def check(d):
                path.write_text(json.dumps(d))
                return adapter.read_feed(path, now=101, check_process=False)

            self.assertIsNotNone(check(base))
            for fields in (
                {"updated_at": 90},
                {"updated_at": 102},
                {"mode": "stopped"},
                {"producer": "other"},
                {"game_running": False},
                {"run_id": "x" * 32},
                {"elapsed": float("nan")},
                {"items": [{}]},
                {"play_mode": "speedrun"},
                {"slot": True},
            ):
                with self.subTest(fields=fields):
                    self.assertIsNone(check({**base, **fields}))
            self.assertIsNotNone(check({**base, "schema": 1}))

    def test_feed_requires_live_game_and_current_process_lifetimes(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "live.json"
            d = dict(
                schema=2,
                application="boshy-randomizer",
                producer="boshy-fusion",
                updated_at=time.time(),
                game_running=True,
                host_pid=os.getpid(),
                host_start=process_start(os.getpid()),
                game_pid=os.getpid(),
                game_start=process_start(os.getpid()),
                game_dir=os.getcwd(),
                **snapshot(),
            )
            p.write_text(json.dumps(d))
            self.assertIsNone(adapter.read_feed(p))  # Python is not Boshy.exe.
            self.assertIsNone(adapter._process(os.getpid(), "wrong-start"))
            self.assertIsNotNone(
                adapter._process(os.getpid(), process_start(os.getpid()))
            )

    def test_publisher_pauses_on_menu_and_restores_each_slot_clock(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run = root / "run"
            work = root / "working"
            run.mkdir()
            work.mkdir()
            (run / "plan.json").write_text(json.dumps(plan()))
            atomic(work / "SaveFile1.ini", RC4(b"BLOB", b"[Stats]\nTimeSeconds=0\n"))
            store = SimpleNamespace(
                current=lambda slot: {"run": "rebuilt-menu-" + "a" * 32},
                folder=lambda slot: run,
            )
            c = SimpleNamespace(
                closed=False,
                window=SimpleNamespace(
                    pid=os.getpid(),
                    reader=SimpleNamespace(frame=lambda: "First Boss - Hello Kitty"),
                ),
                folder=work,
                phase="playing",
                active_slot=1,
            )
            clock = [10.0]
            with patch(
                "tracker.publisher.time.monotonic", side_effect=lambda: clock[0]
            ):
                pub = Publisher(store, root / "feed.json")
                pub.tick(c, True)
                self.assertFalse(pub.last_error)
                clock[0] = 14
                pub.tick(c, True)
                s = json.loads(pub.path.read_text())
                self.assertEqual(s["elapsed"], 4)
                c.phase = "menu"
                pub.tick(c, True)
                clock[0] = 99
                pub.tick(c, True)
                self.assertEqual(
                    json.loads((run / "tracker-clock.json").read_text())["elapsed"], 4
                )
                c.phase = "playing"
                pub.tick(c, True)
                self.assertEqual(json.loads(pub.path.read_text())["elapsed"], 4)
                c.closed = True
                c.window.pid = None
                pub.close(c)
                self.assertEqual(json.loads(pub.path.read_text())["mode"], "stopped")
