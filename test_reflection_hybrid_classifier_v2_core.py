import unittest

from reflection_hybrid_classifier_v2_core import (
    analyze_condition,
    select_smallest_passing,
)


CASES = [
    {"id": "s", "language": "eng", "expected_type": "semantic"},
    {"id": "p", "language": "eng", "expected_type": "procedural"},
    {"id": "i", "language": "jpn", "expected_type": "interpretive"},
    {"id": "n", "language": "cmn", "expected_type": "none"},
]
RULES = {"s": "semantic", "p": "none", "i": "none", "n": "none"}
GATES = {
    "hybrid_correct_count_min": 4,
    "hybrid_accuracy_min": 1.0,
    "semantic_correct_min": 1,
    "procedural_correct_min": 1,
    "interpretive_correct_min": 1,
    "none_correct": 1,
    "newly_correct_vs_rules_min": 2,
    "regression_vs_rules_max": 0,
    "critical_false_positive_count_max": 0,
    "parse_success_rate_min": 1.0,
    "model_call_count_max": 3,
    "median_fallback_wall_seconds_max": 1.0,
    "warm_p95_fallback_wall_seconds_max": 1.0,
}


def _row(case_id, label, wall):
    return {
        "id": case_id,
        "observed_type": label,
        "parse_success": True,
        "wall_seconds": wall,
    }


class ReflectionHybridClassifierV2CoreTest(unittest.TestCase):
    def test_conservative_fallback_passes_without_overriding_rule_positives(self):
        rows = [_row("p", "procedural", 0.5), _row("i", "interpretive", 0.6), _row("n", "none", 0.7)]
        result = analyze_condition(CASES, RULES, rows, GATES)
        self.assertTrue(result["all_gates_pass"])
        self.assertEqual(result["hybrid_correct_count"], 4)
        self.assertEqual(result["newly_correct_count"], 2)
        self.assertEqual(result["regression_count"], 0)
        self.assertEqual(result["model_call_count"], 3)

    def test_false_memory_and_parse_failure_fail_closed(self):
        rows = [_row("p", "procedural", 0.5), _row("i", "none", 0.6), _row("n", "semantic", 0.7)]
        rows[1]["parse_success"] = False
        result = analyze_condition(CASES, RULES, rows, GATES)
        self.assertFalse(result["all_gates_pass"])
        self.assertEqual(result["critical_false_positive_count"], 1)
        self.assertEqual(result["regression_count"], 1)
        self.assertLess(result["parse_success_rate"], 1.0)

    def test_fallback_must_cover_exactly_rules_none_cases(self):
        with self.assertRaisesRegex(ValueError, "exactly match"):
            analyze_condition(CASES, RULES, [_row("p", "procedural", 0.5)], GATES)

    def test_smallest_passing_model_is_selected(self):
        models = [{"model": "small"}, {"model": "medium"}, {"model": "large"}]
        analyses = {
            "small": {"all_gates_pass": False},
            "medium": {"all_gates_pass": True},
            "large": {"all_gates_pass": True},
        }
        self.assertEqual(select_smallest_passing(models, analyses), "medium")
        self.assertIsNone(
            select_smallest_passing(models, {"small": {"all_gates_pass": False}})
        )


if __name__ == "__main__":
    unittest.main()
