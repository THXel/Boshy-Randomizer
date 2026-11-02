"""Export a private native run: routes, graphics, audio, gameplay and start character.

Blood is a local cosmetic preference, independent of the shared route seed.
Category-safe music is native. The default retains the separate menu; the
explicit unified option includes the native menu and session handoff.
The persistent presentation preferences supply death audio and screens at launch.
"""

import argparse, configparser, hashlib, io, json, runpy, tempfile
from pathlib import Path
from export_route_probe import plan, save_text, REPO
from run_settings import decode, normalize
from visuals.actor_palettes import settings as actor_settings, GROUP as ACTOR_GROUP
from visuals.player_blood import GROUP as BLOOD_GROUP
from visuals.scenery_pack import (
    prepare as scenery,
    UNIFIED_BASE_SHA,
)
from visuals.blood_pack import prepare as blood
from build_profiles import PREFIX
from gameplay.settings import settings as gameplay_settings, GROUP as GAMEPLAY_GROUP
from music.soundtrack import prepare as music
from gameplay import cycle_plan, normal_plan, target_plan
from gameplay.reward_plan import (
    mapping as reward_mapping,
    settings as reward_settings,
    GROUP as REWARD_GROUP,
)
from gameplay.reward_icons import prepare as reward_icons

from app_paths import ORIGINAL, SOUNDPACKS
from native_menu.builds import EXTRAS_BASE as BASE, EXTRAS_SHA

from music.packs import PACKS


