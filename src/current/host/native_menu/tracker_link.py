"""One visible tracker card and one native click, shared by both title pages."""

import struct
from gameplay.native_events import Events
from native_menu import events as menu
from tracker.server import URL
from transition.events import action, expression, integer, parameter, string

BOUNDS = (6, 22, 148, 50)
LABEL = "Open LiveTracker"


def contains(x, y):
    return BOUNDS[0] <= x <= BOUNDS[2] and BOUNDS[1] <= y <= BOUNDS[3]


def draw(draw, fonts, *, busy=False, hover=False):
    left, top, right, bottom = BOUNDS
    edge = "#435767" if busy else "#b5f5df" if hover else "#86bfce"
    ink = "#71818d" if busy else "#edf5f6"
    draw.rounded_rectangle(BOUNDS, radius=4, fill=(16, 29, 39, 235), outline=edge)
    draw.line((left + 8, top + 1, right - 8, top + 1), fill=edge)
    draw.text((left + 9, top + 8), LABEL, font=fonts[12], fill=ink)


def transform(sections):
    e = Events(sections, low=0xD600, high=0xD700)
    mouse_x = struct.pack("<hhH", -6, 0, 6)
    mouse_y = struct.pack("<hhH", -6, 1, 6)
    left, top, right, bottom = BOUNDS
    click = menu.condition(
        -6, -5, 0, [parameter(32, struct.pack("<IH", 0, 0))], e.ident()
    )
    conditions = [
        click,
        e.eq(menu.VIEW, menu.GROUP, "Schema", 3),
        e.eq(menu.VIEW, menu.GROUP, "Enabled", 1),
        e.eq(menu.VIEW, menu.GROUP, "Busy", 0),
        e.cmp(mouse_x, integer(left), 4),
        e.cmp(mouse_x, integer(right), 3),
        e.cmp(mouse_y, integer(top), 4),
        e.cmp(mouse_y, integer(bottom), 3),
    ]
    # Reuse the original Open URLs extension. Fusion detects the click; no
    # global mouse hook, save transition, seed generation or input injection.
    native_open = action(40, 80, 7, [expression(string(URL), 45)])
    result = [list(rows) for rows in sections]
    result.append([e.row(conditions, [native_open])])
    return result, dict(
        url=URL,
        bounds=BOUNDS,
        original_open_urls_object=7,
        native_click=True,
        no_save_or_seed_actions=True,
    )


OPTIONS_CARD = 4511
OPTIONS_OPEN = 4512


def prepare(folder, fonts):
    """Reuse exactly the title card, with transparent surroundings."""
    from PIL import Image, ImageDraw
    from menu_host.store import atomic
    import io
    for hover, name in ((False, 'tracker'), (True, 'tracker-hover')):
        image = Image.new('RGBA', (154, 54))
        draw(ImageDraw.Draw(image), fonts, hover=hover)
        data = io.BytesIO()
        image.save(data, format='PNG')
        atomic(folder / ('native-options/' + name + '.png'), data.getvalue())


def convert_frame(number, frame, objects):
    if number != 20:
        return frame, objects
    import copy
    result = copy.deepcopy(frame)
    objs = dict(objects) if isinstance(objects, dict) else dict(enumerate(objects))
    for oi, template, name in ((OPTIONS_CARD,41,'Options LiveTracker'),(OPTIONS_OPEN,7,'Options Open LiveTracker')):
        assert oi not in objs
        obj = copy.deepcopy(objs[template]);obj.update(handle=oi,name=name)
        if oi == OPTIONS_CARD:
            obj.update(values=[0],qualifiers=[])
            props = bytearray(obj['properties'])
            struct.pack_into('<I',props,16,struct.unpack_from('<I',props,16)[0] | 0x6800)
            obj['properties'] = bytes(props)
        objs[oi] = obj
        result['instances'].append(dict(handle=59430+oi-OPTIONS_CARD,objectInfo=oi,x=0,y=0,layer=1,parentType=0,parentObjectInfo=0,tail='00 '*8))
    return result, objs


def options_transform(sections):
    from native_menu.classic_events import load
    from native_menu.events import alt, value
    e = Events(sections,low=0x1000,high=0xFFFE)
    result = [list(rows) for rows in sections]
    x = struct.pack('<hhH',-6,0,6)
    y = struct.pack('<hhH',-6,1,6)
    left,top,right,bottom = BOUNDS
    result.append([
        e.row([e.start()],[load(OPTIONS_CARD,'native-options/tracker.png')]),
        e.row([
            menu.condition(-6,-5,0,[parameter(32,struct.pack('<IH',0,0))],e.ident()),
            e.cmp(x,integer(left),4),e.cmp(x,integer(right),3),
            e.cmp(y,integer(top),4),e.cmp(y,integer(bottom),3),
        ],[action(40,80,OPTIONS_OPEN,[expression(string(URL),45)])]),
    ])
    # Decode an image only when hover changes, never on every game frame.
    result[-1].append(e.row([
        e.cmp(alt(OPTIONS_CARD, 0), integer(0)),
        e.cmp(x, integer(left), 4), e.cmp(x, integer(right), 3),
        e.cmp(y, integer(top), 4), e.cmp(y, integer(bottom), 3),
    ], [load(OPTIONS_CARD, 'native-options/tracker-hover.png'),
        value(OPTIONS_CARD, 0, integer(1))]))
    for axis, boundary, comparison in ((x,left,2),(x,right,5),(y,top,2),(y,bottom,5)):
        result[-1].append(e.row([
            e.cmp(alt(OPTIONS_CARD, 0), integer(1)),
            e.cmp(axis, integer(boundary), comparison),
        ], [load(OPTIONS_CARD, 'native-options/tracker.png'),
            value(OPTIONS_CARD, 0, integer(0))]))
    return result, dict(url=URL,bounds=BOUNDS,scrolling_independent=True,native_click=True)
