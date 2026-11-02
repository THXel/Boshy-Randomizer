"""Real title/save-page tracker clicks; read-only engine observations."""

import json
import subprocess
import time
import uuid
from export_route_probe import ROOT
from menu_host.store import Store, digest
from native_menu import builds
from native_menu.combined import CombinedController
from native_menu.observe import objects
from native_menu_probe import pump
from god_mode_boss_probe import values
from tracker import server
import god_mode_live as capture

OUT = ROOT / "outputs/Fusion-TrackerMenu-20261025"


def main():
    candidate = builds.PREFIX / "drive_c/BoshyTransitions/Boshy-dynamic-v25.exe"
    builds.DYNAMIC_BASE, builds.DYNAMIC_SHA = candidate, digest(candidate)
    requests = []
    original = server.Handler.do_GET

    def record(handler):
        requests.append(handler.path)
        return original(handler)

    server.Handler.do_GET = record
    service = server.start()
    assert service is not None, "Use owned tracker server for request evidence"
    capture.OUT = OUT
    report = dict(
        build=str(candidate), sha256=digest(candidate), memory_writes=0, checks=[]
    )
    store = Store(OUT / ("menu-profile-" + uuid.uuid4().hex[:8]))
    with store.lock():
        c = CombinedController(store, dynamic=True)
        try:
            c.open()
            deadline = time.monotonic() + 35
            while c.window.reader.frame() != "Title Screen":
                assert time.monotonic() < deadline
                c.window.key("Return")
                pump(c, 0.5)
            pump(c, 12)
            for page in ("initial", "main", "saves"):
                if page == "main":
                    capture.point(c.window, 600, 100)
                    c.window.key("Return")
                    deadline = time.monotonic() + 35
                    while True:
                        trigger = next(
                            o
                            for o in objects(c.window.reader)
                            if o["name"] == "MenuTrigger"
                        )
                        if values(c.window.reader, trigger, 2)[1] == -1:
                            break
                        assert time.monotonic() < deadline, (
                            "Main menu animation did not finish"
                        )
                        pump(c, 0.2)
                    pump(c, 0.4)
                if page == "saves":
                    c.enter()
                    pump(c, 0.7)
                trigger = next(
                    o for o in objects(c.window.reader) if o["name"] == "MenuTrigger"
                )
                trigger_values = values(c.window.reader, trigger, 2)
                report[page + "_objects"] = [
                    dict(o, values=values(c.window.reader, o, 10))
                    for o in objects(c.window.reader)
                    if o["name"] in ("MenuTrigger", "Randomizer Panel")
                ]
                print(page, report[page + "_objects"], flush=True)
                before = (c.model.slot, c.model.draft.shared(), c.model.page)
                capture.point(c.window, 600, 100)
                pump(c, 0.2)
                capture.snap(c.window, page + "-menu")
                roots = requests.count("/")
                capture.point(c.window, 72, 46)
                pump(c, 0.2)
                subprocess.run(["xdotool", "mousedown", "1"], check=True)
                pump(c, 0.15)
                subprocess.run(["xdotool", "mouseup", "1"], check=True)
                deadline = time.monotonic() + 15
                while requests.count("/") <= roots and time.monotonic() < deadline:
                    pump(c, 0.2)
                assert requests.count("/") > roots, (page, requests)
                pump(c, 1)
                titles = subprocess.check_output(
                    ["wmctrl", "-l"], text=True
                ).splitlines()
                tracker_titles = [t for t in titles if "Live Tracker" in t]
                assert tracker_titles, titles
                assert before == (c.model.slot, c.model.draft.shared(), c.model.page)
                report["checks"].append(
                    dict(
                        page=page,
                        trigger=trigger_values,
                        native_browser_request=True,
                        menu_unchanged=True,
                        browser_titles=tracker_titles,
                    )
                )
                print("PASS", page, flush=True)
            report["passed"] = True
        except BaseException as error:
            report["error"] = repr(error)
            raise
        finally:
            c.close()
            server.stop(service)
            report["requests"] = requests
            (OUT / "live-results.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
