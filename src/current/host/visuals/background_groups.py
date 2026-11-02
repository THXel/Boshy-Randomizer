"""Whole reviewed landscapes: artwork, placement, cloud motion and parallax.

The nine sets and deterministic selection match the former randomizer. Native
Fusion objects own all images/effects; no runtime image-bank or process patches.
Only listed layer-zero cosmetics are replaced. Collision-bearing scenery is not.
"""
import copy
import hashlib
import json
import math
import struct
from functools import lru_cache
from pathlib import Path

from gameplay.native_events import Events
from transition.events import action, expression, integer, ini_value
from transition.router import frame_metadata

from app_paths import REPO
CATALOGUE = REPO / 'assets/catalogues/background_sets_catalogue.json'
GROUP = 'FusionSceneryV1'
PREFIX = 'Randomizer Background Group '
FIRST = 4600
DIM_OBJECT = 4625
DIM_IMAGE = 30000
DIM_NAME = "Randomizer Background Shade"


@lru_cache(maxsize=1)
def catalogue():
    return json.loads(CATALOGUE.read_text())


def owned():
    return {r['oi'] for r in catalogue()['objects']}


def helper(index):
    return FIRST + index


def target_index(frame):
    return next((i for i, s in enumerate(catalogue()['sets']) if s['scene'] + 1 == frame), None)


def mapping(seed, shuffle):
    sets = catalogue()['sets']
    result = []
    for i, target in enumerate(sets):
        candidates = [n for n,s in enumerate(sets) if not target['locked'] or s['coefficient'] == target['coefficient']]
        alternatives = [n for n in candidates if n != i]
        result.append(min(alternatives or candidates, key=lambda n: hashlib.sha256(
            f'boshy-background-set-v1\0{seed}\0{i}\0{n}'.encode()).digest()) if shuffle else i)
    return result


def settings(seed, options):
    enabled = options.get('sprite_scenery', False)
    choices = mapping(seed, enabled and options.get('sprite_backgrounds', False))
    return dict(BackgroundSchema=1, BackgroundDim=options.get('sprite_dim',0) if enabled else 0,
                **{'BackgroundSet'+str(i): v for i,v in enumerate(choices)})


def placements(target, source):
    sets = catalogue()['sets']; rows = catalogue()['objects']; s = sets[source]
    width = max(i['x']+rows[i['object']]['width'] for i in s['instances'] if rows[i['object']]['type']==1)
    repeat = max(1, math.ceil((640+sets[target]['width']*s['coefficient'])/width))
    assert 1 <= repeat <= 16
    for inst in s['instances']:
        row = rows[inst['object']]
        for n in range(1 if row['cloud'] or row['type']==48 else repeat):
            yield inst['object'], inst['x']+width*n, inst['y']


def convert_frame(number, frame, objects):
    target = target_index(number)
    if target is None:
        return frame, objects
    result = copy.deepcopy(frame)
    objs = dict(objects) if isinstance(objects,dict) else dict(enumerate(objects))
    own = {catalogue()['objects'][i['object']]['oi'] for i in catalogue()['sets'][target]['instances']}
    # Retain original object definitions for their old events. Static backgrounds
    # cannot be hidden by an event, so move only reviewed, non-colliding ones away.
    for inst in result['instances']:
        if inst['layer']==0 and inst['objectInfo'] in own and objs[inst['objectInfo']]['type']==1:
            assert struct.unpack_from('<I',objs[inst['objectInfo']]['properties'],4)[0]==0
            inst['x']=inst['y']=-32000
    for index,row in enumerate(catalogue()['objects']):
        ident=helper(index)
        obj=copy.deepcopy(objs[row['oi']] if row['type']==48 else objs[41])
        obj.update(handle=ident,name=PREFIX+str(index),qualifiers=[],values=[],strings=[])
        for key in ('inkEffect','inkEffectParameter','shader'):
            obj[key]=copy.deepcopy(objs[row['oi']][key])
        if row['type']!=48:
            obj['animations']=[dict(slot=0,name='Stopped',directions=[dict(direction=0,minSpeed=0,maxSpeed=0,repeat=1,backTo=0,frames=[row['image']])])]
        objs[ident]=obj
    next_handle=max(i['handle'] for i in result['instances'])+1
    for source in range(len(catalogue()['sets'])):
        for index,x,y in placements(target,source):
            result['instances'].append(dict(handle=next_handle,objectInfo=helper(index),x=x,y=y,layer=0,
                parentType=0,parentObjectInfo=0,tail='00 '*8))
            next_handle+=1
    shade = copy.deepcopy(objs[41])
    shade.update(handle=DIM_OBJECT, name=DIM_NAME, qualifiers=[], values=[], strings=[])
    props = bytearray(shade['properties'])
    struct.pack_into('<I', props, 16, struct.unpack_from('<I', props, 16)[0] | 0x6000)
    shade['properties'] = bytes(props)
    shade['animations'] = [dict(slot=0, name='Stopped', directions=[dict(
        direction=0, minSpeed=0, maxSpeed=0, repeat=1, backTo=0, frames=[DIM_IMAGE])])]
    objs[DIM_OBJECT] = shade
    result['instances'].append(dict(handle=next_handle, objectInfo=DIM_OBJECT,
        x=0, y=0, layer=0, parentType=0, parentObjectInfo=0, tail='00 '*8))
    return result,objs


