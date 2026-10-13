"""Versioned deterministic mixed chest assignments and native action records."""
import hashlib,json,struct
from pathlib import Path
MAX_SOURCES=40
PATCH_BYTES=512
LOCATION_SIZE=7508
CONTEXT_SIZE=124+MAX_SOURCES*LOCATION_SIZE+MAX_SOURCES*96

def rewards(plan):
 return sorted((dict(name=s['source'],kind=s['source_kind']) for s in plan['locations']),key=lambda x:(x['kind'],x['name']))
def assignments(seed,plan):
 pool=rewards(plan)
 assert len({(x['kind'],x['name']) for x in pool})==len(pool)
 def score(r):return hashlib.sha256(('mixed-chests-v1\0'+str(seed)+'\0'+r['kind']+'\0'+r['name']).encode()).digest()
 pool.sort(key=score)
 return {s['key']:r for s,r in zip(sorted(plan['locations'],key=lambda x:x['key']),pool)}
def validate(mapping,seed,plan,enabled=True):
 expected=assignments(seed,plan) if enabled else {l['key']:dict(name=l['source'],kind=l['source_kind']) for l in plan['locations']}
 if mapping!=expected:raise ValueError('Belohnungen passen nicht zum Seed.')
def literal(name):
 raw=name.encode('ascii')+b'\0';raw+=bytes(len(raw)%2)
 return struct.pack('<hhH',-1,3,len(raw)+6)+raw

def string_param(name):
 expr=literal(name)+bytes(4)
 return struct.pack('<HHH',len(expr)+6,45,0)+expr

def integer_param(value):return bytes.fromhex('140016000000ffff00000a00')+struct.pack('<I',value)+bytes(4)
def params(action):
 pos=14;out=[]
 for _ in range(action[12]):
  n=struct.unpack_from('<H',action,pos)[0];assert n>=6
  out.append(action[pos:pos+n]);pos+=n
 assert pos==len(action)
 return out

def action(template,parameters,ref=None):
 h=bytearray(template[:14]);h[12]=len(parameters)
 if ref:h[6:10]=ref
 data=h+b''.join(parameters);struct.pack_into('<H',data,0,len(data));return bytes(data)
def setter(template,ref,group,name):return action(template,[string_param(group),string_param(name),integer_param(0),integer_param(1)],ref)

def context(plan,mapping,session_id):
 assert len(plan['locations'])<=MAX_SOURCES
 assert not session_id or len(session_id)==32 and all(c in '0123456789abcdef' for c in session_id)
 out=struct.pack('<16I',0x42524832,7,0,0,0,0,0,0,0,0,0,0,len(plan['locations']),0,0,0)
 out+=session_id.encode().ljust(36,b'\0')+b'randochecks\0'+b'sessionid\0'.ljust(12,b'\0')
 assert len(out)==124
 icons=[]
 for loc in plan['locations']:
  reward=mapping[loc['key']];name=reward['name'];kind=reward['kind'];template=bytes.fromhex(loc['grant_template']);save=bytes.fromhex(loc['save_ref']);license=bytes.fromhex(loc['license_ref'])
  grant=setter(template,license if kind=='character' else save,'Unlockables' if kind=='character' else 'Collectables',name)
  extra=setter(template,save,'RandoChecks',loc['key'])
  assert len(grant)<=256 and len(extra)<=192
  data=struct.pack('<9I',loc['scene'],loc['object'],loc['grant_offset'],len(grant),len(extra),0,0,len(loc['patches']),struct.unpack_from('<H',save)[0])+loc['key'].lower().encode().ljust(8,b'\0')+grant.ljust(256,b'\0')+extra.ljust(192,b'\0')
  for p in loc['patches']:
   old,new,mask=(bytes.fromhex(p[k]) for k in ('old','new','mask'));assert len(old)==len(new)==len(mask)<=PATCH_BYTES
   data+=struct.pack('<4I',p['offset'],len(old),p['conditions']|(p.get('new_conditions',0)<<8),p['actions'])+old.ljust(PATCH_BYTES,b'\0')+new.ljust(PATCH_BYTES,b'\0')+mask.ljust(PATCH_BYTES,b'\xff')
  data+=bytes((4-len(loc['patches']))*(16+3*PATCH_BYTES))
  data+=struct.pack('<I',len(loc['display']))
  for d in loc['display']:
   old=bytes.fromhex(d['old']);ps=params(old)
   if (d['kind'],d['code'])==(-1,19):new=action(old,[ps[0],string_param(name)])
   elif (d['kind'],d['code'])==(32,49):new=action(old,[ps[0],string_param('\r\nBelohnung erhalten!\r\n'+name)])
   elif (d['kind'],d['code'])==(37,82):new=action(old,[string_param(('Charakter' if kind=='character' else 'Item')+' erhalten: '+name),string_param('RANDOMIZER')])
   else:raise ValueError('Unbekannte Anzeigeaktion')
   assert len(new)<=256
   data+=struct.pack('<IiI',d['offset'],d['kind'],len(new))+new.ljust(256,b'\0')
  data+=bytes((3-len(loc['display']))*268)
  assert len(data)==LOCATION_SIZE,len(data)
  out+=data
  path=(('..\\native-icons\\'+name+'.bmp') if name in ('Simon Belmont','Spike') else ('..\\Custom\\trophies\\'+name+'.png')).encode();assert len(path)<64
  icons.append(bytes(32)+path.ljust(64,b'\0'))
 out+=bytes((MAX_SOURCES-len(plan['locations']))*LOCATION_SIZE)
 out+=b''.join(icons)+bytes((MAX_SOURCES-len(icons))*96)
 assert len(out)==CONTEXT_SIZE
 return out

def run_blob(base,m):
 base=Path(base);plan=json.loads((base/'slot_reward_plan.json').read_text());validate(m['rewards'],m['seed'],plan,enabled=m['options']['items'])
 blob=bytearray((base/'slot_reward_hook.bin').read_bytes());offset=json.loads((base/'slot_reward_symbols.json').read_text())['context_offset']
 assert len(blob)-offset==CONTEXT_SIZE+2160,(len(blob),offset,CONTEXT_SIZE)
 blob[offset:offset+CONTEXT_SIZE]=context(plan,m['rewards'],m['run_id']);struct.pack_into('<I',blob,offset+CONTEXT_SIZE+32,(int(m['options']['characters'])|(2 if m['options'].get('mode')=='target' else 0)));return bytes(blob)
