from __future__ import annotations

from copy import deepcopy
import inspect
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest import mock

import m56_4_separate_formal_scorer as scorer_m56
import m56_7_mac_full_sync_generation as durable_m56
import m56_10_crash_safe_outcome_join as crash_safe_m56
import m57_component_error_localization as localization_m57
import m57_1_preoutcome_diagnostic_commitment as commitment_m57
import m57_2_component_prediction_capsule as component_m57
import m57_3_sanctioned_outcome_analyzer_bridge as bridge
from test_m56_10_crash_safe_outcome_join import m5610_private_roots
from test_m56_9_single_writer_formal_scoring import materialize_scoring_run


ROOT = Path(__file__).resolve().parent


def prepare_full_chain(root: Path, run_id: str) -> Path:
    run_root = materialize_scoring_run(root, run_id)
    commitment_m57.commit_m57_preoutcome_diagnostic_mode(run_id)
    context = component_m57._load_preoutcome_context(run_id)
    evidence = component_m57.build_forged_engineering_evidence_manifest(run_id, context)
    durable_m56._durable_atomic_write_json(
        run_root / "generation" / component_m57.EVIDENCE_FILENAME,
        evidence,
        exclusive=True,
    )
    with mock.patch.object(
        component_m57.runner_m56,
        "_ollama_generate",
        side_effect=component_m57._mock_ollama_call,
    ):
        component_m57._execute(run_id, allow_forged=True)
    crash_safe_m56.execute_crash_safe_outcome_join_formal_scoring(run_id)
    return run_root


def rewrite_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