def x(oi):
    return struct.pack('<hhHHH',2,11,10,oi,0)


def transform(frame, sections, objects, instances):
    target=target_index(frame)
    if target is None:return sections,[]
    ini,_,_=frame_metadata(frame,sections,objects,instances)
    e=Events(sections,low=0x1000,high=0xfffe)
    sets=catalogue()['sets']; objectspec=catalogue()['objects']
    key='BackgroundSet'+str(target)
    selected=ini_value(GROUP,key,target,oi=ini)
    rows=[e.row([e.start()],[e.load(ini,'SaveFile1.ini')])]
    own={objectspec[i['object']]['oi'] for i in sets[target]['instances']}
    rows.append(e.row([e.start()],[action(objects[oi]['type'],24,oi,[]) for oi in sorted(own) if objects[oi]['type']>=2]))
    assert objects[84]['name']=='Layer object' and objects[84]['type']==51
    for source,s in enumerate(sets):
        indices=sorted({i['object'] for i in s['instances']})
        # Layer.mfx ABI: action 40 sets X coefficient; 47 sets RGB coefficient.
        # Read from installed extension's eventInformations2 table (GetActionInfos).
        coefficient=struct.pack('<hhHdf',-1,23,18,s['coefficient'],s['coefficient'])
        rows.append(e.row([e.start(),e.cmp(selected,integer(source))], [
            action(51,120,84,[expression(integer(1),71),expression(coefficient)])]))
        rows.append(e.row([e.start(),e.cmp(selected,integer(source),1)], [
            action(objectspec[i]['type'] if objectspec[i]['type']==48 else 2,24,helper(i),[]) for i in indices]))
    # Standard Fusion rendering ignores hardware-only layer RGB coefficients.
    # One translucent black Active covers the completed composition, underneath
    # every gameplay layer. Its position follows this layer's camera coefficient.
    for dim in (0, 20, 40, 60):
        rows.append(e.row([e.start(), e.eq(ini,GROUP,'BackgroundDim',dim)], [
            action(2,39,DIM_OBJECT,[expression(integer(round(128*(1-dim/100))))])]))
    for source, scenery in enumerate(sets):
        coefficient = struct.pack('<hhHdf', -1,23,18, scenery['coefficient'], scenery['coefficient'])
        left = struct.pack('<hhH', -3,2,6)
        top = struct.pack('<hhH', -3,4,6)
        horizontal = left + struct.pack('<hhH', 0,6,6) + coefficient
        rows.append(e.row([e.cmp(selected,integer(source))], [
            action(2,2,DIM_OBJECT,[expression(horizontal)]),
            action(2,3,DIM_OBJECT,[expression(top)])]))
    for index,row in enumerate(objectspec):
        oi=helper(index)
        if row['cloud']:
            rows.append(e.row([struct.pack('<HhhHHHBBH',16,-1,-1,0,0,0x20,0,0,e.ident())], [action(2,2,oi,[expression(e.add(x(oi),integer(row['speed'])))])]))
            left=struct.pack('<hhH',-3,2,6)
            rows.append(e.row([e.cmp(x(oi),e.add(left,integer(-row['width'])),3)],[action(2,2,oi,[expression(e.add(left,integer(640)))])]))
        elif row['type']==48:
            offset=struct.pack('<hhHHH',48,80,10,oi,0)
            rows.append(e.row([struct.pack('<HhhHHHBBH',16,-1,-1,0,0,0x20,0,0,e.ident())], [action(48,80,oi,[expression(e.add(offset,integer(1)))])]))
    result=[list(s) for s in sections]
    # Finish all original start initialization before selecting our cosmetic group.
    result.append(rows)
    return result,[dict(frame=frame,rule='whole_background_group',target=target,sets=len(sets),owned=sorted(own))]


def image_loader(original):
    """Embed one tiny-compressing opaque mask; no external graphics dependency."""
    from PIL import Image
    from visuals.embedded_blood import raw_image

    def load(app):
        images = dict(original(app))
        if DIM_IMAGE in images:
            raise ValueError('Background mask image handle collision')
        images[DIM_IMAGE] = raw_image(Image.new('RGBA',(640,480),(0,0,0,255)), (0,0))
        return images

    return load
