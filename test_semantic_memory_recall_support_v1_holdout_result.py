import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
LOCK = ROOT / "configs/semantic_memory_recall_support_v1_holdout_result_lock.json"


def file_sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class SemanticMemoryRecallSupportV1HoldoutResultTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lock = json.loads(LOCK.read_text(encoding="utf-8"))
        cls.report = json.loads(
            (ROOT / cls.lock["artifacts"]["report_json"]["path"]).read_text(
                encoding="utf-8"
            )
        )

    def test_all_locked_artifacts_match(self):
        for artifact in self.lock["artifacts"].values():
            self.assertEqual(file_sha256(ROOT / artifact["path"]), artifact["sha256"])

    def test_holdout_failure_is_not_relabelled_as_a_pass(self):
        self.assertEqual(self.lock["status"], "holdout_rejected_locked")
        self.assertEqual(self.report["decision"], "holdout_reject_or_inconclusive")
        self.assertFalse(all(self.report["gates"].values()))
        self.assertEqual(self.lock["observed"]["target_removed_selection_count"], 6)

    def test_rejected_path_remains_disabled(self):
        authorization = self.lock["authorization"]
        self.assertFalse(authorization["production_default_enablement"])
        self.assertFalse(authorization["runtime_enablement"])
        self.assertTrue(authorization["new_disjoint_holdout_required"])

    def test_result_does_not_overclaim(self):
        authorization = self.lock["authorization"]
        self.assertFalse(authorization["benchmark_score_claim"])
        self.assertFalse(authorization["persona_similarity_claim"])
        self.assertFalse(authorization["human_memory_equivalence_claim"])


if __name__ == "__main__":
    unittest.main()
