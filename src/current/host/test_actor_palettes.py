import copy
import json
import struct
import unittest
from pathlib import Path
from recover_boshy_routes import payloads, original_sections, objects, frames
from visuals.actor_palettes import transform, ACTORS, colours, settings, GROUP
from transition.events import commands
from transition.router import params


class ActorPaletteTests(unittest.TestCase):
    def test_every_original_event_and_image_reference_is_preserved(self):
        affected = set()
        for payload, frame in payloads.items():
            original = original_sections(payload)
            changed, audit = transform(
                frame, original, objects, frames[frame - 1]["instances"]
            )
            self.assertEqual(changed[: len(original)], original)
            for row in changed[len(original) :]:
                for event in row:
                    actions = [c for c in commands(event) if not c[0]]
                    self.assertEqual(len(actions), 1)
                    _, kind, code, oi, raw = actions[0]
                    self.assertEqual((kind, code), (2, 66))
                    self.assertIn(oi, ACTORS)
                    self.assertEqual([p[0] for p in params(raw)], [22])
                    affected.add(oi)
            if frame in [14, 46, 60]:
                self.assertEqual(
                    changed, original, "Fire boss frames must remain byte-identical"
                )
        self.assertEqual(affected, set(ACTORS))
        self.assertTrue(
            {1088, 1089} <= affected, "Both shared-image skeleton types are covered"
        )

    def test_colour_choice_matches_existing_seed_identity(self):
        palettes = (
            "ef95ba",
            "8fdaf2",
            "e9c26c",
            "b0ed8b",
            "c7a0f0",
            "f0a36b",
            "83e6d3",
            "e0e1ec",
        )
        import hashlib

        for seed in ["A", "B", "test-2026"]:
            for oi, value in colours(seed).items():
                chosen = min(
                    palettes,
                    key=lambda v: hashlib.sha256(
                        (
                            "boshy-graphics-v2\0" + seed + "\0" + "8\0" + oi + "\0#" + v
                        ).encode()
                    ).digest(),
                )
                self.assertEqual(value, int.from_bytes(bytes.fromhex(chosen), "little"))
        self.assertNotEqual(colours("A"), colours("B"))

    def test_unexpected_actor_identity_is_rejected(self):
        changed = dict(objects)
        changed[1088] = {**objects[1088], "name": "Fire"}
        source = original_sections(next(p for p, f in payloads.items() if f == 15))
        with self.assertRaises(AssertionError):
            transform(15, source, changed, frames[14]["instances"])

    def test_settings_are_opt_in(self):
        self.assertEqual(settings("A", False)["Enabled"], 0)
        with self.assertRaises(ValueError):
            settings("A", 1)


if __name__ == "__main__":
    unittest.main()
