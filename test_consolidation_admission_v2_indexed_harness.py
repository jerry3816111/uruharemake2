#!/usr/bin/env python3
"""Test the frozen indexed consolidation V2 harness without inference."""

from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

import analyze_consolidation_admission_v2_indexed_development as analyzer
import run_consolidation_admission_v2_indexed_development as runner
from consolidation_admission_v2_indexed_core import (
    analyze_indexed_conditions,
    compile_indexed_frame,
    parse_indexed_tool_response,
    parse_v1_control_response,
)


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = (
    ROOT
    / "configs"
    / "consolidation_admission_v2_indexed_development_preregistration.json"
)
CORRECTION_PATH = (
    ROOT / "configs" / "consolidation_admission_v2_indexed_protocol_correction.json"
)
LOCK_PATH = (
    ROOT / "configs" / "consolidation_admission_v2_indexed_harness_lock.json"
)
V1_CONFIG_PATH = (
    ROOT / "configs" / "consolidation_admission_v1_development_preregistration.json"
)
RESULT_LOCK_PATH = (
    ROOT / "configs" / "consolidation_admission_v2_indexed_result_lock.json"
)


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _tool_response(arguments, *, name="classify_memory_admission", content=""):
    return {
        "message": {
            "content": content,
            "tool_calls": [
                {"function": {"name": name, "arguments": arguments}}
            ],
        }
    }


class ConsolidationAdmissionV2CoreTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = _load(CONFIG_PATH)
        cls.dataset = _load(ROOT / cls.config["dataset"]["path"])
        cls.v1_config = _load(V1_CONFIG_PATH)

    def test_tool_parser_accepts_each_authorized_target(self):
        frames = (
            (
                {
                    "memory_kind": "wisdom",
                    "scope": "stable",
                    "owner": "user",
                    "evidence_user_turns": [2],
                    "confidence_band": "high",
                },
                "wisdom",
            ),
            (
                {
                    "memory_kind": "procedural",
                    "scope": "recurring",
                    "owner": "assistant",
                    "evidence_user_turns": [1],
                    "confidence_band": "medium",
                },
                "procedural",
            ),
            (
                {
                    "memory_kind": "none",
                    "scope": "transient",
                    "owner": "user",
                    "evidence_user_turns": [],
                    "confidence_band": "low",
                },
                "none",
            ),
        )
        for frame, expected in frames:
            with self.subTest(expected=expected):
                parsed = parse_indexed_tool_response(_tool_response(frame))
                self.assertTrue(parsed["parse_success"])
                self.assertTrue(parsed["index_contract_success"])
                self.assertEqual(parsed["observed_target"], expected)

    def test_tool_parser_rejects_wrong_transport_and_shape(self):
        valid = {
            "memory_kind": "wisdom",
            "scope": "stable",
            "owner": "user",
            "evidence_user_turns": [2],
            "confidence_band": "high",
        }
        variants = (
            _tool_response(valid, name="wrong_tool"),
            _tool_response({**valid, "extra": "leak"}),
            _tool_response(valid, content="Here is the answer."),
            {"message": {"content": "", "tool_calls": []}},
        )
        for response in variants:
            with self.subTest(response=response):
                parsed = parse_indexed_tool_response(response)
                self.assertFalse(parsed["parse_success"])
                self.assertEqual(parsed["observed_target"], "none")

    def test_index_contract_rejects_invalid_duplicate_and_empty_indices(self):
        variants = (
            [True],
            [4],
            [2, 2],
            [],
        )
        for indices in variants:
            frame = {
                "memory_kind": "wisdom",
                "scope": "stable",
                "owner": "user",
                "evidence_user_turns": indices,
                "confidence_band": "high",
            }
            with self.subTest(indices=indices):
                parsed = parse_indexed_tool_response(_tool_response(frame))
                self.assertTrue(parsed["parse_success"])
                self.assertFalse(parsed["index_contract_success"])
                self.assertEqual(parsed["observed_target"], "none")

    def test_compiler_fails_closed_on_unauthorized_frame(self):
        frame = {
            "memory_kind": "wisdom",
            "scope": "stable",
            "owner": "assistant",
            "evidence_user_turns": [1],
            "confidence_band": "high",
        }
        self.assertEqual(
            compile_indexed_frame(frame, index_contract_success=True), "none"
        )

    def test_v1_control_maps_exact_quotes_to_user_turn_ids(self):
        utterances = ["A temporary request.", "I always use the left side."]
        payload = {
            "episodic_summary": "左側を使う。",
            "candidate_kind": "wisdom",
            "scope": "stable",
            "target": "user",
            "rule_jp": "ユーザーは左側を使う。",
            "evidence_quotes": [utterances[1]],
            "confidence": 0.9,
        }
        response = {"message": {"content": json.dumps(payload)}}
        parsed = parse_v1_control_response(
            response,
            utterances,
            self.v1_config["conditions"]["source_bound_layered_candidate"],
        )
        self.assertEqual(parsed["observed_target"], "wisdom")
        self.assertEqual(parsed["evidence_user_turns"], [2])
        self.assertTrue(parsed["index_contract_success"])

    def test_scorer_applies_every_preregistered_gate(self):
        control_rows = []
        candidate_rows = []
        for case in self.dataset["cases"]:
            expected = case["expected_memory_kind"]
            wrong = "wisdom" if expected == "none" else "none"
            control_rows.append(
                {
                    "id": case["id"],
                    "observed_target": wrong,
                    "parse_success": True,
                    "wall_seconds": 1.0,
                }
            )
            candidate_rows.append(
                {
                    "id": case["id"],
                    "observed_target": expected,
                    "parse_success": True,
                    "index_contract_success": True,
                    "memory_kind": expected,
                    "scope": case["expected_scope"],
                    "owner": case["expected_owner"],
                    "evidence_user_turns": case[
                        "required_evidence_user_turns"
                    ],
                    "wall_seconds": 1.0,
                }
            )
        result = analyze_indexed_conditions(
            self.dataset["cases"],
            control_rows,
            candidate_rows,
            self.config["success_gates"],
        )
        self.assertTrue(result["all_gates_pass"])
        self.assertEqual(result["candidate"]["frame_exact_count"], 18)
        self.assertEqual(result["candidate"]["evidence_grounded_count"], 18)
        self.assertEqual(set(result["gate_checks"]), set(self.config["success_gates"]))


