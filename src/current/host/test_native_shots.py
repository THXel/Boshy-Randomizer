"""Regression coverage for generated native shot events and menu/export contracts."""

import configparser
import copy
import struct
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from gameplay import shot_plan as plan, shot_events
from gameplay.native_extras import advance
from gameplay.normal_plan import FRAMES
from transition.events import commands
from transition.router import params, GROUP as ROUTE
from menu_host.draft import Draft
from menu_host.store import Store
from native_menu.model import Model
from native_menu.shot_labels import CAPTIONS
from menu_host.labels import LANGUAGES
import recover_boshy_classic as source


class EventMachine:
    """Small independent reader for the generated Ini++/arithmetic event subset."""

    def __init__(self, seed, mode, maximum=300):
        self.character = 12
        self.writes = 0
        self.config = plan.settings(
            seed, dict(shot_mode=mode, shot_interval_seconds=maximum)
        )
        self.data = {
            plan.GROUP: dict(self.config),
            **plan.profile(self.config),
            "Stats": {"Deaths": 0},
            ROUTE: {"Schema": 4, "CurrentStage": 1},
        }
        self.read_only = False
        self.saved = copy.deepcopy(self.data)
        self.snapshots = []

    @staticmethod
    def token(data, at):
        kind, code, length = struct.unpack_from("<hhH", data, at)
        return kind, code, data[at : at + length], at + length

    def value(self, data):
        at = 0
        pieces = []
        while at < len(data):
            kind, code, raw, at = self.token(data, at)
            if (kind, code) == (-1, 0):
                pieces.append(str(struct.unpack_from("<i", raw, 6)[0]))
            elif (kind, code) == (-1, 24):
                assert struct.unpack_from("<H", raw, 10)[0] == 5
                pieces.append(str(self.character))
            elif (kind, code) == (33, 88):
                _, _, g, at = self.token(data, at)
                _, _, _, at = self.token(data, at)
                _, _, k, at = self.token(data, at)
                _, _, _, at = self.token(data, at)
                _, _, default, at = self.token(data, at)
                _, _, _, at = self.token(data, at)
                g, k = [r[6:].split(b"\0")[0].decode() for r in (g, k)]
                pieces.append(
                    str(
                        self.data.get(g, {}).get(
                            k, struct.unpack_from("<i", default, 6)[0]
                        )
                    )
                )
            elif kind == 0:
                pieces.append({2: "+", 4: "-", 6: "*", 8: "//", 10: "%"}[code])
            else:
                pieces.append({(-1, -1): "(", (-1, -2): ")"}[(kind, code)])
        return eval(" ".join(pieces), {"__builtins__": {}}, {})

    def parameter(self, raw):
        return self.value(raw[6:-4])

    def run(self, rows, *, start=False, tick=False, alive=True):
        for row in rows:
            cs = commands(row)
            valid = True
            for cond, kind, code, oi, raw in cs:
                if not cond:
                    continue
                ps = params(raw, True)
                if (kind, code) == (-3, -1):
                    valid &= start
                elif (kind, code) == (-4, -4):
                    valid &= tick
                elif (kind, code) == (2, -32):
                    valid &= alive
                else:
                    assert (kind, code) == (-1, -3)
                    left, right = [self.parameter(p) for _, p in ps]
                    comparison = struct.unpack_from("<H", ps[1][1], 4)[0]
                    valid &= (
                        left == right,
                        left != right,
                        left <= right,
                        left < right,
                        left >= right,
                        left > right,
                    )[comparison]
            if not valid:
                continue
            for cond, kind, code, oi, raw in cs:
                if cond or code == 123:
                    continue
                if (kind, code) == (33, 132):
                    self.read_only = bool(self.parameter(params(raw)[0][1]))
                    self.snapshots.append(copy.deepcopy(self.saved))
                    continue
                if (kind, code) == (33, 124):
                    if not self.read_only:
                        self.saved = copy.deepcopy(self.data)
                    self.snapshots.append(copy.deepcopy(self.saved))
                    continue
                assert (kind, code) == (33, 94)
                self.writes += 1
                ps = params(raw)
                group, key = [p[1][12:].split(b"\0")[0].decode() for p in ps[:2]]
                self.data.setdefault(group, {})[key] = self.parameter(ps[3][1])
                if not self.read_only:
                    self.saved = copy.deepcopy(self.data)
                self.snapshots.append(copy.deepcopy(self.saved))


class NativeShotsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.changed = {}
        for payload, frame in source.routes.payloads.items():
            before = source.sections(payload)
            after, audit = shot_events.transform(
                frame,
                before,
                source.routes.objects,
                source.routes.frames[frame - 1]["instances"],
            )
            cls.changed[frame] = before, after, audit

    def rows(self, frame=3):
        before, after, audit = self.changed[frame]
        if frame == 2:
            return after[0][2:3], []
        added = len(after[0]) - len(before[0])
        return after[0][2 : 2 + added], after[-1]

    def step(self, machine, *, frame=3, start=False, tick=False, alive=True):
        early, late = self.rows(frame)
        machine.run(early, start=start, tick=tick, alive=alive)
        machine.run(late, start=start, tick=tick, alive=alive)

    def test_all_playable_frames_change_only_shot_images_and_their_license_guard(
        self,
    ):
        covered = set()
        for frame, (before, after, audit) in self.changed.items():
            if not audit:
                self.assertEqual(before, after)
                continue
            if frame == 2:
                self.assertEqual(before[0], after[0][:2] + after[0][3:])
                self.assertEqual(before[1:], after[1:])
                continue
            covered.add(frame)
            added = len(after[0]) - len(before[0])
            stripped = [after[0][:2] + after[0][2 + added :], *after[1:-1]]
            changes = 0
            for oldrows, newrows in zip(before, stripped):
                self.assertEqual(len(oldrows), len(newrows))
                for old, new in zip(oldrows, newrows):
                    oldcs, newcs = commands(old), commands(new)
                    self.assertEqual(len(oldcs), len(newcs))
                    for a, b in zip(oldcs, newcs):
                        if a == b:
                            continue
                        changes += 1
                        if a[0]:
                            self.check_license_guard(a, b)
                            continue
                        self.assertFalse(a[0])
                        self.assertEqual(a[:4], b[:4])
                        self.assertEqual(a[1:3], (2, 40))
                        self.assertEqual(
                            source.routes.objects[a[3]]["name"], "Bullet 2"
                        )
                        self.assertIn(params(a[-1])[0][1][6:-4], b[-1])
            self.assertEqual(changes, 3)
            # No new gameplay, sound, movement, destruction or character action.
            for rows in self.rows(frame):
                self.assertTrue(
                    all(c[1] == 33 for row in rows for c in commands(row) if not c[0])
                )
        self.assertEqual(covered, set(FRAMES))

    def test_death_section_and_combined_modes_coalesce_and_resume_does_not_advance(
        self,
    ):
        for mode in ("off", "spot", "death", "death_and_spot"):
            m = EventMachine("SHOTS025", mode)
            self.step(m, start=True)
            state = m.data[plan.STATE]
            self.assertEqual(state["Sequence"], 0)
            self.step(m, start=True)  # R without death, same section.
            self.assertEqual(state["Sequence"], 0)
            m.data["Stats"]["Deaths"] = 1
            m.data[ROUTE]["CurrentStage"] = 2
            self.step(m, start=True)
            expected = int(mode in ("death", "death_and_spot"))
            self.assertEqual(state["Sequence"], expected)
            self.step(m)
            self.assertEqual(state["Sequence"], expected)
            m.data[ROUTE]["CurrentStage"] = 3
            self.step(m, start=True)
            expected += int(mode in ("spot", "death_and_spot"))
            self.assertEqual(state["Sequence"], expected)
            menu, _ = self.rows(2)
            m.run(menu, start=True)
            m.data[ROUTE]["CurrentStage"] = 2  # checkpoint resumes elsewhere
            self.step(m, start=True)
            self.assertEqual(state["Sequence"], expected)

    def test_unchanged_gameplay_never_rewrites_the_shot_profile(self):
        for mode in plan.MODES:
            m = EventMachine("SHOTS025", mode)
            self.step(m, start=True)
            writes = m.writes
            for _ in range(100):
                self.step(m, tick=False)
            self.assertEqual(m.writes, writes, mode)

    def test_restart_at_every_action_observes_only_complete_shot_progress(self):
        m = EventMachine("SHOTS025", "random_interval", maximum=2)
        self.step(m, start=True)
        for _ in range(80):
            m.snapshots.clear()
            old = copy.deepcopy(m.saved[plan.STATE])
            self.step(m, tick=True)
            new = m.saved[plan.STATE]
            self.assertFalse(m.read_only)
            keys = ("Rng", "Frame", "Sequence")
            allowed = {tuple(s[k] for k in keys) for s in (old, new)}
            for snapshot in m.snapshots:
                state = snapshot[plan.STATE]
                self.assertIn(tuple(state[k] for k in keys), allowed)
                self.assertEqual(
                    state["Rng"], advance(m.config["InitialState"], state["Sequence"])
                )
        self.assertGreater(m.saved[plan.STATE]["Sequence"], 30)

    def test_normal_rooms_and_route_split_sections(self):
        m = EventMachine("SHOTS025", "spot")
        m.data[ROUTE]["Schema"] = 0
        self.step(m, start=True)
        self.step(m, frame=4, start=True)
        self.assertEqual(m.data[plan.STATE]["Sequence"], 1)
        self.step(m, frame=4, start=True)
        self.assertEqual(m.data[plan.STATE]["Sequence"], 1)
        m = EventMachine("SHOTS025", "spot")
        self.step(m, start=True)
        m.data[ROUTE]["CurrentStage"] = 2
        self.step(m, start=True)  # same actual frame, another split route section
        self.assertEqual(m.data[plan.STATE]["Sequence"], 1)

    def test_interval_native_arithmetic_bounds_no_repeat_and_death_time_pauses(self):
        for maximum in (1, 2, 300, 86400):
            m = EventMachine("SHOTS025", "random_interval", maximum)
            self.step(m, start=True)
            state = m.data[plan.STATE]
            previous = state["Frame"]
            for i in range(1, 60):
                remaining = state["Remaining"]
                self.step(m, tick=False)
                self.step(m, tick=True, alive=False)
                self.assertEqual(state["Remaining"], remaining)
                # Jump to the last remaining active second, exercising actual events.
                state["Remaining"] = 1
                self.step(m, tick=True)
                self.assertEqual(state["Sequence"], i)
                self.assertEqual(state["Rng"], advance(m.config["InitialState"], i))
                self.assertNotEqual(state["Frame"], previous)
                self.assertEqual(
                    state["Frame"], plan.next_frame(previous, state["Rng"])
                )
                self.assertEqual(
                    state["Remaining"], plan.interval(state["Rng"], maximum)
                )
                self.assertTrue(1 <= state["Remaining"] <= maximum)
                previous = state["Frame"]

    def check_license_guard(self, a, b):
        self.assertEqual(a[:4], b[:4])
        self.assertEqual(a[1:3], (-1, -3))
        old, new = params(a[-1], True), params(b[-1], True)
        self.assertIn(b"OnlineLicenseCharacter\0", old[0][1])
        self.assertEqual(old[1], new[1])
        m = EventMachine("SHOTS025", "spot")
        for enabled in (0, 1):
            for licensed in (0, 1):
                m.data[plan.GROUP]["Enabled"] = enabled
                m.data["Options"] = {"OnlineLicenseCharacter": licensed}
                self.assertEqual(m.parameter(new[0][1]), 1 if enabled else licensed)

    def test_shooting_sound_selection_keeps_all_actions_and_other_sound_rules(self):
        from gameplay import shot_sounds

        total = 0
        for frame, (before, _, _) in self.changed.items():
            after, audit = shot_sounds.transform(
                frame,
                before,
                source.routes.objects,
                source.routes.frames[frame - 1]["instances"],
            )
            if not audit:
                self.assertEqual(before, after)
                continue
            changed_rows = gates = 0
            for oldrows, newrows in zip(before, after):
                for old, new in zip(oldrows, newrows):
                    if old == new:
                        continue
                    changed_rows += 1
                    self.assertTrue(
                        any(
                            c[0] and c[1:3] == (-1, -16) and b"shooot\0" in c[-1]
                            for c in commands(old)
                        )
                    )
                    self.assertEqual(len(commands(old)), len(commands(new)))
                    for a, b in zip(commands(old), commands(new)):
                        if a == b:
                            continue
                        self.assertTrue(a[0])
                        if a[1:3] == (-1, -3):
                            self.check_license_guard(a, b)
                            gates += 1
                            continue
                        self.assertEqual(a[1:3], (-1, -8))
                        self.assertEqual(b[1:3], (-1, -3))
                        self.assertEqual(params(a[-1], True)[1], params(b[-1], True)[1])
                        expr = params(b[-1], True)[0][1]
                        m = EventMachine("SHOTS025", "spot")
                        for selected in range(36):
                            m.data[plan.STATE]["Frame"] = selected
                            self.assertEqual(m.parameter(expr), 12 + 4 * selected)
                        m.data[plan.GROUP]["Enabled"] = 0
                        m.character = 148
                        self.assertEqual(m.parameter(expr), 148)
                        total += 1
            self.assertEqual(changed_rows, 38)
            self.assertEqual(gates, 38)
        self.assertEqual(total, 39 * 37)

    def test_menu_all_modes_localized_seed_roundtrip_and_interval_bounds(self):
        with tempfile.TemporaryDirectory() as tmp:
            model = Model(Store(Path(tmp) / "profile", Path(tmp) / "runs"))
            model.go("cosmetics")
            model.select("shots")
            self.assertEqual(model.page, "shots")
            for mode in plan.MODES:
                before = model.draft.seed
                previous = model.draft.options["extras"]["shot_mode"]
                model.select("shot:" + mode)
                if mode != previous:
                    self.assertNotEqual(model.draft.seed, before)
                imported = Draft()
                imported.import_seed(model.draft.shared())
                self.assertEqual(imported.options["extras"]["shot_mode"], mode)
            for language in LANGUAGES:
                model.language = language
                self.assertTrue(all(r.label for r in model.rows()))
                self.assertEqual(len(CAPTIONS["shots"]), len(LANGUAGES))
            model.draft.update(shot_interval_seconds=1)
            model.select("shot_interval_seconds", -1)
            self.assertEqual(model.draft.options["extras"]["shot_interval_seconds"], 1)
            model.draft.update(shot_interval_seconds=86400)
            model.select("shot_interval_seconds", 1)
            self.assertEqual(
                model.draft.options["extras"]["shot_interval_seconds"], 86400
            )
            model.key(27)
            self.assertEqual(model.page, "cosmetics")

    def test_native_export_supports_auto_character_and_keeps_slots_separate(self):
        from functools import partial
        from export_native_run import export
        from menu_host.store import save
        from native_menu import builds

        self.assertTrue(builds.DYNAMIC_SHOTS)
        with tempfile.TemporaryDirectory() as tmp:
            store = Store(
                Path(tmp) / "profile",
                Path(tmp) / "runs",
                exporter=partial(export, dynamic=True),
            )
            with store.lock():
                for slot, mode in enumerate(
                    ("random_interval", "death_and_spot", "off"), 1
                ):
                    d = Draft()
                    d.update(
                        characters=False,
                        start_character="Auto",
                        shot_mode=mode,
                        shot_interval_seconds=86400,
                    )
                    d.seed = "SLOT000" + str(slot)
                    store.create(slot, d)
                    folder, p, c = store.resume(slot)
                    self.assertIsNone(p["start_character"])
                    self.assertEqual(p["native_shots_schema"], 1)
                    self.assertEqual(
                        c.getint(plan.GROUP, "Mode"), plan.MODES.index(mode)
                    )
                    if mode != "off":
                        profile = save(folder / "onlineLicense.ini")
                        self.assertFalse(profile.has_section("License"))
                        self.assertEqual(profile.getint(plan.STATE, "Sequence"), 0)
                first = save(store.folder(1) / "onlineLicense.ini")
                second = save(store.folder(2) / "onlineLicense.ini")
                self.assertNotEqual(
                    first.getint(plan.STATE, "Rng"), second.getint(plan.STATE, "Rng")
                )

    def test_compiled_shots_preserve_art_audio_collision_properties_and_viewport_fix(
        self,
    ):
        from native_menu import builds
        from visuals.scenery_pack import App, object_mapping
        from visuals.fusion25 import property_bank
        from menu_host.runtime import verify_engine

        verify_engine(builds.DYNAMIC_BASE, builds.DYNAMIC_SHA)
        old = App(builds.DYNAMIC_BASE.with_name("Boshy-dynamic-v16.exe"))
        new = App(builds.DYNAMIC_BASE)
        from visuals.compiled_audit import assert_original_banks, assert_active_extension
        assert_original_banks(self, old, new)
        original = list(source.routes.objects.values())
        maps = [object_mapping(app, original, active_only=True) for app in (old, new)]
        banks = [
            property_bank(app.payload(0x2256), app.payload(0x2257))
            for app in (old, new)
        ]
        for oi in maps[0]:
            assert_active_extension(self, banks[0][maps[0][oi]], banks[1][maps[1][oi]], oi)
        # Fusion may deduplicate equivalent viewports during compilation.
        names = new.payload(0x2254).decode("utf-16le").split("\0")[:-1]
        viewports = [i for i, n in enumerate(names) if n == "Viewport 2"]
        self.assertTrue(viewports)
        for oi in viewports:
            self.assertTrue(struct.unpack_from("<I", banks[1][oi], 16)[0] & 0x2000)

    def test_older_build_rejects_enabled_and_state_validation_detects_changes(self):
        from export_native_run import export

        d = Draft()
        d.update(shot_mode="death")
        with (
            tempfile.TemporaryDirectory() as tmp,
            patch("native_menu.builds.DYNAMIC_SHOTS", False),
        ):
            with self.assertRaisesRegex(ValueError, "newer native build"):
                export(d.shared(), Path(tmp) / "run", dynamic=True)
            self.assertFalse((Path(tmp) / "run").exists())
        config = configparser.ConfigParser()
        config.read_dict(
            {
                plan.GROUP: plan.settings(d.seed, d.options["extras"]),
                "Stats": {"Deaths": 0},
            }
        )
        license = configparser.ConfigParser()
        license.read_dict(plan.profile(plan.settings(d.seed, d.options["extras"])))
        p = dict(seed=d.seed, options=d.options, native_shots_schema=1)
        plan.validate(p, config, license)
        license[plan.STATE]["Sequence"] = "1"
        with self.assertRaisesRegex(ValueError, "progress"):
            plan.validate(p, config, license)
        license[plan.STATE]["Sequence"] = "0"
        config[plan.GROUP]["Mode"] = "1"
        with self.assertRaisesRegex(ValueError, "settings"):
            plan.validate(p, config, license)


if __name__ == "__main__":
    unittest.main()
