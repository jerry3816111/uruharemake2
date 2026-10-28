import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
LOCK = ROOT / "configs/m11_research_evidence_map_lock.json"


class M11ResearchEvidenceMapLockTests(unittest.TestCase):
    def test_locked_evidence_map_artifacts_match(self):
        payload = json.loads(LOCK.read_text(encoding="utf-8"))
        self.assertEqual(payload["scientific_result_count_created"], 0)
        for artifact in payload["artifacts"].values():
            actual = hashlib.sha256((ROOT / artifact["path"]).read_bytes()).hexdigest()
            self.assertEqual(actual, artifact["sha256"], artifact["path"])


if __name__ == "__main__":
    unittest.main()