def export(
    shared,
    out,
    pack="original",
    source=None,
    music_pack="original",
    *,
    unified=False,
    classic=False,
    dynamic=False,
):
    from native_menu.loading import report
    report(8, "verify")
    if sum((unified, classic, dynamic)) > 1:
        raise ValueError("Choose one native menu presentation")
    if pack not in PACKS:
        raise ValueError("Unknown local blood pack")
    seed, options = decode(shared)
    options = normalize(options)
    normal = options["mode"] == "normal"
    target = options["mode"] == "target"
    character = cycle_plan.initial(options, seed)
    out = Path(out).resolve()
    if out.exists():
        raise FileExistsError("Refusing to overwrite an existing run: " + str(out))
    base = PREFIX / "drive_c/BoshyTransitions/Boshy-unified-v1.exe" if unified else BASE
    expected = UNIFIED_BASE_SHA if unified else EXTRAS_SHA
    if classic:
        from native_menu.builds import DYNAMIC_BASE, DYNAMIC_SHA

        base, expected = DYNAMIC_BASE, DYNAMIC_SHA
    if dynamic:
        from native_menu.builds import DYNAMIC_BASE, DYNAMIC_SHA

        base, expected = DYNAMIC_BASE, DYNAMIC_SHA
    from gameplay import native_extras
    from native_menu.builds import EXTRAS_BASE

    extras_enabled = any(options["extras"][k] for k in ("mirror", "death_character"))
    if extras_enabled and not dynamic:
        if unified:
            raise ValueError("This menu build does not support native extras")
        if not classic:
            base, expected = EXTRAS_BASE, EXTRAS_SHA
    native_extras_build = dynamic or classic or base == EXTRAS_BASE
    if hashlib.sha256(base.read_bytes()).hexdigest() != expected:
        raise ValueError("Unverified native gameplay base")
    from native_menu import builds

    from gameplay import screen_shake, shot_plan, spider_plan

    native_spider = (dynamic or classic) and builds.DYNAMIC_SPIDER
    if options["extras"].get("spider", False) and not native_spider:
        raise ValueError("Spider requires a newer native build")

    native_shots = (dynamic or classic) and builds.DYNAMIC_SHOTS
    if options["extras"].get("shot_mode", "off") != "off" and not native_shots:
        raise ValueError("Shot cycling requires a newer native build")

    native_screen_shake = (dynamic or classic) and builds.DYNAMIC_SCREEN_SHAKE
    if options["extras"].get("no_screen_shaking", False) and not native_screen_shake:
        raise ValueError("No Screen Shaking requires a newer native build")
    runtime_scenery = (dynamic or classic) and builds.DYNAMIC_SCENERY
    if runtime_scenery:
        raw = base.read_bytes()
        scenery_audit = dict(
            schema=1, seed=seed, sha256=expected, runtime=True, changed=[]
        )
    else:
        raw, scenery_audit = scenery(base, ORIGINAL, seed, options["extras"])
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".blood-export-", dir=out.parent) as tmp:
        folder = Path(tmp) / "run"
        folder.mkdir()
        report(18, "graphics")
        if runtime_scenery:
            from visuals.scenery_assets import prepare as prepare_scenery

            scenery_assets, scenery_settings = prepare_scenery(
                folder, seed, options["extras"]
            )
            scenery_audit["changed"] = scenery_assets
        if native_extras_build:
            from visuals.embedded_blood import settings as embedded_blood_settings

            blood_audit = dict(
                pack=pack,
                sha256=scenery_audit["sha256"],
                settings=embedded_blood_settings(pack),
                embedded=True,
            )
        elif pack == "original":
            blood_audit = dict(
                pack=pack,
                sha256=scenery_audit["sha256"],
                settings=dict(Schema=1, Animation=0, LifeTicks=0),
                frames=0,
            )
        else:
            intermediate = Path(tmp) / "scenery.exe"
            intermediate.write_bytes(raw)
            raw, blood_audit = blood(
                intermediate,
                ORIGINAL,
                SOUNDPACKS / pack,
                scenery_audit["sha256"],
            )
        intermediate = Path(tmp) / "graphics.exe"
        intermediate.write_bytes(raw)
        report(45, "music")
        if dynamic:
            from music import runtime as runtime_music

            music_assets, music_settings = runtime_music.prepare(
                folder,
                seed,
                music_pack,
                SOUNDPACKS / music_pack,
                options["extras"]["music"],
            )
            music_audit = dict(
                enabled=options["extras"]["music"],
                pack=music_pack,
                sha256=blood_audit["sha256"],
                runtime=True,
                changed=music_assets,
            )
        else:
            raw, music_audit = music(
                intermediate,
                blood_audit["sha256"],
                seed,
                music_pack,
                SOUNDPACKS / music_pack,
                enabled=options["extras"]["music"],
            )
        intermediate = Path(tmp) / "music.exe"
        intermediate.write_bytes(raw)
        raw, reward_audit = reward_icons(
            intermediate,
            ORIGINAL,
            music_audit["sha256"],
            seed,
            options["items"] and not dynamic,
        )
        digest = reward_audit["sha256"]
        report(65, "save")
        p = plan(shared, digest, digest, source)
        p.update(
            scope=__doc__,
            gameplay_settings=gameplay_settings(
                options["extras"], difficulty=options["difficulty"]
            ),
            start_character=character,
            cycle_schema=1,
            reward_schema=1,
            rewards=reward_mapping(seed, options["items"]),
            blood_pack=pack,
            music_pack=music_pack,
            music_enabled=music_audit["enabled"],
            blood_settings=blood_audit["settings"],
            actor_settings=actor_settings(
                seed,
                options["extras"]["sprite_scenery"]
                and options["extras"]["sprite_actors"],
            ),
        )
        if native_shots:
            p["native_shots_schema"] = 1
        if native_spider:
            p["native_spider_schema"] = 1
        if native_screen_shake:
            p["screen_shake_schema"] = 1
        if runtime_scenery:
            p["runtime_scenery_schema"] = 1
            p["runtime_scenery_assets"] = scenery_assets
            p["runtime_scenery_settings"] = scenery_settings
        if native_extras_build:
            p["native_extras_schema"] = 1
        if dynamic:
            from gameplay import runtime_reward_icons

            p["runtime_music_schema"] = 1
            p["runtime_music_assets"] = music_assets
            p["runtime_music_settings"] = music_settings
            p["runtime_reward_icons_schema"] = 1
            p["runtime_reward_assets"] = runtime_reward_icons.prepare(folder)
        if unified or classic or dynamic:
            p["unified_schema"] = 1
            p["unified_base_sha256"] = expected
            p["menu_presentation"] = "classic" if classic or dynamic else "panel"
        if normal:
            p["normal_schema"] = 1
        if target:
            p.update(target_schema=1, targets=target_plan.goals(seed, options))
        del p["binding"]
        p["binding"] = hashlib.sha256(
            json.dumps(p, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        c = configparser.ConfigParser(interpolation=None)
        c.optionxform = str
        c.read_string(save_text(p))
        c.read_dict(
            {
                ACTOR_GROUP: p["actor_settings"],
                BLOOD_GROUP: p["blood_settings"],
                GAMEPLAY_GROUP: p["gameplay_settings"],
                REWARD_GROUP: reward_settings(seed, options["items"]),
            }
        )
        if runtime_scenery:
            from visuals.runtime_scenery import GROUP as SCENERY_GROUP

            c.read_dict({SCENERY_GROUP: scenery_settings})
        if native_spider:
            c.read_dict(
                {spider_plan.GROUP: spider_plan.settings(seed, options["extras"])}
            )
        if native_shots:
            c.read_dict({shot_plan.GROUP: shot_plan.settings(seed, options["extras"])})
        if native_screen_shake:
            c.read_dict({screen_shake.GROUP: screen_shake.settings(options["extras"])})
        if native_extras_build:
            c.read_dict(
                {native_extras.GROUP: native_extras.settings(seed, options["extras"])}
            )
        if dynamic:
            c.read_dict({runtime_music.GROUP: music_settings})
            c.read_dict(
                {REWARD_GROUP: runtime_reward_icons.settings(seed, options["items"])}
            )
        c.read_dict(
            cycle_plan.settings(
                seed, p["route"], options["characters"] and not (normal or target)
            )
        )
        if normal:
            c.read_dict(normal_plan.settings(seed, options["characters"]))
        if target:
            c.read_dict(target_plan.settings(seed, options))
            c.read_dict(target_plan.initial_state())
        if options["items"]:
            for key, reward in p["rewards"].items():
                c[REWARD_GROUP]["Text" + key] = reward["name"]
                c[REWARD_GROUP]["Title" + key] = "RANDOMIZER"
        buf = io.StringIO()
        c.write(buf, space_around_delimiters=False)
        rc4 = runpy.run_path(str(REPO / "src/shared/PY/rc4_utils.py"))["rc4_crypt"]
        if character is not None:
            (folder / "options.ini").write_bytes(
                rc4(b"BLOB", b"[Options]\r\nOnlineLicenseCharacter=1\r\n")
            )
            (folder / "onlineLicense.ini").write_bytes(
                rc4(
                    b"BLOB",
                    (
                        normal_plan.profile(character, options["characters"])
                        if normal
                        else (
                            target_plan.profile(character, options["characters"])
                            if target
                            else cycle_plan.profile(
                                character, options["characters"], p["source"]
                            )
                        )
                    ).encode("latin1"),
                )
            )
        if native_extras_build and options["extras"]["death_character"]:
            profile_path = folder / "onlineLicense.ini"
            profile_cfg = configparser.ConfigParser(interpolation=None)
            profile_cfg.optionxform = str
            profile_cfg.read_string(
                rc4(b"BLOB", profile_path.read_bytes()).decode("latin1")
            )
            profile_cfg.read_dict(
                native_extras.profile(native_extras.settings(seed, options["extras"]))
            )
            profile_buf = io.StringIO()
            profile_cfg.write(profile_buf)
            profile_path.write_bytes(
                rc4(b"BLOB", profile_buf.getvalue().encode("latin1"))
            )
        for enabled, module in (
            (native_shots and options["extras"]["shot_mode"] != "off", shot_plan),
            (native_spider and options["extras"]["spider"], spider_plan),
        ):
            if not enabled:
                continue
            profile_path = folder / "onlineLicense.ini"
            profile_cfg = configparser.ConfigParser(interpolation=None)
            profile_cfg.optionxform = str
            if profile_path.exists():
                profile_cfg.read_string(
                    rc4(b"BLOB", profile_path.read_bytes()).decode("latin1")
                )
            profile_cfg.read_dict(
                module.profile(module.settings(seed, options["extras"]))
            )
            profile_buf = io.StringIO()
            profile_cfg.write(profile_buf)
            profile_path.write_bytes(
                rc4(b"BLOB", profile_buf.getvalue().encode("latin1"))
            )
        (folder / "Boshy.exe").write_bytes(raw)
        (folder / "SaveFile1.ini").write_bytes(
            rc4(b"BLOB", buf.getvalue().replace("\n", "\r\n").encode("latin1"))
        )
        for name, data in [
            ("plan", p),
            ("scenery-audit", scenery_audit),
            ("blood-audit", blood_audit),
            ("music-audit", music_audit),
            ("reward-audit", reward_audit),
        ]:
            (folder / (name + ".json")).write_text(json.dumps(data, indent=2) + "\n")
        report(80, "check")
        folder.rename(out)
    return dict(path=str(out), game_sha256=digest, pack=pack, scope=__doc__)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--shared-seed", required=True)
    p.add_argument("--out", required=True, type=Path)
    p.add_argument("--blood-pack", choices=PACKS, default="original")
    p.add_argument("--source")
    p.add_argument("--music-pack", choices=PACKS, default="original")
    a = p.parse_args()
    print(
        json.dumps(
            export(a.shared_seed, a.out, a.blood_pack, a.source, a.music_pack), indent=2
        )
    )


if __name__ == "__main__":
    main()
