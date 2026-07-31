import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from public_persona_evidence_v1 import (
    DEFAULT_PREREGISTRATION,
    PROHIBITED_CONTENT_KEYS,
    audit,
    build_audit_from_paths,
    build_markdown,
    load_json,
)
from project_paths import (
    PUBLIC_PERSONA_EVIDENCE_V1_PATH,
    PUBLIC_PERSONA_SOURCE_REGISTRY_V1_PATH,
)


ROOT = Path(__file__).resolve().parent
LOCK = ROOT / "configs/public_persona_evidence_v1_harness_lock.json"


class PublicPersonaEvidenceV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = load_json(PUBLIC_PERSONA_SOURCE_REGISTRY_V1_PATH)
        cls.evidence = load_json(PUBLIC_PERSONA_EVIDENCE_V1_PATH)
        cls.preregistration = load_json(DEFAULT_PREREGISTRATION)

    def run_audit(self, registry=None, evidence=None, preregistration=None):
        return audit(
            copy.deepcopy(registry if registry is not None else self.registry),
            copy.deepcopy(evidence if evidence is not None else self.evidence),
            copy.deepcopy(
                preregistration if preregistration is not None else self.preregistration
            ),
        )

    def test_seed_contract_passes_only_development_hypotheses(self):
        report = self.run_audit()
        self.assertTrue(report["passed"])
        self.assertEqual(
            report["decision"],
            "authorize_public_persona_development_hypotheses_only",
        )
        self.assertTrue(report["authorizations"]["development_hypothesis_use"])
        self.assertFalse(report["authorizations"]["runtime_persona_activation"])
        self.assertFalse(report["authorizations"]["model_training"])
        self.assertFalse(report["authorizations"]["holdout_evaluation"])
        self.assertFalse(report["authorizations"]["public_persona_fidelity_claim"])

    def test_seed_counts_and_dimensions_are_explicit(self):
        summary = self.run_audit()["summary"]
        self.assertEqual(summary["source_count"], 4)
        self.assertEqual(summary["source_role_counts"], {"persona_evidence": 2, "rights_policy": 2})
        self.assertEqual(summary["evidence_count"], 6)
        self.assertEqual(len(summary["dimension_counts"]), 6)
        self.assertEqual(len(summary["trait_keys"]), 6)
        self.assertEqual(sum(summary["source_evidence_counts"].values()), 6)
        self.assertEqual(summary["dataset_role_counts"], {"development": 6})
        self.assertEqual(summary["source_partition_role_overlap_count"], 0)

    def test_persona_sources_are_official_and_conservatively_bounded(self):
        persona_sources = [
            row for row in self.registry["sources"] if row["source_role"] == "persona_evidence"
        ]
        self.assertEqual({row["authority"] for row in persona_sources}, {"agency_official", "target_official"})
        for source in self.registry["sources"]:
            policy = source["project_use_policy"]
            self.assertEqual(policy["automated_collection"], "not_authorized")
            self.assertEqual(policy["verbatim_transcript_storage"], "not_authorized")
            self.assertEqual(policy["model_training_from_source_content"], "not_authorized")

    def test_unofficial_primary_persona_source_is_rejected(self):
        registry = copy.deepcopy(self.registry)
        registry["sources"][0]["authority"] = "fan_summary"
        report = self.run_audit(registry=registry)
        self.assertFalse(report["passed"])
        self.assertIn("vspo_official_profile_20260801:persona_authority", report["violations"]["source_contract"])

    def test_raw_or_verbatim_content_field_is_rejected(self):
        evidence = copy.deepcopy(self.evidence)
        evidence["evidence"][0]["verbatim_text"] = "source sentence"
        report = self.run_audit(evidence=evidence)
        self.assertFalse(report["passed"])
        self.assertTrue(
            any(path.endswith(".verbatim_text") for path in report["violations"]["prohibited_content_key"])
        )
        self.assertIn("verbatim_text", PROHIBITED_CONTENT_KEYS)

    def test_fixed_reply_or_training_flag_is_rejected(self):
        evidence = copy.deepcopy(self.evidence)
        evidence["evidence"][0]["contains_target_reply"] = True
        evidence["evidence"][1]["training_authorized"] = True
        report = self.run_audit(evidence=evidence)
        self.assertFalse(report["passed"])
        self.assertIn("persona_dev_v1_001:contains_target_reply", report["violations"]["dataset_boundary"])
        self.assertIn("persona_dev_v1_002:training_authorized", report["violations"]["dataset_boundary"])

    def test_same_source_partition_cannot_cross_development_and_holdout(self):
        evidence = copy.deepcopy(self.evidence)
        evidence["evidence"][1]["dataset_role"] = "holdout"
        preregistration = copy.deepcopy(self.preregistration)
        preregistration["minimum_seed_contract"]["allowed_dataset_roles"] = [
            "development",
            "holdout",
        ]
        report = self.run_audit(evidence=evidence, preregistration=preregistration)
        self.assertFalse(report["passed"])
        self.assertEqual(report["summary"]["source_partition_role_overlap_count"], 1)
        self.assertIn(
            "vspo_official_member_profile_ichinose_uruha",
            report["violations"]["partition_role_overlap"],
        )

    def test_private_identity_inference_is_rejected_even_when_flag_is_false(self):
        evidence = copy.deepcopy(self.evidence)
        evidence["evidence"][0]["observable_behavior"] += " 中之人資訊也可推論。"
        report = self.run_audit(evidence=evidence)
        self.assertFalse(report["passed"])
        self.assertIn("persona_dev_v1_001:中之人", report["violations"]["private_inference"])

    def test_audit_inputs_are_hash_bound_and_markdown_keeps_boundary(self):
        report = build_audit_from_paths(
            PUBLIC_PERSONA_SOURCE_REGISTRY_V1_PATH,
            PUBLIC_PERSONA_EVIDENCE_V1_PATH,
            DEFAULT_PREREGISTRATION,
        )
        for artifact in report["inputs"].values():
            self.assertEqual(len(artifact["sha256"]), 64)
        markdown = build_markdown(report)
        self.assertIn("不允許用途", markdown)
        self.assertIn("模型訓練", markdown)
        self.assertIn("逐字資料 | 0", markdown)
        self.assertIn("group_straight_man_role", markdown)
        self.assertIn("https://vspo.jp/", markdown)

    def test_report_can_be_written_without_mutating_source_artifacts(self):
        before_registry = Path(PUBLIC_PERSONA_SOURCE_REGISTRY_V1_PATH).read_bytes()
        before_evidence = Path(PUBLIC_PERSONA_EVIDENCE_V1_PATH).read_bytes()
        report = build_audit_from_paths(
            PUBLIC_PERSONA_SOURCE_REGISTRY_V1_PATH,
            PUBLIC_PERSONA_EVIDENCE_V1_PATH,
            DEFAULT_PREREGISTRATION,
        )
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "audit.json"
            output.write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")
            self.assertTrue(json.loads(output.read_text(encoding="utf-8"))["passed"])
        self.assertEqual(before_registry, Path(PUBLIC_PERSONA_SOURCE_REGISTRY_V1_PATH).read_bytes())
        self.assertEqual(before_evidence, Path(PUBLIC_PERSONA_EVIDENCE_V1_PATH).read_bytes())

    def test_harness_lock_hashes_match(self):
        lock = json.loads(LOCK.read_text(encoding="utf-8"))
        for artifact in lock["frozen_artifacts"].values():
            actual = hashlib.sha256((ROOT / artifact["path"]).read_bytes()).hexdigest()
            self.assertEqual(actual, artifact["sha256"])


if __name__ == "__main__":
    unittest.main()
