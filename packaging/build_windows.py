"""Transparent portable layout: original signed CPython + plain application files.
No self-extracting executable, scan exclusions or runtime software installation.
"""
from pathlib import Path
import os,sys,subprocess,json,hashlib,shutil
import argparse
parser=argparse.ArgumentParser();parser.add_argument('payload',type=Path);parser.add_argument('output',type=Path);a=parser.parse_args()
if os.name!='nt':raise SystemExit('Run this builder on Windows with the required Python packages installed.')
D=a.output.resolve();D.mkdir(parents=True,exist_ok=True);package=D/'BoshyRandomizer'
if package.exists():raise SystemExit('Choose a fresh output directory; builds never overwrite an existing package.')
package.mkdir()
manifest=json.loads((a.payload/'package-files.json').read_text(encoding='utf-8'))
for name,digest in manifest['files'].items():
 if hashlib.sha256((a.payload/name).read_bytes()).hexdigest()!=digest:raise ValueError('Payload integrity: '+name)
source=Path(sys.base_prefix);tag=f'python{sys.version_info.major}{sys.version_info.minor}';runtime=package/'runtime';runtime.mkdir(exist_ok=True)
for name in ('python.exe','pythonw.exe',tag+'.dll','python3.dll','vcruntime140.dll','vcruntime140_1.dll','LICENSE.txt'):
 if (source/name).exists():shutil.copy2(source/name,runtime/name)
for name in ('DLLs','tcl'):
 shutil.copytree(source/name,runtime/name,dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
shutil.copytree(source/'Lib',runtime/'Lib',dirs_exist_ok=True,ignore=shutil.ignore_patterns('site-packages','__pycache__','*.pyc','test','idlelib','ensurepip'))
allowed=('PIL','pillow.libs','numpy','numpy.libs','psutil','pygetwindow','pyrect','pycaw','comtypes','imageio_ffmpeg')
site=runtime/'Lib/site-packages';site.mkdir(exist_ok=True)
for name in allowed:
 src=source/'Lib/site-packages'/name
 if src.exists():shutil.copytree(src,site/name,dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
for src in (source/'Lib/site-packages').glob('*.dist-info'):
 if src.name.split('-')[0].lower() in [n.lower() for n in allowed]:shutil.copytree(src,site/src.name,dirs_exist_ok=True)
(runtime/(tag+'._pth')).write_text('.\nDLLs\nLib\nLib/site-packages\nimport site\n')
shutil.copytree(a.payload,package/'app')
(package/'BoshyRandomizer.cmd').write_text('@echo off\nsetlocal\nset "PYTHONUTF8=1"\nset "PYTHONNOUSERSITE=1"\nstart "" "%~dp0runtime\\pythonw.exe" "%~dp0app\\windows_entry.py"\n',encoding='ascii')
(package/'README.txt').write_text('Boshy Randomizer Windows preview\n\nExtract the entire folder. Open BoshyRandomizer.cmd.\nSupply your own compatible game folder or ZIP on first start.\nYour game and runs are kept in %LOCALAPPDATA%\\BoshyRandomizer.\nNo Python installation, administrator rights, Wine or Lutris required.\nThe game and personal saves are not distributed.\nThis preview uses the original CPython executables, with application source\nfiles alongside them. Defender must remain enabled; no exclusions required.\nWindows compatibility testing is ongoing.\n',encoding='utf-8')
subprocess.run([str(runtime/'python.exe'),'-c','import tkinter,PIL,numpy,psutil,pygetwindow,pycaw,comtypes,imageio_ffmpeg;print("Portable dependencies OK")'],check=True,cwd=package)
archive=shutil.make_archive(str(D/('BoshyRandomizer-'+manifest['version']+'-x64')),'zip',package.parent,package.name)
digest=hashlib.sha256(Path(archive).read_bytes()).hexdigest()
(D/'portable-build.json').write_text(json.dumps({'archive':str(archive),'sha256':digest,'package':str(package)},indent=2))
