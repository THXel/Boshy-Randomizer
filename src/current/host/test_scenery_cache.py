"""A reset cache must not leak a saved or previous room's graphics into a run."""

import copy
import unittest
from visuals import scenery_cache as cache, runtime_scenery
from transition.events import commands, global_value
import recover_boshy_routes as source


class SceneryCacheTests(unittest.TestCase):
    def test_marker_is_new_zero_initialized_application_memory(self):
        class App:
            def globals(self):
                return {"count": 25, "values": list(range(25)), "types": [0] * 25}, {
                    "values": ["old"]
                }

        cache.install(App)
        values, strings = App().globals()
        self.assertEqual(values["values"], [*range(25), 0])
        self.assertEqual(values["count"], 26)
        self.assertEqual(strings, {"values": ["old"]})

    def test_every_room_and_menu_invalidates_previous_room_after_start_actions(self):
        checked = set()
        for payload, frame in source.payloads.items():
            before = source.original_sections(payload)
            after = cache.finish(frame, before)
            self.assertEqual(after[:-1], before)
            cs = commands(after[-1][0])
            self.assertEqual(cs[0][1:3], (-3, -1))
            self.assertEqual(cs[-1][-1], global_value(cache.GLOBAL, frame))
            self.assertFalse(
                any(c[1] == 33 for c in cs), "Cache must never persist to a save"
            )
            checked.add(frame)
        self.assertEqual(checked, set(range(1, 62)))

    def test_original_objects_remain_unmodified_and_only_image_loads_are_cached(self):
        for payload, frame in source.payloads.items():
            before = source.original_sections(payload)
            scene = source.frames[frame - 1]
            after, _ = runtime_scenery.transform(
                frame, before, source.objects, scene["instances"]
            )
            for section in after:
                for row in section:
                    cs = commands(row)
                    guards = [c for c in cs if c[0] and cache.previous_frame() in c[-1]]
                    if guards:
                        self.assertTrue(all(c[1:3] == (2, 89) for c in cs if not c[0]))
            original = copy.deepcopy(source.objects)
            _, objects = runtime_scenery.convert_frame(frame, scene, source.objects)
            for oi, obj in original.items():
                self.assertEqual(objects[oi], obj)


if __name__ == "__main__":
    unittest.main()
