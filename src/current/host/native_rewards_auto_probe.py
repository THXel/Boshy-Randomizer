"""A default-character run can persist a randomized character unlock locally."""

import json, uuid
from native_rewards_live import OUT, run_case
from menu_host.store import Store
from menu_host.draft import Draft
from menu_host.runtime import Runtime
from native_pickups_live import dialogs, close_dialog
import god_mode_live as capture


def main():
    report = dict(scope=__doc__, memory_writes=0, cases=[])
    capture.OUT = OUT / "auto-character"
    capture.OUT.mkdir(exist_ok=True)
    s = Store(OUT / ("auto-profile-" + uuid.uuid4().hex[:6]))
    with s.lock():
        d = Draft()
        d.update(
            items=True,
            sprite_scenery=True,
            sprite_backgrounds=True,
            sprite_actors=True,
            level_pool=["save1.ini"],
            level_count=1,
            boss_pool=[],
            route_boss_count=0,
            god_mode=True,
            no_mouse_ghost=True,
            fast_chests=True,
            quiet_pickups=True,
        )
        d.seed = "0000001D"
        s.create(1, d)
        folder = s.folder(1)
        assert json.loads((folder / "plan.json").read_text())["start_character"] is None
        r = Runtime(s)
        try:
            run_case(s, r, folder, "cd", True, True, report)
            report["passed"] = True
        except BaseException as e:
            report["error"] = repr(e)
            raise
        finally:
            for row in dialogs(r) if r.pid else []:
                close_dialog(row)
            if s.active:
                r.close("auto-reward-cleanup")
            (OUT / "auto-live-results.json").write_text(
                json.dumps(report, indent=2) + "\n"
            )


if __name__ == "__main__":
    main()
