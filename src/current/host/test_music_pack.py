"""Category boundaries and byte-exact native soundbank regressions."""

import hashlib, json, struct, unittest
from pathlib import Path
from music.bank import read, write
from music.soundtrack import mapping, pack_rows, prepare, PACKS, SOURCE_TRACKS, cue_kind
from visuals.scenery_pack import App
from visuals.fusion25 import rebuild
from build_profiles import executable, profile, LAB

OUT = LAB.parents[1] / "outputs/Fusion-Music-20261024"
PACKROOT = Path("/home/thxel/.local/share/boshy-randomizer/soundpacks")


class MusicPackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.builds = []
        # Archived builds predate the fourth pack; current mappings below cover all packs.
        for pack in ("original", "kamilia3", "wannafest22"):
            before, after = App(executable("blood-" + pack)), App(
                executable("music-" + pack)
            )
            a, n = read(before.payload(0x6668), before.payload(0x5557))
            b, m = read(after.payload(0x6668), after.payload(0x5557))
            cls.builds.append(
                (
                    pack,
                    before,
                    after,
                    a,
                    b,
                    json.loads((OUT / (pack + "-audit.json")).read_text()),
                )
            )

    def test_category_separation_for_600_mappings(self):
        for pack in PACKS:
            rows = pack_rows(PACKROOT / pack, pack) if pack != "original" else None
            kinds = (
                {r["file"]: r["kind"] for r in rows}
                if rows
                else {n: cue_kind(n) for n in SOURCE_TRACKS}
            )
            for seed in range(200):
                swaps = mapping(str(seed), pack, rows)
                self.assertEqual(set(swaps), set(SOURCE_TRACKS))
                self.assertTrue(all(cue_kind(c) == kinds[t] for c, t in swaps.items()))
                self.assertNotIn("Do teh mario!", swaps.values())
                if rows:
                    self.assertEqual(
                        swaps, mapping(str(seed), pack, list(reversed(rows)))
                    )

    def test_boss_pool_does_not_change_level_choices(self):
        rows = pack_rows(PACKROOT / "kamilia3", "kamilia3")
        a = mapping("independent", "kamilia3", rows)
        b = mapping("independent", "kamilia3", rows + [dict(file="extra", kind="boss")])
        self.assertEqual(
            {c: t for c, t in a.items() if cue_kind(c) == "level"},
            {c: t for c, t in b.items() if cue_kind(c) == "level"},
        )

    def test_all_426_non_music_records_remain_byte_identical(self):
        for pack, before, after, a, b, audit in self.builds:
            self.assertEqual(set(a), set(b))
            effects = [h for h, s in a.items() if s.name not in SOURCE_TRACKS]
            self.assertEqual(len(effects), 426)
            for h in effects:
                self.assertEqual(a[h].stored, b[h].stored, (pack, a[h].name))
            for h in a:
                self.assertEqual(a[h].name, b[h].name)
                head = bytearray(b[h].header)
                head[12:16] = a[h].header[12:16]
                head[28:32] = a[h].header[28:32]
                self.assertEqual(bytes(head), a[h].header)

    def test_exact_music_bytes_and_audit(self):
        for pack, before, after, a, b, audit in self.builds:
            self.assertEqual(hashlib.sha256(after.data).hexdigest(), audit["sha256"])
            self.assertEqual(len(audit["changed"]), 45)
            byname = {s.name: s for s in a.values()}
            for row in audit["changed"]:
                data = (
                    byname[row["target"]].audio
                    if pack == "original"
                    else (PACKROOT / pack / row["target"]).read_bytes()
                )
                self.assertEqual(data, b[row["handle"]].audio)
                self.assertEqual(hashlib.sha256(data).hexdigest(), row["audio_sha256"])

    def test_events_graphics_engine_and_other_chunks_are_unchanged(self):
        for pack, before, after, a, b, audit in self.builds:
            self.assertEqual(
                before.data[: before.chunks[0].offset],
                after.data[: after.chunks[0].offset],
            )
            self.assertEqual(
                [c.id for c in before.chunks], [c.id for c in after.chunks]
            )
            for x, y in zip(before.chunks, after.chunks):
                if x.id not in (0x6668, 0x5557, 0x2242):
                    self.assertEqual(
                        before.data[x.offset : x.offset + 8 + x.size],
                        after.data[y.offset : y.offset + 8 + y.size],
                        (pack, hex(x.id)),
                    )

    def test_soundbank_roundtrip(self):
        for _, before, after, a, b, _ in self.builds:
            for app, sounds in [(before, a), (after, b)]:
                bank, offsets = write(sounds, len(app.payload(0x5557)) // 4)
                self.assertEqual(bank, app.payload(0x6668))
                self.assertEqual(offsets, app.payload(0x5557))

    def test_corrupt_index_truncation_and_bank_permissions_rejected(self):
        app = self.builds[0][1]
        data, offsets = app.payload(0x6668), app.payload(0x5557)
        for bad, idx in [
            (data[:-1], offsets),
            (data, bytes(len(offsets))),
            (data[:20], offsets),
        ]:
            with self.assertRaises(ValueError):
                read(bad, idx)
        with self.assertRaises(ValueError):
            rebuild(app, {0x3333: b""}, sound_bank=True)
        with self.assertRaises(ValueError):
            rebuild(app, {0x6668: b""})

    def test_disabled_music_is_exact_base_and_wrong_hash_fails(self):
        path = executable("blood-original")
        expected = profile("blood-original")["sha256"]
        raw, audit = prepare(path, expected, "off", "original", enabled=False)
        self.assertEqual(raw, path.read_bytes())
        self.assertFalse(audit["enabled"])
        with self.assertRaises(ValueError):
            prepare(path, "0" * 64, "bad", "original")


if __name__ == "__main__":
    unittest.main()
