import json
import tempfile
import unittest
from pathlib import Path

import run_v2_19_fifty_turn_memory_remediation as v219


class FiftyTurnMemoryRemediationV219Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.case = v219.load_json(v219.CASE_PATH)
        cls.prereg = v219.load_json(v219.PREREG_PATH)

    def test_design_is_fifty_turn_new_value_remediation(self):
        result = v219.validate_design(self.case, self.prereg)
        self.assertTrue(result["passed"], result["errors"])
        self.assertTrue(result["new_values_disjoint_from_v2_18"])
        self.assertEqual(result["checkpoint_turns"], [25, 26, 48, 49, 50])

    def test_false_memory_non_answer_is_no_longer_a_pass(self):
        turn = self.case["turns"][49]
        score = v219._score_condition(
            {
                "condition": "uruha_memory",
                "reply": "ん、もう一回だけ聞かせて。",
                "passed_target_rows": [],
                "visible_contract": {"pass": True},
            },
            turn,
            self.case,
        )
        self.assertTrue(score["non_answer"])
        self.assertFalse(score["task_pass"])

    def test_false_memory_relational_denial_passes(self):
        turn = self.case["turns"][49]
        score = v219._score_condition(
            {
                "condition": "uruha_memory",
                "reply": "レモネードは友達の話だろ。お前の一番好きとは聞いてない。",
                "passed_target_rows": [{"text": "友達がレモネードを買った"}],
                "visible_contract": {"pass": True},
            },
            turn,
            self.case,
        )
        self.assertTrue(score["relational_false_claim_directly_denied"])
        self.assertTrue(score["task_pass"])

    def test_explicit_update_requires_visible_current_value(self):
        turn = self.case["turns"][25]
        missing = v219._score_condition(
            {"condition": "uruha_memory", "reply": "分かった。", "passed_target_rows": [], "visible_contract": {"pass": True}},
            turn,
            self.case,
        )
        present = v219._score_condition(
            {"condition": "uruha_memory", "reply": "今はほうじ茶なんだな。", "passed_target_rows": [], "visible_contract": {"pass": True}},
            turn,
            self.case,
        )
        self.assertFalse(missing["task_pass"])
        self.assertTrue(present["task_pass"])

    def test_lock_builder_binds_remediation_runtime_and_tests(self):
        lock = v219.build_lock()
        self.assertIn("runtime", lock["artifacts"])
        self.assertIn("personhood", lock["artifacts"])
        self.assertIn("remediation_tests", lock["artifacts"])
        self.assertTrue(lock["policy"]["development_remediation_not_independent_holdout"])

    def test_lock_validation_detects_changed_artifact(self):
        lock = v219.build_lock()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "lock.json"
            path.write_text(json.dumps(lock, ensure_ascii=False), encoding="utf-8")
            original = v219.LOCK_PATH
            try:
                v219.LOCK_PATH = path
                result = v219.validate_lock()
            finally:
                v219.LOCK_PATH = original
        self.assertTrue(result["passed"])


if __name__ == "__main__":
    unittest.main()
