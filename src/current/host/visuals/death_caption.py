"""Small native, localized typewriter captions over the shared death screen."""
import copy
import io
import json
from functools import lru_cache
from PIL import Image
from app_paths import SOUNDPACKS
from music.death_text import ANIMATIONS
from visuals.death_graphics import trim
from gameplay.spider_events import window
from gameplay.native_events import Events
from transition.events import action, expression, integer, ini_value
from visuals.player_blood import GROUP

OBJECT = 4402
NAME = "Randomizer Death Caption"
FIRST_IMAGE = 23000


@lru_cache(maxsize=1)
def assets():
    from visuals.death_screen import checked
    root = SOUNDPACKS / "undertale"
    captions = json.loads((root / "pack.json").read_text())["death_visuals"]["captions"]
    result = {}
    handle = FIRST_IMAGE
    for language, animation in ANIMATIONS.items():
        timeline = captions[language]
        rows, ticks, loop = (timeline[k] for k in ("frames", "ticks", "loop"))
        if not 1 <= len(rows) <= 100 or len(rows) != len(ticks) or loop != len(rows)-1:
            raise ValueError("Death caption timeline")
        if any(type(t) is not int or not 1 <= t <= 50 for t in ticks) or sum(ticks) > 512:
            raise ValueError("Death caption duration")
        images, origins, frames, handles = [], [], [], []
        for row, duration in zip(rows, ticks):
            with Image.open(io.BytesIO(checked(root, row))) as image:
                if image.format != "PNG" or image.size != (400, 80):
                    raise ValueError("Death caption geometry")
                image, origin = trim(image.convert("RGBA"), (0,0))
            images.append(image);origins.append(origin);handles.append(handle)
            frames.extend([handle]*duration);handle += 1
        result[language] = dict(animation=animation,images=images,origins=origins,
                                handles=handles,frames=frames,loop=sum(ticks[:loop]))
    return result


def convert_frame(frame, objects, template):
    objects = dict(objects)
    if OBJECT in objects:
        raise ValueError("Death caption handle collision")
    obj = copy.deepcopy(objects[template])
    obj.update(handle=OBJECT,name=NAME,values=[0],qualifiers=[])
    obj["animations"] = []
    for language, data in assets().items():
        obj["animations"].append(dict(slot=data["animation"],name=language,directions=[dict(
            direction=0,minSpeed=100,maxSpeed=100,repeat=0,backTo=data["loop"],frames=data["frames"])]))
    hidden = copy.deepcopy(obj["animations"][0]);hidden.update(slot=0,name="Hidden")
    hidden["directions"][0].update(frames=[assets()["en"]["handles"][0]],backTo=0)
    obj["animations"].insert(0,hidden);objects[OBJECT]=obj
    instance = copy.deepcopy(next(i for i in frame["instances"] if i["objectInfo"]==template))
    instance.update(handle=59402,objectInfo=OBJECT)
    frame["instances"].append(instance)
    return frame,objects


def position():
    return [action(2,2,OBJECT,[expression(Events.add(window(0),integer(150)))]),
            action(2,3,OBJECT,[expression(Events.add(window(1),integer(285)))])]


def begin(save):
    return [*position(),
            action(2,17,OBJECT,[expression(ini_value(GROUP,"CaptionAnimation",ANIMATIONS["en"],oi=save))]),
            action(2,27,OBJECT,[])]
