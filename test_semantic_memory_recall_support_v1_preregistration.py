import json
import unittest
from pathlib import Path

import memory_item_causal_intervention_v1 as mici


ROOT = Path(__file__).resolve().parent
PREREG = ROOT / "configs/semantic_memory_recall_support_v1_preregistration.json"
PARENT_LOCK = ROOT / "configs/high_confidence_memory_recall_v1_result_lock.json"


class SemanticMemoryRecallSupportV1PreregistrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payload = json.loads(PREREG.read_text(encoding="utf-8"))

    def test_parent_failure_is_locked_before_new_hypothesis(self):
        parent = json.loads(PARENT_LOCK.read_text(encoding="utf-8"))
        self.assertEqual(parent["status"], "development_rejected_locked")
        self.assertEqual(
            self.payload["parent_result"]["decision"],
            "development_reject_or_inconclusive",
        )

    def test_support_contract_changes_one_selection_variable(self):
        contract = self.payload["frozen_support_contract"]
        self.assertEqual(contract["minimum_shared_focus_unit_count"], 1)
        self.assertEqual(contract["cjk_focus_unit"], "character_bigram")
        self.assertEqual(contract["english_focus_unit"], "non_stopword_token")
        self.assertTrue(contract["unsupported_candidates_do_not_create_ambiguity"])
        self.assertFalse(contract["sensitive_memory_allowed"])

    def test_development_rejects_any_removed_target_fast_path(self):
        gates = self.payload["development_gates"]
        self.assertEqual(gates["expected_decision_run_count"], 32)
        self.assertEqual(gates["target_removed_fast_path_activation_count_max"], 0)
        self.assertLessEqual(gates["leftbrain_model_call_count_max"], 6)

    def test_contract_has_no_known_answers(self):
        serialized = json.dumps(self.payload, ensure_ascii=False).lower()
        for answer in ("金沢", "ミモザ", "銀河鉄道", "マグカップ", "リゾット"):
            self.assertNotIn(answer.lower(), serialized)

    def test_parent_result_artifacts_still_match(self):
        lock = json.loads(PARENT_LOCK.read_text(encoding="utf-8"))
        for artifact in lock["artifacts"].values():
            self.assertEqual(
                mici.file_sha256(ROOT / artifact["path"]),
                artifact["sha256"],
            )


if __name__ == "__main__":
    unittest.main()
