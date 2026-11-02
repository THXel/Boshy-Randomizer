"""Bank regression checks permitting only the reviewed ending packs and the solid background shade."""

from visuals.fusion25 import image_bank
from visuals.death_screen import assets
from visuals.embedded_blood import assets as blood_assets


def assert_original_banks(test, old, new):
    for chunk in (0x6668, 0x5557):
        test.assertEqual(old.payload(chunk), new.payload(chunk))
    before, _ = image_bank(old.payload(0x6666), old.payload(0x5555))
    after, _ = image_bank(new.payload(0x6666), new.payload(0x5555))
    test.assertFalse(set(before) - set(after))
    for handle, original in before.items():
        test.assertEqual(original.bytes(), after[handle].bytes(), handle)
    expected = {h: im for pack in assets().values()
                for h, im in zip(pack["handles"], pack["images"])}
    expected.update({h: im for pack in blood_assets().values()
                     for h, im in zip(pack["handles"], pack["images"])})
    from visuals.death_soul import assets as soul_assets
    soul = soul_assets()
    expected.update(zip(soul['handles'], soul['images']))
    from visuals.death_caption import assets as caption_assets
    for caption in caption_assets().values():
        expected.update(zip(caption["handles"],caption["images"]))
    from visuals.background_groups import DIM_IMAGE
    if DIM_IMAGE in after:
        from PIL import Image
        expected[DIM_IMAGE] = Image.new('RGBA', (640, 480), (0, 0, 0, 255))
    added = set(after) - set(before)
    if not added:
        return  # Historical pinned builds predate the optional death sequences.
    test.assertEqual(added, set(expected) - set(before))
    for handle in added:
        actual, original = after[handle].rgba(), expected[handle]
        test.assertEqual(actual.size, original.size)
        test.assertEqual(actual.getchannel("A").tobytes(), original.getchannel("A").tobytes())
        test.assertTrue(all(a == b for a, b in zip(actual.getdata(), original.getdata()) if b[3]))


def assert_active_extension(test, before, after, oi):
    """Only the two blood actives gain slot 18; all existing data stays exact."""
    if oi not in (105, 1032):
        test.assertEqual(before, after, oi)
        return
    import struct
    from visuals.fusion25 import animation_slot
    starts = [struct.unpack_from('<H', body, 4)[0] for body in (before, after)]
    test.assertEqual(*starts)
    start = starts[0]
    # The first DWORD is the serialized size. All fixed object properties survive.
    test.assertEqual(before[4:start], after[4:start])
    sizes = [struct.unpack_from('<H', body, start)[0] for body in (before, after)]
    test.assertEqual(before[start+sizes[0]:], after[start+sizes[1]:])
    count = struct.unpack_from('<H', before, start+2)[0]
    for slot in range(count):
        for direction in range(32):
            values=[]
            for body in (before, after):
                try:at=animation_slot(body,slot,direction,0)
                except ValueError:values.append(None)
                else:
                    n=struct.unpack_from('<H',body,at-2)[0]
                    values.append(body[at-8:at+2*n])
            test.assertEqual(*values, (oi, slot, direction))
