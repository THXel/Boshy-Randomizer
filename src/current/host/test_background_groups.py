"""Whole compositions, original gameplay, deterministic choices and menu layers."""
import copy,importlib.util,unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"Boshy-Randomizer/src/python/graphics"))
from unittest.mock import patch
import recover_boshy_routes as source
from visuals import background_groups as bg
from transition.events import commands
from transition.router import frame_metadata
from native_menu import events

class BackgroundGroupTests(unittest.TestCase):
 def test_matches_old_randomizer_and_locked_cameras(self):
  spec=importlib.util.spec_from_file_location('old_bg',bg.CATALOGUE.parents[2]/'src/python/graphics/background_sets.py')
  old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
  with patch.object(old,'catalogue',bg.catalogue):
   for seed in map(str,range(25)):
    self.assertEqual(bg.mapping(seed,True),old.mapping(seed,True))
    for target,choice in zip(bg.catalogue()['sets'],bg.mapping(seed,True)):
     if target['locked']:self.assertEqual(target['coefficient'],bg.catalogue()['sets'][choice]['coefficient'])
 def test_gameplay_instances_and_original_objects_unchanged(self):
  for n,frame in enumerate(source.frames,1):
   original=copy.deepcopy(frame);objects=copy.deepcopy(source.objects)
   result,clones=bg.convert_frame(n,frame,source.objects)
   self.assertEqual(original,frame);self.assertEqual(objects,source.objects)
   if bg.target_index(n) is None:self.assertIs(result,frame);continue
   before={i['handle']:i for i in frame['instances']};after={i['handle']:i for i in result['instances']}
   self.assertEqual(len(after),len(result['instances']))
   for h,i in before.items():
    expected=dict(i,x=-32000,y=-32000) if i['layer']==0 and i['objectInfo'] in bg.owned() and source.objects[i['objectInfo']]['type']==1 else i
    self.assertEqual(after[h],expected)
   for index,row in enumerate(bg.catalogue()['objects']):
    o=clones[bg.helper(index)];self.assertEqual(o['qualifiers'],[])
    for key in ('inkEffect','inkEffectParameter','shader'):self.assertEqual(o[key],objects[row['oi']][key])
    if row['type']==48:self.assertEqual(o['private'],objects[row['oi']]['private'])
    else:self.assertEqual(o['animations'][0]['directions'][0]['frames'],[row['image']])
   self.assertEqual(result['instances'][-1]['objectInfo'],bg.DIM_OBJECT)
   self.assertEqual(result['instances'][-1]['layer'],0)
   self.assertEqual({i['layer'] for i in result['instances'] if bg.FIRST<=i['objectInfo']<bg.FIRST+25},{0})
 def test_original_events_preserved_only_cosmetics_changed(self):
  for p,n in source.payloads.items():
   before=source.original_sections(p);after,audit=bg.transform(n,before,source.objects,source.frames[n-1]['instances'])
   if not audit:self.assertEqual(after,before);continue
   self.assertEqual(after[:-1],before)
   self.assertTrue(all(row[2]>0 for row in after[-1]))
   ini=frame_metadata(n,before,source.objects,source.frames[n-1]['instances'])[0]
   changed={c[3] for row in after[-1] for c in commands(row) if not c[0]}
   self.assertFalse(changed-bg.owned()-set(range(bg.FIRST,bg.FIRST+25))-{84,ini,bg.DIM_OBJECT})
 def test_off_keeps_original_group_and_brightness(self):
  s=bg.settings('x',dict(sprite_scenery=False,sprite_backgrounds=True,sprite_dim=80))
  self.assertEqual(s['BackgroundDim'],0)
  self.assertEqual([s['BackgroundSet'+str(i)] for i in range(9)],list(range(9)))
 def test_no_background_layer_is_independently_shuffled(self):
  import tempfile
  from visuals import scenery_assets
  with tempfile.TemporaryDirectory() as folder:
   rows,_=scenery_assets.prepare(folder,'ALL-BACKGROUNDS',dict(sprite_scenery=True,sprite_backgrounds=True,sprite_dim=0))
   kinds={r['oi']:r['category'] for r in scenery_assets.records()}
   self.assertTrue(any(kinds[r['oi']]==1 for r in rows))
   self.assertFalse(any(r['changed'] for r in rows if kinds[r['oi']]==1))
 def test_update_card_after_background_before_foreground(self):
  f=copy.deepcopy(source.frames[1]);o=dict(source.objects);events.clone_objects(o,f)
  card=next(i for i in f['instances'] if i['objectInfo']==4510);self.assertEqual(card['layer'],0)
  for oi in [30,79]:self.assertLess(f['instances'].index(next(i for i in f['instances'] if i['objectInfo']==oi)),f['instances'].index(card))
  for oi in [18,21,23,41,43,44,45,events.PANEL]:self.assertGreater(next(i for i in f['instances'] if i['objectInfo']==oi)['layer'],0)
if __name__=='__main__':unittest.main()
