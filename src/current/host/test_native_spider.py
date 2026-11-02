"""Native spider regression tests using decoded events, not a second game writer."""

import ast
import math
import struct
import tempfile
import unittest
from functools import partial
from pathlib import Path
from unittest.mock import patch
import recover_boshy_classic as source
from gameplay import spider_events as ev, spider_plan as plan, spider_object
from gameplay.normal_plan import FRAMES
from gameplay.native_extras import advance
from gameplay.god_mode import GROUP as GOD, KEY as GOD_KEY
from transition.events import commands
from transition.router import params
from test_native_shots import EventMachine
from menu_host.draft import Draft
from menu_host.store import Store, save
from native_menu.model import Model


class NativeDivision(ast.NodeTransformer):
    def visit_BinOp(self, node):
        node = self.generic_visit(node)
        if isinstance(node.op, ast.Div):
            return ast.copy_location(
                ast.Call(ast.Name("divide", ast.Load()), [node.left, node.right], []),
                node,
            )
        return node


class Machine(EventMachine):
    def __init__(self, seed="SPIDER", enabled=True, god=True):
        self.config = plan.settings(seed, {"spider": enabled})
        self.data = {
            plan.GROUP: self.config,
            **plan.profile(self.config),
            GOD: {GOD_KEY: int(not god)},
        }
        self.values = [0] * 12
        self.player = [320, 240]
        self.camera = [0, 0]
        self.focus = self.alive = True
        self.invulnerable = False
        self.visible = False
        self.position = [-200, -200]
        self.angle = self.scale = 0
        self.deaths = self.sounds = self.writes = 0

    def value(self, data):
        at, pieces = 0, []
        while at < len(data):
            kind, code, raw, at = self.token(data, at)
            if (kind, code) == (-1, 0):
                pieces.append(str(struct.unpack_from("<i", raw, 6)[0]))
            elif (kind, code) == (-1, 23):
                pieces.append(repr(struct.unpack_from("<d", raw, 6)[0]))
            elif (kind, code) == (33, 88):
                start = at - len(raw)
                for _ in range(6):
                    _, _, _, at = self.token(data, at)
                pieces.append(str(super().value(data[start:at])))
            elif kind == 2:
                oi = struct.unpack_from("<H", raw, 6)[0]
                if code == 16:
                    assert oi == spider_object.OBJECT
                    result = self.values[struct.unpack_from("<H", raw, 10)[0]]
                else:
                    assert code in (11, 1)
                    result = self.player[0 if code == 11 else 1]
                pieces.append(repr(result))
            elif kind == -3:
                pieces.append(str(self.camera[{2: 0, 4: 1}[code]]))
            elif kind == 0:
                pieces.append({2: "+", 4: "-", 6: "*", 8: "/", 10: "%"}[code])
            elif kind == -1 and code in (13, 29, 41, 59):
                pieces.append({13: "sqrt(", 29: "abs(", 41: "max(", 59: "angle("}[code])
            else:
                pieces.append(
                    {(-1, -1): "(", (-1, -2): ")", (-1, -3): ","}[(kind, code)]
                )
        tree = ast.fix_missing_locations(
            NativeDivision().visit(ast.parse(" ".join(pieces), mode="eval"))
        )
        return eval(
            compile(tree, "<native>", "eval"),
            {"__builtins__": {}},
            {
                "sqrt": math.sqrt,
                "abs": abs,
                "max": max,
                "angle": lambda y, x: math.degrees(math.atan2(y, x)),
                "divide": lambda a, b: int(a / b)
                if isinstance(a, int) and isinstance(b, int)
                else a / b,
            },
        )

    def run(self, rows, start=False):
        for row in rows:
            cs = commands(row)
            valid = True
            for cond, kind, code, oi, raw in cs:
                if not cond:
                    continue
                ps = params(raw, True)
                if (kind, code) == (-3, -1):
                    valid &= start
                elif (kind, code) == (44, -85):
                    valid &= self.focus != bool(
                        struct.unpack_from("<H", raw, 10)[0] & 0x100
                    )
                elif (kind, code) == (2, -32):
                    comparison = struct.unpack_from("<H", ps[-1][1], 4)[0]
                    value = self.parameter(ps[-1][1])
                    valid &= (
                        (int(self.alive) == value)
                        if comparison == 0
                        else int(self.alive) > value
                    )
                elif kind == 2 and code in (-24, -25):
                    valid &= self.invulnerable == (code == -25)
                else:
                    assert (kind, code) == (-1, -3), (kind, code)
                    left, right = [self.parameter(p) for _, p in ps]
                    valid &= (
                        left == right,
                        left != right,
                        left <= right,
                        left < right,
                        left >= right,
                        left > right,
                    )[struct.unpack_from("<H", ps[1][1], 4)[0]]
            if not valid:
                continue
            for cond, kind, code, oi, raw in cs:
                if cond:
                    continue
                ps = params(raw)
                if kind == 33 and code in (132, 124):
                    continue  # Persistence boundaries; state calculations stay native.
                if (kind, code) == (33, 94):
                    group, key = [p[1][12:].split(b"\0")[0].decode() for p in ps[:2]]
                    self.data[group][key] = int(self.parameter(ps[3][1]))
                    self.writes += 1
                elif (kind, code) == (2, 31):
                    self.values[struct.unpack_from("<I", ps[0][1], 4)[0]] = (
                        self.parameter(ps[1][1])
                    )
                elif kind == 2 and code in (2, 3):
                    self.position[code - 2] = int(self.parameter(ps[0][1]))
                elif (kind, code) == (2, 26):
                    self.visible = False
                elif (kind, code) == (2, 27):
                    self.visible = True
                elif (kind, code) == (2, 85):
                    self.scale = self.parameter(ps[0][1])
                elif (kind, code) == (2, 88):
                    self.angle = self.parameter(ps[0][1]) % 360
                elif (kind, code) == (2, 57):
                    pass
                elif (kind, code) == (-2, 11):
                    self.sounds += 1
                elif (kind, code) == (-1, 14):
                    self.alive = False
                    self.deaths += 1
                else:
                    raise AssertionError((kind, code))


class SpiderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = {}
        cls.audits = {}
        for payload, frame in source.routes.payloads.items():
            before = source.sections(payload)
            after, audit = ev.transform(
                frame,
                before,
                source.routes.objects,
                source.routes.frames[frame - 1]["instances"],
            )
            assert after[:-1] == before if audit else after == before
            if audit:
                cls.rows[frame] = after[-1]
                cls.audits[frame] = audit[0]

    def test_all_scenes_preserve_original_events_and_isolate_new_object(self):
        self.assertEqual(set(self.rows), set(FRAMES))
        for frame, rows in self.rows.items():
            original = source.routes.frames[frame - 1]
            changed, objects = spider_object.convert_frame(
                frame, original, source.routes.objects
            )
            self.assertEqual(changed["instances"][:-1], original["instances"])
            obj = objects[spider_object.OBJECT]
            self.assertEqual(obj["qualifiers"], [])
            self.assertEqual(obj["animations"][0]["directions"][0]["frames"], [2287])
            self.assertTrue(struct.unpack_from("<I", obj["properties"], 16)[0] & 0x2000)
            acts = [c for row in rows for c in commands(row) if not c[0]]
            self.assertEqual(len([c for c in acts if c[1:3] == (-1, 14)]), 1)
            self.assertTrue(
                all(c[3] == spider_object.OBJECT for c in acts if c[1] == 2)
            )
            self.assertTrue(all(c[1] in (2, 33, -1, -2) for c in acts))

    def test_coordinate_expressions_match_original_self_position_actions(self):
        # The runtime assigns X=11, Y=1; code 0 is not a valid Active expression.
        # Derive the expected tokens from the original game's own X/Y updates.
        matched = set()
        for payload in source.routes.payloads:
            for section in source.sections(payload):
                for row in section:
                    for cond, kind, code, oi, raw in commands(row):
                        if cond or kind != 2 or code not in (2, 3):
                            continue
                        ps = params(raw)
                        if not ps or ps[0][0] != 22:
                            continue
                        token = ps[0][1][6:16]
                        if len(token) == 10:
                            tk, tc, size, reference, _ = struct.unpack("<hhHHH", token)
                            if tk == 2 and reference == oi and tc in (1, 11):
                                self.assertEqual(ev.xy(oi, code - 2), token)
                                matched.add(code)
            if matched == {2, 3}:
                break
        self.assertEqual(matched, {2, 3})

    def test_compiled_spider_is_separate_and_uses_unchanged_original_art(self):
        from native_menu import builds
        from visuals.scenery_pack import App, object_mapping
        from visuals.fusion25 import property_bank, animation_slot

        app = App(builds.DYNAMIC_BASE)
        names = app.payload(0x2254).decode("utf-16le").split("\0")[:-1]
        self.assertEqual(names.count(spider_object.NAME), 1)
        oi = names.index(spider_object.NAME)
        bank = property_bank(app.payload(0x2256), app.payload(0x2257))
        props = bank[oi]
        self.assertEqual(struct.unpack_from("<I", props, 16)[0] & 0x6000, 0x6000)
        self.assertEqual(props[20:36], b"\xff" * 16)
        mapping = object_mapping(
            app, list(source.routes.objects.values()), active_only=True
        )
        original = bank[mapping[181]]
        self.assertEqual(
            struct.unpack_from("<H", props, animation_slot(props, 0, 0, 0)),
            struct.unpack_from("<H", original, animation_slot(original, 0, 0, 0)),
        )

    def test_countdown_grace_pause_off_and_single_second_writes(self):
        rows = self.rows[4]
        m = Machine()
        m.run(rows, start=True)
        remaining = m.data[plan.STATE]["Remaining"]
        for _ in range(plan.GRACE - 2):
            m.run(rows)
        self.assertEqual(m.data[plan.STATE]["Remaining"], remaining)
        for _ in range(50):
            m.run(rows)
        self.assertEqual(m.data[plan.STATE]["Remaining"], remaining - 1)
        self.assertEqual(m.writes, 1)
        for key, val in [("focus", False), ("alive", False), ("invulnerable", True)]:
            m = Machine()
            m.run(rows, start=True)
            setattr(m, key, val)
            m.values[ev.GRACE] = 0
            for _ in range(60):
                m.run(rows)
            self.assertEqual(
                m.data[plan.STATE]["Remaining"], plan.interval(m.config["InitialState"])
            )
            self.assertEqual(m.sounds, 0)
        m = Machine(enabled=False)
        m.run(rows, start=True)
        m.data[plan.STATE]["Remaining"] = 0
        m.values[ev.GRACE] = 0
        for _ in range(60):
            m.run(rows)
        self.assertEqual(m.sounds, 0)
        self.assertFalse(m.visible)
        self.assertEqual(m.writes, 0)

    def test_four_edges_speed_straight_flight_and_feet_face_player(self):
        sides = set()
        for seed in range(40):
            m = Machine(str(seed))
            rows = self.rows[4]
            m.run(rows, start=True)
            m.data[plan.STATE]["Remaining"] = 0
            m.values[ev.GRACE] = 0
            m.run(rows)
            self.assertTrue(m.visible)
            self.assertEqual(m.sounds, 1)
            self.assertEqual(m.data[plan.STATE]["Attacks"], 1)
            self.assertEqual(
                m.data[plan.STATE]["Rng"], advance(m.config["InitialState"], 3)
            )
            self.assertTrue(
                plan.MINIMUM <= m.data[plan.STATE]["Remaining"] <= plan.MAXIMUM
            )
            sides.add(m.values[ev.SIDE])
            velocity = m.values[ev.DX : ev.DY + 1]
            self.assertAlmostEqual(math.hypot(*velocity) * 50, 475, places=7)
            m.player = [600, 50]
            m.run(rows)
            self.assertEqual(m.values[ev.DX : ev.DY + 1], velocity)
            dx, dy = m.player[0] - m.values[ev.X], m.player[1] - m.values[ev.Y]
            self.assertAlmostEqual(
                m.angle, (math.degrees(math.atan2(-dy, dx)) + 90) % 360
            )
        self.assertEqual(sides, {0, 1, 2, 3})

    def test_hit_uses_normal_death_godmode_survives_cleanup_and_resume(self):
        rows = self.rows[4]
        for god in (True, False):
            m = Machine(god=god)
            m.run(rows, start=True)
            m.data[plan.STATE]["Remaining"] = 0
            m.values[ev.GRACE] = 0
            m.run(rows)
            m.player = [
                m.values[ev.X] + m.values[ev.DX],
                m.values[ev.Y] + m.values[ev.DY],
            ]
            m.run(rows)
            self.assertEqual(m.deaths, int(not god))
            self.assertEqual(m.data[plan.STATE]["Hits"], int(not god))
            if god:
                for _ in range(180):
                    m.run(rows)
                self.assertFalse(m.visible)
            state = dict(m.data[plan.STATE])
            m.alive = True
            m.run(rows, start=True)
            self.assertFalse(m.visible)
            self.assertEqual(m.data[plan.STATE], state)
        m = Machine()
        m.run(rows, start=True)
        m.values[ev.GRACE] = 0
        m.data[plan.STATE]["Remaining"] = 0
        m.run(rows)
        m.focus = False
        m.run(rows)
        self.assertFalse(m.visible)
        self.assertEqual(m.values[ev.GRACE], 750)

    def test_menu_remembers_spider_without_overwriting_saved_seed_or_language(self):
        from native_menu.preferences import save_preferences, load_preferences

        with tempfile.TemporaryDirectory() as t:
            store = Store(Path(t) / "p", Path(t) / "r")
            save_preferences(store.root, language="en", spider=False)
            m = Model(store)
            m.go("gameplay")
            before = m.draft.seed
            m.select("spider")
            self.assertNotEqual(before, m.draft.seed)
            self.assertTrue(m.draft.options["extras"]["spider"])
            self.assertTrue(Model(store).draft.options["extras"]["spider"])
            self.assertEqual(load_preferences(store.root)["language"], "en")
            for lang in ("de", "en", "es", "ru", "ja"):
                m.language = lang
                self.assertNotEqual(m.t("spider"), "spider")
                self.assertNotEqual(m.t("spider_hint"), "spider_hint")
            shared = m.draft.shared()
            d = Draft()
            d.import_seed(shared)
            self.assertTrue(d.options["extras"]["spider"])
            m.select("spider")
            self.assertFalse(Model(store).draft.options["extras"]["spider"])
            d.apply_preset("training")
            self.assertTrue(d.options["extras"]["spider"])

    def test_export_slot_profiles_validation_and_old_build_rejection(self):
        from export_native_run import export
        from native_menu import builds

        with (
            tempfile.TemporaryDirectory() as t,
            patch.object(builds, "DYNAMIC_SPIDER", True),
        ):
            store = Store(
                Path(t) / "p", Path(t) / "r", exporter=partial(export, dynamic=True)
            )
            with store.lock():
                for slot, enabled in ((1, True), (2, False)):
                    d = Draft()
                    d.update(spider=enabled, start_character="Auto", characters=False)
                    d.seed = "SPIDER" + str(slot)
                    store.create(slot, d)
                    folder, p, c = store.resume(slot)
                    self.assertEqual(p["native_spider_schema"], 1)
                    if enabled:
                        profile = save(folder / "onlineLicense.ini")
                        self.assertFalse(profile.has_section("License"))
                        plan.validate(p, c, profile)
                        profile[plan.STATE]["Rng"] = "0"
                        with self.assertRaisesRegex(ValueError, "progress"):
                            plan.validate(p, c, profile)
                m = Model(store)
                self.assertTrue(m.draft.options["extras"]["spider"])
                m.go("gameplay")
                seed = m.draft.seed
                m.select("spider")
                self.assertEqual(m.draft.seed, seed)
        with (
            tempfile.TemporaryDirectory() as t,
            patch.object(builds, "DYNAMIC_SPIDER", False),
        ):
            d = Draft()
            d.update(spider=True)
            with self.assertRaisesRegex(ValueError, "newer native build"):
                export(d.shared(), Path(t) / "old", dynamic=True)


if __name__ == "__main__":
    unittest.main()
