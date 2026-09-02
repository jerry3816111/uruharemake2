from __future__ import annotations

from contextlib import ExitStack
from copy import deepcopy
from hashlib import sha256
import inspect
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest import mock

import m56_2_real_data_activation_envelope as activation
import m56_3_lease_gated_generation_runner as runner
import m56_4_separate_formal_scorer as scorer
import m56_5_crash_safe_no_retry_continuation as continuation
from test_m56_3_lease_gated_generation_runner import mechanics


ROOT = Path(__file__).resolve().parent


class SimulatedPowerLoss(BaseException):
    pass


class DeterministicProvider:
    def __init__(self) -> None:
        self.call_count = 0
        self.prompt_hashes: list[str] = []

    def __call__(self, prompt: str, output_schema: dict, options: dict) -> dict:
        del options
        self.call_count += 1
        prompt_digest = sha256(prompt.encode("utf-8")).hexdigest()
        self.prompt_hashes.append(prompt_digest)
        properties = output_schema.get("properties") or {}
        if set(properties) == {"summary_text"}:
            parsed = {"summary_text": f"Deterministic summary {self.call_count}."}
        else:
            labels = list(((properties.get("probabilities") or {}).get("properties") or {}))
            weights = {label: float(index + 1) for index, label in enumerate(labels)}
            total = sum(weights.values())
            parsed = {
                "probabilities": {label: value / total for label, value in weights.items()},
                "authorized_evidence_ids": [],
                "brief_evidence": "Checkpoint mechanics fixture; no human provenance.",
            }
        raw_digest = sha256(f"mock-call-{self.call_count}:{prompt_digest}".encode("utf-8")).hexdigest()
        return {
            "parsed": parsed,
            "raw_response_hash": raw_digest,
            "prompt_tokens": 128,
            "completion_tokens": 20,
            "latency_seconds": 0.01,
            "process_cpu_seconds": 0.001,
            "process_peak_rss_bytes": 1024,
            "ollama_rss_bytes": 2048,
            "total_duration_ns": 10,
            "load_duration_ns": 1,
            "prompt_eval_duration_ns": 4,
            "eval_duration_ns": 5,
            "model_reported": "qwen3.5:9b",
            "transport_attempt_count": 1,
            "retry_count": 0,
            "fallback_count": 0,
        }


def write_json(path: Path, value: dict) -> None:
    runner._atomic_write_json(path, value, exclusive=True)


def materialize_run(private_root: Path, run_id: str) -> dict:
    rows = mechanics(run_id)
    root = private_root / run_id
    generation = root / "generation"
    commitments = root / "commitments"
    telemetry = root / "telemetry"
    scoring_dir = root / "scoring"
    for directory in (generation, commitments, telemetry, scoring_dir):
        directory.mkdir(parents=True, exist_ok=True)
    write_json(commitments / "activation_request.json", rows["request"])
    write_json(commitments / activation.FORMAL_RECEIPT_FILENAME, rows["receipt"])
    write_json(commitments / activation.FORMAL_LEASE_FILENAME, rows["lease"])
    write_json(generation / "prediction_packet.json", rows["packet"])
    write_json(generation / "run_manifest.json", rows["manifest"])
    write_json(generation / "execution_capsule.json", rows["capsule"])
    write_json(generation / "equation_artifacts.json", rows["bundle"])
    write_json(generation / "runtime_snapshot.json", rows["snapshot"])
    sentinel = {
        "private_outcome_sentinel": "must-not-be-read-or-mutated-by-generation",
        "sentinel_hash": "9" * 64,
    }
    write_json(scoring_dir / "private_outcome_sentinel.json", sentinel)
    return rows


class private_roots:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.stack = ExitStack()

    def __enter__(self):
        self.stack.enter_context(mock.patch.object(continuation, "PRIVATE_ROOT", self.root))
        self.stack.enter_context(mock.patch.object(runner, "PRIVATE_ROOT", self.root))
        return self

    def __exit__(self, exc_type, exc, traceback):
        return self.stack.__exit__(exc_type, exc, traceback)


