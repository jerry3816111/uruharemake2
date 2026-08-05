import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PREREG = ROOT / "configs/source_preserving_memory_projection_v2_5_locomo_fresh_holdout_preregistration.json"
AUDIT = ROOT / "reports/source_preserving_memory_projection_v2_5_locomo_provenance_audit.json"


class LocomoV25PreregistrationTests(unittest.TestCase):
    def setUp(self):
        self.prereg = json.loads(PREREG.read_text(encoding="utf-8"))
        self.audit = json.loads(AUDIT.read_text(encoding="utf-8"))

    def test_source_is_pinned_and_matches_audit(self):
        source = self.prereg["official_source"]
        audited = self.audit["official_source"]
        self.assertEqual(len(source["repository_commit"]), 40)
        self.assertEqual(len(source["dataset_sha256"]), 64)
        self.assertEqual(source["dataset_sha256"], audited["dataset_sha256"])
        self.assertEqual(source["dataset_bytes"], audited["dataset_bytes"])
        self.assertEqual(source["license"], "CC BY-NC 4.0")

    def test_partition_is_conversation_disjoint(self):
        partition = self.prereg["dataset_partition"]
        self.assertEqual(partition["unit"], "whole_conversation")
        self.assertEqual(partition["holdout_conversation_count"], 4)
        self.assertEqual(partition["reserve_conversation_count"], 6)
        self.assertEqual(partition["cross_split_conversation_overlap"], 0)

    def test_call_count_and_case_math_are_frozen(self):
        selection = self.prereg["case_selection"]
        controlled = self.prereg["controlled_variables"]
        self.assertEqual(selection["question_count"], 12)
        self.assertEqual(selection["cases_per_holdout_conversation"], 3)
        expected = (
            selection["question_count"]
            * controlled["records_per_question"]
            * len(controlled["representations"])
        )
        self.assertEqual(expected, 48)
        self.assertEqual(controlled["planned_model_call_count"], expected)

    def test_no_gold_fields_are_allowed_in_model_prompt(self):
        excluded = set(self.prereg["controlled_variables"]["prompt_excludes"])
        self.assertIn("official answer", excluded)
        self.assertIn("official evidence IDs", excluded)
        self.assertIn("expected support verdict", excluded)

    def test_authorization_stops_before_generation(self):
        authorization = self.prereg["authorization"]
        self.assertTrue(authorization["build_frozen_case_manifest_once_after_merge"])
        self.assertFalse(authorization["run_fresh_generation_once_after_case_contract_freeze"])
        self.assertFalse(authorization["runtime_change"])
        self.assertFalse(authorization["runtime_shadow"])
        self.assertFalse(authorization["production_enablement"])


if __name__ == "__main__":
    unittest.main()
