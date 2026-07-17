#!/usr/bin/env python3

import hashlib
import json
import subprocess
import unittest
from pathlib import Path

import analyze_rightbrain_pipeline_shadow_v61 as analyzer
import run_rightbrain_pipeline_shadow_v61 as runner


ROOT = Path(__file__).resolve().parent
PREREG_PATH = (
    ROOT / "configs" / "rightbrain_pipeline_shadow_v61_preregistration.json"
)
LOCK_PATH = (
    ROOT / "configs" / "rightbrain_pipeline_shadow_v61_harness_lock.json"
)


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class _FakeRightBrain:
    def _model_required_semantic_groups(self, _logic):
        return [("必要", "要る")]

    @staticmethod
    def _semantic_marker_hit(reply, marker):
        return marker in reply

    def _model_candidate_rejection_reasons(
        self,
        reply,
        _logic,
        _max_chars,
        user_input="",
    ):
        del user_input
        return [] if "必要" in reply else ["semantic_slots_missing:0/1"]

    def _prepare_model_surface_candidate(
        self,
        raw_reply,
        _logic,
        _user_input,
        _memory_data,
        _max_chars,
    ):
        reasons = self._model_candidate_rejection_reasons(
            raw_reply,
            {},
            50,
        )
        return (raw_reply, reasons) if not reasons else ("", reasons)

    @staticmethod
    def reset_session_state():
        return None


class _FakeBrain:
    def __init__(self):
        self.right_brain = _FakeRightBrain()

    @staticmethod
    def _self_monitor_reply(
        _user_input,
        _reply,
        _logic,
        _memory_data,
    ):
        return {"needs_repair": False, "issues": []}

    @staticmethod
    def _repair_reply_from_self_monitor(
        reply,
        _logic,
        _monitor,
        _user_input,
        _memory_data,
        _psyche,
    ):
        return reply

    @staticmethod
    def _attach_reply_post_check(
        _logic,
        _user_input,
        reply,
        _memory_data,
    ):
        return {"did_reply_follow_obligation": bool(reply)}


