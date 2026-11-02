"""Responsive Linux setup window; all disk/network/Wine work stays off Tk."""

import queue
import subprocess
import threading
import time
import traceback

STAGES = {
    "winecheck": ("Wine Staging wird geprüft …", "Checking Wine Staging …"),
    "winedownload": (
        "Wine Staging wird heruntergeladen …",
        "Downloading Wine Staging …",
    ),
    "wineextract": ("Wine Staging wird entpackt …", "Unpacking Wine Staging …"),
}


class Cancelled(Exception):
    """Preparation stopped at a safe callback boundary."""


STATUS = {
    "Waiting for Wine setup…": (
        "Warten auf eine laufende Wine-Einrichtung …",
        "Waiting for another Wine setup …",
    ),
    "Checking Wine Staging 11.2…": STAGES["winecheck"],
    "Downloading Wine Staging 11.2 (72 MiB)…": STAGES["winedownload"],
    "Installing verified Wine Staging 11.2…": STAGES["wineextract"],
}


def progress_detail(stage, current, total, tr):
    """Describe real counts only, including downloads without Content-Length."""
    if current < 0 or total < 0:
        raise ValueError("Negative progress")
    percent = min(100, current * 100 / total) if total else None
    if stage == "winedownload":
        amount = f"{current / 1024**2:.1f} MiB"
        if total:
            amount += f" / {total / 1024**2:.1f} MiB"
    elif total:
        amount = tr(
            "{current} von {total} Dateien", "{current} of {total} files"
        ).format(current=current, total=total)
    else:
        amount = tr("Wird bearbeitet …", "Working …")
    if percent is not None:
        amount += f"  ·  {percent:.0f} %"
    return percent, amount


