import tempfile
import unittest
from pathlib import Path

import audit_planner_supervision_v75 as v75
import planner_supervision_v76 as v76


ROOT = Path(__file__).resolve().parent


def complete_plan():
    return {
        "intent": "chat",
        "scene": "casual",
        "listener_state": "少し疲れている",
        "reply_goal": "状態を受けて短く返す",
        "jp_summary": "ユーザーが少し疲れたと言っている。",
        "core_message_jp": "今日は少し休め",
        "cognitive_mode": "direct",
        "response_mode": "direct_answer",
        "premise_check": "accept",
        "uncertainty": 0.1,
        "hidden_intent": "plain_statement",
        "surface_act": "light_support",
        "user_belief": "普通に受け止めてもらえると思っている。",
        "my_hidden_knowledge": "深刻な危機だとは判断していない。",
        "user_expectation": "短い気遣い。",
        "working_memory_used": [],
        "routing_path": "high_road",
        "bayes_candidates": [
            {"candidate_label": "soft", "bayes_probability": 0.4},
            {"candidate_label": "default", "bayes_probability": 0.35},
            {"candidate_label": "sharp", "bayes_probability": 0.25},
        ],
    }


def log_record(session_id, turn_index, user_text="今日は少し疲れた。", plan=None):
    return {
        "timestamp": "2026-07-18T12:00:00+09:00",
        "session_id": session_id,
        "turn_index": turn_index,
        "input_mode": "text",
        "user_text": user_text,
        "assistant_reply": "今日はちょっと休め。",
        "logic": complete_plan() if plan is None else plan,
        "cognition_trace": {
            "psyche_before": {"mood": -0.1, "trust": 55, "trust_lock_turns": 0}
        },
        "memory_snapshot": {
            "recent_turns": [],
            "working_memory_items": [],
        },
    }


