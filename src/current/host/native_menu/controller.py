"""Headless menu/run lifecycle. Fusion owns all visible UI and menu audio."""

import concurrent.futures, configparser, json, shutil, time, uuid
from native_menu.model import Model
from native_menu.render import Renderer
from native_menu.transport import Mailbox
from native_menu.window import Window
from menu_host.runtime import Runtime, verify_engine
from menu_host.store import RUNS, atomic
from build_profiles import PREFIX
from native_menu.observe import objects, values

BASE = PREFIX / "drive_c/BoshyTransitions/Boshy-native-menu-v7.exe"

BASE_SHA256 = "39d195d6e75f654f1cffad8da1917497cc3b9f0c718fa71fdc8224227cdb5331"


class Controller:
    def __init__(self, store, base=BASE):
        if base == BASE:
            verify_engine(base, BASE_SHA256)
        self.store = store
        self.model = Model(store)
        self.base = base
        self.folder = RUNS / ("rebuilt-menu-" + uuid.uuid4().hex)
        self.folder.mkdir()
        from menu_host.cleanup import started

        started(self.folder, store.root)
        shutil.copy2(base, self.folder / "Boshy.exe")
        self.renderer = Renderer(self.folder)
        self.mail = Mailbox(self.folder, self.renderer, self.model)
        self.window = Window(self.folder)
        self.runtime = Runtime(store)
        self.future = None
        self.operation = None
        self.pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        self.closed = False
        self.clipboard = None
        self.name_future = None
        from queue import SimpleQueue
        self.loading_events = SimpleQueue()

    def open(self):
        self.mail = Mailbox(self.folder, self.renderer, self.model)
        from native_menu.display import prepare_options

        prepare_options(self.folder, self.model.display)
        self.window.launch()
        self.apply_display()

    def apply_display(self):
        from native_menu.display_window import apply

        self.display_state = apply(self.window, self.model.display)

    def enter(self):
        """Exercise the existing intro/Game entry using normal key presses."""
        end = time.monotonic() + 35
        last = 0
        while time.monotonic() < end:
            try:
                if self.window.reader.frame() == "Title Screen":
                    panel = next(
                        (
                            o
                            for o in objects(self.window.reader)
                            if o["name"] == "Randomizer Panel"
                        ),
                        None,
                    )
                    if panel and values(self.window.reader, panel, 2)[1] == 1:
                        time.sleep(0.12)
                        self.mail.discard_entry()
                        return
                    trigger = next(
                        (
                            o
                            for o in objects(self.window.reader)
                            if o["name"] == "MenuTrigger"
                        ),
                        None,
                    )
                    if trigger and values(self.window.reader, trigger, 2)[1] == 0:
                        # Stop sending Return once on the original save page.
                        # A missing custom panel must never launch an old save.
                        time.sleep(0.12)
                        continue
            except (RuntimeError, StopIteration):
                pass
            if time.monotonic() - last > 1.7:
                self.window.key("Return")
                last = time.monotonic()
            time.sleep(0.12)
        raise TimeoutError("Native Randomizer page not reached")

    def action(self, action):
        m = self.model
        if action == "save_preset":
            try:
                from platform_support.name_dialog import ask

                existing = {p["name"].casefold() for p in m.presets.read()}
                m.busy = True
                self.name_future = self.pool.submit(
                    ask,
                    self.window.window,
                    m.t("save_preset"),
                    m.t("preset_name"),
                    m.t("save"),
                    m.t("cancel"),
                    m.t("preset_error"),
                    existing,
                )
            except Exception as error:
                m.busy = False
                self.failure(action, error)
            return
        if action == "display":
            try:
                from native_menu.display import prepare_options

                prepare_options(self.folder, self.model.display)
                self.apply_display()
            except Exception as error:
                self.failure(action, error)
            self.mail.publish()
            return
        if action == "diagnostics":
            from native_menu.diagnostics import Diagnostics

            if not hasattr(self, "diagnostics"):
                self.diagnostics = Diagnostics(self)
            self.diagnostics.toggle()
            return
        if action == "exit":
            self.closed = True
            return
        if action in ("copy", "import"):
            try:
                if self.clipboard is None:
                    from menu_clipboard import Clipboard

                    self.clipboard = Clipboard()
                if action == "copy":
                    self.clipboard.put(m.draft.shared())
                    m.message = m.t("copied")
                else:
                    code = self.clipboard.get()
                    try:
                        m.draft.import_seed(code)
                        m.message = ""
                    except ValueError:
                        m.message = m.t("invalid_seed")
            except Exception as error:
                self.failure(action, error, "clipboard_failed")
            self.mail.publish()
            return
        if action not in ("new", "resume", "delete"):
            raise ValueError(action)
        m.busy = True
        m.busy_label = "deleting" if action == "delete" else "busy"
        self.operation = action
        m.loading_progress = (2, "prepare")
        self.mail.publish()
        slot = m.slot
        if action == "new":
            self.future = self.pool.submit(self.loading_job, self.store.create, slot, m.draft)
        elif action == "resume":
            self.future = self.pool.submit(self.loading_job, self.store.resume, slot)
        else:
            self.future = self.pool.submit(self.loading_job, self.store.archive, slot)

    def loading_job(self, function, *args):
        from native_menu.loading import listen, report
        with listen(self.loading_events.put):
            report(3, "prepare")
            result = function(*args)
            report(90, "check")
            return result

    def loading_tick(self):
        from queue import Empty
        latest = None
        while True:
            try:
                latest = self.loading_events.get_nowait()
            except Empty:
                break
        if latest is not None and self.model.busy:
            old = getattr(self.model, "loading_progress", (0, "prepare"))
            if latest[0] >= old[0] and latest != old:
                self.model.loading_progress = latest
                self.mail.publish(state=False)

    def failure(self, operation, error, caption="operation_failed"):
        """Keep technical failures out of localized UI and retain a local diagnosis."""
        if getattr(self, "diagnostics", None):
            self.diagnostics.record_error(operation, error)
        self.model.message = self.model.t(caption)
        atomic(
            self.folder / "native-error.json",
            (
                json.dumps(
                    dict(
                        operation=operation,
                        error_type=type(error).__name__,
                        error=str(error),
                    ),
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n"
            ).encode(),
        )

    def sync_display(self):
        self.poll_name()
        from native_menu.display import from_options, save
        from native_menu.display_window import tick

        tick(self.window)
        if hasattr(self, "diagnostics"):
            self.diagnostics.tick()

        folder = (
            self.runtime.folder
            if self.store.active and self.runtime.folder
            else self.folder
        )
        path = folder / "options.ini"
        if not path.exists():
            return
        signature = (str(path), path.stat().st_mtime_ns)
        if getattr(self, "display_signature", None) == signature:
            return
        try:
            settings = from_options(folder)
            from menu_host.store import save as read_options

            intro = read_options(path).getint("Options", "IntroVariant", fallback=-1)
        except (OSError, ValueError, configparser.Error):
            # Fusion rewrites the file in place. Keep the last valid preference
            # and retry next tick when its write is complete.
            return
        previous = getattr(self, "intro_variant", None)
        if previous != intro:
            self.intro_variant = intro
            if previous is not None:
                import secrets

                self.renderer.presentation_seed = secrets.token_hex(16)
                self.mail.publish()
        if settings is not None and settings != self.model.display:
            self.model.display = settings
            save(self.store.root, settings)
            window = (
                self.runtime
                if self.store.active and self.runtime.folder
                else self.window
            )
            if window.owned():
                # Keep larger selections visible on the user's monitor.
                from native_menu.display_window import apply

                self.display_state = apply(window, settings)
        self.display_signature = signature

    def poll_name(self):
        if self.name_future is not None and self.name_future.done():
            future, self.name_future = self.name_future, None
            self.model.busy = False
            try:
                title = future.result()
                if title is not None:
                    self.model.presets.save(title, self.model.draft.options)
                    self.model.message = self.model.t("preset_saved")
            except Exception as error:
                self.failure("save_preset", error)
            self.mail.publish()

    def tick(self):
        self.sync_display()
        if self.clipboard:
            self.clipboard.pump()
        if self.store.active:
            if self.runtime.poll() == "menu":
                self.model.busy = False
                self.model.go("home")
                self.model.load_slot()
                self.open()
                self.enter()
            return
        if self.future and self.future.done():
            op = self.operation
            f = self.future
            self.future = None
            try:
                f.result()
                if op == "delete":
                    self.model.fresh_draft()
                    self.model.message = ""
                else:
                    self.window.close()
                    from native_menu.display import prepare_options

                    prepare_options(
                        self.store.folder(self.model.slot), self.model.display
                    )
                    self.runtime.start(self.model.slot)
                    from native_menu.display_window import apply

                    apply(self.runtime, self.model.display)
                    self.model.busy = False
                    return
            except Exception as error:
                self.failure(op, error)
                if not self.window.owned():
                    self.open()
                    self.enter()
            self.model.busy = False
            self.mail.publish()
        if not self.window.owned():
            self.closed = True
            return
        if not self.model.busy and self.mail.poll():
            action = self.model.action
            self.model.action = None
            if action:
                self.action(action)

    def close(self):
        self.closed = True
        self.pool.shutdown(wait=True)
        if self.store.active:
            self.runtime.close("native-menu-shutdown")
        self.window.close()
        if self.clipboard:
            self.clipboard.close()
        from menu_host.cleanup import finished

        finished(self.folder, self.store.root)
