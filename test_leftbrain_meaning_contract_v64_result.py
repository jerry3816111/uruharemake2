import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent


class LeftBrainMeaningContractV64ResultTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = json.loads((ROOT / "reports/leftbrain_meaning_contract_v64_raw.json").read_text(encoding="utf-8"))
        cls.analysis = json.loads((ROOT / "reports/leftbrain_meaning_contract_v64_analysis.json").read_text(encoding="utf-8"))

    def test_formal_run_integrity_is_complete(self):
        self.assertEqual(self.raw["case_count"], 14)
        self.assertEqual(self.raw["model_call_count"], 28)
        self.assertEqual(self.raw["transport_attempt_count"], 28)
        self.assertEqual(self.raw["transport_error_count"], 0)
        self.assertEqual(len(self.raw["rows"]), 28)
        self.assertTrue(self.raw["preflight"]["passed"])
        self.assertFalse(self.raw["gold_in_raw"])
        self.assertFalse(self.raw["production_runtime_changed"])
        self.assertFalse(self.raw["production_memory_read_or_write"])

    def test_frozen_decision_is_negative(self):
        self.assertFalse(self.analysis["automatic_gates"]["passed"])
        self.assertEqual(
            self.analysis["decision"],
            "freeze_negative_result_and_stop_structured_meaning_contract_hypothesis",
        )
        metrics = self.analysis["metrics"]
        self.assertEqual(metrics["c0_compact_plan"]["required_hits"], 12)
        self.assertEqual(metrics["t1_structured_meaning_contract"]["required_hits"], 11)
        self.assertAlmostEqual(
            self.analysis["paired_effect"]["response_commitment_recall_delta"],
            -1 / 28,
        )

    def test_schema_compliance_did_not_imply_semantic_success(self):
        treatment = self.analysis["metrics"]["t1_structured_meaning_contract"]
        self.assertEqual(treatment["json_parse_rate"], 1.0)
        self.assertEqual(treatment["frame_schema_valid_rate"], 1.0)
        self.assertLess(treatment["response_commitment_recall"], 0.7)
        self.assertLess(treatment["required_frame_relation_recall"], 0.7)
        self.assertGreater(treatment["latency_median_seconds"], 8.0)

    def test_result_lock_binds_immutable_evidence(self):
        lock_path = ROOT / "configs/leftbrain_meaning_contract_v64_result_lock.json"
        self.assertTrue(lock_path.exists())
        lock = json.loads(lock_path.read_text(encoding="utf-8"))
        for name, artifact in lock["frozen_artifacts"].items():
            digest = hashlib.sha256((ROOT / artifact["path"]).read_bytes()).hexdigest()
            self.assertEqual(digest, artifact["sha256"], name)
        self.assertFalse(lock["authorizations"]["runtime_change"])
        self.assertFalse(lock["authorizations"]["rightbrain_realization_pilot"])


if __name__ == "__main__":
    unittest.main()
