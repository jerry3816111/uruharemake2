import json
import unittest
from pathlib import Path

from audit_semantic_memory_recall_support_v1_evidence_contract import file_sha256


ROOT = Path(__file__).resolve().parent
PREREG = ROOT / "configs/source_preserving_memory_projection_v2_development_preregistration.json"


class SourcePreservingMemoryProjectionV2PreregistrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payload = json.loads(PREREG.read_text(encoding="utf-8"))

    def test_dataset_is_explicitly_development_only(self):
        boundary = self.payload["why_this_is_not_a_holdout"]
        self.assertEqual(boundary["status"], "exposed_official_dataset_development_only")
        self.assertEqual(boundary["retrieval_baseline_report"]["selected_question_count"], 500)
        self.assertFalse(boundary["generalization_claim_allowed"])
        self.assertFalse(boundary["official_benchmark_score_claim_allowed"])

    def test_prior_artifact_hashes_are_frozen(self):
        prior = self.payload["prior_invalidity_evidence"]
        for key in ("audit_lock", "v1_cases"):
            artifact = prior[key]
            self.assertEqual(file_sha256(ROOT / artifact["path"]), artifact["sha256"])
        retrieval = self.payload["why_this_is_not_a_holdout"]["retrieval_baseline_report"]
        self.assertEqual(file_sha256(ROOT / retrieval["path"]), retrieval["sha256"])

    def test_projection_is_the_only_changed_variable(self):
        variable = self.payload["single_changed_variable"]
        self.assertEqual(variable["name"], "candidate_evidence_representation")
        self.assertIn("official question and source sessions", variable["held_constant"])
        contract = self.payload["source_preservation_contract"]
        self.assertEqual(contract["construction_model_calls"], 0)
        self.assertEqual(contract["translation_calls"], 0)
        self.assertEqual(contract["paraphrase_calls"], 0)
        self.assertEqual(contract["summarization_calls"], 0)

    def test_projection_never_uses_gold_answer(self):
        projection = self.payload["source_preservation_contract"]["projection"]
        gate = self.payload["span_gate"]
        self.assertEqual(projection["eligible_roles"], ["user"])
        self.assertEqual(projection["top_k"], 3)
        self.assertFalse(projection["gold_answer_used"])
        self.assertFalse(projection["expected_trace_id_used"])
        self.assertFalse(gate["gold_answer_in_prompt"])
        self.assertFalse(gate["expected_trace_id_in_prompt"])

    def test_control_and_treatment_run_on_each_condition(self):
        expected_representations = ["complete_session", "source_projection"]
        conditions = self.payload["matched_conditions"]
        self.assertEqual(len(conditions), 3)
        for condition in conditions:
            self.assertEqual(condition["run_for_representations"], expected_representations)
        self.assertEqual(self.payload["staged_execution"]["maximum_total_model_calls"], 48)

    def test_success_requires_gain_and_zero_projected_false_support(self):
        gates = self.payload["success_gates"]
        self.assertEqual(gates["projected_minus_complete_target_only_support_count_at_least"], 2)
        self.assertEqual(gates["projected_target_removed_false_support_count_equals"], 0)
        self.assertEqual(gates["source_projection_exactness_rate_equals"], 1.0)

    def test_no_runtime_or_claim_is_authorized(self):
        authorization = self.payload["decision_and_authorization"]
        for key, value in authorization.items():
            if key.endswith("_authorized"):
                self.assertFalse(value, key)


if __name__ == "__main__":
    unittest.main()
