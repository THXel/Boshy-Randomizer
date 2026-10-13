"""Transport for native owned dialogs in the Boshy process."""
from pathlib import Path
import json,struct,subprocess,os,time
from lab import BASE,RUNNER,Bridge,game_window
from runtime_paths import command,environment
from mixed_rewards import CONTEXT_SIZE
from native_session import atomic
from window_position import wait_for_game
MENU_SIZE=2160
class MenuGame:
 def __init__(self,enabled=True,position=None):
  folder=BASE/'native-runs'/('0'*32);folder.mkdir(parents=True,exist_ok=True)
  blob=bytearray((BASE/'slot_reward_hook.bin').read_bytes());off=json.loads((BASE/'slot_reward_symbols.json').read_text())['context_offset']+CONTEXT_SIZE
  struct.pack_into('<I',blob,off+60,int(enabled));struct.pack_into('<I',blob,off+40,1);payload=folder/'reward_hook.bin'
  atomic(payload,__import__("intro_guard").attach(BASE,blob))
  log=folder/'launch.log'
  with log.open('w') as f:ret=subprocess.run(command('slot_reward_launcher.exe',payload.relative_to(BASE)),cwd=BASE,env=environment(),stdout=f,stderr=f,timeout=45)
  if ret.returncode:raise RuntimeError(log.read_text()[-1000:])
  meta=json.loads(next(x for x in log.read_text().splitlines() if x.startswith('{')));self.address=meta['hook']+off;self.bridge=None
  try:
   wait_for_game(position)
   self.bridge=Bridge();self.generation=1
   deadline=time.monotonic()+20
   while time.monotonic()<deadline:
    try:self.header();break
    except RuntimeError as e:
     if not (e.args and isinstance(e.args[0],dict) and e.args[0].get('error')=='state unavailable'):raise
     time.sleep(.1)
   else:raise RuntimeError('Natives Menü wurde nicht initialisiert.')
   if position:position.restore()
  except Exception:
   self.close();raise
 def header(self):return struct.unpack('<16I',self.bridge.read(self.address,64))
 def write(self,off,value):self.bridge.cmd(f'menu {self.address:x} {off} {int(value)}')
 def events(self):
  try:h=self.header()
  except RuntimeError as e:
   if e.args and isinstance(e.args[0],dict) and e.args[0].get('error')=='state unavailable':return []
   raise
  end,ack=h[5:7]
  if h[12]:raise RuntimeError(f'Natives Menü meldet Fehler {h[12]}')
  if end-ack>64:raise RuntimeError('Menüeingaben übergelaufen')
  events=[]
  for n in range(ack,end):events.append(struct.unpack('<4I',self.bridge.read(self.address+324+16*(n%64),16))[:3])
  if end!=ack:self.write(24,end)
  return events
 def refresh(self):self.generation+=1;self.write(40,self.generation)
 def close(self):
  if self.bridge:self.bridge.close();self.bridge=None
  import psutil
  try:w=game_window()
  except RuntimeError as e:
   if str(e)=='Expected one laboratory window: 0':return
   raise
  p=psutil.Process(w.pid);subprocess.run(['wmctrl','-ic',hex(w._hWnd)],check=True);p.wait(timeout=15)
