"""Read-only tracker regressions: receipts, lifecycle, HTTP boundary and assets."""

import copy
import json
import os
import tempfile
import threading
import time
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from tracker.events import Awards
from tracker.source import read_feed, alive
from tracker.server import Server, Assets, present


def state():
    return dict(
        schema=2,
        application="boshy-randomizer",
        producer="boshy-fusion",
        updated_at=time.time(),
        game_running=True,
        mode="randomizer",
        play_mode="boss_rush",
        run_id="a" * 32,
        slot=1,
        elapsed=1.0,
        items=[dict(name="Cake", kind="item", done=False)],
        characters=[],
        bosses=[dict(name="Hello Kitty", kind="boss", done=False)],
        goals=[],
        route_stages=[],
        share_seed="BR12-example",
        deaths=0,
    )


class WebTrackerTests(unittest.TestCase):
    def test_loading_baseline_awards_once_and_menu_resume_does_not_replay(self):
        awards = Awards()
        d = state()
        d["phase"] = "loading"
        self.assertEqual(awards.update(d), [])
        d["phase"] = "running"
        d["items"][0]["done"] = True
        event = awards.update(d)
        self.assertEqual(len(event), 1)
        self.assertEqual(event[0]["name"], "Cake")
        self.assertEqual(awards.update(dict(mode="menu")), [])
        self.assertEqual(awards.update(d), event)
        other = copy.deepcopy(d)
        other["run_id"] = "b" * 32
        self.assertEqual(awards.update(other), [])
        self.assertEqual(awards.update(d), event)
        self.assertEqual(Awards().update(d), [])
        d["bosses"][0]["done"] = True
        self.assertEqual(len(awards.update(d)), 2)

    def test_loading_another_slot_does_not_replay_shared_unlocks(self):
        awards = Awards()
        data = state()
        awards.update(data)
        data["phase"] = "loading"
        data["characters"] = [dict(name="Kirby", kind="character", done=True)]
        self.assertEqual(awards.update(data), [])
        data["phase"] = "running"
        self.assertEqual(awards.update(data), [])
        data["items"][0]["done"] = True
        self.assertEqual([e["name"] for e in awards.update(data)], ["Cake"])

    def test_reader_rejects_expired_and_malformed_data_without_game_writes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "live.json"
            d = state()
            now = d["updated_at"]

            def check(value):
                path.write_text(json.dumps(value))
                before = path.read_bytes()
                result = read_feed(path, now=now, check_process=False)
                self.assertEqual(path.read_bytes(), before)
                return result

            self.assertEqual(check(d), d)
            for fields in (
                {"updated_at": now - 9},
                {"updated_at": now + 1},
                {"mode": "stopped"},
                {"game_running": False},
                {"elapsed": float("nan")},
                {"deaths": -1},
                {"slot": True},
                {"run_id": "invalid"},
                {"items": [{"name": "x", "done": 1}]},
                {"route_stages": [{}]},
                {"producer": "other"},
            ):
                with self.subTest(fields=fields):
                    self.assertIsNone(check({**d, **fields}))
            self.assertIsNone(check([]))
            path.write_text("x" * 262145)
            self.assertIsNone(read_feed(path))

    def test_process_lifetime_and_game_identity_are_required(self):
        d = state()
        proc = Path("/proc") / str(os.getpid())
        start = (proc / "stat").read_text().rsplit(")", 1)[1].split()[19]
        d.update(
            host_pid=os.getpid(),
            host_start=start,
            game_pid=os.getpid(),
            game_start=start,
            game_dir=str(Path.cwd()),
        )
        self.assertFalse(alive(d))
        d["game_start"] = "wrong"
        self.assertFalse(alive(d))
        d["host_pid"] = -1
        self.assertFalse(alive(d))

    def test_public_payload_hides_private_paths_and_retains_confirmed_receipts(self):
        d = state()
        d.update(game_dir="/private/save", host_pid=123, game_pid=456)
        result = present(d, Assets())
        self.assertNotIn("game_dir", result)
        self.assertNotIn("host_pid", result)
        self.assertFalse(result["bosses"][0]["done"])
        self.assertEqual(result["share_seed"], "BR12-example")
        self.assertEqual(present(None, Assets()), dict(connected=False))

    def test_all_native_rewards_and_routes_have_real_icons(self):
        from test_tracker import snapshot, plan, config
        from transition.router import STAGES
        from tracker.publisher import run_data

        assets = Assets()
        d = snapshot()
        for key in ("items", "characters", "bosses"):
            for row in d[key]:
                self.assertIn(assets.icon(row), assets.files)
                self.assertNotEqual(assets.icon(row), assets.fallback, row)
        p = plan()
        p["route"] = list(STAGES)
        d = run_data(
            p, config(), config(), run_id="a" * 32, slot=1, frame="", elapsed=0
        )
        for row in d["route_stages"]:
            self.assertIn(assets.icon(row), assets.files)
            self.assertNotEqual(assets.icon(row), assets.fallback, row)

    def test_http_is_read_only_allowlisted_and_expires_game(self):
        data = state()
        server = Server(0, source=lambda: data)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server.server_port}"
        try:
            with urlopen(base + "/state") as response:
                self.assertEqual(response.headers["Cache-Control"], "no-store")
                payload = json.load(response)
                self.assertTrue(payload["connected"])
            for path in (
                "/",
                "/overlay",
                "/app.js",
                "/style.css",
                payload["items"][0]["icon"],
            ):
                with urlopen(base + path) as response:
                    self.assertEqual(response.status, 200)
            for request, code in (
                (Request(base + "/state", method="POST"), 501),
                (Request(base + "/../source.py"), 404),
                (Request(base + "/state", headers={"Host": "example.org"}), 403),
                (
                    Request(base + "/state", headers={"Origin": "https://example.org"}),
                    403,
                ),
            ):
                with self.assertRaises(HTTPError) as exc:
                    urlopen(request)
                self.assertEqual(exc.exception.code, code)
            data = None
            with urlopen(base + "/state") as response:
                self.assertFalse(json.load(response)["connected"])
        finally:
            server.shutdown()
            server.server_close()
            thread.join()


if __name__ == "__main__":
    unittest.main()
