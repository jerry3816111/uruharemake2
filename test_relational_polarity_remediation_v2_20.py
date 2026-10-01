import unittest

import run_v2_20_relational_polarity_remediation as v220


class RelationalPolarityRemediationV220Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.case = v220.load_json(v220.CASE_PATH)
        cls.prereg = v220.load_json(v220.PREREG_PATH)
        cls.raw = v220.load_json(v220.V219_RAW_PATH)

    def test_design_reuses_exact_v219_case_and_frozen_outputs(self):
        result = v220.validate_design(self.case, self.prereg, self.raw)
        self.assertTrue(result["passed"], result["errors"])
        self.assertEqual(result["checkpoint_count"], 5)
        self.assertFalse(self.prereg["claim_boundary"]["independent_semantic_holdout"])

    def test_frozen_lookup_keeps_all_three_reference_conditions(self):
        lookup = v220._frozen_condition_lookup(self.raw)
        self.assertIn((50, "uruha_memory"), lookup)
        self.assertIn((50, "plain_recent"), lookup)
        self.assertIn((50, "plain_full"), lookup)

    def test_withdrawal_scorer_accepts_natural_direct_denial(self):
        turn = self.case["turns"][48]
        score = v220._score_condition(
            {
                "condition": "uruha_memory",
                "reply": "麦茶はもう前の情報だろ。今の好みとして見てない。",
                "passed_target_rows": [{"text": "dislikes=麦茶"}],
                "visible_contract": {"pass": True},
            },
            turn,
            self.case,
        )
        self.assertTrue(score["withdrawn_old_value_directly_denied"])
        self.assertFalse(score["stale_value_revival"])
        self.assertTrue(score["task_pass"])

    def test_relational_positive_surface_still_fails_strict_gate(self):
        turn = self.case["turns"][49]
        score = v220._score_condition(
            {
                "condition": "uruha_memory",
                "reply": "レモネードが好きなんだな。",
                "passed_target_rows": [{"text": "友達がレモネードを買った"}],
                "visible_contract": {"pass": True},
            },
            turn,
            self.case,
        )
        self.assertFalse(score["relational_false_claim_directly_denied"])
        self.assertFalse(score["task_pass"])


if __name__ == "__main__":
    unittest.main()
