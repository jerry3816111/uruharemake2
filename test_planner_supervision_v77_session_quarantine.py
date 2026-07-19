import json
import tempfile
import unittest
from pathlib import Path

import audit_planner_supervision_v75 as v75
import planner_supervision_v76 as v76
from test_planner_supervision_v76_collection import log_record


ROOT = Path(__file__).resolve().parent
CONTRACT_PATH = ROOT / "configs/planner_supervision_v77_session_quarantine_contract.json"
REPORT_PATH = ROOT / "reports/planner_supervision_v77_session_quarantine.json"


class PlannerSupervisionV77SessionQuarantineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = v76.load_json(v76.CONTRACT_PATH)
        cls.v75_contract = v76.load_json(v76.V75_CONTRACT_PATH)

    def test_mixed_session_quarantine_preserves_clean_session(self):
        protected_text = "正式評価と同じ入力"
        protected = {v75._normalize(protected_text)}
        records = [
            log_record("mixed-session", 1, user_text="今日は普通に雑談したい。"),
            log_record("mixed-session", 2, user_text=protected_text),
            log_record("clean-session", 1, user_text="今日は何を食べようか。"),
        ]
        control = v76.build_candidates(
            records,
            protected_inputs=protected,
            contract=self.contract,
            v75_contract=self.v75_contract,
            quarantine_contaminated_sessions=False,
        )
        treatment = v76.build_candidates(
            records,
            protected_inputs=protected,
            contract=self.contract,
            v75_contract=self.v75_contract,
            quarantine_contaminated_sessions=True,
        )

        self.assertEqual(control["summary"]["candidate_count"], 2)
        self.assertEqual(treatment["summary"]["candidate_count"], 1)
        self.assertEqual(treatment["summary"]["evaluation_contaminated_session_count"], 1)
        self.assertEqual(treatment["summary"]["otherwise_valid_records_quarantined"], 1)
        self.assertEqual(treatment["exclusion_reason_counts"]["evaluation_contaminated_session"], 2)
        self.assertEqual(treatment["candidates"][0]["source_session_id"], "clean-session")
        self.assertTrue(treatment["candidates"][0]["collection_checks"]["session_quarantine_applied"])
        mixed_control = next(row for row in control["candidates"] if row["source_session_id"] == "mixed-session")
        self.assertTrue(mixed_control["collection_checks"]["evaluation_contaminated_session"])

    def test_near_evaluation_overlap_quarantines_entire_session(self):
        protected_text = "これは正式評価用の長い入力文章です。誰が申請書を出しますか？"
        near_text = "これは正式評価用の長い入力文章です。誰が申請書を提出しますか？"
        protected = {v75._normalize(protected_text)}
        reason = v76._overlap_reason(near_text, protected, self.contract["near_evaluation_overlap_threshold"])
        self.assertEqual(reason, "near_evaluation_overlap")

        report = v76.build_candidates(
            [
                log_record("near-mixed", 1, user_text="先に普通の話をしよう。"),
                log_record("near-mixed", 2, user_text=near_text),
            ],
            protected_inputs=protected,
            contract=self.contract,
            v75_contract=self.v75_contract,
        )
        self.assertEqual(report["summary"]["candidate_count"], 0)
        self.assertEqual(report["summary"]["otherwise_valid_records_quarantined"], 1)
        self.assertEqual(report["exclusion_reason_counts"]["near_evaluation_overlap"], 1)

    def test_reviewer_rejects_candidate_from_stale_pre_v77_queue(self):
        candidate = v76.build_candidates(
            [log_record("clean-session", 1, user_text="普通の雑談をしよう。")],
            protected_inputs=set(),
            contract=self.contract,
            v75_contract=self.v75_contract,
        )["candidates"][0]
        candidate["collection_checks"].pop("session_quarantine_applied")
        candidate["collection_checks"].pop("evaluation_contaminated_session")
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            candidate_path = base / "candidates.jsonl"
            v76.write_jsonl(candidate_path, [candidate])
            with self.assertRaisesRegex(ValueError, "not built with session quarantine"):
                v76.review_candidate(
                    candidate["id"],
                    "reject",
                    "human-reviewer",
                    candidate["scenario_family"],
                    candidate_path=candidate_path,
                    review_path=base / "reviews.jsonl",
                    manifest_path=base / "manifest.jsonl",
                    strict_annotation_path=base / "strict.jsonl",
                    contract=self.contract,
                    v75_contract=self.v75_contract,
                    protected_inputs=set(),
                )

    def test_contract_and_report_publish_only_aggregate_private_evidence(self):
        contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
        report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
        self.assertEqual(contract["status"], "frozen_before_implementation")
        self.assertTrue(report["success_gates"]["passed"])
        self.assertFalse(report["private_source"]["raw_content_committed"])
        self.assertFalse(report["private_source"]["raw_session_ids_committed"])
        serialized = json.dumps(report, ensure_ascii=False)
        self.assertNotIn("202605", serialized)
        self.assertNotIn("user_utterance", serialized)

    def test_runtime_does_not_contain_v77_experiment_code(self):
        for path in (ROOT / "uruha_brain_mac.py", ROOT / "uruha_web_ui.py"):
            self.assertNotIn("session_quarantine_v77", path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
