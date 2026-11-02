"""Regressions for native death rendering, music ownership and optional assets."""
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch
from PIL import Image
from app_paths import SOUNDPACKS
from music.pack_health import PackHealth, PackUnavailable, death_audio
from native_menu.presentation import Presentation, write_config, UNAVAILABLE
from native_menu.presentation_events import GROUP, INPUT_FILE, VIEW_FILE
from native_menu.preferences import save_preferences, load_preferences
from native_menu.classic import ClassicModel
from menu_host.store import Store, save
from visuals.death_graphics import trim, encode
from visuals.embedded_blood import raw_image
from transition.events import commands, expression, integer
from transition.router import params


class DeathPolishTests(unittest.TestCase):
    def test_trimming_preserves_every_visible_pixel_and_world_hotspot(self):
        from visuals.death_soul import assets
        data = assets()
        source = SOUNDPACKS / "undertale"
        rows = json.loads((source/"pack.json").read_text())["death_visuals"]["soul"]["frames"]
        original_area = final_area = 0
        for row, image, origin in zip(rows, data["images"], data["origins"]):
            with Image.open(source/row["file"]) as expected:
                rebuilt = Image.new("RGBA", expected.size)
                rebuilt.alpha_composite(image, (320-origin[0], 240-origin[1]))
                self.assertEqual(rebuilt.tobytes(), expected.convert("RGBA").tobytes())
                original_area += expected.width * expected.height
                final_area += image.width * image.height
        self.assertLess(final_area, original_area // 5)

    def test_opaque_image_omits_alpha_without_making_black_transparent(self):
        import struct
        image = Image.new("RGBA", (640,480), "black")
        image.putpixel((20,20), (255,255,255,255))
        raw = encode(image,(0,0))
        self.assertEqual(raw[17], 0)
        key = struct.unpack_from("<I",raw,28)[0]
        self.assertNotIn(key, (0,0xffffff))
        self.assertEqual(len(raw),32+640*480*3)
        translucent = Image.new("RGBA", (32,32), (255,0,0,128))
        self.assertEqual(encode(translucent,(8,8)),raw_image(translucent,(8,8)))

    def test_loop_starts_once_on_the_original_death_channel_after_intro(self):
        from visuals.death_screen import transform, OBJECT
        import recover_boshy_classic as source
        for number in (3, 23, 45, 53):
            payload = next(p for p,n in source.routes.payloads.items() if n==number)
            after,_ = transform(number,source.sections(payload),source.routes.objects,source.routes.frames[number-1]["instances"])
            loops = [row for section in after for row in section if any(not c[0] and c[1:3]==(-2,29) for c in commands(row)) and b"undertale-loop.ogg" in row]
            self.assertEqual(len(loops),1)
            cs = commands(loops[0])
            self.assertTrue(any(c[0] and c[1:3]==(-2,-8) for c in cs))
            play = next(c for c in cs if not c[0] and c[1:3]==(-2,29))
            self.assertEqual([p[1] for p in params(play[-1])][1:], [expression(integer(3)), expression(integer(0),27)])
            self.assertTrue(any(not c[0] and c[1:4]==(2,31,OBJECT) for c in cs))

    def test_original_starts_without_any_optional_pack_and_failed_selection_recovers(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);folder=root/"working";folder.mkdir()
            store=Store(root/"profile",runs=root/"runs");model=ClassicModel(store)
            c=SimpleNamespace(folder=folder,store=store,model=model,mail=Mock(),active_slot=None)
            seed=model.draft.shared()
            with patch("visuals.embedded_blood.PACK_ROOT",root/"missing"), patch("visuals.death_screen.PACK_ROOT",root/"missing"):
                p=Presentation(c)
                self.assertEqual(p.pack,"original")
                write_config(folder/INPUT_FILE,{GROUP:dict(Language=1,Pack=3)})
                p.tick()
                self.assertEqual(p.pack,"original")
                self.assertIn("missing or damaged",p.notice)
                self.assertEqual(load_preferences(store.root)["presentation_pack"],"original")
                self.assertEqual(save(folder/VIEW_FILE).getint("FusionBloodV1","Animation"),0)
                self.assertEqual(save(folder/INPUT_FILE).getint(GROUP,"Pack"),0)
                self.assertEqual(model.draft.shared(),seed)
                # Restart with a formerly selected, now missing pack also works.
                save_preferences(store.root,presentation_pack="wannafest22")
                restored=Presentation(c)
                self.assertEqual(restored.pack,"original")
                self.assertIn("WannaFest 22",restored.notice)

    def test_changed_music_invalidates_health_cache_and_repaired_pack_can_be_used(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/"undertale";shutil.copytree(SOUNDPACKS/"undertale",root)
            health=PackHealth();health.check(root,"undertale")
            path=root/"mus_ruins.ogg";original=path.read_bytes()
            path.write_bytes(b"broken"+original[6:])
            with self.assertRaises(PackUnavailable):health.check(root,"undertale")
            path.write_bytes(original);health.check(root,"undertale")
            # Missing unselected packs cannot affect this selected pack.
            health.check(root,"undertale")
            self.assertEqual(set(death_audio(root,"undertale")),{".wav","-loop.ogg"})

    def test_every_supported_language_has_an_actionable_pack_notice(self):
        self.assertEqual(len(UNAVAILABLE),5)
        self.assertTrue(all("{pack}" in s and "Original" in s for s in UNAVAILABLE))


class LocalizedCaptionTests(unittest.TestCase):
    def test_native_caption_languages_have_compact_final_text_and_exact_timing(self):
        from visuals.death_caption import assets
        from music.death_text import LANGUAGES, MESSAGES, animation
        from music.import_undertale import FULL_TICK
        captions=assets()
        self.assertEqual(set(captions),set(LANGUAGES))
        self.assertEqual(animation("unknown"),animation("en"))
        finals=set()
        for language,data in captions.items():
            self.assertEqual(data["animation"],animation(language))
            self.assertTrue(all(image.width<=400 and image.height<=80 for image in data["images"]))
            self.assertIsNone(data["images"][0].getchannel("A").getbbox())
            self.assertIsNotNone(data["images"][-1].getchannel("A").getbbox())
            self.assertEqual(len(data["frames"]),FULL_TICK+3*len(MESSAGES[language])+1)
            self.assertEqual(data["loop"],len(data["frames"])-1)
            finals.add(data["images"][-1].tobytes())
        self.assertEqual(len(finals),5)

    def test_language_preference_selects_caption_without_touching_run_seed(self):
        from music.death_text import LANGUAGES, animation
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);folder=root/"working";folder.mkdir()
            store=Store(root/"profile",runs=root/"runs");model=ClassicModel(store)
            c=SimpleNamespace(folder=folder,store=store,model=model,mail=Mock(),active_slot=None)
            save_preferences(store.root,presentation_pack="undertale")
            p=Presentation(c);seed=model.draft.shared()
            for index,language in enumerate(LANGUAGES):
                write_config(folder/INPUT_FILE,{GROUP:dict(Language=index,Pack=3)})
                p.tick()
                self.assertEqual(save(folder/VIEW_FILE).getint("FusionBloodV1","CaptionAnimation"),animation(language))
                self.assertEqual(model.draft.shared(),seed)
                self.assertEqual(Presentation(c).language,language)
