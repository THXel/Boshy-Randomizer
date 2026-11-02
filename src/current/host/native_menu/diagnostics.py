"""Local diagnosis and explicit test-copy actions, toggled with Ctrl+Alt+D.

Only an explicit allowlist is displayed: no save contents, profile paths,
credentials, environment variables, or other processes.
"""

import configparser
import json
import time
from collections import deque
from dataclasses import asdict
from pathlib import Path
from menu_host.store import save
from distribution.identity import VERSION

LANGS = ("de", "en", "es", "ru", "ja")
TEXT = {
    "title": (
        "Randomizer · Diagnose",
        "Randomizer · Diagnostics",
        "Randomizer · Diagnóstico",
        "Randomizer · Диагностика",
        "Randomizer · 診断",
    ),
    "copy": (
        "Bericht kopieren",
        "Copy report",
        "Copiar informe",
        "Копировать отчёт",
        "レポートをコピー",
    ),
    "export": (
        "Bericht speichern",
        "Save report",
        "Guardar informe",
        "Сохранить отчёт",
        "レポートを保存",
    ),
    "save_error": (
        "Bericht konnte nicht gespeichert werden.",
        "Could not save report.",
        "No se pudo guardar el informe.",
        "Не удалось сохранить отчёт.",
        "レポートを保存できませんでした。",
    ),
    "close": ("Schließen", "Close", "Cerrar", "Закрыть", "閉じる"),
    "hint": (
        "Nur lokale Spielinformationen · Strg+Alt+D",
        "Local game information only · Ctrl+Alt+D",
        "Solo información local del juego · Ctrl+Alt+D",
        "Только локальные данные игры · Ctrl+Alt+D",
        "ローカルのゲーム情報のみ · Ctrl+Alt+D",
    ),
}

from native_menu.debug_labels import TEXT as ACTION_TEXT

TEXT.update(ACTION_TEXT)


def snapshot(c):
    try:
        frame = c.window.reader.frame() if c.window.reader else None
    except (RuntimeError, OSError):
        frame = "unavailable"
    draft = c.model.draft
    options = getattr(draft, "options", {})
    seed = draft.seed
    if getattr(c, "phase", "menu") in ("starting", "playing"):
        try:
            plan_folder = c.store.folder(c.active_slot)
            plan = json.loads((plan_folder / "plan.json").read_text(encoding="utf-8"))
            seed, options = plan["seed"], plan["options"]
        except (OSError, ValueError, KeyError, AttributeError):
            # Do not silently report the menu draft as the active run.
            seed, options = None, {}
    from menu_host.draft import initial

    template = initial()

    def allowed(values, shape):
        result = {}
        for key, default in shape.items():
            if key not in values:
                continue
            value = values[key]
            if isinstance(default, dict) and isinstance(value, dict):
                result[key] = allowed(value, default)
            elif isinstance(value, (bool, int, float)) or value is None:
                result[key] = value
            elif (
                isinstance(value, str)
                and len(value) <= 80
                and not any(s in value for s in ("/", "\\"))
            ):
                result[key] = value
            elif isinstance(value, list) and all(
                isinstance(v, str)
                and len(v) <= 80
                and not any(s in v for s in ("/", "\\"))
                for v in value
            ):
                result[key] = value[:100]
        return result

    return {
        "schema": 2,
        "version": VERSION,
        "build": c.base.name,
        "phase": getattr(c, "phase", "menu"),
        "frame": frame,
        "slot": getattr(c, "active_slot", None),
        "seed": seed,
        "options": allowed(options, template),
        "language": getattr(c.model, "language", None),
        "presentation_pack": getattr(getattr(c, "presentation", None), "pack", None),
        "recent_transitions": list(
            getattr(getattr(c, "diagnostics", None), "transitions", [])
        ),
        "recent_errors": list(getattr(getattr(c, "diagnostics", None), "errors", [])),
        "working_copy_cleanup": getattr(c, "cleanup_summary", {}),
        "display": asdict(c.model.display),
        "result_screen": bool(getattr(getattr(c, "completion", None), "data", None)),
    }


