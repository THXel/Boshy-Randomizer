"""One native Undertale soul at the player's world position at death.

Position is copied before the original player-destruction action. The active
scrolls with its world layer, independently of the viewport-fixed death screen.
Animation and early restart are handled by the engine, without host polling.
"""
import copy
import io
import json
from functools import lru_cache
from PIL import Image
from app_paths import SOUNDPACKS
from gameplay.spider_events import xy
from transition.events import action, expression, integer

OBJECT = 4401
FIRST_IMAGE = 22000
NAME = "Randomizer Death Soul"


@lru_cache(maxsize=1)
def assets():
    from visuals.death_screen import checked
    root = SOUNDPACKS / 'undertale'
    timeline = json.loads((root / 'pack.json').read_text())['death_visuals']['soul']
    rows, ticks, loop = (timeline[k] for k in ('frames', 'ticks', 'loop'))
    if not 1 <= len(rows) <= 100 or len(rows) != len(ticks) or type(loop) is not int or not 0 <= loop < len(rows):
        raise ValueError('Soul animation timeline')
    if any(type(t) is not int or not 1 <= t <= 50 for t in ticks):
        raise ValueError('Soul animation duration')
    images, frames = [], []
    handles = list(range(FIRST_IMAGE, FIRST_IMAGE + len(rows)))
    for handle, row, duration in zip(handles, rows, ticks):
        with Image.open(io.BytesIO(checked(root, row))) as im:
            if im.format != 'PNG' or im.size != (640, 480):
                raise ValueError('Soul animation geometry')
            images.append(im.convert('RGBA'))
        frames.extend([handle] * duration)
    from visuals.death_graphics import trim
    trimmed = [trim(image, (320,240)) for image in images]
    return dict(images=[p[0] for p in trimmed], origins=[p[1] for p in trimmed],
                handles=handles, frames=frames, loop=sum(ticks[:loop]))


def convert_frame(frame, objects, template):
    result = copy.deepcopy(frame)
    objects = dict(objects)
    assert OBJECT not in objects
    data = assets()
    obj = copy.deepcopy(objects[template])
    obj.update(handle=OBJECT, name=NAME, values=[0], qualifiers=[])
    def animation(slot, frames, back):
        return dict(slot=slot, name='Soul' if slot else 'Hidden', directions=[dict(
            direction=0, minSpeed=100, maxSpeed=100, repeat=0, backTo=back, frames=frames)])
    obj['animations'] = [animation(0, [data['handles'][-1]], 0), animation(18, data['frames'], data['loop'])]
    objects[OBJECT] = obj
    instance = copy.deepcopy(next(i for i in result['instances'] if i['objectInfo'] == template))
    instance.update(handle=59401, objectInfo=OBJECT)
    result['instances'].append(instance)
    return result, objects


def begin(player):
    # Keep these before the existing death actions: Player no longer exists later.
    return [action(2, 2, OBJECT, [expression(xy(player, 0))]),
            action(2, 3, OBJECT, [expression(xy(player, 1))]),
            action(2, 17, OBJECT, [expression(integer(18))]),
            action(2, 27, OBJECT, [])]
