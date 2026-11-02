"""Private prepared-run adapter for the combined menu/game executable.

Fusion owns start/respawn/menu transitions. Python still prepares assets, renders
panels and handles settings navigation. Creating/replacing runs inside a running
application is deliberately not exposed until native asset selection exists.
"""

import time
import configparser
from dataclasses import replace
from native_menu.controller import Controller
from native_menu.model import Model
from native_menu.render import Renderer
from native_menu.transport import Mailbox
from native_menu.window import Window
from menu_host.store import save
from menu_host.runtime import MENU_FRAMES
from visuals.scenery_pack import UNIFIED_BASE_SHA


def read_session(folder, timeout=2):
    """INI++ saves in place; tolerate only a bounded partial disk write."""
    end = time.monotonic() + timeout
    while True:
        try:
            state = save(folder / "native-session.ini")
            if state.getint("Session", "Schema") != 1:
                raise ValueError("Unsupported native session")
            state.getint("Session", "Accepted", fallback=0)
            state.getint("Session", "Status")
            return state
        except (OSError, ValueError, configparser.Error):
            if time.monotonic() >= end:
                raise
            time.sleep(0.01)


class PreparedModel(Model):
    def key(self, key, x=0, y=0):
        if key == 46:
            return  # The Delete shortcut must respect the disabled slot action.
        return super().key(key, x, y)

    def rows(self):
        rows = super().rows()
        if self.page == "home":
            rows = [
                (
                    replace(r, enabled=False)
                    if r.key in ("new", "delete") or r.key.startswith("slot:")
                    else r
                )
                for r in rows
            ]
        return rows


class PreparedController(Controller):
    def __init__(self, store, slot=1):
        self.store = store
        self.folder, plan, _ = store.resume(slot)
        if (
            plan.get("unified_schema") != 1
            or plan.get("unified_base_sha256") != UNIFIED_BASE_SHA
        ):
            raise ValueError("This run has no verified combined application")
        self.model = PreparedModel(store)
        self.model.slot = slot
        self.model.load_slot()
        self.model.focus = 4
        self.renderer = Renderer(self.folder)
        self.window = Window(self.folder)
        self.clipboard = None
        self.closed = False
        self.phase = "menu"
        self.reset_mail()

    def reset_mail(self):
        path = self.folder / "native-session.ini"
        accepted = (
            read_session(self.folder).getint("Session", "Accepted", fallback=0)
            if path.exists()
            else 0
        )
        self.mail = Mailbox(
            self.folder, self.renderer, self.model, session_begin=accepted
        )

    def open(self):
        self.window.launch()

    def action(self, action):
        if action in ("exit", "copy", "import"):
            return super().action(action)
        if action != "resume":
            raise ValueError(
                "Prepared runs cannot be replaced while the application is open"
            )
        self.store.resume(self.model.slot)
        self.store.active = self.model.slot
        self.mail.session_begin += 1
        self.mail.publish()
        self.phase = "starting"
        self.deadline = time.monotonic() + 15

    def tick(self):
        if self.clipboard:
            self.clipboard.pump()
        if not self.window.owned():
            self.closed = True
            return
        if self.phase in ("starting", "playing"):
            try:
                frame = self.window.reader.frame()
            except RuntimeError:
                if self.phase == "starting" and time.monotonic() > self.deadline:
                    raise TimeoutError("Native run entry timed out")
                return
            if self.phase == "starting":
                if frame not in MENU_FRAMES:
                    self.phase = "playing"
                else:
                    state = read_session(self.folder)
                    if state.getint("Session", "Status", fallback=0) == 3:
                        self.store.active = None
                        self.phase = "menu"
                        self.model.message = self.model.t("operation_failed")
                        self.mail.publish()
                    elif time.monotonic() > self.deadline:
                        raise TimeoutError("Native run entry timed out")
                return
            if frame in MENU_FRAMES:
                self.store.active = None
                self.store.resume(self.model.slot)
                self.phase = "menu"
                self.model.go("home")
                self.model.load_slot()
                self.model.focus = 4
                self.reset_mail()
                self.enter()
            return
        if self.mail.poll():
            action = self.model.action
            self.model.action = None
            if action:
                self.action(action)

    def close(self):
        self.closed = True
        self.window.close()
        self.store.active = None
        if self.clipboard:
            self.clipboard.close()
        self.store.resume(self.model.slot)
