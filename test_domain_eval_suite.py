import os
import tempfile
import unittest

from run_domain_eval_suite import (
    FORMAL_BENCHMARK_REFRESH_ENV,
    TASKS,
    should_reuse_report_for_missing_runner,
    should_reuse_existing_report,
    task_run_succeeded,
)


class DomainEvalSuiteTest(unittest.TestCase):
    def test_surface_microplanning_is_part_of_domain_suite(self):
        self.assertIn("surface_microplanning", [task[0] for task in TASKS])

    def test_existing_formal_report_is_reused_by_default(self):
        with tempfile.NamedTemporaryFile() as report:
            self.assertTrue(should_reuse_existing_report("formal_benchmarks", report.name, {}))

    def test_refresh_flag_forces_formal_benchmark_execution(self):
        with tempfile.NamedTemporaryFile() as report:
            env = {FORMAL_BENCHMARK_REFRESH_ENV: "1"}
            self.assertFalse(should_reuse_existing_report("formal_benchmarks", report.name, env))

    def test_other_reports_are_always_executed(self):
        with tempfile.NamedTemporaryFile() as report:
            self.assertFalse(should_reuse_existing_report("runtime_dynamics", report.name, {}))

    def test_missing_formal_report_is_executed(self):
        missing_path = os.path.join(tempfile.gettempdir(), "uruha-missing-formal-report.json")
        if os.path.exists(missing_path):
            os.unlink(missing_path)
        self.assertFalse(should_reuse_existing_report("formal_benchmarks", missing_path, {}))

    def test_missing_runner_reuses_existing_report_explicitly(self):
        with tempfile.NamedTemporaryFile() as report:
            missing_runner = os.path.join(tempfile.gettempdir(), "uruha-missing-eval-runner.py")
            if os.path.exists(missing_runner):
                os.unlink(missing_runner)
            self.assertTrue(should_reuse_report_for_missing_runner(missing_runner, report.name))

    def test_missing_runner_without_report_cannot_be_reused(self):
        temp_dir = tempfile.gettempdir()
        self.assertFalse(
            should_reuse_report_for_missing_runner(
                os.path.join(temp_dir, "uruha-missing-runner.py"),
                os.path.join(temp_dir, "uruha-missing-report.json"),
            )
        )

    def test_reused_report_does_not_need_fake_process_returncode(self):
        self.assertTrue(
            task_run_succeeded(
                {
                    "returncode": None,
                    "execution_mode": "reused_existing_report",
                    "report_found": True,
                }
            )
        )

    def test_executed_task_must_have_zero_returncode_and_report(self):
        self.assertTrue(task_run_succeeded({"returncode": 0, "execution_mode": "executed", "report_found": True}))
        self.assertFalse(task_run_succeeded({"returncode": 2, "execution_mode": "executed", "report_found": True}))


if __name__ == "__main__":
    unittest.main()
