import json
import unittest
from pathlib import Path

import analyze_high_confidence_memory_recall_v1_development as analyzer
import memory_item_causal_intervention_v1 as mici


ROOT = Path(__file__).resolve().parent
PREREG = json.loads(
    (ROOT / "configs/high_confidence_memory_recall_v1_preregistration.json").read_text(
        encoding="utf-8"
    )
)
RESULT_LOCK = ROOT / "configs/high_confidence_memory_recall_v1_result_lock.json"


def row(case_id, condition, *, call_count=0, planner_path=None):
    return {
        "case_id": case_id,
        "condition": condition,
        "leftbrain_call_count": call_count,
        "elapsed_seconds": 0.2 if call_count == 0 else 60.0,
        "planner_path": planner_path,
        "target_anchor": condition in {mici.C0, mici.N1},
        "replacement_anchor": condition == mici.T2,
        "target_marker_in_plan": condition in {mici.C0, mici.N1},
        "replacement_marker_in_plan": condition == mici.T2,
        "target_marker_in_reply": condition in {mici.C0, mici.N1},
        "replacement_marker_in_reply": condition == mici.T2,
        "transport_error_count": 0,
        "production_memory_write_count": 0,
        "physical_vrm_action_count": 0,
    }


class HighConfidenceMemoryRecallV1DevelopmentTests(unittest.TestCase):
    def rows(self, candidate):
        rows = []
        for index in range(8):
            for condition in mici.CONDITIONS:
                calls = int((not candidate) or condition == mici.T1)
                path = (
                    "high_confidence_memory_recall_v1"
                    if candidate and condition in {mici.C0, mici.T2, mici.N1}
                    else None
                )
                rows.append(row(f"case-{index}", condition, call_count=calls, planner_path=path))
        return rows

    def test_passing_candidate_is_limited_to_fresh_holdout(self):
        report = analyzer.build_report(
            self.rows(candidate=False),
            self.rows(candidate=True),
            PREREG,
            preflight={"passed": True},
        )
        self.assertEqual(report["decision"], "development_reject_or_inconclusive")
        self.assertFalse(report["authorization"]["production_default_enablement"])
        self.assertEqual(
            report["posthoc_diagnostics_not_preregistered_gates"][
                "target_removed_fast_path_activation_count"
            ],
            0,
        )

        candidate = self.rows(candidate=True)
        for row_value in candidate:
            if row_value["condition"] == mici.T1:
                row_value["leftbrain_call_count"] = 0
        report = analyzer.build_report(
            self.rows(candidate=False),
            candidate,
            PREREG,
            preflight={"passed": True},
        )
        self.assertEqual(report["decision"], "development_pass_requires_fresh_holdout")
        self.assertTrue(report["authorization"]["fresh_holdout"])
        self.assertFalse(report["authorization"]["production_default_enablement"])

    def test_removed_target_leak_rejects_candidate(self):
        candidate = self.rows(candidate=True)
        for row_value in candidate:
            row_value["leftbrain_call_count"] = 0
            if row_value["condition"] == mici.T1:
                row_value["target_marker_in_plan"] = True
        report = analyzer.build_report(
            self.rows(candidate=False),
            candidate,
            PREREG,
            preflight={"passed": True},
        )
        self.assertEqual(report["decision"], "development_reject_or_inconclusive")
        self.assertFalse(report["gates"]["removed_target_does_not_leak"])

    def test_target_removed_false_fast_paths_are_counted_as_diagnostic(self):
        candidate = self.rows(candidate=True)
        for row_value in candidate:
            row_value["leftbrain_call_count"] = 0
            if row_value["condition"] == mici.T1:
                row_value["planner_path"] = "high_confidence_memory_recall_v1"
                row_value["reply"] = "unrelated memory"
        report = analyzer.build_report(
            self.rows(candidate=False),
            candidate,
            PREREG,
            preflight={"passed": True},
        )
        diagnostic = report["posthoc_diagnostics_not_preregistered_gates"]
        self.assertEqual(diagnostic["target_removed_fast_path_activation_count"], 8)
        self.assertEqual(diagnostic["target_removed_irrelevant_reply_count"], 8)

    def test_rejected_result_artifacts_are_locked(self):
        lock = json.loads(RESULT_LOCK.read_text(encoding="utf-8"))
        self.assertEqual(lock["status"], "development_rejected_locked")
        self.assertFalse(lock["authorization"]["fresh_holdout"])
        self.assertFalse(lock["authorization"]["production_default_enablement"])
        for artifact in lock["artifacts"].values():
            self.assertEqual(
                mici.file_sha256(ROOT / artifact["path"]),
                artifact["sha256"],
            )


if __name__ == "__main__":
    unittest.main()
