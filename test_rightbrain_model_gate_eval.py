import unittest

from eval_rightbrain_model_gate import _summarize


class RightBrainModelGateEvalTest(unittest.TestCase):
    def test_summary_separates_raw_model_maturity_from_final_safety(self):
        rows = [
            {
                "actual_model_policy": "allow",
                "policy_match": True,
                "generated_candidate_count": 1,
                "accepted_candidate_count": 0,
                "selected_source": "deterministic",
                "final_contract_pass": True,
                "final_language_clean": True,
                "deterministic_contract_pass": True,
                "rejection_reasons": ["semantic_slots_missing:1/3"],
                "disabled_reason": "",
            },
            {
                "actual_model_policy": "deny",
                "policy_match": True,
                "generated_candidate_count": 0,
                "accepted_candidate_count": 0,
                "selected_source": "deterministic",
                "final_contract_pass": True,
                "final_language_clean": True,
                "deterministic_contract_pass": True,
                "rejection_reasons": [],
                "disabled_reason": "high_withdrawal_risk",
            },
        ]

        summary = _summarize(rows)

        self.assertEqual(summary["raw_candidate_acceptance_rate"], 0.0)
        self.assertEqual(summary["fallback_protection_rate"], 1.0)
        self.assertEqual(summary["final_contract_pass_rate"], 1.0)
        self.assertEqual(summary["policy_match_rate"], 1.0)


if __name__ == "__main__":
    unittest.main()
