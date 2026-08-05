import unittest

import answer_bearing_memory_single_record as single


class AnswerBearingMemorySingleRecordTests(unittest.TestCase):
    def test_schema_has_no_source_index(self):
        schema = single.json_schema()
        self.assertEqual(set(schema["properties"]), {"supports_answer", "answer_span"})
        self.assertNotIn("source_index", str(schema))

    def test_grounded_positive_is_normalized_to_source_zero(self):
        candidate = {"trace_id": "t", "text": "I packed 7 shirts."}
        result = single.validate(
            {"supports_answer": True, "answer_span": "7 shirts"}, candidate
        )
        self.assertTrue(result["valid"])
        self.assertEqual(result["verdicts"][0]["source_index"], 0)
        self.assertEqual(result["verdicts"][0]["trace_id"], "t")

    def test_unsupported_verdict_requires_empty_span(self):
        candidate = {"trace_id": "t", "text": "No answer here."}
        result = single.validate(
            {"supports_answer": False, "answer_span": "answer"}, candidate
        )
        self.assertFalse(result["valid"])

    def test_positive_span_must_be_verbatim_grounded(self):
        candidate = {"trace_id": "t", "text": "I packed 7 shirts."}
        result = single.validate(
            {"supports_answer": True, "answer_span": "seven shirts"}, candidate
        )
        self.assertFalse(result["valid"])


if __name__ == "__main__":
    unittest.main()
