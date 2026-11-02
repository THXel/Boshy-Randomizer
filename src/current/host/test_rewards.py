"""Mixed rewards: deterministic bijection, native chest gates and save binding."""

import configparser, unittest
from collections import Counter
from gameplay.reward_plan import LOCATIONS, mapping, settings, validate, GROUP
from gameplay.rewards import transform
from transition.events import commands, expression, integer
from transition.router import params
import recover_boshy_pickups as source


class RewardsTests(unittest.TestCase):
    def test_pool_is_exact_deterministic_and_independent(self):
        original = {(l["source_kind"], l["source"]) for l in LOCATIONS}
        self.assertEqual(len(original), 36)
        for seed in ["00000000", "DEADBEEF", "12345678"]:
            m = mapping(seed, True)
            self.assertEqual(set(m), {l["key"] for l in LOCATIONS})
            self.assertEqual({(r["kind"], r["name"]) for r in m.values()}, original)
            self.assertEqual(m, mapping(seed, True))
        self.assertNotEqual(mapping("DEADBEEF", True), mapping("12345678", True))
        self.assertTrue(
            any(
                m["I00A4"]["kind"] == "character"
                for m in [mapping(str(i), True) for i in range(20)]
            )
        )
        for l in LOCATIONS:
            self.assertEqual(mapping("seed", False)[l["key"]]["name"], l["source"])

    def test_native_census_and_non_chest_events_unchanged(self):
        found = []
        for payload, frame in source.routes.payloads.items():
            before = source.sections(payload)
            after, audit = transform(frame, before)
            found += audit
            changed = {a["section"] for a in audit}
            for si, rows in enumerate(before):
                if si not in changed:
                    self.assertEqual(rows, after[si])
            for a in audit:
                loc = next(l for l in LOCATIONS if l["key"] == a["key"])
                rows = after[a["section"]]
                grants = []
                for row in rows:
                    cs = commands(row)
                    grant = [
                        c
                        for c in cs
                        if not c[0]
                        and c[1:3] == (33, 94)
                        and b"Name" + a["key"].encode() + b"\0" in c[-1]
                    ]
                    if not grant:
                        continue
                    self.assertEqual(len(grant), 1)
                    grants += grant
                    self.assertTrue(
                        any(
                            c[0] and b"Kind" + a["key"].encode() + b"\0" in c[-1]
                            for c in cs
                        )
                    )
                    self.assertTrue(any(c[0] and b"RandoChecks\0" in c[-1] for c in cs))
                    self.assertTrue(
                        any(not c[0] and b"RandoChecks\0" in c[-1] for c in cs)
                    )
                    self.assertTrue(
                        any(
                            c[0]
                            and c[1:4] == (2, -25, loc["object"])
                            and params(c[-1], True) == [(22, expression(integer(0)))]
                            for c in cs
                        )
                    )
                self.assertEqual(len(grants), 2 * a["grants"])
                targets = Counter(c[3] for c in grants)
                save = int.from_bytes(bytes.fromhex(loc["save_ref"])[:2], "little")
                license = int.from_bytes(
                    bytes.fromhex(loc["license_ref"])[:2], "little"
                )
                self.assertEqual(targets, {save: a["grants"], license: a["grants"]})
        self.assertEqual({r["key"] for r in found}, {l["key"] for l in LOCATIONS})
        self.assertEqual(len(found), 36)
        self.assertEqual(
            sum(a["grants"] for a in found), 40
        )  # four optional help dialogs

    def test_character_messages_keep_heading_and_actual_reward_kind(self):
        from transition.events import string

        loc = next(l for l in LOCATIONS if l["source"] == "Orc")
        payload = next(p for p, f in source.routes.payloads.items() if f == loc["scene"] + 1)
        after, audit = transform(loc["scene"] + 1, source.sections(payload))
        section = next(a["section"] for a in audit if a["key"] == loc["key"])
        messages = []
        for row in after[section]:
            cs = commands(row)
            for c in cs:
                if not c[0] and c[1:3] == (32, 49) and b"NameL0B7F\0" in c[-1]:
                    self.assertTrue(any(x[0] and b"KindL0B7F\0" in x[-1] for x in cs))
                    messages.append(c[-1])
        self.assertEqual(len(messages), 2)
        self.assertTrue(any(string("\r\nCharacter unlocked!!\r\n") in m for m in messages))
        self.assertTrue(any(string("\r\nSECRET ITEM!\r\n") in m for m in messages))

    def test_export_changes_only_revealed_chest_icons_and_binds_mapping(self):
        import tempfile
        from pathlib import Path
        from menu_host.store import Store
        from menu_host.draft import Draft
        from export_native_run import BASE
        from visuals.scenery_pack import App, object_mapping
        from visuals.fusion25 import property_bank, animation_slot
        from menu_host.runtime import verify_engine
        from export_native_run import ORIGINAL

        before = App(BASE)
        ids = object_mapping(before, App(ORIGINAL).objects()[0])
        old = property_bank(before.payload(0x2256), before.payload(0x2257))
        with tempfile.TemporaryDirectory() as temp:
            d = Draft()
            d.update(items=True)
            d.seed = "0000001D"
            s = Store(Path(temp) / "profile", Path(temp) / "runs")
            with s.lock():
                s.create(1, d)
                folder, plan, c = s.resume(1)
                verify_engine(folder / "Boshy.exe", plan["game_sha256"])
                self.assertEqual(plan["rewards"], mapping(d.seed, True))
                after = App(folder / "Boshy.exe")
                for chunk in before.chunks:
                    if chunk.id not in (0x2256, 0x2257, 0x2242):
                        # Repeated frame chunks are compared in their stored order.
                        self.assertEqual(
                            [x.payload for x in before.by_id[chunk.id]],
                            [x.payload for x in after.by_id[chunk.id]],
                        )
                new = property_bank(after.payload(0x2256), after.payload(0x2257))
                allowed = {
                    ids[l["object"]]: animation_slot(old[ids[l["object"]]], 0, 0, 2)
                    for l in LOCATIONS
                }
                for i, (a, b) in enumerate(zip(old, new)):
                    restored = bytearray(b)
                    if i in allowed:
                        pos = allowed[i]
                        restored[pos : pos + 2] = a[pos : pos + 2]
                    self.assertEqual(a, bytes(restored))

    def test_seed_menu_and_tampering(self):
        from menu_host.draft import Draft

        d = Draft()
        old = d.seed
        d.update(items=True)
        self.assertNotEqual(old, d.seed)
        other = Draft()
        other.import_seed(d.shared())
        self.assertEqual(other.shared(), d.shared())
        p = dict(seed=d.seed, options=d.options, rewards=mapping(d.seed, True))
        c = configparser.ConfigParser(interpolation=None)
        c.read_dict({GROUP: settings(d.seed, True)})
        validate(p, c)
        c[GROUP]["NameI00A4"] = "Luigi"
        if p["rewards"]["I00A4"]["name"] == "Luigi":
            c[GROUP]["NameI00A4"] = "Mixer"
        with self.assertRaisesRegex(ValueError, "Changed reward"):
            validate(p, c)
        c.read_dict({GROUP: settings(d.seed, True), "RandoChecks": {"I00A4": 1}})
        validate(p, c)
        c["RandoChecks"]["I00A4"] = "2"
        with self.assertRaisesRegex(ValueError, "receipt"):
            validate(p, c)


if __name__ == "__main__":
    unittest.main()
