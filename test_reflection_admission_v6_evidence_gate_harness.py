#!/usr/bin/env python3
"""Test the frozen V6 admission harness without model inference."""

from __future__ import annotations

import hashlib
import json
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

import run_reflection_admission_v6_evidence_gate_development as runner
from reflection_admission_v6_core import (
    analyze_admission_condition,
    parse_admission_tool_response,
)


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = (
    ROOT
    / "configs"
    / "reflection_admission_v6_evidence_gate_development_preregistration.json"
)
LOCK_PATH = (
    ROOT / "configs" / "reflection_admission_v6_evidence_gate_harness_lock.json"
)
RESULT_LOCK_PATH = (
    ROOT / "configs" / "reflection_admission_v6_evidence_gate_result_lock.json"
)


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _tool_response(arguments, name="verify_reflection_admission"):
    return {
        "message": {
            "content": "",
            "tool_calls": [
                {"function": {"name": name, "arguments": arguments}}
            ],
        }
    }


class ReflectionAdmissionCoreTest(unittest.TestCase):
    def test_parser_accepts_exact_admit_and_reject_contracts(self):
        utterance = "Be careful next time."
        admit = {
            "admission": "admit",
            "evidence_span": "Be careful next time.",
            "reason_code": "explicit_future_instruction",
        }
        decision, parsed, evidence, *_ = parse_admission_tool_response(
            _tool_response(admit), utterance
        )
        self.assertEqual(decision, admit)
        self.assertTrue(parsed)
        self.assertTrue(evidence)

        reject = {
            "admission": "reject",
            "evidence_span": "",
            "reason_code": "speaker_intention_or_promise",
        }
        decision, parsed, evidence, *_ = parse_admission_tool_response(
            _tool_response(reject), "I'll do better next time."
        )
        self.assertEqual(decision, reject)
        self.assertTrue(parsed)
        self.assertTrue(evidence)

    def test_parser_rejects_malformed_tool_calls(self):
        valid = {
            "admission": "admit",
            "evidence_span": "Next time",
            "reason_code": "explicit_future_instruction",
        }
        variants = [
            {"message": {"content": "", "tool_calls": []}},
            _tool_response({key: value for key, value in valid.items() if key != "reason_code"}),
            _tool_response({**valid, "extra": "leak"}),
            _tool_response(valid, name="wrong_tool"),
        ]
        for response in variants:
            with self.subTest(response=response):
                decision, parsed, evidence, *_ = parse_admission_tool_response(
                    response, "Next time"
                )
                self.assertIsNone(decision)
                self.assertFalse(parsed)
                self.assertFalse(evidence)

    def test_parser_separates_parse_from_evidence_failure(self):
        invalid_admit_span = {
            "admission": "admit",
            "evidence_span": "words not in the utterance",
            "reason_code": "explicit_future_instruction",
        }
        decision, parsed, evidence, *_ = parse_admission_tool_response(
            _tool_response(invalid_admit_span), "Next time, study harder."
        )
        self.assertIsNotNone(decision)
        self.assertTrue(parsed)
        self.assertFalse(evidence)

    def test_scorer_compares_admit_all_to_evidence_gate(self):
        cases = [
            {"id": "a1", "language": "eng", "expected_admission": "admit"},
            {"id": "a2", "language": "eng", "expected_admission": "admit"},
            {"id": "r1", "language": "eng", "expected_admission": "reject"},
            {"id": "r2", "language": "eng", "expected_admission": "reject"},
        ]
        rows = [
            {
                "id": case["id"],
                "observed_admission": case["expected_admission"],
                "parse_success": True,
                "evidence_contract_success": True,
                "wall_seconds": 1.0,
            }
            for case in cases
        ]
        gates = {
            "control_correct_count_exact": 2,
            "candidate_correct_count_min": 4,
            "candidate_accuracy_min": 1.0,
            "candidate_admit_correct_min": 2,
            "candidate_reject_correct_min": 2,
            "newly_correct_vs_control_min": 2,
            "regression_vs_control_max": 0,
            "net_gain_vs_control_min": 2,
            "false_admit_count_max": 0,
            "false_reject_count_max": 0,
            "parse_success_rate_min": 1.0,
            "evidence_contract_success_rate_min": 1.0,
            "model_call_count_exact": 4,
            "median_wall_seconds_max": 2.0,
            "warm_p95_wall_seconds_max": 2.0,
        }
        result = analyze_admission_condition(cases, rows, gates)
        self.assertTrue(result["all_gates_pass"])
        self.assertEqual(result["control_correct_count"], 2)
        self.assertEqual(result["candidate_correct_count"], 4)
        self.assertEqual(result["newly_correct_case_ids"], ["r1", "r2"])
        self.assertEqual(result["regression_case_ids"], [])


class ReflectionAdmissionHarnessTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = _load(CONFIG_PATH)
        cls.lock = _load(LOCK_PATH)

    def test_lock_hashes_all_frozen_harness_artifacts(self):
        frozen = self.lock["frozen_artifacts"]
        for name in (
            "preregistration",
            "construction_closure",
            "dataset",
            "core",
            "runner",
            "analyzer",
            "harness_test",
        ):
            path = ROOT / frozen[name]
            self.assertEqual(_sha256(path), frozen[f"{name}_sha256"])

    def test_model_payload_contains_no_gold_or_case_id(self):
        captured = {}
        arguments = {
            "admission": "admit",
            "evidence_span": "Be careful next time.",
            "reason_code": "explicit_future_instruction",
        }

        def fake_post(url, body, timeout):
            captured.update({"url": url, "body": body, "timeout": timeout})
            return _tool_response(arguments)

        case = {
            "id": "synthetic",
            "language": "eng",
            "text": "Be careful next time.",
            "expected_admission": "admit",
            "gold_reason": "must_not_leak",
        }
        with patch.object(runner, "_post_json", side_effect=fake_post):
            result = runner._call_model(self.config, case)
        self.assertTrue(result["parse_success"])
        user_payload = json.loads(captured["body"]["messages"][1]["content"])
        self.assertEqual(
            user_payload,
            {
                "language": "eng",
                "utterance": "Be careful next time.",
                "proposal": self.config["proposal_under_review"],
            },
        )
        serialized = json.dumps(captured["body"], ensure_ascii=False)
        self.assertNotIn("expected_admission", serialized)
        self.assertNotIn("gold_reason", serialized)
        self.assertNotIn("case_id", serialized)
        self.assertEqual(captured["body"]["model"], "qwen3.5:4b")
        self.assertEqual(captured["body"]["options"]["temperature"], 0.0)

    def test_runner_does_not_load_prior_reflection_eval_datasets(self):
        source = Path(runner.__file__).read_text(encoding="utf-8")
        forbidden = (
            "reflection_classifier_v1_external_holdout.json",
            "reflection_hybrid_classifier_v4_independent_holdout",
            "reflection_hybrid_classifier_v5_discourse_frame",
        )
        for value in forbidden:
            self.assertNotIn(value, source)

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
