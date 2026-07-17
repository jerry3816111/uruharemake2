#!/usr/bin/env python3
"""Test the frozen consolidation-admission model screen V1 harness."""

from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

import analyze_consolidation_admission_model_screen_v1_development as analyzer
import run_consolidation_admission_model_screen_v1_development as runner
from consolidation_admission_model_screen_v1_core import (
    CANDIDATES,
    CONDITIONS,
    CONTROL,
    analyze_model_screen,
)


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = (
    ROOT
    / "configs"
    / "consolidation_admission_model_screen_v1_development_preregistration.json"
)
LOCK_PATH = (
    ROOT
    / "configs"
    / "consolidation_admission_model_screen_v1_harness_lock.json"
)
RESULT_LOCK_PATH = (
    ROOT
    / "configs"
    / "consolidation_admission_model_screen_v1_result_lock.json"
)


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _row(case, condition, *, correct, wall_seconds):
    expected = case["expected_memory_kind"]
    if correct:
        observed = expected
        memory_kind = expected
        basis = case["expected_persistence_basis"]
        evidence = case["required_evidence_user_turns"]
        applies_to = case["expected_applies_to"]
    else:
        observed = "wisdom" if expected == "none" else "none"
        memory_kind = observed
        basis = (
            "stable_trait"
            if observed == "wisdom"
            else "no_long_term_basis"
        )
        evidence = [1] if observed == "wisdom" else []
        applies_to = "user_profile" if observed == "wisdom" else "none"
    return {
        "id": case["id"],
        "condition": condition,
        "observed_target": observed,
        "parse_success": True,
        "index_contract_success": True,
        "parse_error": None,
        "memory_kind": memory_kind,
        "persistence_basis": basis,
        "evidence_user_turns": evidence,
        "compiled_applies_to": applies_to,
        "wall_seconds": wall_seconds,
        "transport_attempts": 1,
        "transport_error": None,
    }


class ConsolidationAdmissionModelScreenV1CoreTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = _load(CONFIG_PATH)
        cls.dataset = _load(ROOT / cls.config["dataset"]["path"])

    def _passing_rows(self):
        rows = {condition: [] for condition in CONDITIONS}
        for case in self.dataset["cases"]:
            rows[CONTROL].append(
                _row(case, CONTROL, correct=False, wall_seconds=1.0)
            )
            rows[CANDIDATES[0]].append(
                _row(
                    case,
                    CANDIDATES[0],
                    correct=True,
                    wall_seconds=1.5,
                )
            )
            rows[CANDIDATES[1]].append(
                _row(
                    case,
                    CANDIDATES[1],
                    correct=True,
                    wall_seconds=3.5,
                )
            )
        return rows

    def test_scorer_applies_all_gates_and_selects_efficient_tie(self):
        result = analyze_model_screen(
            self.dataset["cases"],
            self._passing_rows(),
            models=self.config["models"],
            eligibility_gates=self.config["eligibility_gates"],
            latency_gates=self.config["latency_gates"],
            run_invariants=self.config["run_invariants"],
            model_calls=36,
            transport_attempts=36,
        )
        self.assertTrue(all(result["run_checks"].values()))
        self.assertEqual(
            set(result["candidates"]), set(CANDIDATES)
        )
        for condition in CANDIDATES:
            candidate = result["candidates"][condition]
            self.assertTrue(candidate["eligible"])
            self.assertTrue(all(candidate["gate_checks"].values()))
            self.assertEqual(
                set(candidate["gate_checks"]),
                {
                    "candidate_correct_count_min",
                    "candidate_accuracy_min",
                    "candidate_wisdom_correct_min",
                    "candidate_procedural_correct_min",
                    "candidate_none_correct_min",
                    "candidate_semantic_frame_exact_count_min",
                    "candidate_evidence_grounded_count_min",
                    "candidate_positive_evidence_grounded_count_min",
                    "newly_correct_vs_control_min",
                    "regression_vs_control_max",
                    "net_correct_gain_vs_control_min",
                    "candidate_false_long_term_write_count_max",
                    "candidate_missed_long_term_write_count_max",
                    "candidate_tool_parse_success_count",
                    "candidate_index_contract_success_count",
                    "candidate_median_wall_seconds_max",
                    "candidate_warm_p95_wall_seconds_max",
                },
            )
        self.assertEqual(
            result["selected_model_condition"], "qwen35_4b_candidate"
        )

    def test_run_invariant_failure_prevents_selection(self):
        result = analyze_model_screen(
            self.dataset["cases"],
            self._passing_rows(),
            models=self.config["models"],
            eligibility_gates=self.config["eligibility_gates"],
            latency_gates=self.config["latency_gates"],
            run_invariants=self.config["run_invariants"],
            model_calls=36,
            transport_attempts=37,
        )
        self.assertIsNone(result["selected_model_condition"])
        self.assertFalse(
            result["run_checks"]["transport_attempt_count_exact"]
        )

    def test_duplicate_or_missing_rows_are_rejected(self):
        rows = self._passing_rows()
        rows[CANDIDATES[0]].pop()
        with self.assertRaisesRegex(ValueError, "exactly match"):
            analyze_model_screen(
                self.dataset["cases"],
                rows,
                models=self.config["models"],
                eligibility_gates=self.config["eligibility_gates"],
                latency_gates=self.config["latency_gates"],
                run_invariants=self.config["run_invariants"],
                model_calls=35,
                transport_attempts=35,
            )


