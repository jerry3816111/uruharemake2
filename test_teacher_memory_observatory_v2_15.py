import unittest
from unittest import mock

from uruha_memory_observatory import (
    MEMORY_OBSERVATORY_CSS,
    _graph_kind,
    collect_cognitive_graph,
    collect_memory_nodes,
    render_memory_observatory,
)
from uruha_web_ui import WEB_HEAD, RUNTIME, _observatory_result_from_log_record, reset_session


class TeacherMemoryObservatoryV215Tests(unittest.TestCase):
    def _fixture(self):
        return {
            "user_text": "你還記得我喜歡喝什麼嗎？",
            "reply": "草莓牛奶。",
            "memory_data": {
                "working_memory_items": [
                    {
                        "trace_id": "stored:profile:tea",
                        "source": "profile",
                        "text": "使用者喜歡草莓牛奶",
                        "score": 0.92,
                    }
                ],
                "memory_provenance": {
                    "retrieved_candidate_count": 3,
                    "candidate_count": 2,
                    "candidate_pool": [
                        {
                            "trace_id": "stored:profile:tea",
                            "source": "profile",
                            "text": "使用者喜歡草莓牛奶",
                            "score": 0.92,
                            "rank": 1,
                            "selected": True,
                        },
                        {
                            "trace_id": "stored:episode:old",
                            "source": "episode",
                            "text": "<script>alert('no')</script>",
                            "score": 0.31,
                            "rank": 2,
                            "selected": False,
                        },
                    ],
                    "selected_working_memory_trace_ids": ["stored:profile:tea"],
                    "passed_to_leftbrain_trace_ids": [
                        "stored:profile:tea",
                        "derived:procedural:support",
                    ],
                    "passed_to_leftbrain": [
                        {
                            "trace_id": "derived:procedural:support",
                            "source": "procedural",
                            "text": "先確認對方的情緒，再提出一個具體步驟",
                            "channel": "direct_procedural",
                            "score": 0.66,
                        }
                    ],
                },
            },
            "runtime_trace": {
                "blackboard": [
                    {
                        "stage": "retrieve",
                        "label": "working_memory",
                        "salience": 0.93,
                        "payload": {"summary": "找到草莓牛奶偏好"},
                    },
                    {
                        "stage": "attention",
                        "label": "attention_frame",
                        "salience": 0.91,
                        "payload": {"focus": "最喜歡的飲料"},
                    },
                    {
                        "stage": "select",
                        "label": "selected_plan",
                        "salience": 0.97,
                        "payload": {"intent": "memory_recall", "reply_goal": "回答偏好"},
                    },
                    {
                        "stage": "surface",
                        "label": "utterance",
                        "salience": 0.9,
                        "payload": {"text": "草莓牛奶。"},
                    },
                ],
                "state_diff": {
                    "psyche": {
                        "mood_before": 0,
                        "mood_after": 1,
                        "mood_delta": 1,
                    },
                    "focus": {"before": "飲料", "after": "草莓牛奶"},
                },
                "memory_writes": [
                    {
                        "layer": "episodic_memory",
                        "kind": "turn_episode",
                        "summary": "記住這次飲料偏好回想",
                    }
                ]
            },
        }

    def test_renders_runtime_as_clickable_node_graph(self):
        html = render_memory_observatory(self._fixture())
        self.assertIn("Runtime Node Graph", html)
        self.assertIn("brain-graph-canvas", html)
        self.assertIn("brain-edge is-selected", html)
        self.assertIn("brain-edge is-active", html)
        self.assertIn("<details", html)
        self.assertIn("attention_frame", html)
        self.assertIn("使用者喜歡草莓牛奶", html)
        self.assertIn("is-selected", html)
        self.assertIn("is-active", html)
        self.assertIn("episodic_memory", html)
        self.assertIn("記住這次飲料偏好回想", html)
        self.assertNotIn("trace-card", html)

    def test_graph_contains_runtime_memory_state_and_writeback_nodes(self):
        graph = collect_cognitive_graph(self._fixture())
        by_id = {node["id"]: node for node in graph["nodes"]}
        self.assertIn("turn-input", by_id)
        self.assertIn("turn-output", by_id)
        self.assertIn("memory-0", by_id)
        self.assertIn("state-psyche-mood", by_id)
        self.assertIn("write-0", by_id)
        self.assertTrue(any(edge["class"] == "is-active" for edge in graph["edges"]))

    def test_new_or_unknown_runtime_stage_cannot_break_the_graph(self):
        fixture = self._fixture()
        fixture["runtime_trace"]["blackboard"].extend(
            [
                {"stage": "plan", "label": "adaptive_planner_fast_path_m17", "payload": {}},
                {"stage": "future_stage", "label": "forward_compatible_trace", "payload": {}},
                {
                    "stage": "select",
                    "label": "desired_response_candidates_m17",
                    "payload": {
                        "schema": "uruha_desired_response_candidates_m17",
                        "candidates": ["compact-old-trace"],
                        "utility_margin": 0.2,
                    },
                },
            ]
        )

        graph = collect_cognitive_graph(fixture)

        self.assertEqual(_graph_kind("plan"), "select")
        self.assertEqual(_graph_kind("future_stage"), "appraise")
        self.assertTrue(any(node["label"] == "adaptive_planner_fast_path_m17" for node in graph["nodes"]))

    def test_direct_passed_memory_is_not_lost_when_absent_from_candidate_pool(self):
        nodes = collect_memory_nodes(self._fixture())
        by_id = {row["trace_id"]: row for row in nodes}
        self.assertIn("derived:procedural:support", by_id)
        self.assertTrue(by_id["derived:procedural:support"]["passed"])
        self.assertEqual(by_id["derived:procedural:support"]["source_key"], "procedural")

    def test_runtime_memory_text_is_html_escaped(self):
        html = render_memory_observatory(self._fixture())
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)

    def test_unknown_source_cannot_inject_css_class(self):
        fixture = self._fixture()
        fixture["memory_data"]["memory_provenance"]["candidate_pool"][1]["source"] = 'x\" onmouseover="bad'
        nodes = collect_memory_nodes(fixture)
        by_id = {row["trace_id"]: row for row in nodes}
        self.assertEqual(by_id["stored:episode:old"]["source_key"], "unknown")

    def test_empty_state_and_reduced_motion_are_available(self):
        html = render_memory_observatory({})
        self.assertIn("送出訊息後，節點與流向會在這裡亮起", html)
        self.assertIn("prefers-reduced-motion", MEMORY_OBSERVATORY_CSS)

    def test_voice_button_label_update_is_idempotent_for_safari(self):
        self.assertIn(
            'record && window.__uruhaVadAttached && record.textContent !== "Just Start Talking"',
            WEB_HEAD,
        )

    def test_reset_session_returns_one_value_for_each_bound_web_output(self):
        with mock.patch.object(RUNTIME, "reset_brain_session", return_value=None):
            values = reset_session()
        self.assertEqual(len(values), 13)

    def test_hands_free_vad_waits_for_explicit_voice_mode_opt_in(self):
        self.assertEqual(WEB_HEAD.count("attachVad();"), 1)
        self.assertIn('input.addEventListener("change", enableHandsFree)', WEB_HEAD)

    def test_logged_runtime_can_seed_the_external_browser_graph(self):
        fixture = self._fixture()
        result = _observatory_result_from_log_record(
            {
                "user_text": fixture["user_text"],
                "assistant_reply": fixture["reply"],
                "memory_snapshot": fixture["memory_data"],
                "cognition_trace": {"runtime_trace": fixture["runtime_trace"]},
            }
        )
        self.assertEqual(result["user_text"], fixture["user_text"])
        self.assertEqual(result["reply"], fixture["reply"])
        self.assertEqual(len(result["runtime_trace"]["blackboard"]), 4)

    def test_m32_commit_and_surface_are_visible_as_a_causal_graph_path(self):
        fixture = self._fixture()
        contract = {
            "schema": "uruha_deterministic_semantic_commit_m32",
            "status": "deterministic_commit_repaired",
            "repair_kind": "authoritative_surface_completeness_override",
            "surface_authority": True,
            "surface_status": "matched",
            "visible_anchor_count": 3,
            "rejection_checks_m31": ["surface_self_check:subject_preserved"],
            "response_jp": "ダニエルは火曜日にメイに赤いペン四本を渡したんだね。",
        }
        fixture["runtime_trace"]["semantic_commit_repair_m32"] = contract
        fixture["runtime_trace"]["blackboard"].extend(
            [
                {
                    "stage": "verify",
                    "label": "semantic_authorization_m31",
                    "payload": {
                        "schema": "uruha_semantic_authorization_m31",
                        "status": "semantically_authorized",
                    },
                },
                {
                    "stage": "surface",
                    "label": "semantic_commit_repair_m32",
                    "payload": contract,
                },
                {
                    "stage": "surface",
                    "label": "semantic_commit_surface_m32",
                    "payload": contract,
                },
            ]
        )

        graph = collect_cognitive_graph(fixture)
        html = render_memory_observatory(fixture)
        by_label = {node["label"]: node["id"] for node in graph["nodes"]}

        self.assertIn("semantic_commit_repair_m32", by_label)
        self.assertIn("semantic_commit_surface_m32", by_label)
        self.assertTrue(
            any(
                edge["source"] == by_label["semantic_authorization_m31"]
                and edge["target"] == by_label["semantic_commit_repair_m32"]
                for edge in graph["edges"]
            )
        )
        self.assertIn("COMPLETE SEMANTIC COMMIT · M32", html)
        self.assertIn("authoritative_surface_completeness_override", html)

    def test_m33_source_atoms_verification_and_commit_are_visible(self):
        fixture = self._fixture()
        ledger = {
            "schema": "uruha_source_semantic_atom_ledger_m33",
            "status": "source_atoms_extracted",
            "family": "negated_object_quantity",
            "atom_count": 4,
            "atoms": [
                {"type": "object", "value_jp": "鉛筆", "source_span_digest": "abc"}
            ],
        }
        verification = {
            "schema": "uruha_source_atom_verification_m33",
            "status": "source_canonical_conflict",
            "conflict_atom_count": 1,
        }
        commitment = {
            "schema": "uruha_source_anchored_semantic_commit_m33",
            "status": "source_anchored_semantic_committed",
            "repair_kind": "source_atom_bounded_reconstruction",
            "surface_authority": True,
            "source_atom_trace_coverage": 1.0,
            "surface_status": "matched",
            "response_jp": "箱には三本の鉛筆がないんだね。",
        }
        fixture["runtime_trace"].update(
            {
                "source_semantic_atoms_m33": ledger,
                "semantic_atom_verification_m33": verification,
                "source_anchored_semantic_commit_m33": commitment,
            }
        )
        fixture["runtime_trace"]["blackboard"].extend(
            [
                {"stage": "understand", "label": "source_semantic_atoms_m33", "payload": ledger},
                {"stage": "verify", "label": "semantic_atom_verification_m33", "payload": verification},
                {"stage": "surface", "label": "source_anchored_semantic_commit_m33", "payload": commitment},
                {"stage": "surface", "label": "source_anchored_semantic_surface_m33", "payload": commitment},
            ]
        )

        graph = collect_cognitive_graph(fixture)
        html = render_memory_observatory(fixture)
        labels = {node["label"] for node in graph["nodes"]}

        self.assertIn("source_semantic_atoms_m33", labels)
        self.assertIn("semantic_atom_verification_m33", labels)
        self.assertIn("source_anchored_semantic_surface_m33", labels)
        self.assertIn("SOURCE-ANCHORED SEMANTIC ATOM LEDGER · M33", html)
        self.assertIn("source_atom_bounded_reconstruction", html)
        self.assertIn("M33 · SOURCE-ANCHORED SEMANTIC ATOM SEALED RESERVE", html)
        self.assertIn("FROZEN GATE · PASS", html)
        self.assertIn("12/12", html)
        self.assertIn("只證明 5 類 bounded construction", html)


if __name__ == "__main__":
    unittest.main()
