#!/usr/bin/env python3
"""Test the frozen consolidation-admission cascade V1 harness."""

from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

import analyze_consolidation_admission_cascade_v1_development as analyzer
import run_consolidation_admission_cascade_v1_development as runner
from consolidation_admission_cascade_v1_core import (
    CANDIDATE,
    CONTROL,
    analyze_cascade,
    parse_write_gate_tool_response,
)


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = (
    ROOT
    / "configs"
    / "consolidation_admission_cascade_v1_development_preregistration.json"
)
LOCK_PATH = (
    ROOT
    / "configs"
    / "consolidation_admission_cascade_v1_harness_lock.json"
)
RESULT_LOCK_PATH = (
    ROOT
    / "configs"
    / "consolidation_admission_cascade_v1_result_lock.json"
)


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _stage1_row(case, decision, wall_seconds=1.0):
    return {
        "id": case["id"],
        "condition": CANDIDATE,
        "stage": "stage1",
        "admission_decision": decision,
        "parse_success": True,
        "parse_error": None,
        "payload": {"admission_decision": decision},
        "raw_content": "",
        "raw_tool_calls": [],
        "wall_seconds": wall_seconds,
        "transport_attempts": 1,
        "transport_error": None,
    }


def _final_row(case, stage, *, correct=True, wall_seconds=2.0):
    expected = case["expected_memory_kind"]
    if correct:
        observed = expected
        kind = expected
        basis = case["expected_persistence_basis"]
        evidence = case["required_evidence_user_turns"]
        applies_to = case["expected_applies_to"]
    else:
        observed = "none" if expected != "none" else "wisdom"
        kind = observed
        basis = (
            "no_long_term_basis"
            if observed == "none"
            else "stable_trait"
        )
        evidence = [] if observed == "none" else [1]
        applies_to = "none" if observed == "none" else "user_profile"
    return {
        "id": case["id"],
        "condition": CONTROL if stage == "control" else CANDIDATE,
        "stage": stage,
        "observed_target": observed,
        "parse_success": True,
        "index_contract_success": True,
        "parse_error": None,
        "memory_kind": kind,
        "persistence_basis": basis,
        "evidence_user_turns": evidence,
        "raw_applies_to": applies_to,
        "compiled_applies_to": applies_to,
        "payload": {},
        "raw_content": "",
        "raw_tool_calls": [],
        "wall_seconds": wall_seconds,
        "transport_attempts": 1,
        "transport_error": None,
    }


def _passing_rows(cases):
    control = []
    stage1 = []
    stage2 = []
    for index, case in enumerate(cases):
        control.append(
            _final_row(
                case,
                "control",
                correct=index != 0,
                wall_seconds=2.0,
            )
        )
        decision = (
            "write"
            if case["expected_memory_kind"] != "none"
            else "none"
        )
        stage1.append(_stage1_row(case, decision))
        if decision == "write":
            stage2.append(_final_row(case, "stage2", wall_seconds=2.0))
    return control, stage1, stage2


