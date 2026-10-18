import copy,json,sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from minibosses import Gate,prepare_pool
from native_level_route import catalogue
from native_triggers import exits_for
from native_progress import Progress
from beta_catalogue import catalogue as bosses,EXTRA_POINTS
import run_settings as r
from run_extras import defaults as extras

def options(version=6,mode='randomizer'):
 return r.normalize(dict(difficulty=1,levels=True,items=True,characters=False,mode=mode,target_count=5,boss_count=0,**r.defaults(version),extras=extras()))
def pool(version=6):
 p=catalogue(json.loads((ROOT/'INI/positions.json').read_text()));p.update(json.loads((ROOT/'native_spots.json').read_text()));p.update(EXTRA_POINTS)
 return prepare_pool(p,options(version))
def sample(x=717,y=6607,tick=100,boss=42,door=True,intro=False,alive=True,generation=(11,22)):
 return dict(frame=27,position=[x,y],tick=tick,boss_object=boss,exit_blocked=door,intro_active=intro,player_alive=alive,generation=list(generation))
class KidIcarus(unittest.TestCase):
 def test_new_pool_contains_user_confirmed_points_and_old_rules_unchanged(self):
  p=pool();self.assertEqual((p['boss_kid_icarus']['x'],p['boss_kid_icarus']['y']),(717,6600));self.assertEqual((p['kid_icarus_after']['x'],p['kid_icarus_after']['y']),(1288,6607))
  self.assertEqual(exits_for('save12.ini',p['save12.ini']),());self.assertEqual(exits_for('boss_kid_icarus',p['boss_kid_icarus']),());self.assertEqual(exits_for('kid_icarus_after',p['kid_icarus_after']),(59,))
  old=pool(5);self.assertNotIn('segment',old['save12.ini']);self.assertNotIn('kid_icarus_after',old);self.assertEqual(exits_for('save12.ini',old['save12.ini']),(59,));self.assertNotIn('kid_icarus',bosses(options(5)))
 def test_entry_only_after_crossing_above_checkpoint_not_spawn_or_reset(self):
  p=pool()['save12.ini'];g=Gate()
  self.assertIsNone(g.observe('save12.ini',0,p,sample(),0,0))
  self.assertIsNone(g.observe('save12.ini',0,p,sample(y=6671,tick=110),0,1))
  self.assertEqual(g.observe('save12.ini',0,p,sample(tick=120),0,2),'Miniboss-Eingang')
  self.assertIsNone(g.observe('save12.ini',0,p,sample(tick=1),0,3))
 def test_boss_requires_living_encounter_all_fragments_and_open_exit(self):
  p=pool()['boss_kid_icarus'];g=Gate()
  self.assertIsNone(g.observe('boss_kid_icarus',0,p,sample(boss=None,door=False),0,0))
  g.observe('boss_kid_icarus',0,p,sample(tick=110),0,1)
  self.assertIsNone(g.observe('boss_kid_icarus',0,p,sample(boss=99,tick=120),0,2))
  self.assertIsNone(g.observe('boss_kid_icarus',0,p,sample(boss=None,tick=130),0,3))
  self.assertIsNone(g.observe('boss_kid_icarus',0,p,sample(boss=None,door=False,tick=140),0,4))
  self.assertEqual(g.observe('boss_kid_icarus',0,p,sample(boss=None,door=False,tick=150),0,5.1),'Kid Icarus besiegt')
 def test_death_reset_and_new_scene_generation_never_award(self):
  p=pool()['boss_kid_icarus']
  for change,deaths in [({'tick':1},0),({},1),({'alive':False},0),({'generation':(33,44)},0),({'intro':True},0)]:
   g=Gate();g.observe('boss_kid_icarus',0,p,sample(),0,0)
   self.assertIsNone(g.observe('boss_kid_icarus',0,p,sample(boss=None,door=False,**change),deaths,3))
 def test_all_new_destinations_work_with_shared_seed_and_loading(self):
  from loading_destination import for_selection
  for spot in ('boss_kid_icarus','kid_icarus_after'):
   o=options(9);o.update(level_count=int(spot=='kid_icarus_after'),route_boss_count=int(spot=='boss_kid_icarus'),level_pool=['kid_icarus_after'],boss_pool=['kid_icarus'])
   seed,decoded=r.decode(r.encode('1234ABCD',o));self.assertEqual(r.route(seed,decoded)[0],spot)
   with patch('loading_destination.for_frame',side_effect=lambda base,frame:frame):self.assertEqual(for_selection(SimpleNamespace(base=ROOT),2,'new',dict(seed=seed,options=o)),27)
 def test_target_receipt_and_checkpoint_do_not_skip_new_segments(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);(root/'run').mkdir();o=options(mode='target');m=dict(run_id='run',session_binding='test',seed='1234ABCD',options=o,pool=pool());store=SimpleNamespace(base=ROOT,root=root)
   p=Progress(store,m);p.goals={'items':[],'bosses':['kid_icarus']};p.data['spot']='boss_kid_icarus'
   def observe(s,t):
    with patch('minibosses.time.monotonic',return_value=t):return p.observe(frame=27,position=(717,6600),collectables={},achievements={},disk_achievements={},stats={},mini_sample=s)
   self.assertIsNone(observe(sample(),0));self.assertIsNone(observe(sample(boss=None,door=False,tick=120),1));self.assertEqual(observe(sample(boss=None,door=False,tick=140),2.1),'boss_solgryn.ini');self.assertIn('kid_icarus',p.data['stage_bosses'])
   p.data['pending']=None;p.data['checkpoints']={'27':[717,6664]};p.request({},3,'test',{},target='kid_icarus_after');self.assertEqual(p.destination('kid_icarus_after'),m['pool']['kid_icarus_after'])
if __name__=='__main__':unittest.main()
