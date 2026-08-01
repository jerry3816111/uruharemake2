import copy
import json
import unittest

import persona_surface_provider_migration_v1 as construction
import uruha_compute_ledger as ledger_module
import uruha_persona_policy as persona_policy
from uruha_brain_mac import (
    RIGHT_BRAIN_MODEL_SYSTEM_PROMPT,
    RightBrain,
    StructuredSurfaceUnavailableError,
)


class PersonaSurfaceProviderMigrationV1Test(unittest.TestCase):
    def test_provider_surface_modes_are_explicit(self):
        legacy = persona_policy.build_persona_policy_provider(persona_policy.LEGACY_PROVIDER)
        target = persona_policy.build_persona_policy_provider(persona_policy.TARGET_PROVIDER)
        neutral = persona_policy.build_persona_policy_provider(persona_policy.NEUTRAL_PROVIDER)

        self.assertTrue(legacy.permits_legacy_fixed_surface)
        self.assertFalse(legacy.requires_structured_model_surface)
        self.assertEqual(legacy.surface_mode, persona_policy.LEGACY_SURFACE_MODE)
        for provider in (target, neutral):
            self.assertFalse(provider.permits_legacy_fixed_surface)
            self.assertTrue(provider.requires_structured_model_surface)
            self.assertEqual(provider.surface_mode, persona_policy.STRUCTURED_SURFACE_MODE)

    def test_structured_projections_expose_equal_shape_surface_contract(self):
        target = persona_policy.build_persona_policy_provider(persona_policy.TARGET_PROVIDER).compile(
            construction.BASE_LOGIC,
            construction.PSYCHE,
        )
        neutral = persona_policy.build_persona_policy_provider(persona_policy.NEUTRAL_PROVIDER).compile(
            construction.BASE_LOGIC,
            construction.PSYCHE,
        )
        self.assertEqual(target["surface_mode"], neutral["surface_mode"])
        self.assertFalse(target["legacy_fixed_surface_allowed"])
        self.assertFalse(neutral["legacy_fixed_surface_allowed"])

    def test_structured_runtime_has_no_legacy_family_entries(self):
        for provider_id in (persona_policy.TARGET_PROVIDER, persona_policy.NEUTRAL_PROVIDER):
            rightbrain = construction.build_structured_rightbrain(provider_id)
            self.assertEqual(rightbrain.scene_fallbacks, {})
            self.assertEqual(rightbrain.intent_reply_families, {})

    def test_structured_runtime_selects_only_strict_model_output(self):
        for provider_id in (persona_policy.TARGET_PROVIDER, persona_policy.NEUTRAL_PROVIDER):
            ledger = ledger_module.ComputeLedger()
            row = construction.run_success_case(provider_id, ledger)
            self.assertEqual(row["status"], "model_reply_selected")
            self.assertEqual(row["selected_source"], "structured_model")
            self.assertEqual(row["legacy_fixed_surface_access_count"], 0)
            self.assertFalse(row["legacy_fixed_surface_used"])
            self.assertEqual(ledger.snapshot()["call_count"], 1)

    def test_structured_runtime_fails_closed_without_model(self):
        for provider_id in (persona_policy.TARGET_PROVIDER, persona_policy.NEUTRAL_PROVIDER):
            row = construction.run_failed_closed_case(provider_id, "model_not_loaded")
            self.assertTrue(row["typed_error_raised"])
            self.assertEqual(row["error_reason"], "model_not_loaded")
            self.assertFalse(row["reply_returned"])
            self.assertEqual(row["legacy_fixed_surface_access_count"], 0)

    def test_structured_runtime_fails_closed_for_hard_boundary(self):
        for provider_id in (persona_policy.TARGET_PROVIDER, persona_policy.NEUTRAL_PROVIDER):
            row = construction.run_failed_closed_case(provider_id, "hard_boundary")
            self.assertTrue(row["typed_error_raised"])
            self.assertEqual(row["error_reason"], "hard_boundary_scene")
            self.assertFalse(row["reply_returned"])
            self.assertEqual(row["legacy_fixed_surface_access_count"], 0)

    def test_structured_runtime_fails_closed_when_all_candidates_rejected(self):
        for provider_id in (persona_policy.TARGET_PROVIDER, persona_policy.NEUTRAL_PROVIDER):
            ledger = ledger_module.ComputeLedger()
            row = construction.run_failed_closed_case(
                provider_id,
                "all_candidates_rejected",
                ledger,
            )
            self.assertTrue(row["typed_error_raised"])
            self.assertEqual(row["error_reason"], "all_model_candidates_rejected")
            self.assertFalse(row["reply_returned"])
            self.assertEqual(row["legacy_fixed_surface_access_count"], 0)
            self.assertEqual(ledger.snapshot()["call_count"], 1)

    def test_direct_legacy_surface_access_is_guarded(self):
        row = construction.direct_guard_check()
        self.assertTrue(row["typed_error_raised"])
        self.assertEqual(row["error_reason"], "legacy_fixed_surface_access:template_reply")
        self.assertEqual(row["guard_access_count"], 1)

    def test_structured_sanitizer_does_not_force_target_first_person(self):
        neutral = construction.build_structured_rightbrain(persona_policy.NEUTRAL_PROVIDER)
        self.assertEqual(neutral._sanitize_reply("私は少し休む。", 32), "私は少し休む。")
        self.assertNotIn("Do not use 私.", neutral._model_surface_system_instruction())

        legacy = RightBrain(load_model=False)
        self.assertEqual(legacy._sanitize_reply("私は少し休む。", 32), "うちは少し休む。")
        self.assertEqual(legacy._model_surface_system_instruction(), RIGHT_BRAIN_MODEL_SYSTEM_PROMPT)

    def test_default_and_explicit_legacy_runtime_remain_identical(self):
        rows = construction.run_legacy_pairs()
        self.assertEqual(len(rows), 3)
        self.assertTrue(all(row["reply_equal"] for row in rows))

    def test_construction_report_meets_preregistered_counts(self):
        preregistration = json.loads(
            construction.DEFAULT_PREREGISTRATION.read_text(encoding="utf-8")
        )
        report = construction.build_report(preregistration)
        self.assertEqual(report["status"], "construction_passed")
        self.assertTrue(all(report["checks"].values()))
        self.assertEqual(report["counts"]["structured_legacy_fixed_surface_access_count"], 0)
        self.assertEqual(report["counts"]["structured_reachable_fixed_family_entry_count"], 0)
        self.assertEqual(report["counts"]["legacy_runtime_mismatch_count"], 0)
        self.assertTrue(report["compute_parity"]["parity_pass"])
        self.assertFalse(report["authorizations"]["formal_persona_similarity_evaluation"])
        self.assertFalse(report["authorizations"]["production_default_enablement"])
        serialized = json.dumps(report, ensure_ascii=False)
        for raw_output in [*construction.SUCCESS_OUTPUTS.values(), construction.REJECTED_OUTPUT]:
            self.assertNotIn(raw_output, serialized)

    def test_failed_structured_call_publishes_trace_to_original_logic(self):
        rightbrain = construction.build_structured_rightbrain(persona_policy.TARGET_PROVIDER)
        logic = copy.deepcopy(construction.BASE_LOGIC)
        with self.assertRaises(StructuredSurfaceUnavailableError):
            rightbrain.speak(
                "今日は少し疲れた。",
                logic,
                copy.deepcopy(construction.MEMORY),
                dict(construction.PSYCHE),
            )
        self.assertEqual(logic["persona_surface_runtime_trace"]["status"], "failed_closed")
        self.assertEqual(
            logic["persona_surface_runtime_trace"]["failure_reason"],
            "model_not_loaded",
        )


if __name__ == "__main__":
    unittest.main()
