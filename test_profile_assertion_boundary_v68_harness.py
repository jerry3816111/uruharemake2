import hashlib
import json
import unittest
from pathlib import Path

import analyze_profile_assertion_boundary_v68 as analyzer
import run_profile_assertion_boundary_v68 as runner
from uruha_profile_assertion import filter_profile_facts_by_assertion_scope


ROOT = Path(__file__).resolve().parent


class ProfileAssertionBoundaryV68HarnessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dataset = json.loads(runner.DATASET_PATH.read_text(encoding="utf-8"))
        cls.prereg = json.loads(runner.PREREG_PATH.read_text(encoding="utf-8"))
        cls.lock = json.loads(runner.LOCK_PATH.read_text(encoding="utf-8"))

    def test_guard_preserves_direct_multilingual_assertions(self):
        probes = [
            ("I like board games.", [("like", "board games")]),
            ("我喜歡看星星。", [("like", "看星星")]),
            ("海が好き。", [("like", "海")]),
            ("Call me Ren.", [("name", "Ren")]),
        ]
        for utterance, facts in probes:
            self.assertEqual(filter_profile_facts_by_assertion_scope(utterance, facts), facts)

    def test_guard_rejects_questions_reports_quotes_and_third_person(self):
        probes = [
            "Do I like board games?",
            "A friend said I like board games.",
            "'I like board games.'",
            "友達は海が好き。",
        ]
        for utterance in probes:
            self.assertEqual(filter_profile_facts_by_assertion_scope(utterance, [("like", "probe")]), [])

    def test_runner_uses_same_extractor_and_never_reads_expected(self):
        source = Path(runner.__file__).read_text(encoding="utf-8")
        self.assertIn("EXTRACTOR._extract_profile_facts", source)
        run_case_source = source[source.index("def run_case"):source.index("def benchmark_guard")]
        self.assertNotIn("expected", run_case_source)

    def test_candidate_contains_no_case_ids_or_complete_holdout_utterances(self):
        source = (ROOT / "uruha_profile_assertion.py").read_text(encoding="utf-8").casefold()
        for case in self.dataset["cases"]:
            self.assertNotIn(case["id"].casefold(), source)
            self.assertNotIn(case["utterance"].casefold(), source)

    def test_analyzer_accepts_only_large_gain_without_regression(self):
        report = analyzer.analyze_raw(self._synthetic_raw(exact_treatment=True), self.dataset, self.prereg, self.lock)
        self.assertTrue(report["run_integrity"]["passed"])
        self.assertTrue(report["success_gates"]["passed"], report["success_gates"]["checks"])
        self.assertEqual(report["pairwise"]["newly_exact_vs_control"], 12)
        self.assertEqual(report["pairwise"]["regressions_vs_control"], 0)

    def test_analyzer_rejects_lost_direct_assertion(self):
        raw = self._synthetic_raw(exact_treatment=True)
        target = next(row for row in raw["rows"] if row["condition"] == runner.CONDITIONS[1] and row["case_id"] == "v68_direct_en_astronomy")
        target["observed_facts"] = []
        report = analyzer.analyze_raw(raw, self.dataset, self.prereg, self.lock)
        self.assertFalse(report["success_gates"]["passed"])
        self.assertFalse(report["success_gates"]["checks"]["direct_assertion_exact_count"])
        self.assertFalse(report["success_gates"]["checks"]["regressions_vs_control"])

    def test_harness_lock_binds_artifacts_and_forbids_persistence(self):
        for name, artifact in self.lock["frozen_artifacts"].items():
            self.assertEqual(hashlib.sha256((ROOT / artifact["path"]).read_bytes()).hexdigest(), artifact["sha256"], name)
        self.assertTrue(self.lock["formal_run"]["pilot_execution_authorized"])
        self.assertFalse(self.lock["persistent_memory_access_authorized"])

    def _synthetic_raw(self, *, exact_treatment):
        rows = []
        for case in self.dataset["cases"]:
            for condition in runner.CONDITIONS:
                if condition == runner.CONDITIONS[1] and exact_treatment:
                    facts = list(case["expected_facts"])
                elif case["expected_facts"]:
                    facts = list(case["expected_facts"])
                else:
                    facts = [{"fact_type": "like", "value": "false fact"}]
                rows.append({
                    "case_id": case["id"],
                    "scenario_family": case["scenario_family"],
                    "language": case["language"],
                    "condition": condition,
                    "observed_facts": facts,
                    "scope_decision": {},
                    "guard_seconds": 0.0001 if condition == runner.CONDITIONS[1] else 0.0,
                })
        return {
            "row_count": 48,
            "case_count": 24,
            "gold_in_raw": False,
            "language_model_inference": False,
            "production_runtime_changed": False,
            "persistent_memory_read_or_write": False,
            "warmup_iterations_per_case": self.lock["formal_run"]["timing"]["warmup_iterations_per_case"],
            "scored_iterations_per_case": self.lock["formal_run"]["timing"]["scored_iterations_per_case"],
            "rows": rows,
        }


if __name__ == "__main__":
    unittest.main()
