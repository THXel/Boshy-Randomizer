from pathlib import Path
import json
from mixed_rewards import context
B=Path(__file__).resolve().parent
def build(target=None):
 target=Path(target or B).resolve()
 from build_icon_formats import build as build_icons
 build_icons(B)
 plan=json.loads((B/'slot_reward_plan.json').read_text(encoding='utf-8'))
 mapping={s['key']:dict(name=s['source'],kind=s['source_kind']) for s in plan['locations']}
 import struct
 path=lambda s:s.encode().ljust(260,b'\0')
 menu=struct.pack('<16I',0x424d4e31,1,*([0]*14))+path(str(target/'menu-runtime/frame.bmp').replace('/','\\'))+bytes(1024)+bytes(8)+path(str(target/'native_menu.dll').replace('/','\\'))+b'MenuTick'.ljust(32,b'\0')
 assert len(menu)==1648
 # Drive Z maps the host filesystem under Wine.
 menu=bytearray(menu)
 for off in (64,1356):
  v=bytes(menu[off:off+260]).split(b'\0')[0];menu[off:off+260]=(b'Z:'+v).ljust(260,b'\0')
 (B/'slot_reward_context.bin').write_bytes(context(plan,mapping,'')+menu+bytes(512))
if __name__=='__main__':build()
