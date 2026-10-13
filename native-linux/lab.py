from pathlib import Path
import os,json,subprocess,select,time,struct,hashlib,sys
from runtime_paths import BASE,RUNNER,EXPECTED,environment,command
class Bridge:
 def __init__(self):
  assert hashlib.sha256((BASE/'IWBTB/I Wanna Be The Boshy.exe').read_bytes()).hexdigest()==EXPECTED
  self.p=subprocess.Popen(command('bridge.exe'),stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=open(BASE/'evidence/bridge.log','a'),text=True,bufsize=1,env=environment())
  self.ready=self.response()
 def response(self):
  if not select.select([self.p.stdout],[],[],8)[0]:raise TimeoutError('Bridge response timeout')
  line=self.p.stdout.readline()
  if not line:raise RuntimeError('Bridge exited')
  data=json.loads(line)
  if 'error' in data:raise RuntimeError(data)
  return data
 def cmd(self,s):
  self.p.stdin.write(s+'\n');self.p.stdin.flush();return self.response()
 def read(self,addr,size):return bytes.fromhex(self.cmd(f'read {addr:x} {size}')['hex'])
 def snapshot(self):return self.cmd('snapshot')
 def scene(self,dest):
  before=self.snapshot();self.cmd(f'scene {dest} {before["scene"]}')
  deadline=time.monotonic()+8
  while time.monotonic()<deadline:
   time.sleep(.04)
   try:cur=self.snapshot()
   except RuntimeError:continue
   if cur['scene']==dest and cur['next']==0:return cur
  raise TimeoutError(f'Scene {dest} not confirmed: {cur}')
 def close(self):
  self.p.stdin.write('quit\n');self.p.stdin.flush();self.p.wait(timeout=5)
def game_window():
 import psutil
 from PY import platform_windows as gw
 candidates=[]
 for w in gw.getWindowsWithTitle('I Wanna Be The Boshy'):
  try:
   p=psutil.Process(w.pid)
   if Path(p.cwd())==BASE/'IWBTB' and p.environ().get('WINEPREFIX')==str(BASE/'wineprefix'):candidates.append(w)
  except (psutil.Error,AttributeError):pass
 if len(candidates)!=1:raise RuntimeError(f'Expected one laboratory window: {len(candidates)}')
 return candidates[0]
def key(name,hold=.12):
 w=game_window();w.activate();time.sleep(.1)
 subprocess.run(['xdotool','keydown',name],check=True)
 try:time.sleep(hold)
 finally:subprocess.run(['xdotool','keyup',name],check=True)
def screenshot(name):
 from PIL import ImageGrab
 from PY import platform_windows as gw
 w=game_window()
 active=next((v for v in gw.getAllWindows() if v.isActive),None)
 if active is None or active.pid!=w.pid:w.activate()
 time.sleep(.3);x,y,width,height=gw.window_rect(w)
 ImageGrab.grab(bbox=(x,y,x+width,y+height)).save(BASE/'evidence'/name)
def objects(b):
 s=b.snapshot();n=s['objects']
 if not 0<n<=20000:raise RuntimeError('Unexpected object capacity')
 table=bytearray()
 for off in range(0,n*8,64000):table.extend(b.read(s['object_list']+off,min(64000,n*8-off)))
 arr=struct.unpack('<'+'I'*(n*2),table)
 result=[]
 for i in range(n):
  p=arr[i*2]
  if p<0x10000:continue
  try:
   raw=b.read(p,160)
   result.append({'slot':i,'ptr':p,'handle':struct.unpack_from('<h',raw,0)[0],'type':struct.unpack_from('<h',raw,24)[0],'oi':struct.unpack_from('<H',raw,18)[0],'x':struct.unpack_from('<i',raw,76)[0],'y':struct.unpack_from('<i',raw,84)[0],'w':struct.unpack_from('<i',raw,96)[0],'h':struct.unpack_from('<i',raw,100)[0],'raw':raw.hex()})
  except RuntimeError:pass
 return result
if __name__=='__main__':
 b=Bridge();print(b.ready);print(b.snapshot());screenshot('initial.png');b.close()

def ini_groups(b,oi=109):
 known=ini_objects(b)
 obj=next((o for o in known.values() if o['oi']==oi),None)
 if obj is None:obj=next(o for o in objects(b) if o['oi']==oi)
 state=struct.unpack('<I',b.read(obj['ptr']+0x168,4))[0]
 head=struct.unpack('<I',b.read(state+0x14,4))[0]
 root=struct.unpack('<I',b.read(head+4,4))[0]
 result={};seen={head}
 def walk(p):
  if p in seen:return
  if len(seen)>512:raise RuntimeError('Group tree limit')
  seen.add(p);raw=b.read(p,64)
  left,parent,right=struct.unpack_from('<III',raw)
  if left==parent==right==0:return
  ptr,length,cap=struct.unpack_from('<III',raw,16)
  assert length<200 and length<=cap
  key=b.read(ptr,length).decode('latin1')
  result[key]={'node':p,'raw':raw.hex()}
  walk(left);walk(right)
 walk(root)
 return result

def ini_items(b,group,oi=109):
 g=ini_groups(b,oi)[group];head=struct.unpack_from('<I',bytes.fromhex(g['raw']),32)[0]
 root=struct.unpack('<I',b.read(head+4,4))[0];result={};seen={head}
 def walk(p):
  if p in seen:return
  if len(seen)>2048:raise RuntimeError('Item tree limit')
  seen.add(p);raw=b.read(p,64);left,parent,right=struct.unpack_from('<III',raw)
  if left==parent==right==0:return
  def string(off):
   ptr,length,cap=struct.unpack_from('<III',raw,off);assert length<8192 and length<=cap
   return b.read(ptr,length).decode('latin1')
  key=string(16);result[key]={'value':string(48),'node':p,'raw':raw.hex()}
  walk(left);walk(right)
 walk(root);return result

