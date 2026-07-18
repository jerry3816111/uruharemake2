import inspect
import json
import unittest
from pathlib import Path

import analyze_profile_grounded_speech_plan_v72 as analyzer
import run_profile_grounded_speech_plan_v72 as runner
import uruha_profile_grounding as grounding
from uruha_brain_mac import RightBrain


ROOT = Path(__file__).resolve().parent
PREREG = json.loads(
    (ROOT / "configs/profile_grounded_speech_plan_v72_preregistration.json").read_text(encoding="utf-8")
)


class ProfileGroundedSpeechPlanV72HarnessTests(unittest.TestCase):
    def setUp(self):
        self.candidate = {
            "memory_id": "development_memory",
            "metadata": {
                "fact_type": "dislike",
                "value": "炭酸水",
                "source_utterance": "今は炭酸水が苦手。",
            },
        }
        self.evidence = {
            "answerability": "supported",
            "fact_type": "dislike",
            "value": "炭酸水",
            "relation": "dislikes",
        }

    def test_evidence_contract_preserves_value_relation_and_answerability(self):
        self.assertEqual(
            grounding.build_evidence_contract([self.candidate], "selected"),
            self.evidence,
        )
        self.assertEqual(
            grounding.build_evidence_contract([], "requested_but_unavailable")["answerability"],
            "unsupported",
        )
        self.assertEqual(
            grounding.build_evidence_contract([], "not_requested")["answerability"],
            "not_requested",
        )

    def test_relation_slot_is_the_primary_plan_difference(self):
        value_only = grounding.build_grounded_profile_logic(
            {"schema": grounding.SCHEMA, "mode": "value_only", "evidence": {**self.evidence, "relation": None}}
        )
        treatment = grounding.build_grounded_profile_logic(
            {"schema": grounding.SCHEMA, "mode": "value_relation", "evidence": self.evidence}
        )
        self.assertEqual(value_only["profile_evidence_contract"]["value"], treatment["profile_evidence_contract"]["value"])
        self.assertEqual(value_only["profile_evidence_contract"]["answerability"], "supported")
        self.assertIsNone(value_only["profile_evidence_contract"]["relation"])
        self.assertEqual(treatment["profile_evidence_contract"]["relation"], "dislikes")
        self.assertEqual(value_only["required_marker_groups"], [["炭酸水"]])
        self.assertEqual(treatment["required_marker_groups"][0], ["炭酸水"])
        self.assertIn("苦手", treatment["required_marker_groups"][1])

    def test_bridge_is_inert_without_an_explicit_valid_request(self):
        self.assertIsNone(grounding.build_grounded_profile_logic(None))
        self.assertIsNone(grounding.build_grounded_profile_logic({"evidence": self.evidence}))
        self.assertIsNone(
            grounding.build_grounded_profile_logic(
                {"schema": grounding.SCHEMA, "mode": "value_relation", "evidence": {**self.evidence, "relation": "likes"}}
            )
        )

    def test_rightbrain_realizes_generic_relation_without_structural_labels(self):
        logic = grounding.build_grounded_profile_logic(
            {"schema": grounding.SCHEMA, "mode": "value_relation", "evidence": self.evidence}
        )
        right = RightBrain(load_model=False)
        reply = right._memory_grounded_reply(logic, "前の好みを覚えてる？")
        self.assertIn("炭酸水", reply)
        self.assertTrue(any(marker in reply for marker in ("苦手", "嫌い", "好きじゃない", "無理")))
        self.assertFalse(any(marker in reply for marker in grounding.STRUCTURAL_SURFACES))
        groups, hits = right._surface_semantic_group_hits(reply, logic)
        self.assertEqual(len(groups), 2)
        self.assertTrue(all(hits))

    def test_runner_does_not_read_gold_fields(self):
        self.assertNotIn("expected", inspect.getsource(runner.prepare_case))
        self.assertNotIn("expected", inspect.getsource(runner.run_case))
        main_source = inspect.getsource(runner.main)
        self.assertIn('for key in ("id", "scenario_family", "user_input", "profile_history")', main_source)

    def test_runtime_and_bridge_contain_no_holdout_ids_or_values(self):
        bridge_source = (ROOT / "uruha_profile_grounding.py").read_text(encoding="utf-8")
        runtime_source = (ROOT / "uruha_brain_mac.py").read_text(encoding="utf-8")
        dataset = json.loads((ROOT / "datasets/profile_grounded_speech_plan_v72.json").read_text(encoding="utf-8"))
        for case in dataset["cases"]:
            self.assertNotIn(case["id"], bridge_source)
            self.assertNotIn(case["id"], runtime_source)
            for row in case["profile_history"]:
                self.assertNotIn(row["value"], bridge_source)
                self.assertNotIn(row["value"], runtime_source)

    def test_synthetic_analyzer_attributes_relation_gain(self):
        cases = []
        rows = []
        for index in range(24):
            relevant = index < 16
            relation_case = index < 12
            abstention = 16 <= index < 20
            value = f"項目{index}" if relevant else None
            relation = "likes" if relation_case else "preferred_name" if relevant else None
            expected_contract = {
                "answerability": "supported" if relevant else "unsupported" if abstention else "not_requested",
                "fact_type": "like" if relation_case else "name" if relevant else None,
                "value": value,
                "relation": relation,
            }
            cases.append(
                {
                    "id": f"synthetic_{index}",
                    "scenario_family": "synthetic",
                    "expected": {
                        "evidence_contract": expected_contract,
                        "required_value_markers": [value] if relevant else [],
                        "required_relation_markers": ["好き"] if relation_case else [],
                        "forbidden_terms": [f"侵入{index}"] if not relevant else [],
                        "memory_relevant": relevant,
                        "abstention_required": abstention,
                    },
                }
            )
            for condition in runner.CONDITIONS:
                if relevant:
                    if condition == runner.CONDITIONS[2]:
                        reply = f"{value}が好き"
                    elif condition == runner.CONDITIONS[1]:
                        reply = value
                    else:
                        reply = "思い出せない"
                else:
                    reply = "覚えてない" if abstention else "普通の返事"
                rows.append(
                    {
                        "case_id": f"synthetic_{index}",
                        "condition": condition,
                        "reply": reply,
                        "evidence_contract": expected_contract,
                        "surface_gate_pass": True,
                        "selection_contract": {"selector_seconds": 0.01, "status": "selected" if relevant else "not_requested"},
                        "leftbrain_model_calls": 1 if condition == runner.CONDITIONS[0] and relevant else 0,
                        "turn_seconds": 0.2,
                        "temporary_database": True,
                    }
                )
        raw = {
            "row_count": 72,
            "conditions": list(runner.CONDITIONS),
            "gold_in_raw": False,
            "locked_preflight": {"passed": True, "observed_test_count": 1, "expected_test_count": 1},
            "rightbrain_model_loading": False,
            "selector_call_count": 24,
            "transport_error_count": 0,
            "production_database_access_count": 0,
            "physical_action_count": 0,
            "rows": rows,
        }
        report = analyzer.analyze(raw, {"cases": cases}, PREREG)
        self.assertEqual(report["decision"], "authorize_grounded_plan_answer_shadow_only")
        self.assertEqual(report["pairwise"]["newly_passed_vs_value_only"], 12)
        self.assertEqual(report["pairwise"]["regressions_vs_value_only"], 0)
        self.assertEqual(report["cost"]["leftbrain_model_calls_reduction_vs_current"], 16)


if __name__ == "__main__":
    unittest.main()
