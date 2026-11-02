"""Scenery must preserve collision masks, scene layering and per-save isolation."""

import copy
import json
import io
import struct
import tempfile
import unittest
from functools import partial
from pathlib import Path
from unittest.mock import patch
from PIL import Image
import recover_boshy_routes as source
from visuals import runtime_scenery as runtime, scenery_assets as assets
from transition.events import commands, expression, integer, parameter
from transition.router import params
from native_menu import builds
from native_menu.session_store import WorkingSession
from menu_host.store import Store, digest, save, RC4
from menu_host.draft import Draft
from export_native_run import export


class RuntimeSceneryTests(unittest.TestCase):
    def test_every_placement_preserves_coordinates_layer_mask_and_order(self):
        count = 0
        for payload, frame in source.payloads.items():
            scene = source.frames[frame - 1]
            before = source.original_sections(payload)
            after, audit = runtime.transform(
                frame, before, source.objects, scene["instances"]
            )
            converted, objects = runtime.convert_frame(frame, scene, source.objects)
            if not audit:
                self.assertEqual(before, after)
                self.assertIs(converted, scene)
                continue
            extra = after[0][: len(after[0]) - len(before[0])]
            self.assertEqual(after[0][len(extra) :], before[0])
            self.assertEqual(after[1:], before[1:])
            acts = [c for row in extra for c in commands(row) if not c[0]]
            placed = runtime.placements(frame, scene["instances"])
            positions = [c for c in acts if c[1] == 2 and c[2] in (2, 3, 83)]
            self.assertEqual(len(positions), len(placed) * 3)
            helper_instances = {
                i["objectInfo"]: i
                for i in converted["instances"]
                if i["objectInfo"] >= 6000
            }
            removed = {r["oi"] for _, _, r in placed}
            self.assertEqual(
                [i for i in converted["instances"] if i["objectInfo"] < 6000],
                [i for i in scene["instances"] if i["objectInfo"] not in removed],
            )
            for offset, (inst, index, row) in enumerate(placed):
                oi = runtime.helper(row["oi"], inst["layer"])
                x, y, add = positions[offset * 3 : offset * 3 + 3]
                self.assertEqual([c[3] for c in (x, y, add)], [oi] * 3)
                self.assertEqual(
                    params(x[-1]), [(22, expression(integer(inst["x"] + row["hx"])))]
                )
                self.assertEqual(
                    params(y[-1]), [(22, expression(integer(inst["y"] + row["hy"])))]
                )
                self.assertEqual(
                    params(add[-1]),
                    [(43, parameter(43, struct.pack("<IH", row["obstacle"], 0)))],
                )
                self.assertEqual(helper_instances[oi]["layer"], inst["layer"])
                self.assertEqual(
                    objects[oi]["animations"][0]["directions"][0]["frames"],
                    [row["image"]],
                )
                self.assertEqual(objects[oi]["qualifiers"], [])
            self.assertEqual(
                set(c[3] for c in acts if c[1:3] == (2, 26)), set(helper_instances)
            )
            self.assertFalse(
                any(c[1:3] == (2, 24) and c[3] in helper_instances for c in acts)
            )
            for oi in helper_instances:
                self.assertTrue(
                    struct.unpack_from("<I", objects[oi]["properties"], 16)[0] & 0x2000
                )
            count += len(placed)
        self.assertGreater(count, 10000)

    def test_retained_backdrops_never_cover_an_earlier_replaced_backdrop(self):
        selected = {r["oi"] for r in runtime.records() if r["type"] == 1}
        self.assertEqual(len(selected), 131)
        self.assertFalse(selected & runtime.ORDER_PROTECTED)
        for oi in selected:
            obj = source.objects[oi]
            self.assertEqual(
                (obj["inkEffect"], obj["inkEffectParameter"], obj["shader"]),
                (0x10000000, 0xFFFFFFFF, None),
            )
        for number, frame in enumerate(source.frames, 1):
            selected = {
                r["oi"] for _, r in runtime.frame_records(number) if r["type"] == 1
            }
            moved = []
            for inst in frame["instances"]:
                obj = source.objects[inst["objectInfo"]]
                if obj["type"] not in (0, 1):
                    continue
                w, h = struct.unpack_from("<II", obj["properties"], 8)
                box = (
                    inst["x"],
                    inst["y"],
                    inst["x"] + w,
                    inst["y"] + h,
                    inst["layer"],
                )
                if inst["objectInfo"] in selected:
                    moved.append(box)
                else:
                    for old in moved:
                        overlap = (
                            old[4] == box[4]
                            and old[0] < box[2]
                            and box[0] < old[2]
                            and old[1] < box[3]
                            and box[1] < old[3]
                        )
                        self.assertFalse(overlap, (inst["objectInfo"], old, box))

    def test_pngs_preserve_original_alpha_and_restore_original_when_disabled(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            choices = []
            for n, seed, enabled in (
                (1, "SEED-A", True),
                (2, "SEED-B", True),
                (3, "SEED-A", False),
            ):
                folder = root / str(n)
                folder.mkdir()
                rows, settings = assets.prepare(
                    folder,
                    seed,
                    dict(
                        sprite_scenery=enabled,
                        sprite_backgrounds=True,
                        sprite_tiles=True,
                        sprite_decor=True,
                        sprite_dim=20,
                    ),
                )
                plan = dict(
                    seed=seed,
                    options={
                        "extras": dict(
                            sprite_scenery=enabled,
                            sprite_backgrounds=True,
                            sprite_dim=20,
                        )
                    },
                    runtime_scenery_schema=1,
                    runtime_scenery_assets=rows,
                    runtime_scenery_settings=settings,
                )
                assets.validate_assets(folder, plan)
                self.assertEqual(settings["EmbeddedOnly"], int(not enabled))
                legacy = copy.deepcopy(plan)
                del legacy["runtime_scenery_settings"]["EmbeddedOnly"]
                assets.validate_assets(folder, legacy)
                if enabled:
                    bad_embedded = copy.deepcopy(plan)
                    bad_embedded["runtime_scenery_settings"]["EmbeddedOnly"] = 1
                    with self.assertRaisesRegex(ValueError, "original artwork"):
                        assets.validate_assets(folder, bad_embedded)
                choices.append([r["sha256"] for r in rows])
                self.assertEqual(any(r["changed"] for r in rows), enabled)
                bad = copy.deepcopy(plan)
                bad["runtime_scenery_assets"][0]["file"] = "../outside.png"
                with self.assertRaises(ValueError):
                    assets.validate_assets(folder, bad)
                if not enabled:
                    for r in rows:
                        with Image.open(
                            folder / runtime.DIRECTORY / r["file"]
                        ) as image:
                            self.assertEqual(
                                image.convert("RGBA").tobytes(),
                                assets.graphic(r["image"]).tobytes(),
                            )
                (folder / runtime.DIRECTORY / rows[0]["file"]).write_bytes(b"corrupt")
                with self.assertRaises(ValueError):
                    assets.validate_assets(folder, plan)
            self.assertNotEqual(choices[0], choices[1])
            self.assertNotEqual(choices[0], choices[2])

    @unittest.skipUnless(builds.DYNAMIC_SCENERY, "Runtime scenery build not enabled")
    def test_compiled_original_actives_and_asset_banks_are_unchanged(self):
        from visuals.scenery_pack import App, object_mapping
        from visuals.fusion25 import property_bank

        old = App(builds.DYNAMIC_BASE.with_name("Boshy-dynamic-v13.exe"))
        new = App(builds.DYNAMIC_BASE)
        names = new.payload(0x2254).decode("utf-16le").split("\0")[:-1]
        expected = {
            runtime.PREFIX + str(r["oi"]) + "/" + str(i["layer"])
            for f, scene in enumerate(source.frames, 1)
            for i, _, r in runtime.placements(f, scene["instances"])
        }
        actual = [n for n in names if n.startswith(runtime.PREFIX)]
        self.assertEqual(set(actual), expected)
        self.assertEqual(len(actual), len(expected))
        from visuals.compiled_audit import (
            assert_original_banks,
            assert_active_extension,
        )

        assert_original_banks(self, old, new)
        mappings = [
            object_mapping(app, source.app.objects()[0], active_only=True)
            for app in (old, new)
        ]
        banks = [
            property_bank(app.payload(0x2256), app.payload(0x2257))
            for app in (old, new)
        ]
        self.assertEqual(set(mappings[0]), set(mappings[1]))
        self.assertEqual(len(mappings[0]), 1686)
        for oi in mappings[0]:
            assert_active_extension(
                self, banks[0][mappings[0][oi]], banks[1][mappings[1][oi]], oi
            )

    def test_slots_share_exe_and_stage_only_their_own_images(self):
        with patch.object(
            builds, "DYNAMIC_SCENERY", True
        ), tempfile.TemporaryDirectory() as t:
            root = Path(t)
            store = Store(
                root / "profile",
                runs=root / "runs",
                exporter=partial(export, dynamic=True),
            )
            with store.lock():
                for slot in (1, 2, 3):
                    draft = Draft()
                    draft.update(
                        sprite_scenery=slot != 3,
                        sprite_backgrounds=True,
                        sprite_decor=True,
                        sprite_tiles=True,
                    )
                    draft.seed = f"SCENERY{slot}"
                    store.create(slot, draft)
                    self.assertEqual(
                        digest(store.folder(slot) / "Boshy.exe"), builds.DYNAMIC_SHA
                    )
                working = root / "working"
                working.mkdir()
                session = WorkingSession(working, store, builds.DYNAMIC_SHA)
                for slot in (1, 2, 3, 1):
                    session.stage(slot)
                    plan = json.loads((store.folder(slot) / "plan.json").read_text())
                    assets.validate_assets(working, plan)
                    self.assertEqual(
                        len(list((working / runtime.DIRECTORY).iterdir())), 140
                    )
                    self.assertEqual(
                        save(working / "SaveFile1.ini").getint(runtime.GROUP, "Schema"),
                        1,
                    )
                    session.commit()
                config = save(store.folder(1) / "SaveFile1.ini")
                config[runtime.GROUP]["Image0"] = "native-scenery\\wrong.png"
                buffer = io.StringIO()
                config.write(buffer)
                (store.folder(1) / "SaveFile1.ini").write_bytes(
                    RC4(b"BLOB", buffer.getvalue().encode("latin1"))
                )
                with self.assertRaisesRegex(ValueError, "scenery settings"):
                    store.resume(1)


if __name__ == "__main__":
    unittest.main()
