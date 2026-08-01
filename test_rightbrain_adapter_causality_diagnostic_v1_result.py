import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
LOCK = ROOT / "configs/rightbrain_adapter_causality_diagnostic_v1_result_lock.json"
RESULT = ROOT / "reports/rightbrain_adapter_causality_diagnostic_v1_result.json"
FINAL = ROOT / "reports/rightbrain_adapter_causality_diagnostic_v1_final_review.json"
FINAL_MD = ROOT / "reports/rightbrain_adapter_causality_diagnostic_v1_final_review.md"


def sha256_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class RightBrainAdapterCausalityDiagnosticV1ResultTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lock = json.loads(LOCK.read_text(encoding="utf-8"))
        cls.result = json.loads(RESULT.read_text(encoding="utf-8"))
        cls.final = json.loads(FINAL.read_text(encoding="utf-8"))

    def test_frozen_artifact_hashes_match(self):
        for artifact in self.lock["frozen_artifacts"].values():
            self.assertEqual(
                sha256_file(ROOT / artifact["path"]),
                artifact["sha256"],
                artifact["path"],
            )

    def test_formal_result_and_classification_are_preserved(self):
        self.assertEqual(self.result["status"], "valid_diagnostic")
        self.assertEqual(
            self.result["classification"],
            "both_surface_carriers_inadequate",
        )
        self.assertEqual(self.final["formal_result"], self.lock["formal_result"])

    def test_adapter_is_the_only_cross_model_difference(self):
        self.assertTrue(
            self.lock["formal_result"]["cross_model_controls_equal_except_adapter"]
        )
        states = self.result["adapter_states"]
        self.assertFalse(states["qwen25_7b_base_only"]["compat_adapter_loaded"])
        self.assertTrue(states["qwen25_7b_v10_adapter"]["compat_adapter_loaded"])
        self.assertEqual(
            self.lock["formal_result"]["strict_valid_delta_base_minus_adapter"],
            0,
        )

    def test_interrupted_attempt_is_excluded(self):
        amendment = json.loads(
            (ROOT / "configs/rightbrain_adapter_causality_diagnostic_v1_protocol_amendment.json").read_text(encoding="utf-8")
        )
        self.assertFalse(amendment["failed_attempt"]["formal_result_file_written"])
        self.assertFalse(amendment["failed_attempt"]["evidence_reused"])
        self.assertTrue(self.final["review_findings"]["failed_sequential_attempt_excluded"])

    def test_only_next_experiment_is_authorized(self):
        authorizations = self.final["authorizations"]
        self.assertTrue(authorizations["merge_diagnostic_evidence"])
        self.assertTrue(authorizations["preregister_compact_japanese_payload_experiment"])
        for field in (
            "change_production_default",
            "build_persona_blind_rating",
            "model_training",
            "sealed_holdout_unsealing",
            "formal_persona_similarity_claim",
        ):
            self.assertFalse(authorizations[field], field)

    def test_markdown_states_no_gain_and_hypothesis_boundary(self):
        markdown = FINAL_MD.read_text(encoding="utf-8")
        self.assertIn("Base-only 2/10，v10 也是 2/10", markdown)
        self.assertIn("只是待測假設", markdown)
        self.assertIn("不得同時換模型", markdown)


if __name__ == "__main__":
    unittest.main()
