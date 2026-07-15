#!/usr/bin/env python3

import hashlib
import json
import subprocess
import unittest
from pathlib import Path

from analyze_predicate_morphology_v60_independent_holdout import summarize_morphology
from run_predicate_morphology_v60_independent_holdout import CONDITIONS


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "predicate_morphology_v60_independent_holdout_preregistration.json"
LOCK_PATH = ROOT / "configs" / "predicate_morphology_v60_independent_holdout_harness_lock.json"


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class PredicateMorphologyV60IndependentHoldoutHarnessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        cls.lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
        cls.runner_source = (
            ROOT / cls.lock["frozen_artifacts"]["runner"]
        ).read_text(encoding="utf-8")
        cls.analyzer_source = (
            ROOT / cls.lock["frozen_artifacts"]["analyzer"]
        ).read_text(encoding="utf-8")

    def test_every_harness_artifact_is_hash_bound(self):
        frozen = self.lock["frozen_artifacts"]
        for key, expected in frozen.items():
            if not key.endswith("_sha256"):
                continue
            path_key = key.removesuffix("_sha256")
            self.assertIn(path_key, frozen)
            self.assertEqual(_sha256(ROOT / frozen[path_key]), expected, path_key)

    def test_conditions_model_budget_and_main_branch_are_frozen(self):
        self.assertEqual(tuple(self.config["conditions"]), CONDITIONS)
        self.assertEqual(tuple(self.lock["conditions"]), CONDITIONS)
        self.assertEqual(self.config["model_call_budget"], 120)
        self.assertEqual(self.lock["model_calls_authorized"], 120)
        self.assertEqual(self.lock["shared_fallback_calls_per_target"], 1)
        self.assertEqual(self.lock["required_run_branch"], "main")

    def test_runner_rejects_dirty_or_drifting_resumes(self):
        for required in (
            "_git_tracked_tree_clean()",
            '("model_snapshot", snapshot)',
            '("candidate_rows", candidate_rows)',
            '("construction_audit", construction)',
            '"transport_attempts_made"',
        ):
            self.assertIn(required, self.runner_source)
        self.assertIn(
            "V60 holdout transport-attempt accounting mismatch",
            self.analyzer_source,
        )

    def test_runner_uses_one_shared_fallback_for_both_states(self):
        self.assertEqual(self.runner_source.count("_run_judgment("), 1)
        for required in (
            "fallback = (",
            "resolve_v59(",
            "resolve_v60(",
            "select_commitment(state59, fallback)",
            "select_commitment(state60, fallback)",
            '"shared_fallback_commitment": fallback',
        ):
            self.assertIn(required, self.runner_source)
        for forbidden in ("expected_frames", "expected_calls"):
            self.assertNotIn(forbidden, self.runner_source)

    def test_same_frozen_compiler_is_used_for_both_conditions(self):
        self.assertEqual(
            self.runner_source.count("compile_relation_authorized_v57("), 2
        )
        self.assertNotIn("compile_target_relative_v48", self.runner_source)

    def test_analyzer_contains_every_preregistered_gate_group(self):
        for required in (
            '"state_external_accuracy"',
            '"compiler_external_accuracy"',
            '"compiler_false_actions"',
            '"morphology_controlled_slots"',
            '"morphology_completed_relation"',
            '"morphology_polite_relation"',
            '"morphology_omitted_direct"',
            '"morphology_full_direct"',
            '"morphology_embedded_relation"',
            '"matched_state_gain"',
            '"matched_case_gain"',
            '"matched_state_regressions"',
            '"matched_case_regressions"',
            '"matched_exact_mcnemar"',
        ):
            self.assertIn(required, self.analyzer_source)

    def test_perfect_synthetic_morphology_contract_scores_every_slot(self):
        contracts = self.config["expected_morphology_by_family"]
        cases = []
        rows = []
        for index, (family, contract) in enumerate(contracts.items()):
            case_id = f"synthetic_{index}"
            cases.append({"id": case_id, "family": family})
            rows.append(
                {
                    "case_id": case_id,
                    "target_id": "expression.happy",
                    "candidate_state": {
                        "v60_event_role_graph": {
                            "event_owner": contract["event_owner"],
                            "directive_governor": contract["request_governor"],
                            "direct_focus_request": contract["direct_focus_request"],
                            "relation_types": contract["relation_types"],
                            "v60_predicate_morphology": {
                                "predicate_force": contract["predicate_force"],
                                "event_aspect": contract["event_aspect"],
                            },
                        }
                    },
                }
            )
        summary = summarize_morphology(
            {"target_rows": rows}, {"cases": cases}, self.config
        )
        self.assertEqual(summary["controlled_slot_correct_count"], 42)
        self.assertEqual(summary["controlled_slot_count"], 42)
        self.assertEqual(summary["controlled_slot_accuracy"], 1.0)

    def test_result_did_not_exist_when_harness_was_frozen(self):
        result_path = ROOT / self.lock["result_artifacts"]["raw"]
        if not result_path.exists():
            self.assertFalse(result_path.exists())
            return
        freeze_commit = subprocess.check_output(
            [
                "git",
                "log",
                "--diff-filter=A",
                "--format=%H",
                "-1",
                "--",
                str(LOCK_PATH.relative_to(ROOT)),
            ],
            cwd=ROOT,
            text=True,
        ).strip()
        self.assertTrue(freeze_commit)
        historical_result = subprocess.run(
            [
                "git",
                "cat-file",
                "-e",
                f"{freeze_commit}:{result_path.relative_to(ROOT)}",
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(historical_result.returncode, 0)

    def test_harness_authorizes_no_post_result_changes_or_deployment(self):
        for key in (
            "post_run_metric_changes_authorized",
            "post_run_threshold_changes_authorized",
            "post_run_case_exclusion_authorized",
            "runtime_change_authorized",
            "shadow_integration_authorized",
            "physical_vrm_execution_enabled",
            "complete_rightbrain_claim_authorized",
            "broad_human_likeness_claim_authorized",
        ):
            self.assertFalse(self.lock[key], key)


if __name__ == "__main__":
    unittest.main()