class ConsolidationAdmissionV2HarnessTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = _load(CONFIG_PATH)
        cls.lock = _load(LOCK_PATH)
        cls.dataset = _load(ROOT / cls.config["dataset"]["path"])

    def test_protocol_correction_is_pre_inference_and_hash_bound(self):
        correction = _load(CORRECTION_PATH)
        self.assertFalse(correction["inference_performed_before_detection"])
        self.assertFalse(correction["result_artifacts_present_before_correction"])
        self.assertEqual(correction["correction"]["before"], 256)
        self.assertEqual(correction["correction"]["after"], 384)
        self.assertEqual(
            correction["corrected_preregistration_sha256"],
            _sha256(CONFIG_PATH),
        )

    def test_lock_hashes_all_frozen_artifacts_and_v1_dependencies(self):
        frozen = self.lock["frozen_artifacts"]
        for name in (
            "preregistration",
            "protocol_correction",
            "dataset",
            "v1_preregistration",
            "v1_core",
            "v1_result_lock",
            "core",
            "runner",
            "analyzer",
            "harness_test",
        ):
            path = ROOT / frozen[name]
            self.assertEqual(_sha256(path), frozen[f"{name}_sha256"])

    def test_condition_order_is_balanced_and_alternating(self):
        first_counts = {runner.CONTROL: 0, runner.CANDIDATE: 0}
        for index, _case in enumerate(self.dataset["cases"]):
            order = runner.condition_order(self.config, index)
            self.assertEqual(set(order), set(first_counts))
            first_counts[order[0]] += 1
        self.assertEqual(
            first_counts, {runner.CONTROL: 9, runner.CANDIDATE: 9}
        )

    def test_request_payload_contains_transcript_but_no_gold(self):
        case = self.dataset["cases"][0]
        control = runner.build_request_body(
            self.config, case, runner.CONTROL
        )
        candidate = runner.build_request_body(
            self.config, case, runner.CANDIDATE
        )
        for body in (control, candidate):
            serialized = json.dumps(body, ensure_ascii=False)
            self.assertIn(case["session"][0]["user"], serialized)
            self.assertIn("User[U1]", serialized)
            for forbidden in (
                case["id"],
                case["gold_reason"],
                "expected_memory_kind",
                "expected_scope",
                "expected_owner",
                "required_evidence_user_turns",
                "allowed_evidence_user_turns",
            ):
                self.assertNotIn(forbidden, serialized)
            self.assertEqual(body["options"]["num_predict"], 384)
            self.assertEqual(body["options"]["temperature"], 0.1)
        self.assertNotIn("tools", control)
        self.assertEqual(
            candidate["tools"][0]["function"]["name"],
            "classify_memory_admission",
        )

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
        control_rows = []
        candidate_rows = []
        for case in self.dataset["cases"]:
            expected = case["expected_memory_kind"]
            wrong = "wisdom" if expected == "none" else "none"
            control_rows.append(
                {
                    "id": case["id"],
                    "condition": runner.CONTROL,
                    "observed_target": wrong,
                    "parse_success": True,
                    "wall_seconds": 1.0,
                }
            )
            candidate_rows.append(
                {
                    "id": case["id"],
                    "condition": runner.CANDIDATE,
                    "observed_target": expected,
                    "parse_success": True,
                    "index_contract_success": True,
                    "memory_kind": expected,
                    "scope": case["expected_scope"],
                    "owner": case["expected_owner"],
                    "evidence_user_turns": case[
                        "required_evidence_user_turns"
                    ],
                    "wall_seconds": 1.0,
                }
            )
        gate_snapshot = analyze_indexed_conditions(
            self.dataset["cases"],
            control_rows,
            candidate_rows,
            self.config["success_gates"],
        )
        raw = {
            "experiment_id": self.config["experiment_id"],
            "completed_at": "2026-07-17T00:00:00+09:00",
            "preregistration_sha256": _sha256(CONFIG_PATH),
            "protocol_correction_sha256": _sha256(CORRECTION_PATH),
            "harness_lock_sha256": _sha256(LOCK_PATH),
            "dataset_sha256": _sha256(
                ROOT / self.config["dataset"]["path"]
            ),
            "v1_preregistration_sha256": _sha256(
                ROOT
                / "configs"
                / "consolidation_admission_v1_development_preregistration.json"
            ),
            "v1_core_sha256": _sha256(
                ROOT / "consolidation_admission_v1_core.py"
            ),
            "v1_result_lock_sha256": _sha256(
                ROOT / "configs" / "consolidation_admission_v1_result_lock.json"
            ),
            "gold_fields_passed_to_model": False,
            "runtime_memory_write_performed": False,
            "model_snapshot": self.config["model"],
            "model_calls": 36,
            "transport_attempts_made": 36,
            "control_rows": control_rows,
            "candidate_rows": candidate_rows,
            "gate_snapshot": gate_snapshot,
        }
        with tempfile.TemporaryDirectory() as temporary:
            raw_path = Path(temporary) / "raw.json"
            raw_path.write_text(
                json.dumps(raw, ensure_ascii=False), encoding="utf-8"
            )
            analysis = analyzer.analyze(raw_path)
        self.assertTrue(analysis["matched_result"]["all_gates_pass"])
        self.assertTrue(
            analysis["post_admission_generation_pilot_authorized"]
        )
        self.assertFalse(analysis["runtime_memory_write_authorized"])
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
