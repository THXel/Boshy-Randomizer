"""Portable JSON contract for desktop/OBS consumers; no game-memory writes.

Fusion's own save/profile receipts determine awards. The current menu host only
publishes them; consumers never infer wins from entering a room or route order.
"""

import configparser
import json
import math
import os
import time
from pathlib import Path
from menu_host.store import atomic, save
from gameplay.reward_plan import LOCATIONS, CHECKS
from gameplay.target_plan import progress as target_progress
from transition.router import STAGES, GROUP
from beta_catalogue import BOSSES
from position_names import position_name
from run_extras import presentation
from tracker.source import feed_path
from tracker.events import Awards
from tracker.snapshots import SnapshotCache


def process_start(pid):
    if os.name == "nt":
        from tracker.windows_process import inspect

        identity = inspect(pid)
        if identity is None:
            raise ProcessLookupError(pid)
        return identity.start
    # Bind the heartbeat to this process lifetime, preventing PID-reuse matches.
    return Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()[19]


def run_data(plan, config, profile, *, run_id, slot, frame, elapsed):
    mode = plan["options"]["mode"]
    completed = config.getint(GROUP, "Completed", fallback=0) == 1
    current = config.getint(GROUP, "CurrentStage", fallback=0)
    from gameplay.collections import collected

    items, chars = collected(config, profile)
    bosses = [
        dict(
            name=v[0],
            key=k,
            kind="boss",
            done=(
                config.getint("Achievements", k, fallback=0) >= 2
                or mode != "normal"
                and config.getint(GROUP, "Done" + str(STAGES[v[2]]["id"]), fallback=0)
                == 1
            ),
        )
        for k, v in BOSSES.items()
    ]
    bosses.append(
        dict(
            name="Solgryn",
            key="solgryn",
            kind="boss",
            done=completed or config.getint("Achievements", "Solgryn", fallback=0) >= 2,
        )
    )
    goals = []
    if mode == "target":
        got = target_progress(plan["targets"], config)
        goals = [
            dict(name=n, kind="item", done=n in got["items"])
            for n in plan["targets"]["items"]
        ]
        goals += [
            dict(name=BOSSES[k][0], key=k, kind="boss", done=k in got["bosses"])
            for k in plan["targets"]["bosses"]
        ]
    route = []
    for key in plan["route"] if mode not in ("normal", "target") else []:
        sid = STAGES[key]["id"]
        boss = next((v[0] for v in BOSSES.values() if v[2] == key), None)
        route.append(
            dict(
                name=boss
                or (
                    "Solgryn"
                    if key == "boss_solgryn.ini"
                    else position_name(key).replace("_", " ").title()
                ),
                kind="boss" if STAGES[key]["category"] == "bosses" else "level",
                frame=STAGES[key]["frame"],
                done=config.getint(GROUP, "Done" + str(sid), fallback=0) == 1
                or key == "boss_solgryn.ini"
                and completed,
                current=sid == current,
            )
        )
    index = next((i + 1 for i, r in enumerate(route) if r["current"]), 0)
    if mode == "target":
        index = config.getint("FusionTargetV1", "Visit", fallback=0)
    spot = next((key for key, s in STAGES.items() if s["id"] == current), None)
    return dict(
        mode="target" if mode == "target" else "randomizer",
        play_mode=mode,
        phase="finished" if completed else "running",
        test_run=config.getint("RandomizerDebug", "Enabled", fallback=0) == 1,
        run_id=run_id,
        slot=slot,
        seed=plan["seed"],
        share_seed=plan["shared_seed"],
        character=profile.get("License", "CharacterName", fallback="Boshy"),
        difficulty=plan["options"]["difficulty"],
        location=(
            frame
            if mode == "normal"
            else position_name(spot).replace("_", " ").title()
            if spot
            else frame
        ),
        frame=frame,
        elapsed=elapsed,
        timer_running=not completed,
        deaths=config.getint("Stats", "Deaths", fallback=0),
        items=items,
        characters=chars,
        bosses=bosses,
        goals=goals,
        route_stages=route,
        route_index=index,
        route_limit=len(route),
        checks_done=sum(
            config.getint(CHECKS, r["key"], fallback=0) == 1 for r in LOCATIONS
        ),
        checks_total=len(LOCATIONS),
        solgryn_unlocked=(
            all(r["done"] for r in goals)
            if goals
            else current == STAGES["boss_solgryn.ini"]["id"]
        ),
        active_extras=presentation(plan["options"]),
        run_settings=dict(
            music_enabled=plan["options"]["extras"].get("music", False),
            music_pack=plan.get("music_pack", "original"),
            blood_pack=plan.get("blood_pack", "original"),
            shot_mode=plan["options"]["extras"].get("shot_mode", "off"),
            shot_interval_seconds=plan["options"]["extras"].get(
                "shot_interval_seconds", 300
            ),
        ),
    )


