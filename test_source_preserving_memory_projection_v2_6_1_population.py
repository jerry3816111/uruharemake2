import json
import unittest

import build_source_preserving_memory_projection_v2_6_1_population_cases as v261
import build_source_preserving_memory_projection_v2_6_corrected_oracle_cases as v26
from test_build_source_preserving_memory_projection_v2_5_locomo_cases import sample


class ExposedPopulationV261Tests(unittest.TestCase):
    def setUp(self):
        self.base = v26.load_preregistration()
        self.revision = v261.load_preregistration()
        self.data = [sample(f"sample-{index}", f"d{index}") for index in range(10)]
        ids = [f"sample-{index}" for index in range(4)]
        self.base["controlled_variables"]["exposed_sample_ids"] = ids
        self.revision["controlled_variables"]["exposed_sample_ids"] = ids
        self.revision["controlled_variables"]["expected_case_count_by_sample"] = {
            sample_id: 3 for sample_id in ids
        }
        self.revision["controlled_variables"]["question_count"] = 12
        self.revision["construction_gates"]["question_count_equals"] = 12

    def test_only_population_allocation_changes(self):
        self.assertEqual(
            self.revision["independent_variable"]["name"],
            "exposed_development_population_allocation",
        )
        controlled = self.revision["controlled_variables"]
        self.assertEqual(
            controlled["projection_representation"],
            "unchanged top-three isolated turns by lexical overlap",
        )
        self.assertEqual(controlled["reserve_sample_access_count"], 0)
        self.assertEqual(controlled["model_calls"], 0)

    def test_manifest_uses_entire_corrected_population_without_text(self):
        manifest = v261.build_manifest(self.data, self.base, self.revision)
        checks = v261.validate_gates(manifest, self.revision)
        self.assertTrue(all(checks.values()))
        self.assertEqual(manifest["case_count"], 12)
        self.assertEqual(manifest["reserve_sample_access_count"], 0)
        payload = json.dumps(manifest)
        self.assertNotIn("My favorite fruit is mango", payload)

    def test_population_drift_fails_closed(self):
        self.revision["controlled_variables"]["expected_case_count_by_sample"][
            "sample-0"
        ] = 2
        with self.assertRaisesRegex(ValueError, "population drift"):
            v261.build_manifest(self.data, self.base, self.revision)

    def test_authorization_stops_before_new_projection(self):
        authorization = self.revision["authorization"]
        self.assertTrue(authorization["build_exposed_population_manifest_once_after_merge"])
        self.assertFalse(authorization["preregister_adjacency_projection_after_baseline_lock"])
        self.assertFalse(authorization["model_generation"])
        self.assertFalse(authorization["use_reserve_conversations"])
        self.assertFalse(authorization["runtime_change"])


if __name__ == "__main__":
    unittest.main()
