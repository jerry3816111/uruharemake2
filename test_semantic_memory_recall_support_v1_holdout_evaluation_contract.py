import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONTRACT = ROOT / "configs/semantic_memory_recall_support_v1_holdout_evaluation_contract.json"


def file_sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class SemanticMemoryRecallSupportV1HoldoutEvaluationContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payload = json.loads(CONTRACT.read_text(encoding="utf-8"))

    def test_all_frozen_inputs_match(self):
        for key in ("cases", "preregistration", "development_lock", "runtime"):
            path = self.payload["inputs"][f"{key}_path"]
            expected = self.payload["inputs"][f"{key}_sha256"]
            self.assertEqual(file_sha256(ROOT / path), expected)

    def test_query_wrappers_are_fixed_only_by_language(self):
        wrappers = self.payload["query_wrapper"]
        for language in ("English", "Japanese", "Traditional Chinese"):
            self.assertEqual(wrappers[language].count("{question}"), 1)
        serialized = json.dumps(wrappers, ensure_ascii=False)
        self.assertNotIn("official-", serialized)

    def test_selector_and_condition_count_are_frozen(self):
        selector = self.payload["selector"]
        self.assertEqual(selector["minimum_shared_focus_unit_count"], 1)
        self.assertEqual(selector["model_calls"], 0)
        self.assertEqual(len(self.payload["conditions_in_order"]), 4)

    def test_contract_does_not_score_answers_or_persona(self):
        exclusions = set(self.payload["scoring_exclusions"])
        self.assertIn("official_answer content", exclusions)
        self.assertIn("persona similarity", exclusions)
        self.assertFalse(self.payload["authorization"]["production_default_enablement"])


if __name__ == "__main__":
    unittest.main()