class ConsolidationAdmissionCascadeV1CoreTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = _load(CONFIG_PATH)
        cls.dataset = _load(ROOT / cls.config["dataset"]["path"])

    def test_stage1_parser_accepts_only_one_exact_tool_call(self):
        valid = {
            "message": {
                "content": "",
                "tool_calls": [
                    {
                        "function": {
                            "name": "decide_memory_write",
                            "arguments": {"admission_decision": "write"},
                        }
                    }
                ],
            }
        }
        parsed = parse_write_gate_tool_response(valid)
        self.assertTrue(parsed["parse_success"])
        self.assertEqual(parsed["admission_decision"], "write")

        invalid_responses = [
            {"message": {"content": "write", "tool_calls": []}},
            {"message": {"content": "", "tool_calls": []}},
            {
                "message": {
                    "content": "",
                    "tool_calls": [
                        {
                            "function": {
                                "name": "wrong",
                                "arguments": {
                                    "admission_decision": "write"
                                },
                            }
                        }
                    ],
                }
            },
            {
                "message": {
                    "content": "",
                    "tool_calls": [
                        {
                            "function": {
                                "name": "decide_memory_write",
                                "arguments": {
                                    "admission_decision": "write",
                                    "reason": "extra",
                                },
                            }
                        }
                    ],
                }
            },
        ]
        for response in invalid_responses:
            with self.subTest(response=response):
                parsed = parse_write_gate_tool_response(response)
                self.assertFalse(parsed["parse_success"])
                self.assertEqual(parsed["admission_decision"], "none")

    def test_scorer_passes_only_complete_predeclared_pattern(self):
        control, stage1, stage2 = _passing_rows(self.dataset["cases"])
        result = analyze_cascade(
            self.dataset["cases"],
            control,
            stage1,
            stage2,
            success_gates=self.config["success_gates"],
            run_invariants=self.config["run_invariants"],
            model_calls=32,
            transport_attempts=32,
        )
        self.assertTrue(result["all_gates_pass"])
        self.assertTrue(all(result["gate_checks"].values()))
        self.assertTrue(all(result["run_checks"].values()))
        self.assertEqual(result["control"]["correct_count"], 11)
        self.assertEqual(result["candidate"]["correct_count"], 12)
        self.assertEqual(result["stage2"]["call_count"], 8)
        self.assertEqual(result["paired_vs_control"]["newly_correct_count"], 1)
        self.assertEqual(result["paired_vs_control"]["regression_count"], 0)

    def test_closed_gate_never_requires_a_stage2_row(self):
        control, stage1, stage2 = _passing_rows(self.dataset["cases"])
        none_ids = {
            case["id"]
            for case in self.dataset["cases"]
            if case["expected_memory_kind"] == "none"
        }
        self.assertFalse(none_ids & {row["id"] for row in stage2})
        result = analyze_cascade(
            self.dataset["cases"],
            control,
            stage1,
            stage2,
            success_gates=self.config["success_gates"],
            run_invariants=self.config["run_invariants"],
            model_calls=32,
            transport_attempts=32,
        )
        by_id = {row["id"]: row for row in result["candidate"]["rows"]}
        self.assertTrue(
            all(
                by_id[case_id]["final_source"]
                == "stage1_compiled_none"
                for case_id in none_ids
            )
        )

    def test_stage2_row_after_closed_gate_is_rejected(self):
        control, stage1, stage2 = _passing_rows(self.dataset["cases"])
        none_case = next(
            case
            for case in self.dataset["cases"]
            if case["expected_memory_kind"] == "none"
        )
        stage2.append(_final_row(none_case, "stage2"))
        with self.assertRaisesRegex(ValueError, "compiled stage1 writes"):
            analyze_cascade(
                self.dataset["cases"],
                control,
                stage1,
                stage2,
                success_gates=self.config["success_gates"],
                run_invariants=self.config["run_invariants"],
                model_calls=33,
                transport_attempts=33,
            )


