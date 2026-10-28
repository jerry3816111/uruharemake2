import json
import unittest

import uruha_web_ui as web
from uruha_memory_observatory import (
    M24_GRAPH_DETAIL_BUDGET_BYTES,
    M24_NODE_DETAIL_BUDGET_BYTES,
    collect_cognitive_graph,
    render_memory_observatory,
)


class ProgressiveRuntimeGraphM24Tests(unittest.TestCase):
    def _large_record(self):
        tail = "UNRENDERED_TAIL_" + ("x" * 180_000) + "_TAIL_END_SHOULD_NOT_RENDER"
        mode = {
            "schema": "uruha_desired_response_mode_m23",
            "selected_mode": "practical_help",
            "authority": "verified_reversible_preference",
            "surface_status": "matched",
            "evidence": [{"kind": "scope", "value": "support"}] * 80,
            "large_internal_evidence": tail,
        }
        blackboard = [
            {
                "stage": "select",
                "label": "desired_response_mode_m23",
                "payload": mode,
                "salience": 0.98,
            }
        ]
        runtime_trace = {
            "blackboard": blackboard,
            "desired_response_mode_m23": mode,
            "semantic_route_classifier_m22": {
                "schema": "uruha_semantic_route_taxonomy_m22",
                "selected_type": "emotional_bid",
                "confidence": 0.92,
            },
        }
        runtime_state = {
            "recent_turn_traces": [{"payload": tail}] * 8,
            "recent_autonomous_traces": [{"payload": tail}] * 5,
            "adaptive_person_model": {"revision": 7, "large": tail},
            "last_state_diff": {"large": tail},
        }
        cognition = {
            "response_mode": "chat",
            "runtime_trace": runtime_trace,
            "runtime_state": runtime_state,
        }
        memory = {"recent_turns": [{"summary": tail}] * 20}
        return {
            "timestamp": "2026-08-24T12:00:00",
            "session_id": "m24-isolated",
            "turn_index": 6,
            "input_mode": "text",
            "user_text": "隔離測試輸入",
            "assistant_reply": "今すぐできる一個だけ決めよ。",
            "logic": {"desired_response_mode_m23": mode},
            "cognition_trace": cognition,
            "memory_snapshot": memory,
        }

    def test_graph_renders_progressive_details_under_explicit_budgets(self):
        record = self._large_record()
        cognition = record["cognition_trace"]
        result = {
            "user_text": record["user_text"],
            "reply": record["assistant_reply"],
            "memory_data": record["memory_snapshot"],
            "runtime_trace": cognition["runtime_trace"],
            "runtime_state": cognition["runtime_state"],
        }

        graph = collect_cognitive_graph(result)
        html = render_memory_observatory(result)
        budget = graph["payload_budget_m24"]

        self.assertTrue(budget["budget_met"])
        self.assertLessEqual(
            budget["rendered_detail_bytes"], M24_GRAPH_DETAIL_BUDGET_BYTES
        )
        self.assertLessEqual(
            budget["largest_node_detail_bytes"], M24_NODE_DETAIL_BUDGET_BYTES
        )
        self.assertIn("Progressive Runtime Node Graph · M24", html)
        self.assertIn("local_web_jsonl", html)
        self.assertIn("desired_response_mode_m23", html)
        self.assertNotIn("TAIL_END_SHOULD_NOT_RENDER", html)

    def test_browser_cognition_keeps_decision_but_drops_repeated_full_history(self):
        record = self._large_record()
        full = record["cognition_trace"]
        compact = web._client_cognition_payload_m24(full)
        budget = compact["payload_budget_m24"]

        self.assertGreater(web._json_size_m24(full), 1_000_000)
        self.assertTrue(budget["budget_met"])
        self.assertLessEqual(
            web._json_size_m24(compact), web.M24_CLIENT_COGNITION_BUDGET_BYTES
        )
        self.assertEqual(
            compact["runtime_trace"]["desired_response_mode_m23"]["selected_mode"],
            "practical_help",
        )
        counts = compact["runtime_state"]["retained_history_counts"]
        self.assertEqual(counts["recent_turn_traces"], 8)
        self.assertEqual(counts["recent_autonomous_traces"], 5)
        self.assertFalse(counts["full_history_in_browser"])
        self.assertNotIn("recent_turn_traces", compact["runtime_state"])
        self.assertNotIn(
            "TAIL_END_SHOULD_NOT_RENDER", json.dumps(compact, ensure_ascii=False)
        )

    def test_browser_turn_state_is_bounded_while_local_record_remains_complete(self):
        record = self._large_record()
        client_cognition = web._client_cognition_payload_m24(
            record["cognition_trace"]
        )
        client_memory = web._client_memory_payload_m24(record["memory_snapshot"])
        client_turn = web._client_turn_record_m24(
            record,
            client_cognition,
            client_memory,
        )

        self.assertTrue(client_turn["payload_budget_m24"]["budget_met"])
        self.assertLessEqual(
            web._json_size_m24(client_turn), web.M24_CLIENT_TURN_BUDGET_BYTES
        )
        self.assertEqual(client_turn["user_text"], "隔離測試輸入")
        self.assertEqual(client_turn["assistant_reply"], "今すぐできる一個だけ決めよ。")
        self.assertIn("UNRENDERED_TAIL_", json.dumps(record, ensure_ascii=False))
        self.assertNotIn(
            "TAIL_END_SHOULD_NOT_RENDER", json.dumps(client_turn, ensure_ascii=False)
        )
        self.assertEqual(
            client_turn["payload_budget_m24"]["full_turn_retained_in"],
            "local_web_jsonl",
        )

    def test_text_and_audio_final_updates_use_progressive_client_payloads(self):
        with open(web.__file__, "r", encoding="utf-8") as handle:
            source = handle.read()

        self.assertIn(
            "client_cognition = _client_cognition_payload_m24(result[\"cognition_trace\"])",
            source,
        )
        self.assertEqual(source.count("client_record = _client_turn_record_m24("), 2)
        self.assertNotIn(
            'yield streamed_history, streamed_history, "", result["audio_path"], debug_payload, result["cognition_trace"]',
            source,
        )


if __name__ == "__main__":
    unittest.main()
