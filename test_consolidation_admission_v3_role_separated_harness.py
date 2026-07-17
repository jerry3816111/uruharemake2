#!/usr/bin/env python3
"""Test the frozen role-separated consolidation V3 harness."""

from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

import analyze_consolidation_admission_v3_role_separated_development as analyzer
import run_consolidation_admission_v3_role_separated_development as runner
from consolidation_admission_v3_role_separated_core import (
    analyze_role_separated_conditions,
    compile_role_separated_frame,
    derive_applies_to,
    parse_role_separated_tool_response,
)


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = (
    ROOT
    / "configs"
    / "consolidation_admission_v3_role_separated_development_preregistration.json"
)
LOCK_PATH = (
    ROOT
    / "configs"
    / "consolidation_admission_v3_role_separated_harness_lock.json"
)
RESULT_LOCK_PATH = (
    ROOT
    / "configs"
    / "consolidation_admission_v3_role_separated_result_lock.json"
)


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _tool_response(arguments, *, name="classify_memory_basis", content=""):
    return {
        "message": {
            "content": content,
            "tool_calls": [
                {"function": {"name": name, "arguments": arguments}}
            ],
        }
    }


class ConsolidationAdmissionV3CoreTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = _load(CONFIG_PATH)
        cls.dataset = _load(ROOT / cls.config["dataset"]["path"])

    def test_tool_parser_accepts_each_authorized_target(self):
        frames = (
            (
                {
                    "memory_kind": "wisdom",
                    "persistence_basis": "stable_trait",
                    "evidence_user_turns": [2],
                },
                "wisdom",
                "user_profile",
            ),
            (
                {
                    "memory_kind": "procedural",
                    "persistence_basis": "explicit_future_policy",
                    "evidence_user_turns": [1],
                },
                "procedural",
                "assistant_policy",
            ),
            (
                {
                    "memory_kind": "none",
                    "persistence_basis": "no_long_term_basis",
                    "evidence_user_turns": [],
                },
                "none",
                "none",
            ),
        )
        for frame, target, applies_to in frames:
            with self.subTest(target=target):
                parsed = parse_role_separated_tool_response(
                    _tool_response(frame)
                )
                self.assertTrue(parsed["parse_success"])
                self.assertTrue(parsed["index_contract_success"])
                self.assertEqual(parsed["observed_target"], target)
                self.assertEqual(
                    parsed["compiled_applies_to"], applies_to
                )

    def test_tool_parser_rejects_wrong_transport_and_shape(self):
        valid = {
            "memory_kind": "wisdom",
            "persistence_basis": "stable_trait",
            "evidence_user_turns": [2],
        }
        variants = (
            _tool_response(valid, name="wrong_tool"),
            _tool_response({**valid, "owner": "user"}),
            _tool_response(valid, content="Narrative."),
            {"message": {"content": "", "tool_calls": []}},
        )
        for response in variants:
            with self.subTest(response=response):
                parsed = parse_role_separated_tool_response(response)
                self.assertFalse(parsed["parse_success"])
                self.assertEqual(parsed["observed_target"], "none")

    def test_index_contract_rejects_bad_indices(self):
        for indices in ([True], [4], [2, 2], []):
            frame = {
                "memory_kind": "wisdom",
                "persistence_basis": "stable_trait",
                "evidence_user_turns": indices,
            }
            with self.subTest(indices=indices):
                parsed = parse_role_separated_tool_response(
                    _tool_response(frame)
                )
                self.assertTrue(parsed["parse_success"])
                self.assertFalse(parsed["index_contract_success"])
                self.assertEqual(parsed["observed_target"], "none")

    def test_compiler_requires_matching_kind_basis_and_evidence(self):
        invalid_frames = (
            {
                "memory_kind": "wisdom",
                "persistence_basis": "explicit_future_policy",
                "evidence_user_turns": [1],
            },
            {
                "memory_kind": "wisdom",
                "persistence_basis": "repeated_pattern",
                "evidence_user_turns": [1],
            },
            {
                "memory_kind": "procedural",
                "persistence_basis": "stable_trait",
                "evidence_user_turns": [1],
            },
        )
        for frame in invalid_frames:
            with self.subTest(frame=frame):
                self.assertEqual(
                    compile_role_separated_frame(
                        frame, index_contract_success=True
                    ),
                    "none",
                )
        self.assertEqual(derive_applies_to("wisdom"), "user_profile")
        self.assertEqual(
            derive_applies_to("procedural"), "assistant_policy"
        )

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
                    "persistence_basis": case[
                        "expected_persistence_basis"
                    ],
                    "evidence_user_turns": case[
                        "required_evidence_user_turns"
                    ],
                    "compiled_applies_to": case["expected_applies_to"],
                    "wall_seconds": 1.0,
                }
            )
        result = analyze_role_separated_conditions(
            self.dataset["cases"],
            control_rows,
            candidate_rows,
            self.config["success_gates"],
        )
        self.assertTrue(result["all_gates_pass"])
        self.assertEqual(
            result["candidate"]["semantic_frame_exact_count"], 18
        )
        self.assertEqual(
            result["candidate"]["derived_applicability_success_count"], 18
        )
        self.assertEqual(
            set(result["gate_checks"]), set(self.config["success_gates"])
        )


