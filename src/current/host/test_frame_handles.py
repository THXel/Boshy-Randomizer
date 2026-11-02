import struct, unittest
from recovery.frame_handles import mapping, rewrite_sections
from recover_boshy_transition import app, original_sections, walk_chunks
from transition.events import commands


class FrameHandleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.table, cls.handles, cls.aliases = mapping(app.payload(0x222B), 61)

    def test_noncontiguous_original_lookup_preserved(self):
        self.assertEqual(len(self.table), 62)
        self.assertEqual(len(set(self.handles)), 61)
        self.assertEqual(self.aliases, {4: 2})
        self.assertEqual(self.handles[10], 12)  # Mario's literal 12 means VVVVVV.
        for position, handle in enumerate(self.handles):
            self.assertEqual(self.table[handle], position)

    def test_every_original_literal_keeps_its_destination(self):
        count = 0
        for chunk in app.by_id[0x3333]:
            kids, _, _ = walk_chunks(
                chunk.payload, 0, len(chunk.payload), keep_payload=True
            )
            original = original_sections(
                next(k.payload for k in kids if k.id == 0x333D)
            )
            result, audit = rewrite_sections(original, self.aliases, self.table)
            self.assertEqual(
                original, result
            )  # This game has no live alias references.
            for literal in audit["literal_destinations"]:
                canonical = self.aliases.get(literal["handle"], literal["handle"])
                self.assertEqual(
                    self.handles.index(canonical) + 1, literal["destination_frame"]
                )
                count += 1
        self.assertGreater(count, 400)

    def test_alias_references_are_equivalent(self):
        from transition.events import action, parameter, event

        command = action(-3, 2, 0, [parameter(26, struct.pack("<I", 4))])
        template = struct.pack("<hBB", -14, 0, 0) + bytes(10)
        row = event(template, [], [command])
        fixed, audit = rewrite_sections([[row]], self.aliases, self.table)
        self.assertEqual(
            struct.unpack_from("<I", commands(fixed[0][0])[0][-1], 18)[0], 2
        )
        self.assertEqual(audit["literal_destinations"][0]["destination_frame"], 1)

    def test_incomplete_or_unknown_maps_rejected(self):
        for data, count in [
            (b"\x00", 1),
            (struct.pack("<HH", 0, 0), 2),
            (struct.pack("<HH", 0, 3), 2),
        ]:
            with self.assertRaises(ValueError):
                mapping(data, count)


if __name__ == "__main__":
    unittest.main()
