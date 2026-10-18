"""OS transport only. Game rules and validation stay shared across platforms."""
import os,sys,subprocess,time,threading,queue
from pathlib import Path
WINDOWS=os.name=='nt'
def native_path(path):
 p=str(path).replace('/','\\')
 return p if WINDOWS else 'Z:'+p

def owned_process(process,base):
 import psutil
 try:
  if WINDOWS:return Path(process.exe()).resolve()==(Path(base)/'IWBTB/I Wanna Be The Boshy.exe').resolve()
  return Path(process.cwd())==Path(base)/'IWBTB' and process.environ().get('WINEPREFIX')==str(Path(base)/'wineprefix')
 except (psutil.Error,OSError):return False

def lock_file(file):
 if WINDOWS:
  import msvcrt
  file.seek(0);file.write('0');file.flush();file.seek(0)
  try:msvcrt.locking(file.fileno(),msvcrt.LK_NBLCK,1)
  except OSError as e:raise BlockingIOError('Already locked') from e
 else:
  import fcntl
  fcntl.flock(file,fcntl.LOCK_EX|fcntl.LOCK_NB)

class LineReader:
 def __init__(self,stream):
  self.q=queue.Queue()
  def read():
   try:
    for line in stream:self.q.put(line)
   finally:self.q.put(None)
  threading.Thread(target=read,daemon=True).start()
 def readline(self,timeout=8):
  try:line=self.q.get(timeout=timeout)
  except queue.Empty:raise TimeoutError('Bridge response timeout')
  if line is None:raise RuntimeError('Bridge exited')
  return line

def close_window(window):
 if WINDOWS:
  from windows_api import user
  if not user.PostMessageW(window._hWnd,0x10,0,0):raise RuntimeError('Unable to close game window')
 else:subprocess.run(['wmctrl','-ic',hex(window._hWnd)],check=True,timeout=2)

def press(name,hold=.12):
 if WINDOWS:
  from windows_api import send_key
  send_key(name,True)
  try:time.sleep(hold)
  finally:send_key(name,False)
 else:
  subprocess.run(['xdotool','keydown',name],check=True)
  try:time.sleep(hold)
  finally:subprocess.run(['xdotool','keyup',name],check=True)

def python_command(script,*args):
 if getattr(sys,'frozen',False):return [sys.executable,'--component',script,*map(str,args)]
 executable=str(Path(sys.executable).with_name('python.exe')) if WINDOWS and Path(sys.executable).name.lower()=='pythonw.exe' else sys.executable
 if WINDOWS:return [executable,str(Path(os.environ.get('BOSHY_DATA_HOME',Path(__file__).parent))/'windows_entry.py'),'--component',script,*map(str,args)]
 return [executable,str((Path(os.environ.get('BOSHY_DATA_HOME',Path(__file__).parent)) if WINDOWS else Path(__file__).parent)/script),*map(str,args)]

def replace_file(source,target):
 """Windows readers can briefly deny FILE_SHARE_DELETE; never unlink the target."""
 deadline=time.monotonic()+.5
 while True:
  try:os.replace(source,target);return
  except PermissionError:
   if not WINDOWS or time.monotonic()>=deadline:raise
   time.sleep(.01)

def child_options():
 return {"creationflags":0x08000000} if WINDOWS else {}
