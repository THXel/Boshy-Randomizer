"""Native keys create/resume/clear slot 2; Q/R/F2; same menu process on clear."""

import json, time, uuid, subprocess
from menu_host.store import Store, digest
from menu_host.processes import games
from native_menu.controller import Controller
from native_menu_probe import key, pump, OUT, capture


def wait_for(c, test, seconds=150):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        c.tick()
        if test():
            return
        time.sleep(0.04)
    raise AssertionError("Lifecycle timeout: " + str(c.model.message))


def pulse_inputs(pid):
    streams = json.loads(
        subprocess.check_output(["pactl", "--format=json", "list", "sink-inputs"])
    )
    return [
        s["index"]
        for s in streams
        if str(s["properties"].get("application.process.id")) == str(pid)
    ]


def main():
    report = {"scope": __doc__, "memory_writes": 0, "events": []}
    store = Store(OUT / ("native-lifecycle-profile-" + uuid.uuid4().hex[:8]))
    with store.lock():
        c = Controller(store)
        # Bound the export fixture; every lifecycle action uses real native keys.
        c.model.draft.update(
            level_pool=["save1.ini"],
            level_count=1,
            boss_pool=[],
            route_boss_count=0,
            god_mode=True,
            no_mouse_ghost=True,
        )
        try:
            c.open()
            c.enter()
            pump(c, 0.3)
            key(c, "Down")
            key(c, "Return")
            assert c.model.slot == 2
            key(c, "Down")
            key(c, "Down")
            key(c, "Return")
            assert c.model.busy and c.operation == "new"
            capture.snap(c.window, "native-export-loading")
            wait_for(c, lambda: bool(store.active))
            assert c.runtime.reader.frame() == "First World - Prehistorik"
            assert len(games()) == 1, games()
            before = store.summary(2)
            exe = digest(store.folder(2) / "Boshy.exe")
            seed = before["seed"]
            report["events"].append(
                {"create_slot": 2, "seed": seed, "pid": c.runtime.pid}
            )
            c.runtime.key("q")
            pump(c, 1.3)
            capture.snap(c.runtime, "native-run-death")
            c.runtime.key("r")
            pump(c, 0.8)
            c.runtime.key("F2")
            wait_for(c, lambda: not store.active and c.window.owned())
            pump(c, 0.4)
            saved = store.summary(2)
            assert saved["deaths"] > before["deaths"], (before, saved)
            assert c.model.slot == 2 and c.model.draft.seed == seed, (
                c.model.slot,
                c.model.draft.seed,
                seed,
            )
            capture.snap(c.window, "native-return-slot2")
            report["events"].append({"Q_R_F2": True, "save": saved})
            # Home focus is zero on return; resume is row four.
            for _ in range(4):
                key(c, "Down")
            key(c, "Return")
            wait_for(c, lambda: bool(store.active))
            assert c.runtime.reader.frame() == "First World - Prehistorik"
            assert digest(store.folder(2) / "Boshy.exe") == exe
            assert store.summary(2)["seed"] == seed
            c.runtime.key("F2")
            wait_for(c, lambda: not store.active and c.window.owned())
            pump(c, 0.4)
            report["events"].append({"resume_same_export": True})
            pid, window = c.window.pid, c.window.window
            streams = pulse_inputs(pid)
            for _ in range(5):
                key(c, "Down")
            key(c, "Return")
            wait_for(c, lambda: not c.model.busy and c.future is None)
            pump(c, 0.5)
            assert store.current(2) is None
            assert (
                c.window.pid == pid and c.window.window == window and c.window.owned()
            )
            assert len(games()) == 1
            assert c.model.draft.seed != seed
            after_streams = pulse_inputs(pid)
            report["events"].append(
                {
                    "clear_slot": 2,
                    "same_menu_pid": pid,
                    "same_window": window,
                    "audio_streams_before": streams,
                    "audio_streams_after": after_streams,
                    "audio_not_restarted": bool(streams) and streams == after_streams,
                }
            )
            capture.snap(c.window, "native-cleared-slot2")
            report["passed"] = True
        except BaseException as error:
            report["error"] = repr(error)
            try:
                capture.snap(
                    c.window if c.window.owned() else c.runtime,
                    "native-lifecycle-failure",
                )
            except Exception:
                pass
            raise
        finally:
            c.close()
            (OUT / "native-lifecycle-results.json").write_text(
                json.dumps(report, indent=2) + "\n"
            )
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    main()
