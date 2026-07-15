#!/usr/bin/env python3

import unittest

from analyze_relation_authorized_action_compiler_v57_holdout import (
    CANDIDATE,
    summarize_compiler,
)


WAVE = {"name": "play_motion", "arguments": {"motion": "wave"}}
NOD = {"name": "play_motion", "arguments": {"motion": "nod"}}


def _case(case_id, calls):
    frames = [
        {
            "domain": "motion",
            "value": call["arguments"]["motion"],
            "commitment": "requested",
        }
        for call in calls
    ]
    return {
        "id": case_id,
        "family": "synthetic",
        "source_type": "controlled_compositional",
        "expected_frames": frames,
        "expected_calls": calls,
        "expected_no_action": not calls,
    }


def _row(case, calls):
    commitments = {
        f"{frame['domain']}.{frame['value']}": frame["commitment"]
        for frame in case["expected_frames"]
    }
    return {
        "case_id": case["id"],
        "frozen_v56_commitments": commitments,
        "v56_selection_sources": {
            target_id: "deterministic_state_machine" for target_id in commitments
        },
        "candidate_compilation": {
            "accepted_calls": calls,
            "authorization_provenance_coverage": 1.0,
            "ungrounded_execution_count": 0,
            "unresolved_model_only_execution_count": 0,
            "commitment_mutation_count": 0,
        },
    }


class RelationAuthorizedCompilerV57HoldoutAnalysisTests(unittest.TestCase):
    def test_reversed_plan_is_set_exact_but_not_ordered_exact(self):
        case = _case("ordered", [WAVE, NOD])
        dataset = {"cases": [case]}
        report = summarize_compiler(
            {"case_rows": [_row(case, [NOD, WAVE])]}, dataset, CANDIDATE
        )
        self.assertEqual(report["set_exact_count"], 1)
        self.assertEqual(report["ordered_exact_count"], 0)
        self.assertEqual(report["required_call_recall"], 1.0)

    def test_always_abstaining_cannot_hide_zero_action_recall(self):
        action = _case("action", [WAVE])
        restraint = _case("restraint", [])
        dataset = {"cases": [action, restraint]}
        report = summarize_compiler(
            {
                "case_rows": [
                    _row(action, []),
                    _row(restraint, []),
                ]
            },
            dataset,
            CANDIDATE,
        )
        self.assertEqual(report["no_action_specificity"], 1.0)
        self.assertEqual(report["action_ordered_exact_accuracy"], 0.0)
        self.assertEqual(report["required_call_recall"], 0.0)
        self.assertEqual(report["ordered_exact_accuracy"], 0.5)


if __name__ == "__main__":
    unittest.main()
