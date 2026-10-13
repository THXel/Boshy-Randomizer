"""Keep only this Boshy instance silent across its loading handoff."""
import json,os,subprocess,threading

def pulse(*args):
 return subprocess.check_output(['pactl',*map(str,args)],text=True,timeout=3,stderr=subprocess.DEVNULL).strip()

class AudioGate:
 def __init__(self,game_pid=None):
  self.name=f'boshy_loading_{os.getpid()}';self.module=None;self.saved={};self.stop=threading.Event();self.thread=None
  self.target=pulse('get-default-sink')
  try:
   self.module=pulse('load-module','module-null-sink',f'sink_name={self.name}','sink_properties=device.description=Boshy-Loading')
   pulse('set-sink-mute',self.name,1)
   self.sink=next(x['index'] for x in json.loads(pulse('-f','json','list','sinks')) if x['name']==self.name)
   for row in self.inputs():
    if game_pid and str(row.get('properties',{}).get('application.process.id'))==str(game_pid):
     self.saved[row['index']]=(row['sink'],row.get('mute',False));self.target=row['sink']
     pulse('set-sink-input-mute',row['index'],1);pulse('move-sink-input',row['index'],self.name)
   self.thread=threading.Thread(target=self.watch,daemon=True);self.thread.start()
  except Exception:
   self.close();raise RuntimeError('Boshy konnte zum Laden nicht stummgeschaltet werden.')
 def inputs(self):return json.loads(pulse('-f','json','list','sink-inputs'))
 def watch(self):
  while not self.stop.wait(.05):
   try:
    for row in self.inputs():
     if row['sink']==self.sink or row['index'] in self.saved:
      self.saved.setdefault(row['index'],(self.target,False))
      if not row.get('mute'):pulse('set-sink-input-mute',row['index'],1)
   except (OSError,ValueError,subprocess.SubprocessError):pass
 def close(self):
  self.stop.set()
  if self.thread:self.thread.join(timeout=4)
  if self.module is None:return
  try:
   for row in self.inputs():
    if row['index'] in self.saved or row['sink']==getattr(self,'sink',None):
     target,mute=self.saved.get(row['index'],(self.target,False))
     try:
      try:pulse('move-sink-input',row['index'],target)
      except subprocess.SubprocessError:pulse('move-sink-input',row['index'],pulse('get-default-sink'))
      pulse('set-sink-input-mute',row['index'],int(mute))
     except subprocess.SubprocessError:pass
  finally:
   pulse('unload-module',self.module);self.module=None
