import json
import unittest
from types import SimpleNamespace

import persona_policy_token_parity_v1 as construction
import uruha_compute_ledger as ledger_module


class PersonaPolicyTokenParityV1Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.preregistration = json.loads(
            construction.DEFAULT_PREREGISTRATION.read_text(encoding="utf-8")
        )
        cls.report = construction.build_report(cls.preregistration)

    def test_construction_passes_every_preregistered_check(self):
        self.assertEqual(self.report["status"], "construction_passed")
        self.assertTrue(all(self.report["checks"].values()))
        self.assertEqual(self.report["counts"]["context_pair_count"], 6)
        self.assertEqual(self.report["counts"]["actual_model_weight_load_count"], 0)
        self.assertEqual(self.report["counts"]["actual_model_generation_call_count"], 0)

    def test_allocation_is_equal_while_active_tokens_remain_observable(self):
        parity = self.report["compute_parity"]
        self.assertTrue(parity["parity_pass"])
        self.assertTrue(parity["prompt_token_schedule_equal"])
        self.assertEqual(parity["left_prompt_tokens"], [640] * 6)
        self.assertEqual(parity["right_prompt_tokens"], [640] * 6)
        self.assertTrue(parity["active_prompt_tokens_available"])
        self.assertFalse(parity["active_prompt_token_schedule_equal"])
        self.assertEqual(
            [row["active_token_delta"] for row in self.report["paired_contexts"]],
            [1, 1, 0, -6, -11, -2],
        )

    def test_left_padding_preserves_active_sequence_and_masks_prefix(self):
        for row in self.report["paired_contexts"]:
            self.assertTrue(row["both_active_sequences_preserved"])
            self.assertTrue(row["both_prefixes_attention_masked"])
            self.assertEqual(row["target_allocated_prompt_tokens"], 640)
            self.assertEqual(row["neutral_allocated_prompt_tokens"], 640)

    def test_budget_exceeded_fails_closed_without_truncation(self):
        exceeded = self.report["budget_exceeded"]
        self.assertTrue(exceeded["typed_error_raised"])
        self.assertEqual(exceeded["error_reason"], "prompt_token_budget_exceeded")
        self.assertEqual(exceeded["allocation_status"], "budget_exceeded")
        self.assertGreater(exceeded["active_prompt_tokens"], 640)
        self.assertFalse(exceeded["truncation_used"])

    def test_legacy_runtime_does_not_apply_structured_budget(self):
        self.assertEqual(
            self.report["counts"]["legacy_prompt_token_behavior_change_count"],
            0,
        )
        for row in self.report["legacy_checks"]:
            self.assertEqual(row["mode"], "unmodified")
            self.assertEqual(row["raw_prompt_tokens"], row["allocated_prompt_tokens"])

    def test_ledger_backward_compatibility_marks_all_tokens_active(self):
        ledger = ledger_module.ComputeLedger()
        ledger.record_local_generation(
            model="local-model",
            prompt_text="private prompt",
            prompt_tokens=7,
            completion_text="private reply",
            completion_tokens=2,
            generation_options={"do_sample": False},
            latency_seconds=0.1,
        )
        call = ledger.snapshot()["calls"][0]
        self.assertEqual(call["response"]["prompt_tokens"], 7)
        self.assertEqual(call["response"]["active_prompt_tokens"], 7)
        self.assertEqual(call["response"]["masked_prompt_tokens"], 0)
        self.assertFalse(ledger.snapshot()["contains_raw_prompt_or_reply"])

    def test_compute_parity_allows_active_content_length_to_be_the_intervention(self):
        left = ledger_module.ComputeLedger()
        right = ledger_module.ComputeLedger()
        for ledger, active, masked in ((left, 590, 50), (right, 579, 61)):
            ledger.record_local_generation(
                model="same-model",
                prompt_text="condition-specific private prompt",
                prompt_tokens=640,
                completion_text="private reply",
                completion_tokens=2,
                generation_options={
                    "prompt_allocation_mode": "fixed_budget_left_attention_masked",
                    "structured_prompt_token_budget": 640,
                },
                latency_seconds=0.1,
                active_prompt_tokens=active,
                masked_prompt_tokens=masked,
            )
        parity = ledger_module.compare_compute_envelopes(left.snapshot(), right.snapshot())
        self.assertTrue(parity["parity_pass"])
        self.assertFalse(parity["active_prompt_token_schedule_equal"])

    def test_openai_compatible_calls_expose_missing_active_token_data(self):
        left = ledger_module.ComputeLedger()
        right = ledger_module.ComputeLedger()
        response = SimpleNamespace(
            choices=[],
            usage=SimpleNamespace(prompt_tokens=3, completion_tokens=1, total_tokens=4),
        )
        for ledger in (left, right):
            ledger.record_chat_completion(
                {"model": "same", "messages": []},
                response,
                0.1,
            )
        parity = ledger_module.compare_compute_envelopes(left.snapshot(), right.snapshot())
        self.assertTrue(parity["parity_pass"])
        self.assertFalse(parity["active_prompt_tokens_available"])
        self.assertFalse(parity["active_prompt_token_schedule_equal"])


if __name__ == "__main__":
    unittest.main()
