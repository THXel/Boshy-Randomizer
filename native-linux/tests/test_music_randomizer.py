import copy,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import music_randomizer as music,run_extras as extras,run_settings as settings,seed_share
from test_compact_seeds import options
class Music(unittest.TestCase):
 def test_deterministic_combined_permutation_without_self_swaps(self):
  a=music.mapping('same');self.assertEqual(a,music.mapping('same'));self.assertNotEqual(a,music.mapping('different'))
  self.assertEqual(set(a),set(music.TRACKS));self.assertEqual(set(a.values()),set(a));self.assertTrue(all(k!=v for k,v in a.items()))
 def test_music_and_shots_have_distinct_flags(self):
  o=options();self.assertFalse(o['extras']['music']);before=extras.flags(o)
  o['extras']['music']=True;self.assertEqual(extras.flags(o)^before,4096)
  o['extras']['shot_mode']='spot';self.assertEqual(extras.flags(o)^before,4096|2048)
 def test_new_setting_is_shared_without_changing_route(self):
  o=options();before=settings.route('MUSIC',o);o['extras']['music']=True
  code=seed_share.encode('MUSIC',o,ROOT);self.assertEqual(settings.decode(code),('MUSIC',settings.normalize(o)));self.assertEqual(settings.route('MUSIC',o),before)
 def test_old_codes_remain_byte_exact_and_music_stays_off(self):
  for code in ('BR3-ARI0q80AZSwBuA','BR4-ARI0q80AGVBuhw'):
   seed,o=settings.decode(code);self.assertEqual(settings.encode(seed,o),code);self.assertFalse(extras.enabled(o,'music'))
   old=copy.deepcopy(o);extras.upgrade(o);self.assertEqual(o['extras']['version'],5);self.assertFalse(o['extras']['music']);self.assertEqual(settings.route(seed,old),settings.route(seed,o))
 def test_old_versions_cannot_smuggle_new_option(self):
  for version in (1,2,3):
   e=extras.defaults();e['version']=version
   with self.assertRaises(ValueError):extras.normalize(e)
 def test_localized_compact_hack_controls_do_not_overlap(self):
  import ui_i18n
  from menu_controls import controls
  from types import SimpleNamespace
  rows=controls(SimpleNamespace(page='extras'))
  for a,b in zip(rows,rows[1:]):self.assertLess(a[1][3],b[1][1])
  for lang in ui_i18n.SUPPORTED:
   for text in extras.EXTRAS[-1][1:3]:self.assertIn(text,ui_i18n.catalog(lang))
if __name__=='__main__':unittest.main()
