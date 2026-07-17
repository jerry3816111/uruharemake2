#!/usr/bin/env python3
"""Test the frozen consolidation-admission V1 harness without inference."""

from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import analyze_consolidation_admission_v1_development as analyzer
import run_consolidation_admission_v1_development as runner
from consolidation_admission_v1_core import (
    analyze_conditions,
    parse_candidate_response,
    parse_control_response,
)


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = (
    ROOT / "configs" / "consolidation_admission_v1_development_preregistration.json"
)
LOCK_PATH = ROOT / "configs" / "consolidation_admission_v1_harness_lock.json"
RESULT_LOCK_PATH = ROOT / "configs" / "consolidation_admission_v1_result_lock.json"


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _response(payload):
    return {"message": {"content": json.dumps(payload, ensure_ascii=False)}}


class ConsolidationAdmissionCoreTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = _load(CONFIG_PATH)
        cls.condition = cls.config["conditions"][
            "source_bound_layered_candidate"
        ]

    def test_control_parser_distinguishes_both_memory_stores(self):
        wisdom = parse_control_response(
            _response(
                {
                    "episodic_summary": "要約",
                    "wisdom_rule": "長期事実",
                    "procedural_rule": "NO_RULE",
                    "salience": 0.7,
                }
            )
        )
        multiple = parse_control_response(
            _response(
                {
                    "episodic_summary": "要約",
                    "wisdom_rule": "長期事実",
                    "procedural_rule": "応答手順",
                    "salience": 0.7,
                }
            )
        )
        self.assertEqual(wisdom["observed_target"], "wisdom")
        self.assertEqual(multiple["observed_target"], "multiple")

    def test_candidate_compiler_accepts_source_bound_targets(self):
        utterances = [
            "I prefer quiet rooms.",
            "Use that preference later too.",
        ]
        wisdom = {
            "episodic_summary": "静かな場所を好むと話した。",
            "candidate_kind": "wisdom",
            "scope": "repeated",
            "target": "user",
            "rule_jp": "ユーザーは静かな場所を好む。",
            "evidence_quotes": utterances,
            "confidence": 0.9,
        }
        procedural = {
            "episodic_summary": "今後の応答順を指定した。",
            "candidate_kind": "procedural",
            "scope": "recurring",
            "target": "assistant",
            "rule_jp": "次回も結論を先に返す。",
            "evidence_quotes": ["Use that preference later too."],
            "confidence": 0.8,
        }
        parsed_wisdom = parse_candidate_response(
            _response(wisdom), utterances, self.condition
        )
        parsed_procedural = parse_candidate_response(
            _response(procedural), utterances, self.condition
        )
        self.assertEqual(parsed_wisdom["observed_target"], "wisdom")
        self.assertEqual(parsed_procedural["observed_target"], "procedural")
        self.assertTrue(parsed_wisdom["evidence_contract_success"])
        self.assertTrue(parsed_procedural["japanese_rule_contract_success"])

    def test_candidate_compiler_fails_closed(self):
        utterances = ["For this answer only, be brief."]
        variants = [
            {
                "episodic_summary": "今回だけ短くする。",
                "candidate_kind": "procedural",
                "scope": "one_off",
                "target": "assistant",
                "rule_jp": "今回だけ短く返す。",
                "evidence_quotes": utterances,
                "confidence": 0.9,
            },
            {
                "episodic_summary": "好みを推測した。",
                "candidate_kind": "wisdom",
                "scope": "stable",
                "target": "user",
                "rule_jp": "短い回答を好む。",
                "evidence_quotes": ["not an exact utterance"],
                "confidence": 0.7,
            },
            {
                "episodic_summary": "安定した好みを述べた。",
                "candidate_kind": "wisdom",
                "scope": "stable",
                "target": "user",
                "rule_jp": "NO_RULE",
                "evidence_quotes": utterances,
                "confidence": 0.8,
            },
        ]
        for payload in variants:
            with self.subTest(payload=payload):
                parsed = parse_candidate_response(
                    _response(payload), utterances, self.condition
                )
                self.assertEqual(parsed["observed_target"], "none")

    def test_parser_rejects_extra_keys_and_non_numeric_confidence(self):
        payload = {
            "episodic_summary": "要約",
            "candidate_kind": "none",
            "scope": "none",
            "target": "none",
            "rule_jp": "NO_RULE",
            "evidence_quotes": [],
            "confidence": "0.5",
            "extra": "leak",
        }
        parsed = parse_candidate_response(
            _response(payload), ["hello"], self.condition
        )
        self.assertFalse(parsed["parse_success"])
        self.assertEqual(parsed["observed_target"], "none")

    def test_scorer_applies_all_matched_gates(self):
        cases = [
            {
                "id": f"{target}-{index}",
                "language": "eng",
                "expected_long_term_target": target,
            }
            for target in ("wisdom", "procedural", "none")
            for index in range(2)
        ]
        control_observed = {
            "wisdom": "none",
            "procedural": "none",
            "none": "wisdom",
        }
        control_rows = [
            {
                "id": case["id"],
                "observed_target": control_observed[
                    case["expected_long_term_target"]
                ],
                "parse_success": True,
                "wall_seconds": 1.0,
            }
            for case in cases
        ]
        candidate_rows = [
            {
                "id": case["id"],
                "observed_target": case["expected_long_term_target"],
                "parse_success": True,
                "evidence_contract_success": True,
                "japanese_rule_contract_success": True,
                "wall_seconds": 1.0,
            }
            for case in cases
        ]
        gates = {
            "candidate_correct_count_min": 6,
            "candidate_accuracy_min": 1.0,
            "candidate_wisdom_correct_min": 2,
            "candidate_procedural_correct_min": 2,
            "candidate_none_correct_min": 2,
            "newly_correct_vs_control_min": 6,
            "regression_vs_control_max": 0,
            "net_correct_gain_vs_control_min": 6,
            "candidate_false_long_term_write_count_max": 0,
            "candidate_missed_long_term_write_count_max": 0,
            "candidate_parse_success_rate_min": 1.0,
            "candidate_evidence_contract_success_rate_min": 1.0,
            "candidate_japanese_rule_contract_success_rate_min": 1.0,
            "model_call_count_exact": 12,
            "control_median_wall_seconds_max": 2.0,
            "candidate_median_wall_seconds_max": 2.0,
            "control_warm_p95_wall_seconds_max": 2.0,
            "candidate_warm_p95_wall_seconds_max": 2.0,
        }
        result = analyze_conditions(
            cases, control_rows, candidate_rows, gates
        )
        self.assertTrue(result["all_gates_pass"])
        self.assertEqual(result["net_correct_gain_vs_control"], 6)


class ConsolidationAdmissionHarnessTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = _load(CONFIG_PATH)
        cls.lock = _load(LOCK_PATH)
        cls.dataset = _load(ROOT / cls.config["dataset"]["path"])

    def test_lock_hashes_all_frozen_harness_artifacts(self):
        frozen = self.lock["frozen_artifacts"]
        for name in (
            "preregistration",
            "protocol_correction",
            "dataset",
            "core",
            "runner",
            "analyzer",
            "harness_test",
        ):
            path = ROOT / frozen[name]
            self.assertEqual(_sha256(path), frozen[f"{name}_sha256"])

    def test_condition_order_is_balanced_and_alternating(self):
        first_counts = {"current_direct_rule_control": 0, "source_bound_layered_candidate": 0}
        for index, _case in enumerate(self.dataset["cases"]):
            order = runner.condition_order(self.config, index)
            self.assertEqual(set(order), set(first_counts))
            first_counts[order[0]] += 1
        self.assertEqual(first_counts, {"current_direct_rule_control": 9, "source_bound_layered_candidate": 9})

    def test_model_payload_contains_transcript_but_no_gold_or_case_id(self):
        captured = {}
        candidate_payload = {
            "episodic_summary": "一度だけ短く答えた。",
            "candidate_kind": "none",
            "scope": "one_off",
            "target": "none",
            "rule_jp": "NO_RULE",
            "evidence_quotes": [],
            "confidence": 0.8,
        }

        def fake_post(url, body, timeout):
            captured.update({"url": url, "body": body, "timeout": timeout})
            return _response(candidate_payload)

        case = {
            "id": "must_not_leak",
            "language": "eng",
            "session": [
                {"user": "For this answer only, be brief.", "assistant": "Okay."},
                {"user": "Next time can be normal.", "assistant": "Understood."},
            ],
            "expected_long_term_target": "none",
            "expected_evidence_quotes": [],
            "gold_reason": "must_not_leak",
        }
        with patch.object(runner, "_post_json", side_effect=fake_post):
            result = runner._call_condition(
                self.config, case, "source_bound_layered_candidate"
            )
        self.assertEqual(result["observed_target"], "none")
        serialized = json.dumps(captured["body"], ensure_ascii=False)
        self.assertIn("For this answer only, be brief.", serialized)
        for forbidden in (
            "must_not_leak",
            "expected_long_term_target",
            "expected_evidence_quotes",
            "gold_reason",
            "case_id",
        ):
            self.assertNotIn(forbidden, serialized)
        self.assertEqual(captured["body"]["model"], "qwen2.5:7b")
        self.assertEqual(captured["body"]["options"]["temperature"], 0.1)
        self.assertNotIn("tools", captured["body"])

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

    def test_analyzer_independently_recomputes_a_complete_raw_result(self):
        control_rows = []
        candidate_rows = []
        for case in self.dataset["cases"]:
            expected = case["expected_long_term_target"]
            wrong_control = "wisdom" if expected == "none" else "none"
            control_rows.append(
                {
                    "id": case["id"],
                    "condition": "current_direct_rule_control",
                    "observed_target": wrong_control,
                    "parse_success": True,
                    "wall_seconds": 1.0,
                }
            )
            candidate_rows.append(
                {
                    "id": case["id"],
                    "condition": "source_bound_layered_candidate",
                    "observed_target": expected,
                    "parse_success": True,
                    "evidence_contract_success": True,
                    "japanese_rule_contract_success": True,
                    "wall_seconds": 1.0,
                }
            )
        gate_snapshot = analyze_conditions(
            self.dataset["cases"],
            control_rows,
            candidate_rows,
            self.config["success_gates"],
        )
        raw = {
            "experiment_id": self.config["experiment_id"],
            "completed_at": "2026-07-17T00:00:00+09:00",
            "preregistration_sha256": _sha256(CONFIG_PATH),
            "protocol_correction_sha256": _sha256(
                ROOT
                / "configs"
                / "consolidation_admission_v1_protocol_correction.json"
            ),
            "harness_lock_sha256": _sha256(LOCK_PATH),
            "dataset_sha256": _sha256(
                ROOT / self.config["dataset"]["path"]
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
        self.assertTrue(analysis["runtime_shadow_authorized"])
        self.assertFalse(analysis["runtime_memory_write_authorized"])

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
