import importlib
import os
import unittest

from project_paths import (
    BASE_DIR,
    REPLY_DIVERSITY_REPORT_PATH,
    RIGHTBRAIN_MODEL_GATE_REPORT_JSON_PATH,
    RUNTIME_DYNAMICS_REPORT_PATH,
    STRESS_EVAL_REPORT_PATH,
    SURFACE_MICROPLANNING_REPORT_JSON_PATH,
    V2_HUMAN_ANSWER_REPORT_PATH,
)


class ReportOutputPathTest(unittest.TestCase):
    def test_legacy_root_reports_are_not_present(self):
        legacy_names = [
            "cognitive_architecture_eval_report.json",
            "formal_brain_benchmarks_report.json",
            "formal_brain_benchmarks_report.md",
            "formal_tombench_refresh.json",
            "reply_diversity_report.json",
            "stress_eval_report_10000.json",
            "system_vs_prompt_only_compare.json",
            "unified_eval_summary.json",
            "unified_eval_summary_zh.md",
            "v2_human_answer_report.json",
        ]
        for name in legacy_names:
            with self.subTest(name=name):
                self.assertFalse(os.path.exists(os.path.join(BASE_DIR, name)))

    def test_evaluators_write_to_reports_directory(self):
        expected = {
            "reply_diversity_eval": REPLY_DIVERSITY_REPORT_PATH,
            "runtime_dynamics_eval": RUNTIME_DYNAMICS_REPORT_PATH,
            "stress_eval_10000": STRESS_EVAL_REPORT_PATH,
            "eval_v2_human_answer": V2_HUMAN_ANSWER_REPORT_PATH,
            "eval_surface_microplanning_holdout": SURFACE_MICROPLANNING_REPORT_JSON_PATH,
            "eval_rightbrain_model_gate": RIGHTBRAIN_MODEL_GATE_REPORT_JSON_PATH,
        }
        for module_name, report_path in expected.items():
            with self.subTest(module_name=module_name):
                module = importlib.import_module(module_name)
                self.assertEqual(module.REPORT_PATH, report_path)
                self.assertTrue(report_path.startswith(os.path.join(BASE_DIR, "reports")))


if __name__ == "__main__":
    unittest.main()
