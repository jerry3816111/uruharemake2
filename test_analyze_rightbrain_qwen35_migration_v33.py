import unittest

from analyze_rightbrain_qwen35_migration_v33 import (
    _paired_binary,
    exact_mcnemar,
    expected_holdout_accounting,
)


class AnalyzeRightBrainQwen35MigrationV33Test(unittest.TestCase):
    def test_exact_mcnemar_is_one_without_discordant_pairs(self):
        self.assertEqual(exact_mcnemar(0, 0), 1.0)

    def test_exact_mcnemar_detects_one_sided_difference(self):
        self.assertLess(exact_mcnemar(0, 10), 0.01)

    def test_paired_binary_preserves_direction(self):
        control = {"a": False, "b": True, "c": False, "d": True}
        treatment = {"a": True, "b": True, "c": True, "d": False}
        result = _paired_binary(control, treatment)
        self.assertEqual(result["treatment_wins"], 2)
        self.assertEqual(result["control_wins"], 1)
        self.assertEqual(result["ties"], 1)
        self.assertEqual(result["treatment_delta"], 0.25)

    def test_paired_binary_rejects_mismatched_keys(self):
        with self.assertRaises(ValueError):
            _paired_binary({"a": True}, {"b": True})

    def test_expected_accounting_expands_preregistered_groups(self):
        prereg = {
            "stage_1_design": {
                "fresh_holdout": {
                    "rightbrain_cases_per_category": 4,
                    "rightbrain_categories": ["support", "memory"],
                    "action_cases_per_family": 20,
                    "action_families": ["explicit", "negated"],
                }
            }
        }
        self.assertEqual(
            expected_holdout_accounting(prereg),
            {
                "rightbrain_categories": {"support": 4, "memory": 4},
                "action_families": {"explicit": 20, "negated": 20},
            },
        )


if __name__ == "__main__":
    unittest.main()
