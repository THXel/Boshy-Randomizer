"""Import a verified user-supplied game into a new private copy, never its saves."""
from pathlib import Path,PurePosixPath
import hashlib,json,os,shutil,stat,tempfile,zipfile
from runtime_paths import EXPECTED
EXE='I Wanna Be The Boshy.exe'
LIMIT=2*1024**3

def import_game(source,base):
 source=Path(source).expanduser().resolve();base=Path(base);destination=base/'IWBTB'
 if destination.exists():raise ValueError('A game copy already exists. It will not be replaced.')
 base.mkdir(parents=True,exist_ok=True)
 with tempfile.TemporaryDirectory(prefix='.game-import-',dir=base) as folder:
  staged=Path(folder)/'IWBTB';staged.mkdir();total=0
  if source.is_dir():
   candidates=[]
   for pattern in ('*','*/*','*/*/*'):
    candidates += [p for p in source.glob(pattern) if p.is_file() and p.name.casefold()==EXE.casefold()]
   if len(candidates)!=1:raise ValueError('Select a folder containing exactly one Boshy game.')
   game=candidates[0].parent
   for p in game.rglob('*'):
    rel=p.relative_to(game)
    if len(rel.parts)>1 and rel.parts[0].casefold()!='custom':continue
    if len(rel.parts)==1 and p.name.casefold() not in (EXE.casefold(),'custom'):continue
    if p.is_symlink():raise ValueError('Symbolic links are not accepted in the game folder.')
    if not p.is_file():continue
    total+=p.stat().st_size
    if total>LIMIT:raise ValueError('The game folder exceeds the import size limit.')
    target=staged/(EXE if p.name.casefold()==EXE.casefold() and len(rel.parts)==1 else Path('Custom',*rel.parts[1:]))
    target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,target)
  elif source.is_file() and zipfile.is_zipfile(source):
   with zipfile.ZipFile(source) as z:
    members=z.infolist()
    if len(members)>10000:raise ValueError('The ZIP contains too many files.')
    paths=[];seen=set()
    for info in members:
     name=info.filename.replace('\\','/');path=PurePosixPath(name)
     if path.is_absolute() or '..' in path.parts or any(':' in part for part in path.parts) or stat.S_ISLNK(info.external_attr>>16):raise ValueError('The ZIP contains an unsafe path or symbolic link.')
     if info.flag_bits&1:raise ValueError('Encrypted ZIP files are not supported.')
     key=str(path).casefold()
     if key in seen:raise ValueError('The ZIP contains duplicate file names.')
     seen.add(key);paths.append((info,path));total+=info.file_size
     if total>LIMIT:raise ValueError('The ZIP exceeds the import size limit.')
    games=[p for i,p in paths if p.name.casefold()==EXE.casefold() and not i.is_dir()]
    if len(games)!=1:raise ValueError('The ZIP must contain exactly one Boshy game.')
    parent=games[0].parent
    for info,path in paths:
     if info.is_dir() or not path.is_relative_to(parent):continue
     rel=path.relative_to(parent)
     if str(rel).casefold()==EXE.casefold():target=staged/EXE
     elif len(rel.parts)>1 and rel.parts[0].casefold()=='custom':target=staged/'Custom'/Path(*rel.parts[1:])
     else:continue
     target.parent.mkdir(parents=True,exist_ok=True)
     with z.open(info) as src,target.open('xb') as dst:shutil.copyfileobj(src,dst,1024*1024)
  else:raise ValueError('Choose a Boshy folder or a ZIP file.')
  if hashlib.sha256((staged/EXE).read_bytes()).hexdigest()!=EXPECTED:raise ValueError('This game version is not supported. Your original files were not changed.')
  # Fresh independent settings and global profile; never copy a player's progress.
  from PY.rc4_utils import rc4_crypt
  chars=json.loads((base/'INI/characters.json').read_text(encoding='utf-8'))
  from character_cycle import initial
  dark=initial(base,'',False)['id']
  profile=f'[License]\nName=Player\nCharacter={dark}\nCharacterName=Dark Boshy\n[Unlockables]\n'+''.join(str(k)+'=0\n' for k in chars)+'[Achievements]\n'
  (staged/'onlineLicense.ini').write_bytes(rc4_crypt(b'BLOB',profile.encode('latin-1')))
  options='[Options]\nScreenSize=880\nFrameRate=50\nOnlineLicenseCharacter=1\n'
  (staged/'options.ini').write_bytes(rc4_crypt(b'BLOB',options.encode('ascii')))
  os.rename(staged,destination)
 return destination
