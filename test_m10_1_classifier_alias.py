import unittest

from longitudinal_human_model.realization_parser_v1_1 import ClassifierAliasParser


LABELS = [
    "accept_support_and_continue",
    "acknowledge_then_continue",
    "ask_clarification",
    "defer_commitment",
    "direct_rejection",
    "pause_and_reassess",
]


class M101ClassifierAliasTests(unittest.TestCase):
    def test_exact_classification_alias_is_normalized_and_recorded(self):
        parser = ClassifierAliasParser()
        raw = {label: float(label == "direct_rejection") for label in LABELS}
        result = parser('{"brief_evidence":"x","classification":' + __import__('json').dumps(raw) + '}', LABELS)
        self.assertEqual(result["selected_behavior"], "direct_rejection")
        self.assertEqual(result["distribution_source_key"], "classification")
        self.assertEqual(len(parser.normalizations), 1)

    def test_existing_probabilities_are_untouched(self):
        parser = ClassifierAliasParser()
        raw = {label: float(label == "ask_clarification") for label in LABELS}
        result = parser('{"probabilities":' + __import__('json').dumps(raw) + '}', LABELS)
        self.assertEqual(result["selected_behavior"], "ask_clarification")
        self.assertEqual(result["distribution_source_key"], "probabilities")
        self.assertEqual(parser.normalizations, [])

    def test_alias_with_wrong_label_set_fails_closed(self):
        parser = ClassifierAliasParser()
        with self.assertRaises(ValueError):
            parser('{"classification":{"direct_rejection":1}}', LABELS)


if __name__ == "__main__":
    unittest.main()
