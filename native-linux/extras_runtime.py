"""Build a versioned optional blob; legacy runs keep their original bytecode."""
import json,struct
from mixed_rewards import CONTEXT_SIZE,context,validate
from run_extras import flags
ASSETS=('run_extras.py','extras_runtime.py','native_extras.dll','slot_reward_extras.bin','slot_reward_extras_symbols.json','death_character.py','shot_cycle.py','music_randomizer.py','spider_randomizer.py')
def run_blob(base,m):
 plan=json.loads((base/'slot_reward_plan.json').read_text());validate(m['rewards'],m['seed'],plan,enabled=m['options']['items'])
 raw=bytearray((base/'slot_reward_extras.bin').read_bytes());offset=json.loads((base/'slot_reward_extras_symbols.json').read_text())['context_offset']
 if len(raw)-offset!=CONTEXT_SIZE+2160:raise ValueError('Ungültiger Extras-Patch.')
 if m['options']['extras'].get('fast_chests',False):
  import copy
  plan=copy.deepcopy(plan)
  for loc in plan['locations']:
   for p in loc['patches']:
    b=bytearray.fromhex(p['new']);at=0
    for _ in range(p.get('new_conditions',p['conditions'])):
     size,kind,code=struct.unpack_from('<Hhh',b,at)
     if kind==2 and code==-27 and size>=46 and struct.unpack_from('<I',b,at+20)[0]==24:
      old=struct.unpack_from('<I',b,at+38)[0]
      if old in (200,250,315,330,360):struct.pack_into('<I',b,at+38,{200:0,250:1,315:2,330:3,360:4}[old])
     at+=size
    p['new']=b.hex()
 raw[offset:offset+CONTEXT_SIZE]=context(plan,m['rewards'],m['run_id'])
 struct.pack_into('<I',raw,offset+CONTEXT_SIZE+32,flags(m['options']))
 if m['options']['extras'].get('shot_mode','off')!='off':
  from shot_cycle import initial
  struct.pack_into('<III',raw,offset+CONTEXT_SIZE+2124,0x42534531,initial(base,m)['frame'],0)
 return bytes(raw),offset
