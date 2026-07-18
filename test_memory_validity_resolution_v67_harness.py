import hashlib
import inspect
import json
import unittest
from pathlib import Path

import analyze_memory_validity_resolution_v67 as analyzer
import run_memory_validity_resolution_v67 as runner
from uruha_memory_validity import resolve_memory_validity


ROOT = Path(__file__).resolve().parent


def candidate(memory_id, metadata=None):
    return {
        "memory_id": memory_id,
        "source": "test",
        "text": f"synthetic memory {memory_id}",
        "distance": 0.1,
        "metadata": metadata or {},
    }


class MemoryValidityResolutionV67HarnessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dataset = json.loads(runner.DATASET_PATH.read_text(encoding="utf-8"))
        cls.prereg = json.loads(runner.PREREG_PATH.read_text(encoding="utf-8"))
        cls.lock = json.loads(runner.LOCK_PATH.read_text(encoding="utf-8"))

    def test_legacy_and_invalid_metadata_fail_open(self):
        rows = [
            candidate("legacy"),
            candidate("invalid", {"valid_until": "not-a-time"}),
        ]
        result = resolve_memory_validity(rows, reference_time="2026-07-18T12:00:00+09:00")
        self.assertEqual([row["memory_id"] for row in result["eligible_candidates"]], ["legacy", "invalid"])
        self.assertEqual(result["decisions"]["legacy"]["reason"], "legacy_metadata_fail_open")
        self.assertEqual(result["decisions"]["invalid"]["reason"], "invalid_contract_fail_open")

    def test_temporal_context_retraction_and_cardinality_are_generic(self):
        base = {"subject": "entity", "predicate": "attribute", "valid_from": "2026-01-01T00:00:00+09:00"}
        rows = [
            candidate("older", {**base, "fact_cardinality": "single"}),
            candidate("newer", {**base, "fact_cardinality": "single", "valid_from": "2026-07-01T00:00:00+09:00"}),
            candidate("expired", {**base, "fact_cardinality": "multi", "valid_until": "2026-06-01T00:00:00+09:00"}),
            candidate("conditional", {**base, "fact_cardinality": "multi", "condition_tags": ["work"]}),
            candidate("multi", {**base, "fact_cardinality": "multi"}),
        ]
        result = resolve_memory_validity(rows, reference_time="2026-07-18T12:00:00+09:00", condition_tags=["casual"])
        self.assertEqual({row["memory_id"] for row in result["eligible_candidates"]}, {"newer", "multi"})
        self.assertEqual({row["memory_id"] for row in result["historical_candidates"]}, {"older", "expired"})
        self.assertEqual({row["memory_id"] for row in result["inapplicable_candidates"]}, {"conditional"})

    def test_retraction_preserves_history_and_removes_target_from_working_set(self):
        old = candidate("old", {"subject": "entity", "predicate": "status", "fact_cardinality": "single", "valid_from": "2026-01-01T00:00:00+09:00"})
        retract = candidate("retract", {"subject": "entity", "predicate": "status", "fact_cardinality": "single", "memory_state": "retracted", "valid_from": "2026-07-01T00:00:00+09:00", "supersedes_ids": ["old"]})
        result = resolve_memory_validity([old, retract], reference_time="2026-07-18T12:00:00+09:00")
        self.assertFalse(result["eligible_candidates"])
        self.assertEqual({row["memory_id"] for row in result["historical_candidates"]}, {"old", "retract"})
        self.assertEqual(result["decisions"]["old"]["reason"], "explicitly_superseded")

    def test_runner_never_passes_expected_values_to_candidate(self):
        source = inspect.getsource(runner.run_case)
        self.assertNotIn("expected", source)
        case = self.dataset["cases"][0]
        row = runner.run_case(case, runner.CONDITIONS[1])
        encoded = json.dumps(row, ensure_ascii=False)
        self.assertNotIn('"expected"', encoded)
        self.assertNotIn(case["query_context"]["query_text"], encoded)

    def test_candidate_contains_no_case_ids_text_or_dataset_predicates(self):
        source = (ROOT / "uruha_memory_validity.py").read_text(encoding="utf-8").casefold()
        for case in self.dataset["cases"]:
            self.assertNotIn(case["id"].casefold(), source)
            self.assertNotIn(case["query_context"]["query_text"].casefold(), source)
            for row in case["candidates"]:
                predicate = row["metadata"].get("predicate")
                if predicate:
                    self.assertNotIn(predicate.casefold(), source)

    def test_analyzer_accepts_only_preregistered_large_clean_gain(self):
        raw = self._synthetic_raw(treatment_exact=True)
        report = analyzer.analyze_raw(raw, self.dataset, self.prereg, self.lock)
        self.assertTrue(report["run_integrity"]["passed"])
        self.assertTrue(report["success_gates"]["passed"], report["success_gates"]["checks"])
        self.assertEqual(report["pairwise"]["newly_exact_working_memory_vs_control"], 11)
        self.assertEqual(report["pairwise"]["regressions_vs_control"], 0)

    def test_analyzer_rejects_over_suppression(self):
        raw = self._synthetic_raw(treatment_exact=True)
        target = next(row for row in raw["rows"] if row["condition"] == runner.CONDITIONS[1] and row["case_id"] == "v67_multi_fruit")
        target["eligible_ids"] = ["fruit_apple_active"]
        target["working_memory_ids"] = ["fruit_apple_active"]
        target["historical_ids"] = ["fruit_banana_active"]
        report = analyzer.analyze_raw(raw, self.dataset, self.prereg, self.lock)
        self.assertFalse(report["success_gates"]["passed"])
        self.assertFalse(report["success_gates"]["checks"]["over_suppression_count"])
        self.assertFalse(report["success_gates"]["checks"]["multi_value_exact_count"])

    def test_harness_lock_binds_artifacts_and_forbids_runtime_change(self):
        for name, artifact in self.lock["frozen_artifacts"].items():
            self.assertEqual(hashlib.sha256((ROOT / artifact["path"]).read_bytes()).hexdigest(), artifact["sha256"], name)
        self.assertTrue(self.lock["formal_run"]["pilot_execution_authorized"])
        self.assertFalse(self.lock["runtime_change_authorized"])

    def _synthetic_raw(self, *, treatment_exact):
        rows = []
        for case in self.dataset["cases"]:
            expected = case["expected"]
            for condition in runner.CONDITIONS:
                if condition == runner.CONDITIONS[1] and treatment_exact:
                    eligible = list(expected["eligible_ids"])
                    historical = list(expected["historical_ids"])
                    inapplicable = list(expected["inapplicable_ids"])
                    working = list(expected["working_memory_ids"])
                else:
                    eligible = [row["memory_id"] for row in case["candidates"]]
                    historical = []
                    inapplicable = []
                    working = eligible[: case["working_memory_limit"]]
                rows.append({
                    "case_id": case["id"],
                    "scenario_family": case["scenario_family"],
                    "condition": condition,
                    "eligible_ids": eligible,
                    "historical_ids": historical,
                    "inapplicable_ids": inapplicable,
                    "working_memory_ids": working,
                    "decisions": {},
                    "resolver_seconds": 0.0001 if condition == runner.CONDITIONS[1] else 0.0,
                })
        return {
            "row_count": 36,
            "case_count": 18,
            "gold_in_raw": False,
            "language_model_inference": False,
            "production_runtime_changed": False,
            "production_memory_read_or_write": False,
            "warmup_iterations_per_case": self.lock["formal_run"]["timing"]["warmup_iterations_per_case"],
            "scored_iterations_per_case": self.lock["formal_run"]["timing"]["scored_iterations_per_case"],
            "rows": rows,
        }


if __name__ == "__main__":
    unittest.main()
