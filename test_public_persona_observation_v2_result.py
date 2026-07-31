import hashlib
import json
import unittest
from pathlib import Path

from project_paths import (
    PUBLIC_PERSONA_OBSERVATION_SOURCE_REGISTRY_V2_PATH,
    PUBLIC_PERSONA_OBSERVATIONS_V2_PATH,
    PUBLIC_PERSONA_OBSERVATION_V2_AUDIT_JSON_PATH,
)


ROOT = Path(__file__).resolve().parent
LOCK = ROOT / "configs/public_persona_observation_v2_result_lock.json"
HARNESS_LOCK = ROOT / "configs/public_persona_observation_v2_harness_lock.json"
PREREGISTRATION = (
    ROOT / "configs/public_persona_observation_v2_preregistration.json"
)
V1_RESULT_LOCK = ROOT / "configs/public_persona_evidence_v1_result_lock.json"


class PublicPersonaObservationV2ResultTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = json.loads(
            Path(PUBLIC_PERSONA_OBSERVATION_V2_AUDIT_JSON_PATH).read_text(
                encoding="utf-8"
            )
        )
        cls.lock = json.loads(LOCK.read_text(encoding="utf-8"))

    def test_result_artifact_hashes_match_lock(self):
        for artifact in self.lock["frozen_artifacts"].values():
            actual = hashlib.sha256((ROOT / artifact["path"]).read_bytes()).hexdigest()
            self.assertEqual(actual, artifact["sha256"])

    def test_formal_result_has_exact_counts_and_zero_violations(self):
        summary = self.report["summary"]
        self.assertTrue(self.report["passed"])
        self.assertEqual(
            self.report["decision"],
            "authorize_conditional_persona_development_hypotheses_and_sealed_holdout_protocol_only",
        )
        self.assertEqual(summary["source_count"], 10)
        self.assertEqual(summary["development_observation_count"], 5)
        self.assertEqual(len(summary["dimension_counts"]), 5)
        self.assertEqual(len(summary["context_counts"]), 5)
        self.assertEqual(summary["sealed_holdout_reservation_count"], 2)
        for count_name in (
            "source_partition_role_overlap_count",
            "development_holdout_overlap_count",
            "holdout_content_reviewed_count",
            "holdout_label_available_count",
            "verbatim_record_count",
            "target_reply_count",
            "private_identity_inference_count",
            "training_authorized_count",
        ):
            self.assertEqual(summary[count_name], 0, count_name)
        self.assertEqual(self.report["violations"], {})
        self.assertTrue(all(self.report["contract_checks"].values()))
        self.assertTrue(all(self.report["threshold_checks"].values()))

    def test_report_inputs_bind_current_sources_and_preregistration(self):
        expected = {
            "source_registry": Path(
                PUBLIC_PERSONA_OBSERVATION_SOURCE_REGISTRY_V2_PATH
            ),
            "observation_dataset": Path(PUBLIC_PERSONA_OBSERVATIONS_V2_PATH),
            "preregistration": PREREGISTRATION,
        }
        for key, path in expected.items():
            self.assertEqual(
                self.report["inputs"][key]["sha256"],
                hashlib.sha256(path.read_bytes()).hexdigest(),
            )

    def test_v1_dependency_is_locked_and_has_required_decision(self):
        harness = json.loads(HARNESS_LOCK.read_text(encoding="utf-8"))
        v1_result = json.loads(V1_RESULT_LOCK.read_text(encoding="utf-8"))
        dependency = harness["frozen_artifacts"]["v1_result_lock"]
        self.assertEqual(
            hashlib.sha256(V1_RESULT_LOCK.read_bytes()).hexdigest(),
            dependency["sha256"],
        )
        self.assertEqual(
            v1_result["decision"],
            harness["depends_on"]["required_decision"],
        )

    def test_result_does_not_authorize_runtime_training_or_fidelity_claim(self):
        authorizations = self.report["authorizations"]
        self.assertTrue(authorizations["conditional_development_hypothesis_use"])
        self.assertTrue(authorizations["sealed_holdout_protocol_ready"])
        self.assertFalse(authorizations["runtime_persona_activation"])
        self.assertFalse(authorizations["prompt_injection"])
        self.assertFalse(authorizations["model_training"])
        self.assertFalse(authorizations["holdout_unsealing"])
        self.assertFalse(authorizations["holdout_evaluation_claim"])
        self.assertFalse(authorizations["public_persona_fidelity_claim"])
        self.assertFalse(authorizations["private_person_copy_claim"])


if __name__ == "__main__":
    unittest.main()
