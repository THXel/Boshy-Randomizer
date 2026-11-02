"""Presentation-only title music, using the old randomizer's opening tracks.

The engine retains ownership of playback, channels and volume. No host player,
run seed or gameplay music shuffle participates in this selection.
"""

import hashlib
import json
import struct
from pathlib import Path
from menu_host.store import atomic
from gameplay.native_events import Events
from gameplay.rewards import ini_string
from native_menu.presentation_events import VIEW
from transition.events import action, commands, event, expression, integer
from transition.router import guarded, params

GROUP = "TitleMusicV1"
CUE = "Intro Megaman X Infinity Mijinion stage"
TRACKS = {
    "undertale": ("mus_menu0.ogg", "f52bce7dca16f1631b7a6f1d51f712e7a778059cbd51908ff69c4011bd371456"),
    "kamilia3": ("Opening.ogg", "0754ad44f03df9fb79575f409b18566e24c53c749973cd38ddb63c64a9e32ed3"),
    "wannafest22": ("music/hwr_theme.ogg", "f746adc3f0d11717a8558246de7ca33f0355c2f6ece3544b5b0e4524a9230c09"),
}


def prepare(folder, pack, pack_root):
    if pack == "original":
        return dict(Enabled=0, Opening="")
    if pack not in TRACKS:
        raise ValueError("Unknown title soundtrack")
    root = Path(pack_root).resolve()
    name, expected = TRACKS[pack]
    manifest = json.loads((root / "pack.json").read_text(encoding="utf-8"))
    if manifest.get("version") != 1 or manifest.get("id") != pack:
        raise ValueError("Title soundtrack identity")
    rows = [r for r in manifest["tracks"] if "opening" in r.get("roles", [])]
    if len(rows) != 1 or rows[0]["file"] != name or rows[0]["sha256"] != expected:
        raise ValueError("Title soundtrack catalogue changed")
    source = root / name
    if source.is_symlink() or not source.resolve().is_relative_to(root):
        raise ValueError("Title soundtrack path")
    data = source.read_bytes()
    if not data.startswith(b"OggS") or hashlib.sha256(data).hexdigest() != expected:
        raise ValueError("Title soundtrack checksum")
    target = Path(folder) / "presentation-music" / ("title-" + expected[:16] + ".ogg")
    target.parent.mkdir(exist_ok=True)
    if target.is_symlink():
        raise ValueError("Linked title soundtrack cache")
    if not target.exists() or hashlib.sha256(target.read_bytes()).hexdigest() != expected:
        atomic(target, data)
    return dict(Enabled=1, Opening="presentation-music\\" + target.name)


def is_title(command):
    condition, kind, code, _, raw = command
    if condition or kind != -2 or code not in (11, 12):
        return False
    ps = params(raw)
    return bool(ps and ps[0][0] == 6 and ps[0][1][8:].split(b"\0", 1)[0].decode("latin1") == CUE)


def transform(number, sections):
    if number != 2:
        return sections, []
    e = Events(sections, low=0x1000, high=0xFFFE)
    result, changed = [], 0

    def clone(conditions):
        result = []
        for condition in conditions:
            raw = bytearray(condition)
            struct.pack_into("<H", raw, 14, e.ident())
            result.append(bytes(raw))
        return result

    for rows in sections:
        output = []
        for row in rows:
            cs = commands(row)
            if not any(is_title(c) for c in cs):
                output.append(row)
                continue
            conditions = [c[-1] for c in cs if c[0]]
            original = [c[-1] for c in cs if not c[0]]
            replacement = []
            for c in cs:
                if c[0]:
                    continue
                if not is_title(c):
                    replacement.append(c[-1])
                    continue
                # Apppath$ + persisted relative asset path. Keep the original
                # channel and loop parameters, along with surrounding actions.
                path = struct.pack("<hhH", -1, 8, 6) + struct.pack("<hhH", 0, 2, 6) + ini_string(GROUP, "Opening", "", VIEW)
                ps = params(c[-1])
                replacement.append(action(-2, 28 if c[2] == 11 else 29, 0, [expression(path, 45), *[p[1] for p in ps[1:]]]))
                changed += 1
            for enabled, actions in ((0, original), (1, replacement)):
                output.append(event(row, clone(guarded(conditions, [e.eq(VIEW, GROUP, "Enabled", enabled)])), actions))
        result.append(output)
    # Automatic intro effects must not claim the music channel before file
    # playback starts; gameplay uses the same reservation.
    result[0].insert(1, e.row(
        [e.start(), e.eq(VIEW, GROUP, "Enabled", 1)],
        [action(-2, 30, 0, [expression(integer(2))])],
    ))
    if changed != 1:
        raise ValueError("Expected exactly one native title-music event")
    return result, [dict(frame=number, title_music=changed, native_channel_preserved=True)]
