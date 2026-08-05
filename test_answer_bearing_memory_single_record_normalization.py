import unittest

import answer_bearing_memory_single_record_normalization as normalization


class SingleRecordNormalizationTests(unittest.TestCase):
    def test_quote_only_negative_placeholders_normalize(self):
        for value in ('""', "''", "“”", "‘’", '  ""  '):
            payload, audit = normalization.normalize(
                {"supports_answer": False, "answer_span": value}
            )
            self.assertEqual(payload["answer_span"], "")
            self.assertTrue(audit["applied"])

    def test_positive_verdict_is_never_changed(self):
        original = {"supports_answer": True, "answer_span": '""'}
        payload, audit = normalization.normalize(original)
        self.assertEqual(payload, original)
        self.assertFalse(audit["applied"])

    def test_nonempty_negative_span_is_never_changed(self):
        original = {"supports_answer": False, "answer_span": '"answer"'}
        payload, audit = normalization.normalize(original)
        self.assertEqual(payload, original)
        self.assertFalse(audit["applied"])

    def test_invalid_payload_is_never_repaired(self):
        original = {"answer_span": '""'}
        payload, audit = normalization.normalize(original)
        self.assertEqual(payload, original)
        self.assertFalse(audit["applied"])


if __name__ == "__main__":
    unittest.main()
