import hashlib
import json
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

import analyze_rightbrain_shared_final_plan_v63 as analyzer
from run_rightbrain_shared_final_plan_v63 import (
    C0,
    T1,
    _assert_no_gold_fields,
    _plan_source,
    _validate_capture_accounting,
    build_condition_payloads,
)
from uruha_brain_mac import RightBrain


class RightBrainSharedFinalPlanV63HarnessTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.right_brain = RightBrain(load_model=False)
        cls.base_logic = {
            "scene": "casual",
            "intent": "chat",
            "surface_act": "direct_answer",
            "jp_summary": "明日の朝が早いので休息を選ぶ必要がある。",
            "core_message_jp": "今日は寝る方を勧める。",
            "grounding": {},
            "constraints": {},
            "must_avoid": [],
        }
        cls.payloads = build_condition_payloads(
            cls.right_brain,
            cls.base_logic,
            "映画を見るか寝るか、どっちがいい？",
            {"working_memory_items": []},
            {"mood": 0.0, "trust": 50},
            72,
        )

    def test_matched_pair_changes_only_by_attaching_speech_plan(self):
        control = json.loads(self.payloads[C0]["payload"])
        treatment = json.loads(self.payloads[T1]["payload"])
        plan = self.payloads["runtime_speech_plan"]

        self.assertTrue(plan["content_units"])
        self.assertTrue(plan["dialogue_act"])
        self.assertFalse(self.payloads[C0]["payload_plan_present"])
        self.assertTrue(self.payloads[T1]["payload_plan_present"])
        self.assertFalse(control["leftbrain_plan"]["content_units"])
        self.assertTrue(treatment["leftbrain_plan"]["content_units"])
        self.assertEqual(control["task"], treatment["task"])
        self.assertEqual(control["user_input"], treatment["user_input"])
        self.assertEqual(control["context"], treatment["context"])
        self.assertEqual(
            control["reply_requirements"], treatment["reply_requirements"]
        )

    def test_payloads_reject_scoring_gold(self):
        _assert_no_gold_fields(self.payloads[C0]["payload"])
        _assert_no_gold_fields(self.payloads[T1]["payload"])
        leaked = json.loads(self.payloads[T1]["payload"])
        leaked["required_meaning_propositions"] = []
        with self.assertRaisesRegex(ValueError, "scoring gold leaked"):
            _assert_no_gold_fields(json.dumps(leaked, ensure_ascii=False))

    def test_existing_plan_in_base_logic_fails_closed(self):
        contaminated = deepcopy(self.base_logic)
        contaminated["human_speech_plan"] = {"content_units": ["stale"]}
        with self.assertRaisesRegex(ValueError, "already contains speech plan"):
            build_condition_payloads(
                self.right_brain,
                contaminated,
                "映画を見るか寝るか、どっちがいい？",
                {"working_memory_items": []},
                {"mood": 0.0, "trust": 50},
                72,
            )

    @staticmethod
    def _capture(source):
        return {
            "base_logic": {"intent": "chat"},
            "runtime_speech_plan": {
                "content_units": ["meaning"],
                "dialogue_act": "direct_chat_answer",
            },
            "plan_source": source,
            "leftbrain_model_call_delta": int(source == "model_high_road"),
            "conditions": {
                C0: {"payload_plan_present": False},
                T1: {"payload_plan_present": True},
            },
        }

    def test_plan_source_accounting_accepts_rule_plans_without_model_calls(self):
        captures = [self._capture("model_high_road") for _ in range(8)]
        captures.extend(self._capture("rule_high_road") for _ in range(4))
        captures.extend(self._capture("rule_low_road") for _ in range(2))
        distribution = _validate_capture_accounting(
            captures,
            leftbrain_calls=[{} for _ in range(8)],
            expected_count=14,
        )
        self.assertEqual(
            distribution,
            {
                "model_high_road": 8,
                "rule_high_road": 4,
                "rule_low_road": 2,
            },
        )

    def test_plan_source_uses_route_and_per_case_model_call_delta(self):
        self.assertEqual(
            _plan_source({"route": "low_road"}, 0),
            "rule_low_road",
        )
        self.assertEqual(
            _plan_source({"route": "high_road"}, 0),
            "rule_high_road",
        )
        self.assertEqual(
            _plan_source({"route": "high_road"}, 1),
            "model_high_road",
        )
        with self.assertRaisesRegex(ValueError, "invalid route/model-call"):
            _plan_source({"route": "low_road"}, 1)

    def test_plan_source_accounting_rejects_mismatched_model_calls(self):
        captures = [self._capture("model_high_road") for _ in range(8)]
        captures.extend(self._capture("rule_high_road") for _ in range(4))
        captures.extend(self._capture("rule_low_road") for _ in range(2))
        with self.assertRaisesRegex(ValueError, "call accounting mismatch"):
            _validate_capture_accounting(
                captures,
                leftbrain_calls=[{} for _ in range(14)],
                expected_count=14,
            )

    def test_harness_lock_binds_dependencies_and_forbids_runtime_change(self):
        root = Path(__file__).resolve().parent
        lock = json.loads(
            (
                root
                / "configs/rightbrain_shared_final_plan_v63_harness_lock.json"
            ).read_text(encoding="utf-8")
        )
        for name, artifact in lock["frozen_artifacts"].items():
            if name == "harness_test":
                continue
            path = root / artifact["path"]
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            self.assertEqual(digest, artifact["sha256"], name)
        self.assertTrue(lock["formal_run"]["candidate_inference_authorized"])
        self.assertNotIn(
            "leftbrain_call_count_exact",
            lock["formal_run"],
        )
        self.assertFalse(lock["human_blind_review_authorized"])
        self.assertFalse(lock["runtime_change_authorized"])
        self.assertFalse(lock["production_rightbrain_replacement_authorized"])

    @staticmethod
    def _score(hit, reply):
        return {
            "required_meaning_hit_count": int(hit),
            "required_meaning_count": 1,
            "required_meaning_pass": bool(hit),
            "forbidden_meaning_hit_count": 0,
            "forbidden_meaning_propositions": [{"hit": False}],
            "private_memory_intrusion": False,
            "current_gate_pass": True,
            "normalized_reply": reply,
            "current_gate_rejection_reasons": [],
        }

    def _synthetic_raw(self, treatment_hits):
        dataset = json.loads(analyzer.DATASET_PATH.read_text(encoding="utf-8"))
        case_ids = [case["id"] for case in dataset["cases"]]
        captures = []
        rows = []
        for index, case_id in enumerate(case_ids):
            if index < 8:
                source = "model_high_road"
            elif index < 12:
                source = "rule_high_road"
            else:
                source = "rule_low_road"
            captures.append(
                {
                    "case_id": case_id,
                    "base_logic": {"intent": "chat"},
                    "plan_source": source,
                    "leftbrain_model_call_delta": int(
                        source == "model_high_road"
                    ),
                    "runtime_speech_plan": {
                        "content_units": ["meaning"],
                        "dialogue_act": "direct_chat_answer",
                    },
                }
            )
            rows.append(
                {
                    "case_id": case_id,
                    "condition": C0,
                    "plan_source": source,
                    "payload_plan_present": False,
                    "raw_score": self._score(index < 7, f"c0-{index}"),
                    "generation_metrics": {"wall_seconds": 2.0},
                    "peak_ollama_rss_bytes": 8_000_000_000,
                    "transport_error": None,
                }
            )
            rows.append(
                {
                    "case_id": case_id,
                    "condition": T1,
                    "plan_source": source,
                    "payload_plan_present": True,
                    "raw_score": self._score(
                        index < treatment_hits,
                        f"t1-{index}",
                    ),
                    "generation_metrics": {"wall_seconds": 2.2},
                    "peak_ollama_rss_bytes": 8_200_000_000,
                    "transport_error": None,
                }
            )
        return {
            "captures": captures,
            "model_rows": rows,
            "plan_source_distribution": {
                "model_high_road": 8,
                "rule_high_road": 4,
                "rule_low_road": 2,
            },
            "leftbrain_call_count": 8,
            "logical_model_call_count": 28,
            "transport_error_count": 0,
            "production_memory_write_count": 0,
            "physical_vrm_action_count": 0,
        }

    def test_synthetic_passing_result_authorizes_only_shadow_test(self):
        prereg = json.loads(analyzer.PREREG_PATH.read_text(encoding="utf-8"))
        dataset = json.loads(analyzer.DATASET_PATH.read_text(encoding="utf-8"))
        lock = {"statistics": {"bootstrap_samples": 100}}
        with patch.object(analyzer, "_artifact_checks", return_value={"ok": True}):
            report = analyzer.analyze(
                self._synthetic_raw(treatment_hits=14),
                prereg,
                dataset,
                lock,
            )
        self.assertTrue(report["automatic_gates"]["passed"])
        self.assertEqual(
            report["decision"],
            "authorize_new_data_runtime_integration_shadow_test",
        )
        self.assertFalse(report["runtime_change_authorized"])
        self.assertFalse(report["production_rightbrain_replacement_authorized"])

    def test_synthetic_no_gain_result_stops_hypothesis(self):
        prereg = json.loads(analyzer.PREREG_PATH.read_text(encoding="utf-8"))
        dataset = json.loads(analyzer.DATASET_PATH.read_text(encoding="utf-8"))
        lock = {"statistics": {"bootstrap_samples": 100}}
        with patch.object(analyzer, "_artifact_checks", return_value={"ok": True}):
            report = analyzer.analyze(
                self._synthetic_raw(treatment_hits=7),
                prereg,
                dataset,
                lock,
            )
        self.assertFalse(report["automatic_gates"]["passed"])
        self.assertIn(
            "t1_raw_required_meaning_recall_delta_vs_c0_at_least",
            report["automatic_gates"]["failed_checks"],
        )
        self.assertEqual(
            report["decision"],
            "freeze_negative_result_and_stop_full_speech_plan_payload_hypothesis",
        )


if __name__ == "__main__":
    unittest.main()
