import unittest

from build_unified_eval_summary import _compact_domain_suite_summary, _flatten_long_dialogue_memory_summary
from build_research_vnext_90plus_report import _long_dialogue_recall_summary
from memory_causal_effect_eval import build_cases, build_summary
from project_paths import (
    MEMORY_CAUSAL_EFFECT_REPORT_JSON_PATH,
    MEMORY_SPEAKABILITY_RESPONSE_REPORT_JSON_PATH,
)
from run_domain_eval_suite import TASKS


class UnifiedMemorySummaryTest(unittest.TestCase):
    def test_domain_suite_summary_drops_captured_process_output(self):
        compact = _compact_domain_suite_summary(
            {
                "summary": {
                    "task_runs": [
                        {
                            "task": "surface_microplanning",
                            "returncode": 0,
                            "execution_mode": "executed",
                            "stdout_tail": "large output",
                            "stderr_tail": "large error output",
                        }
                    ]
                }
            }
        )
        self.assertEqual(compact["task_runs"][0]["task"], "surface_microplanning")
        self.assertNotIn("stdout_tail", compact["task_runs"][0])
        self.assertNotIn("stderr_tail", compact["task_runs"][0])

    def test_flatten_long_dialogue_memory_summary_exposes_nested_recall(self):
        summary = {
            "delayed_recall": {
                "delayed_recall_rate": 0.92,
            },
            "speakability": {
                "case_pass_rate": 0.84,
                "label_accuracy": 0.88,
            },
        }

        flat = _flatten_long_dialogue_memory_summary(summary)

        self.assertEqual(flat["delayed_recall_rate"], 0.92)
        self.assertEqual(flat["memory_speakability_case_pass_rate"], 0.84)
        self.assertEqual(flat["memory_speakability_label_accuracy"], 0.88)
        self.assertEqual(flat["delayed_recall"], summary["delayed_recall"])
        self.assertEqual(flat["speakability"], summary["speakability"])

    def test_research_report_reads_nested_delayed_recall_summary(self):
        report = {
            "summary": {
                "delayed_recall": {
                    "delayed_recall_rate": 0.91,
                    "profile_capture_rate": 0.82,
                },
                "speakability": {
                    "case_pass_rate": 0.77,
                },
            }
        }

        recall = _long_dialogue_recall_summary(report)

        self.assertEqual(recall["delayed_recall_rate"], 0.91)
        self.assertEqual(recall["profile_capture_rate"], 0.82)

    def test_domain_suite_refreshes_memory_causal_and_speakability_reports(self):
        tasks = {key: (script, report_path) for key, script, report_path in TASKS}

        self.assertEqual(
            tasks["memory_causal_effect"],
            ("memory_causal_effect_eval.py", MEMORY_CAUSAL_EFFECT_REPORT_JSON_PATH),
        )
        self.assertEqual(
            tasks["memory_speakability_response"],
            ("memory_speakability_response_eval.py", MEMORY_SPEAKABILITY_RESPONSE_REPORT_JSON_PATH),
        )

    def test_memory_causal_summary_separates_positive_and_negative_controls(self):
        rows = [
            {
                "category": "positive",
                "language": "ja",
                "memory_effect_expected": 1,
                "strong_causal_effect": 1,
                "weak_causal_effect": 1,
                "appropriate_memory_effect": 1,
                "unwanted_memory_intrusion": 0,
                "anchor_in_reply": 1,
                "anchor_in_working_memory": 1,
                "memory_expected": 1,
                "memory_used_explicitly": 1,
                "memory_relevance": 1.0,
            },
            {
                "category": "positive",
                "language": "zh",
                "memory_effect_expected": 1,
                "strong_causal_effect": 0,
                "weak_causal_effect": 0,
                "appropriate_memory_effect": 0,
                "unwanted_memory_intrusion": 0,
                "anchor_in_reply": 0,
                "anchor_in_working_memory": 1,
                "memory_expected": 1,
                "memory_used_explicitly": 0,
                "memory_relevance": 0.4,
            },
            {
                "category": "negative",
                "language": "ja",
                "memory_effect_expected": 0,
                "strong_causal_effect": 0,
                "weak_causal_effect": 0,
                "appropriate_memory_effect": 1,
                "negative_control_pass": 1,
                "unwanted_memory_intrusion": 0,
                "anchor_in_reply": 0,
                "anchor_in_working_memory": 1,
                "memory_expected": 0,
                "memory_used_explicitly": 0,
                "memory_relevance": 0.1,
            },
            {
                "category": "negative",
                "language": "zh",
                "memory_effect_expected": 0,
                "strong_causal_effect": 0,
                "weak_causal_effect": 1,
                "appropriate_memory_effect": 0,
                "negative_control_pass": 0,
                "unwanted_memory_intrusion": 1,
                "anchor_in_reply": 1,
                "anchor_in_working_memory": 1,
                "memory_expected": 1,
                "memory_used_explicitly": 1,
                "memory_relevance": 0.8,
            },
        ]

        summary = build_summary(rows)

        self.assertEqual(summary["positive_cases"], 2)
        self.assertEqual(summary["negative_control_cases"], 2)
        self.assertEqual(summary["strong_causal_effect_rate"], 0.5)
        self.assertEqual(summary["negative_control_pass_rate"], 0.5)
        self.assertEqual(summary["unwanted_memory_intrusion_rate"], 0.5)
        self.assertEqual(summary["appropriate_memory_effect_rate"], 0.5)
        self.assertEqual(summary["memory_expected_rate"], 1.0)
        self.assertEqual(summary["memory_used_explicitly_rate"], 0.5)
        self.assertEqual(summary["overall_memory_used_explicitly_rate"], 0.5)
        self.assertEqual(summary["by_language"]["ja"]["strong_causal_effect_rate"], 1.0)
        self.assertEqual(summary["by_language"]["ja"]["negative_control_pass_rate"], 1.0)

    def test_memory_causal_cases_include_negative_controls(self):
        cases = build_cases()
        negative_cases = [case for case in cases if not case["memory_effect_expected"]]

        self.assertGreaterEqual(len(negative_cases), 5)
        self.assertTrue(any(case["category"] == "sensitive_memory_control" for case in negative_cases))
        self.assertTrue(any(case["category"] == "third_party_memory_control" for case in negative_cases))


if __name__ == "__main__":
    unittest.main()
