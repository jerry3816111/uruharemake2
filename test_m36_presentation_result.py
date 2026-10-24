import unittest

from uruha_memory_observatory import _load_m36_compositional_summary


class M36PresentationResultTests(unittest.TestCase):
    def test_loader_preserves_the_frozen_fail_and_key_metrics(self):
        summary = _load_m36_compositional_summary()

        self.assertTrue(summary["available"])
        self.assertEqual(summary["decision"], "fail_one_or_more_frozen_gates")
        self.assertEqual(summary["case_count"], 12)
        self.assertAlmostEqual(summary["baseline_accuracy"], 0.1667)
        self.assertAlmostEqual(summary["system_accuracy"], 0.8333)
        self.assertAlmostEqual(summary["accuracy_delta"], 0.6666)
        self.assertEqual(summary["annotation_error_count"], 0)
        self.assertEqual(summary["failed_gate_count"], 7)
        self.assertFalse(summary["human_evidence"])


if __name__ == "__main__":
    unittest.main()
