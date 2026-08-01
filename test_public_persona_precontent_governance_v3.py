import copy
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from public_persona_precontent_governance_v3 import (
    DEFAULT_BLIND_PROTOCOL,
    DEFAULT_CONSENT,
    DEFAULT_EVENT_SCHEMA,
    DEFAULT_METHOD_REGISTRY,
    DEFAULT_PREREGISTRATION,
    DEFAULT_READINESS,
    DEFAULT_RIGHTS_REVIEW,
    DEFAULT_SOURCE_MANIFEST,
    DEFAULT_V1_PREREGISTRATION,
    DEFAULT_V2_RESULT,
    EXPECTED_CALIBRATION_IDS,
    EXPECTED_DIMENSIONS,
    EXPECTED_FINAL_IDS,
    FAIL_DECISION,
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


class PublicPersonaPrecontentGovernanceV3Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.preregistration = load_json(DEFAULT_PREREGISTRATION)
        cls.event_schema = load_json(DEFAULT_EVENT_SCHEMA)
        cls.rights_review = load_json(DEFAULT_RIGHTS_REVIEW)
        cls.consent = load_json(DEFAULT_CONSENT)
        cls.method_registry = load_json(DEFAULT_METHOD_REGISTRY)
        cls.source_manifest = load_json(DEFAULT_SOURCE_MANIFEST)
        cls.blind_protocol = load_json(DEFAULT_BLIND_PROTOCOL)
        cls.readiness = load_json(DEFAULT_READINESS)
        cls.v1_preregistration = load_json(DEFAULT_V1_PREREGISTRATION)
        cls.v2_result = load_json(DEFAULT_V2_RESULT)

    def run_audit(self, **overrides):
        names = (
            "preregistration",
            "event_schema",
            "rights_review",
            "consent",
            "method_registry",
            "source_manifest",
            "blind_protocol",
            "readiness",
            "v1_preregistration",
            "v2_result",
        )
        values = [
            copy.deepcopy(overrides.get(name, getattr(self, name))) for name in names
        ]
        return audit(*values, root=ROOT)

    def test_protocol_passes_but_formal_execution_remains_blocked(self):
        report = self.run_audit()
        self.assertTrue(report["protocol_passed"])
        self.assertFalse(report["formal_execution_ready"])
        self.assertFalse(report["persona_score_computed"])
        self.assertEqual(report["decision"], PASS_DECISION)
        self.assertEqual(report["summary"]["protocol_check_count"], 16)
        self.assertEqual(report["summary"]["protocol_check_pass_count"], 16)
        self.assertEqual(report["summary"]["formal_readiness_pass_count"], 4)
        self.assertEqual(report["summary"]["formal_readiness_check_count"], 19)
        self.assertEqual(report["violations"], {})

    def test_goal_separates_general_persona_local_and_embodied_evidence(self):
        axes = set(self.preregistration["long_term_goal"]["independent_evidence_axes"])
        self.assertEqual(len(axes), 4)
        self.assertIn("general_cognitive_capability", axes)
        self.assertIn("public_observable_persona_fidelity", axes)
        self.assertIn("local_pc_latency_and_resource_feasibility", axes)
        self.assertIn("Function_Calling_voice_and_VRM_action_safety", axes)

    def test_event_schema_uses_exact_six_public_observable_dimensions(self):
        dimensions = set(self.event_schema["construct"]["dimensions"])
        self.assertEqual(dimensions, EXPECTED_DIMENSIONS)
        self.assertEqual(
            dimensions,
            set(self.v1_preregistration["target_construct"]["dimensions"]),
        )
        self.assertIn(
            "private_inner_state",
            self.event_schema["construct"]["excluded_constructs"],
        )

    def test_only_three_calibration_sources_are_authorized(self):
        phase = self.event_schema["initial_phase"]
        self.assertEqual(set(phase["authorized_source_ids"]), EXPECTED_CALIBRATION_IDS)
        self.assertEqual(set(phase["forbidden_source_ids"]), EXPECTED_FINAL_IDS)
        self.assertFalse(phase["final_holdout_content_review_authorized"])
        self.assertFalse(phase["contrast_actor_content_coding_authorized"])
        self.assertEqual(phase["maximum_events_before_separate_pilot_freeze"], 30)

    def test_event_coding_is_two_stage_and_blind_to_system_outputs(self):
        self.assertTrue(
            self.event_schema["observation_unit"][
                "fixed_duration_chunking_forbidden"
            ]
        )
        stages = self.event_schema["coding_workflow"]
        self.assertEqual(stages[0]["stage"], "primary_observation")
        self.assertEqual(stages[1]["stage"], "independent_review")
        self.assertFalse(stages[0]["system_outputs_visible"])
        self.assertFalse(stages[1]["system_outputs_visible"])
        self.assertFalse(
            stages[2]["unfavorable_or_ambiguous_records_deleted_to_raise_score"]
        )

    def test_event_data_cannot_become_prompt_memory_training_or_answer(self):
        leakage = self.event_schema["anti_leakage"]
        prohibited = (
            "event_records_may_enter_prompt",
            "event_records_may_enter_memory",
            "event_records_may_enter_retrieval",
            "event_records_may_enter_training",
            "event_records_may_define_fixed_target_answer",
            "candidate_or_model_output_visible_during_coding",
        )
        self.assertTrue(all(leakage[field] is False for field in prohibited))

    def test_all_17_source_locators_have_exactly_one_rights_review(self):
        manifest_ids = {
            row["source_id"] for row in self.source_manifest["sources"]
        }
        review_ids = {
            row["source_id"] for row in self.rights_review["source_reviews"]
        }
        self.assertEqual(len(self.rights_review["source_reviews"]), 17)
        self.assertEqual(review_ids, manifest_ids)
        self.assertEqual(
            self.rights_review["review_completion"][
                "registered_source_locator_reviewed_count"
            ],
            17,
        )

    def test_only_calibration_profile_allows_manual_paraphrase(self):
        profiles = self.rights_review["permission_profiles"]
        allowed = profiles["calibration_manual_observation_project_policy"]
        self.assertTrue(allowed["bounded_manual_behavior_observation"])
        self.assertTrue(allowed["researcher_behavior_paraphrase"])
        for profile_id, profile in profiles.items():
            if profile_id == "calibration_manual_observation_project_policy":
                continue
            self.assertFalse(profile["bounded_manual_behavior_observation"])
            self.assertFalse(profile["researcher_behavior_paraphrase"])

    def test_no_profile_allows_raw_transcript_training_or_runtime_use(self):
        for profile in self.rights_review["permission_profiles"].values():
            self.assertFalse(profile["raw_media_storage"])
            self.assertFalse(profile["verbatim_transcript_storage"])
            self.assertFalse(profile["automated_bulk_collection"])
            self.assertFalse(profile["model_training"])
            self.assertFalse(profile["prompt_memory_or_retrieval_use"])
            self.assertFalse(profile["runtime_persona_activation"])

    def test_registered_locator_review_is_not_formal_corpus_rights_completion(self):
        completion = self.rights_review["review_completion"]
        self.assertEqual(completion["registered_source_locator_reviewed_count"], 17)
        self.assertFalse(completion["formal_corpus_rights_review_complete"])
        self.assertEqual(completion["contrast_behavior_source_registered_count"], 0)

    def test_consent_matches_blind_protocol_and_collects_no_identifiers(self):
        data = self.consent["data_handling"]
        blind = self.blind_protocol["data_minimization"]
        self.assertEqual(set(data["stored_fields"]), set(blind["stored_fields"]))
        self.assertEqual(
            set(data["prohibited_fields"]), set(blind["prohibited_fields"])
        )
        self.assertFalse(data["raw_identity_linkage"])

    def test_consent_is_participant_facing_but_recruitment_blocked(self):
        document_path = ROOT / self.consent["document"]["path"]
        document = document_path.read_text(encoding="utf-8")
        self.assertIn("全部由 AI 產生", document)
        self.assertIn("參加完全自願", document)
        self.assertIn("研究聯絡窗口尚未填入", document)
        self.assertIn("不得用於正式招募", document)
        self.assertTrue(
            all(
                value is False
                for value in self.consent["recruitment_blockers"].values()
            )
        )
        self.assertFalse(self.consent["authorizations"]["rater_recruitment"])

    def test_counts_remain_zero_and_no_persona_score_exists(self):
        report = self.run_audit()
        for field in (
            "behavior_event_count",
            "human_rater_count",
            "model_response_count",
            "persona_score_count",
            "holdout_content_review_count",
            "runtime_change_count",
            "model_call_count",
        ):
            self.assertEqual(report["summary"][field], 0, field)

    def test_pass_authorizes_only_calibration_coding_and_governance_review(self):
        auth = self.run_audit()["authorizations"]
        self.assertTrue(auth["bounded_calibration_event_coding"])
        self.assertTrue(auth["consent_form_usability_review"])
        self.assertTrue(auth["contrast_event_source_registration"])
        for field in (
            "rater_recruitment",
            "rating_collection",
            "model_execution",
            "runtime_change",
            "prompt_change",
            "memory_change",
            "model_training",
            "sealed_holdout_unsealing",
            "formal_persona_scoring",
            "public_persona_fidelity_claim",
            "private_person_copy_claim",
        ):
            self.assertFalse(auth[field], field)

    def test_mutation_final_holdout_authorization_fails(self):
        mutated = copy.deepcopy(self.event_schema)
        mutated["initial_phase"]["final_holdout_content_review_authorized"] = True
        report = self.run_audit(event_schema=mutated)
        self.assertFalse(report["protocol_passed"])
        self.assertEqual(report["decision"], FAIL_DECISION)
        self.assertIn("event_schema", report["violations"])

    def test_mutation_event_training_use_fails(self):
        mutated = copy.deepcopy(self.event_schema)
        mutated["anti_leakage"]["event_records_may_enter_training"] = True
        report = self.run_audit(event_schema=mutated)
        self.assertFalse(report["protocol_passed"])
        self.assertIn("leakage", report["violations"])

    def test_mutation_rights_holder_license_claim_fails(self):
        mutated = copy.deepcopy(self.rights_review)
        mutated["review_policy"]["rights_holder_permission_claimed"] = True
        report = self.run_audit(rights_review=mutated)
        self.assertFalse(report["protocol_passed"])
        self.assertIn("rights", report["violations"])

    def test_mutation_recruitment_authorization_fails(self):
        mutated = copy.deepcopy(self.consent)
        mutated["authorizations"]["rater_recruitment"] = True
        report = self.run_audit(consent=mutated)
        self.assertFalse(report["protocol_passed"])
        self.assertIn("consent", report["violations"])

    def test_markdown_is_explicit_that_this_is_not_a_persona_score(self):
        markdown = build_markdown(self.run_audit())
        self.assertIn("通用認知、公開人格相似、本機可部署", markdown)
        self.assertIn("不是人格能力提升", markdown)
        self.assertIn("不能正式評分", markdown)
        self.assertIn("4/19", markdown)

    def test_path_builder_hash_binds_all_inputs(self):
        report = build_audit_from_paths()
        self.assertTrue(report["protocol_passed"])
        self.assertEqual(len(report["inputs"]), 10)
        for artifact in report["inputs"].values():
            self.assertEqual(len(artifact["sha256"]), 64)
            self.assertTrue((ROOT / artifact["path"]).is_file())

    def test_cli_refuses_overwrite_without_flag(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_json = Path(temp_dir) / "report.json"
            output_md = Path(temp_dir) / "report.md"
            output_json.write_text("existing", encoding="utf-8")
            result = subprocess.run(
                [
                    str(PYTHON),
                    str(ROOT / "public_persona_precontent_governance_v3.py"),
                    "--output-json",
                    str(output_json),
                    "--output-md",
                    str(output_md),
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(output_json.read_text(encoding="utf-8"), "existing")


if __name__ == "__main__":
    unittest.main()
