import json
import unittest
from pathlib import Path

import audit_planner_supervision_v75 as audit_module


ROOT = Path(__file__).resolve().parent
CONTRACT = ROOT / "configs/planner_supervision_v75_readiness_contract.json"
REPORT = ROOT / "reports/planner_supervision_v75_readiness.json"


class PlannerSupervisionV75ReadinessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        cls.report = json.loads(REPORT.read_text(encoding="utf-8"))

    def test_report_is_reproducible_from_registered_sources(self):
        self.assertEqual(self.report, audit_module.build_audit())
        self.assertTrue(self.report["audit_integrity_passed"])
        self.assertFalse(self.report["discovery"]["unregistered_plan_signature_files"])

    def test_current_repository_is_not_authorized_for_planner_training(self):
        self.assertEqual(self.report["readiness"], "not_ready")
        self.assertEqual(self.report["decision"], "do_not_train_collect_strict_full_plan_supervision")
        self.assertFalse(self.report["authorizations"]["planner_training"])
        self.assertFalse(self.report["authorizations"]["runtime_change"])
        self.assertEqual(self.report["totals"]["training_eligible_count"], 0)

    def test_complete_model_plans_are_protected_not_training_answers(self):
        sources = {row["source_id"]: row for row in self.report["source_audits"]}
        self.assertEqual(sources["v61_formal_plan_captures"]["complete_plan_count"], 30)
        self.assertEqual(sources["v63_formal_plan_captures"]["complete_plan_count"], 14)
        self.assertTrue(sources["v61_formal_plan_captures"]["protected_evaluation"])
        self.assertTrue(sources["v63_formal_plan_captures"]["protected_evaluation"])
        self.assertEqual(sources["v61_formal_plan_captures"]["strict_plan_accept_count"], 0)
        self.assertEqual(sources["v63_formal_plan_captures"]["strict_plan_accept_count"], 0)
        self.assertEqual(self.report["totals"]["protected_complete_plan_count"], 44)
        self.assertEqual(self.report["totals"]["unprotected_complete_plan_count"], 0)

    def test_surface_training_is_not_misclassified_as_planner_supervision(self):
        sources = {row["source_id"]: row for row in self.report["source_audits"]}
        surface = sources["canonical_rightbrain_surface_training"]
        self.assertEqual(surface["record_count"], 1025)
        self.assertEqual(surface["complete_plan_count"], 0)
        self.assertEqual(surface["raw_user_utterance_count"], 0)
        self.assertEqual(surface["training_eligible_count"], 0)

    def test_human_surface_labels_do_not_become_plan_acceptance(self):
        sources = {row["source_id"]: row for row in self.report["source_audits"]}
        human = sources["human_blind_surface_annotations"]
        self.assertEqual(human["record_count"], 19)
        self.assertEqual(human["surface_human_accept_count"], 9)
        self.assertEqual(human["strict_plan_accept_count"], 0)

    def test_thresholds_are_explicitly_project_defined(self):
        self.assertEqual(
            self.contract["threshold_status"],
            "project_defined_coverage_gates_not_official_sample_size_rules",
        )
        self.assertEqual(self.contract["readiness_levels"]["pilot_ready"]["minimum_eligible_rows"], 60)
        self.assertEqual(self.contract["readiness_levels"]["training_candidate"]["minimum_eligible_rows"], 600)

    def test_strict_review_requires_hash_binding_and_no_benchmark_origin(self):
        plan = {
            field: ([] if field in {"working_memory_used", "bayes_candidates"} else "value")
            for field in self.contract["required_target_plan_fields"]
        }
        plan["bayes_candidates"] = [{}, {}, {}]
        row = {
            "target_plan": plan,
            "human_review": {
                "decision": "accept",
                "reviewer_id": "reviewer",
                "reviewed_at": "2026-07-18T00:00:00+09:00",
                "target_plan_sha256": "0" * 64,
            },
            "provenance": {
                "source_kind": "project_authored_non_eval",
                "source_id": "fixture",
                "source_sha256": "1" * 64,
                "benchmark_origin": "none",
            },
        }
        self.assertFalse(audit_module._strict_review(row, self.contract))
        row["human_review"]["target_plan_sha256"] = audit_module._canonical_sha256(plan)
        self.assertTrue(audit_module._strict_review(row, self.contract))
        self.assertTrue(audit_module._complete_provenance(row, self.contract))
        row["provenance"]["benchmark_origin"] = "formal_holdout"
        self.assertFalse(audit_module._complete_provenance(row, self.contract))

    def test_runtime_does_not_contain_v75_experiment_code(self):
        runtime = (ROOT / "uruha_brain_mac.py").read_text(encoding="utf-8")
        self.assertNotIn("planner_supervision_v75", runtime)


if __name__ == "__main__":
    unittest.main()
