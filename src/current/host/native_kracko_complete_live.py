"""Natural Kracko fight and next-screen exit; native extras, no memory writes."""
import json
import subprocess
import time
import uuid
from functools import partial
from export_route_probe import ROOT
from export_native_run import export
from menu_host.store import Store, save
from menu_host.draft import Draft
from native_menu.combined import CombinedController
from native_menu_probe import pump
from native_classic_live import wait
from native_menu.observe import objects
from transition.router import GROUP
from god_mode_boss_probe import values
from native_menu import builds
import god_mode_live as capture

OUT = ROOT / 'outputs/Fusion-BackgroundGroups-20261026'
capture.OUT = OUT
report = dict(scope=__doc__, build=str(builds.DYNAMIC_BASE), sha256=builds.DYNAMIC_SHA,
              memory_writes=0, samples=[])
store = Store(OUT / ('kracko-' + uuid.uuid4().hex[:8]), exporter=partial(export, dynamic=True))
with store.lock():
    draft = Draft()
    draft.set_mode('boss_rush')
    draft.update(boss_pool=['kracko'], route_boss_count=1, level_pool=[], level_count=0,
                 no_mouse_ghost=True, god_mode=True, autofire=True, characters=False,
                 sprite_scenery=True, sprite_backgrounds=True, sprite_decor=True,
                 sprite_tiles=True, sprite_actors=True)
    draft.seed = 'KRACKO-NATURAL-V39'
    store.create(1, draft)
    controller = CombinedController(store, dynamic=True)
    try:
        controller.open()
        controller.enter()
        controller.model.slot = 1
        controller.model.load_slot()
        controller.begin()
        wait(controller, lambda: controller.phase == 'playing')
        controller.window.key('Right')
        subprocess.run(['xdotool', 'keydown', 'x'], check=True)
        start = time.monotonic()
        last = -1
        while time.monotonic() - start < 180:
            if controller.window.reader.frame() == 'Options':
                report['options_interruptions'] = report.get('options_interruptions', 0) + 1
                assert report['options_interruptions'] <= 1, 'Repeated options interruption'
                controller.window.key('Escape')
                pump(controller, 1)
                start = time.monotonic()
            controller.window.key('Shift_L')
            pump(controller, .55)
            cfg = save(controller.folder / 'SaveFile1.ini')
            if cfg.getint(GROUP, 'KrackoVictory', fallback=0):
                report['native_victory'] = True
                break
            elapsed = round(time.monotonic() - start, 1)
            if int(elapsed) // 10 != last:
                last = int(elapsed) // 10
                sample = dict(seconds=elapsed, objects=[
                    dict(name=o['name'], x=o['x'], y=o['y'], values=values(controller.window.reader, o, 5))
                    for o in objects(controller.window.reader) if o['name'] in ['Player', 'Active 83']])
                report['samples'].append(sample)
                print(json.dumps(sample), flush=True)
                capture.snap(controller.window, 'kracko-fight-' + str(last))
        subprocess.run(['xdotool', 'keyup', 'x'], check=True)
        assert report.get('native_victory'), 'Kracko did not reach native victory'
        capture.snap(controller.window, 'kracko-victory')
        subprocess.run(['xdotool', 'keydown', 'Right'], check=True)
        try:
            end = time.monotonic() + 12
            while time.monotonic() < end:
                pump(controller, .15)
                cfg = save(controller.folder / 'SaveFile1.ini')
                if cfg.getint(GROUP, 'Done10', fallback=0):
                    break
        finally:
            subprocess.run(['xdotool', 'keyup', 'Right'], check=True)
        wait(controller, lambda: controller.window.reader.frame() == 'Eleventh Boss - Solgryn')
        report['arrival'] = dict(cfg[GROUP])
        report['frame'] = controller.window.reader.frame()
        assert cfg.getint(GROUP, 'Done10') == 1
        assert cfg.getint(GROUP, 'CurrentStage') == 23
        capture.snap(controller.window, 'kracko-arrival')
        controller.window.key('q')
        pump(controller, .6)
        assert not any(o['name'] == 'Player' for o in objects(controller.window.reader))
        controller.window.key('r')
        pump(controller, .8)
        assert any(o['name'] == 'Player' for o in objects(controller.window.reader))
        report['death_retry_after_exit'] = True
        report['passed'] = True
    finally:
        subprocess.run(['xdotool', 'keyup', 'x', 'Right', 'Shift_L'], check=True)
        controller.close()
        (OUT / 'kracko-complete-live.json').write_text(json.dumps(report, indent=2) + '\n')
