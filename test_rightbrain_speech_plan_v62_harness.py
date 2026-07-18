import hashlib
import json
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

import analyze_rightbrain_speech_plan_payload_v62 as analyzer
from run_rightbrain_speech_plan_payload_v62 import (
    C0,
    T1,
    _assert_no_gold_fields,
    build_condition_payloads,
)
from uruha_brain_mac import RightBrain


class RightBrainSpeechPlanV62HarnessTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.right_brain = RightBrain(load_model=False)
        cls.base_logic = {
            "scene": "casual",
            "intent": "chat",
            "surface_act": "direct_answer",
            "jp_summary": "ユーザーが今夜の気分を聞いている。",
            "core_message_jp": "今夜は音楽を流したい。",
            "grounding": {},
            "constraints": {},
            "must_avoid": [],
        }
        cls.payloads = build_condition_payloads(
            cls.right_brain,
            cls.base_logic,
            "今夜は何したい？",
            {"working_memory_items": []},
            {"mood": 0.0, "trust": 50},
            70,
        )

    def test_matched_payload_pair_changes_only_by_attaching_runtime_plan(self):
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
        self.assertEqual(control["reply_requirements"], treatment["reply_requirements"])

    def test_payloads_never_contain_scoring_field_names(self):
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
                "今夜は何したい？",
                {"working_memory_items": []},
                {"mood": 0.0, "trust": 50},
                70,
            )

    def test_harness_lock_binds_every_dependency_and_forbids_runtime_change(self):
        root = Path(__file__).resolve().parent
        lock = json.loads(
            (
                root
                / "configs/rightbrain_speech_plan_payload_v62_harness_lock.json"
            ).read_text(encoding="utf-8")
        )
        for name, artifact in lock["frozen_artifacts"].items():
            if name == "harness_test":
                continue
            path = root / artifact["path"]
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            self.assertEqual(digest, artifact["sha256"], name)
        self.assertTrue(lock["formal_run"]["candidate_inference_authorized"])
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
        captures = [
            {
                "case_id": case_id,
                "runtime_speech_plan": {
                    "content_units": ["meaning"],
                    "dialogue_act": "direct_chat_answer",
                },
            }
            for case_id in case_ids
        ]
        rows = []
        for index, case_id in enumerate(case_ids):
            rows.append(
                {
                    "case_id": case_id,
                    "condition": C0,
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
            "leftbrain_call_count": 14,
            "logical_model_call_count": 28,
            "transport_error_count": 0,
            "production_memory_write_count": 0,
            "physical_vrm_action_count": 0,
        }

    def test_synthetic_passing_result_authorizes_only_next_development(self):
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
            "authorize_new_data_semantic_contract_projector_development",
        )
        self.assertFalse(report["runtime_change_authorized"])
        self.assertFalse(report["production_rightbrain_replacement_authorized"])

    def test_synthetic_low_recall_result_stops_hypothesis(self):
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
            "t1_raw_required_meaning_recall_at_least",
            report["automatic_gates"]["failed_checks"],
        )
        self.assertEqual(
            report["decision"],
            "freeze_negative_result_and_stop_full_speech_plan_hypothesis",
        )


if __name__ == "__main__":
    unittest.main()
