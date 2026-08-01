import json
import unittest

import run_rightbrain_compact_japanese_payload_v1 as experiment
import uruha_surface_payload_v2 as surface_payload


def summary(valid, pollution=0, semantics=0):
    return {
        "strict_valid_generation_count": valid,
        "rejection_families": {
            "language_or_script_pollution": pollution,
            "required_semantics_missing": semantics,
        },
    }


class CompactJapanesePayloadExperimentTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.preregistration = json.loads(
            experiment.DEFAULT_PREREGISTRATION.read_text(encoding="utf-8")
        )

    def test_single_variable_and_compute_are_frozen(self):
        self.assertEqual(
            self.preregistration["single_changed_variable"],
            "structured_surface_payload_serialization",
        )
        frozen = self.preregistration["frozen_model_and_runtime"]
        self.assertEqual(frozen["base_model"], "Qwen/Qwen2.5-7B-Instruct")
        self.assertIsNone(frozen["adapter"])
        self.assertEqual(frozen["prompt_allocation_budget_tokens"], 640)
        self.assertEqual(frozen["candidate_count"], 1)
        self.assertFalse(frozen["repair_enabled"])

    def test_classification_matches_preregistered_boundaries(self):
        self.assertEqual(
            experiment.classify_result(
                summary(2, pollution=4, semantics=7),
                summary(5, pollution=2, semantics=4),
            ),
            "compact_payload_supported",
        )
        self.assertEqual(
            experiment.classify_result(summary(2), summary(4)),
            "compact_payload_partial_gain",
        )
        self.assertEqual(
            experiment.classify_result(summary(2), summary(3)),
            "compact_payload_no_gain",
        )
        self.assertEqual(
            experiment.classify_result(summary(3), summary(2)),
            "compact_payload_regression",
        )

    def test_cross_serializer_check_allows_only_prompt_representation(self):
        def artifact(prompt_hash, active):
            return {
                "ledger_snapshots": {
                    provider: {
                        "calls": [
                            {
                                "item_id": "case",
                                "condition_id": provider,
                                "stage": "rightbrain_surface_generation",
                                "backend": "transformers_local",
                                "model": "Qwen/Qwen2.5-7B-Instruct",
                                "request": {
                                    "prompt_sha256": prompt_hash,
                                    "options": {"temperature": 0.82},
                                    "allocation": {
                                        "allocated_prompt_tokens": 640,
                                        "active_prompt_tokens": active,
                                    },
                                },
                                "response": {"prompt_tokens": 640},
                            }
                        ]
                    }
                    for provider in experiment.pilot.PROVIDERS
                }
            }

        artifacts = {
            surface_payload.LEGACY_JSON_V1: artifact("legacy", 620),
            surface_payload.COMPACT_JAPANESE_V2: artifact("compact", 380),
        }
        checks = experiment._cross_serializer_control_checks(artifacts)
        self.assertTrue(
            all(row["controls_equal_except_serialization"] for row in checks)
        )
        self.assertTrue(all(row["prompt_hash_difference_exact"] for row in checks))
        self.assertTrue(all(row["compact_active_tokens_lower_each"] for row in checks))

    def test_no_broad_authorization_is_preregistered(self):
        non_authorizations = set(self.preregistration["non_authorizations"])
        self.assertIn("production default change", non_authorizations)
        self.assertIn("persona similarity claim", non_authorizations)
        self.assertIn("human blind persona rating", non_authorizations)
        self.assertIn("model training", non_authorizations)


if __name__ == "__main__":
    unittest.main()
