"""Camera-only suppression, seed compatibility and saved option integrity."""

import configparser
import struct
import tempfile
import unittest
from functools import partial
from pathlib import Path
from unittest.mock import patch
from gameplay import screen_shake as shake
from menu_host.draft import Draft
from menu_host.store import Store
from export_native_run import export
from native_menu import builds
from menu_host.labels import LANGUAGES, text
from seed_codec import defaults, pack, unpack, FIELDS, FIELDS_V8
from run_extras import normalize, upgrade, flags, EXTRAS
from transition.events import commands, event, parameter
from transition.router import params
import recover_boshy_dynamic as source


class ScreenShakeTests(unittest.TestCase):
    def test_old_seed_bytes_and_defaults_remain_frozen(self):
        frozen = "BR12-AQm5AAAAAAAAAAASNFZ4AOJi4pA"
        self.assertEqual(pack("12345678", defaults(), 20261025, bytes(8)), frozen)
        self.assertEqual(unpack(frozen)[1], defaults())
        self.assertEqual(FIELDS_V8[:-1], FIELDS)
        old = defaults()
        before = dict(old["extras"])
        self.assertEqual(normalize(before), before)
        self.assertFalse(upgrade(old)[shake.OPTION])
        self.assertEqual(old["extras"]["version"], 8)
        legacy6 = dict(before, version=6)
        for k in (
            "sprite_backgrounds",
            "sprite_decor",
            "sprite_tiles",
            "sprite_actors",
            "sprite_dim",
        ):
            del legacy6[k]
        self.assertEqual(normalize(legacy6), legacy6)

    def test_seed_roundtrip_toggle_renews_and_flag_does_not_collide(self):
        d = Draft()
        self.assertFalse(d.options["extras"][shake.OPTION])
        old = d.seed
        d.update(no_screen_shaking=True)
        self.assertNotEqual(old, d.seed)
        e = Draft()
        e.import_seed(d.shared())
        self.assertEqual(d.shared(), e.shared())
        self.assertTrue(e.options["extras"][shake.OPTION])
        for key, *_ in EXTRAS:
            options = dict(characters=False, extras={key: True, "version": 8})
            self.assertEqual(bool(flags(options) & 65536), key == shake.OPTION)
        for lang in LANGUAGES:
            self.assertNotIn(text(shake.OPTION, lang), ("", shake.OPTION))

    def test_only_camera_offset_tokens_change_in_all_original_consumers(self):
        frames = set()
        total = 0
        shakers = {
            oi
            for oi, obj in source.routes.objects.items()
            if obj["name"] == "Screen Shaker"
        }
        for payload, frame in source.routes.payloads.items():
            before = source.classic.sections(payload)
            after, audit = shake.transform(
                frame,
                before,
                source.routes.objects,
                source.routes.frames[frame - 1]["instances"],
            )
            changed = {(a["section"], a["row"]): a for a in audit}
            self.assertEqual(len(before), len(after))
            for si, (oldrows, newrows) in enumerate(zip(before, after)):
                self.assertEqual(len(oldrows), len(newrows))
                for ri, (old, new) in enumerate(zip(oldrows, newrows)):
                    # Inventory all expression readers independently, not just
                    # viewport actions: fail if another shake consumer appears.
                    for cond, kind, code, oi, raw in commands(old):
                        for pk, p in params(raw, cond):
                            if pk not in (22, 23, 45):
                                continue
                            for tk, tc, token in shake.tokens(p[6:-4]):
                                if shake.offset_token(tk, tc, token, shakers):
                                    self.assertFalse(cond)
                                    self.assertEqual((kind, code), (34, 83))
                                    self.assertIn((si, ri), changed)
                    if (si, ri) not in changed:
                        self.assertEqual(old, new)
                        continue
                    a = changed[si, ri]
                    frames.add(frame)
                    total += a["offsets"]
                    # Undo only known offset wrappers; every other byte,
                    # condition, action, order and parameter must be original.
                    restored = []
                    for cond, kind, code, oi, raw in commands(new):
                        ps = []
                        for pk, p in params(raw, cond):
                            if (
                                not cond
                                and (kind, code) == (34, 83)
                                and pk in (22, 23, 45)
                            ):
                                data = p[6:-4]
                                for tk, tc, t in list(shake.tokens(data)):
                                    if shake.offset_token(tk, tc, t, shakers):
                                        data = data.replace(
                                            shake.gated_offset(t, a["ini"]), t
                                        )
                                p = parameter(pk, p[4:6] + data + p[-4:])
                            ps.append(p)
                        h = bytearray(raw[: 16 if cond else 14])
                        body = b"".join(ps)
                        struct.pack_into("<H", h, 0, len(h) + len(body))
                        restored.append((cond, bytes(h) + body))
                    self.assertEqual(
                        old,
                        event(
                            new,
                            [r for c, r in restored if c],
                            [r for c, r in restored if not c],
                        ),
                    )
        self.assertEqual(total, 54)
        self.assertEqual(len(frames), 26)
        self.assertTrue({4, 14, 46, 60}.issubset(frames))

    def test_missing_old_settings_are_off_and_tampering_is_rejected(self):
        p = dict(options=defaults())
        c = configparser.ConfigParser()
        shake.validate(p, c)
        p["options"]["extras"].update(version=8, no_screen_shaking=True)
        with self.assertRaisesRegex(ValueError, "newer"):
            shake.validate(p, c)
        p["screen_shake_schema"] = 1
        c.read_dict({shake.GROUP: shake.settings(p["options"]["extras"])})
        shake.validate(p, c)
        c[shake.GROUP]["Disabled"] = "0"
        with self.assertRaisesRegex(ValueError, "settings"):
            shake.validate(p, c)

    def test_export_rejects_old_build_and_roundtrips_native_save(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            d = Draft()
            d.update(no_screen_shaking=True)
            with patch.object(builds, "DYNAMIC_SCREEN_SHAKE", False):
                with self.assertRaisesRegex(ValueError, "newer native build"):
                    export(d.shared(), root / "unsupported", dynamic=True)
            if not builds.DYNAMIC_SCREEN_SHAKE:
                self.skipTest("Compiled camera patch not yet pinned")
            store = Store(
                root / "p", root / "r", exporter=partial(export, dynamic=True)
            )
            with store.lock():
                store.create(1, d)
                folder, plan, cfg = store.resume(1)
                self.assertEqual(cfg.getint(shake.GROUP, shake.KEY), 1)
                self.assertEqual(plan["screen_shake_schema"], 1)
                shake.validate(plan, cfg)


if __name__ == "__main__":
    unittest.main()
