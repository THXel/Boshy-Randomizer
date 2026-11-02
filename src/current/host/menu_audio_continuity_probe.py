"""Record only the menu-owned PulseAudio stream across a real slot deletion."""
import json, subprocess, time, tkinter as tk
from pathlib import Path
import numpy as np
from menu_host.store import Store
from menu_host.draft import Draft
from menu_host.ui import Menu
from music.continuity import decoded, match
from export_route_probe import ROOT

OUT = ROOT / "outputs/Fusion-MenuAudio-20261024"

def pulse(kind):
    return json.loads(subprocess.check_output(["pactl", "--format=json", "list", kind]))

def main():
    store = Store(OUT / "continuity-profile")
    report = {"scope": __doc__}
    with store.lock():
        if not store.current(1):
            draft = Draft()
            draft.update(level_pool=["save1.ini"], level_count=1, boss_pool=[], route_boss_count=0)
            store.create(1, draft)
        root = tk.Tk()
        menu = Menu(root, store)
        recorder = None
        raw_path = OUT / "menu-only.s16le"
        def pump(seconds):
            until = time.monotonic() + seconds
            while time.monotonic() < until:
                root.update()
                time.sleep(.02)
        try:
            pump(1.5)
            assert menu.audio.process and menu.audio.process.poll() is None, menu.audio.error
            pid = menu.audio.process.pid
            inputs = [v for v in pulse("sink-inputs") if str(v["properties"].get("application.process.id")) == str(pid)]
            assert len(inputs) == 1, inputs
            stream = inputs[0]
            sink = next(s for s in pulse("sinks") if s["index"] == stream["sink"])
            report["stream"] = {"pid": pid, "input": stream["index"], "sink": sink["name"]}
            with raw_path.open("wb") as output:
                recorder = subprocess.Popen(["parec", "--monitor-stream=" + str(stream["index"]),
                    "--device=" + sink["monitor_source"], "--format=s16le", "--rate=22050", "--channels=2", "--raw"],
                    stdout=output, stderr=subprocess.PIPE)
                started = time.monotonic()
                pump(2.5)
                report["delete_started"] = time.monotonic() - started
                menu.widgets["delete"].invoke()
                assert menu.loading.active
                pump(3.5)
                assert not menu.future and not store.current(1), menu.error
                assert menu.audio.process.pid == pid and menu.audio.starts == 1 and menu.audio.stops == 0
                report["delete_completed"] = True
                recorder.terminate()
                recorder.wait(timeout=3)
            signal = np.frombuffer(raw_path.read_bytes(), dtype="<i2").reshape(-1, 2).mean(axis=1)[::5] / 32768
            reference = decoded(menu.audio.path.read_bytes())
            start = int(.5 * 4410)
            end = len(signal) - int(1.3 * 4410)
            width = int(.7 * 4410)
            before = match(reference, signal[start:start+width])
            after = match(reference, signal[end:end+width])
            elapsed = (end-start) / 4410
            advance = (after["reference_seconds"] - before["reference_seconds"]) % (len(reference)/4410)
            report.update(before=before, after=after, elapsed=elapsed, advance=advance, advance_error=abs(elapsed-advance),
                          same_pid=True, starts=menu.audio.starts, stops=menu.audio.stops)
            report["passed"] = min(before["correlation"], after["correlation"]) > .8 and abs(elapsed-advance) < .08
            assert report["passed"], report
        finally:
            if recorder and recorder.poll() is None:
                recorder.terminate()
                recorder.wait(timeout=3)
            menu.audio.close()
            menu.executor.shutdown(wait=True)
            root.destroy()
            (OUT / "continuity-results.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))

if __name__ == "__main__":
    main()
