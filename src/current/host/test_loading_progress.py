import tempfile
import unittest
from pathlib import Path
from native_menu.loading import listen, report, TEXT, LANGS
from native_menu.classic import ClassicModel, ClassicRenderer
from menu_host.store import Store

class LoadingTests(unittest.TestCase):
    def test_worker_reports_are_scoped_and_ordered(self):
        seen=[]
        report(1,'prepare')
        with listen(seen.append):
            report(2,'prepare'); report(45,'music'); report(90,'check')
        report(100,'start')
        self.assertEqual(seen,[(2,'prepare'),(45,'music'),(90,'check')])
        self.assertTrue(all(len(v)==len(LANGS) for v in TEXT.values()))

    def test_new_run_settings_show_progress_in_every_language(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);m=ClassicModel(Store(p/'profile',runs=p/'runs'));r=ClassicRenderer(p)
            m.go('settings');m.busy=True;m.busy_label='busy';m.loading_progress=(45,'music')
            for lang in LANGS:
                m.language=lang;im=r.render(m)
                self.assertEqual(im.getpixel((100,355))[:3],(140,221,198))
                self.assertEqual(im.getpixel((550,355))[:3],(36,55,68))