class M573SanctionedOutcomeAnalyzerBridgeTests(unittest.TestCase):
    def test_contract_and_public_api_are_frozen_and_injection_free(self):
        validation = bridge.validate_contract()
        self.assertTrue(validation["valid"], validation["errors"])
        self.assertEqual(validation["binding_count"], 9)
        self.assertEqual(
            list(inspect.signature(bridge.execute_m57_sanctioned_outcome_analyzer_bridge).parameters),
            ["run_id"],
        )
        self.assertEqual(
            list(inspect.signature(bridge.validate_m57_sanctioned_outcome_analyzer_bridge).parameters),
            ["run_id"],
        )

    def test_live_state_remains_denied_without_human_chain(self):
        audit = bridge.build_live_audit()
        self.assertTrue(audit["contract_valid"])
        self.assertEqual(audit["counts"]["v7_slots_by_ledger"], [0, 0])
        self.assertEqual(audit["counts"]["real_temporal_rows"], 0)
        self.assertFalse(audit["formal_m57_outcome_access_authorized"])
        self.assertFalse(audit["formal_m57_result_created"])
        self.assertEqual(audit["target_outcome_access_count"], 0)
        self.assertFalse(audit["m58_authorized"])

    def test_full_forged_chain_joins_once_replays_without_load_and_remains_nonformal(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            run_id = "m573-full-forged-chain"
            with m5610_private_roots(root):
                prepare_full_chain(root, run_id)
                original = scorer_m56.load_outcome_inputs
                loads = {"count": 0}

                def counted(value: str):
                    loads["count"] += 1
                    return original(value)

                with mock.patch.object(scorer_m56, "load_outcome_inputs", side_effect=counted):
                    first = bridge._execute(run_id, allow_forged=True)
                    replay = bridge._execute(run_id, allow_forged=True)
                validation = bridge._validate_existing(run_id, allow_forged=True)
                result = bridge.load_json(bridge._paths(run_id)["m57_3_result"])
            self.assertEqual(loads["count"], 1)
            self.assertEqual(first["m57_diagnostic_outcome_load_this_invocation"], 1)
            self.assertEqual(replay["m57_diagnostic_outcome_load_this_invocation"], 0)
            self.assertTrue(validation["valid"], validation["errors"])
            self.assertEqual(first["observed_label_count"], 30)
            self.assertEqual(first["preoutcome_component_prediction_count"], 90)
            self.assertEqual(first["decision_ceiling_count"], 30)
            self.assertEqual(first["available_stage_substitution_count"], 120)
            self.assertFalse(first["realization_stage_available"])
            self.assertFalse(result["formal_result_created"])
            self.assertFalse(result["m58_planning_authorized"])

    def test_join_preserves_all_preoutcome_probabilities_and_adds_only_decision_ceiling(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            run_id = "m573-exact-transformation"
            with m5610_private_roots(root):
                prepare_full_chain(root, run_id)
                bridge._execute(run_id, allow_forged=True)
                paths = bridge._paths(run_id)
                capsule = bridge.load_json(paths["m57_2_capsule"])
                checkpoint = bridge.load_json(paths["m57_3_checkpoint"])
            joined = checkpoint["joined_bundle"]
            for source, row in zip(capsule["rows"], joined["rows"]):
                self.assertEqual(row["original_probabilities"], source["original_probabilities"])
                for stage_id in ("perception", "retrieval", "state"):
                    self.assertEqual(
                        row["substitutions"][stage_id]["probabilities"],
                        source["substitutions"][stage_id]["probabilities"],
                    )
                observed = row["observed_label"]
                self.assertEqual(row["substitutions"]["decision"]["probabilities"][observed], 1.0)
                self.assertEqual(sum(row["substitutions"]["decision"]["probabilities"].values()), 1.0)
                self.assertTrue(row["substitutions"]["decision"]["future_outcome_used"])
                self.assertEqual(row["substitutions"]["realization"]["availability"], "unavailable")
            self.assertEqual(
                checkpoint["core_analysis"],
                localization_m57.analyze_component_substitution_bundle(bridge._projection(joined)),
            )

    def test_public_formal_execution_and_validator_reject_forged_run_before_bridge_artifacts(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            run_id = "m573-public-rejects-forged"
            with m5610_private_roots(root):
                prepare_full_chain(root, run_id)
                with mock.patch.object(scorer_m56, "load_outcome_inputs") as loader:
                    with self.assertRaisesRegex(PermissionError, "author_constructed_not_formal|real independent"):
                        bridge.execute_m57_sanctioned_outcome_analyzer_bridge(run_id)
                validation = bridge.validate_m57_sanctioned_outcome_analyzer_bridge(run_id)
                paths = bridge._paths(run_id)
            self.assertEqual(loader.call_count, 0)
            self.assertFalse(validation["valid"])
            self.assertFalse(paths["m57_3_mode"].exists())
            self.assertFalse(paths["m57_3_intent"].exists())

    def test_missing_m572_or_m56_result_chain_fails_before_bridge_outcome_access(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            with m5610_private_roots(root):
                run_id = "m573-missing-m572"
                materialize_scoring_run(root, run_id)
                commitment_m57.commit_m57_preoutcome_diagnostic_mode(run_id)
                with mock.patch.object(scorer_m56, "load_outcome_inputs") as loader:
                    with self.assertRaises(PermissionError):
                        bridge._execute(run_id, allow_forged=True)
                self.assertEqual(loader.call_count, 0)

                run_id = "m573-missing-m56-result"
                run_root = materialize_scoring_run(root, run_id)
                commitment_m57.commit_m57_preoutcome_diagnostic_mode(run_id)
                context = component_m57._load_preoutcome_context(run_id)
                evidence = component_m57.build_forged_engineering_evidence_manifest(run_id, context)
                durable_m56._durable_atomic_write_json(
                    run_root / "generation" / component_m57.EVIDENCE_FILENAME,
                    evidence, exclusive=True,
                )
                with mock.patch.object(
                    component_m57.runner_m56, "_ollama_generate",
                    side_effect=component_m57._mock_ollama_call,
                ):
                    component_m57._execute(run_id, allow_forged=True)
                with mock.patch.object(scorer_m56, "load_outcome_inputs") as loader:
                    with self.assertRaises(PermissionError):
                        bridge._execute(run_id, allow_forged=True)
                self.assertEqual(loader.call_count, 0)

    def test_intent_without_checkpoint_is_terminal_and_does_not_reload(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            run_id = "m573-intent-only"
            with m5610_private_roots(root):
                prepare_full_chain(root, run_id)
                upstream = bridge._load_upstream(run_id, allow_forged=True)
                mode = bridge.build_bridge_mode(run_id, upstream)
                intent = bridge.build_join_intent(run_id, mode)
                durable_m56._durable_atomic_write_json(
                    upstream["paths"]["m57_3_mode"], mode, exclusive=True
                )
                durable_m56._durable_atomic_write_json(
                    upstream["paths"]["m57_3_intent"], intent, exclusive=True
                )
                with mock.patch.object(scorer_m56, "load_outcome_inputs") as loader:
                    with self.assertRaisesRegex(PermissionError, "outcome reload is forbidden"):
                        bridge._execute(run_id, allow_forged=True)
                failure = bridge.load_json(upstream["paths"]["m57_3_failure"])
            self.assertEqual(loader.call_count, 0)
            self.assertFalse(failure["additional_outcome_load_authorized"])
            self.assertFalse(failure["formal_result_created"])

    def test_checkpoint_restart_finalizes_without_reloading_outcome(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            run_id = "m573-checkpoint-restart"
            with m5610_private_roots(root):
                prepare_full_chain(root, run_id)
                bridge._execute(run_id, allow_forged=True)
                paths = bridge._paths(run_id)
                paths["m57_3_result"].unlink()
                paths["m57_3_commitment"].unlink()
                with mock.patch.object(
                    scorer_m56, "load_outcome_inputs",
                    side_effect=AssertionError("checkpoint restart must not reload outcome"),
                ) as loader:
                    replay = bridge._execute(run_id, allow_forged=True)
            self.assertEqual(loader.call_count, 0)
            self.assertEqual(replay["m57_diagnostic_outcome_load_this_invocation"], 0)
            self.assertTrue(paths["m57_3_result"].exists())
            self.assertTrue(paths["m57_3_commitment"].exists())

    def test_private_outcome_mutation_fails_terminally_after_one_attempt(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            run_id = "m573-mutated-outcome"
            with m5610_private_roots(root):
                prepare_full_chain(root, run_id)
                paths = bridge._paths(run_id)
                outcome_path = paths["scoring"] / "private_outcome_key.json"
                outcome = bridge.load_json(outcome_path)
                outcome["outcomes"][0]["actual_observed_behavior"] = "not_a_frozen_label"
                rewrite_json(outcome_path, outcome)
                original = scorer_m56.load_outcome_inputs
                with mock.patch.object(scorer_m56, "load_outcome_inputs", wraps=original) as loader:
                    with self.assertRaises(ValueError):
                        bridge._execute(run_id, allow_forged=True)
                    with self.assertRaisesRegex(PermissionError, "terminal"):
                        bridge._execute(run_id, allow_forged=True)
            self.assertEqual(loader.call_count, 1)
            self.assertTrue(paths["m57_3_failure"].exists())
            self.assertFalse(paths["m57_3_checkpoint"].exists())

    def test_upstream_capsule_mutation_fails_before_bridge_mode_intent_or_outcome_access(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            run_id = "m573-upstream-capsule-mutation"
            with m5610_private_roots(root):
                prepare_full_chain(root, run_id)
                paths = bridge._paths(run_id)
                capsule = bridge.load_json(paths["m57_2_capsule"])
                capsule["available_prediction_count"] = 89
                capsule["capsule_hash"] = component_m57.digest(
                    {key: value for key, value in capsule.items() if key != "capsule_hash"}
                )
                rewrite_json(paths["m57_2_capsule"], capsule)
                with mock.patch.object(scorer_m56, "load_outcome_inputs") as loader:
                    with self.assertRaises(PermissionError):
                        bridge._execute(run_id, allow_forged=True)
            self.assertEqual(loader.call_count, 0)
            self.assertFalse(paths["m57_3_mode"].exists())
            self.assertFalse(paths["m57_3_intent"].exists())

    def test_joined_bundle_probability_label_and_decision_mutations_fail_closed(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            run_id = "m573-bundle-mutations"
            with m5610_private_roots(root):
                prepare_full_chain(root, run_id)
                bridge._execute(run_id, allow_forged=True)
                upstream = bridge._load_upstream(run_id, allow_forged=True)
                checkpoint = bridge.load_json(bridge._paths(run_id)["m57_3_checkpoint"])
            base = checkpoint["joined_bundle"]
            mutations = []
            changed = deepcopy(base)
            probabilities = changed["rows"][0]["substitutions"]["retrieval"]["probabilities"]
            first, second = localization_m57.LABELS[:2]
            probabilities[first], probabilities[second] = probabilities[second], probabilities[first]
            changed.pop("bundle_hash")
            changed["bundle_hash"] = localization_m57.digest(changed)
            mutations.append(changed)
            changed = deepcopy(base)
            changed["rows"][0]["observed_label"] = "not_a_frozen_label"
            changed.pop("bundle_hash")
            changed["bundle_hash"] = localization_m57.digest(changed)
            mutations.append(changed)
            changed = deepcopy(base)
            changed["rows"][0]["substitutions"]["decision"]["future_outcome_used"] = False
            changed.pop("bundle_hash")
            changed["bundle_hash"] = localization_m57.digest(changed)
            mutations.append(changed)
            for mutation in mutations:
                self.assertFalse(bridge.validate_joined_bundle(mutation, upstream)["valid"])

    def test_checkpoint_result_and_commitment_mutations_fail_closed(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            run_id = "m573-result-mutations"
            with m5610_private_roots(root):
                prepare_full_chain(root, run_id)
                bridge._execute(run_id, allow_forged=True)
                upstream = bridge._load_upstream(run_id, allow_forged=True)
                paths = bridge._paths(run_id)
                mode = bridge.load_json(paths["m57_3_mode"])
                intent = bridge.load_json(paths["m57_3_intent"])
                checkpoint = bridge.load_json(paths["m57_3_checkpoint"])
                result = bridge.load_json(paths["m57_3_result"])
                commitment = bridge.load_json(paths["m57_3_commitment"])
            changed = deepcopy(checkpoint)
            changed["decision_ceiling_count"] = 29
            changed["checkpoint_hash"] = bridge.digest({k: v for k, v in changed.items() if k != "checkpoint_hash"})
            self.assertFalse(bridge.validate_private_checkpoint(changed, run_id, mode, intent, upstream)["valid"])
            changed_result = deepcopy(result)
            changed_result["formal_result_created"] = True
            changed_result["result_hash"] = bridge.digest({k: v for k, v in changed_result.items() if k != "result_hash"})
            self.assertFalse(bridge.validate_result(changed_result, run_id, checkpoint, upstream)["valid"])
            changed_commitment = deepcopy(commitment)
            changed_commitment["m58_planning_authorized"] = True
            changed_commitment["commitment_hash"] = bridge.digest({k: v for k, v in changed_commitment.items() if k != "commitment_hash"})
            self.assertFalse(bridge.validate_result_commitment(changed_commitment, result)["valid"])

    def test_aggregate_result_does_not_publish_per_sample_observed_labels(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            run_id = "m573-private-label-boundary"
            with m5610_private_roots(root):
                prepare_full_chain(root, run_id)
                bridge._execute(run_id, allow_forged=True)
                paths = bridge._paths(run_id)
                result = bridge.load_json(paths["m57_3_result"])
                checkpoint = bridge.load_json(paths["m57_3_checkpoint"])

            def keys(value):
                if isinstance(value, dict):
                    return set(value) | set().union(*(keys(child) for child in value.values()))
                if isinstance(value, list):
                    return set().union(*(keys(child) for child in value)) if value else set()
                return set()

            self.assertNotIn("observed_label", keys(result))
            self.assertIn("observed_label", keys(checkpoint))
            self.assertFalse(result["formal_result_created"])
            self.assertFalse(result["m58_planning_authorized"])

    def test_saved_rehearsal_dashboard_and_implementation_freeze_match_files(self):
        value = bridge.load_saved_rehearsal()
        validation = bridge.validate_rehearsal(value)
        self.assertTrue(validation["valid"], validation["errors"])
        self.assertEqual(value["complete_run_total_named_sanctioned_outcome_loads"], 2)
        self.assertEqual(value["replay_additional_outcome_loads"], 0)
        self.assertFalse(value["formal_result_created"])
        page = bridge.render_dashboard(value, bridge.build_live_audit())
        self.assertIn("預測不能自己填答案", page)
        self.assertIn("120", page)
        self.assertIn("FORMAL M57 DENIED", page)
        self.assertIn("M58 denied", page)
        freeze = bridge.load_json(
            ROOT / "research/m57_3_sanctioned_outcome_analyzer_bridge_implementation_freeze_2026-09-04.json"
        )
        self.assertEqual(
            freeze["schema"],
            "uruha_m57_3_sanctioned_outcome_analyzer_bridge_implementation_freeze_v1",
        )
        self.assertEqual(
            freeze["status"],
            "implementation_frozen_after_engineering_acceptance_before_any_real_m57_diagnostic_target_outcome_access",
        )
        for relative, expected_hash in freeze["files"].items():
            self.assertEqual(bridge.sha256_file(ROOT / relative), expected_hash)


if __name__ == "__main__":
    unittest.main()
