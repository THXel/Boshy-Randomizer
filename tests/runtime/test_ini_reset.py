import struct
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import lab
from native_player import transient_read_error


class Bridge:
    def __init__(self):
        self._ini_cache = {'old': True}
        self.snap = dict(scene=26, run=0x20000, object_list=0x30000, frame_count=100)
        self.data = {}

    def snapshot(self):
        return dict(self.snap)

    def read(self, address, size):
        return self.data[address][:size]


class IniReset(unittest.TestCase):
    def test_same_scene_reset_discards_entire_observation_and_cache(self):
        b = Bridge()

        @lab._ini_observation
        def observation(bridge):
            bridge.snap['frame_count'] = 1
            return {'sessionid': 'stale'}

        with self.assertRaises(lab.IniReadInProgress) as e:
            observation(b)
        self.assertTrue(transient_read_error(e.exception))
        self.assertIsNone(b._ini_cache)

    def test_changed_generation_discards_read(self):
        for field in ('run', 'scene', 'object_list'):
            b = Bridge()

            @lab._ini_observation
            def observation(bridge):
                bridge.snap[field] += 1
                return {}

            with self.subTest(field=field), self.assertRaises(lab.IniReadInProgress):
                observation(b)

    def test_absent_optional_group_keeps_validated_pointer_cache(self):
        b = Bridge()
        cache = b._ini_cache

        @lab._ini_observation
        def observation(bridge):
            raise KeyError('achievements')

        with self.assertRaises(KeyError):
            observation(b)
        self.assertIs(b._ini_cache, cache)

    def test_absent_group_during_reset_still_invalidates_cache(self):
        for field in ('run', 'scene', 'object_list', 'frame_count'):
            b = Bridge()

            @lab._ini_observation
            def observation(bridge):
                bridge.snap[field] += -99 if field == 'frame_count' else 1
                raise KeyError('achievements')

            with self.subTest(field=field), self.assertRaises(lab.IniReadInProgress):
                observation(b)
            self.assertIsNone(b._ini_cache)

    def test_torn_string_is_retryable_without_reading_invalid_address(self):
        b = Bridge()
        raw = bytearray(64)
        struct.pack_into('<III', raw, 16, 0x12345678, 4294967295, 16)
        with self.assertRaises(lab.IniReadInProgress) as e:
            lab._ini_string(b, raw, 16, 8192)
        self.assertTrue(transient_read_error(e.exception))

    def test_valid_strings_and_empty_strings(self):
        b = Bridge()
        b.data[0x40000] = b'value'
        raw = bytearray(64)
        struct.pack_into('<III', raw, 16, 0x40000, 5, 15)
        self.assertEqual(lab._ini_string(b, raw, 16, 8192), 'value')
        self.assertEqual(lab._ini_string(b, bytes(64), 16, 8192), '')

    def test_retry_reacquires_state_and_unrelated_assertions_are_not_hidden(self):
        b = Bridge()

        @lab._ini_observation
        def observation(bridge):
            return {'value': 'valid'}

        self.assertEqual(observation(b), {'value': 'valid'})
        self.assertFalse(transient_read_error(AssertionError('programming error')))

    def test_strict_object_scan_does_not_turn_failed_reads_into_victory(self):
        b = Bridge()
        b.snap['objects'] = 1
        b.data[0x30000] = struct.pack('<II', 0x40000, 0)

        def read(address, size):
            if address == 0x40000:
                raise RuntimeError({'error': 'read failed'})
            return b.data[address][:size]

        b.read = read
        with self.assertRaises(RuntimeError):
            lab.objects(b, strict=True)

    def test_actual_item_tree_with_torn_value_rejects_all_rows(self):
        b = Bridge()
        head = 0x40000
        root = 0x50000
        group = bytearray(64)
        struct.pack_into('<I', group, 32, head)
        b.data[head + 4] = struct.pack('<I', root)
        node = bytearray(64)
        struct.pack_into('<III', node, 0, head, head, head)
        struct.pack_into('<III', node, 16, 0x60000, 3, 15)
        struct.pack_into('<III', node, 48, 0x70000, 999999, 15)
        b.data[root] = bytes(node)
        b.data[0x60000] = b'key'
        with (
            patch('lab._ini_group', return_value=bytes(group)),
            self.assertRaises(lab.IniReadInProgress),
        ):
            lab.ini_items(b, 'stats')
        self.assertIsNone(b._ini_cache)


