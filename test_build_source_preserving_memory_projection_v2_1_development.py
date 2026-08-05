import copy
import inspect
import json
import unittest

import build_source_preserving_memory_projection_v2_1_development as builder


class BuildSourcePreservingMemoryProjectionV21DevelopmentTests(unittest.TestCase):
    def test_effective_preregistration_changes_only_limits_and_id(self):
        base = {
            "experiment_id": "v2",
            "case_selection": {
                "source_size_rules": {
                    "maximum_target_characters": 7000,
                    "maximum_hard_negative_characters": 7000,
                    "maximum_combined_visible_characters": 14000,
                }
            },
            "fixed": {"projection_top_k": 3},
        }
        revision = {
            "experiment_id": "v2_1",
            "effective_overrides": {
                "case_selection.source_size_rules.maximum_target_characters": 14000,
                "case_selection.source_size_rules.maximum_hard_negative_characters": 10000,
                "case_selection.source_size_rules.maximum_combined_visible_characters": 22000,
            },
        }
        original = copy.deepcopy(base)
        effective = builder.effective_preregistration(base, revision)
        self.assertEqual(base, original)
        self.assertEqual(effective["experiment_id"], "v2_1")
        self.assertEqual(effective["fixed"], base["fixed"])
        self.assertEqual(
            effective["case_selection"]["source_size_rules"]["maximum_target_characters"],
            14000,
        )

    def test_builder_has_no_model_or_runtime_calls(self):
        source = inspect.getsource(builder)
        self.assertNotIn("ollama_chat", source)
        self.assertNotIn("requests.post", source)
        self.assertNotIn("uruha_brain", source)

    def test_revision_authorizes_cases_but_not_model_evaluation(self):
        revision = json.loads(builder.REVISION_PREREG.read_text(encoding="utf-8"))
        self.assertTrue(revision["authorization"]["build_source_preserving_cases"])
        self.assertFalse(revision["authorization"]["run_model_evaluation"])


if __name__ == "__main__":
    unittest.main()
