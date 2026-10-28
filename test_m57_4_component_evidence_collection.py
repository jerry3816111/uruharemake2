import inspect
import json
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import m56_7_mac_full_sync_generation as durable_m56
import m57_1_preoutcome_diagnostic_commitment as commitment_m57
import m57_2_component_prediction_capsule as component_m57
import m57_4_component_evidence_collection as collection
from test_m56_10_crash_safe_outcome_join import m5610_private_roots
from test_m56_9_single_writer_formal_scoring import materialize_scoring_run


ROOT = Path(__file__).resolve().parent


def prepare(root: Path, run_id: str):
    materialize_scoring_run(root, run_id)
    commitment_m57.commit_m57_preoutcome_diagnostic_mode(run_id)
    initialized = collection._initialize(run_id, collection._synthetic_roster(), synthetic=True)
    return initialized, collection._context(run_id)


def coder_payload(source, *, variant="a", index=1):
    return collection._synthetic_coder_payload(source, variant=variant, index=index)


def complete_coders(run_id, context, tokens):
    for index, sample_id in enumerate(collection._sample_order(context)):
        for role, variant in (("coder_a", "a"), ("coder_b", "b")):
            view = collection.record_component_source_view(run_id, role, tokens[role], sample_id)
            collection.save_component_evidence_entry(
                run_id, role, tokens[role], sample_id,
                coder_payload(view["source_information"], variant=variant, index=index),
            )
    return {
        role: collection.seal_component_evidence_ledger(run_id, role, tokens[role])
        for role in collection.CODER_SLOTS
    }


def complete_adjudicator(run_id, context, tokens):
    for sample_id in collection._sample_order(context):
        view = collection.record_component_source_view(
            run_id, "adjudicator", tokens["adjudicator"], sample_id
        )
        contributions = view["adjudication_context"]["coder_contributions"]
        payload = {
            "resolved_perception": deepcopy(contributions["coder_a"]["perception"]),
            "perception_resolution_basis": "Synthetic test resolution preserves the raw disagreement.",
            "resolved_retrieval": deepcopy(contributions["coder_a"]["retrieval"]),
            "retrieval_resolution_basis": "Synthetic test resolution preserves the raw disagreement.",
            "observable_state_proxy": collection._synthetic_state_payload(
                context, sample_id, view["source_information"]
            ),
        }
        collection.save_component_evidence_entry(
            run_id, "adjudicator", tokens["adjudicator"], sample_id, payload
        )
    return collection.seal_component_evidence_ledger(
        run_id, "adjudicator", tokens["adjudicator"]
    )


