import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
LOCK = ROOT / "configs/semantic_memory_recall_support_v1_development_result_lock.json"


def file_sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class SemanticMemoryRecallSupportV1DevelopmentResultTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lock = json.loads(LOCK.read_text(encoding="utf-8"))
        cls.report = json.loads(
            (ROOT / cls.lock["artifacts"]["report_json"]["path"]).read_text(
                encoding="utf-8"
            )
        )

    def test_locked_artifacts_match(self):
        for artifact in self.lock["artifacts"].values():
            self.assertEqual(file_sha256(ROOT / artifact["path"]), artifact["sha256"])

    def test_all_preregistered_development_gates_passed(self):
        self.assertEqual(self.lock["status"], "development_pass_locked")
        self.assertTrue(all(self.report["gates"].values()))
        self.assertEqual(
            self.report["decision"],
            "development_pass_requires_fresh_holdout",
        )

    def test_only_fresh_holdout_is_authorized(self):
        authorization = self.lock["authorization"]
        self.assertTrue(authorization["fresh_disjoint_holdout"])
        self.assertFalse(authorization["production_default_enablement"])
        self.assertFalse(authorization["benchmark_claim"])
        self.assertFalse(authorization["persona_similarity_claim"])
        self.assertFalse(authorization["human_memory_equivalence_claim"])


if __name__ == "__main__":
    unittest.main()
