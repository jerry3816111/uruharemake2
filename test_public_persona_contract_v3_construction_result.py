import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
RESULT_LOCK_PATH = ROOT / "configs/public_persona_contract_v3_construction_result_lock.json"
REPORT_PATH = ROOT / "reports/public_persona_contract_v3_construction.json"


class PublicPersonaContractV3ConstructionResultTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lock = json.loads(RESULT_LOCK_PATH.read_text(encoding="utf-8"))
        cls.report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))

    def test_locked_artifact_hashes_match(self):
        for artifact in self.lock["artifacts"].values():
            path = ROOT / artifact["path"]
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), artifact["sha256"])

    def test_result_is_a_pass_with_the_locked_decision(self):
        self.assertTrue(self.report["passed"])
        self.assertEqual(self.report["decision"], self.lock["decision"])
        self.assertEqual(self.report["summary"], self.lock["summary"])

    def test_current_input_hashes_match_report(self):
        input_paths = {
            "dataset": ROOT / "datasets/public_persona_contract_v3_development.json",
            "preregistration": ROOT / "configs/public_persona_contract_v3_preregistration.json",
            "v2_dataset": ROOT / "datasets/public_persona_observations_v2.json",
            "v2_result_lock": ROOT / "configs/public_persona_observation_v2_result_lock.json",
        }
        for name, path in input_paths.items():
            self.assertEqual(
                hashlib.sha256(path.read_bytes()).hexdigest(),
                self.report["inputs"][name]["sha256"],
            )

    def test_holdout_and_training_remain_absent(self):
        summary = self.report["summary"]
        self.assertEqual(summary["holdout_content_reviewed_count"], 0)
        self.assertEqual(summary["holdout_label_available_count"], 0)
        self.assertEqual(summary["training_authorized_count"], 0)

    def test_dangerous_authorizations_remain_false(self):
        authorizations = self.report["authorizations"]
        for name in (
            "context_perception_experiment",
            "holdout_unsealing",
            "runtime_default_enable",
            "training",
            "persona_fidelity_claim",
        ):
            self.assertFalse(authorizations[name])
        self.assertEqual(authorizations, self.lock["authorizations"])


if __name__ == "__main__":
    unittest.main()
