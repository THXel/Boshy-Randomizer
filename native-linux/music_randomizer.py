"""Seeded music swaps, extracted only from the user's verified game copy.

Names are stable; runtime sample handles are local to each room. Short jingles,
spoken cues and CD/item sounds deliberately do not belong to this catalogue.
"""
import hashlib,json,struct,zlib
from pathlib import Path

SOURCE_TRACKS=(
 '232446_Street_Shinobi','255232_Bomberman','321522_Jarrid_Langill___Wasteland',
 'Ace Combat  Megalith','Burningheat(fulloptionmix)','CHEETAHMENTHEME','Castlevania',
 'Cavestory - on to grasstown','CeladonTrance','Do teh mario!','Duck Tales - The Himalayas',
 'Fight_Scene_MP3','First Boss Music','Ganon boss battle 1','Kirby Bos','Legends of Azeroth',
 'Mario Boss Smithy','Mega Metal Man4','MetalGearEncounter','Mulgore - World of Warcraft Cataclysm OST',
 'NinjaGaiden (2)','Pokemon_Battle_Megamix','Prehistorik2Boss (2)','Robotnik sonic 2',
 'Ryu Theme (2)','SMW_SpeedRemix (2)','SavageSecret','Sonic_the_Hedgehog GREEN HILL',
 'WIld Pokemon','cheetah new','forest-stage-kirby-s-adventure-','greengreens',
 'kid icarus underworld theme','mega_man_3_theme','mountain stage kirby','plainsstageKirby',
 'relax','rose at midnight','rose at nightfall','sea of flames','stormwind',
 'terranigma-theunderworld','vvv positive force','warioland stage','wilystage',
)
# Keep the original cue recognized, but never choose this song as replacement.
EXCLUDED_TRACKS=frozenset({'Do teh mario!'})
TRACKS=tuple(name for name in SOURCE_TRACKS if name not in EXCLUDED_TRACKS)
MAGIC=b'BRM1'

def mapping(seed):
 # Versioned independent hash ordering never consumes route/reward RNG.
 order=sorted(SOURCE_TRACKS,key=lambda name:hashlib.sha256(('boshy-music-v1\0'+str(seed)+'\0'+name).encode()).digest())
 # Bypass excluded destinations in the stable cycle: unrelated swaps stay put.
 cycle={name:order[(i+1)%len(order)] for i,name in enumerate(order)}
 result={}
 for name in SOURCE_TRACKS:
  target=cycle[name]
  while target in EXCLUDED_TRACKS:target=cycle[target]
  result[name]=target
 return result

def extract(path,expected,*,names=TRACKS):
 data=Path(path).read_bytes()
 if hashlib.sha256(data).hexdigest()!=expected or data[2495611:2495615]!=b'PAME':raise ValueError('Unsupported game checksum')
 at=2495627;bank=None
 while at+8<=len(data):
  kind,flags,size=struct.unpack_from('<HHI',data,at);at+=8
  if at+size>len(data):raise ValueError('Sound bank bounds')
  if kind==0x6668:
   if flags:raise ValueError('Sound bank flags')
   bank=data[at:at+size];break
  at+=size
 if bank is None:raise ValueError('Missing sound bank')
 count=struct.unpack_from('<I',bank)[0];at=4;found={}
 if count>4096:raise ValueError('Sound bank count')
 for _ in range(count):
  if at+32>len(bank):raise ValueError('Sound header bounds')
  handle,checksum,refs,length,flags,frequency,namelen,packed=struct.unpack_from('<8I',bank,at);at+=32
  if not 0<namelen<=256 or not namelen<=length<=32_000_000 or at+packed>len(bank):raise ValueError('Sound size')
  dec=zlib.decompressobj();raw=dec.decompress(bank[at:at+packed],length+1);at+=packed
  if len(raw)!=length or not dec.eof or dec.unused_data:raise ValueError('Sound length')
  name=raw[:namelen].split(b'\0')[0].decode('latin1');audio=raw[namelen:]
  if name in names:
   if not audio.startswith((b'OggS',b'RIFF',b'ID3')):raise ValueError('Unsupported music encoding: '+name)
   if name in found and found[name]!=audio:raise ValueError('Ambiguous music sample: '+name)
   found[name]=audio
 if at!=len(bank) or set(found)!=set(names):raise ValueError('Incomplete music catalogue: '+str(set(names)-set(found)))
 return found

def prepare(base,manifest):
 from lab import EXPECTED
 from native_session import atomic
 base=Path(base);folder=base/'menu-runtime';folder.mkdir(exist_ok=True)
 plan=folder/'music.bin'
 if not manifest['options'].get('extras',{}).get('music',False):
  atomic(plan,MAGIC+bytes(36));return
 session=manifest['run_id']
 if len(session)!=32 or any(c not in '0123456789abcdef' for c in session):raise ValueError('Music session')
 tracks=extract(base/'IWBTB/I Wanna Be The Boshy.exe',EXPECTED)
 cache=folder/'music';cache.mkdir(exist_ok=True);paths={}
 for name,audio in tracks.items():
  digest=hashlib.sha256(audio).hexdigest();filename=digest[:24]+('.ogg' if audio.startswith(b'OggS') else '.mp3' if audio.startswith(b'ID3') else '.wav');path=cache/filename
  if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=digest:atomic(path,audio)
  paths[name]='..\\menu-runtime\\music\\'+filename
 swaps=mapping(manifest['seed']);raw=bytearray(MAGIC+session.encode()+struct.pack('<I',len(SOURCE_TRACKS)))
 for name in SOURCE_TRACKS:raw.extend(name.encode('latin1').ljust(68,b'\0')+paths[swaps[name]].encode('ascii').ljust(100,b'\0'))
 atomic(plan,bytes(raw))
 atomic(folder/'music-map.json',(json.dumps(dict(version=2,run_id=session,tracks=swaps),indent=2)+'\n').encode())
