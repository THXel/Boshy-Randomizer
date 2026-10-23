import hashlib
import json
import struct
import sys
import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import music_playback as playback


class Playback(unittest.TestCase):
    def setup_plan(self, base, path=None):
        folder = base / 'menu-runtime'
        cache = folder / 'music'
        cache.mkdir(parents=True)
        source = cache / 'abc.wav'
        with wave.open(str(source), 'wb') as w:
            w.setparams((2, 2, 44100, 0, 'NONE', 'not compressed'))
            w.writeframes(struct.pack('<hh', 100, -100) * 4410)
        name = 'plainsstageKirby'.encode().ljust(68, b'\0')
        target = (path or playback.PREFIX + source.name).encode().ljust(100, b'\0')
        raw = b'BRM1' + b'a' * 32 + struct.pack('<I', 1) + name + target
        (folder / 'music.bin').write_bytes(raw)
        return source, dict(run_id='a' * 32, options={'extras': {'music': True}}), raw

    def test_only_transport_paths_change_and_cache_is_reused(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            source, m, raw = self.setup_plan(base)
            self.assertTrue(playback.prepare(base, m))
            plan = base / 'menu-runtime/music.bin'
            first = plan.read_bytes()
            self.assertEqual(first[:108], raw[:108])
            self.assertNotEqual(first, raw)
            output = (
                base
                / 'menu-runtime/music'
                / first[108:].split(b'\0')[0].decode().rsplit('\\', 1)[-1]
            )
            self.assertEqual(playback.pcm_info(output), 4410)
            plan.write_bytes(raw)
            with patch(
                'music_playback.subprocess.run',
                side_effect=AssertionError('Cached audio must not be decoded again'),
            ):
                self.assertTrue(playback.prepare(base, m))
            self.assertEqual(plan.read_bytes(), first)

    def test_frozen_run_exclusion_preserves_unrelated_swaps(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            names = ['cheetah new', 'Do teh mario!', 'other']
            swaps = dict(zip(names, ['Do teh mario!', 'other', 'cheetah new']))
            manifest = {'run_id': 'a' * 32}
            raw = b'BRM1' + b'a' * 32 + struct.pack('<I', 3)
            for i, name in enumerate(names):
                raw += name.encode().ljust(68, b'\0') + (
                    playback.PREFIX + str(i) + '.ogg'
                ).encode().ljust(100, b'\0')
            (folder / 'music-map.json').write_text(
                json.dumps(dict(run_id='a' * 32, tracks=swaps))
            )
            result, record = playback.exclude_tracks(raw, folder, manifest)
            self.assertEqual(result[108:208], raw[276:376])
            self.assertEqual(result[208:], raw[208:])
            self.assertNotIn('Do teh mario!', record['tracks'].values())
            self.assertEqual(record['tracks']['other'], swaps['other'])
            self.assertEqual(result[:108], raw[:108])

    def test_exclusion_rejects_foreign_map(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            _, manifest, _ = self.setup_plan(base)
            (base / 'menu-runtime/music-map.json').write_text(
                json.dumps(
                    dict(run_id='b' * 32, tracks={'plainsstageKirby': 'Do teh mario!'})
                )
            )
            with self.assertRaises(ValueError):
                playback.prepare(base, manifest)
            self.assertEqual(
                (base / 'menu-runtime/music.bin').read_bytes(), b'BRM1' + bytes(36)
            )

    def test_telemetry_uses_effective_plan_for_frozen_runs(self):
        from types import SimpleNamespace
        from native_telemetry import MusicReader

        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            _, m, _ = self.setup_plan(base)
            (base / 'menu-runtime/music-map.json').write_text(
                json.dumps(
                    dict(run_id=m['run_id'], tracks={'plainsstageKirby': 'other'})
                )
            )
            legacy = SimpleNamespace(
                TRACKS=('wrong-index',),
                mapping=lambda seed: {'wrong-index': 'Do teh mario!'},
            )
            player = SimpleNamespace(
                bridge=object(),
                store=SimpleNamespace(base=base),
                m=dict(m, seed='seed'),
                rules=SimpleNamespace(module=lambda name: legacy),
            )
            reader = MusicReader(player)
            reader.reader = SimpleNamespace(
                read=lambda *args: (0x42524D31, 1, 0, 3, 0, 0)
            )
            self.assertEqual(
                reader.read(),
                dict(original='plainsstageKirby', track='other', changes=3),
            )

    def test_corrupt_cache_is_rebuilt(self):
        with tempfile.TemporaryDirectory() as d:
            source, _, _ = self.setup_plan(Path(d))
            out = playback.convert(source, source.parent)
            out.write_bytes(b'broken')
            self.assertEqual(playback.convert(source, source.parent), out)
            self.assertEqual(playback.pcm_info(out), 4410)

    def test_foreign_session_and_unsafe_paths_are_rejected_and_plan_cleared(self):
        for wrong in ('..\\..\\other.mp3', playback.PREFIX + '../../outside.wav'):
            with tempfile.TemporaryDirectory() as d:
                base = Path(d)
                source, m, _ = self.setup_plan(base, wrong)
                with self.assertRaises(ValueError):
                    playback.prepare(base, m)
                self.assertEqual(
                    (base / 'menu-runtime/music.bin').read_bytes(), b'BRM1' + bytes(36)
                )
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            _, m, _ = self.setup_plan(base)
            m['run_id'] = 'b' * 32
            with self.assertRaises(ValueError):
                playback.prepare(base, m)

    def test_decoder_failure_does_not_publish_partial_audio(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            source, m, _ = self.setup_plan(base)
            with patch(
                'music_playback.subprocess.run',
                side_effect=RuntimeError('decoder failed'),
            ):
                with self.assertRaises(RuntimeError):
                    playback.prepare(base, m)
            self.assertFalse(list(source.parent.glob('.pcm-*')))
            self.assertEqual(
                (base / 'menu-runtime/music.bin').read_bytes(), b'BRM1' + bytes(36)
            )

    def test_disabled_music_is_untouched(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            _, m, raw = self.setup_plan(base)
            m['options']['extras']['music'] = False
            self.assertFalse(playback.prepare(base, m))
            self.assertEqual((base / 'menu-runtime/music.bin').read_bytes(), raw)

    def test_truncated_pcm_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            source, _, _ = self.setup_plan(Path(d))
            source.write_bytes(source.read_bytes()[:-4])
            with self.assertRaises(ValueError):
                playback.pcm_info(source)


if __name__ == '__main__':
    unittest.main()
