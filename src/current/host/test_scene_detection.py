import unittest
from pathlib import Path
from PIL import Image
from scene_detection import is_slot_menu

ROOT = Path(__file__).resolve().parents[2]


class SceneDetectionTests(unittest.TestCase):
    def test_menu_vs_bright_green_greens(self):
        ref = Image.open(
            ROOT / "outputs/Fusion-Baseline-20261023/original-checkpoint-slot.png"
        ).convert("RGB")
        self.assertTrue(is_slot_menu(ref, ref))
        self.assertFalse(
            is_slot_menu(Image.new("RGB", (640, 480), (160, 230, 255)), ref)
        )
        gameplay = Image.open(
            ROOT
            / "outputs/Fusion-Routes-20261023/live-split-kracko/green-greens-start.png"
        ).convert("RGB")
        self.assertFalse(is_slot_menu(gameplay, ref))


if __name__ == "__main__":
    unittest.main()
