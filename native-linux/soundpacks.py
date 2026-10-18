"""Local, persistent cosmetic audio packs; seeded music never consumes route RNG."""
import hashlib,json,secrets,struct
from pathlib import Path
from native_session import atomic,write_json
from music_playback import convert,PREFIX
PACKS=(('original','Original Boshy'),('kamilia3','Kamilia 3'),('wannafest22','WannaFest22'))
# Exact embedded sample names, not filenames or frame-based sound polling.
CUES={'opening':('Intro Megaman X Infinity Mijinion stage',),'death':('BLAAHLouder','Death 3','death','Dead','smb die (2)','castlevania die'),'ending':('Boshy Credits',),'menu':('select',)}

def selected(base):
 try:
  name=json.loads((Path(base)/'INI/soundpack-preferences.json').read_text(encoding='utf-8'))['pack']
  if name in dict(PACKS):return name
 except (OSError,ValueError,KeyError,TypeError):pass
 return 'original'

def catalogue(base,name):
 if name not in dict(PACKS) or name=='original':raise ValueError('Unknown sound pack')
 root=Path(base)/'soundpacks'/name
 d=json.loads((root/'pack.json').read_text(encoding='utf-8'))
 if d.get('version')!=1 or d.get('id')!=name or not isinstance(d.get('tracks'),list):raise ValueError('Invalid sound pack manifest')
 seen=set()
 for row in d['tracks']:
  rel=Path(row['file']);path=root/rel
  if rel.is_absolute() or '..' in rel.parts or path.is_symlink() or not path.resolve().is_relative_to(root.resolve()) or not path.is_file() or row['file'] in seen:raise ValueError('Invalid sound pack file')
  if row.get('shuffle') and not 30<float(row['seconds'])<=1200:raise ValueError('Shuffle tracks must exceed 30 seconds')
  seen.add(row['file'])
 return d

def available(base):
 rows=[]
 for name,title in PACKS:
  try:d=catalogue(base,name) if name!='original' else None
  except (OSError,ValueError,KeyError,TypeError):continue
  rows.append(dict(id=name,title=title,count=sum(bool(r.get('shuffle')) for r in d['tracks']) if d else None))
 return rows

def audio(base,name,row):
 source=Path(base)/'soundpacks'/name/row['file']
 if hashlib.sha256(source.read_bytes()).hexdigest()!=row['sha256']:raise ValueError('Sound pack checksum: '+row['file'])
 cache=Path(base)/'menu-runtime/music';cache.mkdir(parents=True,exist_ok=True)
 return PREFIX+convert(source,cache).name

def prepare_menu(base,name=None):
 base=Path(base);name=name or selected(base);folder=base/'menu-runtime';folder.mkdir(exist_ok=True)
 rows=[]
 if name!='original':
  data=catalogue(base,name)
  for entry in data['tracks']:
   for role in entry.get('roles',[]):
    for cue in CUES.get(role,()):rows.append((cue,audio(base,name,entry),2 if role in ('death','save') else 1))
 if len(rows)>32:raise ValueError('Sound pack cue count')
 raw=bytearray(struct.pack('<4sIII',b'BRP1',secrets.randbelow(0xffffffff)+1,len(rows),0))
 for cue,path,kind in rows:
  a=cue.encode('latin1');b=path.encode('ascii')
  if len(a)>=68 or len(b)>=100:raise ValueError('Sound pack path length')
  raw.extend(a.ljust(68,b'\0')+b.ljust(100,b'\0')+struct.pack('<I',kind))
 atomic(folder/'soundpack.bin',bytes(raw));write_json(folder/'soundpack-map.json',dict(pack=name,rows=[dict(cue=a,path=b,kind=c) for a,b,c in rows]))
 return name

def select(base,name):
 if name not in dict(PACKS):raise ValueError('Unknown sound pack')
 prepare_menu(base,name)
 write_json(Path(base)/'INI/soundpack-preferences.json',dict(version=1,pack=name))

def mapping(seed,tracks):
 files=[r['file'] for r in tracks if r.get('shuffle')]
 if not files:raise ValueError('Sound pack has no music longer than 30 seconds')
 from music_randomizer import SOURCE_TRACKS
 # Shuffle a bag, repeat only when every track has been used; independent of route.
 files.sort(key=lambda f:hashlib.sha256(('boshy-pack-v1\0'+str(seed)+'\0'+f).encode()).digest())
 cues=sorted(SOURCE_TRACKS,key=lambda f:hashlib.sha256(('boshy-pack-cues-v1\0'+str(seed)+'\0'+f).encode()).digest())
 return {cue:files[i%len(files)] for i,cue in enumerate(cues)}

def prepare_music(base,manifest):
 base=Path(base);name=selected(base);prepare_menu(base,name)
 if name=='original' or not manifest['options'].get('extras',{}).get('music'):return False
 data=catalogue(base,name);swaps=mapping(manifest['seed'],data['tracks']);byfile={r['file']:r for r in data['tracks']}
 from music_randomizer import SOURCE_TRACKS
 paths={file:audio(base,name,byfile[file]) for file in set(swaps.values())}
 session=manifest['run_id'];raw=bytearray(b'BRM1'+session.encode('ascii')+struct.pack('<I',len(SOURCE_TRACKS)))
 if len(session)!=32 or any(c not in '0123456789abcdef' for c in session):raise ValueError('Music session')
 for cue in SOURCE_TRACKS:raw.extend(cue.encode('latin1').ljust(68,b'\0')+paths[swaps[cue]].encode('ascii').ljust(100,b'\0'))
 folder=base/'menu-runtime';write_json(folder/'music-map.json',dict(version=3,pack=name,run_id=session,tracks={cue:data['title']+' · '+byfile[file]['name'] for cue,file in swaps.items()}));atomic(folder/'music.bin',bytes(raw));return True
