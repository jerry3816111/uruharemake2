import json
import tempfile
import unittest
from pathlib import Path

import analyze_planner_outcome_evaluator_v83 as analyzer
import planner_outcome_evaluator_v83 as v83
import run_planner_outcome_evaluator_v83 as runner


ROOT = Path(__file__).resolve().parent
CONTRACT_PATH = ROOT / "configs/planner_outcome_evaluator_v83_contract.json"
DATASET_PATH = ROOT / "datasets/planner_outcome_evaluator_v83_calibration.json"


class PlannerOutcomeEvaluatorV83Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
        cls.dataset = json.loads(DATASET_PATH.read_text(encoding="utf-8"))

    def test_frozen_artifact_hashes_match(self):
        artifacts = self.contract["artifacts"]
        self.assertEqual(v83.file_sha256(DATASET_PATH), artifacts["dataset_sha256"])
        self.assertEqual(v83.file_sha256(ROOT / artifacts["evaluator"]), artifacts["evaluator_sha256"])

    def test_calibration_is_project_authored_and_has_no_benchmark_answers(self):
        self.assertEqual(self.dataset["source_type"], "project_authored_controlled_calibration")
        self.assertFalse(self.dataset["official_benchmark_items"])
        self.assertFalse(self.dataset["benchmark_answers_present"])

    def test_every_valid_outcome_passes(self):
        for case in self.dataset["cases"]:
            with self.subTest(case=case["id"]):
                self.assertEqual(v83.evaluate_outcome(case, case["valid_outcome"])["failure_codes"], [])

    def test_each_mutation_triggers_only_its_preregistered_failure(self):
        for case in self.dataset["cases"]:
            for mutation in case["mutations"]:
                with self.subTest(case=case["id"], mutation=mutation["id"]):
                    result = v83.evaluate_outcome(case, mutation["outcome"])
                    self.assertEqual(result["failure_codes"], [mutation["target_failure_code"]])

    def test_evaluator_is_deterministic(self):
        first = v83.evaluate_calibration(self.dataset)
        second = v83.evaluate_calibration(self.dataset)
        self.assertEqual(first, second)

    def test_all_failure_families_have_calibration_coverage(self):
        covered = {
            mutation["target_failure_code"]
            for case in self.dataset["cases"]
            for mutation in case["mutations"]
        }
        expected = {
            "required_semantic_missing",
            "forbidden_semantic_present",
            "private_memory_intrusion",
            "cjk_language_leak",
            "foreign_script_leak",
            "unexpected_ascii_leak",
            "unicode_replacement_character",
            "over_max_chars",
            "required_action_missing",
            "unexpected_action",
            "forbidden_action_present",
            "malformed_action",
        }
        self.assertEqual(covered, expected)

    def test_runner_and_analyzer_pass_all_gates(self):
        with tempfile.TemporaryDirectory() as directory:
            raw_path = Path(directory) / "raw.json"
            json_path = Path(directory) / "analysis.json"
            md_path = Path(directory) / "analysis.md"
            raw = runner.run_calibration(CONTRACT_PATH, raw_path, root=ROOT)
            report = analyzer.write_report(CONTRACT_PATH, raw_path, json_path, md_path)
        self.assertTrue(raw["deterministic_rerun_match"])
        self.assertTrue(report["calibration_passed"])
        self.assertEqual(
            report["decision"],
            "authorize_evaluator_for_bounded_causal_planner_pilot_only",
        )
        self.assertTrue(all(report["gate_checks"].values()))

    def test_analyzer_rejects_tampered_raw_rows(self):
        with tempfile.TemporaryDirectory() as directory:
            raw_path = Path(directory) / "raw.json"
            json_path = Path(directory) / "analysis.json"
            md_path = Path(directory) / "analysis.md"
            raw = runner.run_calibration(CONTRACT_PATH, raw_path, root=ROOT)
            raw["rows"][0]["result"]["passed"] = False
            raw_path.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")
            report = analyzer.write_report(CONTRACT_PATH, raw_path, json_path, md_path)
        self.assertFalse(report["calibration_passed"])
        self.assertFalse(report["gate_checks"]["raw_rows_match_frozen_recalculation"])

    def test_no_runtime_or_training_authorization(self):
        self.assertFalse(self.contract["authorization"]["training_data"])
        self.assertFalse(self.contract["authorization"]["production_runtime_change"])


if __name__ == "__main__":
    unittest.main()
