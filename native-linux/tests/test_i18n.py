import unittest,sys,json,string
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import ui_i18n as ui
class Languages(unittest.TestCase):
 def test_detection(self):
  for value,expected in [('de_DE.UTF-8','de'),('ru_RU','ru'),('es-MX','es'),('ja_JP','ja'),('en_GB','en'),('fr_FR','en'),('C.UTF-8','en')]:
   with self.subTest(value=value):self.assertEqual(ui.detect_language({'LANG':value}),expected)
  self.assertEqual(ui.detect_language({'LANGUAGE':'fr:ja'}),'ja')
  self.assertEqual(ui.detect_language({'BOSHY_LANGUAGE':'ru','LANG':'de_DE'}),'ru')
  self.assertEqual(ui.detect_language({},'de_DE.UTF-8'),'de')
 def test_catalogs_and_placeholders(self):
  english=ui.catalog('en')
  def fields(text):return sorted(v for _,v,_,_ in string.Formatter().parse(text) if v is not None)
  for code in ui.SUPPORTED:
   catalog=ui.catalog(code);self.assertEqual(catalog.keys(),english.keys())
   for key,value in catalog.items():
    with self.subTest(language=code,key=key):self.assertTrue(value);self.assertEqual(fields(key),fields(value))
 def test_missing_translation_falls_back_to_english(self):
  old=ui.LANGUAGE;ui.LANGUAGE='ja';catalog=ui.catalog('ja');saved=catalog.pop('Neuer Lauf')
  try:self.assertEqual(ui.tr('Neuer Lauf'),'New run')
  finally:catalog['Neuer Lauf']=saved;ui.LANGUAGE=old
 def test_canonical_values_remain_untouched(self):
  for value in ('BR2-a1B2c3-12345','Dark Boshy','Awesomesauce','seed_1','save23.ini'):
   self.assertEqual(ui.display(value),value)
 def test_changelog_is_english(self):
  entries=json.loads((ROOT/'menu_updates.json').read_text())['entries'];self.assertEqual(entries[0]['title'],'Recent improvements')
if __name__=='__main__':unittest.main()