class Publisher:
    def __init__(self, store, path=None):
        self.store = store
        self.path = Path(path) if path is not None else feed_path()
        self.last = 0.0
        self.identity = None
        self.plan = None
        self.clock = 0.0
        self.anchor = None
        self.clock_path = None
        self.last_clock = 0.0
        self.last_error = ""
        self.awards = Awards()
        self.snapshots = SnapshotCache(save)
        self.host_start = process_start(os.getpid())

    def pause(self):
        if self.anchor is not None:
            self.clock += max(0, time.monotonic() - self.anchor)
            self.anchor = None
            self.persist_clock(self.clock)

    def finish_run(self, controller, identity):
        """Freeze the correct run before the result takes its one-time snapshot.

        Completion can observe the receipt between regular publisher ticks.
        Force identity/clock initialization, then include the active interval.
        """
        self.tick(controller, force=True)
        if self.last_error or self.identity != identity:
            raise RuntimeError("Completion clock is not ready for this run")
        self.pause()
        return self.clock

    def persist_clock(self, elapsed):
        if self.clock_path:
            atomic(
                self.clock_path,
                json.dumps(
                    dict(schema=1, run_id=self.identity, elapsed=elapsed)
                ).encode(),
            )
            self.last_clock = time.monotonic()

    def emit(self, c, data):
        from tracker.localization import present

        pid = c.window.pid
        language = getattr(getattr(c, "model", None), "language", "en")
        events = self.awards.update(data)
        if data.get("test_run"):
            events = []  # Test grants are never presented as genuine discovery events.
        data = present(data, language)
        payload = dict(
            schema=2,
            producer="boshy-fusion",
            application="boshy-randomizer",
            updated_at=time.time(),
            host_pid=os.getpid(),
            host_start=self.host_start,
            game_pid=pid,
            game_start=process_start(pid) if pid else None,
            game_dir=str(c.folder.resolve()),
            game_running=bool(pid),
            language=language,
            events=events,
            **data,
        )
        atomic(self.path, (json.dumps(payload, ensure_ascii=False) + "\n").encode())

    def tick(self, c, force=False):
        now = time.monotonic()
        if not force and now - self.last < 0.5:
            return
        self.last = now
        try:
            if c.closed or not c.window.pid:
                self.pause()
                self.emit(c, dict(mode="stopped", phase="stopped", timer_running=False))
                return
            if c.phase not in ("starting", "playing") or c.active_slot is None:
                self.pause()
                self.emit(
                    c,
                    dict(
                        mode="menu",
                        play_mode="menu",
                        phase=c.phase,
                        elapsed=0,
                        timer_running=False,
                        items=[],
                        characters=[],
                        bosses=[],
                        goals=[],
                        seed="",
                        slot=0,
                        location="Spielstand wählen",
                    ),
                )
                return
            slot = c.active_slot
            meta = self.store.current(slot)
            identity = meta["run"][13:]
            if identity != self.identity:
                self.snapshots.clear()
            config = self.snapshots(c.folder / "SaveFile1.ini")
            profile = (
                self.snapshots(c.folder / "onlineLicense.ini")
                if (c.folder / "onlineLicense.ini").is_file()
                else configparser.ConfigParser(interpolation=None)
            )
            if identity != self.identity:
                self.pause()
                self.identity = identity
                folder = self.store.folder(slot)
                self.plan = json.loads((folder / "plan.json").read_text())
                self.clock_path = folder / "tracker-clock.json"
                self.clock = max(0, config.getfloat("Stats", "TimeSeconds", fallback=0))
                try:
                    old = json.loads(self.clock_path.read_text())
                    if old["schema"] == 1 and old["run_id"] == identity:
                        # The native counter can keep running in the ending/credits.
                        # The matching tracker receipt is the run clock, not a lower bound.
                        elapsed = float(old["elapsed"])
                        if math.isfinite(elapsed) and elapsed >= 0:
                            self.clock = elapsed
                except (OSError, ValueError, KeyError, TypeError):
                    pass
            complete = config.getint(GROUP, "Completed", fallback=0) == 1
            if complete or c.phase == "starting":
                self.pause()
            elif self.anchor is None:
                self.anchor = now
            elapsed = self.clock + (
                max(0, now - self.anchor) if self.anchor is not None else 0
            )
            data = run_data(
                self.plan,
                config,
                profile,
                run_id=identity,
                slot=slot,
                frame=c.window.reader.frame(),
                elapsed=elapsed,
            )
            presentation = getattr(c, "presentation", None)
            if presentation is not None:
                data["run_settings"].update(
                    music_pack=presentation.pack,
                    blood_pack=presentation.pack,
                    music_enabled=bool(presentation.music["Enabled"]),
                )
            if c.phase == "starting":
                data.update(phase="loading", timer_running=False)
            self.emit(c, data)
            if now - self.last_clock > 2:
                self.persist_clock(elapsed)
            self.last_error = ""
        except (
            OSError,
            ValueError,
            KeyError,
            TypeError,
            configparser.Error,
            RuntimeError,
        ) as exc:
            # A save may be between native Ini++ writes. Never crash gameplay or
            # award partial progress; consumers expire a stalled feed after 8s.
            self.last_error = str(exc)

    def close(self, c):
        self.snapshots.clear()
        self.pause()
        try:
            self.emit(c, dict(mode="stopped", phase="stopped", timer_running=False))
        except OSError:
            pass
