import json,random,struct,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import intro_cast as cast

def raw_image(width,height,pixels,flags=0):
 header=bytearray(32);struct.pack_into('<HH',header,12,width,height);header[16:18]=bytes([4,flags]);return bytes(header)+pixels

class IntroCastTests(unittest.TestCase):
 def test_no_repeat_per_role_or_duplicate_cast(self):
  previous=None;rng=random.Random(123)
  for _ in range(1000):
   chosen=cast.choose(previous,rng);self.assertEqual(len(set(chosen)),3)
   if previous:self.assertTrue(all(a!=b for a,b in zip(previous,chosen)))
   self.assertLessEqual(set(chosen),set(cast.CAST));previous=chosen
 def test_does_not_consume_gameplay_random_state(self):
  before=random.getstate();cast.choose(None);self.assertEqual(before,random.getstate())
 def test_invalid_previous_is_ignored(self):
  for value in (None,{},'oops',[],[1]):self.assertEqual(len(cast.choose(value)),3)
 def test_bgr_transparency_and_even_row_padding(self):
  im=cast.image(raw_image(1,2,bytes([0,0,255,0,0,0,0,0,0,0,0,0])))
  self.assertEqual(im.getpixel((0,0)),(255,0,0,255));self.assertEqual(im.getpixel((0,1)),(0,0,0,0))
 def test_rle_repeated_and_literal_pixels(self):
  im=cast.image(raw_image(4,1,bytes([2,0,0,255,130,0,255,0,255,0,0,0]),4))
  self.assertEqual(list(im.getdata()),[(255,0,0,255)]*2+[(0,255,0,255),(0,0,255,255)])
 def test_bad_image_is_rejected(self):
  for raw in (raw_image(0,1,b''),raw_image(2,1,b'\0',4),raw_image(2,1,b'\x03\0\0\0',4),raw_image(2,1,b'',0)):
   with self.assertRaises((ValueError,IndexError)):cast.image(raw)
 def test_chunk_bounds_and_flags(self):
  for data in (b'bad',struct.pack('<HHI',1,0,8),struct.pack('<HHI',1,2,0)):
   with self.assertRaises(ValueError):list(cast.chunks(data,0,len(data)))
 def test_unknown_game_fails_before_parsing(self):
  with tempfile.TemporaryDirectory() as folder:
   p=Path(folder)/'game.exe';p.write_bytes(b'unknown')
   with self.assertRaisesRegex(ValueError,'checksum'):cast.read_game(p,'0'*64)
 def test_preparation_failure_removes_stale_plan_preserves_last_cast(self):
  with tempfile.TemporaryDirectory() as folder:
   base=Path(folder);root=base/'menu-runtime';root.mkdir();(root/'intro.bin').write_bytes(b'stale');(root/'intro-last.json').write_text('{"cast":[194,197,198]}')
   with patch.object(cast,'read_game',side_effect=ValueError('bad game')),self.assertLogs(level='ERROR'):
    self.assertIsNone(cast.prepare(base))
   self.assertFalse((root/'intro.bin').exists());self.assertEqual(json.loads((root/'intro-last.json').read_text())['cast'],[194,197,198])
 def test_host_prepares_once_before_restart_loop(self):
  import ast
  tree=ast.parse((Path(cast.__file__).parent/'native_menu_host.py').read_text());calls=[n for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='prepare_intro'];self.assertEqual(len(calls),1)
  for node in ast.walk(tree):
   if isinstance(node,(ast.While,ast.For)):self.assertNotIn(calls[0],list(ast.walk(node)))

if __name__=='__main__':unittest.main()
