"""Owned X11 window geometry and focus-aware borderless presentation.

No monitor mode changes. A black backing window fills unused aspect-ratio space
and disappears on focus loss, close, or host disconnect.
"""

import re
import os
from pathlib import Path
import subprocess
from Xlib import X, display as xdisplay


def monitors():
    result = subprocess.run(
        ["xrandr", "--listactivemonitors"],
        text=True,
        capture_output=True,
        check=True,
        timeout=3,
    )
    found = []
    for line in result.stdout.splitlines()[1:]:
        m = re.search(r"(\d+)/\d+x(\d+)/\d+([+-]\d+)([+-]\d+)", line)
        if m:
            w, h, x, y = map(int, m.groups())
            found.append((x, y, w, h))
    if not found:
        raise RuntimeError("No active display geometry")
    return found


class Backing:
    def __init__(self, window, monitor):
        self.connection = xdisplay.Display()
        d = self.connection
        self.root = d.screen().root
        self.native = d.create_resource_object("window", int(window.window, 16))
        x, y, width, height = monitor
        self.matte = self.root.create_window(
            x,
            y,
            width,
            height,
            0,
            X.CopyFromParent,
            X.InputOutput,
            X.CopyFromParent,
            background_pixel=d.screen().black_pixel,
            override_redirect=True,
            event_mask=0,
        )
        self.matte.set_wm_name("Boshy Randomizer presentation backing")
        self.active = d.intern_atom("_NET_ACTIVE_WINDOW")
        self.shown = False
        d.flush()

    def tick(self):
        d = self.connection
        p = self.root.get_full_property(self.active, X.AnyPropertyType)
        focused = bool(p is not None and len(p.value) and p.value[0] == self.native.id)
        if focused:
            # Reparenting window managers put the client inside their frame.
            sibling = self.native
            while True:
                parent = sibling.query_tree().parent
                if parent.id == self.root.id:
                    break
                sibling = parent
            if not self.shown:
                self.matte.map()
            self.matte.configure(sibling=sibling, stack_mode=X.Below)
        elif self.shown:
            self.matte.unmap()
        self.shown = focused
        d.flush()

    def close(self):
        self.matte.destroy()
        self.connection.flush()
        self.connection.close()


def release(window):
    backing = getattr(window, "presentation_backing", None)
    if backing:
        window.presentation_backing = None
        backing.close()


def tick(window):
    backing = getattr(window, "presentation_backing", None)
    if backing:
        if window.owned():
            backing.tick()
        else:
            release(window)


def apply(window, settings):
    if not window.owned():
        raise RuntimeError("Owned display window disappeared")
    release(window)
    d = xdisplay.Display()
    try:
        native = d.create_resource_object("window", int(window.window, 16))
        g = native.get_geometry()
        pos = d.screen().root.translate_coords(native, 0, 0)
        cx, cy = pos.x + g.width // 2, pos.y + g.height // 2
        screens = monitors()
        x, y, w, h = next(
            (
                m
                for m in screens
                if m[0] <= cx < m[0] + m[2] and m[1] <= cy < m[1] + m[3]
            ),
            screens[0],
        )
        area = (w, h) if settings.fullscreen else (max(1, w - 32), max(1, h - 88))
        width, height = settings.fit(area)
        from menu_host.runtime import WINE
        from build_profiles import PREFIX

        subprocess.run(
            [
                "wmctrl",
                "-ir",
                window.window,
                "-b",
                "remove,maximized_vert,maximized_horz",
            ],
            check=True,
            timeout=3,
        )
        d.sync()
        subprocess.run(
            [
                WINE,
                str(Path(__file__).with_name("window_style.exe")),
                "C:\\BoshySceneTests\\" + window.folder.name + "\\Boshy.exe",
                "borderless" if settings.fullscreen else "restore",
                str(x + (w - width) // 2),
                str(y + (h - height) // 2),
                str(width),
                str(height),
            ],
            env={**os.environ, "WINEPREFIX": str(PREFIX), "WINEDEBUG": "-all"},
            check=True,
            timeout=8,
            stdout=subprocess.DEVNULL,
        )
        d.sync()
        if settings.fullscreen:
            window.presentation_backing = Backing(window, (x, y, w, h))
            window.presentation_backing.tick()
        return dict(
            requested=list(settings.size),
            applied=[width, height],
            monitor=[x, y, w, h],
            aspect=settings.aspect,
            fullscreen=settings.fullscreen,
        )
    finally:
        d.close()