class PlannerSupervisionV76CollectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = v76.load_json(v76.CONTRACT_PATH)
        cls.v75_contract = v76.load_json(v76.V75_CONTRACT_PATH)

    def _fixture_report(self):
        incomplete = complete_plan()
        incomplete.pop("bayes_candidates")
        records = [
            log_record("session-valid", 1),
            log_record("session-duplicate", 2),
            log_record("session-incomplete", 3, user_text="今日は頭が重い。", plan=incomplete),
            log_record("session-protected", 4, user_text="正式評価と同じ入力"),
        ]
        protected = {v75._normalize("正式評価と同じ入力")}
        return v76.build_candidates(
            records,
            protected_inputs=protected,
            contract=self.contract,
            v75_contract=self.v75_contract,
        )

    def test_builder_keeps_only_complete_unique_non_evaluation_candidate(self):
        report = self._fixture_report()
        self.assertEqual(report["summary"]["source_record_count"], 4)
        self.assertEqual(report["summary"]["candidate_count"], 1)
        self.assertEqual(report["summary"]["training_rows_created"], 0)
        self.assertEqual(report["summary"]["additional_model_calls"], 0)
        self.assertEqual(report["exclusion_reason_counts"]["duplicate_input_context"], 1)
        self.assertEqual(report["exclusion_reason_counts"]["incomplete_target_plan"], 1)
        self.assertEqual(report["exclusion_reason_counts"]["exact_evaluation_overlap"], 1)

    def test_pending_candidate_fails_v75_training_gates(self):
        candidate = self._fixture_report()["candidates"][0]
        unit = v75._strict_units([candidate], self.v75_contract)[0]
        failures = v75._unit_rejection_reasons(unit, self.v75_contract, False, set())
        self.assertIn("no_strict_human_plan_acceptance", failures)
        self.assertIn("incomplete_provenance", failures)
        self.assertIn("not_train_split", failures)

    def test_rejection_writes_no_strict_training_row(self):
        candidate = self._fixture_report()["candidates"][0]
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            candidate_path = base / "candidates.jsonl"
            review_path = base / "reviews.jsonl"
            manifest_path = base / "manifest.jsonl"
            strict_path = base / "strict.jsonl"
            v76.write_jsonl(candidate_path, [candidate])
            result = v76.review_candidate(
                candidate["id"],
                "reject",
                "human-reviewer",
                candidate["scenario_family"],
                candidate_path=candidate_path,
                review_path=review_path,
                manifest_path=manifest_path,
                strict_annotation_path=strict_path,
                reviewed_at="2026-07-18T12:10:00+09:00",
                contract=self.contract,
                v75_contract=self.v75_contract,
                protected_inputs=set(),
            )
            self.assertIsNone(result["accepted_row"])
            self.assertFalse(strict_path.exists())
            self.assertEqual(len(v76.load_jsonl(review_path)), 1)

    def test_acceptance_requires_certification_then_becomes_v75_eligible(self):
        candidate = self._fixture_report()["candidates"][0]
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            candidate_path = base / "candidates.jsonl"
            review_path = base / "reviews.jsonl"
            manifest_path = base / "manifest.jsonl"
            strict_path = base / "strict.jsonl"
            v76.write_jsonl(candidate_path, [candidate])
            with self.assertRaisesRegex(ValueError, "certified non-benchmark"):
                v76.review_candidate(
                    candidate["id"],
                    "accept",
                    "human-reviewer",
                    candidate["scenario_family"],
                    candidate_path=candidate_path,
                    review_path=review_path,
                    manifest_path=manifest_path,
                    strict_annotation_path=strict_path,
                    contract=self.contract,
                    v75_contract=self.v75_contract,
                    protected_inputs=set(),
                )

            result = v76.review_candidate(
                candidate["id"],
                "accept",
                "human-reviewer",
                candidate["scenario_family"],
                certify_non_benchmark=True,
                consent_to_training=True,
                candidate_path=candidate_path,
                review_path=review_path,
                manifest_path=manifest_path,
                strict_annotation_path=strict_path,
                reviewed_at="2026-07-18T12:10:00+09:00",
                contract=self.contract,
                v75_contract=self.v75_contract,
                protected_inputs=set(),
            )
            accepted = result["accepted_row"]
            self.assertEqual(accepted["split"], "train")
            self.assertEqual(accepted["provenance"]["benchmark_origin"], "none")
            self.assertEqual(len(v76.load_jsonl(strict_path)), 1)
            unit = v75._strict_units([accepted], self.v75_contract)[0]
            self.assertEqual(v75._unit_rejection_reasons(unit, self.v75_contract, False, set()), [])
            with self.assertRaisesRegex(ValueError, "already reviewed"):
                v76.review_candidate(
                    candidate["id"],
                    "accept",
                    "human-reviewer",
                    candidate["scenario_family"],
                    candidate_path=candidate_path,
                    review_path=review_path,
                    manifest_path=manifest_path,
                    strict_annotation_path=strict_path,
                    contract=self.contract,
                    v75_contract=self.v75_contract,
                    protected_inputs=set(),
                )

    def test_review_rejects_tampered_source_binding(self):
        candidate = self._fixture_report()["candidates"][0]
        candidate["source_record"]["user_text"] = "改ざんされた入力"
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            candidate_path = base / "candidates.jsonl"
            v76.write_jsonl(candidate_path, [candidate])
            with self.assertRaisesRegex(ValueError, "source hash mismatch"):
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

    def test_private_collection_artifacts_are_gitignored(self):
        ignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
        self.assertIn("analysis/local_planner_supervision_v76/", ignore)
        self.assertIn("analysis/planner_supervision_annotations_v75.jsonl", ignore)

    def test_original_formal_holdout_inputs_are_protected_before_model_output_exists(self):
        protected = v76.protected_inputs_from_v75(self.v75_contract)
        holdout = v76.load_json(ROOT / "datasets/cognitive_plan_model_screen_v65.json")
        sample = holdout["cases"][0]["planning_packet"]["user_input"]
        self.assertIn(v75._normalize(sample), protected)

    def test_runtime_is_not_modified_for_collection(self):
        runtime = (ROOT / "uruha_brain_mac.py").read_text(encoding="utf-8")
        web_ui = (ROOT / "uruha_web_ui.py").read_text(encoding="utf-8")
        self.assertNotIn("planner_supervision_v76", runtime)
        self.assertNotIn("planner_supervision_v76", web_ui)


if __name__ == "__main__":
    unittest.main()