class ConsolidationAdmissionCascadeV1HarnessTest(unittest.TestCase):
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
            "model_screen_result_lock",
            "v3_preregistration",
            "v3_core",
            "runtime",
            "core",
            "runner",
            "analyzer",
            "harness_test",
        ):
            self.assertEqual(
                _sha256(ROOT / frozen[name]), frozen[f"{name}_sha256"]
            )

    def test_condition_order_is_balanced(self):
        first_counts = {CONTROL: 0, CANDIDATE: 0}
        for index, _case in enumerate(self.dataset["cases"]):
            order = runner.condition_order(self.config, index)
            self.assertEqual(set(order), {CONTROL, CANDIDATE})
            first_counts[order[0]] += 1
        self.assertEqual(first_counts, {CONTROL: 6, CANDIDATE: 6})

    def test_control_and_stage2_use_the_exact_same_final_request(self):
        case = self.dataset["cases"][0]
        control_body = runner.build_final_request_body(self.config, case)
        stage2_body = runner.build_final_request_body(self.config, case)
        self.assertEqual(control_body, stage2_body)
        serialized = json.dumps(control_body, ensure_ascii=False)
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

    def test_stage1_request_is_binary_and_contains_no_final_labels(self):
        case = self.dataset["cases"][0]
        body = runner.build_stage1_request_body(self.config, case)
        parameters = body["tools"][0]["function"]["parameters"]
        self.assertEqual(parameters["required"], ["admission_decision"])
        serialized = json.dumps(body, ensure_ascii=False)
        for forbidden in (
            "memory_kind",
            "persistence_basis",
            "evidence_user_turns",
            case["id"],
            case["gold_reason"],
        ):
            self.assertNotIn(forbidden, serialized)

    def test_transport_failure_is_recorded_once_without_retry(self):
        case = self.dataset["cases"][0]
        with mock.patch.object(
            runner,
            "_post_json",
            side_effect=urllib.error.URLError("offline"),
        ) as post:
            row = runner._call_stage1(self.config, case)
        self.assertEqual(post.call_count, 1)
        self.assertEqual(row["transport_attempts"], 1)
        self.assertFalse(row["parse_success"])
        self.assertEqual(row["admission_decision"], "none")
        self.assertIn("URLError", row["transport_error"])

    def test_resume_accepts_half_finished_write_but_rejects_ambiguity(self):
        case = self.dataset["cases"][0]
        report = {
            "control_rows": [],
            "stage1_rows": [_stage1_row(case, "write")],
            "stage2_rows": [],
            "model_calls": 1,
            "transport_attempts_made": 1,
            "gold_fields_passed_to_model": False,
            "runtime_memory_write_performed": False,
            "inflight": None,
            "gate_snapshot": None,
        }
        completed = runner._validate_report_progress(
            report, self.dataset
        )
        self.assertIn(case["id"], completed["stage1"])
        self.assertNotIn(case["id"], completed["stage2"])

        ambiguous = json.loads(json.dumps(report))
        ambiguous["inflight"] = {"id": case["id"], "stage": "stage2"}
        with self.assertRaisesRegex(ValueError, "ambiguous in-flight"):
            runner._validate_report_progress(ambiguous, self.dataset)

        invalid = json.loads(json.dumps(report))
        invalid["stage1_rows"][0]["admission_decision"] = "none"
        invalid["stage2_rows"] = [_final_row(case, "stage2")]
        invalid["model_calls"] = 2
        invalid["transport_attempts_made"] = 2
        with self.assertRaisesRegex(ValueError, "closed gate"):
            runner._validate_report_progress(invalid, self.dataset)

    def test_runner_skips_stage2_when_every_gate_closes(self):
        snapshots = {
            key: {
                "ollama_tag": self.config["models"][key]["ollama_tag"],
                "digest": self.config["models"][key]["digest"],
            }
            for key in runner.MODEL_KEYS
        }

        def closed_stage1(config, case):
            return _stage1_row(case, "none")

        def control_only(config, case, stage):
            self.assertEqual(stage, "control")
            return _final_row(case, "control")

        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "raw.json"
            with (
                mock.patch.object(runner, "verify"),
                mock.patch.object(
                    runner, "_model_snapshots", return_value=snapshots
                ),
                mock.patch.object(
                    runner, "_ollama_version", return_value="0.31.1"
                ),
                mock.patch.object(
                    runner,
                    "git_value",
                    side_effect=lambda *args: (
                        "main" if args[0] == "branch" else "test-commit"
                    ),
                ),
                mock.patch.object(
                    runner, "_call_stage1", side_effect=closed_stage1
                ) as stage1_call,
                mock.patch.object(
                    runner, "_call_final", side_effect=control_only
                ) as final_call,
            ):
                report = runner.run(output)
        self.assertEqual(stage1_call.call_count, 12)
        self.assertEqual(final_call.call_count, 12)
        self.assertEqual(report["stage2_rows"], [])
        self.assertEqual(report["model_calls"], 24)

    def test_analyzer_independently_recomputes_complete_result(self):
        control, stage1, stage2 = _passing_rows(self.dataset["cases"])
        snapshot = analyze_cascade(
            self.dataset["cases"],
            control,
            stage1,
            stage2,
            success_gates=self.config["success_gates"],
            run_invariants=self.config["run_invariants"],
            model_calls=32,
            transport_attempts=32,
        )
        model_snapshots = {
            key: {
                "ollama_tag": self.config["models"][key]["ollama_tag"],
                "digest": self.config["models"][key]["digest"],
            }
            for key in runner.MODEL_KEYS
        }
        raw = {
            "experiment_id": self.config["experiment_id"],
            "completed_at": "2026-07-18T00:00:00+09:00",
            "preregistration_sha256": _sha256(CONFIG_PATH),
            "harness_lock_sha256": _sha256(LOCK_PATH),
            "dataset_sha256": _sha256(
                ROOT / self.config["dataset"]["path"]
            ),
            "model_screen_result_lock_sha256": _sha256(
                ROOT
                / "configs"
                / "consolidation_admission_model_screen_v1_result_lock.json"
            ),
            "gold_fields_passed_to_model": False,
            "runtime_memory_write_performed": False,
            "inflight": None,
            "model_snapshots": model_snapshots,
            "model_calls": 32,
            "transport_attempts_made": 32,
            "control_rows": control,
            "stage1_rows": stage1,
            "stage2_rows": stage2,
            "gate_snapshot": snapshot,
        }
        with tempfile.TemporaryDirectory() as temporary:
            raw_path = Path(temporary) / "raw.json"
            raw_path.write_text(
                json.dumps(raw, ensure_ascii=False), encoding="utf-8"
            )
            analysis = analyzer.analyze(raw_path)
        self.assertTrue(analysis["cascade_result"]["all_gates_pass"])
        self.assertTrue(analysis["runtime_adapter_development_authorized"])
        self.assertFalse(analysis["runtime_shadow_authorized"])

    def test_runner_cannot_write_or_import_runtime_memory(self):
        source = Path(runner.__file__).read_text(encoding="utf-8")
        for forbidden in (
            "wisdom_col.add",
            "procedural_col.add",
            "episode_col.add",
            "MemoryManager(",
            "consolidate_recent_experiences(",
        ):
            self.assertNotIn(forbidden, source)

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
