import hashlib
import json
import unittest
from pathlib import Path

from project_paths import (
    PUBLIC_PERSONA_EVIDENCE_V1_AUDIT_JSON_PATH,
    PUBLIC_PERSONA_EVIDENCE_V1_PATH,
    PUBLIC_PERSONA_SOURCE_REGISTRY_V1_PATH,
)


ROOT = Path(__file__).resolve().parent
LOCK = ROOT / "configs/public_persona_evidence_v1_result_lock.json"
PREREGISTRATION = ROOT / "configs/public_persona_evidence_v1_preregistration.json"


class PublicPersonaEvidenceV1ResultTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = json.loads(Path(PUBLIC_PERSONA_EVIDENCE_V1_AUDIT_JSON_PATH).read_text(encoding="utf-8"))
        cls.lock = json.loads(LOCK.read_text(encoding="utf-8"))

    def test_result_artifact_hashes_match_lock(self):
        for artifact in self.lock["frozen_artifacts"].values():
            actual = hashlib.sha256((ROOT / artifact["path"]).read_bytes()).hexdigest()
            self.assertEqual(actual, artifact["sha256"])

    def test_formal_result_has_exact_seed_counts_and_zero_violations(self):
        summary = self.report["summary"]
        self.assertTrue(self.report["passed"])
        self.assertEqual(
            self.report["decision"],
            "authorize_public_persona_development_hypotheses_only",
        )
        self.assertEqual(summary["source_count"], 4)
        self.assertEqual(summary["evidence_count"], 6)
        self.assertEqual(len(summary["dimension_counts"]), 6)
        self.assertEqual(summary["verbatim_record_count"], 0)
        self.assertEqual(summary["target_reply_count"], 0)
        self.assertEqual(summary["private_identity_inference_count"], 0)
        self.assertEqual(summary["training_authorized_count"], 0)
        self.assertEqual(self.report["violations"], {})
        self.assertTrue(all(self.report["contract_checks"].values()))
        self.assertTrue(all(self.report["threshold_checks"].values()))

    def test_report_inputs_bind_current_sources_and_preregistration(self):
        expected = {
            "source_registry": Path(PUBLIC_PERSONA_SOURCE_REGISTRY_V1_PATH),
            "evidence_dataset": Path(PUBLIC_PERSONA_EVIDENCE_V1_PATH),
            "preregistration": PREREGISTRATION,
        }
        for key, path in expected.items():
            self.assertEqual(
                self.report["inputs"][key]["sha256"],
                hashlib.sha256(path.read_bytes()).hexdigest(),
            )

    def test_result_does_not_authorize_runtime_training_or_fidelity_claim(self):
        authorizations = self.report["authorizations"]
        self.assertTrue(authorizations["development_hypothesis_use"])
        self.assertFalse(authorizations["runtime_persona_activation"])
        self.assertFalse(authorizations["model_training"])
        self.assertFalse(authorizations["holdout_evaluation"])
        self.assertFalse(authorizations["public_persona_fidelity_claim"])
        self.assertFalse(authorizations["private_person_copy_claim"])


if __name__ == "__main__":
    unittest.main()
