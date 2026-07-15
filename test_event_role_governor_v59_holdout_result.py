#!/usr/bin/env python3

import hashlib
import json
import unittest
from pathlib import Path

from run_event_role_governor_v59_holdout import CANDIDATE, CONTROL


ROOT = Path(__file__).resolve().parent
CLOSURE_PATH = ROOT / "configs" / "event_role_governor_v59_holdout_closure.json"
RAW_PATH = ROOT / "reports" / "event_role_governor_v59_holdout_raw.json"
ANALYSIS_PATH = ROOT / "reports" / "event_role_governor_v59_holdout_analysis.json"


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class EventRoleGovernorV59HoldoutResultTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        load = lambda path: json.loads(path.read_text(encoding="utf-8"))
        cls.closure = load(CLOSURE_PATH)
        cls.raw = load(RAW_PATH)
        cls.analysis = load(ANALYSIS_PATH)

    def test_every_result_artifact_is_hash_bound(self):
        bindings = self.closure["artifact_bindings"]
        for key, expected in bindings.items():
            if not key.endswith("_sha256"):
                continue
            path_key = key.removesuffix("_sha256")
            self.assertIn(path_key, bindings)
            self.assertEqual(_sha256(ROOT / bindings[path_key]), expected, path_key)

    def test_run_started_from_merged_frozen_commit_and_used_one_local_call_per_target(self):
        self.assertEqual(self.raw["runner_commit"], self.closure["frozen_run_commit"])
        self.assertEqual(self.raw["conditions"], [CONTROL, CANDIDATE])
        self.assertEqual(len(self.raw["target_rows"]), 73)
        self.assertEqual(len(self.raw["case_rows"]), 72)
        self.assertEqual(self.raw["model_calls_made"], 73)
        self.assertEqual(
            sum(row["fresh_v51_result"]["transport_attempts"] for row in self.raw["target_rows"]),
            73,
        )
        self.assertTrue(
            all(row["fresh_v51_result"]["parsed"]["parse_success"] for row in self.raw["target_rows"])
        )
        self.assertFalse(self.raw["paid_api_used"])
        self.assertEqual(self.raw["physical_vrm_actions_executed"], 0)

    def test_large_matched_gain_is_preserved_without_hiding_rejection(self):
        comparison = self.analysis["matched_comparison"]
        self.assertEqual(comparison["state_correct_count_delta"], 21)
        self.assertEqual(comparison["ordered_exact_count_delta"], 20)
        self.assertEqual(comparison["case_fix_count"], 20)
        self.assertEqual(comparison["state_regression_count"], 0)
        self.assertEqual(comparison["case_regression_count"], 0)
        self.assertEqual(
            comparison["two_sided_exact_mcnemar_p"], 1.9073486328125e-06
        )
        self.assertFalse(self.analysis["gates"]["passed"])

    def test_all_controlled_cases_pass_but_four_external_false_actions_reject_v59(self):
        candidate = self.analysis["candidate_compiler"]
        self.assertEqual(candidate["ordered_exact_count"], 68)
        self.assertEqual(candidate["action_ordered_exact_count"], 14)
        self.assertEqual(candidate["required_call_recall"], 1.0)
        self.assertEqual(
            candidate["source_groups"]["controlled_researcher_authored"]["accuracy"],
            1.0,
        )
        self.assertEqual(candidate["source_groups"]["external_exact"]["accuracy"], 0.75)
        self.assertEqual(candidate["false_action_case_count"], 4)
        self.assertEqual(
            set(candidate["false_action_case_ids"]),
            {
                "v59h_tatoeba_87104",
                "v59h_tatoeba_89563",
                "v59h_tatoeba_96980",
                "v59h_tatoeba_10550376",
            },
        )

    def test_relations_generalize_but_direct_and_role_slots_miss_their_gates(self):
        roles = self.analysis["event_role_generalization"]
        self.assertEqual(roles["expected_relation_detected_count"], 42)
        self.assertEqual(roles["expected_relation_coverage"], 1.0)
        self.assertEqual(roles["contrast_blocking_relation_target_count"], 0)
        self.assertEqual(roles["direct_focus_request_detected_count"], 11)
        self.assertEqual(roles["direct_focus_request_target_count"], 14)
        self.assertEqual(roles["role_slot_correct_count"], 261)
        self.assertEqual(roles["role_slot_count"], 280)

    def test_four_false_actions_are_deterministic_not_model_or_compiler_failures(self):
        false_ids = set(self.analysis["candidate_compiler"]["false_action_case_ids"])
        rows = [row for row in self.raw["target_rows"] if row["case_id"] in false_ids]
        self.assertEqual(len(rows), 4)
        for row in rows:
            self.assertEqual(row["shared_fallback_commitment"], "mentioned")
            self.assertEqual(row["candidate_commitment"], "requested")
            self.assertEqual(row["candidate_selection_source"], "deterministic_state_machine")
            graph = row["candidate_state"]["v59_event_role_graph"]
            self.assertEqual(graph["event_owner"], "third_party")
            self.assertEqual(graph["event_time"], "unknown")
            self.assertEqual(graph["relation_types"], [])
        self.assertEqual(
            self.analysis["residual_attribution"]["compiler_only_failure_case_count"],
            0,
        )

    def test_rejection_routes_to_representation_before_model_size(self):
        attribution = self.closure["failure_attribution"]
        self.assertFalse(
            attribution["deterministic_false_action_gap"]["model_size_is_primary_cause"]
        )
        self.assertEqual(
            attribution["shared_fallback_semantic_residual"]["count"], 1
        )
        self.assertIn(
            "changing model size now would mix variables",
            attribution["shared_fallback_semantic_residual"]["reason_not_next_variable"],
        )

    def test_failed_candidate_authorizes_no_deployment_or_broad_claim(self):
        expected = "reject_v59_independent_advancement_and_attribute_failure"
        self.assertEqual(self.analysis["decision"], expected)
        self.assertEqual(self.closure["decision"], expected)
        self.assertEqual(
            self.analysis["gates"]["failed_checks"],
            self.closure["failed_preregistered_checks"],
        )
        for key in (
            "runtime_change_authorized",
            "shadow_integration_authorized",
            "physical_vrm_execution_enabled",
            "complete_rightbrain_claim_authorized",
            "broad_human_likeness_claim_authorized",
        ):
            self.assertFalse(self.closure[key], key)


if __name__ == "__main__":
    unittest.main()
