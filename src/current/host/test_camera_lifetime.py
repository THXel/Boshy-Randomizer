"""Camera helper lifetime only: preserve all gameplay data and asset banks."""

import struct
import unittest
from gameplay import camera_lifetime
from native_menu import builds
from visuals.scenery_pack import App
from visuals.fusion25 import property_bank
import recover_boshy_dynamic as source


class CameraLifetimeTests(unittest.TestCase):
    def test_original_viewports_only_gain_never_destroy_far(self):
        original = source.routes.objects
        after = camera_lifetime.protect(original)
        changed = []
        for oi, obj in original.items():
            new = after[oi]
            if obj.get("type") == 34 and obj.get("name") == "Viewport 2":
                changed.append(oi)
                before = obj["properties"]
                patched = new["properties"]
                self.assertEqual(patched[:16], before[:16])
                self.assertEqual(patched[20:], before[20:])
                self.assertEqual(
                    struct.unpack_from("<I", patched, 16)[0],
                    struct.unpack_from("<I", before, 16)[0] | 0x2000,
                )
                self.assertEqual(
                    {k: v for k, v in new.items() if k != "properties"},
                    {k: v for k, v in obj.items() if k != "properties"},
                )
            else:
                self.assertIs(new, obj)
        self.assertEqual(len(changed), 16)
        self.assertEqual(camera_lifetime.protect(after), after)
        self.assertEqual(
            camera_lifetime.protect(list(original.values())), list(after.values())
        )

    def test_candidate_changes_only_four_compiled_viewport_flags(self):
        from export_route_probe import ROOT

        base = builds.PREFIX / "drive_c/BoshyTransitions/Boshy-dynamic-v15.exe"
        candidate = (
            ROOT
            / "outputs/Fusion-SonicFollowup-20261025/Boshy-dynamic-v16-candidate.exe"
        )
        old, new = App(base), App(candidate)
        self.assertEqual(
            old.data[: old.chunks[0].offset], new.data[: new.chunks[0].offset]
        )
        self.assertEqual(len(old.chunks), len(new.chunks))
        for a, b in zip(old.chunks, new.chunks):
            self.assertEqual(a.id, b.id)
            if a.id not in (0x2256, 0x2257, 0x2242):
                self.assertEqual(a.payload, b.payload, hex(a.id))
        banks = [
            property_bank(a.payload(0x2256), a.payload(0x2257)) for a in (old, new)
        ]
        changes = [i for i, (a, b) in enumerate(zip(*banks)) if a != b]
        self.assertEqual(len(changes), 4)
        names = old.payload(0x2254).decode("utf-16le").split("\0")[:-1]
        for h in changes:
            self.assertEqual(names[h], "Viewport 2")
            self.assertEqual(banks[1][h], camera_lifetime.properties(banks[0][h]))


if __name__ == "__main__":
    unittest.main()