class RightBrainPipelineShadowV61HarnessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.prereg = json.loads(
            PREREG_PATH.read_text(encoding="utf-8")
        )
        cls.lock = json.loads(
            LOCK_PATH.read_text(encoding="utf-8")
        )
        cls.runner_source = (
            ROOT / cls.lock["frozen_artifacts"]["runner"]["path"]
        ).read_text(encoding="utf-8")
        cls.analyzer_source = (
            ROOT / cls.lock["frozen_artifacts"]["analyzer"]["path"]
        ).read_text(encoding="utf-8")

    def test_every_harness_artifact_is_hash_bound(self):
        for name, artifact in self.lock["frozen_artifacts"].items():
            self.assertEqual(
                _sha256(ROOT / artifact["path"]),
                artifact["sha256"],
                name,
            )

    def test_conditions_and_call_budget_are_frozen(self):
        self.assertEqual(
            tuple(self.lock["conditions"]),
            runner.CONDITIONS,
        )
        self.assertEqual(
            self.lock["formal_run"][
                "logical_model_call_count_exact"
            ],
            60,
        )
        self.assertEqual(
            self.lock["formal_run"][
                "transport_attempt_count_exact"
            ],
            60,
        )
        self.assertEqual(
            self.lock["formal_run"]["required_run_branch"],
            "main",
        )

    def test_runner_freezes_plan_before_any_candidate_loop(self):
        capture_guard = (
            'if len(captures) != len(cases):'
        )
        candidate_loop = "for condition in MODEL_CONDITIONS:"
        self.assertIn(capture_guard, self.runner_source)
        self.assertIn(candidate_loop, self.runner_source)
        self.assertLess(
            self.runner_source.index(capture_guard),
            self.runner_source.rindex(candidate_loop),
        )
        self.assertIn(
            '"shared_plan_sha256": captured["shared_plan_sha256"]',
            self.runner_source,
        )
        self.assertIn(
            '"gold_or_expected_outcome_passed_to_model": False',
            self.runner_source,
        )

    def test_runner_has_one_attempt_and_no_model_retry_loop(self):
        call_source = self.runner_source[
            self.runner_source.index("def _call_ollama_once"):
            self.runner_source.index("def _chat_body")
        ]
        self.assertNotIn("for attempt", call_source)
        self.assertIn('"transport_attempts": 1', call_source)
        self.assertIn(
            '"transport_attempt_count": sum(',
            self.runner_source,
        )

    def test_runner_isolates_memory_and_disables_actions(self):
        for required in (
            "brain_module.DB_PATH = str(startup_path)",
            'bot.reset_session(db_path=str(temporary_path))',
            '"production_database_opened": False',
            '"production_memory_write_count": 0',
            '"physical_vrm_action_count": 0',
        ):
            self.assertIn(required, self.runner_source)

    def test_scoring_keeps_holdout_gold_outside_model_payload(self):
        brain = _FakeBrain()
        case = {
            "user_input": "入力",
            "maximum_reply_chars": 50,
            "required_meaning_propositions": [
                {
                    "id": "required",
                    "description": "必要を含む",
                    "accepted_surfaces": ["必要"],
                }
            ],
            "forbidden_meaning_propositions": [
                {
                    "id": "forbidden",
                    "description": "秘密を含めない",
                    "accepted_surfaces": ["秘密"],
                }
            ],
            "private_memory_terms": ["秘密"],
        }
        score = runner._score_reply(
            brain,
            case,
            {},
            "必要だけ答える",
        )
        self.assertTrue(score["semantic_contract_pass"])
        self.assertTrue(score["required_meaning_pass"])
        self.assertEqual(
            score["forbidden_meaning_hit_count"],
            0,
        )
        self.assertFalse(score["private_memory_intrusion"])

    def test_failed_raw_candidate_falls_back_without_retry(self):
        brain = _FakeBrain()
        case = {
            "id": "synthetic",
            "scenario_family": "synthetic",
            "user_input": "入力",
            "maximum_reply_chars": 50,
            "required_meaning_propositions": [
                {
                    "id": "required",
                    "description": "必要",
                    "accepted_surfaces": ["必要"],
                }
            ],
            "forbidden_meaning_propositions": [],
            "private_memory_terms": [],
        }
        captured = {
            "logic": {},
            "memory_data": {},
            "model_payload": "{}",
            "model_payload_sha256": "payload",
            "shared_plan_sha256": "plan",
            "psyche_state": {"mood": 0, "trust": 50},
            "deterministic_control": {
                "runtime": {"final_reply": "必要な返事"}
            },
        }
        calls = []

        def one_call(_body):
            calls.append(True)
            return {
                "response": {
                    "message": {"content": "意味なし"}
                },
                "wall_seconds": 0.1,
                "transport_attempts": 1,
                "transport_error": None,
            }

        prereg = {
            "generation": {
                "temperature": 0.2,
                "top_p": 0.85,
                "top_k": 40,
                "repeat_penalty": 1.12,
                "seed": 1,
                "context_tokens": 4096,
                "maximum_output_tokens": 96,
            }
        }
        model = {
            "ollama_tag": "fake",
            "digest": "digest",
            "thinking": False,
        }
        original_peak = runner._peak_ollama_rss_bytes
        runner._peak_ollama_rss_bytes = lambda: 1
        try:
            result = runner._run_model_condition(
                brain,
                prereg,
                case,
                captured,
                runner.T1,
                model,
                call_fn=one_call,
            )
        finally:
            runner._peak_ollama_rss_bytes = original_peak
        self.assertEqual(len(calls), 1)
        self.assertFalse(
            result["strict_takeover_before_self_monitor"]
        )
        self.assertEqual(
            result["runtime"]["final_reply"],
            "必要な返事",
        )

    def test_paired_statistics_are_directional_and_deterministic(self):
        control = [False, False, True, True]
        candidate = [True, False, True, False]
        counts = analyzer._paired_counts(control, candidate)
        self.assertEqual(counts["candidate_fixes"], 1)
        self.assertEqual(counts["candidate_regressions"], 1)
        first = analyzer._bootstrap_delta(
            control,
            candidate,
            7,
            100,
        )
        second = analyzer._bootstrap_delta(
            control,
            candidate,
            7,
            100,
        )
        self.assertEqual(first, second)

    def test_full_analyzer_rejects_synthetic_no_gain_without_crashing(self):
        dataset = json.loads(
            (
                ROOT
                / "datasets"
                / "rightbrain_pipeline_shadow_v61.json"
            ).read_text(encoding="utf-8")
        )

        def score(reply):
            return {
                "reply": reply,
                "character_count": len(reply),
                "semantic_groups": [{"markers": ["必要"], "hit": True}],
                "semantic_group_hit_count": 1,
                "semantic_group_count": 1,
                "semantic_contract_pass": True,
                "required_meaning_propositions": [
                    {"id": "required", "hit": True}
                ],
                "required_meaning_hit_count": 1,
                "required_meaning_count": 1,
                "required_meaning_pass": True,
                "forbidden_meaning_propositions": [],
                "forbidden_meaning_hit_count": 0,
                "private_memory_hits": [],
                "private_memory_intrusion": False,
                "current_gate_rejection_reasons": [],
                "current_gate_pass": True,
                "normalized_reply": reply,
            }

        def runtime(reply):
            monitor = {"needs_repair": False, "issues": []}
            return {
                "initial_reply": reply,
                "final_reply": reply,
                "self_monitor_before": monitor,
                "self_monitor_after": monitor,
                "post_check": {"did_reply_follow_obligation": True},
                "repair_changed_reply": False,
            }

        captures = []
        model_rows = []
        calls = []
        for case in dataset["cases"]:
            plan_hash = f"plan-{case['id']}"
            payload = "{}"
            payload_hash = hashlib.sha256(payload.encode()).hexdigest()
            captures.append(
                {
                    "case_id": case["id"],
                    "scenario_family": case["scenario_family"],
                    "shared_plan_sha256": plan_hash,
                    "temporary_database": True,
                    "production_database_opened": False,
                    "retrieved_fixture_ids": [
                        item["id"] for item in case["memory_fixture"]
                    ],
                    "expected_fixture_ids": [
                        item["id"] for item in case["memory_fixture"]
                    ],
                    "model_payload": payload,
                    "model_payload_sha256": payload_hash,
                    "deterministic_control": {
                        "runtime": runtime("必要"),
                        "score": score("必要"),
                    },
                }
            )
            for condition in (runner.C1, runner.T1):
                row = {
                    "case_id": case["id"],
                    "scenario_family": case["scenario_family"],
                    "condition": condition,
                    "shared_plan_sha256": plan_hash,
                    "model_payload_sha256": payload_hash,
                    "transport_attempts": 1,
                    "transport_error": None,
                    "generation_metrics": {"wall_seconds": 0.1},
                    "peak_ollama_rss_bytes": 1,
                    "raw_score": score("必要"),
                    "strict_takeover_before_self_monitor": True,
                    "model_takeover": True,
                    "runtime": runtime("必要"),
                    "final_score": score("必要"),
                }
                model_rows.append(row)
                frozen = self.prereg["conditions"][condition]
                calls.append(
                    {
                        "case_id": case["id"],
                        "condition": condition,
                        "transport_attempts": 1,
                        "transport_error": None,
                        "model": frozen["ollama_tag"],
                    }
                )

        raw = {
            "experiment_id": self.prereg["experiment_id"],
            "runner_branch": "main",
            "conditions": list(runner.CONDITIONS),
            "captures": captures,
            "model_rows": model_rows,
            "logical_model_calls": calls,
            "logical_model_call_count": 60,
            "transport_attempt_count": 60,
            "transport_error_count": 0,
            "production_memory_write_count": 0,
            "physical_vrm_action_count": 0,
            "gold_or_expected_outcome_passed_to_model": False,
            "database_isolation": {
                "production_database_opened": False,
                "production_database_writes": 0,
            },
            "inflight_request_at_completion": None,
            "preflight": {"passed": True},
            "harness_lock_sha256": _sha256(LOCK_PATH),
            "system_prompt_sha256": self.lock["environment"][
                "rightbrain_system_prompt_sha256"
            ],
            "ollama_version": self.lock["environment"]["ollama_version"],
            "frozen_artifact_hashes": {
                name: artifact["sha256"]
                for name, artifact in self.lock["frozen_artifacts"].items()
            },
            "model_snapshots": {
                condition: {
                    "ollama_tag": self.prereg["conditions"][condition][
                        "ollama_tag"
                    ],
                    "digest": self.prereg["conditions"][condition]["digest"],
                }
                for condition in (runner.C1, runner.T1)
            },
        }
        report = analyzer.analyze(
            raw,
            dataset,
            self.prereg,
            self.lock,
        )
        self.assertTrue(all(report["artifact_checks"].values()))
        self.assertFalse(report["automatic_gates"]["passed"])
        self.assertIn(
            "t1_raw_semantic_delta_vs_c1_at_least",
            report["automatic_gates"]["failed_checks"],
        )

    def test_analyzer_contains_every_preregistered_gate(self):
        for gate in self.prereg["automatic_advance_gates"]:
            self.assertIn(f'"{gate}"', self.analyzer_source)

    def test_result_did_not_exist_when_harness_was_frozen(self):
        result_path = (
            ROOT / self.lock["result_artifacts"]["raw"]
        )
        if not result_path.exists():
            self.assertFalse(result_path.exists())
            return
        freeze_commit = subprocess.check_output(
            [
                "git",
                "log",
                "--diff-filter=A",
                "--format=%H",
                "-1",
                "--",
                str(LOCK_PATH.relative_to(ROOT)),
            ],
            cwd=ROOT,
            text=True,
        ).strip()
        historical_result = subprocess.run(
            [
                "git",
                "cat-file",
                "-e",
                f"{freeze_commit}:{result_path.relative_to(ROOT)}",
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
        )
        self.assertNotEqual(historical_result.returncode, 0)

    def test_harness_authorizes_no_runtime_or_broad_claim(self):
        for key in (
            "post_run_case_editing_authorized",
            "post_run_threshold_change_authorized",
            "runtime_shadow_authorized",
            "production_rightbrain_replacement_authorized",
            "human_blind_review_authorized_before_gate",
            "broad_human_likeness_claim_authorized",
        ):
            self.assertFalse(self.lock[key], key)


if __name__ == "__main__":
    unittest.main()