class SetupWindow:
    def __init__(self, work, mode, logs, tr, launch_work=None):
        import tkinter as tk
        from tkinter import ttk

        self.work, self.mode, self.logs, self.tr = work, mode, logs, tr
        self.launch_work = launch_work
        self.launching = False
        self.setup_performed = False
        self.events = queue.Queue()
        self.stop = threading.Event()
        self.delegated = False
        self.game_id = None
        self.window = window = tk.Tk()
        window.title("Boshy Randomizer")
        window.geometry("620x330")
        window.minsize(540, 330)
        frame = ttk.Frame(window, padding=24)
        frame.pack(fill="both", expand=True)
        self.heading = ttk.Label(
            frame,
            text=tr("Boshy Randomizer einrichten", "Set up Boshy Randomizer"),
            font=("", 16, "bold"),
        )
        self.heading.pack(anchor="w")
        self.text = tk.StringVar()
        self.detail = tk.StringVar()
        self.elapsed = tk.StringVar()
        ttk.Label(frame, textvariable=self.text, wraplength=555).pack(
            anchor="w", pady=(18, 10)
        )
        self.bar = ttk.Progressbar(frame, mode="indeterminate")
        self.bar.pack(fill="x")
        ttk.Label(frame, textvariable=self.detail).pack(anchor="w", pady=8)
        ttk.Label(frame, textvariable=self.elapsed).pack(anchor="w")
        self.hint = tk.StringVar(
            value=tr(
                "Nach der Vorbereitung öffnet sich die Spielinstallation. Dort das Original-ZIP oder den Spielordner auswählen.",
                "After preparation, game setup opens. Select the original ZIP or game folder there.",
            )
        )
        ttk.Label(frame, textvariable=self.hint, wraplength=555).pack(
            anchor="w", pady=(12, 8)
        )
        buttons = ttk.Frame(frame)
        buttons.pack(fill="x", side="bottom")
        self.retry = ttk.Button(
            buttons, text=tr("Erneut versuchen", "Try again"), command=self.start
        )
        self.log_button = ttk.Button(
            buttons,
            text=tr("Protokollordner öffnen", "Open log folder"),
            command=self.open_logs,
        )
        self.launch_option = ttk.Button(
            buttons,
            text=tr("Jetzt spielen", "Play now"),
            command=self.start_game,
        )
        self.close = ttk.Button(
            buttons, text=tr("Schließen", "Close"), command=self.close_requested
        )
        self.close.pack(side="right")
        window.protocol("WM_DELETE_WINDOW", self.close_requested)
        self.default_hint = self.hint.get()
        self.running = False

    def open_logs(self):
        self.logs.mkdir(parents=True, exist_ok=True)
        subprocess.Popen(["xdg-open", str(self.logs)])

    def close_requested(self):
        if self.running:
            if self.launching:
                self.window.withdraw()
                return
            if self.delegated:
                self.hint.set(
                    self.tr(
                        "Bitte im geöffneten Installationsassistenten auf Abbrechen klicken.",
                        "Please click Cancel in the open installation wizard.",
                    )
                )
            else:
                self.stop.set()
                self.close.configure(state="disabled")
                self.hint.set(
                    self.tr("Wird sicher abgebrochen …", "Cancelling safely …")
                )
        else:
            self.window.destroy()

    def start_game(self):
        if self.running or not self.game_id:
            return
        self.launching = True
        self.start()

    def start(self):
        if self.running:
            return
        self.running = True
        self.stop.clear()
        self.delegated = False
        if not self.launching:
            self.game_id = None
            self.setup_performed = False
        self.launch_option.pack_forget()
        self.heading.configure(
            text=self.tr(
                "Boshy Randomizer wird gestartet …", "Starting Boshy Randomizer …"
            )
            if self.launching
            else self.tr("Boshy Randomizer einrichten", "Set up Boshy Randomizer")
        )
        self.started = time.monotonic()
        self.hint.set("" if self.launching else self.default_hint)
        self.close.configure(
            state="normal",
            text=self.tr("Ausblenden", "Hide")
            if self.launching
            else self.tr("Abbrechen", "Cancel"),
        )
        self.retry.pack_forget()
        self.log_button.pack_forget()
        self.status(
            self.tr(
                "Boshy Randomizer wird vorbereitet …", "Preparing Boshy Randomizer …"
            )
        )

        def worker():
            # Coalesce frequent file/byte updates without losing phase changes.
            last = [None, 0.0]

            def progress(stage, current, total):
                if self.stop.is_set():
                    raise Cancelled()
                now = time.monotonic()
                if stage != last[0] or current == total or now - last[1] >= 0.15:
                    self.events.put(("progress", (stage, current, total)))
                    last[:] = stage, now

            def status(value):
                if self.stop.is_set():
                    raise Cancelled()
                self.events.put(("status", value))

            try:
                if self.launching:
                    self.launch_work(self.game_id, status, progress)
                    result = "launched"
                else:
                    result = self.work(status, progress)
                self.events.put(("done", result))
            except Cancelled:
                self.events.put(("cancelled", None))
            except Exception as error:
                try:
                    self.logs.mkdir(parents=True, exist_ok=True)
                    (self.logs / "setup-helper.log").write_text(
                        traceback.format_exc(), encoding="utf-8"
                    )
                except OSError:
                    pass  # An unwritable log folder must not hide the actual failure.
                self.events.put(("error", str(error)))

        threading.Thread(target=worker, daemon=False).start()
        self.window.after(100, self.poll)

    def status(self, value):
        self.text.set(self.tr(*STATUS[value]) if value in STATUS else value)
        self.detail.set(self.tr("Wird bearbeitet …", "Working …"))
        self.bar.stop()
        self.bar.configure(mode="indeterminate")
        self.bar.start(15)

    def finish(self):
        # The preparation window yields to the game installer. Restore it for
        # completion, cancellation or errors so no result remains hidden.
        self.window.deiconify()
        self.running = False
        self.bar.stop()
        self.close.configure(state="normal", text=self.tr("Schließen", "Close"))

    def poll(self):
        elapsed = int(time.monotonic() - self.started)
        self.elapsed.set(
            self.tr("Verstrichene Zeit: ", "Elapsed time: ")
            + f"{elapsed // 60}:{elapsed % 60:02}"
        )
        try:
            while True:
                kind, value = self.events.get_nowait()
                if kind == "status":
                    self.status(value)
                elif kind == "progress":
                    stage, current, total = value
                    if stage == "launching":
                        continue
                    if stage == "wizard":
                        self.setup_performed = True
                        self.window.withdraw()
                        self.bar.stop()
                        self.delegated = True
                        self.close.configure(state="disabled")
                        self.hint.set(
                            self.tr(
                                "Bitte im geöffneten Installationsassistenten auf Abbrechen klicken.",
                                "Please click Cancel in the open installation wizard.",
                            )
                        )
                        continue
                    if stage == "registration":
                        if self.delegated:
                            self.window.deiconify()
                        self.setup_performed = True
                        self.delegated = False
                        self.close.configure(state="normal")
                        self.hint.set(
                            self.tr(
                                "Schließe den letzten Schritt im Lutris-Fenster ab. Hier kannst du das Warten abbrechen.",
                                "Complete the last step in Lutris. You can stop waiting here.",
                            )
                        )
                        continue
                    self.text.set(self.tr(*STAGES[stage]))
                    percent, detail = progress_detail(stage, current, total, self.tr)
                    self.detail.set(detail)
                    if percent is not None:
                        self.bar.stop()
                        self.bar.configure(
                            mode="determinate", maximum=100, value=percent
                        )
                    elif str(self.bar["mode"]) != "indeterminate":
                        self.bar.configure(mode="indeterminate")
                        self.bar.start(15)
                elif kind == "cancelled":
                    self.finish()
                    self.text.set(self.tr("Einrichtung abgebrochen", "Setup cancelled"))
                    self.detail.set("")
                    self.hint.set(
                        self.tr(
                            "Die bisherige Installation bleibt erhalten. Du kannst die Einrichtung erneut starten.",
                            "The existing installation has been kept. You can run setup again.",
                        )
                    )
                    self.retry.pack(side="left")
                    return
                elif kind == "error":
                    self.finish()
                    self.text.set(
                        self.tr(
                            "Einrichtung nicht abgeschlossen", "Setup was not completed"
                        )
                    )
                    self.detail.set("")
                    self.hint.set(value)
                    self.retry.pack(side="left")
                    self.log_button.pack(side="left", padx=8)
                    return
                elif kind == "done":
                    if value == "launched":
                        self.bar.stop()
                        self.running = False
                        self.window.destroy()
                        return
                    self.finish()
                    if value.isdigit():
                        self.game_id = value
                        if self.mode == "run" and not self.setup_performed:
                            self.start_game()
                            return
                        self.bar.configure(mode="determinate", maximum=100, value=100)
                        self.detail.set("")
                        self.text.set(
                            self.tr(
                                "Boshy Randomizer wurde erfolgreich installiert.",
                                "Boshy Randomizer was installed successfully.",
                            )
                        )
                        self.hint.set(
                            self.tr(
                                "Du kannst das Spiel jetzt oder später über Lutris starten.",
                                "You can start the game now or later using Lutris.",
                            )
                        )
                        self.launch_option.pack(side="left")
                        self.close.configure(text=self.tr("Fertig", "Finish"))
                    else:
                        self.bar.configure(mode="determinate", maximum=100, value=100)
                        self.detail.set("")
                        self.text.set(
                            self.tr("Spiel entfernt", "Game removed")
                            if value == "remove"
                            else self.tr("Spiel vorbereitet", "Game prepared")
                        )
                        self.hint.set(
                            self.tr(
                                "Die gewählte Datenoption wurde angewendet. Den Spieleintrag kannst du in Lutris entfernen.",
                                "Your data choice has been applied. You can remove the game entry in Lutris.",
                            )
                            if value == "remove"
                            else self.tr(
                                "Bitte die Einrichtung im geöffneten Lutris-Fenster abschließen.",
                                "Please finish registration in the Lutris window that has opened.",
                            )
                        )
                    return
        except queue.Empty:
            self.window.after(100, self.poll)

    def run(self):
        self.start()
        self.window.mainloop()
