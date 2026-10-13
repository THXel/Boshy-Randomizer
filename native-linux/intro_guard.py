"""Attach the additive native intro fix without changing bound legacy assets."""
import hashlib,json,struct
from mixed_rewards import CONTEXT_SIZE
GUARD_HASH='7a6cefab982c30aad25825928c6046aad59180fc3d627d8c6fc2967de713d71f'
def attach(base,blob,*,context_offset=None,extras=False,asset_base=None):
 archived=asset_base is not None and asset_base!=base
 asset_base=asset_base or base
 if hashlib.sha256((base/'native_menu_polished.dll').read_bytes()).hexdigest()!='d2f81eecbc65281ad94d6cffc4f3d7d564a08e04e26425efa7cb4791125ce20c':raise RuntimeError('Die native Menü-Bibliothek fehlt oder wurde verändert.')
 path=asset_base/'native_intro_guard.dll'
 if not archived and hashlib.sha256(path.read_bytes()).hexdigest()!=GUARD_HASH:raise RuntimeError('Der native Intro-Schutz fehlt oder wurde verändert.')
 raw=bytearray(blob);context=context_offset if context_offset is not None else json.loads((base/'slot_reward_symbols.json').read_text())['context_offset'];offset=context+CONTEXT_SIZE
 if struct.unpack_from('<II',raw,offset)!=(0x424d4e31,1):raise ValueError('Unbekannter Menü-Kontext.')
 old=bytes(raw[offset+1356:offset+1616]).split(b'\0')[0]
 expected=('Z:'+str(base/'native_menu.dll').replace('/','\\')).encode()
 if old!=expected:raise ValueError('Unbekannte native Menü-Bibliothek.')
 if extras:
  path=asset_base/'native_extras.dll'
  if not archived and hashlib.sha256(path.read_bytes()).hexdigest()!='f208f544433ca07d3791208810ff8a2fe871cfe8d0398431ce68fc5f8536ef38':raise RuntimeError('Der Extras-Patch fehlt oder wurde verändert.')
 name=('Z:'+str(path).replace('/','\\')).encode()
 if len(name)>=260:raise ValueError('Bibliothekspfad ist zu lang.')
 raw[offset+1356:offset+1616]=name.ljust(260,b'\0')
 return bytes(raw)
