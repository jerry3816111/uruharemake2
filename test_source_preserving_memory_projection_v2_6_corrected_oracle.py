import copy
import json
import unittest
from pathlib import Path

import build_source_preserving_memory_projection_v2_6_corrected_oracle_cases as v26
from test_build_source_preserving_memory_projection_v2_5_locomo_cases import sample


ROOT = Path(__file__).resolve().parent


class CorrectedOracleV26Tests(unittest.TestCase):
    def setUp(self):
        self.prereg = v26.load_preregistration()
        self.data = [sample(f"sample-{index}", f"d{index}") for index in range(10)]
        self.prereg["controlled_variables"]["exposed_sample_ids"] = [
            f"sample-{index}" for index in range(4)
        ]

    def test_only_independent_variable_is_oracle_scope(self):
        independent = self.prereg["independent_variable"]
        self.assertEqual(independent["name"], "answer_membership_oracle_scope")
        self.assertIn("original non-empty dialogue-turn text only", independent["intervention"])
        self.assertEqual(
            self.prereg["controlled_variables"]["projection_representation"],
            "unchanged V2.5 top-three isolated turns by lexical overlap",
        )

    def test_metadata_only_answer_is_rejected(self):
        row = copy.deepcopy(self.data[0])
        for qa in row["qa"]:
            qa["answer"] = "2024-01-01 10:00"
        self.assertEqual(v26.eligible_cases_for_sample(row, self.prereg), [])

    def test_turn_text_answer_is_eligible(self):
        eligible = v26.eligible_cases_for_sample(self.data[0], self.prereg)
        self.assertEqual(len(eligible), 3)
        self.assertTrue(
            v26.answer_in_turn_text(
                self.data[0]["conversation"], eligible[0]["target_key"], "mango"
            )
        )

    def test_manifest_is_text_free_and_reserve_untouched(self):
        manifest = v26.build_manifest(self.data, self.prereg)
        checks = v26.validate_gates(manifest, self.prereg)
        self.assertTrue(all(checks.values()))
        self.assertEqual(manifest["case_count"], 12)
        self.assertEqual(manifest["reserve_sample_access_count"], 0)
        payload = json.dumps(manifest)
        self.assertNotIn("My favorite fruit is mango", payload)
        for case in manifest["cases"]:
            self.assertNotIn("question", case)
            self.assertNotIn("answer", case)
            self.assertNotIn("text", case)

    def test_authorization_stops_before_projection_revision(self):
        authorization = self.prereg["authorization"]
        self.assertTrue(authorization["build_corrected_exposed_development_cases_once_after_merge"])
        self.assertFalse(authorization["evaluate_new_projection_algorithm"])
        self.assertFalse(authorization["model_generation"])
        self.assertFalse(authorization["use_reserve_conversations"])
        self.assertFalse(authorization["runtime_change"])


if __name__ == "__main__":
    unittest.main()
