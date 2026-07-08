import json
import unittest
from pathlib import Path

from eval_rightbrain_contract_projection_v1 import (
    TARGET_CASE_IDS,
    apply_naturalness_audit,
    build_report,
)
from project_paths import (
    RIGHTBRAIN_CONTRACT_PROJECTION_V1_AUDIT_JSON_PATH,
    RIGHTBRAIN_CONTRACT_PROJECTION_V1_REPORT_JSON_PATH,
)


class RightBrainContractProjectionV1Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = build_report("base-only", load_model=False)

    def test_target_contracts_project_only_when_plan_conflicts_with_memory_policy(self):
        self.assertEqual(
            {row["id"] for row in self.report["contract_snapshots"]},
            set(TARGET_CASE_IDS),
        )
        snapshots = {row["id"]: row for row in self.report["contract_snapshots"]}
        self.assertEqual(snapshots["background_family_pressure"]["projection"]["mode"], "semantic_contract_only")
        self.assertEqual(snapshots["no_memory_plain_question"]["projection"]["mode"], "semantic_contract_only")
        self.assertEqual(snapshots["private_do_not_mention"]["projection"]["mode"], "full_plan")

    def test_private_topic_plan_keeps_only_public_topic_proposal(self):
        snapshots = {row["id"]: row for row in self.report["contract_snapshots"]}
        private = snapshots["private_do_not_mention"]
        self.assertEqual(private["projected_leftbrain_plan"]["intent"], "topic_proposal")
        self.assertEqual(private["projected_leftbrain_plan"]["dialogue_act"], "topic_proposal")
        self.assertEqual(private["projected_leftbrain_plan"]["grounding_terms"], ["話題", "最近"])
        self.assertEqual(
            private["projected_leftbrain_plan"]["content_units"],
            ["軽い話題を一個出す", "相手の近況に渡す"],
        )
        self.assertEqual(private["projected_leftbrain_plan"]["meaning"], "軽い話題なら最近どうしてたかでいい")

    def test_static_report_is_json_serializable(self):
        json.dumps(self.report, ensure_ascii=False)

    def test_recorded_model_report_matches_complete_naturalness_audit(self):
        report_path = Path(RIGHTBRAIN_CONTRACT_PROJECTION_V1_REPORT_JSON_PATH)
        if not report_path.exists():
            self.skipTest("actual-model report has not been generated")
        report = json.loads(report_path.read_text(encoding="utf-8"))
        audit = json.loads(
            Path(RIGHTBRAIN_CONTRACT_PROJECTION_V1_AUDIT_JSON_PATH).read_text(encoding="utf-8")
        )
        report.pop("naturalness_audit", None)
        for key in (
            "naturalness_audit_matches_every_accepted_candidate",
            "projected_candidate_audit_pass_count_improves",
            "projected_final_pairwise_has_no_losses",
        ):
            report["gate"].pop(key, None)
        audited = apply_naturalness_audit(report, audit)
        self.assertTrue(audited["gate_passed"])
        self.assertEqual(
            audited["naturalness_audit"]["candidate_metrics"]["projected_contract"]["pass_count"],
            4,
        )
        self.assertEqual(audited["naturalness_audit"]["final_pairwise"]["legacy_wins"], 0)


if __name__ == "__main__":
    unittest.main()
