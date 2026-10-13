"""Restore the game's outer origin without moving the pointer or changing its size."""
import subprocess,time
from dataclasses import dataclass
from lab import game_window
from PY.platform_windows import window_rect

@dataclass(frozen=True)
class WindowPosition:
 x:int
 y:int
 @classmethod
 def capture(cls,window):
  x,y,_,_=window_rect(window)
  return cls(x,y)
 def restore(self,window=None):
  from PY.platform_windows import _property
  window=window or game_window()
  for _ in range(12):
   x,y,_,_=window_rect(window)
   if (x,y)==(self.x,self.y):return window
   extents=list(_property(window._window,'_NET_FRAME_EXTENTS',[0,0,0,0]))
   # Wine uses StaticGravity: move the client origin, including the top border.
   request_x,request_y=self.x+extents[0],self.y+extents[2]
   subprocess.run(['wmctrl','-ir',hex(window._hWnd),'-e',f'10,{request_x},{request_y},-1,-1'],check=True,timeout=3)
   end=time.monotonic()+.25
   while time.monotonic()<end:
    time.sleep(.025);x,y,_,_=window_rect(window)
    if (x,y)==(self.x,self.y):return window
  raise RuntimeError(f'Die Fensterposition wurde nicht bestätigt: gewünscht {(self.x,self.y)}, gemessen {(x,y)}.')

def wait_for_game(position=None,timeout=15):
 end=time.monotonic()+timeout
 while True:
  try:window=game_window();break
  except RuntimeError:
   if time.monotonic()>=end:raise
   time.sleep(.1)
 return position.restore(window) if position else window
