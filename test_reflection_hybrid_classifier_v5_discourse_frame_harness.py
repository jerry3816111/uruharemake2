#!/usr/bin/env python3
"""Test the frozen V5 discourse-frame pilot harness without model inference."""

from __future__ import annotations

import hashlib
import json
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

import run_reflection_hybrid_classifier_v5_discourse_frame_development as runner
from reflection_hybrid_classifier_v5_core import (
    analyze_discourse_frame_condition,
    parse_discourse_frame_tool_response,
    parse_direct_tool_response,
)


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "reflection_hybrid_classifier_v5_discourse_frame_development_preregistration.json"
LOCK_PATH = ROOT / "configs" / "reflection_hybrid_classifier_v5_discourse_frame_harness_lock.json"
RESULT_LOCK_PATH = ROOT / "configs" / "reflection_hybrid_classifier_v5_discourse_frame_result_lock.json"


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _tool_response(arguments):
    return {
        "message": {
            "content": "",
            "tool_calls": [
                {
                    "function": {
                        "name": "classify_reflection_with_discourse_frame",
                        "arguments": arguments,
                    }
                }
            ],
        }
    }


VALID_FRAME = {
    "speaker_scope": "first_person",
    "addressee_target": "interlocutor",
    "time_scope": "future_interaction",
    "communicative_act": "directive",
    "relation_to_prior_words": "none",
    "reflection_type": "procedural",
}


class ReflectionDiscourseFrameCoreTest(unittest.TestCase):
    def test_parser_accepts_exact_frame(self):
        frame, parsed, content, calls, error = parse_discourse_frame_tool_response(
            _tool_response(VALID_FRAME)
        )
        self.assertTrue(parsed)
        self.assertEqual(frame, VALID_FRAME)
        self.assertEqual(content, "")
        self.assertEqual(len(calls), 1)
        self.assertIsNone(error)

    def test_parser_rejects_missing_extra_and_invalid_slots(self):
        variants = [
            {key: value for key, value in VALID_FRAME.items() if key != "time_scope"},
            {**VALID_FRAME, "extra": "leak"},
            {**VALID_FRAME, "communicative_act": "guess"},
        ]
        for arguments in variants:
            with self.subTest(arguments=arguments):
                frame, parsed, *_ = parse_discourse_frame_tool_response(
                    _tool_response(arguments)
                )
                self.assertFalse(parsed)
                self.assertIsNone(frame)

    def test_direct_parser_accepts_original_v3_contract(self):
        response = {
            "message": {
                "content": "",
                "tool_calls": [
                    {
                        "function": {
                            "name": "classify_reflection",
                            "arguments": {"reflection_type": "semantic"},
                        }
                    }
                ],
            }
        }
        label, parsed, *_ = parse_direct_tool_response(response)
        self.assertTrue(parsed)
        self.assertEqual(label, "semantic")

    def test_matched_scorer_compares_candidate_to_frozen_control(self):
        cases = [
            {"id": "s", "language": "eng", "expected_type": "semantic"},
            {"id": "p", "language": "eng", "expected_type": "procedural"},
            {"id": "i", "language": "eng", "expected_type": "interpretive"},
            {"id": "n", "language": "eng", "expected_type": "none"},
        ]
        rules = {case["id"]: "none" for case in cases}
        control_rows = [
            {"id": "s", "hybrid_observed_type": "semantic"},
            {"id": "p", "hybrid_observed_type": "semantic"},
            {"id": "i", "hybrid_observed_type": "interpretive"},
            {"id": "n", "hybrid_observed_type": "none"},
        ]
        live_control_fallback_rows = [
            {
                "id": row["id"],
                "observed_type": row["hybrid_observed_type"],
                "parse_success": True,
                "wall_seconds": 1.0,
            }
            for row in control_rows
        ]
        candidate_fallback_rows = [
            {
                "id": case["id"],
                "observed_type": case["expected_type"],
                "parse_success": True,
                "wall_seconds": 1.0,
            }
            for case in cases
        ]
        candidate_gates = {
            "candidate_correct_count_min": 4,
            "candidate_accuracy_min": 1.0,
            "candidate_semantic_correct_min": 1,
            "candidate_procedural_correct_min": 1,
            "candidate_interpretive_correct_min": 1,
            "candidate_none_correct": 1,
            "newly_correct_vs_matched_control_min": 1,
            "regression_vs_matched_control_max": 0,
            "critical_false_positive_count_max": 0,
            "parse_success_rate_min": 1.0,
            "median_fallback_seconds_max": 2.0,
            "warm_p95_fallback_seconds_max": 2.0,
        }
        live_control_gates = {
            "correct_count_exact": 3,
            "prediction_drift_vs_frozen_v3_count_max": 0,
            "parse_success_rate_min": 1.0,
            "critical_false_positive_count_max": 0,
            "fallback_call_count_exact": 4,
        }
        result = analyze_discourse_frame_condition(
            cases,
            rules,
            control_rows,
            live_control_fallback_rows,
            candidate_fallback_rows,
            candidate_gates,
            live_control_gates,
            8,
        )
        self.assertTrue(result["all_gates_pass"])
        self.assertEqual(result["frozen_control_correct_count"], 3)
        self.assertEqual(result["live_control_correct_count"], 3)
        self.assertEqual(result["candidate_correct_count"], 4)
        self.assertEqual(result["newly_correct_case_ids"], ["p"])
        self.assertEqual(result["regression_case_ids"], [])


class ReflectionDiscourseFrameHarnessTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = _load(CONFIG_PATH)
        cls.lock = _load(LOCK_PATH)

    def test_lock_hashes_all_frozen_harness_artifacts(self):
        frozen = self.lock["frozen_artifacts"]
        for name in (
            "preregistration",
            "protocol_amendment",
            "dataset",
            "v3_preregistration",
            "frozen_control_result_lock",
            "frozen_control_analysis",
            "core",
            "runner",
            "analyzer",
            "harness_test",
            "protocol_amendment_test",
        ):
            path = ROOT / frozen[name]
            self.assertEqual(_sha256(path), frozen[f"{name}_sha256"])

    def test_model_call_payload_contains_no_gold_or_case_id(self):
        captured = {}

        def fake_post(url, body, timeout):
            captured.update({"url": url, "body": body, "timeout": timeout})
            return _tool_response(VALID_FRAME)

        with patch.object(runner, "_post_json", side_effect=fake_post):
            result = runner._call_model(
                self.config,
                _load(
                    ROOT
                    / "configs"
                    / "reflection_hybrid_classifier_v3_tool_carrier_development_preregistration.json"
                ),
                "discourse_frame_candidate",
                "eng",
                "A synthetic utterance not in the dataset.",
            )
        self.assertTrue(result["parse_success"])
        user_payload = json.loads(captured["body"]["messages"][1]["content"])
        self.assertEqual(
            user_payload,
            {
                "language": "eng",
                "utterance": "A synthetic utterance not in the dataset.",
            },
        )
        serialized = json.dumps(captured["body"], ensure_ascii=False)
        self.assertNotIn("expected_type", serialized)
        self.assertNotIn("case_id", serialized)
        self.assertEqual(captured["body"]["model"], "qwen3.5:4b")
        self.assertEqual(captured["body"]["options"]["temperature"], 0.0)

    def test_runner_cannot_load_retired_v4_holdout(self):
        source = Path(runner.__file__).read_text(encoding="utf-8")
        self.assertNotIn("reflection_hybrid_classifier_v4_independent_holdout.json", source)
        self.assertNotIn("fresh_v4_holdout_exclusion", source)

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


if __name__ == "__main__":
    unittest.main()
