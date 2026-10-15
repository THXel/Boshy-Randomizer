"""Compact share envelope: frozen BR3/4 settings plus exporter and rule identity.

The inner settings format stays unchanged. Legacy codes have unknown provenance,
never silently acquire the current version when copied or pasted.
"""
import base64,hashlib,json,struct
from pathlib import Path
from functools import lru_cache
RELEASE=20261015
RULE_FILES=('spider_randomizer.py','music_randomizer.py','run_settings.py','run_extras.py','native_level_route.py','native_triggers.py','native_progress.py','mixed_rewards.py','shot_cycle.py','character_cycle.py','beta_catalogue.py','minibosses.py','beta_bosses.py','native_targets.py','INI/positions.json','slot_reward_plan.json','INI/characters_rando.json')
def fingerprint(base):
 base=Path(base)
 try:signature=tuple((name,(base/name).stat().st_mtime_ns,(base/name).stat().st_size) for name in RULE_FILES)
 except FileNotFoundError:return bytes(8)
 return _fingerprint(str(base.resolve()),signature)

@lru_cache(maxsize=16)
def _fingerprint(base,signature):
 rows=[]
 for name in RULE_FILES:
  p=Path(base)/name
  if not p.is_file():return bytes(8)
  data=p.read_bytes()
  if name.endswith('.json'):data=json.dumps(json.loads(data),sort_keys=True,separators=(',',':')).encode()
  rows.append((name,hashlib.sha256(data).hexdigest()))
 return hashlib.sha256(json.dumps(rows,separators=(',',':')).encode()).digest()[:8]

def encode(seed,options,base=None):
 from run_settings import encode as core_encode
 code=core_encode(seed,options);version=int(code[2]);raw=base64.urlsafe_b64decode(code[4:]+'='*(-len(code[4:])%4))
 identity=fingerprint(base or Path(__file__).parent)
 payload=bytes([version])+struct.pack('>I',RELEASE)+identity+raw[:-4]
 packet=payload+hashlib.sha256(b'BR5\0'+payload).digest()[:4]
 return 'BR5-'+base64.urlsafe_b64encode(packet).decode().rstrip('=')

def unpack(value):
 try:
  if not value.startswith('BR5-') or len(value)>1024:raise ValueError()
  body=value[4:];packet=base64.b64decode(body+'='*(-len(body)%4),altchars=b'-_',validate=True)
  if len(packet)<19 or base64.urlsafe_b64encode(packet).decode().rstrip('=')!=body:raise ValueError()
  payload,checksum=packet[:-4],packet[-4:]
  if hashlib.sha256(b'BR5\0'+payload).digest()[:4]!=checksum:raise ValueError()
  version=payload[0];release=struct.unpack('>I',payload[1:5])[0]
  if version not in (3,4,6,7) or not 20200101<=release<=20991231:raise ValueError()
  raw=payload[13:];inner=raw+hashlib.sha256(f'BR{version}\0'.encode()+raw).digest()[:4]
  core=f'BR{version}-'+base64.urlsafe_b64encode(inner).decode().rstrip('=')
  return core,dict(release=release,rules=payload[5:13].hex())
 except (ValueError,IndexError,struct.error) as e:raise ValueError('Der geteilte Seed ist unvollständig oder beschädigt.') from e

def metadata(value):
 if str(value).strip().startswith('BR5-'):return unpack(str(value).strip())[1]
 return dict(release=None,rules=None)

def compatibility(value,base):
 info=metadata(value);current=fingerprint(base).hex()
 if not info['rules'] or info['rules']=='0000000000000000' or current=='0000000000000000':status='unknown'
 elif info['rules']!=current:status='different'
 else:status='matching'
 return dict(**info,status=status,current=RELEASE)

def version_text(value):
 if not value:return '–'
 s=str(value);return f'{s[:4]}.{s[4:6]}.{s[6:8]}'
