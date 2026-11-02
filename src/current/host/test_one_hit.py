"""Original damage-event coverage and independent evaluation of native math."""
import struct,unittest
import recover_boshy_routes as source
from transition.events import commands
from gameplay.one_hit import transform,damage_tokens,HEALTH

# Small independent evaluator for the subset of native expressions emitted here.
def evaluate(data,hp,enabled,floor):
    pos=0
    def expr():
        nonlocal pos
        kind,code,size=struct.unpack_from('<hhH',data,pos);start=pos;pos+=size
        if (kind,code)==(-1,0):return struct.unpack_from('<i',data,start+6)[0]
        if (kind,code)==(-1,3):return data[start+6:start+size].split(b'\0')[0].decode()
        if (kind,code)==(2,16):return hp
        if (kind,code)==(-1,-1):
            a=expr();k,op,n=struct.unpack_from('<hhH',data,pos);pos+=n
            assert k==0 and op in (2,4,6)
            b=expr();close();return {2:lambda:a+b,4:lambda:a-b,6:lambda:a*b}[op]()
        if (kind,code) in ((-1,40),(-1,41),(33,88)):
            args=[expr()]
            while struct.unpack_from('<hh',data,pos)==(-1,-3):pos+=6;args.append(expr())
            close()
            if kind==33:return {'OneHit':enabled,'OneHitSonicFloor':floor}[args[1]]
            return min(args) if code==40 else max(args)
        raise AssertionError((kind,code))
    def close():
        nonlocal pos
        assert struct.unpack_from('<hhH',data,pos)==(-1,-2,6)
        pos+=6
    result=expr();assert pos==len(data);return result

class OneHitTests(unittest.TestCase):
    def test_original_damage_and_phase_floor_math(self):
        for frame in (4,14,46,60):
            for damage in (1,2,4,5,15):
                data=damage_tokens(frame,1057,1,damage,312)
                for floor in (35,90,180):
                    for hp in (0,1,34,35,36,45,89,90,91,100,179,180,181,200):
                        self.assertEqual(evaluate(data,hp,0,floor),damage)
                        wanted=hp-floor if frame in (14,60) and hp>floor else hp
                        self.assertEqual(evaluate(data,hp,1,floor),wanted)

    def test_only_explicit_boss_damage_changes(self):
        count=0
        for payload,frame in source.payloads.items():
            before=source.original_sections(payload)
            after,audit=transform(frame,before,source.objects,source.frames[frame-1]['instances'])
            edits={(a['section'],a['row'],a['command']) for a in audit}
            count+=len(audit)
            for si,rows in enumerate(before):
                self.assertEqual(len(rows),len(after[si]))
                for ri,row in enumerate(rows):
                    a,b=commands(row),commands(after[si][ri]);self.assertEqual(len(a),len(b))
                    for ci,(old,new) in enumerate(zip(a,b)):
                        if (si,ri,ci) in edits:
                            self.assertEqual(old[-1][2:14],new[-1][2:14])
                            self.assertEqual(old[1:3],(2,33))
                        else:self.assertEqual(old,new)
        self.assertEqual(count,67)
        self.assertNotIn(39,HEALTH) # Gradius enemies are not boss phases.

    def test_cheetah_acceleration_is_not_health(self):
        payload=next(p for p,f in source.payloads.items() if f==54)
        before=source.original_sections(payload)
        after,audit=transform(54,before,source.objects,source.frames[53]['instances'])
        # Phase 440..468 subtracts one from horizontal speed on each tick.
        # This is movement, with no projectile hit condition and no HP value.
        self.assertEqual(after[91][19],before[91][19])
        self.assertNotIn(2918,HEALTH[54])
        self.assertEqual({(a['section'],a['row'],a['index']) for a in audit},
                         {(91,141,24),(91,142,24)})
        self.assertTrue(all(a['name']=='Cheetah Second Phase' for a in audit))

class OneHitSettingsTests(unittest.TestCase):
    def test_phase_floor_follows_difficulty_and_legacy_cannot_enable(self):
        from menu_host.draft import Draft
        from gameplay.settings import settings
        d=Draft()
        for difficulty,floor in enumerate((35,90,90,180)):
            d.update(difficulty=difficulty,one_hp=True)
            rules=settings(d.options['extras'],difficulty=difficulty)
            self.assertEqual(rules['OneHit'],1)
            self.assertEqual(rules['OneHitSonicFloor'],floor)
            for schema in (1,2):
                with self.assertRaises(ValueError):settings(d.options['extras'],schema,difficulty)
        for invalid in (True,-1,4):
            with self.assertRaises(ValueError):settings(d.options['extras'],difficulty=invalid)

    def test_seed_and_save_keep_one_hit_selection(self):
        from menu_host.draft import Draft
        from menu_host.store import Store
        from test_menu_host import fake_export
        from pathlib import Path
        import tempfile
        d=Draft();old=d.seed;d.update(one_hp=True,difficulty=3)
        self.assertNotEqual(old,d.seed)
        e=Draft();e.import_seed(d.shared());self.assertTrue(e.options['extras']['one_hp'])
        with tempfile.TemporaryDirectory() as tmp:
            s=Store(Path(tmp)/'profile',Path(tmp)/'runs',fake_export)
            with s.lock():
                s.create(1,e);_,p,_=s.resume(1)
                self.assertEqual(p['gameplay_settings']['OneHitSonicFloor'],180)
                self.assertEqual(p['gameplay_settings']['OneHit'],1)

if __name__=='__main__':unittest.main()
