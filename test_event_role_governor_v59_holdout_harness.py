#!/usr/bin/env python3

import hashlib
import json
import subprocess
import unittest
from pathlib import Path

from action_selective_deliberation_v37 import FRAME_TO_CALL
from analyze_event_role_governor_v59_holdout import (
    _two_sided_exact_mcnemar,
    analyze,
    summarize_event_roles,
)
from run_event_role_governor_v59_holdout import CANDIDATE, CONDITIONS, CONTROL


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "event_role_governor_v59_holdout_preregistration.json"
LOCK_PATH = ROOT / "configs" / "event_role_governor_v59_holdout_harness_lock.json"
DATASET_PATH = ROOT / "datasets" / "event_role_governor_v59_holdout.json"


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class EventRoleGovernorV59HoldoutHarnessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        load = lambda path: json.loads(path.read_text(encoding="utf-8"))
        cls.config = load(CONFIG_PATH)
        cls.lock = load(LOCK_PATH)
        cls.dataset = load(DATASET_PATH)
        cls.runner_source = (ROOT / cls.lock["frozen_artifacts"]["runner"]).read_text(
            encoding="utf-8"
        )
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

    def test_conditions_match_the_merged_preregistration(self):
        self.assertEqual(tuple(self.config["conditions"]), CONDITIONS)
        self.assertEqual(tuple(self.lock["conditions"]), CONDITIONS)
        self.assertEqual(CONDITIONS, (CONTROL, CANDIDATE))

    def test_one_model_call_is_shared_between_both_state_resolvers(self):
        self.assertEqual(self.runner_source.count("_run_judgment("), 1)
        for required in (
            "fallback = (",
            "state58 = resolve_v58(",
            "state59 = resolve_v59(",
            "select_commitment(state58, fallback)",
            "select_commitment(state59, fallback)",
        ):
            self.assertIn(required, self.runner_source)
        self.assertEqual(self.lock["model_calls_authorized"], 73)
        self.assertEqual(self.lock["shared_fallback_calls_per_target"], 1)

    def test_runner_never_reads_gold_and_uses_same_compiler_twice(self):
        for forbidden in (
            "expected_frames",
            "expected_calls",
            "candidate_state_gates",
            "matched_comparison_gates",
        ):
            self.assertNotIn(forbidden, self.runner_source)
        self.assertEqual(
            self.runner_source.count("compile_relation_authorized_v57("), 2
        )
        self.assertFalse(self.lock["gold_visible_to_runner_model_state_or_compiler"])

    def test_analyzer_contains_every_preregistered_absolute_and_paired_gate(self):
        for required in (
            '"state_correct_count"',
            '"state_requested_precision"',
            '"state_requested_recall"',
            '"compiler_false_actions"',
            '"compiler_required_call_recall"',
            '"event_role_each_relation_family"',
            '"event_role_contrast_false_positives"',
            '"event_role_direct_focus_recall"',
            '"event_role_slot_accuracy"',
            '"matched_state_gain"',
            '"matched_case_fixes"',
            '"matched_state_regressions"',
            '"matched_case_regressions"',
            '"matched_exact_mcnemar"',
        ):
            self.assertIn(required, self.analyzer_source)

    def test_exact_mcnemar_gate_requires_six_one_way_case_fixes(self):
        self.assertEqual(_two_sided_exact_mcnemar(6, 0), 0.03125)
        self.assertEqual(_two_sided_exact_mcnemar(5, 0), 0.0625)
        self.assertEqual(_two_sided_exact_mcnemar(6, 1), 0.125)
        self.assertEqual(_two_sided_exact_mcnemar(0, 0), 1.0)

    def test_role_slot_scoring_has_280_frozen_controlled_slots(self):
        contracts = self.config["expected_event_roles_by_family"]
        target_rows = []
        for case in self.dataset["cases"]:
            contract = contracts.get(case["family"])
            if contract is None:
                continue
            frame = case["expected_frames"][0]
            expected_relation = contract["relation_type"]
            target_rows.append(
                {
                    "case_id": case["id"],
                    "target_id": f"{frame['domain']}.{frame['value']}",
                    "candidate_state": {
                        "v59_event_role_graph": {
                            "relation_types": (
                                [expected_relation] if expected_relation else []
                            ),
                            "event_owner": contract["event_owner_allowed"][0],
                            "directive_governor": contract["directive_governor"],
                            "event_time": contract["event_time_allowed"][0],
                            "direct_focus_request": contract["direct_focus_request"],
                        }
                    },
                }
            )
        summary = summarize_event_roles(
            {"target_rows": target_rows}, self.dataset, self.config
        )
        self.assertEqual(summary["expected_relation_target_count"], 42)
        self.assertEqual(summary["expected_relation_detected_count"], 42)
        self.assertEqual(summary["direct_focus_request_target_count"], 14)
        self.assertEqual(summary["direct_focus_request_detected_count"], 14)
        self.assertEqual(summary["role_slot_count"], 280)
        self.assertEqual(summary["role_slot_correct_count"], 280)

    def test_synthetic_six_fix_zero_regression_run_passes_every_frozen_gate(self):
        contracts = self.config["expected_event_roles_by_family"]
        fix_ids = {
            case["id"]
            for case in self.dataset["cases"]
            if case["family"] == "controlled_embedded_speech_content"
        }
        fix_ids = set(sorted(fix_ids)[:6])
        target_rows = []
        case_rows = []
        for case in self.dataset["cases"]:
            control_commitments = {}
            candidate_commitments = {}
            contract = contracts.get(case["family"])
            for frame in case["expected_frames"]:
                target_id = f"{frame['domain']}.{frame['value']}"
                expected = frame["commitment"]
                control = "requested" if case["id"] in fix_ids else expected
                control_commitments[target_id] = control
                candidate_commitments[target_id] = expected
                graph = {
                    "relation_types": [],
                    "event_owner": "unknown",
                    "directive_governor": "unknown",
                    "event_time": "unknown",
                    "direct_focus_request": False,
                }
                if contract is not None:
                    relation = contract["relation_type"]
                    graph = {
                        "relation_types": [relation] if relation else [],
                        "event_owner": contract["event_owner_allowed"][0],
                        "directive_governor": contract["directive_governor"],
                        "event_time": contract["event_time_allowed"][0],
                        "direct_focus_request": contract["direct_focus_request"],
                    }
                target_rows.append(
                    {
                        "case_id": case["id"],
                        "target_id": target_id,
                        "shared_fallback_commitment": "mentioned",
                        "control_state": {},
                        "control_commitment": control,
                        "control_selection_source": "deterministic_state_machine",
                        "candidate_state": {"v59_event_role_graph": graph},
                        "candidate_commitment": expected,
                        "candidate_selection_source": "deterministic_state_machine",
                    }
                )
            control_calls = list(case["expected_calls"])
            if case["id"] in fix_ids:
                frame = case["expected_frames"][0]
                control_calls = [FRAME_TO_CALL[(frame["domain"], frame["value"])]]

            def compilation(calls):
                return {
                    "accepted_calls": calls,
                    "authorization_provenance_coverage": 1.0,
                    "ungrounded_execution_count": 0,
                    "commitment_mutation_count": 0,
                }

            case_rows.append(
                {
                    "case_id": case["id"],
                    "control_commitments": control_commitments,
                    "candidate_commitments": candidate_commitments,
                    "control_compilation": compilation(control_calls),
                    "candidate_compilation": compilation(case["expected_calls"]),
                }
            )
        raw = {
            "evidence_status": "synthetic_harness_test_only",
            "conditions": list(CONDITIONS),
            "target_rows": target_rows,
            "case_rows": case_rows,
            "model_calls_made": 73,
            "paid_api_used": False,
            "physical_vrm_actions_executed": 0,
            "construction_audit": {"passed": True},
        }
        report = analyze(raw, self.dataset, self.config)
        self.assertTrue(report["gates"]["passed"])
        self.assertEqual(report["matched_comparison"]["case_fix_count"], 6)
        self.assertEqual(report["matched_comparison"]["case_regression_count"], 0)
        self.assertEqual(
            report["matched_comparison"]["two_sided_exact_mcnemar_p"], 0.03125
        )

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
        )
        self.assertNotEqual(historical_result.returncode, 0)

    def test_harness_requires_merged_main_and_forbids_post_result_changes(self):
        self.assertEqual(self.lock["required_run_branch"], "main")
        for key in (
            "holdout_inference_before_harness_merge_authorized",
            "post_result_metric_changes_authorized",
            "post_result_threshold_changes_authorized",
            "post_result_case_exclusion_authorized",
            "post_result_model_change_authorized",
            "runtime_change_authorized",
            "shadow_integration_authorized",
            "physical_vrm_execution_enabled",
            "complete_rightbrain_claim_authorized",
            "broad_human_likeness_claim_authorized",
        ):
            self.assertFalse(self.lock[key], key)


if __name__ == "__main__":
    unittest.main()
