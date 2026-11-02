import unittest
from gameplay.options_sync import transform, CONTROL
from transition.events import commands
import recover_boshy_routes as source

class OptionsSyncTests(unittest.TestCase):
    def test_original_controls_have_change_guards_in_every_or_branch(self):
        count = 0
        for payload, frame in source.payloads.items():
            before = source.original_sections(payload)
            after, audit = transform(frame, before)
            original = [c[-1] for rows in before for row in rows for c in commands(row)
                        if not c[0] and c[1:3] == (33,95) and b'Options\0' in c[-1] and CONTROL.search(c[-1])]
            actual=[]
            for rows in after:
                for row in rows:
                    cs=commands(row)
                    acts=[c[-1] for c in cs if not c[0]]
                    if len(acts)!=1 or acts[0] not in original:continue
                    actual.extend(acts);branch=[]
                    for c in cs:
                        if not c[0]:continue
                        if c[1:3] in ((-1,-24),(-1,-25)):
                            self.assertTrue(any(CONTROL.search(b) for b in branch));branch=[]
                        else:branch.append(c[-1])
                    self.assertTrue(any(CONTROL.search(b) for b in branch))
            self.assertCountEqual(actual,original)
            count+=len(original)
        self.assertGreater(count,160)

if __name__=='__main__':unittest.main()
