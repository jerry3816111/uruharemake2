import copy
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from public_persona_reference_manifest_v2 import (
    DEFAULT_MANIFEST,
    DEFAULT_PREREGISTRATION,
    DEFAULT_RATER_PROTOCOL,
    DEFAULT_READINESS,
    DEFAULT_V1_PREREGISTRATION,
    DEFAULT_V1_RESULT,
    DEFAULT_V2_SOURCE_REGISTRY,
    EXPECTED_ACTORS,
    EXPECTED_CALIBRATION,
    EXPECTED_FINAL_HOLDOUT,
    PASS_DECISION,
    ROOT,
    audit,
    build_audit_from_paths,
    build_markdown,
    load_json,
)


PYTHON = Path(
    "/Users/jerrychang/Desktop/uruharemake2/Style-Bert-VITS2/venv/bin/python"
)


class PublicPersonaReferenceManifestV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.preregistration = load_json(DEFAULT_PREREGISTRATION)
        cls.manifest = load_json(DEFAULT_MANIFEST)
        cls.rater_protocol = load_json(DEFAULT_RATER_PROTOCOL)
        cls.readiness = load_json(DEFAULT_READINESS)
        cls.v1_result = load_json(DEFAULT_V1_RESULT)
        cls.v1_preregistration = load_json(DEFAULT_V1_PREREGISTRATION)
        cls.v2_source_registry = load_json(DEFAULT_V2_SOURCE_REGISTRY)

    def run_audit(
        self,
        preregistration=None,
        manifest=None,
        rater_protocol=None,
        readiness=None,
        v1_result=None,
        v1_preregistration=None,
        v2_source_registry=None,
    ):
        return audit(
            copy.deepcopy(
                self.preregistration
                if preregistration is None
                else preregistration
            ),
            copy.deepcopy(self.manifest if manifest is None else manifest),
            copy.deepcopy(
                self.rater_protocol
                if rater_protocol is None
                else rater_protocol
            ),
            copy.deepcopy(self.readiness if readiness is None else readiness),
            copy.deepcopy(self.v1_result if v1_result is None else v1_result),
            copy.deepcopy(
                self.v1_preregistration
                if v1_preregistration is None
                else v1_preregistration
            ),
            copy.deepcopy(
                self.v2_source_registry
                if v2_source_registry is None
                else v2_source_registry
            ),
            root=ROOT,
        )

    def source_index(self, manifest=None):
        manifest = self.manifest if manifest is None else manifest
        return {row["source_id"]: row for row in manifest["sources"]}

    def test_protocol_passes_but_formal_execution_remains_blocked(self):
        report = self.run_audit()
        self.assertTrue(report["protocol_passed"])
        self.assertFalse(report["formal_execution_ready"])
        self.assertFalse(report["persona_score_computed"])
        self.assertEqual(report["decision"], PASS_DECISION)
        self.assertEqual(report["summary"]["protocol_check_pass_count"], 13)
        self.assertEqual(report["summary"]["protocol_check_count"], 13)
        self.assertEqual(report["summary"]["readiness_check_pass_count"], 4)
        self.assertEqual(report["summary"]["readiness_check_count"], 19)
        self.assertEqual(report["violations"], {})

    def test_readiness_gain_is_source_governance_not_persona_evidence(self):
        checks = self.run_audit()["readiness_checks"]
        passed = {name for name, value in checks.items() if value}
        self.assertEqual(
            passed,
            {
                "target_calibration_source_count",
                "target_final_holdout_source_count",
                "matched_contrast_person_count",
                "all_nonzero_claims_hash_bound",
            },
        )

    def test_one_target_and_three_preselected_matched_contrasts(self):
        actors = self.manifest["actors"]
        self.assertEqual({row["actor_id"] for row in actors}, set(EXPECTED_ACTORS))
        self.assertEqual(sum(row["role"] == "target" for row in actors), 1)
        self.assertEqual(
            sum(row["role"] == "matched_contrast" for row in actors), 3
        )
        self.assertTrue(self.manifest["actor_selection_frozen_before_behavior_coding"])
        self.assertTrue(
            all(
                row["selected_from_model_outputs_or_similarity_scores"] is False
                for row in actors
            )
        )

    def test_every_actor_has_official_profile_and_channel_binding(self):
        sources = self.source_index()
        for actor_id, expected in EXPECTED_ACTORS.items():
            profile = sources[expected["profile_source_id"]]
            channel = sources[expected["channel_source_id"]]
            self.assertEqual(profile["actor_id"], actor_id)
            self.assertEqual(profile["authority"], "agency_official")
            self.assertEqual(profile["url"], "https://vspo.jp/")
            self.assertEqual(channel["actor_id"], actor_id)
            self.assertEqual(channel["channel_id"], expected["channel_id"])
            self.assertEqual(channel["url"], expected["channel_url"])

    def test_exactly_three_calibration_and_four_final_source_reservations(self):
        sources = self.source_index()
        calibration = {
            source_id
            for source_id, row in sources.items()
            if row["source_role"] == "calibration_reservation"
        }
        final = {
            source_id
            for source_id, row in sources.items()
            if row["source_role"] == "final_holdout_reservation"
        }
        self.assertEqual(calibration, set(EXPECTED_CALIBRATION))
        self.assertEqual(final, set(EXPECTED_FINAL_HOLDOUT))

    def test_source_reservations_have_metadata_but_no_behavior_or_answers(self):
        sources = self.source_index()
        for source_id in set(EXPECTED_CALIBRATION) | set(EXPECTED_FINAL_HOLDOUT):
            row = sources[source_id]
            self.assertEqual(
                set(row["metadata_fields_reviewed"]),
                {
                    "video_id",
                    "publisher_channel_id",
                    "published_at",
                    "context_family",
                },
            )
            self.assertFalse(row["content_reviewed_for_behavior"])
            self.assertFalse(row["labels_available"])
            self.assertFalse(row["candidate_answer_available"])
            self.assertFalse(row["raw_media_stored"])
            self.assertFalse(row["raw_transcript_stored"])
            self.assertNotIn("title", row)
            self.assertNotIn("target_reply", row)
            self.assertNotIn("reference_answer", row)

    def test_calibration_is_unlabeled_and_final_holdout_is_sealed(self):
        sources = self.source_index()
        for source_id in EXPECTED_CALIBRATION:
            row = sources[source_id]
            self.assertFalse(row["sealed"])
            self.assertFalse(row["candidate_freeze_required_before_behavior_review"])
            self.assertFalse(row["holdout_access_log_required"])
        for source_id in EXPECTED_FINAL_HOLDOUT:
            row = sources[source_id]
            self.assertTrue(row["sealed"])
            self.assertTrue(row["candidate_freeze_required_before_behavior_review"])
            self.assertTrue(row["holdout_access_log_required"])

    def test_inherited_v2_holdout_urls_and_partitions_are_preserved(self):
        new_sources = self.source_index()
        old_sources = {
            row["source_id"]: row for row in self.v2_source_registry["sources"]
        }
        for source_id, expected in EXPECTED_FINAL_HOLDOUT.items():
            if not expected["inherited"]:
                continue
            self.assertEqual(new_sources[source_id]["url"], old_sources[source_id]["url"])
            self.assertEqual(
                new_sources[source_id]["source_partition_key"],
                old_sources[source_id]["source_partition_key"],
            )
            self.assertEqual(
                old_sources[source_id]["content_review_scope"],
                "metadata_only_unreviewed_for_behavior",
            )

    def test_all_source_partitions_are_unique_and_event_splits_are_disjoint(self):
        sources = self.manifest["sources"]
        partitions = [row["source_partition_key"] for row in sources]
        self.assertEqual(len(partitions), len(set(partitions)))
        calibration = {
            row["source_partition_key"]
            for row in sources
            if row["dataset_role"] == "calibration"
        }
        final = {
            row["source_partition_key"]
            for row in sources
            if row["dataset_role"] == "final_holdout"
        }
        self.assertFalse(calibration & final)

    def test_contrast_people_have_identity_metadata_only(self):
        contrast_ids = {
            actor_id
            for actor_id, expected in EXPECTED_ACTORS.items()
            if expected["role"] == "matched_contrast"
        }
        rows = [
            row for row in self.manifest["sources"] if row.get("actor_id") in contrast_ids
        ]
        self.assertEqual(len(rows), 6)
        self.assertTrue(all(row["source_role"] == "identity_provenance" for row in rows))
        self.assertTrue(all(row["content_reviewed_for_behavior"] is False for row in rows))

    def test_rights_boundary_is_conservative_and_officially_sourced(self):
        policy = self.manifest["project_policy"]
        self.assertTrue(policy["public_access_is_not_training_permission"])
        self.assertTrue(policy["store_official_metadata_only"])
        for field in (
            "store_raw_media",
            "store_verbatim_transcripts",
            "store_target_replies_or_reference_answers",
            "automated_bulk_collection",
            "model_training_authorized",
            "prompt_or_memory_injection_authorized",
            "runtime_persona_activation_authorized",
            "public_impersonation_authorized",
        ):
            self.assertFalse(policy[field], field)

    def test_blind_protocol_separates_persona_and_language_judgments(self):
        groups = self.rater_protocol["rater_groups"]
        self.assertIn("public_persona_similarity", groups["target_familiar"]["allowed_dimensions"])
        self.assertIn("naturalness", groups["general_japanese"]["allowed_dimensions"])
        self.assertIn(
            "target_persona_similarity",
            groups["general_japanese"]["forbidden_dimensions"],
        )
        assignment = self.rater_protocol["assignment_and_blinding"]
        self.assertTrue(assignment["condition_labels_hidden"])
        self.assertTrue(assignment["response_order_randomized"])
        self.assertEqual(assignment["minimum_independent_ratings_per_item"], 3)

    def test_rater_data_minimization_excludes_direct_identifiers(self):
        minimization = self.rater_protocol["data_minimization"]
        prohibited = set(minimization["prohibited_fields"])
        self.assertTrue(
            {"name", "email", "ip_address", "device_fingerprint", "social_account"}
            <= prohibited
        )
        self.assertFalse(minimization["raw_identity_linkage_stored_with_ratings"])

    def test_no_raters_ratings_outputs_or_persona_scores_exist(self):
        self.assertTrue(
            all(value == 0 for value in self.rater_protocol["current_counts"].values())
        )
        counts = self.readiness["counts"]
        for field in (
            "target_calibration_event_count",
            "target_final_holdout_event_count",
            "contrast_event_count_per_person_min",
            "target_familiar_final_rater_count",
            "general_japanese_final_rater_count",
            "ratings_per_item_min",
            "formal_agent_response_count",
            "formal_persona_score_count",
            "holdout_content_reviewed_count",
            "holdout_label_available_count",
            "raw_or_verbatim_record_count",
            "training_authorized_record_count",
        ):
            self.assertEqual(counts[field], 0, field)

    def test_authorization_is_limited_to_next_protocol_documents(self):
        authorizations = self.run_audit()["authorizations"]
        self.assertTrue(authorizations["metadata_only_event_coding_preregistration"])
        self.assertTrue(authorizations["consent_form_review"])
        for field in (
            "behavior_content_coding",
            "rater_recruitment",
            "rating_collection",
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

    def test_raw_target_reply_payload_is_rejected(self):
        manifest = copy.deepcopy(self.manifest)
        manifest["sources"][8]["target_reply"] = "prohibited"
        report = self.run_audit(manifest=manifest)
        self.assertFalse(report["protocol_passed"])
        self.assertIn("content_boundary", report["violations"])

    def test_behavior_review_or_holdout_unsealing_is_rejected(self):
        manifest = copy.deepcopy(self.manifest)
        sources = {row["source_id"]: row for row in manifest["sources"]}
        sources["uruha_youtube_forza_holdout_v2"]["content_reviewed_for_behavior"] = True
        sources["uruha_youtube_forza_holdout_v2"]["sealed"] = False
        report = self.run_audit(manifest=manifest)
        self.assertFalse(report["protocol_passed"])
        self.assertIn("content_boundary", report["violations"])
        self.assertIn("holdout_seal", report["violations"])

    def test_calibration_final_partition_overlap_is_rejected(self):
        manifest = copy.deepcopy(self.manifest)
        sources = {row["source_id"]: row for row in manifest["sources"]}
        sources["uruha_calibration_youtube_valorant_20260318"][
            "source_partition_key"
        ] = "youtube_archive_K_bNKL3iA_Q"
        report = self.run_audit(manifest=manifest)
        self.assertFalse(report["protocol_passed"])
        self.assertIn("partition", report["violations"])

    def test_wrong_official_channel_or_inherited_holdout_is_rejected(self):
        manifest = copy.deepcopy(self.manifest)
        sources = {row["source_id"]: row for row in manifest["sources"]}
        sources["youtube_channel_tosaki_mimi_20260801"]["channel_id"] = "wrong"
        sources["uruha_youtube_apex_team_holdout_v2"]["url"] = (
            "https://www.youtube.com/watch?v=wrong"
        )
        report = self.run_audit(manifest=manifest)
        self.assertFalse(report["protocol_passed"])
        self.assertIn("official_identity", report["violations"])
        self.assertIn("inherited_holdout", report["violations"])

    def test_posthoc_contrast_selection_or_behavior_content_is_rejected(self):
        manifest = copy.deepcopy(self.manifest)
        manifest["actors"][1]["selected_from_model_outputs_or_similarity_scores"] = True
        manifest["sources"].append(
            {
                "source_id": "posthoc_contrast_event",
                "actor_id": "tachibana_hinano_public_persona",
                "source_role": "behavior_observation",
                "dataset_role": "calibration",
                "source_partition_key": "posthoc_contrast_event_partition",
                "policy_basis_source_ids": ["youtube_terms_reference_v2_20260801"],
            }
        )
        report = self.run_audit(manifest=manifest)
        self.assertFalse(report["protocol_passed"])
        self.assertIn("actors", report["violations"])
        self.assertIn("content_boundary", report["violations"])

    def test_unfavorable_rater_exclusion_or_collection_authorization_is_rejected(self):
        protocol = copy.deepcopy(self.rater_protocol)
        protocol["quality_and_exclusion"]["exclude_for_unfavorable_rating"] = True
        protocol["authorizations"]["rating_collection"] = True
        report = self.run_audit(rater_protocol=protocol)
        self.assertFalse(report["protocol_passed"])
        self.assertIn("rater_protocol", report["violations"])

    def test_fabricated_event_rater_or_score_counts_are_rejected(self):
        readiness = copy.deepcopy(self.readiness)
        readiness["counts"]["target_calibration_event_count"] = 30
        readiness["counts"]["target_familiar_final_rater_count"] = 3
        readiness["counts"]["formal_persona_score_count"] = 1
        report = self.run_audit(readiness=readiness)
        self.assertFalse(report["protocol_passed"])
        self.assertIn("count_honesty", report["violations"])

    def test_boolean_false_cannot_impersonate_a_zero_count(self):
        readiness = copy.deepcopy(self.readiness)
        readiness["counts"]["formal_persona_score_count"] = False
        protocol = copy.deepcopy(self.rater_protocol)
        protocol["current_counts"]["collected_rating_count"] = False
        report = self.run_audit(readiness=readiness, rater_protocol=protocol)
        self.assertFalse(report["protocol_passed"])
        self.assertIn("count_honesty", report["violations"])

    def test_hash_binding_tamper_is_rejected(self):
        readiness = copy.deepcopy(self.readiness)
        readiness["evidence_bindings"]["target_calibration_manifest"]["sha256"] = "0" * 64
        report = self.run_audit(readiness=readiness)
        self.assertFalse(report["protocol_passed"])
        self.assertIn("readiness_evidence", report["violations"])

    def test_require_execution_ready_exits_two_without_fabricating_results(self):
        with tempfile.TemporaryDirectory() as directory:
            output_json = Path(directory) / "audit.json"
            output_md = Path(directory) / "audit.md"
            result = subprocess.run(
                [
                    str(PYTHON),
                    str(ROOT / "public_persona_reference_manifest_v2.py"),
                    "--output-json",
                    str(output_json),
                    "--output-md",
                    str(output_md),
                    "--overwrite",
                    "--require-execution-ready",
                ],
                cwd=ROOT,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 2)
            report = json.loads(output_json.read_text(encoding="utf-8"))
            self.assertTrue(report["protocol_passed"])
            self.assertFalse(report["formal_execution_ready"])
            self.assertEqual(report["summary"]["persona_score_count"], 0)
            self.assertEqual(report["summary"]["model_call_count"], 0)

    def test_report_is_hash_bound_readable_and_does_not_mutate_inputs(self):
        paths = (
            DEFAULT_PREREGISTRATION,
            DEFAULT_MANIFEST,
            DEFAULT_RATER_PROTOCOL,
            DEFAULT_READINESS,
            DEFAULT_V1_RESULT,
            DEFAULT_V1_PREREGISTRATION,
            DEFAULT_V2_SOURCE_REGISTRY,
        )
        before = {path: path.read_bytes() for path in paths}
        report = build_audit_from_paths()
        self.assertTrue(report["protocol_passed"])
        self.assertEqual(set(report["inputs"]), {
            "preregistration",
            "source_manifest",
            "blind_rater_protocol",
            "readiness_inventory",
            "v1_result_lock",
            "v1_preregistration",
            "v2_source_registry",
        })
        for artifact in report["inputs"].values():
            self.assertEqual(len(artifact["sha256"]), 64)
        self.assertEqual(before, {path: path.read_bytes() for path in paths})
        markdown = build_markdown(report)
        self.assertIn("來源不是事件", markdown)
        self.assertIn("未招募、未評分", markdown)
        self.assertIn("仍禁止內容編碼", markdown)


if __name__ == "__main__":
    unittest.main()
