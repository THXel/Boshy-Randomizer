"""Debian entry point: immutable package resources, private user-owned runtime."""
from pathlib import Path
import fcntl,hashlib,json,os,shutil,struct,subprocess,sys,tempfile
PACKAGE=Path(__file__).resolve().parent

def data_root():
 return Path(os.environ.get('BOSHY_DATA_HOME') or Path(os.environ.get('XDG_DATA_HOME',Path.home()/'.local/share'))/'boshy-randomizer').expanduser().resolve()

def install_runtime(base):
 manifest=json.loads((PACKAGE/'package-files.json').read_text(encoding='utf-8'))
 base.mkdir(parents=True,exist_ok=True)
 if any(p.is_symlink() for p in (base/'IWBTB',base/'wineprefix')):raise RuntimeError('The game and Wine prefix must belong to this randomizer.')
 # Old processes must not see a half-updated runtime.
 import psutil
 for p in psutil.process_iter(['pid']):
  if p.pid==os.getpid():continue
  try:
   if Path(p.cwd()) in (base,base/'IWBTB'):raise RuntimeError('Close the running randomizer before updating.')
  except (psutil.Error,FileNotFoundError):pass
 marker=base/'installed-runtime.json';current=json.loads(marker.read_text(encoding='utf-8')) if marker.exists() else {}
 if current.get('release')==manifest['release']:return
 for name,want in manifest['files'].items():
  path=PACKAGE/name
  if hashlib.sha256(path.read_bytes()).hexdigest()!=want:raise RuntimeError('Package integrity check failed: '+name)
 for name in manifest['files']:
  target=base/name;target.parent.mkdir(parents=True,exist_ok=True)
  if target.is_symlink():raise RuntimeError('Refusing to replace a linked runtime file: '+name)
  temp=target.with_name(target.name+'.package-new');shutil.copy2(PACKAGE/name,temp);os.replace(temp,target)
 from mixed_rewards import CONTEXT_SIZE
 for blob_name,symbol_name in [('slot_reward_hook.bin','slot_reward_symbols.json'),('slot_reward_extras.bin','slot_reward_extras_symbols.json')]:
  path=base/blob_name;raw=bytearray(path.read_bytes());off=json.loads((base/symbol_name).read_text(encoding='utf-8'))['context_offset']+CONTEXT_SIZE
  for field,name in ((64,'menu-runtime/frame.bmp'),(1356,'native_menu.dll')):
   value=('Z:'+str(base/name).replace('/','\\')).encode('ascii')
   if len(value)>=260:raise RuntimeError('The runtime folder path is too long.')
   raw[off+field:off+field+260]=value.ljust(260,b'\0')
  path.write_bytes(raw)
 for directory in ('menu-runtime','evidence','native-runs'):(base/directory).mkdir(exist_ok=True)
 marker.write_text(json.dumps({'release':manifest['release'],'version':manifest['version']},indent=2)+'\n', encoding='utf-8')


def main():
 if os.geteuid()==0:raise RuntimeError('Launch the randomizer as your normal desktop user, not root.')
 if not os.environ.get('DISPLAY') or os.environ.get('XDG_SESSION_TYPE')=='wayland':raise RuntimeError('Please use an X11 desktop session.')
 base=data_root()
 if len(str(base))>180 or not str(base).isascii():raise RuntimeError('Choose a shorter ASCII runtime path with BOSHY_DATA_HOME.')
 base.mkdir(parents=True,exist_ok=True);lock=(base/'.package-launch.lock').open('a')
 try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 except BlockingIOError:raise RuntimeError('Boshy Randomizer is already running.')
 os.set_inheritable(lock.fileno(),True)
 install_runtime(base)
 if not (base/'IWBTB').exists():
  from first_run import Setup
  if not Setup(base).run():return
 from first_run import prepare_environment
 if not prepare_environment(base):return
 os.chdir(base);os.execv(str(base/'start-linux.sh'),[str(base/'start-linux.sh')])
if __name__=='__main__':
 try:main()
 except Exception as e:
  import tkinter as tk
  from tkinter import messagebox
  from ui_i18n import tr
  root=tk.Tk();root.withdraw();messagebox.showerror('Boshy Randomizer',tr(str(e)),parent=root);root.destroy();sys.exit(1)
