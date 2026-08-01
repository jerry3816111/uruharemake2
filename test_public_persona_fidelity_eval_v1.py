import copy
import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from public_persona_fidelity_eval_v1 import (
    DEFAULT_METHOD_REGISTRY,
    DEFAULT_PREREGISTRATION,
    DEFAULT_READINESS_INVENTORY,
    EXPECTED_DEPENDENCIES,
    PROTOCOL_PASS_DECISION,
    ROOT,
    audit,
    build_audit_from_paths,
    build_markdown,
    calibrated_distance,
    calibrated_similarity,
    load_json,
    pairwise_preference_summary,
)


HARNESS_LOCK = ROOT / "configs/public_persona_fidelity_eval_v1_harness_lock.json"
PYTHON = Path(
    "/Users/jerrychang/Desktop/uruharemake2/Style-Bert-VITS2/venv/bin/python"
)


class PublicPersonaFidelityEvalV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.preregistration = load_json(DEFAULT_PREREGISTRATION)
        cls.methods = load_json(DEFAULT_METHOD_REGISTRY)
        cls.readiness = load_json(DEFAULT_READINESS_INVENTORY)
        cls.dependencies = {
            path: load_json(ROOT / path) for path in EXPECTED_DEPENDENCIES
        }

    def run_audit(
        self,
        preregistration=None,
        methods=None,
        readiness=None,
        dependencies=None,
    ):
        return audit(
            copy.deepcopy(
                preregistration
                if preregistration is not None
                else self.preregistration
            ),
            copy.deepcopy(methods if methods is not None else self.methods),
            copy.deepcopy(readiness if readiness is not None else self.readiness),
            copy.deepcopy(
                dependencies if dependencies is not None else self.dependencies
            ),
            root=ROOT,
        )

    def test_protocol_passes_but_execution_is_honestly_not_ready(self):
        report = self.run_audit()
        self.assertTrue(report["protocol_passed"])
        self.assertFalse(report["formal_execution_ready"])
        self.assertFalse(report["persona_score_computed"])
        self.assertEqual(report["decision"], PROTOCOL_PASS_DECISION)
        self.assertEqual(report["summary"]["protocol_check_pass_count"], 17)
        self.assertEqual(report["summary"]["protocol_check_count"], 17)
        self.assertEqual(report["summary"]["readiness_check_pass_count"], 1)
        self.assertEqual(report["summary"]["readiness_check_count"], 19)
        self.assertEqual(report["violations"], {})

    def test_authorization_is_limited_to_manifest_and_rater_protocol(self):
        authorizations = self.run_audit()["authorizations"]
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

    def test_primary_conditions_are_matched_and_exact(self):
        conditions = self.preregistration["system_conditions"]
        self.assertEqual(
            set(conditions),
            {
                "s0_full_cognitive_persona",
                "c1_matched_prompt_only",
                "c2_matched_persona_disabled",
            },
        )
        control = conditions["c1_matched_prompt_only"]["description"]
        for required in ("相同本機基礎模型", "開發人格資訊", "總上下文預算"):
            self.assertIn(required, control)

    def test_target_construct_is_public_observable_not_person_identity(self):
        construct = self.preregistration["target_construct"]
        self.assertEqual(len(construct["dimensions"]), 6)
        excluded = set(construct["explicitly_not_measured"])
        self.assertIn("performer_identity", excluded)
        self.assertIn("private_inner_state", excluded)
        self.assertIn("public_deception_success", excluded)

    def test_three_source_independent_evaluation_families_are_separate(self):
        families = self.preregistration["evaluation_families"]
        self.assertEqual(
            set(families),
            {
                "naturalistic_masked_continuation",
                "counterfactual_unseen_open_scenarios",
                "dynamic_multi_turn_episodes",
            },
        )
        self.assertIn(
            "不提供其後續原句或答案",
            families["naturalistic_masked_continuation"]["agent_input"],
        )
        self.assertIn(
            "不建立固定目標答案",
            families["counterfactual_unseen_open_scenarios"]["reference"],
        )

    def test_blind_protocol_separates_fidelity_and_naturalness_raters(self):
        protocol = self.preregistration["human_blind_protocol"]
        self.assertEqual(protocol["setting"], "closed_consented_anonymous_evaluation")
        self.assertIn("公開人格相似", protocol["target_familiar_rater_role"])
        self.assertIn("不評目標人格", protocol["general_japanese_rater_role"])
        self.assertTrue(protocol["condition_blinding"])
        self.assertTrue(protocol["response_order_randomized"])
        self.assertTrue(protocol["debrief_required"])
        self.assertEqual(protocol["minimum_ratings_per_item"], 3)

    def test_primary_endpoint_has_practical_and_statistical_gates(self):
        endpoint = self.preregistration["primary_endpoint"]
        gates = endpoint["success_thresholds"]
        self.assertEqual(
            endpoint["name"], "paired_blind_persona_preference_s0_over_c1"
        )
        self.assertEqual(gates["non_tie_win_rate_min"], 0.6)
        self.assertEqual(gates["confidence_interval_level"], 0.95)
        self.assertEqual(gates["confidence_interval_lower_bound_above"], 0.5)
        self.assertEqual(gates["two_sided_alpha_max"], 0.05)

    def test_similarity_and_distance_calibration_use_human_reference_range(self):
        self.assertAlmostEqual(
            calibrated_similarity(0.7, [0.88, 0.9, 0.92], [0.38, 0.4, 0.42]),
            0.6,
        )
        self.assertAlmostEqual(
            calibrated_distance(0.3, [0.18, 0.2, 0.22], [0.58, 0.6, 0.62]),
            0.75,
        )

    def test_calibration_is_not_clipped_and_rejects_invalid_reference_order(self):
        self.assertGreater(
            calibrated_similarity(1.0, [0.88, 0.9, 0.92], [0.38, 0.4, 0.42]),
            1.0,
        )
        self.assertLess(
            calibrated_distance(0.8, [0.18, 0.2, 0.22], [0.58, 0.6, 0.62]),
            0.0,
        )
        with self.assertRaises(ValueError):
            calibrated_similarity(0.5, [0.4], [0.4])
        with self.assertRaises(ValueError):
            calibrated_distance(0.5, [0.6], [0.4])
        with self.assertRaises(ValueError):
            calibrated_similarity(0.5, [], [0.4])

    def test_pairwise_summary_keeps_ties_separate(self):
        result = pairwise_preference_summary(12, 6, 2)
        self.assertEqual(result["judgment_count"], 20)
        self.assertEqual(result["non_tie_count"], 18)
        self.assertAlmostEqual(result["s0_non_tie_win_rate"], 12 / 18)
        self.assertAlmostEqual(result["s0_tie_adjusted_win_rate"], 0.65)
        lower, upper = result["s0_non_tie_wilson_95_ci"]
        self.assertLess(lower, 12 / 18)
        self.assertGreater(upper, 12 / 18)

    def test_method_registry_uses_five_primary_papers_without_import(self):
        self.assertFalse(self.methods["dataset_or_code_imported"])
        rows = self.methods["methods"]
        self.assertEqual(len(rows), 5)
        self.assertEqual(len({row["doi"] for row in rows}), 5)
        for row in rows:
            self.assertEqual(row["authority"], "peer_reviewed_primary_paper")
            self.assertTrue(row["url"].startswith("https://aclanthology.org/"))
            self.assertTrue(row["doi"].startswith("10."))
            self.assertTrue(row["adopted_element"])
            self.assertTrue(row["not_claimed"])

    def test_non_primary_method_authority_is_rejected(self):
        methods = copy.deepcopy(self.methods)
        methods["methods"][0]["authority"] = "secondary_blog"
        report = self.run_audit(methods=methods)
        self.assertFalse(report["protocol_passed"])
        self.assertIn(
            "incharacter_acl_2024:authority",
            report["violations"]["method_registry"],
        )

    def test_locked_dependencies_must_keep_required_decisions(self):
        dependencies = copy.deepcopy(self.dependencies)
        dependency = "configs/public_persona_observation_v2_result_lock.json"
        dependencies[dependency]["decision"] = "expanded_claim"
        report = self.run_audit(dependencies=dependencies)
        self.assertFalse(report["protocol_passed"])
        self.assertIn(
            f"{dependency}:result_decision", report["violations"]["dependency"]
        )

    def test_readiness_counts_match_locked_v2_and_formal_data_remains_zero(self):
        counts = self.run_audit()["readiness_current"]
        self.assertEqual(counts["target_development_observation_count"], 5)
        self.assertEqual(counts["sealed_target_source_reservation_count"], 2)
        for field in (
            "target_calibration_event_count",
            "target_final_holdout_event_count",
            "matched_contrast_person_count",
            "target_familiar_final_rater_count",
            "formal_agent_response_count",
            "formal_persona_score_count",
            "holdout_content_reviewed_count",
            "raw_or_verbatim_record_count",
        ):
            self.assertEqual(counts[field], 0, field)

    def test_claimed_nonzero_formal_data_without_hash_binding_is_rejected(self):
        readiness = copy.deepcopy(self.readiness)
        readiness["counts"]["target_calibration_event_count"] = 30
        report = self.run_audit(readiness=readiness)
        self.assertFalse(report["protocol_passed"])
        self.assertIn(
            "target_calibration_event_count:target_calibration_manifest",
            report["violations"]["readiness_evidence"],
        )

    def test_readiness_flags_without_hash_binding_are_rejected(self):
        readiness = copy.deepcopy(self.readiness)
        readiness["flags"]["power_plan_frozen"] = True
        report = self.run_audit(readiness=readiness)
        self.assertFalse(report["protocol_passed"])
        self.assertIn(
            "power_plan_frozen:power_plan",
            report["violations"]["readiness_evidence"],
        )
        readiness = copy.deepcopy(self.readiness)
        readiness["flags"]["pilot_completed"] = "false"
        report = self.run_audit(readiness=readiness)
        self.assertFalse(report["protocol_passed"])
        self.assertIn(
            "pilot_completed:boolean",
            report["violations"]["readiness_inventory"],
        )

    def test_data_boundary_cannot_authorize_training_or_contain_answers(self):
        readiness = copy.deepcopy(self.readiness)
        readiness["data_boundary"]["contains_target_reference_answers"] = True
        readiness["data_boundary"]["training_authorized"] = True
        report = self.run_audit(readiness=readiness)
        self.assertFalse(report["protocol_passed"])
        self.assertIn(
            "data_boundary:contains_target_reference_answers",
            report["violations"]["readiness_inventory"],
        )
        self.assertIn(
            "data_boundary:training_authorized",
            report["violations"]["readiness_inventory"],
        )

    def test_require_execution_ready_exits_nonzero_without_fabricating_data(self):
        with tempfile.TemporaryDirectory() as directory:
            output_json = Path(directory) / "audit.json"
            output_md = Path(directory) / "audit.md"
            result = subprocess.run(
                [
                    str(PYTHON),
                    str(ROOT / "public_persona_fidelity_eval_v1.py"),
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
            self.assertFalse(report["persona_score_computed"])

    def test_report_is_hash_bound_readable_and_does_not_mutate_inputs(self):
        paths = (
            DEFAULT_PREREGISTRATION,
            DEFAULT_METHOD_REGISTRY,
            DEFAULT_READINESS_INVENTORY,
        )
        before = {path: path.read_bytes() for path in paths}
        report = build_audit_from_paths()
        self.assertTrue(report["protocol_passed"])
        for artifact in (
            report["inputs"]["preregistration"],
            report["inputs"]["method_registry"],
            report["inputs"]["readiness_inventory"],
        ):
            self.assertEqual(len(artifact["sha256"]), 64)
        markdown = build_markdown(report)
        self.assertIn("協定完整：`True`", markdown)
        self.assertIn("正式執行就緒：`False`", markdown)
        self.assertIn("人格分數已計算：`False`", markdown)
        self.assertIn("同模型、同人格資訊、同預算", markdown)
        self.assertIn("校準公式示意，不是真實結果", markdown)
        self.assertIn("https://aclanthology.org/2024.acl-long.102/", markdown)
        for path in paths:
            self.assertEqual(before[path], path.read_bytes())

    def test_harness_lock_hashes_match(self):
        lock = json.loads(HARNESS_LOCK.read_text(encoding="utf-8"))
        self.assertEqual(lock["preflight"]["expected_test_count"], 20)
        for artifact in lock["frozen_artifacts"].values():
            path = ROOT / artifact["path"]
            self.assertEqual(
                hashlib.sha256(path.read_bytes()).hexdigest(), artifact["sha256"]
            )


if __name__ == "__main__":
    unittest.main()
