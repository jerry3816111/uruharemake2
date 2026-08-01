import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
REPORT_JSON = ROOT / "reports/public_persona_fidelity_eval_v1_construction.json"
REPORT_MD = ROOT / "reports/public_persona_fidelity_eval_v1_construction.md"
HARNESS_LOCK = ROOT / "configs/public_persona_fidelity_eval_v1_harness_lock.json"
RESULT_LOCK = ROOT / "configs/public_persona_fidelity_eval_v1_result_lock.json"


class PublicPersonaFidelityEvalV1ResultTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = json.loads(REPORT_JSON.read_text(encoding="utf-8"))
        cls.lock = json.loads(RESULT_LOCK.read_text(encoding="utf-8"))

    def test_result_artifacts_match_lock(self):
        for artifact in self.lock["frozen_artifacts"].values():
            path = ROOT / artifact["path"]
            self.assertEqual(
                hashlib.sha256(path.read_bytes()).hexdigest(), artifact["sha256"]
            )

    def test_protocol_passes_without_upgrading_readiness_or_claim(self):
        self.assertTrue(self.report["protocol_passed"])
        self.assertFalse(self.report["formal_execution_ready"])
        self.assertFalse(self.report["persona_score_computed"])
        self.assertEqual(
            self.report["decision"],
            "authorize_provenance_only_reference_manifest_and_consented_rater_protocol_construction",
        )
        self.assertEqual(self.report["summary"]["protocol_check_pass_count"], 17)
        self.assertEqual(self.report["summary"]["protocol_check_count"], 17)
        self.assertEqual(self.report["summary"]["readiness_check_pass_count"], 1)
        self.assertEqual(self.report["summary"]["readiness_check_count"], 19)
        self.assertEqual(self.report["violations"], {})

    def test_formal_evidence_counts_remain_zero(self):
        summary = self.report["summary"]
        self.assertEqual(summary["formal_agent_response_count"], 0)
        self.assertEqual(summary["formal_persona_score_count"], 0)
        self.assertEqual(summary["model_call_count"], 0)
        self.assertEqual(summary["runtime_change_count"], 0)
        self.assertEqual(summary["holdout_content_review_count"], 0)
        self.assertEqual(summary["development_observation_count"], 5)
        self.assertEqual(summary["sealed_target_source_reservation_count"], 2)

    def test_inputs_bind_preregistration_methods_inventory_and_dependencies(self):
        inputs = self.report["inputs"]
        for key in ("preregistration", "method_registry", "readiness_inventory"):
            path = ROOT / inputs[key]["path"]
            self.assertEqual(
                hashlib.sha256(path.read_bytes()).hexdigest(), inputs[key]["sha256"]
            )
        for artifact in inputs["dependencies"].values():
            path = ROOT / artifact["path"]
            self.assertEqual(
                hashlib.sha256(path.read_bytes()).hexdigest(), artifact["sha256"]
            )

    def test_method_and_condition_inventory_are_complete(self):
        self.assertEqual(len(self.report["method_inventory"]), 5)
        self.assertEqual(len(self.report["system_conditions"]), 3)
        self.assertEqual(len(self.report["evaluation_families"]), 3)
        self.assertEqual(
            set(self.report["system_conditions"]),
            {
                "s0_full_cognitive_persona",
                "c1_matched_prompt_only",
                "c2_matched_persona_disabled",
            },
        )

    def test_result_authorizes_no_model_holdout_runtime_training_or_claim(self):
        authorizations = self.report["authorizations"]
        self.assertTrue(authorizations["reference_manifest_construction"])
        self.assertTrue(authorizations["consented_rater_protocol_construction"])
        self.assertFalse(authorizations["separately_preregistered_pilot"])
        for field in (
            "model_execution",
            "runtime_change",
            "prompt_change",
            "model_training",
            "sealed_holdout_unsealing",
            "formal_persona_scoring",
            "public_persona_fidelity_claim",
            "private_person_copy_claim",
        ):
            self.assertFalse(authorizations[field], field)
        markdown = REPORT_MD.read_text(encoding="utf-8")
        self.assertIn("沒有產生或暗示任何一ノ瀬うるは人格相似分數", markdown)
        self.assertIn("校準公式示意，不是真實結果", markdown)


if __name__ == "__main__":
    unittest.main()
