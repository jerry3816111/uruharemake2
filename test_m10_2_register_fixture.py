import json
import unittest
from pathlib import Path

from build_m10_2_register_fixture import LABELS, build_fixture, validate_fixture


ROOT = Path(__file__).resolve().parent


class M102RegisterFixtureTests(unittest.TestCase):
    def test_fixture_is_balanced_and_deterministic(self):
        fixture = build_fixture()
        self.assertTrue(validate_fixture(fixture)["valid"])
        self.assertEqual(validate_fixture(fixture)["language_counts"], {"zh": 6, "en": 6, "ja": 6})
        self.assertTrue(all(count == 3 for count in validate_fixture(fixture)["label_counts"].values()))
        saved = json.loads((ROOT / "datasets/m10_2_behavior_preserving_register_synthetic_fixture_v1.json").read_text())
        self.assertEqual(saved, fixture)
        self.assertEqual(set(saved["taxonomy"]["labels"]), set(LABELS))

    def test_fixture_discloses_post_failure_remediation_scope(self):
        fixture = build_fixture()
        boundary = fixture["source_disjointness"]
        self.assertEqual(boundary["m9_m10_event_overlap_count"], 0)
        self.assertTrue(boundary["created_after_m10_failure_type_known"])
        self.assertFalse(boundary["m10_outputs_used_as_cases_or_demonstrations"])
        self.assertFalse(fixture["formal_target_claim"])


if __name__ == "__main__":
    unittest.main()