class M574ComponentEvidenceCollectionTests(unittest.TestCase):
    def test_contract_and_public_signatures_are_frozen(self):
        report = collection.validate_contract()
        self.assertTrue(report["valid"], report["errors"])
        self.assertEqual(report["binding_count"], 6)
        expected = collection.load_contract()["public_functions"]
        functions = {
            "initialize_component_evidence_collection": collection.initialize_component_evidence_collection,
            "record_component_source_view": collection.record_component_source_view,
            "save_component_evidence_entry": collection.save_component_evidence_entry,
            "seal_component_evidence_ledger": collection.seal_component_evidence_ledger,
            "export_component_evidence_manifest": collection.export_component_evidence_manifest,
        }
        for name, function in functions.items():
            self.assertEqual(list(inspect.signature(function).parameters), expected[name])

    def test_live_state_remains_zero_and_denied(self):
        audit = collection.build_live_audit()
        self.assertTrue(audit["contract_valid"])
        self.assertEqual(audit["counts"]["v7_slots_by_ledger"], [0, 0])
        self.assertEqual(audit["counts"]["real_temporal_rows"], 0)
        self.assertEqual(audit["real_private_role_ledgers"], 0)
        self.assertEqual(audit["target_outcome_access_count"], 0)
        self.assertFalse(audit["formal_m57_result_created"])
        self.assertFalse(audit["m58_authorized"])

    def test_real_roster_rejects_repeated_pseudonym_and_missing_human_attestations(self):
        roster = {
            role: {
                "pseudonym": f"human-{role.replace('_', '-')}",
                "consenting_human_attested": True,
                "not_model_or_synthetic_attested": True,
                "different_person_from_other_slots_attested": True,
            }
            for role in collection.ROLE_SLOTS
        }
        self.assertEqual(collection._validate_roster(roster, synthetic=False), [])
        reordered = {role: roster[role] for role in reversed(collection.ROLE_SLOTS)}
        self.assertEqual(collection._validate_roster(reordered, synthetic=False), [])
        repeated = deepcopy(roster)
        repeated["coder_b"]["pseudonym"] = repeated["coder_a"]["pseudonym"]
        self.assertIn("roster.distinct_pseudonyms", collection._validate_roster(repeated, synthetic=False))
        missing = deepcopy(roster)
        missing["adjudicator"]["not_model_or_synthetic_attested"] = False
        self.assertIn("roster.adjudicator.attestations", collection._validate_roster(missing, synthetic=False))
        self.assertNotEqual(collection._validate_roster(collection._synthetic_roster(), synthetic=False), [])

    def test_role_tokens_isolate_coder_surface_and_adjudicator_waits_for_both_seals(self):
        with TemporaryDirectory() as temp, m5610_private_roots(Path(temp)):
            initialized, context = prepare(Path(temp), "m574-token-isolation")
            tokens = initialized["role_session_tokens"]
            sample_id = collection._sample_order(context)[0]
            view = collection.record_component_source_view(
                "m574-token-isolation", "coder_a", tokens["coder_a"], sample_id
            )
            self.assertFalse(view["other_coder_ledger_visible"])
            self.assertIsNone(view["adjudication_context"])
            self.assertNotIn("coder_b", json.dumps(view, ensure_ascii=False))
            with self.assertRaisesRegex(PermissionError, "session token"):
                collection.record_component_source_view(
                    "m574-token-isolation", "coder_a", tokens["coder_b"], sample_id
                )
            with self.assertRaisesRegex(PermissionError, "not valid and sealed"):
                collection.record_component_source_view(
                    "m574-token-isolation", "adjudicator", tokens["adjudicator"], sample_id
                )

    def test_entry_requires_view_and_rejects_unknown_history_forbidden_key_and_private_state(self):
        with TemporaryDirectory() as temp, m5610_private_roots(Path(temp)):
            initialized, context = prepare(Path(temp), "m574-entry-boundaries")
            token = initialized["role_session_tokens"]["coder_a"]
            sample_id = collection._sample_order(context)[0]
            source, _ = collection._source(context, sample_id)
            valid = coder_payload(source)
            with self.assertRaisesRegex(PermissionError, "requires a server-recorded source view"):
                collection.save_component_evidence_entry(
                    "m574-entry-boundaries", "coder_a", token, sample_id, valid
                )
            collection.record_component_source_view(
                "m574-entry-boundaries", "coder_a", token, sample_id
            )
            unknown = deepcopy(valid)
            unknown["retrieval"]["selected_history_ids"] = ["post-cutoff-or-unknown"]
            with self.assertRaisesRegex(ValueError, "post_cutoff_or_unknown_id"):
                collection.save_component_evidence_entry(
                    "m574-entry-boundaries", "coder_a", token, sample_id, unknown
                )
            forbidden = deepcopy(valid)
            forbidden["perception"]["target_outcome"] = "leak"
            with self.assertRaisesRegex(ValueError, "forbidden"):
                collection.save_component_evidence_entry(
                    "m574-entry-boundaries", "coder_a", token, sample_id, forbidden
                )
            state = {
                "observable_proxy_variables": {"transient_state": "invented"},
                "source_refs": ["source_information.current_pre_cutoff_event"],
            }
            errors = component_m57._validate_resolved_payload("state", state, source, "state")
            self.assertIn("state.private_or_unknown_variable", errors)

    def test_partial_ledger_cannot_seal_and_view_revisions_are_preserved(self):
        with TemporaryDirectory() as temp, m5610_private_roots(Path(temp)):
            initialized, context = prepare(Path(temp), "m574-partial-seal")
            token = initialized["role_session_tokens"]["coder_a"]
            sample_id = collection._sample_order(context)[0]
            view = collection.record_component_source_view(
                "m574-partial-seal", "coder_a", token, sample_id
            )
            first = collection.save_component_evidence_entry(
                "m574-partial-seal", "coder_a", token, sample_id,
                coder_payload(view["source_information"], index=1),
            )
            second = collection.save_component_evidence_entry(
                "m574-partial-seal", "coder_a", token, sample_id,
                coder_payload(view["source_information"], index=2),
            )
            self.assertEqual((first["revision_number"], second["revision_number"]), (1, 2))
            ledger = collection.load_json(collection._paths("m574-partial-seal")["ledger_coder_a"])
            self.assertEqual(len(ledger["entries"][sample_id]["revisions"]), 2)
            with self.assertRaisesRegex(ValueError, "incomplete"):
                collection.seal_component_evidence_ledger(
                    "m574-partial-seal", "coder_a", token
                )

    def test_outcome_marker_blocks_view_save_seal_and_export_without_access(self):
        with TemporaryDirectory() as temp, m5610_private_roots(Path(temp)):
            initialized, context = prepare(Path(temp), "m574-outcome-race")
            tokens = initialized["role_session_tokens"]
            sample_id = collection._sample_order(context)[0]
            view = collection.record_component_source_view(
                "m574-outcome-race", "coder_a", tokens["coder_a"], sample_id
            )
            paths = collection._paths("m574-outcome-race")
            durable_m56._durable_atomic_write_json(
                paths["m56_10_intent"], {"synthetic_outcome_state_marker": True}, exclusive=True
            )
            operations = [
                lambda: collection.record_component_source_view(
                    "m574-outcome-race", "coder_b", tokens["coder_b"], sample_id
                ),
                lambda: collection.save_component_evidence_entry(
                    "m574-outcome-race", "coder_a", tokens["coder_a"], sample_id,
                    coder_payload(view["source_information"]),
                ),
                lambda: collection.seal_component_evidence_ledger(
                    "m574-outcome-race", "coder_a", tokens["coder_a"]
                ),
                lambda: collection.export_component_evidence_manifest(
                    "m574-outcome-race", tokens["adjudicator"]
                ),
            ]
            for operation in operations:
                with self.assertRaisesRegex(PermissionError, "after outcome state"):
                    operation()
            self.assertFalse(paths["evidence"].exists())

    def test_outcome_marker_blocks_initialization_and_unsafe_run_is_rejected(self):
        with TemporaryDirectory() as temp, m5610_private_roots(Path(temp)):
            run_id = "m574-late-init"
            materialize_scoring_run(Path(temp), run_id)
            commitment_m57.commit_m57_preoutcome_diagnostic_mode(run_id)
            paths = collection._paths(run_id)
            durable_m56._durable_atomic_write_json(
                paths["m56_10_intent"], {"synthetic_outcome_state_marker": True}, exclusive=True
            )
            with self.assertRaisesRegex(PermissionError, "after outcome state"):
                collection._initialize(run_id, collection._synthetic_roster(), synthetic=True)
            with self.assertRaises((ValueError, PermissionError)):
                collection._initialize("../escape", collection._synthetic_roster(), synthetic=True)

    def test_complete_synthetic_collection_exports_exact_m572_shape_and_stays_nonformal(self):
        with TemporaryDirectory() as temp, m5610_private_roots(Path(temp)):
            run_id = "m574-complete-synthetic"
            initialized, context = prepare(Path(temp), run_id)
            tokens = initialized["role_session_tokens"]
            complete_coders(run_id, context, tokens)
            first_adj_view = collection.record_component_source_view(
                run_id, "adjudicator", tokens["adjudicator"], collection._sample_order(context)[0]
            )
            self.assertIn("coder_contributions", first_adj_view["adjudication_context"])
            complete_adjudicator(run_id, context, tokens)
            exported = collection.export_component_evidence_manifest(run_id, tokens["adjudicator"])
            replay = collection.export_component_evidence_manifest(run_id, tokens["adjudicator"])
            paths = collection._paths(run_id)
            manifest = collection.load_json(paths["evidence"])
            internal = component_m57.validate_evidence_manifest(
                manifest, run_id, context, allow_forged=True
            )
            public = component_m57.validate_evidence_manifest(
                manifest, run_id, context, allow_forged=False
            )
            self.assertTrue(internal["valid"], internal["errors"])
            self.assertFalse(public["valid"])
            self.assertFalse(exported["formal_manifest_exported"])
            self.assertEqual(exported["coder_entry_count"], 60)
            self.assertEqual(exported["adjudicator_entry_count"], 30)
            self.assertEqual(exported["source_view_count"], 90)
            self.assertEqual(exported["disagreement_counts"], {"perception": 6, "retrieval": 8})
            self.assertEqual(replay["manifest_write"], "validated_existing_identical")
            self.assertEqual(replay["export_write"], "validated_existing_identical")
            self.assertEqual(exported["target_outcome_access_count"], 0)
            self.assertEqual(exported["model_call_count"], 0)
            self.assertFalse(exported["m57_2_prediction_execution_started"])
            self.assertFalse(exported["m58_authorized"])
            coder_ledger = collection.load_json(paths["ledger_coder_a"])
            sealed_payload = coder_payload(first_adj_view["source_information"])
            with self.assertRaisesRegex(PermissionError, "sealed"):
                collection.save_component_evidence_entry(
                    run_id, "coder_a", tokens["coder_a"], collection._sample_order(context)[0],
                    sealed_payload,
                )
            self.assertTrue(sealed_payload)
            tampered = deepcopy(coder_ledger)
            tampered["revision_count"] += 1
            self.assertIn("ledger.hash", collection._validate_ledger(
                tampered, collection.load_json(paths["m57_4_mode"]), context, require_complete=True
            ))
            seal = collection.load_json(paths["seal_coder_a"])
            changed_seal = deepcopy(seal)
            changed_seal["entry_count"] = 29
            self.assertTrue(collection._validate_seal(
                changed_seal, coder_ledger, collection.load_json(paths["m57_4_mode"])
            ))
            changed_manifest = deepcopy(manifest)
            changed_manifest["sample_count"] = 29
            changed_manifest["manifest_hash"] = collection.digest(
                {key: value for key, value in changed_manifest.items() if key != "manifest_hash"}
            )
            paths["evidence"].write_text(
                json.dumps(changed_manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
            with self.assertRaisesRegex(FileExistsError, "overwrite forbidden"):
                collection.export_component_evidence_manifest(run_id, tokens["adjudicator"])

    def test_coder_page_is_functional_and_does_not_surface_other_ledger(self):
        with TemporaryDirectory() as temp, m5610_private_roots(Path(temp)):
            initialized, context = prepare(Path(temp), "m574-coder-page")
            token = initialized["role_session_tokens"]["coder_a"]
            sample_id = collection._sample_order(context)[0]
            page = collection.render_collection_page(
                "m574-coder-page", "coder_a", token, sample_id
            )
            self.assertIn("可直接看見的特徵", page)
            self.assertIn("只會看到自己的ledger", page)
            self.assertIn('action="/save"', page)
            self.assertNotIn("coder_contributions", page)
            self.assertNotIn("target_outcome", page)

    def test_saved_rehearsal_dashboard_and_implementation_freeze_match_files(self):
        value = collection.load_saved_rehearsal()
        report = collection.validate_rehearsal(value)
        self.assertTrue(report["valid"], report["errors"])
        self.assertEqual(value["disagreement_counts"], {"perception": 6, "retrieval": 8})
        page = collection.render_dashboard(value, collection.build_live_audit())
        self.assertIn("不是把答案寫進標註", page)
        self.assertIn("90", page)
        self.assertIn("FORMAL M57 DENIED", page)
        self.assertIn("M58 denied", page)
        freeze = collection.load_json(
            ROOT / "research/m57_4_component_evidence_collection_implementation_freeze_2026-09-04.json"
        )
        self.assertEqual(
            freeze["status"],
            "implementation_frozen_after_engineering_acceptance_before_any_real_component_source_view",
        )
        for relative, expected_hash in freeze["files"].items():
            self.assertEqual(collection.sha256_file(ROOT / relative), expected_hash)


if __name__ == "__main__":
    unittest.main()
