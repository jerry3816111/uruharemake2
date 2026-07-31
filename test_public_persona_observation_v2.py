import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from project_paths import (
    PUBLIC_PERSONA_OBSERVATION_SOURCE_REGISTRY_V2_PATH,
    PUBLIC_PERSONA_OBSERVATIONS_V2_PATH,
)
from public_persona_observation_v2 import (
    DEFAULT_PREREGISTRATION,
    PROHIBITED_CONTENT_KEYS,
    audit,
    build_audit_from_paths,
    build_markdown,
    load_json,
)


ROOT = Path(__file__).resolve().parent
LOCK = ROOT / "configs/public_persona_observation_v2_harness_lock.json"


class PublicPersonaObservationV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = load_json(PUBLIC_PERSONA_OBSERVATION_SOURCE_REGISTRY_V2_PATH)
        cls.dataset = load_json(PUBLIC_PERSONA_OBSERVATIONS_V2_PATH)
        cls.preregistration = load_json(DEFAULT_PREREGISTRATION)

    def run_audit(self, registry=None, dataset=None, preregistration=None):
        return audit(
            copy.deepcopy(registry if registry is not None else self.registry),
            copy.deepcopy(dataset if dataset is not None else self.dataset),
            copy.deepcopy(
                preregistration if preregistration is not None else self.preregistration
            ),
        )

    def test_seed_contract_passes_with_narrow_authorization(self):
        report = self.run_audit()
        self.assertTrue(report["passed"])
        self.assertEqual(
            report["decision"],
            "authorize_conditional_persona_development_hypotheses_and_sealed_holdout_protocol_only",
        )
        authorizations = report["authorizations"]
        self.assertTrue(authorizations["conditional_development_hypothesis_use"])
        self.assertTrue(authorizations["sealed_holdout_protocol_ready"])
        self.assertFalse(authorizations["runtime_persona_activation"])
        self.assertFalse(authorizations["prompt_injection"])
        self.assertFalse(authorizations["model_training"])
        self.assertFalse(authorizations["holdout_unsealing"])
        self.assertFalse(authorizations["public_persona_fidelity_claim"])

    def test_preregistration_cannot_expand_authorization(self):
        preregistration = copy.deepcopy(self.preregistration)
        preregistration["authorizations"]["model_training"] = True
        preregistration["authorizations"]["holdout_unsealing"] = True
        report = self.run_audit(preregistration=preregistration)
        self.assertFalse(report["passed"])
        self.assertIn("model_training", report["violations"]["preregistration"])
        self.assertIn("holdout_unsealing", report["violations"]["preregistration"])

    def test_exact_source_observation_and_holdout_counts(self):
        summary = self.run_audit()["summary"]
        self.assertEqual(summary["source_count"], 10)
        self.assertEqual(
            summary["source_role_counts"],
            {
                "behavior_observation": 5,
                "rights_policy": 3,
                "sealed_holdout": 2,
            },
        )
        self.assertEqual(summary["development_observation_count"], 5)
        self.assertEqual(len(summary["dimension_counts"]), 5)
        self.assertEqual(len(summary["context_counts"]), 5)
        self.assertEqual(summary["conditional_rule_count"], 5)
        self.assertEqual(summary["counterevidence_or_boundary_count"], 5)
        self.assertEqual(summary["sealed_holdout_reservation_count"], 2)

    def test_holdout_is_sealed_unreviewed_and_unlabeled(self):
        report = self.run_audit()
        summary = report["summary"]
        self.assertEqual(summary["holdout_content_reviewed_count"], 0)
        self.assertEqual(summary["holdout_label_available_count"], 0)
        for row in self.dataset["sealed_holdout_reservations"]:
            self.assertTrue(row["sealed"])
            self.assertTrue(row["source_metadata_visible_only"])
            self.assertTrue(row["candidate_freeze_required_before_unsealing"])
            self.assertFalse(row["content_reviewed_for_behavior"])
            self.assertFalse(row["labels_available"])

    def test_sources_use_official_authority_and_conservative_policy(self):
        for source in self.registry["sources"]:
            self.assertIn(
                source["authority"],
                {"target_official", "agency_official", "platform_official"},
            )
            policy = source["project_use_policy"]
            self.assertEqual(policy["raw_source_text_storage"], "not_authorized")
            self.assertEqual(policy["automated_bulk_collection"], "not_authorized")
            self.assertEqual(
                policy["model_training_from_source_content"], "not_authorized"
            )

    def test_unofficial_observation_source_is_rejected(self):
        registry = copy.deepcopy(self.registry)
        registry["sources"][0]["authority"] = "fan_summary"
        report = self.run_audit(registry=registry)
        self.assertFalse(report["passed"])
        self.assertIn(
            "uruha_x_profile_dev_20260801:authority",
            report["violations"]["source_contract"],
        )

    def test_non_published_interface_collection_is_rejected(self):
        registry = copy.deepcopy(self.registry)
        registry["sources"][0]["acquisition_method"] = "bulk_scrape"
        report = self.run_audit(registry=registry)
        self.assertFalse(report["passed"])
        self.assertIn(
            "uruha_x_profile_dev_20260801:acquisition_method",
            report["violations"]["source_contract"],
        )

    def test_raw_or_verbatim_content_field_is_rejected(self):
        dataset = copy.deepcopy(self.dataset)
        dataset["observations"][0]["verbatim_text"] = "source sentence"
        report = self.run_audit(dataset=dataset)
        self.assertFalse(report["passed"])
        self.assertTrue(
            any(
                path.endswith(".verbatim_text")
                for path in report["violations"]["prohibited_content_key"]
            )
        )
        self.assertIn("verbatim_text", PROHIBITED_CONTENT_KEYS)

    def test_fixed_reply_or_training_flag_is_rejected(self):
        dataset = copy.deepcopy(self.dataset)
        dataset["observations"][0]["contains_target_reply"] = True
        dataset["observations"][1]["training_authorized"] = True
        report = self.run_audit(dataset=dataset)
        self.assertFalse(report["passed"])
        self.assertIn(
            "persona_obs_v2_dev_001:contains_target_reply",
            report["violations"]["dataset_boundary"],
        )
        self.assertIn(
            "persona_obs_v2_dev_002:training_authorized",
            report["violations"]["dataset_boundary"],
        )

    def test_missing_counterevidence_is_rejected(self):
        dataset = copy.deepcopy(self.dataset)
        dataset["observations"][0]["counterevidence_or_boundary"] = ""
        report = self.run_audit(dataset=dataset)
        self.assertFalse(report["passed"])
        self.assertIn(
            "persona_obs_v2_dev_001:counterevidence_or_boundary",
            report["violations"]["observation_contract"],
        )

    def test_private_identity_inference_is_rejected(self):
        dataset = copy.deepcopy(self.dataset)
        dataset["observations"][0]["behavior_paraphrase"] += " 並可推論中之人。"
        report = self.run_audit(dataset=dataset)
        self.assertFalse(report["passed"])
        self.assertIn(
            "persona_obs_v2_dev_001:中之人",
            report["violations"]["private_inference"],
        )

    def test_unsealed_or_prelabeled_holdout_is_rejected(self):
        dataset = copy.deepcopy(self.dataset)
        dataset["sealed_holdout_reservations"][0]["sealed"] = False
        dataset["sealed_holdout_reservations"][1]["labels_available"] = True
        report = self.run_audit(dataset=dataset)
        self.assertFalse(report["passed"])
        self.assertIn(
            "persona_obs_v2_holdout_001:sealed",
            report["violations"]["holdout_contract"],
        )
        self.assertIn(
            "persona_obs_v2_holdout_002:labels_available",
            report["violations"]["holdout_contract"],
        )

    def test_development_and_holdout_partition_overlap_is_rejected(self):
        registry = copy.deepcopy(self.registry)
        dataset = copy.deepcopy(self.dataset)
        development_partition = dataset["observations"][0]["source_partition_key"]
        registry["sources"][5]["source_partition_key"] = development_partition
        dataset["sealed_holdout_reservations"][0][
            "source_partition_key"
        ] = development_partition
        report = self.run_audit(registry=registry, dataset=dataset)
        self.assertFalse(report["passed"])
        self.assertIn(
            development_partition,
            report["violations"]["source_partition_role_overlap"],
        )
        self.assertIn(
            development_partition,
            report["violations"]["development_holdout_overlap"],
        )

    def test_audit_inputs_are_hash_bound_and_markdown_keeps_boundary(self):
        report = build_audit_from_paths(
            PUBLIC_PERSONA_OBSERVATION_SOURCE_REGISTRY_V2_PATH,
            PUBLIC_PERSONA_OBSERVATIONS_V2_PATH,
            DEFAULT_PREREGISTRATION,
        )
        for artifact in report["inputs"].values():
            self.assertEqual(len(artifact["sha256"]), 64)
        markdown = build_markdown(report)
        self.assertIn("不允許", markdown)
        self.assertIn("Sealed holdout", markdown)
        self.assertIn("Holdout 已看內容 | 0", markdown)
        self.assertIn("逐字資料 | 0", markdown)
        self.assertIn("functional_stream_start_notification", markdown)
        self.assertIn("https://x.com/en/tos", markdown)

    def test_report_build_does_not_mutate_source_artifacts(self):
        before_registry = Path(
            PUBLIC_PERSONA_OBSERVATION_SOURCE_REGISTRY_V2_PATH
        ).read_bytes()
        before_dataset = Path(PUBLIC_PERSONA_OBSERVATIONS_V2_PATH).read_bytes()
        report = build_audit_from_paths(
            PUBLIC_PERSONA_OBSERVATION_SOURCE_REGISTRY_V2_PATH,
            PUBLIC_PERSONA_OBSERVATIONS_V2_PATH,
            DEFAULT_PREREGISTRATION,
        )
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "audit.json"
            output.write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")
            self.assertTrue(json.loads(output.read_text(encoding="utf-8"))["passed"])
        self.assertEqual(
            before_registry,
            Path(PUBLIC_PERSONA_OBSERVATION_SOURCE_REGISTRY_V2_PATH).read_bytes(),
        )
        self.assertEqual(
            before_dataset,
            Path(PUBLIC_PERSONA_OBSERVATIONS_V2_PATH).read_bytes(),
        )

    def test_harness_lock_hashes_match(self):
        lock = json.loads(LOCK.read_text(encoding="utf-8"))
        for artifact in lock["frozen_artifacts"].values():
            actual = hashlib.sha256((ROOT / artifact["path"]).read_bytes()).hexdigest()
            self.assertEqual(actual, artifact["sha256"])


if __name__ == "__main__":
    unittest.main()
