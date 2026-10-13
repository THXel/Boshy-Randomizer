#!/usr/bin/env python3
"""Create a game-free Debian package from the reviewed native source tree."""
from pathlib import Path
import json,hashlib,shutil,subprocess,os,sys
ROOT=Path(__file__).resolve().parents[1];SOURCE=ROOT/'native-linux';VERSION='2026.10.13-1'
# Fail before creating a package if the runtime export is incomplete.
sys.path.insert(0,str(SOURCE))
from native_session import ASSETS
from extras_runtime import ASSETS as EXTRA_ASSETS
required=set(ASSETS+EXTRA_ASSETS)|{'bridge.exe','launch_slot_reward.py','gastly_route_lab.py','loading-icons/index.json','loading-icons/boshy.webp','INI/characters.json','wine-runner-manifest.json'}
missing=sorted(name for name in required if not (SOURCE/name).is_file())
if missing:raise SystemExit('Missing runtime resources: '+', '.join(missing))
OUTPUT=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else ROOT/'dist'
OUTPUT.mkdir(parents=True,exist_ok=True);BUILD=OUTPUT/'package-root'
if BUILD.exists():shutil.rmtree(BUILD)
PAYLOAD=BUILD/'usr/lib/boshy-randomizer';PAYLOAD.mkdir(parents=True)
exclude={'source-manifest.json','slot_reward_context.bin'}
files=[]
for p in SOURCE.iterdir():
 if p.is_file() and (p.suffix in ('.py','.dll','.exe','.bin','.json','.sh')) and not p.name.startswith('build_') and p.name not in exclude:files.append(p)
for folder,exts in [('PY',{'.py'}),('locales',{'.json'}),('INI',{'.json'}),('Custom',{'.png','.bmp','.ttf','.wav','.txt'}),('menu-character-icons',{'.png'}),('native-icons',{'.bmp'}),('loading-icons',{'.png','.webp','.json'})]:
 files.extend(p for p in (SOURCE/folder).rglob('*') if p.is_file() and not p.is_symlink() and p.suffix in exts and '__pycache__' not in p.parts)
for p in files:
 rel=p.relative_to(SOURCE);dest=PAYLOAD/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest);dest.chmod(0o755 if p.suffix=='.sh' else 0o644)
hashes={str(p.relative_to(PAYLOAD)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(PAYLOAD.rglob('*')) if p.is_file()}
release=hashlib.sha256(json.dumps(hashes,sort_keys=True).encode()).hexdigest()
(PAYLOAD/'package-files.json').write_text(json.dumps({'version':VERSION,'release':release,'files':hashes},indent=2)+'\n')
# No maintainer scripts: installing/uninstalling never changes a user's game data.
(BUILD/'DEBIAN').mkdir();(BUILD/'DEBIAN/control').write_text(f'''Package: boshy-randomizer
Version: {VERSION}
Section: games
Priority: optional
Architecture: amd64
Maintainer: THXel
Depends: python3 (>= 3.12), python3-tk, python3-pil, python3-pil.imagetk, python3-numpy, python3-xlib, python3-psutil, wine, wine64, lutris, ca-certificates, xdotool, wmctrl, pulseaudio-utils, zenity, fonts-dejavu-core, fonts-noto-cjk, util-linux
Homepage: https://github.com/THXel/Boshy-Randomizer
Description: Native-menu Boshy Randomizer for Linux
 Randomizer and Target Select modes, shared seeds and a separate live tracker.
 First launch imports a user-supplied Boshy folder or ZIP into a private copy.
 The original game is not included. X11 desktop required.
 Windows support is planned for a later release.
''')
(BUILD/'usr/bin').mkdir(parents=True);launcher=BUILD/'usr/bin/boshy-randomizer';launcher.write_text('#!/bin/sh\nexport PYTHONDONTWRITEBYTECODE=1\nexec /usr/bin/python3 /usr/lib/boshy-randomizer/package_bootstrap.py "$@"\n');launcher.chmod(0o755)
(BUILD/'usr/share/applications').mkdir(parents=True);(BUILD/'usr/share/applications/boshy-randomizer.desktop').write_text('''[Desktop Entry]
Type=Application
Name=Boshy Randomizer
Comment=Randomizer and Target Select for I Wanna Be The Boshy
Comment[de]=Randomizer und Target Select für I Wanna Be The Boshy
Exec=boshy-randomizer
Icon=boshy-randomizer
Terminal=false
Categories=Game;
StartupNotify=true
''')
icons=BUILD/'usr/share/icons/hicolor/256x256/apps';icons.mkdir(parents=True)
from PIL import Image
im=Image.open(SOURCE/'Custom/boshy_randomizer.png').convert('RGBA');im.thumbnail((256,256));out=Image.new('RGBA',(256,256));out.alpha_composite(im,((256-im.width)//2,(256-im.height)//2));out.save(icons/'boshy-randomizer.png')
docs=BUILD/'usr/share/doc/boshy-randomizer';docs.mkdir(parents=True);shutil.copy2(ROOT/'README.md',docs/'README.md');shutil.copy2(ROOT/'CHANGELOG.md',docs/'changelog');shutil.copy2(SOURCE/'Custom/License.txt',docs/'copyright');shutil.copytree(ROOT/'docs',docs/'docs');shutil.copytree(ROOT/'README',docs/'README');(docs/'Custom').mkdir();shutil.copy2(SOURCE/'Custom/boshy_randomizer.png',docs/'Custom/boshy_randomizer.png');shutil.copy2(SOURCE/'Custom/License.txt',docs/'Custom/License.txt')
(BUILD/'DEBIAN/control').write_text((BUILD/'DEBIAN/control').read_text()+f'Installed-Size: {sum(p.stat().st_size for p in BUILD.rglob("*") if p.is_file())//1024}\n')
package=OUTPUT/f'boshy-randomizer_{VERSION}_amd64.deb';subprocess.run(['dpkg-deb','--root-owner-group','--build',str(BUILD),str(package)],check=True)
(OUTPUT/'SHA256SUMS').write_text(hashlib.sha256(package.read_bytes()).hexdigest()+'  '+package.name+'\n')
print(package)
