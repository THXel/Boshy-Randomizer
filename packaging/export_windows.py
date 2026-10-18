#!/usr/bin/env python3
"""Export only public runtime assets; no game, saves, user settings or Wine."""
from pathlib import Path
import argparse,hashlib,json,shutil,sys

def export(source,target,version):
 source=Path(source).resolve();target=Path(target).resolve();sys.path.insert(0,str(source))
 from trigger_audit import FILES
 exclude={'source-manifest.json','slot_reward_context.bin','package_bootstrap.py','wine_setup.py','wine-runner-manifest.json'}
 files=[p for p in source.iterdir() if p.is_file() and not p.is_symlink() and p.suffix in ('.py','.dll','.exe','.bin','.json') and not p.name.startswith('build_') and p.name not in exclude]
 for folder,extensions in [('PY',{'.py'}),('locales',{'.json'}),('INI',{'.json'}),('Custom',{'.png','.bmp','.ttf','.wav','.txt'}),('menu-character-icons',{'.png'}),('native-icons',{'.bmp'}),('loading-icons',{'.png','.webp','.json'})]:
  files.extend(p for p in (source/folder).rglob('*') if p.is_file() and not p.is_symlink() and p.suffix in extensions and '__pycache__' not in p.parts)
 files.extend(source/n for n in FILES if source/n not in files)
 if target.exists() and any(target.iterdir()):raise ValueError('Choose an empty export directory')
 target.mkdir(parents=True,exist_ok=True);hashes={};seen={}
 for p in sorted(set(files)):
  name=p.relative_to(source).as_posix();data=p.read_bytes();digest=hashlib.sha256(data).hexdigest();key=name.casefold()
  if key in seen:
   if seen[key]!=digest:raise ValueError('Windows filename collision: '+name)
   continue
  seen[key]=digest;dest=target/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data);hashes[name]=digest
 release=hashlib.sha256(json.dumps(hashes,sort_keys=True).encode()).hexdigest()
 (target/'package-files.json').write_text(json.dumps(dict(version=version,release=release,files=hashes),indent=2)+'\n',encoding='utf-8')
 return hashes

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('output',type=Path);parser.add_argument('--source',type=Path,default=Path(__file__).resolve().parents[1]/'native-linux');parser.add_argument('--version',default='2026.10.18-win-preview2');a=parser.parse_args()
 print('Exported',len(export(a.source,a.output,a.version)),'files')
