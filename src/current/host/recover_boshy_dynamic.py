"""Classic unified build with native runtime chest-reward artwork selection."""

import json
import sys
from pathlib import Path
import recover_boshy_classic as classic
from gameplay import runtime_reward_icons, native_extras, god_mode_flames, screen_shake
from native_menu import (
    attribution,
    social,
    display_build,
    options_display,
    tracker_link,
    hover,
    input_retry,
    input_buffer,
    options_locale,
    results,
    target_hud,
    presentation_events,
)
from visuals import embedded_blood, death_screen
from visuals import runtime_scenery, background_groups, scenery_cache
from gameplay import (
    camera_lifetime,
    shot_events,
    shot_sounds,
    spider_events,
    spider_object,
)
from gameplay.native_events import Events
from gameplay import dresser
from music import runtime as runtime_music
from music import title as title_music
from music import solgryn as solgryn_music
from music import loops as music_loops

routes = classic.routes
changes = []


def sections(payload):
    frame = routes.payloads[payload]
    initial = classic.sections(payload)
    from transition import hub_guard

    initial, hub_audit = hub_guard.transform(
        frame,
        initial,
        routes.table,
        routes.objects,
        routes.frames[frame - 1]["instances"],
    )
    profile = Events.profile(initial) if frame in spider_events.FRAMES else None
    result, shot_audit = shot_events.transform(
        frame,
        initial,
        routes.objects,
        routes.frames[frame - 1]["instances"],
    )
    result, shot_sound_audit = shot_sounds.transform(
        frame, result, routes.objects, routes.frames[frame - 1]["instances"]
    )
    result, audit = runtime_reward_icons.transform(
        frame,
        result,
        routes.objects,
        routes.frames[frame - 1]["instances"],
    )
    result, extra_audit = native_extras.transform(
        frame, result, routes.objects, routes.frames[frame - 1]["instances"]
    )
    result, dresser_audit = dresser.transform(
        frame, result, routes.objects, routes.frames[frame - 1]["instances"]
    )
    result, credit_audit = attribution.transform(frame, result)
    result, social_audit = social.transform(frame, result)
    if frame == 2:
        result, link_audit = tracker_link.transform(result)
        result = hover.transform(result)
        result = input_retry.transform(result)
        result = input_buffer.transform(result)
        from transition.events import action

        e = Events(result, low=0xD800, high=0xD900)
        result.append([e.row([e.start()], [action(32, 26, 59, [])])])
        social_audit.append(dict(frame=frame, tracker_link=link_audit))
    if frame == 20:
        result, options_link_audit = tracker_link.options_transform(result)
        social_audit.append(dict(frame=frame, tracker_link=options_link_audit))
    result, display_audit = options_display.transform(
        frame,
        result,
        routes.objects,
        options_display.with_options_instance(
            frame, routes.frames[frame - 1]["instances"]
        ),
    )
    result, locale_audit = options_locale.transform(frame, result)
    display_audit += locale_audit
    result, target_hud_audit = target_hud.transform(frame, result, routes.objects, routes.frames[frame - 1]["instances"])
    display_audit += target_hud_audit
    result, result_audit = results.transform(frame, result)
    display_audit += result_audit
    result, music_audit = runtime_music.transform(
        frame, result, routes.objects, routes.frames[frame - 1]["instances"]
    )
    result, solgryn_music_audit = solgryn_music.transform(
        frame, result, routes.objects, routes.frames[frame - 1]["instances"]
    )
    music_audit += solgryn_music_audit
    result, flame_audit = god_mode_flames.transform(frame, result, routes.objects)
    result, shake_audit = screen_shake.transform(
        frame, result, routes.objects, routes.frames[frame - 1]["instances"]
    )
    result, scenery_audit = runtime_scenery.transform(
        frame, result, routes.objects, routes.frames[frame - 1]["instances"]
    )
    result, background_audit = background_groups.transform(
        frame, result, routes.objects, routes.frames[frame - 1]["instances"]
    )
    scenery_audit += background_audit
    result, spider_audit = spider_events.transform(
        frame, result, routes.objects, routes.frames[frame - 1]["instances"], profile
    )
    result, death_audit = death_screen.transform(
        frame, result, routes.objects, routes.frames[frame - 1]["instances"]
    )
    result, presentation_audit = presentation_events.transform(frame, result)
    display_audit += presentation_audit
    result, title_audit = title_music.transform(frame, result)
    music_audit += title_audit
    from gameplay import tower_arrival

    result, tower_audit = tower_arrival.transform(
        frame, result, routes.objects, routes.frames[frame - 1]["instances"]
    )
    changes.extend(tower_audit)
    result, loop_audit = music_loops.transform(frame, result)
    music_audit += loop_audit
    from gameplay import save_transactions

    result, save_audit = save_transactions.transform(
        frame, result, routes.objects, routes.frames[frame - 1]["instances"]
    )
    changes.extend(
        save_audit
        + death_audit
        + dresser_audit
        + hub_audit
        + audit
        + extra_audit
        + credit_audit
        + social_audit
        + display_audit
        + music_audit
        + flame_audit
        + scenery_audit
        + shake_audit
        + shot_audit
        + shot_sound_audit
        + spider_audit
    )
    from gameplay.options_sync import transform as sync_bindings

    result, binding_audit = sync_bindings(frame, result)
    changes.extend(binding_audit)
    if frame == 2:
        from quality.build import stamp_sections

        result = stamp_sections(result)
    from gameplay import startup_loads

    result, startup_audit = startup_loads.transform(frame, result)
    changes.extend(startup_audit)
    return scenery_cache.finish(frame, result)


