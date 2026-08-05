import json
import unittest
from pathlib import Path

from build_source_preserving_memory_projection_v2_5_locomo_cases import file_sha256


ROOT = Path(__file__).resolve().parent
LOCK = ROOT / "configs/source_preserving_memory_projection_v2_10_final_reserve_result_lock.json"
REPORT = ROOT / "reports/source_preserving_memory_projection_v2_10_final_reserve.json"


class FinalReserveResultLockV210Tests(unittest.TestCase):
    def setUp(self):
        self.lock = json.loads(LOCK.read_text(encoding="utf-8"))
        self.report = json.loads(REPORT.read_text(encoding="utf-8"))

    def test_locked_artifacts_match(self):
        for relative, expected in self.lock["artifacts"].items():
            self.assertEqual(file_sha256(ROOT / relative), expected, relative)

    def test_all_preregistered_gates_passed_without_model_or_side_effects(self):
        self.assertTrue(all(self.report["gates"].values()))
        self.assertEqual(self.report["metrics"]["model_calls"], 0)
        self.assertEqual(self.report["metrics"]["production_memory_write_count"], 0)
        self.assertEqual(self.report["metrics"]["physical_vrm_action_count"], 0)
        self.assertEqual(
            self.report["metrics"]["final_reserve_evaluation_payload_access_count"],
            2,
        )

    def test_locked_metrics_match_report(self):
        for name, expected in self.lock["metrics"].items():
            self.assertEqual(self.report["metrics"][name], expected, name)

    def test_paired_transitions_match_case_diagnostics(self):
        transitions = {key: 0 for key in ("both", "isolated_only", "adjacency_only", "neither")}
        for case in self.report["cases"]:
            isolated = case["isolated"]["contains_all_official_evidence"]
            adjacency = case["adjacency"]["contains_all_official_evidence"]
            if isolated and adjacency:
                transitions["both"] += 1
            elif isolated:
                transitions["isolated_only"] += 1
            elif adjacency:
                transitions["adjacency_only"] += 1
            else:
                transitions["neither"] += 1
        self.assertEqual(transitions, self.lock["paired_full_evidence_transitions"])

    def test_report_uses_aliases_and_excludes_official_content(self):
        self.assertFalse(self.report["contains_official_text"])
        self.assertFalse(self.report["contains_official_answers"])
        self.assertEqual(
            {case["sample_id"] for case in self.report["cases"]},
            {"final-reserve-1", "final-reserve-2"},
        )
        for case in self.report["cases"]:
            self.assertNotIn("question", case)
            self.assertNotIn("answer", case)
            self.assertNotIn("evidence_ids", case)
            self.assertNotIn("text", case)

    def test_only_independent_model_preregistration_is_authorized(self):
        authorization = self.lock["authorization"]
        self.assertTrue(authorization["preregister_independent_model_evaluation"])
        self.assertFalse(authorization["run_model_generation"])
        self.assertFalse(authorization["runtime_change"])
        self.assertFalse(authorization["runtime_shadow"])
        self.assertFalse(authorization["production_enablement"])


if __name__ == "__main__":
    unittest.main()
