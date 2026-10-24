import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
LOCK = ROOT / "configs/m10_3_register_human_eval_instrument_lock.json"


class M103RegisterInstrumentLockTests(unittest.TestCase):
    def test_every_frozen_instrument_artifact_matches_hash(self):
        payload = json.loads(LOCK.read_text(encoding="utf-8"))
        self.assertEqual(payload["human_rating_count_at_lock"], 0)
        self.assertEqual(payload["complete_human_rater_count_at_lock"], 0)
        for artifact in payload["artifacts"].values():
            actual = hashlib.sha256((ROOT / artifact["path"]).read_bytes()).hexdigest()
            self.assertEqual(actual, artifact["sha256"], artifact["path"])


if __name__ == "__main__":
    unittest.main()
