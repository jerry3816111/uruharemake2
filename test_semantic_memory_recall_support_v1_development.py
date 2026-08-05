import json
import unittest
from pathlib import Path

import analyze_semantic_memory_recall_support_v1_development as analysis
import memory_item_causal_intervention_v1 as mici


ROOT = Path(__file__).resolve().parent


def synthetic_rows(*, false_removed_fast=False):
    rows = []
    for index in range(8):
        for condition in mici.CONDITIONS:
            valid = condition in {mici.C0, mici.T2, mici.N1}
            planner_path = "high_confidence_memory_recall_v1" if valid else "model"
            if condition == mici.T1 and index < 2:
                planner_path = "existing_rule"
            if false_removed_fast and condition == mici.T1 and index == 0:
                planner_path = "high_confidence_memory_recall_v1"
            rows.append(
                {
                    "condition": condition,
                    "planner_path": planner_path,
                    "leftbrain_call_count": int(planner_path == "model"),
                    "elapsed_seconds": 0.01,
                    "target_marker_in_plan": condition in {mici.C0, mici.N1},
                    "target_marker_in_reply": condition in {mici.C0, mici.N1},
                    "target_anchor": condition in {mici.C0, mici.N1},
                    "replacement_marker_in_plan": condition == mici.T2,
                    "replacement_marker_in_reply": condition == mici.T2,
                    "replacement_anchor": condition == mici.T2,
                    "memory_recall_contract": {
                        "shared_focus_unit_count": int(
                            planner_path == "high_confidence_memory_recall_v1"
                        )
                    },
                    "transport_error_count": 0,
                    "production_memory_write_count": 0,
                    "physical_vrm_action_count": 0,
                }
            )
    return rows


class SemanticMemoryRecallSupportV1DevelopmentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.prereg = json.loads(
            (ROOT / "configs/semantic_memory_recall_support_v1_preregistration.json").read_text(
                encoding="utf-8"
            )
        )
        cls.metadata = {
            "preflight": {"passed": True},
            "boundary_probes": {
                "sensitive": {"selected": False},
                "non_recall": {"selected": False},
                "ambiguous": {"selected": False},
            },
        }

    def test_passing_fixture_authorizes_only_fresh_holdout(self):
        rows = synthetic_rows()
        report = analysis.build_report(rows, rows, rows, self.prereg, self.metadata)

        self.assertEqual(report["decision"], "development_pass_requires_fresh_holdout")
        self.assertTrue(report["authorization"]["fresh_holdout"])
        self.assertFalse(report["authorization"]["production_default_enablement"])

    def test_any_target_removed_fast_path_rejects_development(self):
        baseline = synthetic_rows()
        candidate = synthetic_rows(false_removed_fast=True)
        report = analysis.build_report(
            baseline,
            baseline,
            candidate,
            self.prereg,
            self.metadata,
        )

        self.assertEqual(report["decision"], "development_reject_or_inconclusive")
        self.assertFalse(report["gates"]["no_target_removed_fast_path"])


if __name__ == "__main__":
    unittest.main()