def ini_objects(b):
 # Cache only object locations, never their INI contents. Validate every use.
 before=b.snapshot();identity=(before['scene'],before['run'],before['object_list'])
 cached=getattr(b,'_ini_cache',None);valid=bool(cached and cached['identity']==identity and before['frame_count']>=cached['tick'])
 if valid:
  for o in cached['objects'].values():
   ptr=struct.unpack('<I',b.read(before['object_list']+o['slot']*8,4))[0]
   if ptr!=o['ptr']:valid=False;break
   raw=b.read(ptr,32)
   if (struct.unpack_from('<h',raw,0)[0],struct.unpack_from('<H',raw,18)[0],struct.unpack_from('<h',raw,24)[0])!=(o['handle'],o['oi'],33):valid=False;break
 if valid:result=cached['objects']
 else:
  b._ini_cache=None;result={}
  for o in objects(b):
   if o['type']!=33:continue
   meta=struct.unpack_from('<I',bytes.fromhex(o['raw']),28)[0]
   name=b.read(meta+90,24).split(b'\0')[0].decode('latin1')
   if name in ('Ini++','Ini++ 3'):result[name]=o
 after=b.snapshot()
 if (after['scene'],after['run'],after['object_list'])!=identity or after['frame_count']<before['frame_count']:
  b._ini_cache=None;raise RuntimeError('Scene changed during observation')
 if result:b._ini_cache=dict(identity=identity,tick=after['frame_count'],objects=result)
 return result

def ini_object_ids(b):
 return {name:o['oi'] for name,o in ini_objects(b).items()}

def live_flags(b):
 oi=ini_object_ids(b)['Ini++']
 values=ini_items(b,'collectables',oi)
 return {k:values.get(k,{}).get('value','0') for k in ('scouter','timer')}

def set_reward_flags(b,scouter,timer):
 """Lab-only: update existing booleans in caches and disk with read-back verification (not yet a game-thread transaction)."""
 import psutil
 from PY.file_utils import smart_read
 from PY.ini_utils import apply_values_in_section
 from PY.save_utils import encrypt_save_atomic
 p=psutil.Process(game_window().pid)
 # Do not SIGSTOP Wine: WriteProcessMemory may need the target to service it.
 try:
  ids=ini_object_ids(b)
  for name,fn in [('Ini++','SaveFile1.ini'),('Ini++ 3','onlineLicense.ini')]:
   oi=ids[name]
   text,_=smart_read(str(BASE/'IWBTB'/fn))
   # Use actual cached Stats, not stale disk counters.
   groups=ini_groups(b,oi)
   if 'stats' in groups:
    from PY.ini_utils import parse_ini
    canonical={k.lower():k for k in parse_ini(text).get('stats',{})}
    vals={canonical.get(k,k):v['value'] for k,v in ini_items(b,'stats',oi).items()}
    text=apply_values_in_section(text,'Stats',vals)
   for group in ('collectables','achievements'):
    values=ini_items(b,group,oi)
    for key,new in [('scouter',str(scouter)),('timer',str(timer))]:
     if key not in values:continue
     old=values[key]['value'];assert old in ('0','1')
     if old!=new:assert b.cmd(f'value {oi} {group} {key} {old} {new}')['written']
    text=apply_values_in_section(text,group,{'Scouter':str(scouter),'Timer':str(timer)})
   assert encrypt_save_atomic(text,str(BASE/'IWBTB'/fn),b'BLOB')
 finally:pass

def transition(b,frame,x,y,save_name="SaveFile1.ini"):
 if save_name not in ("SaveFile1.ini","SaveFile2.ini","SaveFile3.ini"):raise ValueError("Invalid save slot")
 from PY.file_utils import smart_read
 from PY.ini_utils import apply_values_in_section
 from PY.save_utils import encrypt_save_atomic
 import psutil
 p=psutil.Process(game_window().pid);# Do not SIGSTOP Wine: WriteProcessMemory may need the target to service it.
 try:
  game_window().activate();time.sleep(.1)
  before=b.snapshot();text,_=smart_read(str(BASE/'IWBTB'/save_name))
  text=apply_values_in_section(text,'Positions',{'frame':str(frame),'xPos':str(x),'yPos':str(y)})
  assert encrypt_save_atomic(text,str(BASE/'IWBTB'/save_name),b'BLOB')
  assert b.cmd(f'scene {frame-1} {before["scene"]}')['requested']
 finally:pass
 deadline=time.monotonic()+8
 while time.monotonic()<deadline:
  time.sleep(.03)
  try:
   s=b.snapshot()
   if s['scene']!=frame-1 or s['next']!=0 or s['frame_count']<2:continue
   ids=ini_object_ids(b);pos=ini_items(b,'positions',ids['Ini++'])
   if all(int(pos[k]['value'])==v for k,v in [('frame',frame),('xpos',x),('ypos',y)]):return s
  except (RuntimeError,KeyError,StopIteration):continue
 raise TimeoutError('Engine did not confirm scene and spawn')

def dismiss_pickup():
 from PY import platform_windows as gw
 w=game_window();dialogs=[d for d in gw.getAllWindows() if d.pid==w.pid and d.title=='SCOUTER GET!']
 if dialogs:
  dialogs[0].activate();subprocess.run(['xdotool','key','Return'],check=True);time.sleep(.25)
 return bool(dialogs)
