import json
import unittest
from collections import Counter
from pathlib import Path

from build_source_preserving_memory_projection_v2_5_locomo_cases import file_sha256


ROOT = Path(__file__).resolve().parent
LOCK = ROOT / "configs/source_preserving_memory_projection_v2_11_model_qa_result_lock.json"
REPORT = ROOT / "reports/source_preserving_memory_projection_v2_11_model_qa.json"


class ModelQAResultLockV211Tests(unittest.TestCase):
    def setUp(self):
        self.lock = json.loads(LOCK.read_text(encoding="utf-8"))
        self.report = json.loads(REPORT.read_text(encoding="utf-8"))

    def test_locked_artifacts_match(self):
        for relative, expected in self.lock["artifacts"].items():
            self.assertEqual(file_sha256(ROOT / relative), expected, relative)

    def test_locked_metrics_and_gates_match_report(self):
        self.assertEqual(self.report["metrics"], self.lock["metrics"])
        self.assertEqual(self.report["gates"], self.lock["gates"])

    def test_preregistered_failure_is_preserved(self):
        self.assertEqual(self.report["decision"], self.lock["decision"])
        failed = {name for name, passed in self.report["gates"].items() if not passed}
        self.assertEqual(failed, set(self.lock["failed_gates"]))
        self.assertEqual(
            failed,
            {
                "adjacency_mean_official_f1_at_least",
                "adjacency_mean_f1_delta_vs_isolated_at_least",
                "paired_bootstrap_95_ci_lower_greater_than",
            },
        )

    def test_report_contains_all_unique_paired_calls(self):
        rows = self.report["rows"]
        self.assertEqual(len(rows), 114)
        self.assertEqual(len({row["call_id"] for row in rows}), 114)
        self.assertEqual(
            Counter(row["representation"] for row in rows),
            Counter({"isolated": 57, "adjacency": 57}),
        )
        by_case = {}
        for row in rows:
            by_case.setdefault(row["case_id"], set()).add(row["representation"])
        self.assertEqual(len(by_case), 57)
        self.assertTrue(
            all(conditions == {"isolated", "adjacency"} for conditions in by_case.values())
        )
        self.assertEqual(
            sum(
                row["representation"] == "adjacency"
                and row["evidence_transition"] == "adjacency_only"
                for row in rows
            ),
            12,
        )

    def test_rows_use_frozen_contract_and_exclude_official_payload(self):
        contract_hash = self.lock["artifacts"][
            "configs/source_preserving_memory_projection_v2_11_model_qa_preregistration.json"
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

    def test_failure_authorizes_no_upper_evidence_layer(self):
        authorization = self.lock["authorization"]
        self.assertFalse(authorization["preregister_full_pipeline_memory_intervention"])
        self.assertFalse(authorization["runtime_change"])
        self.assertFalse(authorization["runtime_shadow"])
        self.assertFalse(authorization["production_enablement"])
        self.assertEqual(authorization, self.report["authorization"])


if __name__ == "__main__":
    unittest.main()
