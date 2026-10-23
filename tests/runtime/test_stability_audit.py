import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from debug_runtime import DebugRuntime
from debug_data import Recorder
from transition_guard import protect
from menu_model import Menu
from trigger_checks import run


class StabilityAudit(unittest.TestCase):
    def test_all_spots_and_hack_gate_invariants(self):
        report = run(ROOT)
        self.assertEqual(report['spots'], 45)
        self.assertEqual(report['hack_combinations'], 16)

    def test_changed_trigger_rules_invalidate_saved_test_results(self):
        import trigger_audit

        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            for name in trigger_audit.FILES:
                path = base / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b'"original"')
            before = trigger_audit.fingerprint(base)
            for name in trigger_audit.FILES:
                path = base / name
                path.write_bytes(b'"changed"')
                self.assertNotEqual(before, trigger_audit.fingerprint(base), name)
                path.write_bytes(b'"original"')
            (base / 'trigger-test-results.json').write_text(
                json.dumps(
                    {
                        'fingerprint': 'stale',
                        'spots': {'example': {'natural': 'Spieltest bestanden'}},
                    }
                )
            )
            with patch('trigger_audit.points', return_value={'example': {'frame': 3}}):
                self.assertEqual(trigger_audit.rows(base)[0]['natural'], 'Offen')

    def test_menu_launch_accepts_packaged_and_legacy_guard_but_rejects_changes(self):
        import hashlib
        import struct
        import shutil
        from intro_guard import attach, GUARD_HASHES
        from mixed_rewards import CONTEXT_SIZE

        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            shutil.copy2(
                ROOT / 'native_menu_polished.dll', base / 'native_menu_polished.dll'
            )
            (base / 'slot_reward_symbols.json').write_text(
                json.dumps({'context_offset': 0})
            )
            blob = bytearray(CONTEXT_SIZE + 2160)
            struct.pack_into('<II', blob, CONTEXT_SIZE, 0x424D4E31, 1)
            name = ('Z:' + str(base / 'native_menu.dll').replace('/', '\\')).encode()
            blob[CONTEXT_SIZE + 1356 : CONTEXT_SIZE + 1616] = name.ljust(260, b'\0')
            packaged = (ROOT / 'native_intro_guard.dll').read_bytes()
            legacy = bytearray(packaged)
            struct.pack_into('<I', legacy, 136, 0x6ACE2740)
            struct.pack_into('<I', legacy, 4100, 0x6ACE2740)
            struct.pack_into('<I', legacy, 216, 0xAEC3)
            for raw in (packaged, legacy):
                self.assertIn(hashlib.sha256(raw).hexdigest(), GUARD_HASHES)
                (base / 'native_intro_guard.dll').write_bytes(raw)
                self.assertEqual(len(attach(base, blob)), len(blob))
            (base / 'native_intro_guard.dll').write_bytes(b'corrupt')
            with self.assertRaises(RuntimeError):
                attach(base, blob)

    def test_error_report_keeps_pre_error_run_and_does_not_include_saves(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            (base / 'IWBTB').mkdir()
            (base / 'IWBTB/SaveFile1.ini').write_text('private')
            runtime = DebugRuntime(SimpleNamespace(base=base), start_window=False)
            runtime.state = {
                'sequence': 1,
                'phase': 'running',
                'run_id': 'original',
                'progress': {
                    'spot': 'save10.ini',
                    'transition_trace': [{'event': 'completion-observed'}],
                },
                'options': {'extras': {'one_hp': True}},
            }
            runtime.recorder.observe(runtime.state)
            runtime.error(KeyError('Ini++'))
            path = Path(
                json.loads((base / 'debug-reports/latest-error.json').read_text())[
                    'path'
                ]
            )
            self.assertTrue(path.exists())
            with zipfile.ZipFile(path) as z:
                self.assertEqual(
                    set(z.namelist()),
                    {
                        'bericht.json',
                        'LESEN.txt',
                        'trigger.txt',
                        'trigger-evidence.json',
                        'zeitverlauf.jsonl',
                        'transition-timings.json',
                        'graphics.json',
                    },
                )
                report = json.loads(z.read('bericht.json'))
                self.assertEqual(report['last_state']['run_id'], 'original')
                self.assertEqual(report['last_state']['exception_type'], 'KeyError')
                self.assertIn('Ini++', report['description'])
                self.assertNotIn('private', z.read('zeitverlauf.jsonl').decode())

    def test_report_failure_does_not_replace_original_failure(self):
        with tempfile.TemporaryDirectory() as d:
            runtime = DebugRuntime(SimpleNamespace(base=Path(d)), start_window=False)
            runtime.recorder.finish = Mock(side_effect=OSError('disk full'))
            runtime.error(RuntimeError('original'))
            self.assertEqual(runtime.events[0]['message'], 'original')
            self.assertIsNone(runtime.last_error_report)

    def test_completed_save_opens_result_without_resume(self):
        for completed in (True, False):
            m = Menu.__new__(Menu)
            m.page = 'slots'
            m.focus = 0
            m.slot = 1
            m.action = None
            m.saves = {1: dict(exists=True, completed=completed)}
            m.open_saved_result = Mock(return_value=True)
            m.key(13)
            if completed:
                m.open_saved_result.assert_called_once()
                self.assertIsNone(m.action)
            else:
                m.open_saved_result.assert_not_called()
                self.assertEqual(m.action, ('resume', 1, None))

    def test_guard_releases_on_exception(self):
        import struct

        b = SimpleNamespace(
            read=Mock(
                side_effect=[struct.pack('<II', 0x42544731, 0), struct.pack('<I', 1)]
            ),
            cmd=Mock(),
        )
        with self.assertRaises(ValueError):
            with protect(b, 100):
                raise ValueError('failed move')
        self.assertEqual(
            [c.args[0] for c in b.cmd.call_args_list], ['menu 64 60 3', 'menu 64 60 1']
        )

    def test_guard_missing_protocol_never_freezes(self):
        b = SimpleNamespace(read=Mock(return_value=bytes(8)), cmd=Mock())
        with self.assertRaises(RuntimeError):
            with protect(b, 100):
                self.fail('unprotected action')
        b.cmd.assert_not_called()

    def test_guard_timeout_unpauses_and_does_not_dispatch(self):
        import struct

        b = SimpleNamespace(
            read=Mock(return_value=struct.pack('<II', 0x42544731, 0)), cmd=Mock()
        )
        with (
            patch('transition_guard.time.monotonic', side_effect=[0, 1]),
            self.assertRaises(RuntimeError),
        ):
            with protect(b, 100):
                self.fail('unconfirmed guard')
        self.assertEqual(b.cmd.call_args.args, ('menu 64 60 1',))


if __name__ == '__main__':
    unittest.main()
