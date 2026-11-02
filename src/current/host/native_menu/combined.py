"""Classic three-slot menu and gameplay in one persistent game process.

The host prepares validated saves and panels. Native events handle play and
asset selection; working-copy transactions own start, return and recovery.
"""

import configparser
import time
from native_menu.classic import ClassicController, BASE_SHA
from native_menu.transport import read
from native_menu.unified import read_session
from native_menu.session_store import WorkingSession
from menu_host.runtime import MENU_FRAMES


class CombinedController(ClassicController):
    def __init__(self, store, *, dynamic=False):
        self.recovery = WorkingSession.recover(store)
        self.dynamic = dynamic
        if dynamic:
            from native_menu.builds import DYNAMIC_BASE, DYNAMIC_SHA
            from gameplay.runtime_reward_icons import prepare

            super().__init__(store, base=DYNAMIC_BASE, expected=DYNAMIC_SHA)
            prepare(self.folder)
            expected = DYNAMIC_SHA
        else:
            super().__init__(store)
            expected = BASE_SHA
        self.session = WorkingSession(self.folder, store, expected)
        self.phase = "menu"
        self.active_slot = None
        self.events = []
        self.mail.session_begin = 0
        self.mail.publish()
        from tracker.publisher import Publisher

        self.tracker = Publisher(store)
        from native_menu.results import Completion

        self.completion = Completion(self)
        from native_menu.diagnostics import Diagnostics

        self.diagnostics = Diagnostics(self)
        from native_menu.presentation import Presentation

        self.presentation = Presentation(self)

    def open(self):
        super().open()
        self.tracker.tick(self, force=True)

    def compatible_draft(self):
        from native_menu import builds

        d = self.model.draft
        ex = d.options["extras"]
        return not (
            (
                (d.options["items"] or ex["mirror"] or ex["death_character"])
                and not self.dynamic
            )
            or (
                ex.get("shot_mode", "off") != "off"
                and not (self.dynamic and builds.DYNAMIC_SHOTS)
            )
            or (
                ex.get("spider", False) and not (self.dynamic and builds.DYNAMIC_SPIDER)
            )
            or (ex["music"] and not self.dynamic)
            or (
                ex.get("no_screen_shaking", False)
                and not (self.dynamic and builds.DYNAMIC_SCREEN_SHAKE)
            )
            or (ex["sprite_scenery"] and not (self.dynamic and builds.DYNAMIC_SCENERY))
            or (d.blood_pack != "original" and not self.dynamic)
        )

    def action(self, action):
        if action == "new" and not self.compatible_draft():
            self.failure(action, ValueError("Dynamic asset bank integration pending"))
            self.mail.publish()
            return
        return super().action(action)

    def begin(self):
        if not self.compatible_draft():
            raise ValueError(
                "Diese Einstellungen sind für diesen Testmodus noch nicht verfügbar."
            )
        self.model.loading_progress = (94, "start")
        self.mail.publish(state=False)
        self.completion.reset()
        slot = self.model.slot
        from native_menu.display import prepare_options

        prepare_options(self.store.folder(slot), self.model.display)
        from menu_host.store import atomic, RC4
        from native_menu.preferences import read_native_settings as read_options
        import io

        intro = read_options(self.folder / "options.ini").getint(
            "Options", "IntroVariant", fallback=-1
        )
        self.session.stage(slot)
        cfg = read_options(self.folder / "options.ini")
        cfg["Options"]["IntroVariant"] = str(intro)
        stream = io.StringIO()
        cfg.write(stream)
        atomic(
            self.folder / "options.ini",
            RC4(b"BLOB", stream.getvalue().encode("latin1")),
        )
        import json

        self.model.loading_progress = (97, "music")
        self.mail.publish(state=False)
        self.presentation.prepare(
            json.loads((self.store.folder(slot) / "plan.json").read_text())
        )
        state = read_session(self.folder)
        self.active_slot = slot
        self.store.active = slot
        self.phase = "starting"
        self.deadline = time.monotonic() + 20
        self.model.busy = False
        self.model.go("home")
        self.mail.session_begin = state.getint("Session", "Accepted", fallback=0) + 1
        # Establish owned rewards before the engine can collect an entry chest.
        self.tracker.tick(self, force=True)
        self.mail.publish()
        self.events.append(dict(event="request", slot=slot, pid=self.window.pid))

    def returned(self):
        self.completion.reset()
        self.session.commit()
        self.store.active = None
        self.phase = "menu"
        self.model.slot = self.active_slot
        self.model.busy = False
        self.model.go("home")
        self.model.load_slot()
        self.preview_signature = None
        self.refresh_slots()
        self.mail.publish()
        self.events.append(
            dict(event="returned", slot=self.active_slot, pid=self.window.pid)
        )
        self.active_slot = None

    def tick(self):
        try:
            self._tick()
        finally:
            self.tracker.tick(self)
            self.completion.tick()

    def _tick(self):
        self.loading_tick()
        self.sync_display()
        self.presentation.tick()
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
                    raise TimeoutError("Native entry timed out; working files retained")
                return
            if self.phase == "starting":
                if frame not in MENU_FRAMES:
                    self.phase = "playing"
                    self.events.append(
                        dict(
                            event="playing",
                            slot=self.active_slot,
                            pid=self.window.pid,
                            frame=frame,
                        )
                    )
                elif read_session(self.folder).getint("Session", "Status") == 3:
                    self.session.abandon_unstarted()
                    self.store.active = None
                    self.active_slot = None
                    self.phase = "menu"
                    self.failure(
                        "native-entry",
                        ValueError("Native save validation rejected entry"),
                    )
                    self.mail.publish()
                elif time.monotonic() > self.deadline:
                    raise TimeoutError("Native entry timed out; working files retained")
            elif frame in MENU_FRAMES:
                self.returned()
            return
        if self.future and self.future.done():
            future, op = self.future, self.operation
            self.future = None
            try:
                future.result()
                if op != "delete":
                    self.begin()
                    return
                self.model.fresh_draft()
                self.model.message = ""
                self.preview_signature = None
                self.refresh_slots()
            except Exception as error:
                self.failure(op, error)
            self.model.busy = False
            self.mail.publish()
        if not self.future:
            self.refresh_slots()
            if self.model.page == "home" and time.monotonic() - self.last_sync > 0.08:
                self.last_sync = time.monotonic()
                try:
                    slot = read(self.folder / "native-input.ini").get("slot")
                except (OSError, ValueError, KeyError, configparser.Error):
                    slot = None
                if slot in (1, 2, 3) and slot != self.model.slot:
                    self.model.slot = slot
                    self.model.load_slot()
                    self.mail.publish()
        if not self.model.busy and self.mail.poll():
            action = self.model.action
            self.model.action = None
            if action:
                self.action(action)

    def close(self):
        self.closed = True
        self.pool.shutdown(wait=True)
        self.diagnostics.close()
        self.window.close()
        self.tracker.close(self)
        try:
            if self.session.slot is not None:
                self.session.commit()
        finally:
            self.store.active = None
            if self.clipboard:
                self.clipboard.close()
        from menu_host.cleanup import finished

        finished(self.folder, self.store.root)
