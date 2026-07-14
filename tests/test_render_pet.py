import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from render_pet import dinosaur_collection


class DinosaurCollectionTests(unittest.TestCase):
    def test_first_dinosaur_is_summoned_immediately(self):
        self.assertEqual(len(dinosaur_collection("demo", 0)), 1)
        self.assertEqual(len(dinosaur_collection("demo", 99)), 1)

    def test_new_dinosaur_is_summoned_every_hundred_commits(self):
        self.assertEqual(len(dinosaur_collection("demo", 100)), 2)
        self.assertEqual(len(dinosaur_collection("demo", 200)), 3)

    def test_draw_is_deterministic_for_the_same_user(self):
        first = dinosaur_collection("demo", 500)
        second = dinosaur_collection("demo", 500)
        self.assertEqual([dino["name"] for dino in first], [dino["name"] for dino in second])


if __name__ == "__main__":
    unittest.main()
