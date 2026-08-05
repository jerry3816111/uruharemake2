import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PREREG = ROOT / "configs/high_confidence_memory_recall_v1_preregistration.json"


class HighConfidenceMemoryRecallV1PreregistrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payload = json.loads(PREREG.read_text(encoding="utf-8"))

    def test_contract_freezes_one_runtime_variable(self):
        self.assertEqual(
            self.payload["single_runtime_variable"].count("enable"),
            1,
        )
        contract = self.payload["frozen_selection_contract"]
        self.assertEqual(contract["minimum_top_score"], 0.55)
        self.assertEqual(contract["minimum_top_runner_up_margin"], 0.15)
        self.assertTrue(contract["explicit_recall_required"])
        self.assertTrue(contract["speakability_should_use_explicitly_required"])
        self.assertFalse(contract["sensitive_memory_allowed"])

    def test_known_cases_are_development_only(self):
        development = self.payload["development_checks"]
        self.assertIn("not fresh generalization evidence", development["purpose"])
        self.assertTrue(
            self.payload["fresh_holdout_requirement"]["required_before_production_authorization"]
        )
        self.assertFalse(self.payload["authorization"]["production_default_enablement"])

    def test_runtime_must_not_receive_case_answers(self):
        self.assertTrue(
            self.payload["frozen_selection_contract"][
                "case_ids_or_expected_answers_in_runtime_forbidden"
            ]
        )
        serialized = json.dumps(self.payload, ensure_ascii=False).lower()
        for answer in ("金沢", "ミモザ", "銀河鉄道", "マグカップ", "リゾット"):
            self.assertNotIn(answer.lower(), serialized)


if __name__ == "__main__":
    unittest.main()
