"""Short-lived loading cover; keeps process/profile switching out of the menu UX."""
from ui_i18n import tr, display as localize, font_path, font_family, configure_tk, LANGUAGE, Localized
import json,os,select,subprocess,sys,time
from pathlib import Path

class LoadingScreen:
 def __init__(self,base,slot=0,message=tr('Spielstand wird geladen …'),destination=None):
  self.position=None;self.p=None;self.old_sink=os.environ.get("PULSE_SINK");base=Path(base)
  try:
   from lab import game_window
   from window_position import WindowPosition
   game=game_window();rect=client_rect(game);pid=game.pid;self.position=WindowPosition.capture(game)
  except RuntimeError:rect=None;pid=None
  (base/'menu-runtime').mkdir(exist_ok=True)
  log=(base/'menu-runtime/loading.log').open('a')
  self.p=subprocess.Popen([sys.executable,str(base/'loading_screen.py'),'--window',json.dumps(dict(slot=slot,message=message,rect=rect,pid=pid,destination=destination,position=vars(self.position) if self.position else None))],cwd=base,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=log,text=True,bufsize=1)
  log.close()
  ready=self.p.stdout.readline().strip() if select.select([self.p.stdout],[],[],8)[0] else ''
  if not ready.startswith('READY '):
   self.close();raise RuntimeError(tr('Ladebildschirm konnte nicht geöffnet werden. Spielstand bleibt unverändert.'))
  os.environ['PULSE_SINK']=ready.split(' ',1)[1]
 def restore_game(self):
  if self.position:self.position.restore()
 def close(self):
  if self.p is None:return
  p,self.p=self.p,None
  if self.old_sink is None:os.environ.pop("PULSE_SINK",None)
  else:os.environ["PULSE_SINK"]=self.old_sink
  try:
   if p.poll() is None:p.stdin.close();p.wait(timeout=8)
  except (OSError,subprocess.TimeoutExpired):
   if p.poll() is None:p.terminate();p.wait(timeout=8)
  finally:p.stdout.close()

def client_rect(game):
 from PY.platform_windows import connection
 win=game._window;xy=connection().screen().root.translate_coords(win,0,0);g=win.get_geometry()
 return xy.x,xy.y,g.width,g.height

def monitor(rect,sw,sh):
 # Confine loading to the actual game area; never obscure an entire monitor.
 return tuple(rect) if rect else (max(0,(sw-880)//2),max(0,(sh-660)//2),880,660)

def window(settings):
 import tkinter as tk,threading,queue
 from PIL import Image,ImageTk,ImageOps
 from loading_audio import AudioGate
 gate=AudioGate(settings.get('pid'))
 try:
  root=tk.Tk();root.withdraw();root.title(tr('Boshy · Laden'));root.overrideredirect(True);root.attributes('-topmost',True)
  x,y,w,h=monitor(settings.get('rect'),root.winfo_screenwidth(),root.winfo_screenheight());root.geometry(f'{w}x{h}{x:+d}{y:+d}')
  canvas=tk.Canvas(root,bg='#101216',highlightthickness=0);canvas.pack(fill='both',expand=True)
  logo=Image.open(Path(__file__).resolve().parent/'Custom/boshy_randomizer.png').convert('RGBA');logo.thumbnail((min(640,w//2),min(260,h//3)),Image.Resampling.LANCZOS);photo=ImageTk.PhotoImage(logo)
  canvas.create_image(w/2,h*.23,image=photo)
  destination=settings.get('destination') or {}
  if destination.get('icon'):
   icon=Image.open(destination['icon']).convert('RGBA');icon=ImageOps.contain(icon,(96,96),method=Image.Resampling.NEAREST);target_photo=ImageTk.PhotoImage(icon)
   canvas.create_image(w/2,h*.44,image=target_photo)
  canvas.create_text(w/2,h*.53,text=localize(destination.get('kind','').upper()),fill='#61dbe8',font=(font_family(),14,'bold'))
  canvas.create_text(w/2,h*.58,text=localize(destination.get('name','')),fill='white',font=(font_family(),24,'bold'),width=w-60)
  text=localize(settings['message']);canvas.create_text(w/2,h*.68,text=text,fill='#ffffff',font=(font_family(),max(18,min(27,w//65))))
  if settings.get('slot'):canvas.create_text(w/2,h*.73,text=tr('Speicherplatz {0}', str(settings['slot'])),fill='#aebbc7',font=(font_family(),16))
  left,right=w/2-160,w/2+160;canvas.create_rectangle(left,h*.79,right,h*.79+5,fill='#283039',outline='');bar=canvas.create_rectangle(left,h*.79,left+70,h*.79+5,fill='#61dbe8',outline='')
  # The cover must not steal keyboard focus from the native, state-checked loader.
  root.update()
  try:
   from Xlib import display,Xutil
   d=display.Display();win=d.create_resource_object('window',root.winfo_id());
   from Xlib.ext import shape
   for target in (win,win.query_tree().parent):
    target.set_wm_hints(flags=Xutil.InputHint,input=0)
    target.shape_rectangles(shape.SO.Set,shape.SK.Input,0,0,0,[])
   d.sync();d.close()
  except Exception:pass
  root.deiconify();root.update()
  print('READY '+gate.name,flush=True);ended=threading.Event()
  def listen():
   for _ in sys.stdin:pass
   ended.set()
  threading.Thread(target=listen,daemon=True).start();start=time.monotonic()
  def tick():
   if ended.is_set():root.destroy();return
   if settings.get('position'):
    try:
     from window_position import WindowPosition
     WindowPosition(**settings['position']).restore()
    except Exception:pass
   dx=((time.monotonic()-start)*120)%250;canvas.coords(bar,left+dx,h*.79,left+dx+70,h*.79+5);root.lift();root.after(40,tick)
  tick();root.mainloop()
 finally:gate.close()

if __name__=='__main__':window(json.loads(sys.argv[2]))
