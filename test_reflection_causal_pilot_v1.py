import json
import hashlib
import unittest
from pathlib import Path

from reflection_causal_pilot_v1_core import behavior_success, score_rows, summarize


ROOT = Path(__file__).resolve().parent
CONFIG = ROOT / "configs" / "reflection_causal_pilot_v1_preregistration.json"
DATASET = ROOT / "datasets" / "reflection_causal_pilot_v1.json"
LOCK = ROOT / "configs" / "reflection_causal_pilot_v1_harness_lock.json"


class ReflectionCausalPilotV1Test(unittest.TestCase):
    def test_frozen_dataset_is_balanced_and_unique(self):
        payload = json.loads(DATASET.read_text(encoding="utf-8"))
        cases = payload["cases"]
        self.assertEqual(payload["case_count"], 12)
        self.assertEqual(len(cases), 12)
        self.assertEqual(len({case["id"] for case in cases}), 12)
        counts = {}
        for case in cases:
            counts[case["category"]] = counts.get(case["category"], 0) + 1
        self.assertEqual(
            counts,
            {
                "stable_user_fact": 3,
                "interaction_strategy": 3,
                "interaction_interpretation": 3,
                "no_rule_control": 3,
            },
        )

    def test_preregistration_forbids_post_run_tuning(self):
        payload = json.loads(CONFIG.read_text(encoding="utf-8"))
        self.assertFalse(payload["post_run_case_editing_authorized"])
        self.assertFalse(payload["post_run_threshold_change_authorized"])
        self.assertFalse(payload["runtime_reflection_change_authorized_before_result"])
        self.assertFalse(payload["paid_api_authorized"])
        self.assertEqual(payload["single_manipulated_variable"], "presence_of_the_current_reflection_rule")

    def test_harness_lock_matches_every_frozen_artifact(self):
        payload = json.loads(LOCK.read_text(encoding="utf-8"))
        self.assertEqual(payload["required_run_branch"], "main")
        for relative, expected in payload["frozen_artifacts"].items():
            actual = hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
            self.assertEqual(actual, expected, relative)

    def test_behavior_contract_checks_content_intrusion_and_shape(self):
        case = {
            "behavior_required_any": ["ご飯"],
            "behavior_forbidden_any": ["コーラ"],
            "behavior_max_question_marks": 1,
            "behavior_max_chars": 20,
        }
        self.assertTrue(
            behavior_success(case, {"future_reply": "ご飯でいい。", "future_logic_text": ""})
        )
        self.assertFalse(
            behavior_success(case, {"future_reply": "コーラとご飯？", "future_logic_text": ""})
        )

    def test_summary_detects_a_clean_paired_gain(self):
        case = {
            "id": "x",
            "language": "ja",
            "category": "interaction_strategy",
            "expected_rule_kind": "procedural_interaction_rule",
            "rule_required_any": ["一つ"],
            "rule_forbidden_any": [],
            "behavior_required_any": ["一つ"],
            "behavior_forbidden_any": [],
            "behavior_max_question_marks": 1,
            "behavior_max_chars": 30,
        }
        raw_rows = [
            {
                "case": case,
                "conditions": {
                    "episodic_memory_only_control": {
                        "future_reply": "三つ聞く？",
                        "future_logic_text": "",
                        "reflection_documents": [],
                    },
                    "same_episodic_memory_plus_current_reflection_treatment": {
                        "future_reply": "まず一つだけ聞く。",
                        "future_logic_text": "",
                        "reflection_documents": ["Rule: 一つだけ聞く"],
                        "retrieved_reflection": True,
                    },
                },
            }
        ]
        scored = score_rows(raw_rows)
        summary = summarize(
            scored,
            {
                "expected_rule_write_recall_min": 1.0,
                "valid_rule_precision_min": 1.0,
                "no_rule_specificity_min": 0.0,
                "valid_rule_retrieval_rate_min": 1.0,
                "treatment_behavior_delta_min": 1.0,
                "paired_behavior_net_gain_min": 1,
                "interaction_category_paired_gains_min": 1,
                "paired_behavior_regressions_max": 0,
            },
        )
        self.assertTrue(scored[0]["paired_gain"])
        self.assertEqual(summary["paired_behavior_net_gain"], 1)
        self.assertTrue(summary["all_gates_pass"])


if __name__ == "__main__":
    unittest.main()
