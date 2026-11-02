"""Private host window for the native Fusion run lifecycle."""

import argparse, concurrent.futures, json, threading, tkinter as tk
from tkinter import ttk
from pathlib import Path
from PIL import Image, ImageTk
from menu_host.draft import Draft, LEVELS, BOSSES
from music.packs import PACKS
from menu_host.store import Store, atomic
from menu_host.runtime import Runtime
from menu_host.audio import MenuAudio
from menu_host.loading import LoadingCover
from menu_host.labels import text, stage, LANGUAGES
from export_route_probe import ROOT, REPO

DEFAULT = ROOT / "outputs/Fusion-Menu-20261024/profile"


class Menu:
    def __init__(self, root, store):
        self.root = root
        self.store = store
        self.runtime = Runtime(store)
        self.draft = Draft()
        self.slot = 1
        self.language = "de"
        preferences = store.root / "preferences.json"
        prefs = json.loads(preferences.read_text()) if preferences.exists() else {}
        if preferences.exists():
            value = prefs.get("language")
            if value in LANGUAGES:
                self.language = value
        self.audio = MenuAudio(store.root, prefs.get("menu_music", True) is True)
        self.pending_delete = False
        self.future = None
        self.closing = threading.Event()
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        self.status_key = "ready"
        self.error = ""
        self.widgets = {}
        self.syncing = False
        root.geometry("1060x800")
        root.minsize(980, 760)
        root.configure(bg="#111b25")
        root.protocol("WM_DELETE_WINDOW", self.close)
        style = ttk.Style(root)
        style.theme_use("clam")
        style.configure(
            ".",
            background="#16232f",
            foreground="#edf5f6",
            fieldbackground="#223440",
            font=("DejaVu Sans", 10),
        )
        style.map(
            "TCombobox",
            fieldbackground=[("readonly", "#223440")],
            foreground=[("readonly", "#edf5f6")],
        )
        style.configure("TButton", padding=8)
        style.map(
            "TButton",
            background=[("active", "#244342")],
            foreground=[("disabled", "#687b87")],
        )
        style.configure("TNotebook.Tab", padding=(16, 9))
        style.map("TNotebook.Tab", background=[("selected", "#244342")])
        self.build()
        self.load_selected_settings()
        self.audio.sync()
        self.root.after(250, self.tick)

    def t(self, key):
        return text(key, self.language)

    def build(self):
        if hasattr(self, "loading"):
            self.loading.hide()
        for child in self.root.winfo_children():
            child.destroy()
        self.widgets = {}
        self.root.title(self.t("title"))
        shell = ttk.Frame(self.root, padding=18)
        shell.pack(fill="both", expand=True)
        header = ttk.Frame(shell)
        header.pack(fill="x")
        im = Image.open(REPO / "assets/Custom/boshy_randomizer.png").convert("RGBA")
        im.thumbnail((270, 90))
        self.logo = ImageTk.PhotoImage(im)
        ttk.Label(header, image=self.logo).pack(side="left")
        info = ttk.Frame(header)
        info.pack(side="left", padx=20)
        ttk.Label(info, text=self.t("title"), font=("DejaVu Sans", 17, "bold")).pack(
            anchor="w"
        )
        ttk.Label(info, text=self.t("private")).pack(anchor="w", pady=8)
        self.lang = tk.StringVar(value=self.language)
        lang = ttk.Combobox(
            header, textvariable=self.lang, values=LANGUAGES, width=5, state="readonly"
        )
        lang.pack(side="right")
        self.language_widget = lang
        lang.bind("<<ComboboxSelected>>", self.language_changed)
        self.menu_music = tk.BooleanVar(value=self.audio.enabled)
        music_button = ttk.Checkbutton(
            header,
            text=self.t("menu_music"),
            variable=self.menu_music,
            command=self.music_changed,
        )
        music_button.pack(side="right", padx=12)
        self.widgets["menu_music"] = music_button
        slots = ttk.Frame(shell)
        self.slot_controls = slots
        slots.pack(fill="x", pady=(12, 4))
        self.slotvar = tk.IntVar(value=self.slot)
        for i in (1, 2, 3):
            ttk.Radiobutton(
                slots,
                text=self.t("slot") + " " + str(i),
                variable=self.slotvar,
                value=i,
                command=self.select_slot,
            ).pack(side="left", padx=(0, 24))
        self.summary = tk.StringVar()
        ttk.Label(shell, textvariable=self.summary).pack(anchor="w", pady=7)
        self.tabs = ttk.Notebook(shell)
        self.tabs.pack(fill="both", expand=True)
        route = ttk.Frame(self.tabs, padding=12)
        cos = ttk.Frame(self.tabs, padding=16)
        seed = ttk.Frame(self.tabs, padding=16)
        gameplay = ttk.Frame(self.tabs, padding=16)
        for page, key in [
            (route, "route"),
            (gameplay, "gameplay"),
            (cos, "cosmetics"),
            (seed, "seed"),
        ]:
            self.tabs.add(page, text=self.t(key))
        self.lists = {}
        self.counts = {}
        cols = ttk.Frame(route)
        cols.pack(fill="both", expand=True)
        for col, (pool, label, count, items) in enumerate(
            [
                ("level_pool", "levels", "level_count", LEVELS),
                (
                    "boss_pool",
                    "bosses",
                    "route_boss_count",
                    {k: v[0] for k, v in BOSSES.items()},
                ),
            ]
        ):
            f = ttk.Frame(cols)
            f.grid(row=0, column=col, sticky="nsew", padx=8)
            cols.columnconfigure(col, weight=1)
            ttk.Label(f, text=self.t(label)).pack(anchor="w")
            bar = ttk.Frame(f)
            bar.pack(fill="x", pady=5)
            ttk.Label(bar, text=self.t("count")).pack(side="left")
            var = tk.IntVar()
            self.counts[count] = var
            spin = ttk.Spinbox(
                bar,
                from_=0,
                to=len(items),
                width=5,
                textvariable=var,
                command=self.route_changed,
            )
            spin.pack(side="right")
            spin.bind("<FocusOut>", self.route_changed)
            spin.bind("<Return>", self.route_changed)
            listframe = ttk.Frame(f)
            listframe.pack(fill="both", expand=True)
            scroll = ttk.Scrollbar(listframe, orient="vertical")
            scroll.pack(side="right", fill="y")
            box = tk.Listbox(
                listframe,
                selectmode="multiple",
                exportselection=False,
                bg="#111b25",
                fg="#edf5f6",
                selectbackground="#315f56",
                selectforeground="#edf5f6",
                disabledforeground="#b3c3ce",
                yscrollcommand=scroll.set,
                height=17,
                highlightthickness=0,
                font=("DejaVu Sans", 10),
            )
            box.pack(side="left", fill="both", expand=True)
            scroll.configure(command=box.yview)
            self.lists[pool] = (box, list(items))
            for name in items.values():
                box.insert("end", stage(name, self.language))
            box.bind("<<ListboxSelect>>", self.route_changed)
        cols.rowconfigure(0, weight=1)
        ttk.Label(route, text=self.t("finale"), wraplength=940).pack(anchor="w", pady=8)
        diffrow = ttk.Frame(route)
        diffrow.pack(fill="x")
        ttk.Label(diffrow, text=self.t("difficulty")).pack(side="left")
        self.difficulty = tk.StringVar()
        diff = ttk.Combobox(
            diffrow,
            textvariable=self.difficulty,
            values=[
                "0 · Ez Mode",
                "1 · Totally Average",
                "2 · Hardon Mode",
                "3 · You're Gonna Rage",
            ],
            state="readonly",
            width=28,
        )
        diff.pack(side="left", padx=15)
        diff.bind(
            "<<ComboboxSelected>>",
            lambda e: self.edit(difficulty=int(self.difficulty.get()[0])),
        )
        self.flags = {}
        for key in ("god_mode", "autofire", "no_mouse_ghost", "one_hp"):
            flag = tk.BooleanVar()
            self.flags[key] = flag
            button = ttk.Checkbutton(
                gameplay,
                text=self.t(key),
                variable=flag,
                command=lambda k=key, v=flag: self.edit(**{k: v.get()}),
            )
            button.pack(anchor="w", pady=(12, 4))
            self.widgets[key] = button
            ttk.Label(gameplay, text=self.t(key + "_hint"), wraplength=900).pack(
                anchor="w", pady=(0, 12)
            )
        for i, key in enumerate(
            [
                "music",
                "sprite_scenery",
                "sprite_backgrounds",
                "sprite_decor",
                "sprite_tiles",
                "sprite_actors",
            ]
        ):
            var = tk.BooleanVar()
            self.flags[key] = var
            c = ttk.Checkbutton(
                cos,
                text=self.t(key),
                variable=var,
                command=lambda k=key: self.edit(**{k: self.flags[k].get()}),
            )
            c.grid(row=i, column=0, columnspan=2, sticky="w", pady=8)
            self.widgets[key] = c
        self.packs = {}
        for row, key in enumerate(["music_pack", "blood_pack"], 6):
            ttk.Label(cos, text=self.t(key)).grid(
                row=row, column=0, sticky="w", pady=10
            )
            var = tk.StringVar()
            self.packs[key] = var
            combo = ttk.Combobox(
                cos,
                textvariable=var,
                values=list(PACKS),
                state="readonly",
                width=24,
            )
            combo.grid(row=row, column=1, sticky="w", padx=15)
            combo.bind("<<ComboboxSelected>>", lambda e, k=key: self.pack_changed(k))
        ttk.Label(cos, text=self.t("dim")).grid(row=8, column=0, sticky="w", pady=10)
        self.dim = tk.StringVar()
        dim = ttk.Combobox(
            cos,
            textvariable=self.dim,
            values=["0", "20", "40", "60"],
            state="readonly",
            width=6,
        )
        dim.grid(row=8, column=1, sticky="w", padx=15)
        dim.bind(
            "<<ComboboxSelected>>", lambda e: self.edit(sprite_dim=int(self.dim.get()))
        )
        self.seedvalue = tk.StringVar()
        ttk.Label(
            seed, textvariable=self.seedvalue, font=("DejaVu Sans Mono", 17)
        ).pack(anchor="w", pady=15)
        self.shared = tk.StringVar()
        entry = ttk.Entry(seed, textvariable=self.shared, font=("DejaVu Sans Mono", 10))
        entry.pack(fill="x", pady=15)
        row = ttk.Frame(seed)
        row.pack(fill="x")
        for key, callback in [
            ("copy", self.copy),
            ("import", self.import_seed),
            ("reroll", self.reroll),
        ]:
            button = ttk.Button(row, text=self.t(key), command=callback)
            button.pack(side="left", padx=(0, 12))
            self.widgets[key] = button
        ttk.Label(seed, text=self.t("limits"), wraplength=900).pack(anchor="w", pady=30)
        footer = ttk.Frame(shell)
        footer.pack(fill="x", pady=(12, 0))
        for key, callback in [
            ("new", lambda: self.start(True)),
            ("resume", lambda: self.start(False)),
            ("delete", self.delete),
            ("return", self.return_to_menu),
        ]:
            button = ttk.Button(footer, text=self.t(key), command=callback)
            button.pack(side="left", padx=(0, 8))
            self.widgets[key] = button
        self.status = tk.StringVar()
        ttk.Label(shell, textvariable=self.status, wraplength=980).pack(
            anchor="w", pady=(10, 0)
        )
        self.loading = LoadingCover(self.root)
        self.sync()

    def sync(self):
        self.syncing = True
        try:
            for pool, (box, keys) in self.lists.items():
                box.configure(state="normal")
                box.selection_clear(0, "end")
                for i, key in enumerate(keys):
                    if key in self.draft.options[pool]:
                        box.selection_set(i)
            for k, v in self.counts.items():
                v.set(self.draft.options[k])
            for k, v in self.flags.items():
                v.set(self.draft.options["extras"][k])
            for k, v in self.packs.items():
                v.set(getattr(self.draft, k))
            self.dim.set(str(self.draft.options["extras"]["sprite_dim"]))
            names = [
                "0 · Ez Mode",
                "1 · Totally Average",
                "2 · Hardon Mode",
                "3 · You're Gonna Rage",
            ]
            self.difficulty.set(names[self.draft.options["difficulty"]])
            self.seedvalue.set("Seed: " + self.draft.seed)
            self.shared.set(self.draft.shared())
            self.refresh()
        finally:
            self.syncing = False

    def refresh(self):
        s = self.store.summary(self.slot)
        stage_labels = {
            **LEVELS,
            **{v[2]: v[0] for v in BOSSES.values()},
            "boss_solgryn.ini": "Solgryn",
        }
        location = stage(stage_labels.get(s.get("spot"), "—"), self.language)
        self.summary.set(
            self.t("empty")
            if not s["exists"]
            else f"Seed {s['seed']} · {location} · {self.t('deaths')}: {s['deaths']}"
        )
        playing = bool(self.store.active)
        busy = self.future is not None
        for key, allow in [
            ("new", not s["exists"]),
            ("resume", s["exists"]),
            ("delete", s["exists"]),
            ("return", playing),
        ]:
            enabled = allow and not busy and (key == "return" or not playing)
            self.widgets[key].configure(state="normal" if enabled else "disabled")

        frozen = busy or playing or s["exists"]

        def freeze(parent):
            for child in parent.winfo_children():
                if isinstance(
                    child,
                    (
                        ttk.Entry,
                        ttk.Combobox,
                        ttk.Spinbox,
                        ttk.Button,
                        ttk.Checkbutton,
                        ttk.Radiobutton,
                    ),
                ):
                    child.state(["disabled"] if frozen else ["!disabled"])
                elif isinstance(child, tk.Listbox):
                    child.configure(state="disabled" if frozen else "normal")
                freeze(child)

        freeze(self.tabs)
        self.widgets["copy"].state(["disabled"] if busy or playing else ["!disabled"])
        for control in self.slot_controls.winfo_children():
            control.state(["disabled"] if busy or playing else ["!disabled"])
        self.language_widget.state(["disabled"] if busy or playing else ["!disabled"])
        self.status.set(self.error or self.t(self.status_key))
        if busy:
            self.loading.show(self.t(self.status_key))
        else:
            self.loading.hide()
        atomic(
            self.store.root / "ui-state.json",
            (
                json.dumps(
                    dict(
                        slot=self.slot,
                        seed=self.draft.seed,
                        options=self.draft.options,
                        busy=busy,
                        playing=playing,
                        error=self.error,
                        language=self.language,
                        summary=s,
                    ),
                    indent=2,
                )
                + "\n"
            ).encode(),
        )

    def fail(self, e):
        self.error = str(e)
        self.refresh()

    def edit(self, **changes):
        if self.syncing or self.future or self.store.active:
            return
        try:
            self.draft.update(**changes)
            self.error = ""
            self.sync()
        except (ValueError, tk.TclError) as e:
            self.fail(e)
            self.sync()

    def route_changed(self, event=None):
        if self.syncing or self.future or self.store.active:
            return
        try:
            changes = {
                p: [keys[i] for i in box.curselection()]
                for p, (box, keys) in self.lists.items()
            }
            for c, p in [
                ("level_count", "level_pool"),
                ("route_boss_count", "boss_pool"),
            ]:
                changes[c] = max(0, min(self.counts[c].get(), len(changes[p])))
            self.edit(**changes)
        except (ValueError, tk.TclError) as e:
            self.fail(e)
            self.sync()

    def pack_changed(self, key):
        if self.future or self.store.active:
            self.sync()
            return
        self.draft.select_pack(key, self.packs[key].get())
        self.sync()

    def save_preferences(self):
        atomic(
            self.store.root / "preferences.json",
            json.dumps(
                {"language": self.language, "menu_music": self.audio.enabled}
            ).encode(),
        )

    def music_changed(self):
        self.audio.enabled = bool(self.menu_music.get())
        self.audio.sync()
        self.save_preferences()

    def language_changed(self, event=None):
        self.language = self.lang.get()
        self.save_preferences()
        self.build()

    def select_slot(self):
        self.slot = self.slotvar.get()
        self.error = ""
        self.load_selected_settings()

    def load_selected_settings(self):
        if self.store.current(self.slot):
            p = json.loads((self.store.folder(self.slot) / "plan.json").read_text())
            self.draft.import_seed(p["shared_seed"])
            self.draft.music_pack = p["music_pack"]
            self.draft.blood_pack = p["blood_pack"]
        self.sync()

    def reroll(self):
        self.draft.consume_seed()
        self.sync()

    def copy(self):
        self.root.clipboard_clear()
        self.root.clipboard_append(self.draft.shared())

    def import_seed(self):
        try:
            self.draft.import_seed(self.shared.get())
            self.error = ""
            self.sync()
        except Exception as e:
            self.fail(e)

    def start(self, new):
        if self.future or self.store.active:
            return
        from copy import deepcopy

        draft = deepcopy(self.draft)
        slot = self.slot
        self.error = ""
        self.status_key = "busy"

        def work():
            if new:
                self.store.create(slot, draft)
            if self.closing.is_set():
                return
            self.audio.suspend()
            return self.runtime.start(slot)

        self.future = self.executor.submit(work)
        self.refresh()

    def delete(self):
        if self.future or self.store.active:
            return
        self.error = ""
        self.pending_delete = True
        self.status_key = "deleting"
        self.future = self.executor.submit(self.store.archive, self.slot)
        self.refresh()

    def return_to_menu(self):
        if self.future:
            return
        self.future = self.executor.submit(self.runtime.close)
        self.status_key = "busy"
        self.refresh()

    def tick(self):
        try:
            if self.future and self.future.done():
                f = self.future
                self.future = None
                try:
                    f.result()
                    if self.pending_delete:
                        self.draft.consume_seed()
                    self.error = ""
                except Exception as e:
                    self.error = str(e)
                self.pending_delete = False
                self.status_key = "playing" if self.store.active else "ready"
                self.sync()
                if not self.store.active and not self.closing.is_set():
                    self.audio.resume()
            if not self.future and self.store.active:
                if self.runtime.poll() == "menu":
                    self.status_key = "ready"
                    self.refresh()
                    self.audio.resume()
                    self.root.deiconify()
                    self.root.lift()
            if self.closing.is_set() and not self.future:
                if self.store.active:
                    self.return_to_menu()
                else:
                    self.audio.close()
                    self.loading.hide()
                    self.executor.shutdown(wait=False)
                    self.root.destroy()
                    return
        except Exception as e:
            self.fail(e)
        self.root.after(250, self.tick)

    def close(self):
        self.closing.set()
        self.audio.close()
        self.status_key = "closing"
        self.refresh()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--profile", type=Path, default=DEFAULT)
    a = p.parse_args()
    store = Store(a.profile)
    with store.lock():
        root = tk.Tk()
        menu = Menu(root, store)
        try:
            root.mainloop()
        finally:
            menu.closing.set()
            menu.audio.close()
            menu.executor.shutdown(wait=True)
            if store.active:
                menu.runtime.close("host-shutdown")


if __name__ == "__main__":
    main()
