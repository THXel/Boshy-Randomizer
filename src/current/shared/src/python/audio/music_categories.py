"""Gameplay music categories, independent of route RNG and cue sound effects.

See docs/MUSIC_CATEGORIES.md for the original-game evidence. Recognize the
existing private audio packs by both filename and digest, never by duration.
"""

import json
from functools import lru_cache
from pathlib import Path

BOSS_CUES = frozenset(
    {
        '255232_Bomberman',
        '321522_Jarrid_Langill___Wasteland',
        'Ace Combat  Megalith',
        'Burningheat(fulloptionmix)',
        'CHEETAHMENTHEME',
        'Do teh mario!',
        'Fight_Scene_MP3',
        'First Boss Music',
        'Ganon boss battle 1',
        'Kirby Bos',
        'Mario Boss Smithy',
        'Pokemon_Battle_Megamix',
        'Ryu Theme (2)',
        'Sonic_the_Hedgehog GREEN HILL',
        'WIld Pokemon',
        'mega_man_3_theme',
        'mountain stage kirby',
        'rose at midnight',
        'rose at nightfall',
        'sea of flames',
    }
)


def cue_kind(cue):
    return 'boss' if cue in BOSS_CUES else 'level'


@lru_cache(maxsize=1)
def audited_tracks():
    path = Path(__file__).with_name('soundpack-music-kinds.json')
    return json.loads(path.read_text(encoding='utf-8'))['packs']


def track_kind(pack, row):
    known = audited_tracks().get(pack, {}).get(row['file'])
    if known and known['sha256'] == row.get('sha256'):
        return known['kind']
    # Explicit metadata supports user-authored packs; an unknown file is never
    # silently guessed to be level music or mixed into both categories.
    kind = row.get('music_kind', 'excluded')
    return kind if kind in ('boss', 'level') else 'excluded'
