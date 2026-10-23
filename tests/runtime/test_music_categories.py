"""Regression checks for category-safe optional soundtrack replacement."""

import unittest
from music_categories import audited_tracks, cue_kind, track_kind, BOSS_CUES
from music_randomizer import SOURCE_TRACKS
from soundpacks import mapping


class MusicCategories(unittest.TestCase):
    def tracks(self, pack):
        return [
            dict(file=file, shuffle=True, roles=[], **row)
            for file, row in audited_tracks()[pack].items()
        ]

    def test_every_existing_pack_stays_in_its_category_for_many_seeds(self):
        for pack in audited_tracks():
            tracks = self.tracks(pack)
            kinds = {row['file']: track_kind(pack, row) for row in tracks}
            for seed in range(200):
                swaps = mapping(seed, tracks, pack)
                self.assertEqual(set(swaps), set(SOURCE_TRACKS))
                self.assertTrue(
                    all(kinds[file] == cue_kind(cue) for cue, file in swaps.items())
                )
                self.assertEqual(swaps, mapping(seed, list(reversed(tracks)), pack))

    def test_boss_addition_does_not_change_level_choices(self):
        tracks = self.tracks('kamilia3')
        before = mapping('independent', tracks, 'kamilia3')
        tracks.append(dict(file='custom.ogg', shuffle=True, music_kind='boss'))
        after = mapping('independent', tracks, 'kamilia3')
        self.assertEqual(
            {c: f for c, f in before.items() if cue_kind(c) == 'level'},
            {c: f for c, f in after.items() if cue_kind(c) == 'level'},
        )

    def test_unknown_or_replaced_files_are_not_guessed(self):
        self.assertEqual(
            track_kind('kamilia3', dict(file='001.ogg', sha256='bad')), 'excluded'
        )
        self.assertEqual(
            track_kind('wannafest22', dict(file='music/newBoss.ogg')), 'excluded'
        )
        with self.assertRaisesRegex(ValueError, 'classified boss'):
            mapping('seed', [dict(file='only.ogg', shuffle=True, music_kind='level')])

    def test_special_scenes_and_role_cues_cannot_enter_shuffle(self):
        self.assertEqual(audited_tracks()['kamilia3']['052.ogg']['kind'], 'excluded')
        self.assertEqual(
            audited_tracks()['wannafest22']['music/musStage6Clear.ogg']['kind'],
            'excluded',
        )
        tracks = self.tracks('kamilia3')
        tracks.append(
            dict(file='intro.ogg', shuffle=True, roles=['opening'], music_kind='boss')
        )
        self.assertNotIn('intro.ogg', mapping('seed', tracks, 'kamilia3').values())

    def test_boshy_boss_cues_are_complete_and_known(self):
        self.assertTrue(BOSS_CUES < set(SOURCE_TRACKS))
        for cue in (
            'Kirby Bos',
            'mountain stage kirby',
            'Sonic_the_Hedgehog GREEN HILL',
            'Ace Combat  Megalith',
            'mega_man_3_theme',
        ):
            self.assertEqual(cue_kind(cue), 'boss')
        for cue in (
            'greengreens',
            'Castlevania',
            'vvv positive force',
            'Mega Metal Man4',
        ):
            self.assertEqual(cue_kind(cue), 'level')
