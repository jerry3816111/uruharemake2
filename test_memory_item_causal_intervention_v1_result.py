import json
import unittest
from pathlib import Path

import memory_item_causal_intervention_v1 as experiment


ROOT = Path(__file__).resolve().parent


class MemoryItemCausalInterventionV1ResultTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = json.loads(
            (ROOT / "reports/memory_item_causal_intervention_v1.json").read_text(encoding="utf-8")
        )
        cls.diagnosis = json.loads(
            (ROOT / "reports/memory_item_causal_intervention_v1_diagnosis.json").read_text(encoding="utf-8")
        )
        cls.lock = json.loads(
            (ROOT / "configs/memory_item_causal_intervention_v1_result_lock.json").read_text(encoding="utf-8")
        )

    def test_formal_decision_remains_inconclusive(self):
        self.assertEqual(
            self.report["decision"],
            "exact_memory_record_causality_not_supported_or_inconclusive",
        )
        self.assertFalse(self.report["integrity"]["decision_view_intervention_clean"])
        self.assertFalse(self.report["integrity"]["condition_deadline_respected"])
        self.assertFalse(self.diagnosis["decision_override_authorized"])

    def test_causal_direction_is_preserved_as_bounded_observation(self):
        summaries = self.report["condition_summaries"]
        self.assertEqual(summaries[experiment.C0]["target_marker_in_plan_rate"], 0.875)
        self.assertEqual(summaries[experiment.T1]["target_marker_in_plan_rate"], 0.0)
        self.assertEqual(summaries[experiment.T2]["replacement_marker_in_plan_rate"], 0.875)
        self.assertEqual(summaries[experiment.N1]["target_marker_in_plan_rate"], 0.875)
        self.assertEqual(
            self.report["paired_effects"]["target_removal_plan_marker"]["mean_delta"],
            0.875,
        )

    def test_diagnosis_identifies_audit_pointer_and_coverage_gap(self):
        cleanliness = self.diagnosis["cleanliness_failure_diagnosis"]
        self.assertTrue(cleanliness["all_failed_rows_are_replacement_condition"])
        self.assertEqual(cleanliness["target_semantic_marker_reappeared_in_plan_count"], 0)
        self.assertEqual(cleanliness["target_semantic_marker_reappeared_in_reply_count"], 0)
        self.assertEqual(
            self.diagnosis["coverage_diagnosis"]["uncovered_case_ids"],
            ["plant_name"],
        )

    def test_production_isolation_and_transport_integrity_passed(self):
        self.assertTrue(self.report["integrity"]["no_production_writes"])
        self.assertTrue(self.report["integrity"]["no_vrm_actions"])
        self.assertTrue(self.report["integrity"]["no_transport_errors"])
        self.assertEqual(self.report["resource_summary"]["transport_error_count"], 0)

    def test_result_lock_matches_committed_evidence(self):
        for artifact in self.lock["artifacts"].values():
            self.assertEqual(
                experiment.file_sha256(ROOT / artifact["path"]),
                artifact["sha256"],
            )
        self.assertFalse(self.lock["authorization"]["formal_decision_override"])
        self.assertEqual(
            self.lock["formal_decision"],
            self.report["decision"],
        )


if __name__ == "__main__":
    unittest.main()