def load_final(private_root: Path, run_id: str) -> dict[str, dict]:
    root = private_root / run_id
    return {
        "schedule": continuation.load_json(root / "generation" / runner.SCHEDULE_FILENAME),
        "submission": continuation.load_json(root / "generation" / runner.SUBMISSION_FILENAME),
        "ledger": continuation.load_json(root / "telemetry" / runner.CALL_LEDGER_FILENAME),
        "commitment": continuation.load_json(root / "commitments" / runner.COMMITMENT_FILENAME),
        "release": continuation.load_json(root / "commitments" / runner.SCORING_RELEASE_FILENAME),
    }


class M565CrashSafeNoRetryContinuationTests(unittest.TestCase):
    def test_contract_and_frozen_dependencies_validate(self):
        report = continuation.validate_contract()
        self.assertTrue(report["valid"], report["errors"])
        self.assertEqual(report["binding_count"], 6)

    def test_public_execution_accepts_only_run_id(self):
        signature = inspect.signature(continuation.execute_resumable_formal_generation)
        self.assertEqual(list(signature.parameters), ["run_id"])

    def test_current_live_state_is_denied_and_zero(self):
        audit = continuation.build_live_audit()
        self.assertEqual(audit["counts"]["v7_slots_by_ledger"], [0, 0])
        self.assertEqual(audit["counts"]["real_temporal_rows"], 0)
        self.assertFalse(audit["formal_generation_authorized"])
        self.assertEqual(audit["formal_model_calls"], 0)
        self.assertEqual(audit["generation_target_outcome_access_count"], 0)
        self.assertFalse(audit["formal_result_created"])

    def test_missing_live_run_fails_without_creating_directory(self):
        with TemporaryDirectory() as temp:
            private_root = Path(temp)
            run_id = "missing-human-authorized-run"
            with private_roots(private_root):
                with self.assertRaises(FileNotFoundError):
                    continuation.execute_resumable_formal_generation(run_id)
            self.assertFalse((private_root / run_id).exists())

    def test_resumed_run_reuses_completed_steps_without_extra_model_calls(self):
        with TemporaryDirectory() as temp:
            private_root = Path(temp)
            resumed_id = "forged-resumed-no-human"
            uninterrupted_id = "forged-uninterrupted-no-human"
            resumed_rows = materialize_run(private_root, resumed_id)
            materialize_run(private_root, uninterrupted_id)
            resumed_provider = DeterministicProvider()
            with private_roots(private_root), mock.patch.object(
                runner, "_ollama_generate", side_effect=resumed_provider
            ), mock.patch.object(
                continuation, "_after_checkpoint_hook",
                side_effect=lambda index: (_ for _ in ()).throw(SimulatedPowerLoss()) if index == 55 else None,
            ):
                with self.assertRaises(SimulatedPowerLoss):
                    continuation.execute_resumable_formal_generation(resumed_id)
            root = private_root / resumed_id
            self.assertFalse((root / "telemetry" / runner.FAILURE_FILENAME).exists())
            first_call_count = resumed_provider.call_count
            self.assertGreater(first_call_count, 0)
            with private_roots(private_root), mock.patch.object(
                runner, "_ollama_generate", side_effect=resumed_provider
            ):
                resumed_result = continuation.execute_resumable_formal_generation(resumed_id)
            self.assertGreater(resumed_result["reused_completed_step_count"], 0)
            self.assertEqual(resumed_provider.call_count, 180)
            self.assertLess(first_call_count, resumed_provider.call_count)
            uninterrupted_provider = DeterministicProvider()
            with private_roots(private_root), mock.patch.object(
                runner, "_ollama_generate", side_effect=uninterrupted_provider
            ):
                uninterrupted_result = continuation.execute_resumable_formal_generation(uninterrupted_id)
            self.assertEqual(uninterrupted_provider.call_count, 180)
            self.assertEqual(uninterrupted_result["reused_completed_step_count"], 0)
            resumed = load_final(private_root, resumed_id)
            uninterrupted = load_final(private_root, uninterrupted_id)
            self.assertEqual(resumed["submission"]["summary_artifacts"], uninterrupted["submission"]["summary_artifacts"])
            self.assertEqual(resumed["submission"]["prediction_rows"], uninterrupted["submission"]["prediction_rows"])
            self.assertEqual(resumed["ledger"]["calls"], uninterrupted["ledger"]["calls"])
            submission_report = runner.validate_formal_submission(
                resumed["submission"], resumed["schedule"], resumed_rows["packet"], resumed_rows["manifest"],
                resumed_rows["capsule"], resumed_rows["bundle"], resumed_rows["lease"],
            )
            self.assertTrue(submission_report["valid"], submission_report["errors"])
            scorer_rows = {
                **resumed_rows,
                "schedule": resumed["schedule"],
                "submission": resumed["submission"],
                "commitment": resumed["commitment"],
                "release": resumed["release"],
                "call_ledger": resumed["ledger"],
            }
            prescore = scorer.validate_prescore_inputs(resumed_id, scorer_rows)
            self.assertTrue(prescore["valid"], prescore["errors"])
            self.assertEqual(prescore["generation_target_outcome_access_count"], 0)
            sentinel = continuation.load_json(root / "scoring" / "private_outcome_sentinel.json")
            self.assertEqual(sentinel["private_outcome_sentinel"], "must-not-be-read-or-mutated-by-generation")

    def test_identical_call_after_completion_is_validation_only(self):
        with TemporaryDirectory() as temp:
            private_root = Path(temp)
            run_id = "forged-complete-idempotence-no-human"
            materialize_run(private_root, run_id)
            provider = DeterministicProvider()
            with private_roots(private_root), mock.patch.object(runner, "_ollama_generate", side_effect=provider):
                first = continuation.execute_resumable_formal_generation(run_id)
                second = continuation.execute_resumable_formal_generation(run_id)
            self.assertEqual(provider.call_count, 180)
            self.assertEqual(first["submission_hash"], second["submission_hash"])
            self.assertEqual(second["status"], "formal_generation_already_complete_scoring_released")
            self.assertEqual(second["reused_completed_step_count"], 211)

    def test_intent_without_checkpoint_is_terminal_and_never_recalled(self):
        with TemporaryDirectory() as temp:
            private_root = Path(temp)
            run_id = "forged-ambiguous-intent-no-human"
            materialize_run(private_root, run_id)
            provider = DeterministicProvider()
            with private_roots(private_root), mock.patch.object(
                runner, "_ollama_generate", side_effect=provider
            ), mock.patch.object(
                continuation, "_after_intent_hook", side_effect=SimulatedPowerLoss()
            ):
                with self.assertRaises(SimulatedPowerLoss):
                    continuation.execute_resumable_formal_generation(run_id)
            self.assertEqual(provider.call_count, 0)
            with private_roots(private_root), mock.patch.object(runner, "_ollama_generate", side_effect=provider):
                with self.assertRaisesRegex(PermissionError, "ambiguous in-flight"):
                    continuation.execute_resumable_formal_generation(run_id)
            self.assertEqual(provider.call_count, 0)
            failure = continuation.load_json(private_root / run_id / "telemetry" / runner.FAILURE_FILENAME)
            self.assertEqual(failure["status"], "terminal_no_retry_generation_failure")
            self.assertFalse(failure["retry_authorized"])

    def test_checkpoint_plus_intent_after_power_loss_is_reused_without_recall(self):
        with TemporaryDirectory() as temp:
            private_root = Path(temp)
            run_id = "forged-complete-checkpoint-with-intent-no-human"
            materialize_run(private_root, run_id)
            provider = DeterministicProvider()
            with private_roots(private_root), mock.patch.object(
                runner, "_ollama_generate", side_effect=provider
            ), mock.patch.object(
                continuation, "_after_checkpoint_write_before_intent_clear_hook",
                side_effect=SimulatedPowerLoss(),
            ):
                with self.assertRaises(SimulatedPowerLoss):
                    continuation.execute_resumable_formal_generation(run_id)
            self.assertEqual(provider.call_count, 1)
            root = private_root / run_id
            self.assertFalse((root / "telemetry" / runner.FAILURE_FILENAME).exists())
            intents = list((root / "telemetry" / continuation.CHECKPOINT_DIRECTORY).glob("*.intent.json"))
            self.assertEqual(len(intents), 1)
            with private_roots(private_root), mock.patch.object(runner, "_ollama_generate", side_effect=provider):
                result = continuation.execute_resumable_formal_generation(run_id)
            self.assertEqual(provider.call_count, 180)
            self.assertGreater(result["reused_completed_step_count"], 0)
            self.assertEqual(list((root / "telemetry" / continuation.CHECKPOINT_DIRECTORY).glob("*.intent.json")), [])

    def test_transport_failure_is_terminal_and_cannot_be_retried(self):
        with TemporaryDirectory() as temp:
            private_root = Path(temp)
            run_id = "forged-terminal-transport-no-human"
            materialize_run(private_root, run_id)
            calls = {"count": 0}

            def fail_transport(prompt: str, output_schema: dict, options: dict):
                del prompt, output_schema, options
                calls["count"] += 1
                raise RuntimeError("simulated single transport failure")

            with private_roots(private_root), mock.patch.object(runner, "_ollama_generate", side_effect=fail_transport):
                with self.assertRaisesRegex(RuntimeError, "single transport failure"):
                    continuation.execute_resumable_formal_generation(run_id)
                with self.assertRaisesRegex(PermissionError, "terminal generation failure"):
                    continuation.execute_resumable_formal_generation(run_id)
            self.assertEqual(calls["count"], 1)
            failure = continuation.load_json(private_root / run_id / "telemetry" / runner.FAILURE_FILENAME)
            self.assertEqual(failure["status"], "terminal_no_retry_generation_failure")
            self.assertFalse(failure["retry_authorized"])

    def test_checkpoint_mutation_and_out_of_order_artifact_fail_closed(self):
        with TemporaryDirectory() as temp:
            private_root = Path(temp)
            run_id = "forged-mutated-checkpoint-no-human"
            materialize_run(private_root, run_id)
            provider = DeterministicProvider()
            with private_roots(private_root), mock.patch.object(
                runner, "_ollama_generate", side_effect=provider
            ), mock.patch.object(
                continuation, "_after_checkpoint_hook",
                side_effect=lambda index: (_ for _ in ()).throw(SimulatedPowerLoss()) if index == 55 else None,
            ):
                with self.assertRaises(SimulatedPowerLoss):
                    continuation.execute_resumable_formal_generation(run_id)
            checkpoint_dir = private_root / run_id / "telemetry" / continuation.CHECKPOINT_DIRECTORY
            candidate = next(
                path for path in sorted(checkpoint_dir.glob("*.json"))
                if not path.name.endswith("intent.json")
                and continuation.load_json(path)["result_kind"] == "prediction_row"
                and continuation.load_json(path)["model_call_count"] == 1
            )
            changed = continuation.load_json(candidate)
            changed["result"]["brief_evidence"] = "post-checkpoint mutation"
            candidate.write_text(json.dumps(changed, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            with private_roots(private_root), mock.patch.object(runner, "_ollama_generate", side_effect=provider):
                with self.assertRaisesRegex(ValueError, "checkpoint validation failed"):
                    continuation.execute_resumable_formal_generation(run_id)
            self.assertLess(provider.call_count, 180)
            self.assertTrue((private_root / run_id / "telemetry" / runner.FAILURE_FILENAME).exists())

    def test_existing_schedule_without_mode_commitment_is_not_adopted(self):
        with TemporaryDirectory() as temp:
            private_root = Path(temp)
            run_id = "forged-legacy-ambiguous-no-human"
            rows = materialize_run(private_root, run_id)
            schedule = runner.build_generation_schedule(
                rows["packet"], rows["manifest"], rows["capsule"], rows["bundle"], rows["lease"]["lease_hash"]
            )
            write_json(private_root / run_id / "generation" / runner.SCHEDULE_FILENAME, schedule)
            provider = DeterministicProvider()
            with private_roots(private_root), mock.patch.object(runner, "_ollama_generate", side_effect=provider):
                with self.assertRaisesRegex(PermissionError, "without M56.5"):
                    continuation.execute_resumable_formal_generation(run_id)
            self.assertEqual(provider.call_count, 0)

    def test_unexpected_checkpoint_artifact_fails_before_any_model_call(self):
        with TemporaryDirectory() as temp:
            private_root = Path(temp)
            run_id = "forged-hidden-checkpoint-no-human"
            materialize_run(private_root, run_id)
            provider = DeterministicProvider()
            checkpoint_dir = private_root / run_id / "telemetry" / continuation.CHECKPOINT_DIRECTORY
            checkpoint_dir.mkdir(parents=True)
            (checkpoint_dir / "unscheduled.json").write_text("{}\n", encoding="utf-8")
            with private_roots(private_root), mock.patch.object(runner, "_ollama_generate", side_effect=provider):
                with self.assertRaisesRegex(PermissionError, "unexpected checkpoint artifact"):
                    continuation.execute_resumable_formal_generation(run_id)
            self.assertEqual(provider.call_count, 0)

    def test_checkpoint_forbids_raw_reasoning_outcome_and_excess_authority(self):
        rows = mechanics("forged-checkpoint-boundary-no-human")
        schedule = runner.build_generation_schedule(
            rows["packet"], rows["manifest"], rows["capsule"], rows["bundle"], rows["lease"]["lease_hash"]
        )
        step = next(row for row in schedule["prediction_steps"] if row["condition_id"] == "B0_PRIOR")
        task = next(row for row in rows["capsule"]["prediction_tasks"] if row["task_id"] == step["step_id"])
        run_map = {row["condition_id"]: row for row in rows["manifest"]["condition_runs"]}
        result = runner._deterministic_b0(task, run_map[task["condition_id"]])
        result["raw_response"] = "forbidden"
        with self.assertRaisesRegex(ValueError, "forbidden content"):
            continuation.build_step_checkpoint(
                "forged-checkpoint-boundary-no-human", rows, schedule, step,
                "prediction_row", result, None,
            )

    def test_implementation_freeze_matches_frozen_files(self):
        freeze = continuation.load_json(
            ROOT / "research/m56_5_crash_safe_no_retry_continuation_implementation_freeze_2026-09-02.json"
        )
        self.assertEqual(
            freeze["schema"],
            "uruha_m56_crash_safe_no_retry_continuation_implementation_freeze_v1",
        )
        self.assertEqual(freeze["status"], "frozen_before_any_real_m56_generation_call")
        self.assertEqual(len(freeze["files"]), 4)
        for row in freeze["files"]:
            self.assertEqual(continuation.sha256_file(ROOT / row["path"]), row["sha256"], row["path"])
        evidence = freeze["pre_freeze_evidence"]
        self.assertEqual(evidence["formal_model_calls"], 0)
        self.assertEqual(evidence["target_outcome_access"], 0)
        self.assertFalse(evidence["formal_commitment_created"])
        self.assertFalse(evidence["formal_scoring_release_created"])
        self.assertFalse(evidence["formal_result_created"])

    def test_rehearsal_and_dashboard_are_graphical_read_only_and_honest(self):
        rehearsal = continuation.build_synthetic_rehearsal()
        self.assertEqual(rehearsal["model_call_count"], 0)
        self.assertEqual(rehearsal["target_outcome_access_count"], 0)
        self.assertFalse(rehearsal["formal_generation_authorized"])
        page = continuation.render_dashboard()
        self.assertIn("M56.5", page)
        self.assertIn("中斷後可以安全續跑，但不能重試", page)
        self.assertIn("完整 checkpoint", page)
        self.assertIn("只有 intent", page)
        self.assertIn("0 FORMAL CALLS", page)
        self.assertIn("0/18", page)
        self.assertNotIn("<form", page)
        self.assertNotIn("overflow-x", page)


if __name__ == "__main__":
    unittest.main()
