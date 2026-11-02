"""Observe the original-style intro, click its updated native website and inspect title."""

import json
import subprocess
import time
import uuid
from export_route_probe import ROOT
from menu_host.store import Store
from native_menu.classic import ClassicController
from native_menu.observe import objects
from native_menu_probe import pump
import god_mode_live as capture

OUT = ROOT / "outputs/Fusion-Attribution-20261025"


def main():
    OUT.mkdir(exist_ok=True)
    capture.OUT = OUT
    report = dict(scope=__doc__, frames=[], memory_writes=0)
    s = Store(OUT / ("profile-pixel-" + uuid.uuid4().hex[:8]))
    with s.lock():
        c = ClassicController(s)
        try:
            c.open()
            report["game_sha256"] = __import__(
                "menu_host.store", fromlist=["digest"]
            ).digest(c.folder / "Boshy.exe")
            start = time.monotonic()
            clicked = False
            while time.monotonic() - start < 4:
                c.tick()
                try:
                    current_frame = c.window.reader.frame()
                except RuntimeError:
                    if clicked:
                        break
                    time.sleep(0.05)
                    continue
                if current_frame != "JAE Intro":
                    break
                obs = objects(c.window.reader, types=(2, 3))
                wordmark = next(
                    (o for o in obs if o["name"] == "Intro - Solgryn.org"), None
                )
                if wordmark is None:
                    break
                assert (wordmark["w"], wordmark["h"]) == (208, 63), wordmark
                assert not any(o["name"] == "Randomizer Attribution" for o in obs)
                n = len(report["frames"])
                name = f"pixel-intro-{n:02d}"
                capture.snap(c.window, name)
                report["frames"].append(
                    dict(screenshot=name + ".png", wordmark=wordmark)
                )
                if n == 3:
                    from native_menu.pixel_wordmark import rectangles, WIDTH

                    px, py, _, _ = next(rectangles())
                    x = wordmark["x"] - WIDTH // 2 + px + 1
                    y = wordmark["y"] + py + 1
                    capture.point(c.window, x, y)
                    subprocess.run(["xdotool", "click", "1"], check=True)
                    clicked = True
                    report["native_website_click"] = dict(x=x, y=y)
                time.sleep(0.12)
            assert clicked, "Intro ended before link test"
            # Leave the opened browser for explicit address verification.
            time.sleep(1)
            c.enter()
            pump(c, 0.4)
            capture.snap(c.window, "main-menu-without-credit-card")
            report["intro_and_menu_passed"] = True
        except BaseException as e:
            report["error"] = repr(e)
            raise
        finally:
            c.close()
            (OUT / "pixel-live-results.json").write_text(
                json.dumps(report, indent=2) + "\n"
            )
    print(
        json.dumps(
            dict(intro_captures=len(report["frames"]), browser_verification="pending")
        )
    )


if __name__ == "__main__":
    main()