class CheckpointSaveReads(unittest.TestCase):
    def test_same_scene_in_place_value_change_rejects_whole_observation(self):
        b = Bridge()
        rows = iter(
            [
                {'frame': '22', 'xpos': '620', 'ypos': '1300'},
                {'frame': '22', 'xpos': '605', 'ypos': '1251'},
            ]
        )

        @lab._ini_observation
        def observation(bridge):
            return next(rows)

        with self.assertRaises(lab.IniReadInProgress):
            observation(b)
        self.assertIsNone(b._ini_cache)

    def test_invalid_frame_from_actual_failure_is_retryable_not_zero(self):
        with self.assertRaises(lab.IniReadInProgress) as caught:
            lab.ini_integer_fields(
                {'frame': 'po', 'xpos': '605', 'ypos': '1251'},
                ('frame', 'xpos', 'ypos'),
                required=True,
            )
        self.assertTrue(transient_read_error(caught.exception))
        self.assertEqual(
            lab.ini_integer_fields(
                {'frame': '22', 'xpos': '605', 'ypos': '1251'},
                ('frame', 'xpos', 'ypos'),
                required=True,
            ),
            {'frame': 22, 'xpos': 605, 'ypos': 1251},
        )

    def test_missing_numeric_checkpoint_is_retried_instead_of_defaulted(self):
        with self.assertRaises(lab.IniReadInProgress):
            lab.ini_integer_fields(
                {'xpos': '605', 'ypos': '1251'},
                ('frame', 'xpos', 'ypos'),
                required=True,
            )

    def test_partial_counters_and_invalid_integer_shapes_are_rejected(self):
        for value in ['po', '', '--1', '1.2', '\x001', None, '9' * 8191]:
            with (
                self.subTest(value=str(value)[:20]),
                self.assertRaises(lab.IniReadInProgress),
            ):
                lab.ini_integer_fields({'deaths': value}, ('deaths',))
        self.assertEqual(
            lab.ini_integer_fields({'xpos': '-10', 'ypos': '+20'}, ('xpos', 'ypos')),
            {'xpos': -10, 'ypos': 20},
        )

    def test_stable_checkpoint_reads_return_complete_original_data(self):
        b = Bridge()
        data = {'frame': '22', 'xpos': '605', 'ypos': '1251'}

        @lab._ini_observation
        def observation(bridge):
            return dict(data)

        self.assertEqual(observation(b), data)

    def test_valid_header_with_non_numeric_achievement_is_rejected(self):
        b = Bridge()
        head = 0x40000
        root = 0x50000
        group = bytearray(64)
        struct.pack_into('<I', group, 32, head)
        b.data[head + 4] = struct.pack('<I', root)
        node = bytearray(64)
        struct.pack_into('<III', node, 0, head, head, head)
        struct.pack_into('<III', node, 16, 0x60000, 5, 15)
        struct.pack_into('<III', node, 48, 0x70000, 2, 15)
        b.data[root] = bytes(node)
        b.data[0x60000] = b'sonic'
        b.data[0x70000] = b'po'
        with (
            patch('lab._ini_group', return_value=bytes(group)),
            self.assertRaises(lab.IniReadInProgress),
        ):
            lab.ini_items(b, 'achievements')
        self.assertIsNone(b._ini_cache)


if __name__ == '__main__':
    unittest.main()
