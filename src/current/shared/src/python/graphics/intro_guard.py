"""Attach the additive native intro fix without changing bound legacy assets."""

import hashlib
import json
import struct
from host_platform import native_path
from mixed_rewards import CONTEXT_SIZE

MENU_HASH = '07dbfff74b850c5ed60224f4f9b1a70e93ebe9c43340911870177b37bab84584'
GUARD_HASH = '7a6cefab982c30aad25825928c6046aad59180fc3d627d8c6fc2967de713d71f'
# The installed legacy build differs only in PE timestamps/checksum.
# Keep both exact, audited hashes; never disable integrity validation.
GUARD_HASHES = {
    GUARD_HASH,
    'c8f97c85655df69b1b69deaa641c2fa1cc947ce24480daa34c4c7b5d42a699c7',
}
EXTRAS_CURRENT = 'b57588042e66f82baaa5602e0d1acf1909ae1387534eddd874d189b4ecd6c002'
EXTRAS_LEGACY = {
    'f208f544433ca07d3791208810ff8a2fe871cfe8d0398431ce68fc5f8536ef38',
    '84fbf44ad3837565aa00fde595587a8ea3c6d20984aa056f65aa31dcfad93c99',
}


def extras_path(base, asset_base):
    current = base / 'native_extras.dll'
    saved = asset_base / 'native_extras.dll'
    # Same ABI and rules; only the engine's relocated chest-object cache index
    # is tolerated. Never upgrade an unknown frozen native implementation.
    if (
        hashlib.sha256(current.read_bytes()).hexdigest() == EXTRAS_CURRENT
        and hashlib.sha256(saved.read_bytes()).hexdigest() in EXTRAS_LEGACY
    ):
        return current
    return saved


def extras_compatible(base, asset_base):
    return (
        extras_path(base, asset_base).read_bytes()
        == (base / 'native_extras.dll').read_bytes()
    )


def attach(base, blob, *, context_offset=None, extras=False, asset_base=None):
    archived = asset_base is not None and asset_base != base
    asset_base = asset_base or base
    if (
        hashlib.sha256((base / 'native_menu_polished.dll').read_bytes()).hexdigest()
        != MENU_HASH
    ):
        raise RuntimeError('Die native Menü-Bibliothek fehlt oder wurde verändert.')
    path = asset_base / 'native_intro_guard.dll'
    if (
        not archived
        and hashlib.sha256(path.read_bytes()).hexdigest() not in GUARD_HASHES
    ):
        raise RuntimeError('Der native Intro-Schutz fehlt oder wurde verändert.')
    raw = bytearray(blob)
    context = (
        context_offset
        if context_offset is not None
        else json.loads(
            (base / 'slot_reward_symbols.json').read_text(encoding='utf-8')
        )['context_offset']
    )
    offset = context + CONTEXT_SIZE
    if struct.unpack_from('<II', raw, offset) != (0x424D4E31, 1):
        raise ValueError('Unbekannter Menü-Kontext.')
    old = bytes(raw[offset + 1356 : offset + 1616]).split(b'\0')[0]
    expected = native_path(base / 'native_menu.dll').encode()
    if old != expected:
        raise ValueError('Unbekannte native Menü-Bibliothek.')
    if extras:
        path = extras_path(base, asset_base)
        if not archived and hashlib.sha256(
            path.read_bytes()
        ).hexdigest() not in EXTRAS_LEGACY | {EXTRAS_CURRENT}:
            raise RuntimeError('Der Extras-Patch fehlt oder wurde verändert.')
    name = native_path(path).encode()
    if len(name) >= 260:
        raise ValueError('Bibliothekspfad ist zu lang.')
    raw[offset + 1356 : offset + 1616] = name.ljust(260, b'\0')
    return bytes(raw)
