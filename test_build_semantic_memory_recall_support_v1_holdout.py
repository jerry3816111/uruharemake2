import inspect
import unittest

import build_semantic_memory_recall_support_v1_holdout as builder


def synthetic_row(question_id, *, split_answer_count=1):
    return {
        "question_id": question_id,
        "question_type": "single-session-user",
        "question": "Where did I leave the blue folder?",
        "answer": "reading room",
        "answer_session_ids": ["target"] * split_answer_count,
        "haystack_session_ids": ["target", "near", "far"],
        "haystack_dates": ["2026/01/01 10:00", "2026/01/02 10:00", "2026/01/03 10:00"],
        "haystack_sessions": [
            [{"role": "user", "content": "I left the blue folder in the reading room."}],
            [{"role": "user", "content": "The blue folder cover needs repair."}],
            [{"role": "user", "content": "I bought oranges."}],
        ],
    }


class BuildSemanticMemoryRecallSupportV1HoldoutTests(unittest.TestCase):
    def test_hard_negative_uses_independent_overlap(self):
        row = synthetic_row("example")
        selected = builder.hard_negative_session(row)

        self.assertEqual(selected["session_id"], "near")
        self.assertGreater(selected["independent_overlap"], 0.0)

    def test_relevant_excerpt_prioritizes_answer_turn(self):
        session = [
            {"role": "user", "content": "I bought oranges."},
            {"role": "user", "content": "I left the blue folder in the reading room."},
        ]
        excerpt = builder.relevant_excerpt(
            session,
            "2026/01/01 10:00",
            "Where did I leave the blue folder?",
            "reading room",
            max_turns=1,
        )

        self.assertIn("reading room", excerpt)
        self.assertNotIn("oranges", excerpt)

    def test_builder_does_not_call_runtime_support_for_selection(self):
        source = inspect.getsource(builder)
        self.assertNotIn("memory_query_support", source)
        self.assertNotIn("memory_recall_focus_units", source)

    def test_english_generation_schema_only_allows_replacement(self):
        self.assertEqual(
            set(builder.REPLACEMENT_SCHEMA["properties"]),
            {"replacement_text"},
        )

    def test_paraphrase_retry_keeps_same_fixed_seed(self):
        source = inspect.getsource(builder.generate_language_row)
        self.assertIn("seed=SEED", source)
        self.assertIn("paraphrase_retry_used", source)


if __name__ == "__main__":
    unittest.main()
