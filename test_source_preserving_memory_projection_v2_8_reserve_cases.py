import copy
import json
import unittest

import build_source_preserving_memory_projection_v2_8_reserve_cases as v28
from test_build_source_preserving_memory_projection_v2_5_locomo_cases import sample


class ReserveCasesV28Tests(unittest.TestCase):
    def setUp(self):
        self.prereg = v28.load_preregistration()
        self.data = [sample(f"sample-{index}", f"d{index}") for index in range(10)]
        self.prereg["reserve_partition"]["excluded_exposed_sample_ids"] = [
            f"sample-{index}" for index in range(4)
        ]

    def test_partition_is_deterministic_four_plus_two(self):
        fresh, final = v28.partition_reserve(self.data, self.prereg)
        reversed_fresh, reversed_final = v28.partition_reserve(
            list(reversed(self.data)), self.prereg
        )
        self.assertEqual(
            [row["sample_id"] for row in fresh],
            [row["sample_id"] for row in reversed_fresh],
        )
        self.assertEqual(
            [row["sample_id"] for row in final],
            [row["sample_id"] for row in reversed_final],
        )
        self.assertEqual(len(fresh), 4)
        self.assertEqual(len(final), 2)
        self.assertFalse(
            {row["sample_id"] for row in fresh} & {row["sample_id"] for row in final}
        )

    def test_balanced_selection_uses_eight_cases(self):
        fresh, _final = v28.partition_reserve(self.data, self.prereg)
        selected, counts = v28.balanced_select(fresh, self.prereg)
        self.assertEqual(len(selected), 8)
        selected_counts = {
            sample_id: sum(row[0] == sample_id for row in selected) for sample_id in counts
        }
        self.assertLessEqual(max(selected_counts.values()), 3)
        self.assertGreaterEqual(sum(value > 0 for value in selected_counts.values()), 3)

    def test_manifest_excludes_official_text_and_final_payload(self):
        manifest = v28.build_manifest(self.data, self.prereg)
        checks, metrics = v28.validate_gates(manifest, self.prereg)
        for name in (
            "reserve_pool_count_equals",
            "fresh_holdout_conversation_count_equals",
            "final_reserve_conversation_count_equals",
            "partition_overlap_equals",
            "question_count_equals",
            "represented_conversation_count_at_least",
            "maximum_cases_per_conversation_at_most",
            "all_corrected_source_oracles_valid",
            "all_adjacency_turns_are_exact_sources",
            "final_reserve_case_selection_payload_access_count_equals",
            "model_calls_equal",
        ):
            self.assertTrue(checks[name], name)
        self.assertEqual(metrics["isolated_target_answer_retention_count"], 8)
        self.assertEqual(metrics["adjacency_target_answer_retention_count"], 8)
        self.assertEqual(
            manifest["partition"][
                "final_reserve_case_selection_payload_access_count"
            ],
            0,
        )
        self.assertEqual(manifest["case_count"], 8)
        payload = json.dumps(manifest)
        self.assertNotIn("My favorite fruit is mango", payload)
        for case in manifest["cases"]:
            self.assertNotIn("question", case)
            self.assertNotIn("answer", case)
            self.assertNotIn("text", case)

    def test_final_reserve_payload_cannot_affect_case_selection(self):
        original = v28.build_manifest(self.data, self.prereg)
        _fresh, final = v28.partition_reserve(self.data, self.prereg)
        final_ids = {row["sample_id"] for row in final}
        modified = copy.deepcopy(self.data)
        for row in modified:
            if row["sample_id"] in final_ids:
                row["conversation"] = {
                    "session_1": [
                        {
                            "speaker": "sealed",
                            "dia_id": "sealed",
                            "text": "changed final reserve payload",
                        }
                    ]
                }
                row["qa"] = []
        rebuilt = v28.build_manifest(modified, self.prereg)
        self.assertEqual(original, rebuilt)

    def test_short_fixture_cannot_pass_formal_effect_and_compression_gates(self):
        manifest = v28.build_manifest(self.data, self.prereg)
        checks, metrics = v28.validate_gates(manifest, self.prereg)
        self.assertEqual(metrics["retention_delta_vs_isolated"], 0)
        self.assertFalse(checks["adjacency_retention_delta_vs_isolated_at_least"])
        self.assertFalse(checks["mean_target_adjacency_character_ratio_at_most"])
        self.assertFalse(checks["mean_all_record_adjacency_character_ratio_at_most"])

    def test_all_frozen_dependencies_match_and_drift_is_rejected(self):
        v28.verify_frozen_dependencies(self.prereg)
        drifted = copy.deepcopy(self.prereg)
        drifted["development_authorization"]["report_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "frozen source hash drift"):
            v28.verify_frozen_dependencies(drifted)

    def test_official_source_contract_matches_v25(self):
        v28.verify_official_source_contract(self.prereg, v28.v25.load_preregistration())
        drifted = copy.deepcopy(self.prereg)
        drifted["official_source"]["dataset_bytes"] += 1
        with self.assertRaisesRegex(ValueError, "official source contract drift"):
            v28.verify_official_source_contract(
                drifted, v28.v25.load_preregistration()
            )

    def test_answer_retention_is_not_selection_filter(self):
        modified = copy.deepcopy(self.data)
        for row in modified:
            row["conversation"]["session_1"].extend(
                [
                    {
                        "speaker": "B",
                        "dia_id": f"distractor-{index}",
                        "text": "favorite fruit question favorite fruit " + str(index),
                    }
                    for index in range(5)
                ]
            )
        fresh, _final = v28.partition_reserve(modified, self.prereg)
        selected, _counts = v28.balanced_select(fresh, self.prereg)
        self.assertEqual(len(selected), 8)

    def test_model_and_runtime_are_not_authorized(self):
        authorization = self.prereg["authorization"]
        self.assertTrue(authorization["build_fresh_case_manifest_once_after_merge"])
        self.assertFalse(authorization["freeze_model_evaluation_contract_after_construction_pass"])
        self.assertFalse(authorization["run_model_generation"])
        self.assertFalse(
            authorization["use_final_reserve_conversations_for_case_selection"]
        )
        self.assertFalse(authorization["runtime_change"])


if __name__ == "__main__":
    unittest.main()
