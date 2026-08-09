import json
import unittest
from collections import Counter
from pathlib import Path

from build_source_preserving_memory_projection_v2_5_locomo_cases import file_sha256


ROOT = Path(__file__).resolve().parent
LOCK = (
    ROOT
    / "configs/source_preserving_memory_projection_v2_12_complete_session_ceiling_result_lock.json"
)
REPORT = (
    ROOT / "reports/source_preserving_memory_projection_v2_12_complete_session_ceiling.json"
)
V2_11_REPORT = ROOT / "reports/source_preserving_memory_projection_v2_11_model_qa.json"


class CompleteSessionCeilingResultLockV212Tests(unittest.TestCase):
    def setUp(self):
        self.lock = json.loads(LOCK.read_text(encoding="utf-8"))
        self.report = json.loads(REPORT.read_text(encoding="utf-8"))

    def test_locked_artifacts_match(self):
        for relative, expected in self.lock["artifacts"].items():
            self.assertEqual(file_sha256(ROOT / relative), expected, relative)

    def test_locked_metrics_and_gates_match_report(self):
        self.assertEqual(self.report["metrics"], self.lock["metrics"])
        self.assertEqual(self.report["gates"], self.lock["gates"])

    def test_preregistered_low_ceiling_decision_is_preserved(self):
        self.assertEqual(self.report["decision"], self.lock["decision"])
        failed = {name for name, passed in self.report["gates"].items() if not passed}
        self.assertEqual(failed, set(self.lock["failed_gates"]))
        self.assertEqual(
            failed,
            {
                "complete_session_mean_official_f1_at_least",
                "complete_session_mean_f1_delta_vs_adjacency_at_least",
            },
        )

    def test_report_contains_all_unique_paired_calls(self):
        rows = self.report["rows"]
        self.assertEqual(len(rows), 114)
        self.assertEqual(len({row["call_id"] for row in rows}), 114)
        self.assertEqual(
            Counter(row["representation"] for row in rows),
            Counter({"adjacency": 57, "complete_session": 57}),
        )
        by_case = {}
        for row in rows:
            by_case.setdefault(row["case_id"], {})[row["representation"]] = row
        self.assertEqual(len(by_case), 57)
        self.assertTrue(
            all(set(pair) == {"adjacency", "complete_session"} for pair in by_case.values())
        )
        deltas = [
            pair["complete_session"]["official_f1"]
            - pair["adjacency"]["official_f1"]
            for pair in by_case.values()
        ]
        self.assertEqual(
            {
                "complete_better_pair_count": sum(delta > 0 for delta in deltas),
                "identical_f1_pair_count": sum(delta == 0 for delta in deltas),
                "complete_worse_pair_count": sum(delta < 0 for delta in deltas),
            },
            self.lock["posthoc_zero_call_diagnostics"],
        )

    def test_adjacency_control_exactly_reproduces_v2_11(self):
        previous = json.loads(V2_11_REPORT.read_text(encoding="utf-8"))
        previous_adjacency = {
            row["case_id"]: (row["prompt_sha256"], row["prediction"], row["official_f1"])
            for row in previous["rows"]
            if row["representation"] == "adjacency"
        }
        current_adjacency = {
            row["case_id"]: (row["prompt_sha256"], row["prediction"], row["official_f1"])
            for row in self.report["rows"]
            if row["representation"] == "adjacency"
        }
        self.assertEqual(current_adjacency, previous_adjacency)
        self.assertEqual(
            len(current_adjacency),
            self.lock["reproducibility_audit"]["adjacency_prediction_count"],
        )
        self.assertEqual(
            len(current_adjacency),
            self.lock["reproducibility_audit"][
                "adjacency_predictions_exactly_reproduced_vs_v2_11"
            ],
        )

    def test_rows_use_frozen_contract_and_exclude_official_payload(self):
        contract_hash = self.lock["artifacts"][
            "configs/source_preserving_memory_projection_v2_12_complete_session_ceiling_preregistration.json"
        ]
        self.assertFalse(self.report["contains_official_questions"])
        self.assertFalse(self.report["contains_official_answers"])
        self.assertFalse(self.report["contains_source_context_text"])
        for row in self.report["rows"]:
            self.assertEqual(row["contract_sha256"], contract_hash)
            self.assertNotIn("question", row)
            self.assertNotIn("answer", row)
            self.assertNotIn("context", row)
            self.assertNotIn("prompt", row)

    def test_costs_and_authorization_preserve_evidence_boundary(self):
        metrics = self.lock["metrics"]
        self.assertLess(metrics["max_prompt_eval_count"], 8192)
        self.assertLessEqual(metrics["mean_model_output_tokens"], 32)
        self.assertGreater(
            metrics["mean_latency_seconds_by_condition"]["complete_session"],
            metrics["mean_latency_seconds_by_condition"]["adjacency"],
        )
        authorization = self.lock["authorization"]
        self.assertFalse(authorization["preregister_projection_coherence_development"])
        self.assertTrue(authorization["preregister_model_prompt_capacity_diagnostic"])
        self.assertFalse(authorization["preregister_full_pipeline_memory_intervention"])
        self.assertFalse(authorization["runtime_change"])
        self.assertFalse(authorization["runtime_shadow"])
        self.assertFalse(authorization["production_enablement"])
        self.assertEqual(authorization, self.report["authorization"])


if __name__ == "__main__":
    unittest.main()
