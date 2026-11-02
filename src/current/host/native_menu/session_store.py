"""Validated working-save handoff for one persistent Fusion game process.

Each slot keeps its existing immutable plan and separate profile. The original
engine reads a working SaveFile1.ini. A binding check precedes every copy back;
no frame or process-memory patching is involved. Interrupted sessions retain a
journal and their working files instead of silently replacing a slot.
"""

import json
import configparser
import tempfile
import time
from pathlib import Path
from menu_host.store import atomic, save

FILES = ("SaveFile1.ini", "onlineLicense.ini", "options.ini")


class WorkingSession:
    def __init__(self, folder, store, game_sha):
        self.folder = Path(folder)
        self.store = store
        self.game_sha = game_sha
        self.marker = self.store.root / "native-session.json"
        self.slot = None
        self.meta = None

    @classmethod
    def recover(cls, store):
        """Complete an interrupted validated handoff before opening another game."""
        store.writable()
        marker = store.root / "native-session.json"
        if marker.is_symlink():
            raise ValueError("Linked session journal")
        if not marker.exists():
            return None
        journal = json.loads(marker.read_text())
        name = journal.get("working", "")
        if (
            journal.get("schema") != 2
            or len(name) != 45
            or not name.startswith("rebuilt-menu-")
            or any(c not in "0123456789abcdef" for c in name[13:])
        ):
            raise ValueError("Invalid working session identity")
        folder = store.runs / name
        if folder.is_symlink() or folder.resolve().parent != store.runs:
            raise ValueError("Working session boundary")
        from menu_host.processes import games

        if folder in games(store.runs).values():
            raise RuntimeError("Close the active game before recovering its save")
        slot = journal["slot"]
        meta = store.current(slot)
        if not meta or any(
            journal.get(k) != meta.get(k) for k in ("run", "plan_sha256", "game_sha256")
        ):
            raise ValueError("Interrupted session no longer matches its slot")
        session = cls(folder, store, journal["game_sha256"])
        session.slot, session.meta = slot, meta
        if journal.get("phase") == "staging":
            # Begin was never sent: preserve the original slot, retain working
            # files for diagnosis, and discard only the incomplete handoff.
            store.validate_folder(store.folder(slot), meta)
            session.abandon_unstarted()
            return dict(slot=slot, recovered=False, unstarted=True)
        if journal.get("phase") != "playing":
            raise ValueError("Unknown interrupted session phase")
        session.commit()
        return dict(slot=slot, recovered=True)

    def stage(self, slot):
        if self.slot is not None or self.marker.exists():
            raise RuntimeError("Uncommitted session must be recovered first")
        source, plan, _ = self.store.resume(slot)
        if plan["game_sha256"] != self.game_sha:
            raise ValueError("This run requires a different loaded asset bank")
        # Files are selected only from a validated Store entry.
        payloads = {
            name: (source / name).read_bytes()
            for name in FILES
            if (source / name).is_file()
        }
        meta = self.store.current(slot)
        journal = dict(
            schema=2,
            working=self.folder.name,
            slot=slot,
            run=meta["run"],
            plan_sha256=meta["plan_sha256"],
            game_sha256=self.game_sha,
            phase="staging",
        )
        atomic(self.marker, json.dumps(journal, indent=2).encode())
        self.slot, self.meta = slot, meta
        if plan.get("runtime_music_schema") is not None:
            from music.runtime import stage as stage_music

            stage_music(source, self.folder, plan)
        if plan.get("runtime_scenery_schema") is not None:
            from visuals.scenery_assets import stage as stage_scenery

            stage_scenery(source, self.folder, plan)
        for name in FILES:
            path = self.folder / name
            if name in payloads:
                atomic(path, payloads[name])
            else:
                path.unlink(missing_ok=True)
        journal["phase"] = "playing"
        atomic(self.marker, json.dumps(journal, indent=2).encode())

    def commit(self):
        if self.slot is None:
            return
        if self.store.current(self.slot) != self.meta:
            raise ValueError("Slot reference changed during active session")
        target = self.store.folder(self.slot)
        # Validate an isolated candidate before changing the saved slot. The
        # original immutable plan/EXE are hardlinked, never edited by this code.
        with tempfile.TemporaryDirectory(
            prefix=".session-check-", dir=self.folder
        ) as t:
            candidate = Path(t)
            for name in ("Boshy.exe", "plan.json"):
                (candidate / name).hardlink_to(target / name)
            assets = target / "native-rewards"
            if assets.is_dir():
                (candidate / "native-rewards").mkdir()
                for row in json.loads((candidate / "plan.json").read_text()).get(
                    "runtime_reward_assets", []
                ):
                    name = row["file"]
                    if Path(name).name != name or (assets / name).is_symlink():
                        raise ValueError("Reward asset boundary")
                    (candidate / "native-rewards" / name).hardlink_to(assets / name)
            plan = json.loads((candidate / "plan.json").read_text())
            if plan.get("runtime_music_schema") is not None:
                from music.runtime import link_assets

                link_assets(self.folder, candidate, plan)
            if plan.get("runtime_scenery_schema") is not None:
                from visuals.scenery_assets import link_assets as link_scenery

                link_scenery(self.folder, candidate, plan)
            deadline = time.monotonic() + 2
            while True:
                try:
                    payloads = {}
                    for name in FILES:
                        source = self.folder / name
                        dest = candidate / name
                        if source.is_symlink():
                            raise ValueError("Linked working save")
                        if source.is_file():
                            payloads[name] = source.read_bytes()
                            dest.write_bytes(payloads[name])
                        else:
                            dest.unlink(missing_ok=True)
                    self.store.validate_folder(candidate, self.meta)
                    # The slot validator checks gameplay receipts, not Options.
                    # Native writes truncate this file before rewriting it; an
                    # empty but successfully copied file must never be committed.
                    if "options.ini" in payloads:
                        options = save(candidate / "options.ini")
                        if not options.has_section("Options") or not options["Options"]:
                            raise ValueError("Working options write incomplete")
                    # Validate the exact bytes we will publish and retry if any
                    # native file changed while the candidate was being checked.
                    if any(
                        (self.folder / name).read_bytes() != data
                        for name, data in payloads.items()
                    ):
                        raise ValueError("Working files changed during snapshot")
                    break
                except (OSError, ValueError, configparser.Error) as error:
                    if time.monotonic() >= deadline:
                        raise ValueError(
                            "Working save could not be validated; journal retained"
                        ) from error
                    time.sleep(0.03)
            for name, data in payloads.items():
                atomic(target / name, data)
        self.store.validate_folder(target, self.meta)
        self.marker.unlink()
        self.slot = self.meta = None

    def abandon_unstarted(self):
        self.marker.unlink(missing_ok=True)
        self.slot = self.meta = None
