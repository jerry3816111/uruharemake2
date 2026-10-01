from __future__ import annotations

from copy import deepcopy
import inspect
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import threading
import unittest
from unittest import mock

import m56_3_lease_gated_generation_runner as runner_m56
import m56_7_mac_full_sync_generation as durable_m56
import m57_1_preoutcome_diagnostic_commitment as commitment_m57
import m57_2_component_prediction_capsule as component
import m57_component_error_localization as localization
from test_m56_9_single_writer_formal_scoring import materialize_scoring_run
from test_m56_10_crash_safe_outcome_join import m5610_private_roots


ROOT = Path(__file__).resolve().parent


def prepare_forged(root: Path, run_id: str) -> tuple[Path, dict, dict]:
    run_root = materialize_scoring_run(root, run_id)
    commitment_m57.commit_m57_preoutcome_diagnostic_mode(run_id)
    context = component._load_preoutcome_context(run_id)
    manifest = component.build_forged_engineering_evidence_manifest(run_id, context)
    durable_m56._durable_atomic_write_json(
        run_root / "generation" / component.EVIDENCE_FILENAME,
        manifest,
        exclusive=True,
    )
    return run_root, context, manifest


def rehash_stage(manifest: dict, row_index: int, stage_id: str) -> None:
    stage = manifest["rows"][row_index]["stage_evidence"][stage_id]
    stage.pop("evidence_hash", None)
    stage["evidence_hash"] = component.digest(stage)
    row = manifest["rows"][row_index]
    row.pop("row_hash", None)
    row["row_hash"] = component.digest(row)
    manifest.pop("manifest_hash", None)
    manifest["manifest_hash"] = component.digest(manifest)


