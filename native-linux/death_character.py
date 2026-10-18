"""Persisted, seeded death cycle using the same native profile transaction."""
import json
from character_cycle import CharacterCycle,available,choose
from native_session import write_json
class DeathCycle(CharacterCycle):
 def __init__(self,store,m):
  self.store=store;self.m=m;self.path=store.root/m['run_id']/'death-characters.json'
  self.data=json.loads(self.path.read_text(encoding='utf-8')) if self.path.exists() else dict(run_id=m['run_id'],binding=m['session_binding'],observed=None,sequence=0,choices={})
  if self.data['run_id']!=m['run_id'] or self.data['binding']!=m['session_binding']:raise ValueError('Falscher Charakterverlauf.')
 def observe(self,stats,bridge,menu):
  from lab import ini_object_ids,ini_items
  deaths=int(stats.get('deaths',0));old=self.data['observed']
  if old is None or deaths<old:
   self.data['observed']=deaths;write_json(self.path,self.data);return
  if deaths==old:return
  ids=ini_object_ids(bridge);unlocks={k:v['value'] for k,v in ini_items(bridge,'unlockables',ids['Ini++ 3']).items()}
  license=ini_items(bridge,'license',ids['Ini++ 3']);seq=self.data['sequence']+1
  key=str(seq)
  if key not in self.data['choices']:
   self.data['choices'][key]=choose(self.m['seed']+'\0death-cycle-v1',seq,available(self.store.base,unlocks),license['charactername']['value'])
   write_json(self.path,self.data)
  picked=self.prepare(seq,bridge,menu)
  self.data.update(observed=deaths,sequence=seq);write_json(self.path,self.data)
  return picked
