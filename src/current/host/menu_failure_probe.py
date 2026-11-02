"""Real Wine startup-failure recovery plus Q/F2/resume regression.

The windowless-child case uses a controlled Python sleeper, not a game hang.
Observer failure is injected after a real native game window has opened.
"""

import json, subprocess, sys, time
from pathlib import Path
from unittest.mock import patch
from menu_host.store import Store, digest
from menu_host.runtime import Runtime, windows, WINE
from menu_host.processes import games
from menu_host.draft import Draft
from export_route_probe import ROOT

OUT = ROOT / "outputs/Fusion-Lifecycle-Fix-20261024"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    report = {"scope": __doc__, "checks": []}
    store = Store(OUT / "profile")
    with store.lock():
        if not store.current(1):
            draft = Draft()
            draft.update(
                level_pool=["save1.ini"],
                level_count=1,
                boss_pool=["hellokitty"],
                route_boss_count=1,
            )
            store.create(1, draft)
        folder = store.folder(1)
        exe = digest(folder / "Boshy.exe")
        original = store.summary(1)
        runtime = Runtime(store)
        child = None
        try:
            # A real owned child, deliberately no window or Wine process.
            popen = subprocess.Popen

            def headless(*args, **kwargs):
                nonlocal child
                if args and args[0][0] != WINE:
                    return popen(*args, **kwargs)
                child = popen(
                    [sys.executable, "-c", "import time; time.sleep(60)", "Boshy.exe"],
                    cwd=folder,
                    start_new_session=True,
                )
                return child

            with patch(
                "menu_host.runtime.subprocess.Popen", side_effect=headless
            ), patch("menu_host.runtime.OPEN_TIMEOUT", 0):
                try:
                    runtime.start(1)
                    raise AssertionError("Expected timeout")
                except RuntimeError as error:
                    assert str(error) == "Game did not open", str(error)
            assert child.poll() is not None and store.active is None and not games()
            report["checks"].append(
                {
                    "test": "windowless owned child stopped after startup timeout",
                    "passed": True,
                    "kind": "controlled child",
                }
            )

            # A pre-existing headless lab game must block any second launch.
            child = headless()
            try:
                assert child.pid in games(), games()
                try:
                    runtime.start(1)
                    raise AssertionError("Expected launch refusal")
                except RuntimeError:
                    pass
                assert games() == {child.pid: folder}
                report["checks"].append(
                    {
                        "test": "pre-existing windowless process blocks second launch",
                        "passed": True,
                        "kind": "controlled child",
                    }
                )
            finally:
                child.terminate()
                child.wait(timeout=5)

            with patch(
                "menu_host.runtime.Reader",
                side_effect=TimeoutError("injected observer startup failure"),
            ):
                try:
                    runtime.start(1)
                    raise AssertionError("Expected observer failure")
                except TimeoutError as error:
                    assert str(error) == "injected observer startup failure"
            time.sleep(1)
            assert store.active is None and not windows() and not games()
            report["checks"].append(
                {
                    "test": "real Wine window closed after observer initialization failure",
                    "passed": True,
                    "kind": "native game with injected observer error",
                }
            )

            frame = runtime.start(1)
            assert frame == "First World - Prehistorik", frame
            observed = games()
            assert runtime.pid in observed and observed[runtime.pid] == folder
            assert len(windows()) == 1
            before = store.summary(1)
            runtime.key("q")
            time.sleep(2)
            runtime.key("r")
            time.sleep(1)
            runtime.key("F2")
            end = time.monotonic() + 15
            while time.monotonic() < end and runtime.poll() != "menu":
                time.sleep(0.2)
            after = store.summary(1)
            assert store.active is None and not games() and not windows()
            assert after["deaths"] > before["deaths"]
            assert after["seed"] == original["seed"]
            report["checks"].append(
                {
                    "test": "native Q death, restart and F2 return after recovered launch",
                    "passed": True,
                    "kind": "native game",
                    "before": before,
                    "after": after,
                    "observed_pids": list(observed),
                }
            )

            runtime = Runtime(store)
            frame = runtime.start(1)
            assert frame == "First World - Prehistorik"
            assert store.summary(1)["deaths"] == after["deaths"]
            runtime.close("probe-menu-button")
            assert store.active is None and not windows() and not games()
            assert digest(folder / "Boshy.exe") == exe
            report["checks"].append(
                {
                    "test": "fresh runtime resumes same seed/deaths and closes normally",
                    "passed": True,
                    "kind": "native game",
                }
            )
            report["passed"] = True
        finally:
            if child is not None and child.poll() is None:
                child.terminate()
                child.wait(timeout=5)
            if store.active:
                runtime.close("probe-cleanup")
            (OUT / "live-results.json").write_text(json.dumps(report, indent=2) + "\n")
    print(
        "PASS: 3 native Wine launches, 2 controlled windowless cases; no games left",
        flush=True,
    )


if __name__ == "__main__":
    main()
