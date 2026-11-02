"""Atomic slot references to immutable exports; native saves stay beside their EXE."""

import configparser, contextlib, hashlib, json, os, runpy, tempfile, uuid
from pathlib import Path
from platform_support.storage import lock_file, replace
from app_paths import RUNS
from export_native_run import export, REPO
from build_profiles import PREFIX
from transition.router import GROUP, STAGES, CATALOGUE_HASH
from menu_host.draft import validate
from gameplay.characters import selected as selected_character
from gameplay.target_plan import progress as target_progress
from run_settings import encode, route
from gameplay.settings import (
    settings as gameplay_settings,
    GROUP as GAMEPLAY_GROUP,
    CONTROLS,
)

RC4 = runpy.run_path(str(REPO / "src/shared/PY/rc4_utils.py"))["rc4_crypt"]


def digest(path):
    with Path(path).open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def atomic(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix="." + path.name + "-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def save(path):
    path = Path(path)
    if (
        path.is_symlink()
        or not path.is_file()
        or not 0 < path.stat().st_size < 2_000_000
    ):
        raise ValueError("Save boundary")
    c = configparser.ConfigParser(interpolation=None)
    c.read_string(RC4(b"BLOB", path.read_bytes()).decode("latin1"))
    return c


class Store:
    def __init__(self, root, runs=RUNS, exporter=export):
        self.root = Path(root).resolve()
        self.runs = Path(runs).resolve()
        self.exporter = exporter
        self.root.mkdir(parents=True, exist_ok=True)
        self.runs.mkdir(parents=True, exist_ok=True)
        self.lockfile = None
        self.active = None

    @contextlib.contextmanager
    def lock(self):
        with (
            lock_file(self.runs / ".fusion-menu.lock"),
            lock_file(self.root / "host.lock") as stream,
        ):
            self.lockfile = stream
            try:
                yield self
            finally:
                self.lockfile = None

    def writable(self):
        if not self.lockfile:
            raise RuntimeError("Store lock required")
        if self.active:
            raise RuntimeError("Cannot edit slots while a game is running")

    def pointer(self, slot):
        if type(slot) is not int or slot not in (1, 2, 3):
            raise ValueError("Slot")
        return self.root / f"slot-{slot}.json"

    def current(self, slot):
        p = self.pointer(slot)
        if p.is_symlink():
            raise ValueError("Linked slot")
        if not p.exists():
            return None
        meta = json.loads(p.read_text())
        name = meta.get("run", "")
        if (
            len(name) != 45
            or not name.startswith("rebuilt-menu-")
            or any(c not in "0123456789abcdef" for c in name[13:])
        ):
            raise ValueError("Run identity")
        folder = self.runs / name
        if folder.is_symlink() or folder.resolve().parent != self.runs:
            raise ValueError("Run boundary")
        return meta

    def folder(self, slot):
        m = self.current(slot)
        if m is None:
            raise ValueError("Empty slot")
        return self.runs / m["run"]

    def create(self, slot, draft):
        self.writable()
        if self.current(slot):
            raise FileExistsError("Slot already occupied")
        options = validate(draft.options)
        name = "rebuilt-menu-" + uuid.uuid4().hex
        folder = self.runs / name
        self.exporter(
            encode(draft.seed, options),
            folder,
            draft.blood_pack,
            None,
            draft.music_pack,
        )
        # Export failure leaves the slot empty. The pointer is the sole commit.
        p = json.loads((folder / "plan.json").read_text())
        meta = dict(
            schema=1,
            slot=slot,
            run=name,
            plan_sha256=digest(folder / "plan.json"),
            game_sha256=p["game_sha256"],
        )
        self.validate_folder(folder, meta)
        atomic(self.pointer(slot), (json.dumps(meta, indent=2) + "\n").encode())
        return meta

    def validate_folder(self, folder, meta):
        for name in ("Boshy.exe", "plan.json"):
            if (folder / name).is_symlink():
                raise ValueError("Linked run data")
        if (
            digest(folder / "plan.json") != meta["plan_sha256"]
            or digest(folder / "Boshy.exe") != meta["game_sha256"]
        ):
            raise ValueError("Run integrity")
        p = json.loads((folder / "plan.json").read_text())
        binding = p.pop("binding")
        if (
            hashlib.sha256(
                json.dumps(p, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest()
            != binding
        ):
            raise ValueError("Plan binding")
        if p.get("runtime_reward_icons_schema") is not None:
            from gameplay.runtime_reward_icons import validate_assets

            validate_assets(folder, p)
        if p.get("runtime_scenery_schema") is not None:
            from visuals.scenery_assets import validate_assets as validate_scenery

            validate_scenery(folder, p)
        if p.get("runtime_music_schema") is not None:
            from music.runtime import validate_assets as validate_music

            validate_music(folder, p)
        options = validate(p["options"])
        from gameplay import cycle_plan

        character = cycle_plan.initial(options, p["seed"])
        profile = None
        if p.get("start_character") != character:
            raise ValueError("Initial character does not match seed")
        if character is not None:
            profile = save(folder / "onlineLicense.ini")
            current = selected_character(
                {"start_character": profile.get("License", "CharacterName")}
            )
            if (
                current is None
                or not profile.get("License", "Name", fallback="").strip()
                or profile.getint("License", "RandomizerStartCharacter", fallback=0)
                != 1
                or profile.getint("License", "Character") != current["id"]
            ):
                raise ValueError("Invalid saved character")

        if profile is None and (
            options["extras"].get("shot_mode", "off") != "off"
            or options["extras"].get("spider", False)
        ):
            profile = save(folder / "onlineLicense.ini")

        normal = options["mode"] == "normal"
        target = options["mode"] == "target"
        if (
            p["route"] != route(p["seed"], options)
            or p["source"] != ("save1.ini" if normal or target else p["route"][0])
            or p["catalogue_sha256"] != CATALOGUE_HASH
            or p["game_sha256"] != meta["game_sha256"]
        ):
            raise ValueError("Route identity")
        p["binding"] = binding
        c = save(folder / "SaveFile1.ini")
        if p.get("runtime_scenery_schema") is not None:
            from visuals.runtime_scenery import GROUP as SCENERY_GROUP

            if dict(c[SCENERY_GROUP]) != {
                k.lower(): str(v) for k, v in p["runtime_scenery_settings"].items()
            }:
                raise ValueError("Runtime scenery settings changed")
        if p.get("runtime_music_schema") is not None:
            from music.runtime import GROUP as MUSIC_GROUP

            if any(
                c.get(MUSIC_GROUP, key, fallback=None) != str(value)
                for key, value in p["runtime_music_settings"].items()
            ):
                raise ValueError("Changed native music settings")
        if (
            c.get(GROUP, "Binding") != binding
            or c.get(GROUP, "Catalogue") != CATALOGUE_HASH
            or c.getint(GROUP, "Schema") != (0 if normal else 4)
        ):
            raise ValueError("Save belongs to another run")
        ids = {
            STAGES[s]["id"]
            for s in (list(STAGES) if target else p["route"] or ["save1.ini"])
        }
        if (
            c.getint(GROUP, "CurrentStage") not in ids
            or not 3 <= c.getint("Positions", "frame") <= 60
        ):
            raise ValueError("Invalid saved station")
        for a, b in zip(p["route"], p["route"][1:]):
            sid = str(STAGES[a]["id"])
            for key, field in [
                ("NextId", "id"),
                ("NextFrame", "frame"),
                ("NextX", "x"),
                ("NextY", "y"),
            ]:
                if c.getint(GROUP, key + sid) != STAGES[b][field]:
                    raise ValueError("Changed route edge")
        for group, settings in [
            ("FusionBloodV1", p["blood_settings"]),
            ("FusionActorsV1", p["actor_settings"]),
        ]:
            if any(c.getint(group, key) != value for key, value in settings.items()):
                raise ValueError("Changed cosmetic settings")
        cycle_plan.validate(p, c, profile)
        from gameplay.native_extras import validate as validate_native_extras

        validate_native_extras(p, c, profile)
        from gameplay.screen_shake import validate as validate_screen_shake

        validate_screen_shake(p, c)
        from gameplay.shot_plan import validate as validate_shots

        validate_shots(p, c, profile)
        from gameplay.spider_plan import validate as validate_spider

        validate_spider(p, c, profile)
        if p.get("reward_schema") == 1:
            from gameplay.reward_plan import validate as validate_rewards

            validate_rewards(p, c)
        elif p.get("reward_schema") is not None or options["items"]:
            raise ValueError("Mixed rewards require a supported native build")
        rules = p.get("gameplay_settings")
        if rules is None:
            if any(options["extras"][k] for k in ("god_mode", *CONTROLS)):
                raise ValueError("God Mode requires a native gameplay build")
        else:
            if rules != gameplay_settings(
                options["extras"], rules.get("Schema"), options["difficulty"]
            ):
                raise ValueError("Gameplay rules do not match seed")
            if any(
                c.getint(GAMEPLAY_GROUP, key) != value for key, value in rules.items()
            ):
                raise ValueError("Changed gameplay settings")
        return p, c

    def resume(self, slot):
        self.writable()
        meta = self.current(slot)
        if not meta:
            raise ValueError("Empty slot")
        folder = self.folder(slot)
        p, c = self.validate_folder(folder, meta)
        return folder, p, c

    def archive(self, slot):
        self.writable()
        m = self.current(slot)
        if not m:
            return
        archive = self.root / "deleted"
        archive.mkdir(exist_ok=True)
        os.replace(self.pointer(slot), archive / (m["run"] + ".json"))
        # Retain the private native directory for undo; it is no longer a slot.

    def summary(self, slot):
        m = self.current(slot)
        if not m:
            return dict(slot=slot, exists=False)
        folder = self.folder(slot)
        p = json.loads((folder / "plan.json").read_text())
        c = save(folder / "SaveFile1.ini")
        if p.get("runtime_music_schema") is not None:
            from music.runtime import GROUP as MUSIC_GROUP

            if any(
                c.get(MUSIC_GROUP, key, fallback=None) != str(value)
                for key, value in p["runtime_music_settings"].items()
            ):
                raise ValueError("Changed native music settings")
        sid = c.getint(GROUP, "CurrentStage")
        spots = STAGES if p["options"]["mode"] == "target" else p["route"]
        spot = next((s for s in spots if STAGES[s]["id"] == sid), "?")
        if p["options"]["mode"] == "normal":
            frame = c.getint("Positions", "frame")
            matches = [k for k, stage in STAGES.items() if stage["frame"] == frame]
            spot = next(
                (k for k in matches if STAGES[k]["category"] == "rooms"),
                matches[0] if matches else "Frame " + str(frame),
            )
        from gameplay.collections import collected

        profile = (
            save(folder / "onlineLicense.ini")
            if (folder / "onlineLicense.ini").is_file()
            else configparser.ConfigParser(interpolation=None)
        )
        items, characters = collected(c, profile)
        return dict(
            slot=slot,
            exists=True,
            test_run=c.getint("RandomizerDebug", "Enabled", fallback=0) == 1,
            character=profile.get("License", "CharacterName", fallback="Boshy"),
            items=[row["name"] for row in items if row["done"]],
            characters=[row["name"] for row in characters if row["done"]],
            seed=p["seed"],
            spot=spot,
            frame=c.getint("Positions", "frame"),
            deaths=c.getint("Stats", "Deaths", fallback=0),
            completed=c.getint(GROUP, "Completed", fallback=0),
            save_sha256=digest(folder / "SaveFile1.ini"),
            blood_pack=p["blood_pack"],
            music_pack=p["music_pack"],
            targets=p.get("targets"),
            target_progress=(
                target_progress(p["targets"], c) if "targets" in p else None
            ),
        )
