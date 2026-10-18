"""Mute only this private game's Windows audio sessions during loading."""
import threading,time
class AudioGate:
 def __init__(self,game_pid=None):
  self.name='windows';self.stop=threading.Event();self.ready=threading.Event();self.error=None
  self.thread=threading.Thread(target=self.watch,daemon=True);self.thread.start()
  if not self.ready.wait(5) or self.error:
   self.close();raise RuntimeError('Windows audio gate failed: '+str(self.error))
 def watch(self):
  import comtypes
  comtypes.CoInitialize()
  saved={}
  try:
   from pycaw.pycaw import AudioUtilities
   from host_platform import owned_process
   from runtime_paths import BASE
   while not self.stop.is_set():
    for session in AudioUtilities.GetAllSessions():
     if not session.Process or not owned_process(session.Process,BASE):continue
     key=session.InstanceIdentifier;volume=session.SimpleAudioVolume
     if key not in saved:saved[key]=(volume,volume.GetMute())
     volume.SetMute(1,None)
    self.ready.set();self.stop.wait(.04)
  except Exception as error:self.error=error;self.ready.set()
  finally:
   for volume,muted in saved.values():
    try:volume.SetMute(muted,None)
    except Exception:pass
   comtypes.CoUninitialize()
 def close(self):
  self.stop.set()
  if self.thread:self.thread.join(timeout=5)
