import hashlib
import inspect
import json
import tempfile
import unittest
from pathlib import Path

import chromadb

import analyze_profile_state_transition_v69 as analyzer
import run_profile_state_transition_v69 as runner
from uruha_memory_validity import resolve_memory_validity
from uruha_profile_memory import (
    compile_profile_memory_record,
    profile_predicate,
    read_profile_candidates,
)


ROOT = Path(__file__).resolve().parent


class ProfileStateTransitionV69HarnessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dataset = json.loads(runner.DATASET_PATH.read_text(encoding="utf-8"))
        cls.prereg = json.loads(runner.PREREG_PATH.read_text(encoding="utf-8"))
        cls.lock = json.loads(runner.LOCK_PATH.read_text(encoding="utf-8"))

    def test_name_updates_share_one_single_value_predicate(self):
        old = self._record("name", "Old", "old", "2026-01-01T00:00:00+09:00")
        new = self._record("name", "New", "new", "2026-01-02T00:00:00+09:00")
        self.assertEqual(old["metadata"]["predicate"], new["metadata"]["predicate"])
        result = resolve_memory_validity(
            self._candidates([old, new]),
            reference_time="2026-01-03T00:00:00+09:00",
        )
        self.assertEqual([row["memory_id"] for row in result["eligible_candidates"]], ["new"])
        self.assertEqual([row["memory_id"] for row in result["historical_candidates"]], ["old"])

    def test_preference_identity_tracks_item_not_sentiment(self):
        self.assertEqual(profile_predicate("like", "Coffee"), profile_predicate("dislike", "coffee"))
        self.assertNotEqual(profile_predicate("like", "Coffee"), profile_predicate("like", "Tea"))

    def test_legacy_and_typed_documents_ids_and_write_counts_match(self):
        records = [
            {"memory_id": "a", "fact_type": "like", "value": "coffee", "timestamp": "2026-01-01T00:00:00+09:00"},
            {"memory_id": "b", "fact_type": "dislike", "value": "coffee", "timestamp": "2026-01-02T00:00:00+09:00"},
        ]
        legacy = runner._compile_records(records, typed_state=False)
        typed = runner._compile_records(records, typed_state=True)
        self.assertEqual([row["memory_id"] for row in legacy], [row["memory_id"] for row in typed])
        self.assertEqual([row["document"] for row in legacy], [row["document"] for row in typed])
        self.assertEqual(len(legacy), len(typed))

    def test_temporary_chroma_preserves_typed_metadata_without_embedding_query(self):
        row = self._record("like", "coffee", "probe", "2026-01-01T00:00:00+09:00")
        with tempfile.TemporaryDirectory(prefix="uruha_v69_test_") as tempdir:
            collection = chromadb.PersistentClient(path=tempdir).get_or_create_collection("v69_probe")
            collection.add(ids=[row["memory_id"]], documents=[row["document"]], metadatas=[row["metadata"]])
            candidates = read_profile_candidates(collection)
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["memory_id"], "probe")
        self.assertEqual(candidates[0]["metadata"]["subject"], "user")
        self.assertEqual(candidates[0]["distance"], None)

    def test_runner_projects_cases_without_expected_and_avoids_production_database(self):
        source = inspect.getsource(runner)
        run_case_source = inspect.getsource(runner.run_case)
        self.assertNotIn("expected", run_case_source)
        self.assertNotIn("DB_PATH", source)
        self.assertIn("TemporaryDirectory", source)
        self.assertFalse(self.lock["formal_run"]["production_database_access_authorized"])

    def test_candidate_contains_no_case_ids_utterances_or_holdout_values(self):
        source = (ROOT / "uruha_profile_memory.py").read_text(encoding="utf-8").casefold()
        for case in self.dataset["cases"]:
            self.assertNotIn(case["id"].casefold(), source)
            for turn in case["turns"]:
                self.assertNotIn(turn["utterance"].casefold(), source)
            for value in runner._extract_records(case):
                self.assertNotIn(str(value["value"]).casefold(), source)

    def test_analyzer_accepts_exact_state_gain_without_regression(self):
        raw = self._synthetic_raw()
        report = analyzer.analyze_raw(raw, self.dataset, self.prereg, self.lock)
        self.assertTrue(report["run_integrity"]["passed"])
        self.assertTrue(report["success_gates"]["passed"], report["success_gates"]["checks"])
        self.assertEqual(report["pairwise"]["newly_exact_vs_matched_control"], 12)
        self.assertEqual(report["pairwise"]["regressions_vs_matched_control"], 0)

    def test_analyzer_rejects_one_stale_active_record(self):
        raw = self._synthetic_raw()
        row = next(
            row
            for row in raw["rows"]
            if row["condition"] == runner.CONDITIONS[2] and row["case_id"] == "v69_name_en"
        )
        row["active_ids"].append("name_en_old")
        row["historical_ids"].remove("name_en_old")
        report = analyzer.analyze_raw(raw, self.dataset, self.prereg, self.lock)
        self.assertFalse(report["success_gates"]["passed"])
        self.assertFalse(report["success_gates"]["checks"]["stale_active_record_count"])

    def test_harness_lock_binds_every_artifact_and_forbids_activation(self):
        for name, artifact in self.lock["frozen_artifacts"].items():
            self.assertEqual(
                hashlib.sha256((ROOT / artifact["path"]).read_bytes()).hexdigest(),
                artifact["sha256"],
                name,
            )
        self.assertTrue(self.lock["formal_run"]["temporary_chroma_access_authorized"])
        self.assertFalse(self.lock["formal_run"]["production_database_access_authorized"])
        self.assertFalse(self.lock["runtime_activation_authorized"])

    def _record(self, fact_type, value, memory_id, timestamp):
        return compile_profile_memory_record(
            fact_type,
            value,
            timestamp=timestamp,
            memory_id=memory_id,
            typed_state=True,
        )

    def _candidates(self, rows):
        return [
            {"memory_id": row["memory_id"], "text": row["document"], "metadata": row["metadata"]}
            for row in rows
        ]

    def _synthetic_raw(self):
        rows = []
        for case in self.dataset["cases"]:
            written = list(case["expected"]["written_turn_ids"])
            active = list(case["expected"]["active_turn_ids"])
            historical = list(case["expected"]["historical_turn_ids"])
            for condition in runner.CONDITIONS:
                if condition == runner.CONDITIONS[0]:
                    observed_active, observed_historical = [], []
                elif condition == runner.CONDITIONS[1]:
                    observed_active, observed_historical = list(written), []
                else:
                    observed_active, observed_historical = list(active), list(historical)
                rows.append(
                    {
                        "case_id": case["id"],
                        "scenario_family": case["scenario_family"],
                        "language": case["language"],
                        "condition": condition,
                        "persisted_ids": list(written),
                        "active_ids": observed_active,
                        "historical_ids": observed_historical,
                        "inapplicable_ids": [],
                        "state_seconds": 0.0001,
                        "temporary_chroma": True,
                    }
                )
        return {
            "row_count": 54,
            "case_count": 18,
            "gold_in_raw": False,
            "language_model_inference": False,
            "production_runtime_changed": False,
            "production_database_access": False,
            "temporary_chroma_access": True,
            "warmup_iterations_per_case": self.lock["formal_run"]["timing"]["warmup_iterations_per_case"],
            "scored_iterations_per_case": self.lock["formal_run"]["timing"]["scored_iterations_per_case"],
            "rows": rows,
        }


if __name__ == "__main__":
    unittest.main()
