import inspect
import unittest

import run_source_preserving_memory_projection_v2_1_development as runner


def fake_generation(verdicts):
    return {
        "content": __import__("json").dumps({"verdicts": verdicts}),
        "carrier_valid": True,
        "carrier_error": None,
        "raw_content": "",
        "raw_tool_calls": [],
        "latency_seconds": 0.1,
        "prompt_sha256": "fake",
        "prompt_character_count": 100,
        "prompt_eval_count": 10,
        "eval_count": 5,
        "total_duration_ns": 1,
    }


class SourcePreservingMemoryProjectionV21RunnerTests(unittest.TestCase):
    def test_condition_candidates_switch_only_representation_text(self):
        case = {
            "target": {
                "trace_id": "t",
                "score": 0.9,
                "complete_session": {"text": "full", "source_turn_indices": [0, 1]},
                "source_projection": {"text": "projected", "source_turn_indices": [1]},
            }
        }
        condition = {
            "visible_candidates": ["target"],
            "expected_answer_bearing_candidate": "target",
        }
        full = runner.condition_candidates(case, condition, "complete_session")
        projected = runner.condition_candidates(case, condition, "source_projection")
        self.assertEqual(full[0]["trace_id"], projected[0]["trace_id"])
        self.assertEqual(full[0]["score"], projected[0]["score"])
        self.assertEqual(full[0]["text"], "full")
        self.assertEqual(projected[0]["text"], "projected")

    def test_run_one_does_not_read_official_answer(self):
        source = inspect.getsource(runner.run_one)
        self.assertNotIn("official_answer", source)
        source = inspect.getsource(runner.condition_candidates)
        self.assertNotIn("official_answer", source)

    def test_phase_one_gate_passes_valid_safe_rows(self):
        rows = []
        for case_index in range(8):
            for condition in ("remove_exact_hard_negative", "remove_exact_target"):
                for representation in ("complete_session", "source_projection"):
                    rows.append(
                        {
                            "case_id": f"case-{case_index}",
                            "condition": condition,
                            "representation": representation,
                            "target_supported": condition == "remove_exact_hard_negative",
                            "hard_negative_supported": False,
                            "evidence_validation": {"valid": True, "all_spans_grounded": True},
                            "transport_error_count": 0,
                        }
                    )
        prereg = {
            "staged_execution": {
                "phase_1_conditions": ["remove_exact_hard_negative", "remove_exact_target"],
                "phase_1_representations": ["complete_session", "source_projection"],
                "phase_1_call_count": 32,
                "phase_1_continue_only_if": {
                    "projected_target_only_supported_count_at_least": 6,
                    "projected_hard_negative_supported_count_equals": 0,
                    "transport_error_count_equals": 0,
                },
            }
        }
        self.assertTrue(runner.phase_1_passes(rows, prereg))

    def test_phase_one_gate_rejects_duplicate_row_matrix(self):
        rows = []
        for case_index in range(8):
            for condition in ("remove_exact_hard_negative", "remove_exact_target"):
                for representation in ("complete_session", "source_projection"):
                    rows.append(
                        {
                            "case_id": f"case-{case_index}",
                            "condition": condition,
                            "representation": representation,
                            "target_supported": condition == "remove_exact_hard_negative",
                            "hard_negative_supported": False,
                            "evidence_validation": {"valid": True, "all_spans_grounded": True},
                            "transport_error_count": 0,
                        }
                    )
        rows[-1] = dict(rows[0])
        prereg = {
            "staged_execution": {
                "phase_1_conditions": ["remove_exact_hard_negative", "remove_exact_target"],
                "phase_1_representations": ["complete_session", "source_projection"],
                "phase_1_call_count": 32,
                "phase_1_continue_only_if": {
                    "projected_target_only_supported_count_at_least": 6,
                    "projected_hard_negative_supported_count_equals": 0,
                    "transport_error_count_equals": 0,
                },
            }
        }
        self.assertFalse(runner.phase_1_passes(rows, prereg))

    def test_run_one_tracks_supported_source_without_runtime(self):
        case = {
            "case_id": "c",
            "official_question_id": "q",
            "question": "Where?",
            "target": {
                "trace_id": "t",
                "score": 0.9,
                "complete_session": {"text": "Place: home", "source_turn_indices": [0]},
                "source_projection": {"text": "Place: home", "source_turn_indices": [0]},
            },
        }
        condition = {
            "id": "remove_exact_hard_negative",
            "visible_candidates": ["target"],
            "expected_answer_bearing_candidate": "target",
        }

        def model_call(*_args):
            return fake_generation(
                [{"source_index": 0, "supports_answer": True, "answer_span": "home"}]
            )

        row = runner.run_one(
            case,
            condition,
            "source_projection",
            {},
            "unused",
            model_call=model_call,
        )
        self.assertTrue(row["safe_outcome"])
        self.assertEqual(row["supported_trace_ids"], ["t"])
        self.assertEqual(row["production_memory_write_count"], 0)
        self.assertEqual(row["physical_vrm_action_count"], 0)


if __name__ == "__main__":
    unittest.main()