class Diagnostics:
    def __init__(self, c):
        self.c = c
        self.sequence = 0
        self.signature = None
        self.root = None
        self.last = 0
        self.text = ""
        self.transitions = deque(maxlen=20)
        self.errors = deque(maxlen=10)
        self.route_signature = None
        self.route_stamp = None
        self.note = ""
        self.recording = False
        self.recorded = deque(maxlen=600)
        self.record_started = self.record_last = 0.0
        self.action_signature = None

    def record_error(self, operation, error):
        from native_menu.support import describe_error
        from menu_host.store import atomic

        self.errors.append(describe_error(operation, error))
        try:
            path = self.c.store.root / "reports/last-error.json"
            atomic(
                path,
                (
                    json.dumps(snapshot(self.c), ensure_ascii=False, indent=2) + "\n"
                ).encode("utf-8"),
            )
        except (OSError, ValueError, AttributeError, TypeError):
            pass  # Reporting must not hide the original error.

    def request(self):
        """An unavailable optional report window must not interrupt gameplay."""
        try:
            self.toggle()
        except Exception as error:
            self.record_error("diagnostics-window", error)
            try:
                self.close()
            except Exception:
                self.root = None

    def toggle(self):
        if self.root:
            self.close()
            return
        import tkinter as tk
        from tkinter import ttk

        language = self.c.model.language
        t = lambda k: TEXT[k][LANGS.index(language)]
        self.root = tk.Tk()
        self.root.title(t("title"))
        height = min(720, self.root.winfo_screenheight() - 80)
        self.root.geometry(f"760x{height}")
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        ttk.Label(self.root, text=t("hint"), padding=8).pack(fill="x")
        self.view = tk.Text(
            self.root,
            wrap="word",
            font=("DejaVu Sans Mono", 10),
            state="disabled",
            background="#101b24",
            foreground="#e4edf2",
            height=8,
        )
        self.view.pack(fill="both", expand=True, padx=8)
        ttk.Label(self.root, text=t("note")).pack(anchor="w", padx=8)
        self.note_view = tk.Text(self.root, height=3, wrap="word")
        self.note_view.insert("1.0", self.note)
        self.note_view.pack(fill="x", padx=8)
        recording = ttk.Frame(self.root, padding=8)
        recording.pack(fill="x")
        self.record_button = ttk.Button(
            recording,
            text=t("stop" if self.recording else "record"),
            command=self.toggle_recording,
        )
        self.record_button.pack(side="left")
        ttk.Label(recording, text=t("record_hint")).pack(side="left", padx=8)
        actions = ttk.LabelFrame(self.root, text=t("actions"), padding=8)
        actions.pack(fill="x", padx=8)
        ttk.Label(actions, text=t("action_hint"), wraplength=710).pack(fill="x")
        self.action_boxes = {}
        for operation in ("teleport", "item", "character"):
            line = ttk.Frame(actions)
            line.pack(fill="x", pady=2)
            box = ttk.Combobox(line, state="readonly", width=45)
            box.pack(side="left", fill="x", expand=True)
            self.action_boxes[operation] = box
            ttk.Button(
                line,
                text=t(operation),
                command=lambda op=operation: self.run_action(op),
            ).pack(side="right")
        ttk.Button(
            actions, text=t("restore"), command=lambda: self.run_action("restore")
        ).pack(anchor="w", pady=3)
        self.update_actions()
        buttons = ttk.Frame(self.root, padding=8)
        buttons.pack(fill="x")
        ttk.Button(buttons, text=t("copy"), command=self.copy).pack(side="left")
        ttk.Button(buttons, text=t("export"), command=self.export).pack(
            side="left", padx=8
        )
        ttk.Button(buttons, text=t("close"), command=self.close).pack(side="right")
        self.refresh()

    def refresh(self):
        if hasattr(self, "note_view") and self.root:
            self.note = self.note_view.get("1.0", "end-1c")[:4000]
        data = snapshot(self.c)
        data.update(
            note=self.note,
            recording=list(self.recorded),
            recording_active=self.recording,
        )
        self.text = json.dumps(data, ensure_ascii=False, indent=2)
        self.view.configure(state="normal")
        self.view.delete("1.0", "end")
        self.view.insert("1.0", self.text)
        self.view.configure(state="disabled")
        self.last = time.monotonic()

    def copy(self):
        self.refresh()
        self.root.clipboard_clear()
        self.root.clipboard_append(self.text)
        self.root.update_idletasks()

    def export(self):
        from tkinter import filedialog, messagebox

        path = filedialog.asksaveasfilename(
            parent=self.root,
            initialfile="Boshy-Randomizer-diagnostics.json",
            defaultextension=".json",
            filetypes=[("JSON", "*.json")],
        )
        if path:
            self.refresh()
            try:
                Path(path).write_text(self.text + "\n", encoding="utf-8")
            except OSError:
                messagebox.showerror(
                    "Boshy Randomizer",
                    TEXT["save_error"][LANGS.index(self.c.model.language)],
                    parent=self.root,
                )

    def observe_route(self):
        """Bounded history of native route receipts; no save dumps or file paths."""
        from transition.router import GROUP

        if self.c.phase not in ("starting", "playing"):
            self.route_stamp = self.route_signature = None
            return
        path = self.c.folder / "SaveFile1.ini"
        try:
            stamp = path.stat().st_mtime_ns
            if stamp == self.route_stamp:
                return
            cfg = save(path)
            row = {
                k: cfg.getint(GROUP, k, fallback=0)
                for k in ("CurrentStage", "NextId", "Completed", "BlockedPortal")
            }
            row["slot"] = self.c.active_slot
            if row != self.route_signature:
                self.transitions.append(row)
                self.route_signature = row
            self.route_stamp = stamp
        except (OSError, ValueError, configparser.Error):
            pass  # A native in-place save can be temporarily incomplete.

    def update_actions(self):
        from native_menu.debug_actions import destinations, ITEMS, CHARACTERS
        from position_names import position_name

        slot = self.c.model.slot
        signature = (slot, str(self.c.store.current(slot)), self.c.phase)
        if signature == self.action_signature:
            return
        self.action_signature = signature
        spots = []
        if self.c.phase == "menu" and self.c.store.current(slot):
            try:
                plan = json.loads((self.c.store.folder(slot) / "plan.json").read_text())
                spots = destinations(plan)
            except (OSError, ValueError, KeyError):
                pass
        self.destinations = spots
        for op, choices in (
            ("teleport", [position_name(s).replace("_", " ").title() for s in spots]),
            ("item", ITEMS),
            ("character", CHARACTERS),
        ):
            box = self.action_boxes[op]
            box.configure(values=choices)
            if choices:
                box.current(0)
            else:
                box.set("")

    def run_action(self, operation):
        from tkinter import messagebox
        from native_menu import debug_actions

        c = self.c
        if (
            c.phase != "menu"
            or c.model.busy
            or c.future
            or not c.store.current(c.model.slot)
        ):
            messagebox.showinfo(
                "Boshy Randomizer",
                TEXT["unavailable"][LANGS.index(c.model.language)],
                parent=self.root,
            )
            return
        value = None
        if operation != "restore":
            box = self.action_boxes[operation]
            if box.current() < 0:
                return
            value = (
                self.destinations[box.current()]
                if operation == "teleport"
                else box.get()
            )
        c.model.busy = True
        c.operation = "debug"
        c.model.loading_progress = (2, "prepare")
        function = (
            debug_actions.restore if operation == "restore" else debug_actions.prepare
        )
        args = (
            (c.store, c.model.slot)
            if operation == "restore"
            else (c.store, c.model.slot, operation, value)
        )
        c.future = c.pool.submit(function, *args)
        c.mail.publish()

    def toggle_recording(self):
        self.recording = not self.recording
        if self.recording:
            self.recorded.clear()
            self.record_started = time.monotonic()
            self.record_last = 0
        self.record_button.configure(
            text=TEXT["stop" if self.recording else "record"][
                LANGS.index(self.c.model.language)
            ]
        )

    def record_tick(self):
        now = time.monotonic()
        if not self.recording:
            return
        if now - self.record_started >= 600:
            self.recording = False
            return
        if now - self.record_last >= 1:
            data = snapshot(self.c)
            self.recorded.append(
                dict(
                    seconds=round(now - self.record_started, 2),
                    **{
                        k: data[k]
                        for k in (
                            "phase",
                            "frame",
                            "slot",
                            "seed",
                            "recent_transitions",
                            "recent_errors",
                        )
                    },
                )
            )
            self.record_last = now

    def tick(self):
        self.observe_route()
        self.record_tick()
        path = self.c.folder / "options.ini"
        try:
            stamp = path.stat().st_mtime_ns
            if stamp != self.signature:
                sequence = save(path).getint("Options", "DiagnosticRequest", fallback=0)
                if sequence > self.sequence:
                    self.request()
                self.sequence, self.signature = sequence, stamp
        except (OSError, ValueError, configparser.Error):
            pass  # Fusion can briefly expose an incomplete in-place write.
        if self.root:
            if time.monotonic() - self.last > 1:
                self.refresh()
                self.update_actions()
                self.record_button.configure(
                    text=TEXT["stop" if self.recording else "record"][
                        LANGS.index(self.c.model.language)
                    ]
                )
            self.root.update()

    def close(self):
        if self.root:
            if hasattr(self, "note_view"):
                self.note = self.note_view.get("1.0", "end-1c")[:4000]
            self.action_signature = None
            root, self.root = self.root, None
            root.destroy()
