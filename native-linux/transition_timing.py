"""Read-only transition telemetry. Clock values never participate in routing."""
from collections import deque
from copy import deepcopy
import time

class Timings:
 def __init__(self,clock=time.monotonic):
  self.clock=clock;self.rows=deque(maxlen=32);self.current=None
 def begin(self,index,source,target,reason=None):
  key=(index,source,target)
  if self.current and self.current['_key']==key:return
  if self.current:self.current['status']='interrupted'
  row=dict(index=index,source=source,target=target,reason=reason,detected_at=time.time(),status='pending',attempts=0,
           detection_to_request_ms=None,request_to_arrival_ms=None,total_ms=None,_key=key,_detected=self.clock())
  self.rows.append(row);self.current=row
 def phase(self,stage):
  row=self.current
  if row is None:return
  now=self.clock()
  if stage=='requested':
   row['attempts']+=1
   if '_requested' not in row:row['_requested']=now
   row['status']='loading'
  elif stage=='spawn-reset':row['target_resets']=row.get('target_resets',0)+1
  elif stage=='arrived':row['_arrived']=now;row['status']='arrived'
 def complete(self):
  if self.current:
   row=self.current;row.setdefault('_arrived',self.clock());row['status']='confirmed' if row['attempts'] else 'already_at_target';self.current=None
 def snapshot(self):
  result=[];now=self.clock()
  for row in self.rows:
   public={k:v for k,v in row.items() if not k.startswith('_')}
   detected=row['_detected'];requested=row.get('_requested');arrived=row.get('_arrived')
   if requested is not None:public['detection_to_request_ms']=round(max(0,requested-detected)*1000,2)
   if requested is not None and arrived is not None:public['request_to_arrival_ms']=round(max(0,arrived-requested)*1000,2)
   if arrived is not None:public['total_ms']=round(max(0,arrived-detected)*1000,2)
   elif row is self.current:public['elapsed_ms']=round(max(0,now-detected)*1000,2)
   result.append(public)
  return deepcopy(result)

def observe(bridge,stage):
 """Instrumentation must never interrupt a working game transition."""
 callback=getattr(bridge,'transition_observer',None)
 if callable(callback):
  try:callback(stage)
  except Exception:pass
