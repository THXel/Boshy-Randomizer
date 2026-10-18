"""Temporary cosmetic diagnostics, independent of immutable seed/gameplay rules."""
import json,struct,time
from collections import deque
from pathlib import Path
from native_telemetry import NativeReader
from native_session import atomic
from ui_i18n import tr
CATEGORIES=((1,'Hintergründe'),(2,'Dekoration'),(4,'Böden und Plattformen'),(8,'Gegner- und Bossfarben'))
MAGIC=b'BGD1'
def reset(base):
 (Path(base)/'menu-runtime').mkdir(exist_ok=True)
 atomic(Path(base)/'menu-runtime/graphics-debug.bin',b'')
def requested(base,run_id,pid):
 try:
  b=(Path(base)/'menu-runtime/graphics-debug.bin').read_bytes()
  if len(b)!=48 or b[:4]!=MAGIC or struct.unpack_from('<I',b,4)[0]!=pid or b[8:40]!=run_id.encode():return 0
  mask=struct.unpack_from('<I',b,40)[0];return mask if mask<=15 else 0
 except OSError:return 0

def request(player,mask):
 if type(mask) is not int or not 0<=mask<=15:raise ValueError(tr('Ungültige Grafikauswahl.'))
 snap=player.bridge.snapshot()
 if snap['scene']<2 or snap['next'] or player.progress.data.get('pending'):raise ValueError(tr('Ein Übergang läuft bereits; bitte dessen Ende abwarten.'))
 sequence=time.monotonic_ns()&0xffffffff or 1
 (player.store.base/'menu-runtime').mkdir(exist_ok=True)
 atomic(player.store.base/'menu-runtime/graphics-debug.bin',MAGIC+struct.pack('<I',player.bridge.ready['pid'])+player.m['run_id'].encode()+struct.pack('<II',mask,sequence))
 return tr('Grafikauswahl vorgemerkt. Wirksam beim nächsten Levelwechsel; der Seed bleibt unverändert.')

class Telemetry:
 def __init__(self,player):
  self.player=player;self.reader=NativeReader(player);self.history=deque(maxlen=32);self.signature=None
  from background_sets import catalogue
  self.names={r['scene']:r['name'] for r in catalogue()['sets']}
  from sprite_chaos import catalogue as actors
  self.actors=actors();self.process=None
 def read(self):
  p=self.player;data={'time':time.time(),'requested_disabled':requested(p.store.base,p.m['run_id'],p.bridge.ready['pid'])}
  try:
   for key,name,count in [('background','BackgroundState',12),('motion','BackgroundMotion',8),('sprites','ChaosState',14),('override','GraphicsDebug',4),('references','ReferenceState',6)]:data[key]=list(self.reader.read(name,count) or [])
   bg=data['background'];sprites=data['sprites'];scene=bg[2] if bg else -1
   from native_models import location
   data['room']=self.names.get(scene,location(scene+1));data['background_set']=self.names.get(bg[3]) if bg and bg[1] else 'Original'
   data['boss_actor_objects']=sorted({r['oi'] for r in self.actors if r['category']==8 and scene+1 in r['frames']})
   data['applied_disabled']=data['override'][1] if data['override'] else None
   signature=(scene,bg[10] if bg else None,data['background_set'],data['requested_disabled'],data['applied_disabled'],sprites[3] if sprites else 0,sprites[6] if sprites else 0)
   if signature!=self.signature:
    self.history.append({k:data.get(k) for k in ('time','room','background_set','requested_disabled','applied_disabled','sprites','background')});self.signature=signature
   if self.process is None:
    import psutil
    from lab import game_window
    self.process=psutil.Process(game_window().pid)
   data['memory_rss_mib']=round(self.process.memory_info().rss/1048576,1)
  except Exception as e:data['error']=str(e)
  data['history']=list(self.history);return data

def capture_game(base):
 """Capture only the game's compositor backing pixmap, never the desktop."""
 from io import BytesIO
 from PIL import Image
 import os
 if os.name=='nt':
  return __import__('windows_capture').capture_game(base)
 from Xlib import display,X,error
 from Xlib.ext import composite
 from lab import game_window
 import psutil
 connection=None;pixmap=None;redirected=False;window=None
 try:
  win=game_window();process=psutil.Process(win.pid)
  if Path(process.cwd()).resolve()!=(Path(base)/'IWBTB').resolve() or Path(process.environ().get('WINEPREFIX','/missing')).resolve()!=(Path(base)/'wineprefix').resolve():raise ValueError('Game identity mismatch')
  connection=display.Display()
  if not connection.has_extension('Composite'):raise RuntimeError('Window capture unavailable')
  window=connection.create_resource_object('window',win._hWnd)
  trap=error.CatchError();pixmap=window.composite_name_window_pixmap(onerror=trap);connection.sync()
  if trap.get_error():
   # Mint may unredirect the game for performance. Automatic redirection keeps
   # normal screen presentation and gives us only this window's backing store.
   pixmap=None;trap=error.CatchError();window.composite_redirect_window(composite.RedirectAutomatic,onerror=trap);connection.sync()
   if trap.get_error():raise RuntimeError('Game window cannot be captured independently')
   redirected=True;pixmap=window.composite_name_window_pixmap();connection.sync()
  g=pixmap.get_geometry()
  if not 0<g.width*g.height<=16_000_000 or g.depth not in (24,32):raise ValueError('Unsupported game window size/format')
  raw=pixmap.get_image(0,0,g.width,g.height,X.ZPixmap,0xffffffff)
  if len(raw.data)!=g.width*g.height*4:raise ValueError('Unsupported window pixel layout')
  picture=Image.frombytes('RGB',(g.width,g.height),raw.data,'raw','BGRX');output=BytesIO();picture.save(output,format='PNG')
  if output.tell()>12*1024*1024:raise ValueError('Screenshot size limit')
  return output.getvalue(),{'captured_at':time.time(),'width':g.width,'height':g.height,'scope':'game-window-only'}
 except Exception as e:return None,{'captured_at':time.time(),'unavailable':str(e),'scope':'game-window-only'}
 finally:
  if pixmap:
   try:pixmap.free()
   except Exception:pass
  if redirected and window:
   try:window.composite_unredirect_window(composite.RedirectAutomatic);connection.sync()
   except Exception:pass
  if connection:connection.close()
