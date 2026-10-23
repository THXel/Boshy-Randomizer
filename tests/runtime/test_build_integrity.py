"""Rebuilt payloads must pass runtime integrity checks before packaging."""

import hashlib
import struct
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from build_runtime import bind_native_hashes
from host_platform import native_path
from mixed_rewards import CONTEXT_SIZE


class BuildIntegrity(unittest.TestCase):
    def test_rebuilt_extras_load_and_tampered_extras_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            for name in (
                'native_intro_guard.dll',
                'native_menu_polished.dll',
                'native_extras.dll',
            ):
                (base / name).write_bytes(
                    ('different compiler output ' + name).encode()
                )
            (base / 'intro_guard.py').write_text((ROOT / 'intro_guard.py').read_text())
            bind_native_hashes(base)
            guard = {}
            exec(compile((base / 'intro_guard.py').read_text(), 'guard', 'exec'), guard)
            self.assertEqual(
                guard['EXTRAS_CURRENT'],
                hashlib.sha256((base / 'native_extras.dll').read_bytes()).hexdigest(),
            )
            raw = bytearray(CONTEXT_SIZE + 2160)
            struct.pack_into('<II', raw, CONTEXT_SIZE, 0x424D4E31, 1)
            raw[CONTEXT_SIZE + 1356 : CONTEXT_SIZE + 1616] = (
                native_path(base / 'native_menu.dll').encode().ljust(260, b'\0')
            )
            out = guard['attach'](base, raw, context_offset=0, extras=True)
            self.assertEqual(
                out[CONTEXT_SIZE + 1356 : CONTEXT_SIZE + 1616].split(b'\0')[0],
                native_path(base / 'native_extras.dll').encode(),
            )
            (base / 'native_extras.dll').write_bytes(b'changed after build')
            with self.assertRaisesRegex(RuntimeError, 'Extras-Patch'):
                guard['attach'](base, raw, context_offset=0, extras=True)

    def test_binding_fails_closed_if_guard_layout_changes(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            for name in (
                'native_intro_guard.dll',
                'native_menu_polished.dll',
                'native_extras.dll',
            ):
                (base / name).write_bytes(b'build')
            p = base / 'intro_guard.py'
            old = (
                (ROOT / 'intro_guard.py')
                .read_text()
                .replace('EXTRAS_CURRENT', 'RENAMED_CURRENT')
            )
            p.write_text(old)
            with self.assertRaises(RuntimeError):
                bind_native_hashes(base)
            self.assertEqual(p.read_text(), old)

    def test_actual_payload_matches_runtime_guard(self):
        import intro_guard

        for name, expected in [
            ('native_extras.dll', intro_guard.EXTRAS_CURRENT),
            ('native_intro_guard.dll', intro_guard.GUARD_HASH),
        ]:
            self.assertEqual(
                hashlib.sha256((ROOT / name).read_bytes()).hexdigest(), expected, name
            )


if __name__ == '__main__':
    unittest.main()
