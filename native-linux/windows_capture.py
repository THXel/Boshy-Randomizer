"""Capture the verified game window with PrintWindow, never the desktop."""
import ctypes as c,time
from ctypes import wintypes as w
from io import BytesIO
from PIL import Image
from windows_api import user

def capture_game(base):
 dc=mem=bitmap=old=None;gdi=c.WinDLL('gdi32');result={'scope':'game-window-only','captured_at':time.time()}
 try:
  from lab import game_window
  from host_platform import owned_process
  import psutil
  game=game_window()
  if not owned_process(psutil.Process(game.pid),base):raise ValueError('Game identity mismatch')
  rect=w.RECT()
  if not user.GetClientRect(game._hWnd,c.byref(rect)):raise RuntimeError('No client rectangle')
  width,height=rect.right,rect.bottom
  if not 0<width*height<=16_000_000:raise ValueError('Capture size limit')
  user.GetDC.argtypes=[w.HWND];user.GetDC.restype=w.HDC
  user.ReleaseDC.argtypes=[w.HWND,w.HDC]
  user.PrintWindow.argtypes=[w.HWND,w.HDC,w.UINT];user.PrintWindow.restype=w.BOOL
  for name,ret,args in [('CreateCompatibleDC',w.HDC,[w.HDC]),('CreateCompatibleBitmap',w.HBITMAP,[w.HDC,c.c_int,c.c_int]),('SelectObject',w.HGDIOBJ,[w.HDC,w.HGDIOBJ]),('DeleteObject',w.BOOL,[w.HGDIOBJ]),('DeleteDC',w.BOOL,[w.HDC])]:
   f=getattr(gdi,name);f.restype=ret;f.argtypes=args
  dc=user.GetDC(game._hWnd);mem=gdi.CreateCompatibleDC(dc);bitmap=gdi.CreateCompatibleBitmap(dc,width,height)
  if not all((dc,mem,bitmap)):raise RuntimeError('Capture allocation failed')
  old=gdi.SelectObject(mem,bitmap)
  if not user.PrintWindow(game._hWnd,mem,3):raise RuntimeError('Window did not provide a capture')
  class INFO(c.Structure):_fields_=[('size',w.DWORD),('width',w.LONG),('height',w.LONG),('planes',w.WORD),('bits',w.WORD),('compression',w.DWORD),('imageSize',w.DWORD),('x',w.LONG),('y',w.LONG),('used',w.DWORD),('important',w.DWORD)]
  info=INFO(c.sizeof(INFO),width,-height,1,32,0,0,0,0,0,0);buf=c.create_string_buffer(width*height*4)
  gdi.GetDIBits.argtypes=[w.HDC,w.HBITMAP,w.UINT,w.UINT,c.c_void_p,c.c_void_p,w.UINT]
  gdi.SelectObject(mem,old);old=None
  if gdi.GetDIBits(mem,bitmap,0,height,buf,c.byref(info),0)!=height:raise RuntimeError('Incomplete capture')
  output=BytesIO();Image.frombytes('RGB',(width,height),buf.raw,'raw','BGRX').save(output,format='PNG')
  return output.getvalue(),{**result,'width':width,'height':height}
 except Exception as error:return None,{**result,'unavailable':str(error)}
 finally:
  if old:gdi.SelectObject(mem,old)
  if bitmap:gdi.DeleteObject(bitmap)
  if mem:gdi.DeleteDC(mem)
  if dc:user.ReleaseDC(game._hWnd,dc)