class M572ComponentPredictionCapsuleTests(unittest.TestCase):
    def test_contract_and_public_api_are_frozen_and_injection_free(self):
        report = component.validate_contract()
        self.assertTrue(report["valid"], report["errors"])
        self.assertEqual(report["binding_count"], 6)
        self.assertEqual(
            list(inspect.signature(component.execute_m57_preoutcome_component_predictions).parameters),
            ["run_id"],
        )
        self.assertEqual(
            list(inspect.signature(component.validate_m57_preoutcome_component_predictions).parameters),
            ["run_id"],
        )

    def test_live_state_is_explicitly_denied_and_empty(self):
        audit = component.build_live_audit()
        self.assertTrue(audit["contract_valid"])
        self.assertEqual(audit["counts"]["v7_slots_by_ledger"], [0, 0])
        self.assertEqual(audit["counts"]["real_temporal_rows"], 0)
        self.assertEqual(audit["live_component_evidence_manifests"], 0)
        self.assertEqual(audit["live_component_prediction_capsules"], 0)
        self.assertFalse(audit["formal_m57_execution_authorized"])
        self.assertEqual(audit["formal_model_call_count"], 0)
        self.assertEqual(audit["target_outcome_access_count"], 0)

    def test_forged_manifest_has_thirty_source_bound_rows_and_ninety_available_predictions(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            run_id = "m572-forged-manifest"
            with m5610_private_roots(root):
                _, context, manifest = prepare_forged(root, run_id)
                accepted = component.validate_evidence_manifest(
                    manifest, run_id, context, allow_forged=True
                )
                formal = component.validate_evidence_manifest(
                    manifest, run_id, context, allow_forged=False
                )
            self.assertTrue(accepted["valid"], accepted["errors"])
            self.assertEqual(accepted["available_prediction_count"], 90)
            self.assertFalse(formal["valid"])
            self.assertIn("manifest.author_constructed_not_formal", formal["errors"])
            self.assertEqual(len(manifest["rows"]), 30)
            for row in manifest["rows"]:
                self.assertEqual(tuple(row["stage_evidence"]), localization.STAGE_IDS)
                self.assertEqual(row["stage_evidence"]["decision"]["availability"], "unavailable")
                self.assertEqual(row["stage_evidence"]["realization"]["availability"], "unavailable")

    def test_schedule_has_exact_order_and_is_committed_before_first_call(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            run_id = "m572-schedule-before-call"
            with m5610_private_roots(root):
                run_root, _, _ = prepare_forged(root, run_id)
                observations: list[bool] = []

                def assert_schedule(*args, **kwargs):
                    observations.append((run_root / "generation" / component.SCHEDULE_FILENAME).is_file())
                    return component._mock_ollama_call(*args, **kwargs)

                with mock.patch.object(runner_m56, "_ollama_generate", side_effect=assert_schedule):
                    result = component._execute(run_id, allow_forged=True)
                validated = component._validate_m57_preoutcome_component_predictions(
                    run_id, allow_forged=True
                )
                schedule = component.load_json(run_root / "generation" / component.SCHEDULE_FILENAME)
            self.assertEqual(result["model_call_count"], 90)
            self.assertEqual(len(observations), 90)
            self.assertTrue(all(observations))
            self.assertTrue(validated["valid"], validated["errors"])
            self.assertEqual(len(schedule["steps"]), 150)
            self.assertEqual(schedule["required_model_call_count"], 90)
            self.assertEqual(schedule["target_outcome_access_count"], 0)
            self.assertEqual(
                [(row["sample_id"], row["stage_id"]) for row in schedule["steps"][:5]],
                [("forged-runner-no-human-01", stage_id) for stage_id in localization.STAGE_IDS],
            )

    def test_each_intervention_removes_only_the_named_component_and_downstream_artifacts(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            run_id = "m572-intervention-views"
            with m5610_private_roots(root):
                _, context, manifest = prepare_forged(root, run_id)
                sample_id = component._sample_order(context["rows"])[5]
                task = component._ours_task_map(context["rows"])[sample_id]
                artifact = component._artifact_map(context["rows"])[sample_id]
                evidence = next(row for row in manifest["rows"] if row["sample_id"] == sample_id)["stage_evidence"]
                views = {
                    stage_id: component._intervention_view(task, artifact, evidence[stage_id])
                    for stage_id in component.PREOUTCOME_STAGES
                }

            perception = views["perception"]["downstream_recomputation"]
            self.assertNotIn("current_pre_cutoff_event", perception["source_information_without_replaced_input"])
            self.assertIn("unchanged_fit_artifact", perception)
            self.assertEqual(
                perception["removed_for_downstream_recomputation"],
                ["state_snapshot", "transition_trace", "decision"],
            )

            retrieval = views["retrieval"]["downstream_recomputation"]
            selected = set(retrieval["replacement_retrieval_annotation"]["selected_history_ids"])
            visible = {
                row["history_id"]
                for row in retrieval["source_information_with_substituted_history"]["all_pre_cutoff_history"]
            }
            self.assertEqual(visible, selected)
            self.assertEqual(
                retrieval["removed_for_downstream_recomputation"],
                ["fit_artifact", "state_snapshot", "transition_trace", "decision"],
            )

            state = views["state"]["downstream_recomputation"]
            self.assertIn("unchanged_source_information", state)
            self.assertIn("unchanged_fit_artifact", state)
            self.assertNotIn("state_snapshot", state)
            self.assertEqual(
                state["removed_for_downstream_recomputation"],
                ["state_snapshot", "transition_trace", "decision"],
            )
            self.assertTrue(all(not component._find_keys(view) for view in views.values()))

    def test_public_formal_path_rejects_author_constructed_manifest_before_schedule_or_call(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            run_id = "m572-public-rejects-forged"
            with m5610_private_roots(root):
                run_root, _, _ = prepare_forged(root, run_id)
                with mock.patch.object(runner_m56, "_ollama_generate") as provider:
                    with self.assertRaisesRegex(PermissionError, "author_constructed_not_formal"):
                        component.execute_m57_preoutcome_component_predictions(run_id)
                self.assertEqual(provider.call_count, 0)
                self.assertFalse((run_root / "generation" / component.SCHEDULE_FILENAME).exists())

    def test_public_validator_does_not_return_forged_capsule_as_valid(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            run_id = "m572-public-validator-rejects-forged"
            with m5610_private_roots(root):
                prepare_forged(root, run_id)
                with mock.patch.object(runner_m56, "_ollama_generate", side_effect=component._mock_ollama_call):
                    component._execute(run_id, allow_forged=True)
                internal = component._validate_m57_preoutcome_component_predictions(
                    run_id, allow_forged=True
                )
                public = component.validate_m57_preoutcome_component_predictions(run_id)
            self.assertTrue(internal["valid"], internal["errors"])
            self.assertFalse(public["valid"])
            self.assertIn(
                "evidence:manifest.author_constructed_not_formal",
                public["errors"],
            )

    def test_dependency_drift_missing_run_and_missing_m571_fail_closed(self):
        contract = component.load_contract()
        contract["frozen_dependencies"]["m57_1_preoutcome_diagnostic_commitment.py"] = "0" * 64
        report = component.validate_contract(contract)
        self.assertFalse(report["valid"])
        self.assertIn("dependency:m57_1_preoutcome_diagnostic_commitment.py", report["errors"])
        with TemporaryDirectory() as temp:
            root = Path(temp)
            with m5610_private_roots(root):
                with self.assertRaises((PermissionError, ValueError)):
                    component.execute_m57_preoutcome_component_predictions("../escape")
                with self.assertRaises(PermissionError):
                    component.execute_m57_preoutcome_component_predictions("missing-m572-run")
                run_id = "m572-missing-m571"
                materialize_scoring_run(root, run_id)
                with self.assertRaisesRegex(PermissionError, "M57.1"):
                    component._execute(run_id, allow_forged=True)

    def test_manifest_mutations_fail_closed(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            run_id = "m572-manifest-mutations"
            with m5610_private_roots(root):
                _, context, manifest = prepare_forged(root, run_id)
                cases = []

                duplicate = deepcopy(manifest)
                duplicate["rows"][1]["sample_id"] = duplicate["rows"][0]["sample_id"]
                duplicate["rows"][1].pop("row_hash")
                duplicate["rows"][1]["row_hash"] = component.digest(duplicate["rows"][1])
                duplicate.pop("manifest_hash")
                duplicate["manifest_hash"] = component.digest(duplicate)
                cases.append(duplicate)

                post_cutoff = deepcopy(manifest)
                payload = post_cutoff["rows"][0]["stage_evidence"]["retrieval"]["resolved_payload"]
                payload["selected_history_ids"] = ["future-history"]
                post_cutoff["rows"][0]["stage_evidence"]["retrieval"]["adjudication"]["replacement_payload"] = deepcopy(payload)
                rehash_stage(post_cutoff, 0, "retrieval")
                cases.append(post_cutoff)

                same_coder = deepcopy(manifest)
                stage = same_coder["rows"][0]["stage_evidence"]["perception"]
                stage["contributions"][1]["contributor_id"] = stage["contributions"][0]["contributor_id"]
                contribution = stage["contributions"][1]
                contribution.pop("contribution_hash")
                contribution["contribution_hash"] = component.digest(contribution)
                rehash_stage(same_coder, 0, "perception")
                cases.append(same_coder)

                adjudicator_is_coder = deepcopy(manifest)
                stage = adjudicator_is_coder["rows"][0]["stage_evidence"]["perception"]
                stage["adjudication"]["adjudicator_id"] = stage["contributions"][0]["contributor_id"]
                adjudication = stage["adjudication"]
                adjudication.pop("adjudication_hash")
                adjudication["adjudication_hash"] = component.digest(adjudication)
                rehash_stage(adjudicator_is_coder, 0, "perception")
                cases.append(adjudicator_is_coder)

                private_state = deepcopy(manifest)
                stage = private_state["rows"][0]["stage_evidence"]["state"]
                stage["resolved_payload"]["observable_proxy_variables"]["transient_state"] = {"invented": True}
                stage["contributions"][0]["payload"] = deepcopy(stage["resolved_payload"])
                contribution = stage["contributions"][0]
                contribution.pop("contribution_hash")
                contribution["contribution_hash"] = component.digest(contribution)
                rehash_stage(private_state, 0, "state")
                cases.append(private_state)

                forbidden = deepcopy(manifest)
                forbidden["rows"][0]["stage_evidence"]["perception"]["resolved_payload"]["answer_key"] = "hidden"
                rehash_stage(forbidden, 0, "perception")
                cases.append(forbidden)

                decision = deepcopy(manifest)
                decision_stage = decision["rows"][0]["stage_evidence"]["decision"]
                decision_stage["availability"] = "available"
                rehash_stage(decision, 0, "decision")
                cases.append(decision)

                source = deepcopy(manifest)
                source["rows"][0]["source_information_hash"] = "0" * 64
                source["rows"][0].pop("row_hash")
                source["rows"][0]["row_hash"] = component.digest(source["rows"][0])
                source.pop("manifest_hash")
                source["manifest_hash"] = component.digest(source)
                cases.append(source)

                reports = [
                    component.validate_evidence_manifest(case, run_id, context, allow_forged=True)
                    for case in cases
                ]
            self.assertEqual(len(reports), 8)
            self.assertTrue(all(not report["valid"] for report in reports))

    def test_outcome_marker_prevents_first_execution_before_schedule_and_calls(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            run_id = "m572-outcome-marker"
            with m5610_private_roots(root):
                run_root, _, _ = prepare_forged(root, run_id)
                marker = run_root / "telemetry" / component.crash_safe_m56.MODE_FILENAME
                marker.write_text("{}", encoding="utf-8")
                with mock.patch.object(runner_m56, "_ollama_generate") as provider:
                    with self.assertRaisesRegex(PermissionError, "outcome state"):
                        component._execute(run_id, allow_forged=True)
                self.assertEqual(provider.call_count, 0)
                self.assertFalse((run_root / "generation" / component.SCHEDULE_FILENAME).exists())

    def test_failed_call_is_terminal_and_same_run_cannot_retry(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            run_id = "m572-terminal-no-retry"
            with m5610_private_roots(root):
                run_root, _, _ = prepare_forged(root, run_id)
                with mock.patch.object(runner_m56, "_ollama_generate", side_effect=RuntimeError("transport")):
                    with self.assertRaises(RuntimeError):
                        component._execute(run_id, allow_forged=True)
                failure = run_root / "telemetry" / component.FAILURE_FILENAME
                self.assertTrue(failure.is_file())
                with mock.patch.object(runner_m56, "_ollama_generate") as provider:
                    with self.assertRaisesRegex(FileExistsError, "already attempted"):
                        component._execute(run_id, allow_forged=True)
                self.assertEqual(provider.call_count, 0)

    def test_model_identity_token_budget_and_distribution_gates_are_terminal(self):
        mutators = {
            "identity": lambda call: call.update(model_reported="different-model"),
            "token_budget": lambda call: call.update(prompt_tokens=9000),
            "distribution": lambda call: call["parsed"]["probabilities"].update(
                {next(iter(call["parsed"]["probabilities"])): 0.9}
            ),
        }
        for case_name, mutate in mutators.items():
            with self.subTest(case_name=case_name), TemporaryDirectory() as temp:
                root = Path(temp)
                run_id = f"m572-gate-{case_name}"
                with m5610_private_roots(root):
                    run_root, _, _ = prepare_forged(root, run_id)

                    def bad_call(*args, **kwargs):
                        call = component._mock_ollama_call(*args, **kwargs)
                        mutate(call)
                        return call

                    with mock.patch.object(runner_m56, "_ollama_generate", side_effect=bad_call):
                        with self.assertRaises(ValueError):
                            component._execute(run_id, allow_forged=True)
                    self.assertTrue((run_root / "telemetry" / component.FAILURE_FILENAME).is_file())
                    self.assertFalse((run_root / "commitments" / component.COMMITMENT_FILENAME).exists())

    def test_shared_lock_prevents_outcome_join_while_component_predictions_are_running(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            run_id = "m572-shared-lock"
            with m5610_private_roots(root):
                prepare_forged(root, run_id)
                entered = threading.Event()
                release = threading.Event()
                owner_errors: list[BaseException] = []
                calls = {"count": 0}

                def held_call(*args, **kwargs):
                    calls["count"] += 1
                    if calls["count"] == 1:
                        entered.set()
                        if not release.wait(timeout=10):
                            raise TimeoutError("test did not release component runner")
                    return component._mock_ollama_call(*args, **kwargs)

                def owner():
                    try:
                        component._execute(run_id, allow_forged=True)
                    except BaseException as exc:  # pragma: no cover - asserted below
                        owner_errors.append(exc)

                with mock.patch.object(runner_m56, "_ollama_generate", side_effect=held_call):
                    thread = threading.Thread(target=owner)
                    thread.start()
                    self.assertTrue(entered.wait(timeout=10))
                    with self.assertRaisesRegex(PermissionError, "active local owner"):
                        component.crash_safe_m56.execute_crash_safe_outcome_join_formal_scoring(run_id)
                    release.set()
                    thread.join(timeout=15)
                    self.assertFalse(thread.is_alive())
                self.assertEqual(owner_errors, [])
                self.assertEqual(calls["count"], 90)

    def test_capsule_resource_and_ledger_mutations_fail_closed(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            run_id = "m572-output-mutations"
            with m5610_private_roots(root):
                run_root, context, manifest = prepare_forged(root, run_id)
                with mock.patch.object(runner_m56, "_ollama_generate", side_effect=component._mock_ollama_call):
                    component._execute(run_id, allow_forged=True)
                schedule = component.load_json(run_root / "generation" / component.SCHEDULE_FILENAME)
                capsule = component.load_json(run_root / "generation" / component.CAPSULE_FILENAME)
                ledger = component.load_json(run_root / "telemetry" / component.CALL_LEDGER_FILENAME)

                mutated_capsule = deepcopy(capsule)
                mutated_capsule["provider_options"]["temperature"] = 9
                mutated_capsule.pop("capsule_hash")
                mutated_capsule["capsule_hash"] = component.digest(mutated_capsule)
                capsule_report = component._validate_capsule_and_ledger(
                    mutated_capsule, ledger, run_id, context, manifest, schedule
                )

                mutated_ledger = deepcopy(ledger)
                mutated_ledger["calls"][0]["prompt_hash"] = "0" * 64
                mutated_ledger["calls"][0].pop("call_hash")
                mutated_ledger["calls"][0]["call_hash"] = component.digest(mutated_ledger["calls"][0])
                mutated_ledger.pop("ledger_hash")
                mutated_ledger["ledger_hash"] = component.digest(mutated_ledger)
                ledger_report = component._validate_capsule_and_ledger(
                    capsule, mutated_ledger, run_id, context, manifest, schedule
                )
            self.assertFalse(capsule_report["valid"])
            self.assertTrue(any("resource:provider_options" in error for error in capsule_report["errors"]))
            self.assertFalse(ledger_report["valid"])
            self.assertTrue(any(error.endswith(".binding") for error in ledger_report["errors"]))

    def test_engineering_rehearsal_and_dashboard_are_bounded(self):
        rehearsal = component.build_engineering_rehearsal()
        report = component.validate_rehearsal(rehearsal)
        self.assertTrue(report["valid"], report["errors"])
        self.assertEqual(rehearsal["available_prediction_count"], 90)
        self.assertEqual(rehearsal["mocked_model_call_count"], 90)
        self.assertTrue(rehearsal["public_formal_path_rejected_author_constructed_evidence"])
        self.assertEqual(rehearsal["public_rejection_model_call_count"], 0)
        self.assertEqual(rehearsal["target_outcome_access_count"], 0)
        page = component.render_dashboard(rehearsal, component.build_live_audit())
        self.assertIn("連替換後答案也先封存", page)
        self.assertIn("90 個 predictions", page)
        self.assertIn("FORMAL M57 DENIED", page)
        self.assertIn("M58 denied", page)

    def test_frozen_m57_analyzer_and_m571_behavior_remain_unchanged(self):
        clear = localization.analyze_component_substitution_bundle(localization.build_synthetic_bundle())
        tied = localization.analyze_component_substitution_bundle(
            localization.build_synthetic_bundle(ambiguous_tie=True)
        )
        self.assertEqual(clear["leading_recoverable_stage"], "retrieval")
        self.assertIsNone(tied["leading_recoverable_stage"])
        self.assertFalse(clear["formal_result_created"])
        self.assertTrue(commitment_m57.validate_contract()["valid"])

    def test_saved_rehearsal_and_implementation_freeze_match_files(self):
        saved = component.load_saved_rehearsal()
        self.assertTrue(component.validate_rehearsal(saved)["valid"])
        freeze_path = ROOT / "research/m57_2_component_prediction_capsule_implementation_freeze_2026-09-04.json"
        freeze = component.load_json(freeze_path)
        self.assertEqual(
            freeze["schema"],
            "uruha_m57_2_component_prediction_capsule_implementation_freeze_v1",
        )
        self.assertEqual(
            freeze["status"],
            "implementation_frozen_after_engineering_acceptance_before_any_real_m56_target_outcome_access",
        )
        for relative, expected_hash in freeze["files"].items():
            self.assertEqual(component.sha256_file(ROOT / relative), expected_hash)


if __name__ == "__main__":
    unittest.main()
