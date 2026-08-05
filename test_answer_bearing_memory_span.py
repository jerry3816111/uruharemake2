import unittest

from answer_bearing_memory_span import (
    anchored_source_span,
    build_answer_evidence_json_schema,
    build_answer_evidence_prompt,
    parse_answer_evidence,
    supported_candidates,
    validate_answer_evidence,
)


class AnswerBearingMemorySpanTests(unittest.TestCase):
    def setUp(self):
        self.candidates = [
            {"trace_id": "target", "text": "We agreed to meet at the north gate."},
            {"trace_id": "negative", "text": "The station has several gates."},
        ]

    def test_schema_requires_one_verdict_per_candidate(self):
        schema = build_answer_evidence_json_schema(2)
        verdicts = schema["properties"]["verdicts"]
        self.assertEqual(verdicts["minItems"], 2)
        self.assertEqual(verdicts["maxItems"], 2)

    def test_prompt_contains_no_expected_trace_or_gold(self):
        prompt = build_answer_evidence_prompt("Where did we agree to meet?", self.candidates)
        self.assertIn("north gate", prompt)
        self.assertNotIn("expected_trace", prompt)
        self.assertNotIn("official_answer", prompt)

    def test_validates_grounded_answer_and_rejects_topic_overlap(self):
        payload = {
            "verdicts": [
                {
                    "source_index": 0,
                    "supports_answer": True,
                    "answer_span": "north gate",
                },
                {
                    "source_index": 1,
                    "supports_answer": False,
                    "answer_span": "",
                },
            ]
        }
        result = validate_answer_evidence(payload, self.candidates)
        self.assertTrue(result["valid"])
        selected = supported_candidates(result, self.candidates)
        self.assertEqual([row["trace_id"] for row in selected], ["target"])
        self.assertEqual(selected[0]["answer_evidence"]["answer_span"], "north gate")

    def test_ungrounded_span_fails_closed_for_entire_call(self):
        payload = {
            "verdicts": [
                {"source_index": 0, "supports_answer": True, "answer_span": "south gate"},
                {"source_index": 1, "supports_answer": False, "answer_span": ""},
            ]
        }
        result = validate_answer_evidence(payload, self.candidates)
        self.assertFalse(result["valid"])
        self.assertEqual(supported_candidates(result, self.candidates), [])

    def test_missing_or_duplicate_indices_fail_closed(self):
        payload = {
            "verdicts": [
                {"source_index": 0, "supports_answer": True, "answer_span": "north gate"},
                {"source_index": 0, "supports_answer": False, "answer_span": ""},
            ]
        }
        self.assertFalse(validate_answer_evidence(payload, self.candidates)["valid"])

    def test_false_verdict_must_not_carry_a_span(self):
        payload = {
            "verdicts": [
                {"source_index": 0, "supports_answer": False, "answer_span": "north gate"},
                {"source_index": 1, "supports_answer": False, "answer_span": ""},
            ]
        }
        self.assertFalse(validate_answer_evidence(payload, self.candidates)["valid"])

    def test_parse_rejects_extra_fields(self):
        value = '{"verdicts":[{"source_index":0,"supports_answer":false,"answer_span":"","reason":"x"}]}'
        self.assertIsNone(parse_answer_evidence(value))

    def test_whitespace_variation_anchors_to_original_source(self):
        source = "We agreed to meet at the\n north gate."
        self.assertEqual(
            anchored_source_span(source, "the north gate"), "the\n north gate"
        )


if __name__ == "__main__":
    unittest.main()
