import json
import unittest
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = (
    ROOT
    / "configs"
    / "reflection_classifier_v1_external_holdout_construction_preregistration.json"
)
CONFIG = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


class ReflectionClassifierV1ExternalHoldoutConstructionPreregistrationTest(
    unittest.TestCase
):
    def test_selected_ids_and_balance_are_frozen(self):
        cases = CONFIG["selected_cases"]
        self.assertEqual(len(cases), CONFIG["fixed_counts"]["case_count"])
        self.assertEqual(len({case["id"] for case in cases}), len(cases))
        self.assertEqual(len({case["sentence_id"] for case in cases}), len(cases))
        self.assertEqual(
            Counter(case["expected_type"] for case in cases),
            CONFIG["fixed_counts"]["per_class"],
        )
        self.assertEqual(
            Counter(case["language"] for case in cases),
            CONFIG["fixed_counts"]["per_language"],
        )

    def test_source_and_label_claims_are_separated(self):
        source = CONFIG["external_source"]
        self.assertEqual(source["name"], "Tatoeba")
        self.assertTrue(source["stable_api"].startswith("https://api.tatoeba.org/v1/"))
        self.assertFalse(source["official_label_claim"])
        self.assertIn("not labels supplied", source["label_note"])

    def test_evaluation_is_forbidden_until_dataset_and_harness_freeze(self):
        self.assertFalse(
            CONFIG[
                "candidate_or_legacy_inference_before_dataset_and_harness_freeze_authorized"
            ]
        )
        self.assertFalse(CONFIG["runtime_memory_write_authorized"])
        self.assertFalse(CONFIG["post_run_case_editing_authorized"])
        self.assertFalse(CONFIG["post_run_case_exclusion_authorized"])
        self.assertFalse(CONFIG["post_run_threshold_change_authorized"])

    def test_success_requires_absolute_and_matched_improvement(self):
        gates = CONFIG["success_gates"]
        self.assertEqual(gates["candidate_correct_count_min"], 28)
        self.assertEqual(gates["candidate_none_correct"], 8)
        self.assertEqual(gates["regression_vs_legacy_count_max"], 0)
        self.assertGreaterEqual(gates["newly_correct_vs_legacy_count_min"], 4)


if __name__ == "__main__":
    unittest.main()
