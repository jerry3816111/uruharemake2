import json
import unittest
from collections import Counter
from pathlib import Path

from build_source_preserving_memory_projection_v2_5_locomo_cases import file_sha256


ROOT = Path(__file__).resolve().parent
LOCK = (
    ROOT
    / "configs/source_preserving_memory_projection_v2_13_27b_capacity_result_lock.json"
)
REPORT = ROOT / "reports/source_preserving_memory_projection_v2_13_27b_capacity.json"
V2_12_REPORT = (
    ROOT / "reports/source_preserving_memory_projection_v2_12_complete_session_ceiling.json"
)


class ModelCapacityResultLockV213Tests(unittest.TestCase):
    def setUp(self):
        self.lock = json.loads(LOCK.read_text(encoding="utf-8"))
        self.report = json.loads(REPORT.read_text(encoding="utf-8"))

    def test_locked_artifacts_match(self):
        for relative, expected in self.lock["artifacts"].items():
            self.assertEqual(file_sha256(ROOT / relative), expected, relative)

    def test_locked_metrics_and_gates_match_report(self):
        self.assertEqual(self.report["metrics"], self.lock["metrics"])
        self.assertEqual(self.report["gates"], self.lock["gates"])

    def test_preregistered_resource_rejection_decision_is_preserved(self):
        self.assertEqual(self.report["decision"], self.lock["decision"])
        self.assertEqual(
            self.lock["decision_resolution"],
            {
                "integrity": "passed",
                "quality": "failed",
                "resource": "rejected",
                "selected_reason": "resource_rejected_not_integrity_invalid",
            },
        )
        failed = {name for name, passed in self.report["gates"].items() if not passed}
        self.assertEqual(failed, set(self.lock["failed_gates"]))
        self.assertEqual(
            failed,
            {
                "candidate_mean_official_f1_at_least",
                "candidate_mean_f1_delta_vs_locked_9b_at_least",
                "paired_bootstrap_95_ci_lower_greater_than",
                "candidate_mean_latency_seconds_at_most",
                "candidate_p95_latency_seconds_at_most",
            },
        )

    def test_report_contains_all_unique_paired_rows(self):
        rows = self.report["rows"]
        self.assertEqual(len(rows), 114)
        self.assertEqual(len({row["call_id"] for row in rows}), 114)
        self.assertEqual(
            Counter(row["model_condition"] for row in rows),
            Counter({"qwen3.5:9b": 57, "qwen3.5:27b": 57}),
        )
        by_case = {}
        for row in rows:
            by_case.setdefault(row["case_id"], {})[row["model_condition"]] = row
        self.assertEqual(len(by_case), 57)
        self.assertTrue(
            all(
                set(pair) == {"qwen3.5:9b", "qwen3.5:27b"}
                for pair in by_case.values()
            )
        )

    def test_historical_controls_exactly_match_v2_12(self):
        previous = json.loads(V2_12_REPORT.read_text(encoding="utf-8"))
        previous_controls = {
            row["case_id"]: row
            for row in previous["rows"]
            if row["representation"] == "complete_session"
        }
        current_controls = {
            row["case_id"]: row
            for row in self.report["rows"]
            if row["model_condition"] == "qwen3.5:9b"
        }
        self.assertEqual(len(previous_controls), 57)
        for case_id, previous_row in previous_controls.items():
            expected = dict(
                previous_row,
                model_condition="qwen3.5:9b",
                row_source="locked_v2_12_historical_control",
            )
            self.assertEqual(current_controls[case_id], expected)

    def test_zero_call_quality_diagnostics_match_rows(self):
        by_case = {}
        for row in self.report["rows"]:
            by_case.setdefault(row["case_id"], {})[row["model_condition"]] = row
        deltas = [
            pair["qwen3.5:27b"]["official_f1"]
            - pair["qwen3.5:9b"]["official_f1"]
            for pair in by_case.values()
        ]
        exact_predictions = sum(
            pair["qwen3.5:27b"]["prediction"]
            == pair["qwen3.5:9b"]["prediction"]
            for pair in by_case.values()
        )
        diagnostics = self.lock["posthoc_zero_call_diagnostics"]
        self.assertEqual(
            {
                "candidate_better_pair_count": sum(delta > 0 for delta in deltas),
                "identical_f1_pair_count": sum(delta == 0 for delta in deltas),
                "candidate_worse_pair_count": sum(delta < 0 for delta in deltas),
                "exact_prediction_match_pair_count": exact_predictions,
            },
            {
                key: diagnostics[key]
                for key in (
                    "candidate_better_pair_count",
                    "identical_f1_pair_count",
                    "candidate_worse_pair_count",
                    "exact_prediction_match_pair_count",
                )
            },
        )

    def test_rows_use_frozen_contracts_and_exclude_official_payload(self):
        candidate_contract_hash = self.lock["artifacts"][
            "configs/source_preserving_memory_projection_v2_13_27b_capacity_preregistration.json"
        ]
        self.assertFalse(self.report["contains_official_questions"])
        self.assertFalse(self.report["contains_official_answers"])
        self.assertFalse(self.report["contains_source_context_text"])
        for row in self.report["rows"]:
            if row["model_condition"] == "qwen3.5:27b":
                self.assertEqual(row["contract_sha256"], candidate_contract_hash)
            self.assertNotIn("question", row)
            self.assertNotIn("answer", row)
            self.assertNotIn("context", row)
            self.assertNotIn("prompt", row)

    def test_resources_and_authorization_preserve_evidence_boundary(self):
        metrics = self.lock["metrics"]
        diagnostics = self.lock["posthoc_zero_call_diagnostics"]
        self.assertGreater(metrics["candidate_mean_latency_seconds"], 12.0)
        self.assertGreater(metrics["candidate_p95_latency_seconds"], 15.0)
        self.assertLessEqual(metrics["candidate_max_latency_seconds"], 45.0)
        self.assertGreater(diagnostics["warm_only_mean_latency_seconds"], 12.0)
        self.assertGreater(diagnostics["warm_only_p95_latency_seconds"], 15.0)
        self.assertEqual(metrics["production_memory_write_count"], 0)
        self.assertEqual(metrics["physical_vrm_action_count"], 0)
        self.assertEqual(self.lock["authorization"], self.report["authorization"])
        self.assertFalse(any(self.lock["authorization"].values()))


if __name__ == "__main__":
    unittest.main()
