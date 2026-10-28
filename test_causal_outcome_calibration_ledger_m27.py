import json
import tempfile
import unittest
from pathlib import Path

import uruha_adaptive_person_model as uapm
import uruha_web_ui as web
from test_adaptive_person_model_m16 import AMBIGUOUS_INPUT, decision_for
from test_outcome_calibrated_implicit_response_m26 import (
    PRACTICAL_CORRECTION,
    REPEATED_AMBIGUOUS,
    gated_decision,
)
from test_personhood_loop_v2_13 import _IsolatedContractBrain
from uruha_memory_observatory import collect_cognitive_graph, render_memory_observatory


def decision_with_m26_action(text, action, turn_index=1, probability=0.70):
    state, decision = decision_for(text, uapm.empty_model(), turn_index)
    selected = decision.get("selected") or {}
    decision["implicit_desired_response_m26"] = {
        "schema": uapm.IMPLICIT_RESPONSE_DISTRIBUTION_SCHEMA_M26,
        "status": action,
        "implicit_top_policy": selected.get("policy_id"),
        "implicit_top_mode": uapm.POLICY_TO_RESPONSE_MODE_M23.get(
            selected.get("policy_id")
        ),
        "top_probability": probability,
        "probability_margin": 0.35,
        "evidence_quality": 0.82,
        "raw_dialogue_persisted": False,
    }
    return state, decision


