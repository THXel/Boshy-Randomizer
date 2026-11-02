"""Readable source names must not reroute an existing shared seed or native save."""

import hashlib
import json
import unittest
from export_route_probe import ROOT, REPO, plan, save_text
from transition.router import STAGES, NAMED_STAGES, CATALOGUE_HASH
from position_names import (
    LEGACY_KEYS,
    POSITION_NAMES,
    legacy_key,
    position_name,
    legacy_catalogue,
    legacy_positions,
)
from menu_host.draft import Draft
from native_level_route import catalogue
from run_settings import route

BEFORE = ROOT / "outputs/Fusion-PositionNames-20261025/before"


class PositionNameTests(unittest.TestCase):
    def test_catalogues_keep_every_coordinate_and_native_identity(self):
        for name, normalizer in [
            ("assets/INI/positions.json", legacy_positions),
            ("assets/catalogues/native_spots.json", legacy_catalogue),
        ]:
            old = json.loads((BEFORE / "repo" / name).read_text())
            new = json.loads((REPO / name).read_text())
            if name.endswith("positions.json"):
                old["bosses"]["boss21.ini"].update(xPos="159", yPos="425")
                old["rooms"]["save20.ini"].update(xPos="319", yPos="3769")
            self.assertEqual(normalizer(new), old)
        old = json.loads((BEFORE / "lab/transition/stages.json").read_text())
        # Explicit corrections to the original spawn and the second Warcraft exit.
        old["boss21.ini"].update(x=159, y=425)
        old["save20.ini"].update(x=319, y=3769)
        old["save21.ini"]["native_exit_frames"] = [54, 29]
        self.assertEqual(STAGES, old)
        self.assertEqual(
            CATALOGUE_HASH,
            hashlib.sha256(
                json.dumps(old, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest(),
        )
        for key in NAMED_STAGES:
            self.assertNotIn(".ini", key)
            self.assertFalse(key.startswith(("boss", "level", "save")), key)
        self.assertEqual(len(STAGES), 44)

    def test_names_are_bijective_and_ambiguous_aliases_fail(self):
        self.assertEqual(len(LEGACY_KEYS), len(POSITION_NAMES))
        for name, key in LEGACY_KEYS.items():
            self.assertEqual(legacy_key(name), key)
            self.assertEqual(position_name(key), name)
        with self.assertRaises(ValueError):
            legacy_catalogue({"sonic": {}, "boss9.ini": {}})
        with self.assertRaises(ValueError):
            Draft().update(level_pool=["castlevania", "save7.ini"], level_count=1)

    def test_named_menu_selections_preserve_seed_bytes_and_route(self):
        for mode in ("randomizer", "level_rush"):
            old, new = Draft(), Draft()
            old.set_mode(mode)
            new.set_mode(mode)
            old.update(
                level_pool=["save1.ini", "save7.ini", "save9.ini", "save10.ini"],
                level_count=4,
            )
            new.update(
                level_pool=[
                    "prehistorik",
                    "castlevania",
                    "random_world_part_1",
                    "random_world_part_2",
                ],
                level_count=4,
            )
            for i in range(100):
                old.seed = new.seed = f"NAME{i:04d}"
                self.assertEqual(old.shared(), new.shared())
                self.assertEqual(
                    route(old.seed, old.options), route(new.seed, new.options)
                )

    def test_named_export_is_byte_identical_to_old_entry(self):
        shared = json.loads(
            (
                ROOT / "outputs/Fusion-FrameLinks-20261023/seed-mario/plan.json"
            ).read_text()
        )["shared_seed"]
        for old, new in [("boss6.ini", "mario"), ("save7.ini", "castlevania")]:
            a = plan(shared, "verified", "verified", old)
            b = plan(shared, "verified", "verified", new)
            self.assertEqual(a, b)
            self.assertEqual(save_text(a), save_text(b))
        with self.assertRaises(ValueError):
            plan(shared, "verified", "verified", "kracko")

    def test_shared_pool_accepts_old_and_named_assets(self):
        old = json.loads((BEFORE / "repo/assets/INI/positions.json").read_text())
        new = json.loads((REPO / "assets/INI/positions.json").read_text())
        old["bosses"]["boss21.ini"].update(xPos="159", yPos="425")
        old["rooms"]["save20.ini"].update(xPos="319", yPos="3769")
        self.assertEqual(catalogue(old), catalogue(new))


if __name__ == "__main__":
    unittest.main()
