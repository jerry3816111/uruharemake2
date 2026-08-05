import inspect
import unittest

import build_source_preserving_memory_projection_v2_development as builder


class BuildSourcePreservingMemoryProjectionV2DevelopmentTests(unittest.TestCase):
    def test_complete_representation_does_not_truncate_turns(self):
        content = "prefix-" + ("x" * 1200) + "-suffix"
        result = builder.complete_representation(
            [{"role": "user", "content": content}], "2026/08/05 10:00"
        )
        self.assertIn(content, result["text"])
        self.assertTrue(result["text"].endswith("-suffix"))
        self.assertEqual(result["source_turn_indices"], [0])

    def test_projection_uses_question_overlap_and_keeps_source_order(self):
        session = [
            {"role": "user", "content": "I bought oranges."},
            {"role": "assistant", "content": "Okay."},
            {"role": "user", "content": "The blue folder is in the reading room."},
            {"role": "user", "content": "The blue folder needs repair."},
            {"role": "user", "content": "I drank tea."},
        ]
        result = builder.projection_representation(
            session,
            "2026/08/05 10:00",
            "Where is the blue folder?",
            top_k=2,
        )
        self.assertEqual(result["source_turn_indices"], [2, 3])
        self.assertIn("reading room", result["text"])
        self.assertNotIn("oranges", result["text"])

    def test_projection_function_has_no_answer_or_expected_trace_input(self):
        parameters = inspect.signature(builder.projection_representation).parameters
        self.assertNotIn("answer", parameters)
        self.assertNotIn("expected_trace_id", parameters)
        source = inspect.getsource(builder.projection_representation)
        self.assertNotIn("official_answer", source)

    def test_hard_negative_rejects_answer_text(self):
        row = {
            "question_id": "example",
            "question": "Where is the blue folder?",
            "answer": "reading room",
            "answer_session_ids": ["target"],
            "haystack_session_ids": ["target", "leaky", "valid"],
            "haystack_dates": ["d1", "d2", "d3"],
            "haystack_sessions": [
                [{"role": "user", "content": "It is in the reading room."}],
                [{"role": "user", "content": "The reading room has a blue folder."}],
                [{"role": "user", "content": "The blue folder cover needs repair."}],
            ],
        }
        selected = builder.choose_hard_negative(row, maximum_characters=7000)
        self.assertEqual(selected["session_id"], "valid")
        self.assertNotIn("reading room", selected["complete"]["text"].lower())

    def test_builder_has_no_model_or_runtime_calls(self):
        source = inspect.getsource(builder)
        self.assertNotIn("ollama_chat", source)
        self.assertNotIn("requests.post", source)
        self.assertNotIn("uruha_brain", source)


if __name__ == "__main__":
    unittest.main()
