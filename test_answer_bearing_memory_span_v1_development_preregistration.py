import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PREREG = ROOT / "configs/answer_bearing_memory_span_v1_development_preregistration.json"


def file_sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class AnswerBearingMemorySpanV1PreregistrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payload = json.loads(PREREG.read_text(encoding="utf-8"))

    def test_consumed_inputs_are_hash_locked(self):
        data = self.payload["development_data"]
        self.assertEqual(
            file_sha256(ROOT / data["cases_path"]), data["cases_sha256"]
        )
        self.assertEqual(
            file_sha256(ROOT / data["baseline_raw_path"]),
            data["baseline_raw_sha256"],
        )
        self.assertEqual(data["question_count"], 8)
        self.assertEqual(data["decision_count"], 32)
        self.assertFalse(data["promotion_evidence_allowed"])

    def test_exactly_one_causal_variable_is_declared(self):
        variable = self.payload["single_changed_variable"]
        self.assertEqual(variable["name"], "recall_authorization_gate")
        self.assertIn("full-record speakability policy", variable["unchanged"])
        self.assertIn("memory candidates and scores", variable["unchanged"])

    def test_four_interventions_are_frozen(self):
        conditions = self.payload["conditions"]
        self.assertEqual(
            [row["id"] for row in conditions],
            [
                "c0_intact_target_and_hard_negative",
                "t1_remove_exact_target",
                "t2_replace_exact_target",
                "n1_remove_exact_hard_negative",
            ],
        )
        self.assertIsNone(conditions[1]["expected_selection"])

    def test_result_cannot_authorize_runtime(self):
        boundary = self.payload["evidence_boundary"]
        self.assertFalse(boundary["runtime_change_authorized"])
        self.assertFalse(boundary["production_enablement_authorized"])
        self.assertEqual(
            boundary["passing_action"],
            "Preregister and run one new disjoint full-pipeline holdout.",
        )

    def test_model_and_fail_closed_contract_are_frozen(self):
        inference = self.payload["inference"]
        self.assertEqual(inference["model"], "qwen3.5:4b")
        self.assertEqual(inference["temperature"], 0)
        self.assertEqual(len(inference["model_digest"]), 64)
        rules = self.payload["span_contract"]["fail_closed_rules"]
        self.assertTrue(any("official answers" in rule for rule in rules))


if __name__ == "__main__":
    unittest.main()
