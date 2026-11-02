"""Undertale category boundaries, death/audio timeline and import failure safety."""
import json
import tempfile
import unittest
import wave
from pathlib import Path
from music.import_undertale import build, local_file, BREAK_TICK, SHATTER_TICK, MUSIC_TICK
from music.packs import PACKS, PACK_NAMES, ANIMATIONS
from music.soundtrack import mapping, pack_rows, cue_kind
from app_paths import SOUNDPACKS
from visuals import embedded_blood, death_screen

class UndertaleTests(unittest.TestCase):
    def test_existing_ids_remain_stable_and_fourth_pack_is_consistent(self):
        self.assertEqual(PACKS, ('original','kamilia3','wannafest22','undertale'))
        self.assertEqual(PACK_NAMES[3], 'Undertale')
        self.assertEqual(ANIMATIONS, {'kamilia3':16,'wannafest22':17,'undertale':18})

    def test_music_never_mixes_level_boss_title_and_gameover_roles(self):
        rows=pack_rows(SOUNDPACKS/'undertale','undertale')
        kinds={r['file']:r['kind'] for r in rows}
        self.assertEqual(len(rows),21)
        self.assertNotIn('mus_gameover.ogg',kinds)
        self.assertNotIn('mus_menu0.ogg',kinds)
        for seed in range(200):
            selection=mapping(str(seed),'undertale',rows)
            self.assertTrue(all(cue_kind(cue)==kinds[name] for cue,name in selection.items()))
            self.assertEqual(selection,mapping(str(seed),'undertale',list(reversed(rows))))

    def test_death_has_one_screen_soul_and_no_player_particle_copies(self):
        b=embedded_blood.assets()['undertale']
        self.assertEqual(len(b['images']),1)
        self.assertIsNone(b['images'][0].getchannel('A').getbbox())
        d=death_screen.assets()['undertale']
        self.assertEqual(d['animation'],18)
        self.assertEqual(d['loop'],len(d['frames'])-1)
        from visuals.death_soul import assets as soul_assets
        soul=soul_assets()
        self.assertEqual(soul['origins'][0], (8, 8))
        self.assertIsNone(soul['images'][-1].getchannel('A').getbbox())
        first=soul['images'][0]
        self.assertEqual(first.size, (16, 16))
        self.assertEqual(first.getpixel((8,8))[:3],(255,0,0))
        self.assertEqual(d['images'][0].getpixel((320,240)),(0,0,0,255))
        self.assertEqual(len(d['frames']),268)

    def test_soul_position_is_captured_before_the_original_player_destruction(self):
        from visuals import death_screen as death
        from visuals.death_soul import OBJECT, begin
        from transition.events import commands
        import recover_boshy_classic as source
        for number in (3, 23, 45, 53):
            payload=next(p for p,n in source.routes.payloads.items() if n==number)
            before=source.sections(payload)
            after,audit=death.transform(number,before,source.routes.objects,source.routes.frames[number-1]['instances'])
            meta=audit[0];row=after[meta['section']][meta['row']+3]
            actions=[c for c in commands(row) if not c[0]]
            self.assertEqual([c[-1] for c in actions[:4]],begin(meta['player']))
            self.assertTrue(any(c[1:4]==(2,24,meta['player']) for c in actions[4:]))
            self.assertEqual([c[3] for c in actions[:4]],[OBJECT]*4)

    def test_death_audio_silence_and_effect_timing(self):
        with wave.open(str(SOUNDPACKS/'undertale/death-visuals/death-sequence.wav'),'rb') as stream:
            self.assertEqual((stream.getframerate(),stream.getnchannels()),(22050,2))
            self.assertAlmostEqual(stream.getnframes()/22050, MUSIC_TICK/50)
            silent=stream.readframes(round(BREAK_TICK*22050/50))
            self.assertFalse(any(silent))
            self.assertTrue(any(stream.readframes(2205)))
        self.assertEqual((BREAK_TICK,SHATTER_TICK,MUSIC_TICK),(33,100,183))

    def test_import_rejects_missing_assets_without_partial_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);dest=root/'pack'
            with self.assertRaises(ValueError):build(root,root,dest)
            self.assertFalse(dest.exists())
            self.assertEqual(list(root.iterdir()),[])

    def test_import_does_not_follow_links_or_replace_packs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);dest=root/'pack';dest.mkdir()
            with self.assertRaises(FileExistsError):build(root,root,dest)
            (root/'link').symlink_to(dest,target_is_directory=True)
            with self.assertRaises(ValueError):local_file(root,'link')
