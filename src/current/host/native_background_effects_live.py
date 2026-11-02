"""Visible parallax motion and complete-layer dimming in the compiled game."""
import json
import uuid
from functools import partial
from PIL import Image, ImageChops, ImageStat
from native_menu import builds
from menu_host.store import Store, digest
from export_route_probe import ROOT

OUT = ROOT / 'outputs/Fusion-BackgroundGroups-20261026'
builds.DYNAMIC_BASE = builds.PREFIX / 'drive_c/BoshyTransitions/Boshy-dynamic-v39.exe'
builds.DYNAMIC_SHA = digest(builds.DYNAMIC_BASE)
from export_native_run import export
from menu_host.draft import Draft
from native_menu.combined import CombinedController
from native_menu_probe import pump
from native_classic_live import wait
from visuals.background_groups import mapping
import god_mode_live as capture

capture.OUT = OUT
report = dict(build=str(builds.DYNAMIC_BASE), sha256=builds.DYNAMIC_SHA, memory_writes=0)
store = Store(OUT / ('effects-' + uuid.uuid4().hex[:8]), exporter=partial(export, dynamic=True))
with store.lock():
    for slot, dim in [(1, 0), (2, 60), (3, 0)]:
        draft = Draft()
        draft.set_mode('level_rush')
        draft.update(level_pool=['save13.ini' if slot == 3 else 'save1.ini'],
                     level_count=1, boss_pool=[], route_boss_count=0,
                     no_mouse_ghost=True, god_mode=True, characters=False,
                     sprite_scenery=True, sprite_backgrounds=True,
                     sprite_decor=False, sprite_tiles=False, sprite_actors=False,
                     sprite_dim=dim)
        draft.seed = (next('BGROUP' + str(i) for i in range(2000)
                           if mapping('BGROUP' + str(i), True)[7] == 2)
                      if slot == 3 else 'BGROUP0')
        store.create(slot, draft)
    controller = CombinedController(store, dynamic=True)
    try:
        controller.open()
        controller.enter()
        means = []
        for slot in (1, 2, 3):
            controller.model.slot = slot
            controller.model.load_slot()
            controller.begin()
            wait(controller, lambda: controller.phase == 'playing')
            pump(controller, .6)
            capture.snap(controller.window, 'effects-' + str(slot))
            region = Image.open(OUT / ('effects-' + str(slot) + '.png')).crop((200, 20, 600, 130))
            if slot < 3:
                means.append(ImageStat.Stat(region.convert('L')).mean[0])
            else:
                pump(controller, 1.3)
                capture.snap(controller.window, 'effects-parallax-later')
                later = Image.open(OUT / 'effects-parallax-later.png').crop((200, 20, 600, 130))
                changed = ImageChops.difference(region, later).convert('L')
                report['parallax_changed_sky_pixels'] = sum(v > 5 for v in changed.getdata())
                assert report['parallax_changed_sky_pixels'] > 1000
            controller.window.key('F2')
            wait(controller, lambda: controller.phase == 'menu')
            controller.enter()
        report['background_brightness'] = means
        assert means[1] < means[0] * .5, means
        report['passed'] = True
        print(report, flush=True)
    finally:
        controller.close()
        (OUT / 'background-effects-live.json').write_text(json.dumps(report, indent=2) + '\n')
