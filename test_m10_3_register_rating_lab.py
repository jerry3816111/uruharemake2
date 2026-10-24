import inspect
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import uruha_register_rating_lab as rating_lab


class M103RegisterRatingLabTests(unittest.TestCase):
    def test_collection_surface_never_loads_or_names_hidden_key(self):
        source = inspect.getsource(rating_lab)
        self.assertNotIn("m10_2_behavior_preserving_register_blind_key", source)
        html = rating_lab.render_blind_rating_item("m10-2-blind-012")
        self.assertIn("CANDIDATE A", html)
        self.assertIn("CANDIDATE B", html)
        self.assertNotIn("S0_ONE_PASS", html)
        self.assertNotIn("S1_REGISTER_REPAIR", html)

    def test_save_requires_human_and_key_unseen_attestations(self):
        with tempfile.TemporaryDirectory() as temp_dir, patch.object(
            rating_lab, "RATINGS_DIR", Path(temp_dir)
        ):
            status, _ = rating_lab.save_blind_rating(
                "rater-one",
                "m10-2-blind-001",
                5,
                5,
                5,
                5,
                4,
                5,
                5,
                5,
                "B",
                False,
                True,
                "",
            )
            self.assertIn("未保存", status)
            self.assertFalse(list(Path(temp_dir).glob("ratings-*.jsonl")))

    def test_save_stores_only_hash_and_isolated_rating_record(self):
        with tempfile.TemporaryDirectory() as temp_dir, patch.object(
            rating_lab, "RATINGS_DIR", Path(temp_dir)
        ):
            status, progress = rating_lab.save_blind_rating(
                "rater-one",
                "m10-2-blind-001",
                5,
                5,
                5,
                5,
                4,
                5,
                5,
                5,
                "B",
                True,
                True,
                "natural but preserve behavior",
            )
            self.assertIn("已保存", status)
            self.assertIn("1/18", progress)
            files = list(Path(temp_dir).glob("ratings-*.jsonl"))
            self.assertEqual(len(files), 1)
            record = json.loads(files[0].read_text(encoding="utf-8"))
            self.assertNotIn("rater_id", record)
            self.assertNotIn("rater-one", files[0].read_text(encoding="utf-8"))
            self.assertEqual(len(record["rater_id_hash"]), 64)
            self.assertEqual(record["item_id"], "m10-2-blind-001")


if __name__ == "__main__":
    unittest.main()
