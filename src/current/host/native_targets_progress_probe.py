"""Read-only native goal display against real collected-item/boss receipts."""

import json
from menu_host.store import Store
from native_menu.controller import Controller
from native_menu_probe import snapshot, key, capture
from native_menu_options_probe import choose, page
from native_targets_live import OUT


def main():
    capture.OUT = OUT
    evidence = json.loads((OUT / "boss-live-results.json").read_text())
    folder = __import__("pathlib").Path(evidence["folder"])
    root = next(
        p.parent
        for p in OUT.glob("pickup-gated-*/slot-1.json")
        if json.loads(p.read_text())["run"] == folder.name
    )
    s = Store(root)
    report = dict(languages=[], memory_writes=0)
    with s.lock():
        c = Controller(s)
        try:
            c.open()
            c.enter()
            original = c.model.draft.shared()
            for language in ("de", "en", "es", "ru", "ja"):
                if language != "de":
                    page(c, "settings")
                    choose(c, "language")
                assert c.model.language == language
                page(c, "targets")
                rows = c.model.rows()
                assert len(rows) == 2 and all(
                    row.value == "✓" and row.enabled for row in rows
                )
                key(c, "Return")
                assert c.model.draft.shared() == original and c.model.action is None
                snapshot(c, "target-completed-goals-" + language)
                report["languages"].append(language)
            report.update(passed=True, completed_items=1, completed_bosses=1)
        except BaseException as error:
            report["error"] = repr(error)
            raise
        finally:
            c.close()
            (OUT / "progress-menu-results.json").write_text(
                json.dumps(report, indent=2) + "\n"
            )
    print(json.dumps(report), flush=True)


if __name__ == "__main__":
    main()
