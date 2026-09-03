from __future__ import annotations

from copy import deepcopy
import inspect
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import m57_component_error_localization as m57


ROOT = Path(__file__).resolve().parent


def rehash_bundle(bundle: dict) -> dict:
    bundle["bundle_hash"] = m57.digest(
        {key: value for key, value in bundle.items() if key != "bundle_hash"}
    )
    return bundle


def rehash_result(result: dict) -> dict:
    result["analysis_hash"] = m57.digest(
        {key: value for key, value in result.items() if key != "analysis_hash"}
    )
    return result


class M57ComponentErrorLocalizationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.clear_bundle = m57.build_synthetic_bundle()
        cls.tied_bundle = m57.build_synthetic_bundle(ambiguous_tie=True)
        cls.clear_result = m57.analyze_component_substitution_bundle(cls.clear_bundle)
        cls.tied_result = m57.analyze_component_substitution_bundle(cls.tied_bundle)

    def test_contract_dependencies_signature_and_frozen_thresholds_validate(self):
        report = m57.validate_contract()
        self.assertTrue(report["valid"], report["errors"])
        self.assertEqual(report["binding_count"], 5)
        self.assertEqual(
            report["contract_hash"],
            "78d6f604b30dfe1b53766bf39d2da2c1d45ad9f0d86b78b28b5a63d428b598b6",
        )
        self.assertEqual(
            list(inspect.signature(m57.diagnose_formal_m56_components).parameters),
            ["run_id"],
        )
        contract = m57.load_contract()
        self.assertEqual(contract["analysis"]["bootstrap_repetitions"], 20000)
        self.assertEqual(contract["analysis"]["bootstrap_seed"], 570904)

    def test_prechange_probe_proves_only_localization_schema_gap(self):
        probe = m57.load_json(
            ROOT / "analysis/m57_prechange_component_error_localization_gap_probe_2026-09-04.json"
        )
        self.assertEqual(len(probe["required_localization_keys_present"]), 10)
        self.assertEqual(probe["required_localization_key_count_present"], 0)
        self.assertEqual(probe["real_target_outcome_access_count"], 0)
        self.assertEqual(probe["formal_model_call_count"], 0)
        self.assertFalse(probe["leading_recoverable_stage_available"])

    def test_clear_fixture_localizes_retrieval_but_excludes_upper_bound(self):
        validation = m57.validate_result(
            self.clear_result, expected_data_kind="synthetic_engineering_only"
        )
        self.assertTrue(validation["valid"], validation["errors"])
        self.assertEqual(self.clear_result["leading_recoverable_stage"], "retrieval")
        self.assertEqual(
            self.clear_result["attribution_status"],
            "descriptive_leading_recoverable_stage_not_unique_cause",
        )
        self.assertEqual(
            self.clear_result["stage_results"]["decision"]["attribution_status"],
            "diagnostic_upper_bound_excluded_from_causal_ranking",
        )
        self.assertEqual(
            self.clear_result["stage_results"]["realization"]["attribution_status"],
            "unavailable_required_evidence_missing",
        )
        self.assertEqual(
            self.clear_result["stage_results"]["state"]["attribution_status"],
            "no_recoverable_effect",
        )
        self.assertFalse(self.clear_result["unique_biological_or_psychological_cause_claim_authorized"])

    def test_tied_fixture_abstains_instead_of_inventing_a_leader(self):
        validation = m57.validate_result(
            self.tied_result, expected_data_kind="synthetic_engineering_only"
        )
        self.assertTrue(validation["valid"], validation["errors"])
        self.assertIsNone(self.tied_result["leading_recoverable_stage"])
        self.assertEqual(
            self.tied_result["attribution_status"], "ambiguous_interacting_or_unresolved"
        )

    def test_bundle_mutations_fail_closed(self):
        mutations = []

        missing = deepcopy(self.clear_bundle)
        missing["rows"].pop()
        mutations.append(rehash_bundle(missing))

        bad_sum = deepcopy(self.clear_bundle)
        bad_sum["rows"][0]["original_probabilities"][m57.LABELS[0]] += 0.2
        bad_sum["rows"][0]["original_output_hash"] = m57.digest(
            bad_sum["rows"][0]["original_probabilities"]
        )
        mutations.append(rehash_bundle(bad_sum))

        wrong_component = deepcopy(self.clear_bundle)
        wrong_component["rows"][0]["substitutions"]["perception"]["changed_component"] = "retrieval"
        mutations.append(rehash_bundle(wrong_component))

        plan_drift = deepcopy(self.clear_bundle)
        plan_drift["rows"][0]["substitutions"]["retrieval"]["plan_hash"] = "0" * 64
        mutations.append(rehash_bundle(plan_drift))

        future_leak = deepcopy(self.clear_bundle)
        future_leak["rows"][0]["substitutions"]["retrieval"]["future_outcome_used"] = True
        mutations.append(rehash_bundle(future_leak))

        retried = deepcopy(self.clear_bundle)
        retried["retry_count"] = 1
        mutations.append(rehash_bundle(retried))

        early_outcome = deepcopy(self.clear_bundle)
        early_outcome["outcome_access_after_all_predictions_committed"] = False
        mutations.append(rehash_bundle(early_outcome))

        for mutated in mutations:
            with self.subTest(mutation=m57.digest(mutated)[:12]):
                report = m57.validate_bundle(mutated)
                self.assertFalse(report["valid"], report)
                with self.assertRaises(ValueError):
                    m57.analyze_component_substitution_bundle(mutated)

    def test_private_mental_truth_is_never_created_as_an_oracle(self):
        contract = m57.load_contract()
        for stage in contract["stages"]:
            self.assertFalse(stage["private_mental_truth_claimed"])
        state = next(stage for stage in contract["stages"] if stage["id"] == "state")
        self.assertEqual(state["oracle_kind"], "observable_only_proxy_not_private_state_oracle")
        source = (ROOT / "m57_component_error_localization.py").read_text(encoding="utf-8")
        self.assertNotIn("mental_state_ground_truth", source)
        self.assertNotIn("private_state_oracle =", source)

    def test_formal_entry_fails_before_analyzer_or_outcome_access(self):
        for invalid in ("", "../run", "run/id"):
            with self.assertRaises(ValueError):
                m57.diagnose_formal_m56_components(invalid)
        with patch.object(m57, "analyze_component_substitution_bundle") as analyzer:
            with self.assertRaisesRegex(PermissionError, "authorized M56 result is required"):
                m57.diagnose_formal_m56_components("future-valid-run")
            analyzer.assert_not_called()

    def test_caller_boolean_cannot_mint_a_formal_bundle_or_result(self):
        forged = deepcopy(self.clear_bundle)
        forged["data_kind"] = "real_formal_m56_diagnostic"
        forged["formal_authorization"] = True
        rehash_bundle(forged)
        report = m57.validate_bundle(forged)
        self.assertFalse(report["valid"])
        self.assertIn("bundle.real_formal_bridge_unavailable", report["errors"])
        with self.assertRaises(ValueError):
            m57.analyze_component_substitution_bundle(forged)

        forged_result = deepcopy(self.clear_result)
        forged_result["data_kind"] = "real_formal_m56_diagnostic"
        forged_result["status"] = "formal_localization_complete"
        forged_result["real_target_outcome_access_count"] = 1
        forged_result["formal_result_created"] = True
        rehash_result(forged_result)
        result_report = m57.validate_result(forged_result)
        self.assertFalse(result_report["valid"])
        self.assertIn("result.real_formal_bridge_unavailable", result_report["errors"])

    def test_live_audit_keeps_human_and_formal_gates_closed(self):
        audit = m57.build_live_audit()
        validation = m57.validate_live_audit(audit)
        self.assertTrue(validation["valid"], validation["errors"])
        self.assertEqual(audit["counts"]["v7_slots_by_ledger"], [0, 0])
        self.assertEqual(audit["counts"]["real_temporal_rows"], 0)
        self.assertFalse(audit["m56_formal_result_created"])
        self.assertFalse(audit["m57_formal_result_created"])
        self.assertEqual(audit["target_outcome_access_count"], 0)
        self.assertEqual(audit["formal_model_call_count"], 0)

    def test_result_tamper_is_not_renderable_even_when_rehashed(self):
        result = deepcopy(self.clear_result)
        result["leading_recoverable_stage"] = "decision"
        report = m57.validate_result(rehash_result(result))
        self.assertFalse(report["valid"])
        self.assertIn("result.leading_stage", report["errors"])

    def test_dashboard_distinguishes_mechanical_fixture_from_real_result(self):
        rehearsal = m57.build_engineering_rehearsal()
        page = m57.render_dashboard(rehearsal, m57.build_live_audit())
        self.assertIn("M56 AGGREGATE", page)
        self.assertIn("M57 COMPONENT SUBSTITUTION", page)
        self.assertIn("leading = retrieval", page)
        self.assertIn("leading = None", page)
        self.assertIn("FORMAL M57 DENIED", page)
        self.assertIn("作者構造的機械驗證，不是真人結果", page)
        self.assertNotIn("<form", page)
        self.assertNotIn("overflow-x", page)

    def test_saved_rehearsal_validates_when_materialized(self):
        if not m57.RESULT_PATH.exists():
            self.skipTest("saved rehearsal is materialized after pre-freeze tests")
        value = m57.load_saved_rehearsal()
        report = m57.validate_rehearsal(value)
        self.assertTrue(report["valid"], report["errors"])

    def test_implementation_freeze_matches_frozen_files(self):
        freeze_path = ROOT / "research/m57_component_error_localization_implementation_freeze_2026-09-04.json"
        if not freeze_path.exists():
            self.skipTest("implementation freeze is created after pre-freeze verification")
        freeze = m57.load_json(freeze_path)
        self.assertEqual(
            freeze["schema"], "uruha_m57_component_error_localization_implementation_freeze_v1"
        )
        self.assertEqual(freeze["status"], "frozen_before_any_real_m56_target_outcome_access")
        for row in freeze["files"]:
            self.assertEqual(m57.sha256_file(ROOT / row["path"]), row["sha256"], row["path"])


if __name__ == "__main__":
    unittest.main()