class ConsolidationAdmissionModelScreenV1HarnessTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = _load(CONFIG_PATH)
        cls.lock = _load(LOCK_PATH)
        cls.dataset = _load(ROOT / cls.config["dataset"]["path"])

    def test_lock_hashes_every_frozen_artifact(self):
        frozen = self.lock["frozen_artifacts"]
        for name in (
            "preregistration",
            "dataset",
            "preregistration_test",
            "v3_preregistration",
            "v3_result_lock",
            "v3_core",
            "v46_analysis",
            "core",
            "runner",
            "analyzer",
            "harness_test",
        ):
            self.assertEqual(
                _sha256(ROOT / frozen[name]), frozen[f"{name}_sha256"]
            )

    def test_condition_order_is_a_balanced_latin_square(self):
        first_counts = {condition: 0 for condition in CONDITIONS}
        for index, _case in enumerate(self.dataset["cases"]):
            order = runner.condition_order(self.config, index)
            self.assertEqual(set(order), set(CONDITIONS))
            first_counts[order[0]] += 1
        self.assertEqual(
            first_counts, {condition: 4 for condition in CONDITIONS}
        )

    def test_request_payload_differs_only_by_frozen_model(self):
        case = self.dataset["cases"][0]
        bodies = {
            condition: runner.build_request_body(
                self.config, case, condition
            )
            for condition in CONDITIONS
        }
        normalized = []
        for condition, body in bodies.items():
            self.assertEqual(
                body["model"],
                self.config["models"][condition]["ollama_tag"],
            )
            serialized = json.dumps(body, ensure_ascii=False)
            self.assertIn(case["session"][0]["user"], serialized)
            self.assertIn("User[U1]", serialized)
            for forbidden in (
                case["id"],
                case["gold_reason"],
                "expected_memory_kind",
                "expected_persistence_basis",
                "expected_applies_to",
                "required_evidence_user_turns",
                "allowed_evidence_user_turns",
            ):
                self.assertNotIn(forbidden, serialized)
            self.assertEqual(
                body["tools"],
                [self.config["fixed_v3_contract"]["tool_contract"]],
            )
            copy = dict(body)
            copy.pop("model")
            normalized.append(copy)
        self.assertTrue(
            all(body == normalized[0] for body in normalized[1:])
        )

    def test_transport_failure_is_recorded_once_without_retry(self):
        case = self.dataset["cases"][0]
        with mock.patch.object(
            runner,
            "_post_json",
            side_effect=urllib.error.URLError("offline"),
        ) as post:
            row = runner._call_condition(
                self.config, case, CANDIDATES[0]
            )
        self.assertEqual(post.call_count, 1)
        self.assertEqual(row["transport_attempts"], 1)
        self.assertFalse(row["parse_success"])
        self.assertEqual(row["observed_target"], "none")
        self.assertIn("URLError", row["transport_error"])

    def test_resume_progress_is_validated_before_more_calls(self):
        report = {
            "rows_by_condition": {condition: [] for condition in CONDITIONS},
            "model_calls": 0,
            "transport_attempts_made": 0,
            "gold_fields_passed_to_model": False,
            "runtime_memory_write_performed": False,
            "inflight": None,
            "gate_snapshot": None,
        }
        self.assertEqual(
            runner._validate_report_progress(report, self.dataset), set()
        )
        corrupted = json.loads(json.dumps(report))
        corrupted["rows_by_condition"][CONTROL].append(
            {
                "id": self.dataset["cases"][0]["id"],
                "condition": CANDIDATES[0],
                "transport_attempts": 1,
            }
        )
        corrupted["model_calls"] = 1
        corrupted["transport_attempts_made"] = 1
        with self.assertRaisesRegex(ValueError, "condition drift"):
            runner._validate_report_progress(corrupted, self.dataset)
        ambiguous = json.loads(json.dumps(report))
        ambiguous["inflight"] = {
            "id": self.dataset["cases"][0]["id"],
            "condition": CONTROL,
        }
        with self.assertRaisesRegex(ValueError, "ambiguous in-flight"):
            runner._validate_report_progress(ambiguous, self.dataset)

    def test_runner_cannot_write_runtime_memory(self):
        source = Path(runner.__file__).read_text(encoding="utf-8")
        for forbidden in (
            "wisdom_col.add",
            "procedural_col.add",
            "episode_col.add",
            "MemoryManager(",
            "consolidate_recent_experiences(",
        ):
            self.assertNotIn(forbidden, source)

    def test_analyzer_independently_recomputes_complete_raw_result(self):
        rows = {condition: [] for condition in CONDITIONS}
        for case in self.dataset["cases"]:
            rows[CONTROL].append(
                _row(case, CONTROL, correct=False, wall_seconds=1.0)
            )
            rows[CANDIDATES[0]].append(
                _row(
                    case,
                    CANDIDATES[0],
                    correct=True,
                    wall_seconds=1.5,
                )
            )
            rows[CANDIDATES[1]].append(
                _row(
                    case,
                    CANDIDATES[1],
                    correct=True,
                    wall_seconds=3.5,
                )
            )
        gate_snapshot = analyze_model_screen(
            self.dataset["cases"],
            rows,
            models=self.config["models"],
            eligibility_gates=self.config["eligibility_gates"],
            latency_gates=self.config["latency_gates"],
            run_invariants=self.config["run_invariants"],
            model_calls=36,
            transport_attempts=36,
        )
        snapshots = {
            condition: {
                "ollama_tag": self.config["models"][condition]["ollama_tag"],
                "digest": self.config["models"][condition]["digest"],
            }
            for condition in CONDITIONS
        }
        raw = {
            "experiment_id": self.config["experiment_id"],
            "completed_at": "2026-07-17T00:00:00+09:00",
            "preregistration_sha256": _sha256(CONFIG_PATH),
            "harness_lock_sha256": _sha256(LOCK_PATH),
            "dataset_sha256": _sha256(
                ROOT / self.config["dataset"]["path"]
            ),
            "v3_result_lock_sha256": _sha256(
                ROOT
                / "configs"
                / "consolidation_admission_v3_role_separated_result_lock.json"
            ),
            "gold_fields_passed_to_model": False,
            "runtime_memory_write_performed": False,
            "inflight": None,
            "model_snapshots": snapshots,
            "model_calls": 36,
            "transport_attempts_made": 36,
            "rows_by_condition": rows,
            "gate_snapshot": gate_snapshot,
        }
        with tempfile.TemporaryDirectory() as temporary:
            raw_path = Path(temporary) / "raw.json"
            raw_path.write_text(
                json.dumps(raw, ensure_ascii=False), encoding="utf-8"
            )
            analysis = analyzer.analyze(raw_path)
        self.assertEqual(
            analysis["selected_model_condition"],
            "qwen35_4b_candidate",
        )
        self.assertTrue(analysis["fresh_integration_pilot_authorized"])
        self.assertFalse(analysis["runtime_shadow_authorized"])

    def test_result_artifacts_were_absent_in_frozen_harness_commit(self):
        result_paths = self.lock["result_artifacts"]
        if RESULT_LOCK_PATH.exists():
            result_lock = _load(RESULT_LOCK_PATH)
            harness_commit = result_lock["harness_merge_commit"]
            for path in result_paths:
                completed = subprocess.run(
                    ["git", "cat-file", "-e", f"{harness_commit}:{path}"],
                    cwd=ROOT,
                    capture_output=True,
                    check=False,
                )
                self.assertNotEqual(completed.returncode, 0)
        else:
            for path in result_paths:
                self.assertFalse((ROOT / path).exists())

    def test_harness_does_not_authorize_runtime_or_broad_claims(self):
        for value in self.config["evidence_limits"].values():
            self.assertFalse(value)
        self.assertFalse(
            self.lock["model_inference_before_harness_merge_authorized"]
        )


if __name__ == "__main__":
    unittest.main()