def frame(w, app, frame, index, objects, *args, **kwargs):
    objects = camera_lifetime.protect(objects)
    frame, objects = tracker_link.convert_frame(index + 1, frame, objects)
    frame, objects = dresser.convert_frame(index + 1, frame, objects)
    frame, objects = options_display.convert_frame(index + 1, frame, objects)
    frame, objects = presentation_events.convert_frame(index + 1, frame, objects)
    frame, objects = options_locale.convert_frame(index + 1, frame, objects)
    frame, objects = results.convert_frame(index + 1, frame, objects)
    frame, objects = target_hud.convert_frame(index + 1, frame, objects)
    frame, objects = death_screen.convert_frame(index + 1, frame, objects)
    frame, objects = background_groups.convert_frame(index + 1, frame, objects)
    frame, objects = runtime_scenery.convert_frame(index + 1, frame, objects)
    frame, objects = spider_object.convert_frame(index + 1, frame, objects)
    return classic.frame(w, app, frame, index, objects, *args, **kwargs)


if __name__ == "__main__":
    assert Path(sys.argv[1]).resolve() == routes.SOURCE.resolve()
    assert (
        routes.app.app_header()["frameRate"] == 50
    ), "Native gameplay timing requires original 50 Hz"
    display_build.install(routes.write_mfa)
    display_build.install_intro_lifetime(type(routes.app))
    scenery_cache.install(type(routes.app))
    type(routes.app).frame_handles = routes.handles
    routes.write_mfa._object_effect_chunk = routes.preserve_alpha_only
    routes.write_mfa._write_frame_item = (
        classic.targets.modes.cycle.rewards.pickups.intro.characters.onehit.gameplay.blood.item
    )
    embedded_blood.install(
        routes.write_mfa,
        classic.targets.modes.cycle.rewards.pickups.intro.characters.onehit.gameplay.blood,
    )
    routes.write_mfa._exe_event_sections = sections
    routes.write_mfa.inflated_images = attribution.image_loader(
        routes.write_mfa.inflated_images
    )
    routes.write_mfa.inflated_images = social.image_loader(
        routes.write_mfa.inflated_images
    )
    routes.write_mfa.inflated_images = death_screen.image_loader(
        routes.write_mfa.inflated_images
    )
    routes.write_mfa.inflated_images = background_groups.image_loader(
        routes.write_mfa.inflated_images
    )
    routes.write_mfa._write_frame = frame
    assert routes.main() == 0
    out = Path(sys.argv[sys.argv.index("--out") + 1])
    (out / "dynamic-source-audit.json").write_text(
        json.dumps(
            dict(scope=__doc__, runtime_reward_icons=changes, menu=classic.changes),
            indent=2,
        )
        + "\n"
    )