class CausalOutcomeCalibrationLedgerM27Tests(unittest.TestCase):
    def test_causally_linked_support_counts_but_gate_stays_blocked_at_n1(self):
        model = uapm.empty_model()
        _state, decision = decision_with_m26_action(
            "我需要一個現在能做的方法。",
            "execute_implicit",
            probability=0.72,
        )
        model = uapm.set_pending_prediction(model, decision, 1)
        model, feedback = uapm.observe_next_turn(model, "對就是這樣。", 2)
        summary = model["outcome_calibration_summary_m27"]
        update = feedback["causal_outcome_calibration_m27"]

        self.assertEqual(update["status"], "resolved_decisive")
        self.assertEqual(summary["effective_decisive_executed_samples"], 1)
        self.assertEqual(summary["supported_executed_count"], 1)
        self.assertEqual(summary["selective_accuracy"], 1.0)
        self.assertEqual(summary["status"], "insufficient_evidence")
        self.assertFalse(summary["minimum_evidence_gate_met"])
        self.assertFalse(summary["automatic_threshold_tuning_allowed"])

    def test_unknown_or_unrelated_next_turn_is_excluded_from_success(self):
        model = uapm.empty_model()
        _state, decision = decision_with_m26_action(
            "我需要一個現在能做的方法。",
            "execute_implicit",
        )
        model = uapm.set_pending_prediction(model, decision, 1)
        model, feedback = uapm.observe_next_turn(model, "今天外面下雨。", 2)
        summary = model["outcome_calibration_summary_m27"]
        row = model["outcome_calibration_ledger_m27"][-1]

        self.assertEqual(
            feedback["causal_outcome_calibration_m27"]["status"],
            "resolved_unknown_excluded",
        )
        self.assertEqual(row["result_status"], "uncertain")
        self.assertFalse(row["feedback_linked_to_prediction"])
        self.assertEqual(summary["effective_decisive_executed_samples"], 0)
        self.assertEqual(summary["supported_executed_count"], 0)
        self.assertEqual(summary["unknown_or_unlinked_count"], 1)
        self.assertFalse(summary["unknown_outcomes_counted_as_success"])

    def test_explicit_authority_bypass_is_recorded_but_not_used_as_implicit_calibration(self):
        model = uapm.empty_model()
        _state, decision = decision_with_m26_action(
            "Just stay with me for a minute, okay?",
            "explicit_authority_bypass",
        )
        model = uapm.set_pending_prediction(model, decision, 1)
        model, _feedback = uapm.observe_next_turn(model, "Exactly, that's right.", 2)
        summary = model["outcome_calibration_summary_m27"]
        row = model["outcome_calibration_ledger_m27"][-1]

        self.assertEqual(row["action"], "explicit_authority_bypass")
        self.assertFalse(row["eligible_for_implicit_calibration"])
        self.assertEqual(summary["ledger_entry_count"], 1)
        self.assertEqual(summary["eligible_implicit_decision_count"], 0)
        self.assertEqual(summary["effective_decisive_executed_samples"], 0)

    def test_minimum_sample_guard_enables_only_offline_descriptive_review(self):
        model = uapm.empty_model()
        model["outcome_calibration_ledger_m27"] = []
        for index in range(8):
            model["outcome_calibration_ledger_m27"].append(
                {
                    "prediction_id": f"holdout-{index}",
                    "turn_index": index + 1,
                    "input_digest": f"digest-{index}",
                    "context_scope_id": "test:implicit:familiar",
                    "implicit_top_policy": "solve_regulation",
                    "implicit_top_mode": "practical_help",
                    "performed_policy": "solve_regulation",
                    "action": "execute_implicit",
                    "top_probability": 0.75 if index < 6 else 0.60,
                    "probability_margin": 0.30,
                    "evidence_quality": 0.80,
                    "result_status": "supported" if index < 6 else "contradicted",
                    "feedback_linked_to_prediction": True,
                    "feedback_linkage_reason": "isolated_contract_fixture",
                    "resolved_turn": index + 2,
                    "raw_dialogue_persisted": False,
                }
            )
        summary = uapm.build_causal_outcome_calibration_summary_m27(model)

        self.assertTrue(summary["minimum_evidence_gate_met"])
        self.assertEqual(summary["effective_decisive_executed_samples"], 8)
        self.assertEqual(summary["selective_accuracy"], 0.75)
        self.assertEqual(summary["selective_risk"], 0.25)
        self.assertEqual(summary["status"], "descriptive_online_evidence_only")
        self.assertEqual(
            summary["threshold_tuning_status"],
            "eligible_for_offline_review_not_auto_tuning",
        )
        self.assertFalse(summary["automatic_threshold_tuning_allowed"])
        self.assertEqual(
            summary["external_calibration_status"],
            "not_established_without_fresh_holdout",
        )

    def test_persistence_is_bounded_and_contains_no_raw_dialogue(self):
        phrase = "這一句原文絕對不能寫進 M27 帳本"
        model = uapm.empty_model()
        for index in range(130):
            _state, decision = decision_with_m26_action(
                phrase,
                "execute_implicit",
                turn_index=index + 1,
                probability=0.70,
            )
            decision["prediction_id"] = f"m27-{index:03d}"
            model = uapm.set_pending_prediction(model, decision, index + 1)
            model["pending_prediction"] = None
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "adaptive.json"
            uapm.save_model(path, model)
            persisted_text = path.read_text(encoding="utf-8")
            loaded, trace = uapm.load_model(path)

        self.assertEqual(trace["status"], "loaded")
        self.assertNotIn(phrase, persisted_text)
        self.assertLessEqual(
            len(loaded["outcome_calibration_ledger_m27"]),
            uapm.M27_MAX_LEDGER_ENTRIES,
        )
        self.assertFalse(loaded["raw_dialogue_persisted"])
        self.assertTrue(
            all(
                not row["raw_dialogue_persisted"]
                for row in loaded["outcome_calibration_ledger_m27"]
            )
        )

    def test_real_runtime_graph_and_compact_payload_show_m27_without_claiming_calibration(self):
        brain = _IsolatedContractBrain()
        brain.run_turn_debug(AMBIGUOUS_INPUT)
        brain.run_turn_debug(PRACTICAL_CORRECTION)
        repeated = brain.run_turn_debug(REPEATED_AMBIGUOUS)
        supported = brain.run_turn_debug("對，就是這樣。")
        summary = supported["runtime_trace"]["causal_outcome_calibration_m27"]

        self.assertEqual(summary["status"], "insufficient_evidence")
        self.assertEqual(summary["effective_decisive_executed_samples"], 1)
        self.assertFalse(summary["automatic_threshold_tuning_allowed"])
        self.assertRegex(supported["reply"], r"[ぁ-んァ-ン一-龯]")
        self.assertNotRegex(supported["reply"], r"[A-Za-z]{3,}")

        result = {
            "user_text": "isolated",
            "reply": supported["reply"],
            "memory_data": supported["memory_data"],
            "runtime_trace": supported["runtime_trace"],
            "runtime_state": supported["runtime_state"],
        }
        graph = collect_cognitive_graph(result)
        html = render_memory_observatory(result)
        labels = {node["label"] for node in graph["nodes"]}
        self.assertIn("causal_outcome_resolution_m27", labels)
        self.assertIn("causal_outcome_calibration_ledger_m27", labels)
        self.assertIn("CAUSAL OUTCOME CALIBRATION LEDGER · M27", html)
        self.assertIn("effective n 1/8", html)
        self.assertIn("automatic tuning false", html)
        self.assertIn("OUTCOME-CALIBRATED IMPLICIT DESIRED RESPONSE · M26", html)
        self.assertTrue(graph["payload_budget_m24"]["budget_met"])

        cognition = {"runtime_trace": supported["runtime_trace"]}
        compact = web._client_cognition_payload_m24(cognition)
        self.assertIn("causal_outcome_calibration_m27", compact["runtime_trace"])
        self.assertTrue(compact["payload_budget_m24"]["budget_met"])
        self.assertNotIn(
            PRACTICAL_CORRECTION,
            json.dumps(summary, ensure_ascii=False),
        )


if __name__ == "__main__":
    unittest.main()