class ConsolidationAdmissionV3HarnessTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = _load(CONFIG_PATH)
        cls.lock = _load(LOCK_PATH)
        cls.dataset = _load(ROOT / cls.config["dataset"]["path"])

    def test_lock_hashes_all_frozen_artifacts_and_v2_dependencies(self):
        frozen = self.lock["frozen_artifacts"]
        for name in (
            "preregistration",
            "dataset",
            "v2_preregistration",
            "v2_core",
            "v2_result_lock",
            "core",
            "runner",
            "analyzer",
            "harness_test",
        ):
            self.assertEqual(
                _sha256(ROOT / frozen[name]), frozen[f"{name}_sha256"]
            )

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
                "expected_persistence_basis",
                "expected_applies_to",
                "required_evidence_user_turns",
                "allowed_evidence_user_turns",
            ):
                self.assertNotIn(forbidden, serialized)
            self.assertEqual(body["options"]["num_predict"], 384)
            self.assertEqual(body["options"]["temperature"], 0.1)
            self.assertEqual(len(body["tools"]), 1)
        self.assertEqual(
            control["tools"][0]["function"]["name"],
            "classify_memory_admission",
        )
        self.assertEqual(
            candidate["tools"][0]["function"]["name"],
            "classify_memory_basis",
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
                    "persistence_basis": case[
                        "expected_persistence_basis"
                    ],
                    "evidence_user_turns": case[
                        "required_evidence_user_turns"
                    ],
                    "compiled_applies_to": case["expected_applies_to"],
                    "wall_seconds": 1.0,
                }
            )
        gate_snapshot = analyze_role_separated_conditions(
            self.dataset["cases"],
            control_rows,
            candidate_rows,
            self.config["success_gates"],
        )
        raw = {
            "experiment_id": self.config["experiment_id"],
            "completed_at": "2026-07-17T00:00:00+09:00",
            "preregistration_sha256": _sha256(CONFIG_PATH),
            "harness_lock_sha256": _sha256(LOCK_PATH),
            "dataset_sha256": _sha256(
                ROOT / self.config["dataset"]["path"]
            ),
            "v2_preregistration_sha256": _sha256(
                ROOT
                / "configs"
                / "consolidation_admission_v2_indexed_development_preregistration.json"
            ),
            "v2_core_sha256": _sha256(
                ROOT / "consolidation_admission_v2_indexed_core.py"
            ),
            "v2_result_lock_sha256": _sha256(
                ROOT
                / "configs"
                / "consolidation_admission_v2_indexed_result_lock.json"
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
