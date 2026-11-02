"""Regression boundaries of the combined Fusion project and native handoff."""

import copy
import struct
import unittest
import recover_boshy_targets as gameplay
from native_menu import events, session
from transition.events import commands


class UnifiedTests(unittest.TestCase):
    def title(self):
        payload = next(p for p, f in gameplay.routes.payloads.items() if f == 2)
        return gameplay.sections(payload)

    def test_combination_keeps_all_gameplay_frames_byte_identical(self):
        import recover_boshy_unified as unified

        checked = 0
        for payload, frame in gameplay.routes.payloads.items():
            if frame != 2:
                self.assertEqual(
                    unified.sections(payload), gameplay.sections(payload), frame
                )
                checked += 1
        self.assertEqual(checked, 60)

    def test_native_handoff_uses_only_valid_save_frames_and_no_process_launch(self):
        menu, _ = events.transform(self.title())
        changed, audit = session.transform(menu)
        self.assertEqual(audit["playable_frames"], session.FRAMES)
        self.assertFalse({1, 2, 18, 19, 20} & set(session.FRAMES))
        rows = changed[-1]
        jumps = []
        for row in rows:
            cs = commands(row)
            if any(not c and k == -3 and code == 2 for c, k, code, oi, raw in cs):
                jumps.append(row)
                gates = b"".join(raw for c, k, code, oi, raw in cs if c)
                for key in (b"SaveVersion\0", b"Positions\0", b"Difficulty\0"):
                    self.assertIn(key, gates)
            self.assertFalse(
                any(not c and k == -1 and code in (0, 1) for c, k, code, oi, raw in cs)
            )
        self.assertEqual(len(jumps), len(session.FRAMES) + 2)
        self.assertIn(b"Completed\0", jumps[-1])
        self.assertIn(b"FusionRouteV4\0", jumps[-1])
        for si, section in enumerate(menu):
            expected = changed[si][:2] + changed[si][3:] if si == 0 else changed[si]
            self.assertEqual(section, expected)
        request = b"".join(raw for c, k, code, oi, raw in commands(rows[0]) if c)
        for key in (b"Begin\0", b"Accepted\0", b"SessionSchema\0", b"Busy\0"):
            self.assertIn(key, request)

    def test_session_object_has_its_own_file_and_no_save_side_effect(self):
        objects = copy.deepcopy(gameplay.routes.objects)
        frame = copy.deepcopy(gameplay.routes.frames[1])
        original = copy.deepcopy(objects[47])
        session.clone_object(objects, frame)
        self.assertEqual(objects[47], original)
        self.assertIn(
            b"native-session.ini\0", objects[session.SESSION]["private"]["data"]
        )
        self.assertEqual(frame["instances"][-1]["objectInfo"], session.SESSION)

    def test_session_condition_ids_do_not_collide_with_existing_menu(self):
        menu, _ = events.transform(self.title())
        result, _ = session.transform(menu)

        def ids(sections):
            return {
                struct.unpack_from("<H", raw, 14)[0]
                for sec in sections
                for row in sec
                for c, k, code, oi, raw in commands(row)
                if c
            }

        before = ids(menu)
        added = ids([result[-1], [result[0][2]]])
        self.assertFalse(before & added)

    def test_prepared_menu_disables_slot_replacement_and_delete_shortcut(self):
        import tempfile
        from pathlib import Path
        from unittest.mock import Mock
        from menu_host.store import Store
        from native_menu.unified import PreparedModel

        with tempfile.TemporaryDirectory() as d:
            model = PreparedModel(Store(Path(d) / "profile", runs=Path(d) / "runs"))
            model.saved = Mock(return_value=True)
            for key in ("new", "delete", "slot:1", "slot:2", "slot:3"):
                self.assertFalse(next(r for r in model.rows() if r.key == key).enabled)
                model.select(key)
                self.assertIsNone(model.action)
            model.key(46)
            self.assertIsNone(model.action)

    def test_repainting_or_input_does_not_reissue_a_native_launch_request(self):
        import tempfile
        from pathlib import Path
        from unittest.mock import Mock
        from menu_host.store import Store
        from native_menu.model import Model
        from native_menu.transport import Mailbox, read, write

        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            model = Model(Store(folder / "profile", runs=folder / "runs"))
            mailbox = Mailbox(folder, Mock(art_generation=1), model, session_begin=3)
            write(folder / "native-input.ini", dict(Sequence=1, Key=40))
            self.assertTrue(mailbox.poll())
            mailbox.publish()
            view = read(folder / "native-view.ini")
            self.assertEqual(view["begin"], 3)
            self.assertEqual(view["sessionschema"], 1)
            self.assertEqual(view["ack"], 1)

    def test_compiled_combination_preserves_banks_and_exports_randomized_scenery(self):
        import tempfile
        from pathlib import Path
        from functools import partial
        from export_native_run import export
        from build_profiles import PREFIX
        from menu_host.store import Store
        from menu_host.draft import Draft
        from menu_host.runtime import verify_engine
        from visuals.scenery_pack import App, UNIFIED_BASE_SHA, GAMEPLAY_BASE_SHA

        combined = PREFIX / "drive_c/BoshyTransitions/Boshy-unified-v1.exe"
        verify_engine(combined, UNIFIED_BASE_SHA)
        # This historical v1 combination was built from targets-v2, before
        # the later intro wordmark update in the current gameplay base.
        reference = PREFIX / "drive_c/BoshyTransitions/Boshy-native-targets-v2.exe"
        verify_engine(reference, GAMEPLAY_BASE_SHA)
        old, new = App(reference), App(combined)
        for kind in (0x6666, 0x5555, 0x6668, 0x5557):
            self.assertEqual(old.payload(kind), new.payload(kind))
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            store = Store(
                folder / "profile",
                runs=folder / "runs",
                exporter=partial(export, unified=True),
            )
            draft = Draft()
            draft.update(
                sprite_scenery=True,
                sprite_backgrounds=True,
                sprite_decor=True,
                sprite_tiles=True,
            )
            with store.lock():
                store.create(1, draft)
                run, plan, config = store.resume(1)
                self.assertEqual(plan["unified_schema"], 1)
                self.assertEqual(plan["unified_base_sha256"], UNIFIED_BASE_SHA)
                self.assertEqual(
                    config.get("FusionRouteV4", "Binding"), plan["binding"]
                )
                import json

                self.assertTrue(
                    json.loads((run / "scenery-audit.json").read_text())["changed"]
                )


if __name__ == "__main__":
    unittest.main()
