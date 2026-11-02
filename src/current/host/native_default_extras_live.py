"""Default exported game: actual death, native character change and F2 resume."""

import json, time, uuid
from export_route_probe import ROOT
from menu_host.store import Store, save, digest
from menu_host.draft import Draft
from menu_host.runtime import Runtime
from native_menu.observe import objects
from gameplay.native_extras import STATE, GROUP
import god_mode_live as capture

OUT = ROOT / "outputs/Fusion-NativeExtras-20261025"


def main():
    capture.OUT = OUT
    s = Store(OUT / ("default-profile-" + uuid.uuid4().hex[:8]))
    report = dict(scope=__doc__, memory_writes=0)
    with s.lock():
        d = Draft()
        d.update(
            level_pool=["save1.ini"],
            level_count=1,
            boss_pool=[],
            route_boss_count=0,
            god_mode=True,
            no_mouse_ghost=True,
            start_character="Kirby",
            mirror=True,
            death_character=True,
        )
        d.seed = "0000001D"
        s.create(1, d)
        r = Runtime(s)
        try:
            report["frame"] = r.start(1)
            time.sleep(0.6)
            report["sha256"] = digest(r.folder / "Boshy.exe")
            capture.snap(r, "default-mirror-initial")
            # Mirror is applied in the native option object's memory, not saved
            # into the user's options.ini. Its source value is run-local.
            assert save(r.folder / "SaveFile1.ini").getint(GROUP, "Mirror") == 1
            r.key("q")
            time.sleep(0.65)
            r.key("r")
            time.sleep(0.65)
            p = save(r.folder / "onlineLicense.ini")
            assert p.getint(STATE, "Sequence") == 1
            assert p.get("License", "CharacterName") == "Megaman"
            assert "ONMegaman" in [o["name"] for o in objects(r.reader)]
            report["after_death"] = dict(
                character=p.get("License", "CharacterName"),
                sequence=p.getint(STATE, "Sequence"),
            )
            capture.snap(r, "default-mirror-after-death")
            r.key("F2")
            end = time.monotonic() + 12
            while time.monotonic() < end and r.poll() != "menu":
                time.sleep(0.1)
            assert not s.active
            r.start(1)
            time.sleep(0.7)
            p = save(r.folder / "onlineLicense.ini")
            assert p.getint(STATE, "Sequence") == 1
            assert "ONMegaman" in [o["name"] for o in objects(r.reader)]
            report.update(resumed_unchanged=True, passed=True)
        except BaseException as error:
            report["error"] = repr(error)
            raise
        finally:
            r.close()
            (OUT / "default-live-results.json").write_text(
                json.dumps(report, indent=2) + "\n"
            )
    print(json.dumps(report))


if __name__ == "__main__":
    main()
