import configparser, json, unittest
from pathlib import Path
from export_route_probe import plan, save_text, STAGES, GROUP, ROOT


class RouteExportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.shared = json.loads(
            (
                ROOT / "outputs/Fusion-FrameLinks-20261023/seed-mario/plan.json"
            ).read_text()
        )["shared_seed"]

    def test_exact_seed_route_and_split_stage_identity(self):
        p = plan(self.shared, "verified", "verified", "boss6.ini")
        self.assertEqual(
            p["route"],
            ["save1.ini", "boss6.ini", "save4.ini", "save7.ini", "boss_solgryn.ini"],
        )
        c = configparser.ConfigParser()
        c.read_string(save_text(p))
        self.assertEqual(c.getint(GROUP, "CurrentStage"), STAGES["boss6.ini"]["id"])
        for source, target in zip(p["route"], p["route"][1:]):
            sid = str(STAGES[source]["id"])
            dst = STAGES[target]
            self.assertEqual(c.getint(GROUP, "NextId" + sid), dst["id"])
            self.assertEqual(c.getint(GROUP, "NextFrame" + sid), dst["frame"])
            self.assertEqual(c.getint(GROUP, "Done" + sid), 0)
        self.assertNotEqual(STAGES["save2.ini"]["id"], STAGES["boss2.ini"]["id"])
        self.assertEqual(STAGES["save2.ini"]["frame"], STAGES["boss2.ini"]["frame"])

    def test_start_selection_does_not_mark_previous_stages_complete(self):
        p = plan(self.shared, "verified", "verified", "save7.ini")
        c = configparser.ConfigParser()
        c.read_string(save_text(p))
        self.assertEqual(p["source_index"], 3)
        self.assertTrue(
            all(int(v) == 0 for k, v in c[GROUP].items() if k.startswith("done"))
        )
        self.assertIn("no_sprite_music_or_item", p["scope"])

    def test_wrong_build_or_source_fails_closed(self):
        for sha, source in [("wrong", "boss6.ini"), ("verified", "boss2.ini")]:
            with self.assertRaises(ValueError):
                plan(self.shared, sha, "verified", source)

    def test_binding_changes_with_start_station(self):
        a = plan(self.shared, "verified", "verified", "boss6.ini")
        b = plan(self.shared, "verified", "verified", "save4.ini")
        self.assertNotEqual(a["binding"], b["binding"])


if __name__ == "__main__":
    unittest.main()
