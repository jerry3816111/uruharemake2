import copy
import unittest

import evaluate_source_preserving_memory_projection_v2_7_adjacency as v27
from test_build_source_preserving_memory_projection_v2_5_locomo_cases import sample


class AdjacencyProjectionV27Tests(unittest.TestCase):
    def test_algorithm_uses_two_anchors_and_original_neighbors(self):
        row = sample("sample-x", "x")
        conversation = row["conversation"]
        indices, anchors = v27.adjacency_indices(
            conversation, "session_1", "favorite fruit"
        )
        self.assertEqual(len(anchors), 2)
        self.assertEqual(indices, sorted(set(indices)))
        self.assertLessEqual(len(indices), 6)
        for anchor in anchors:
            self.assertIn(anchor, indices)

    def test_adjacency_can_recover_answer_next_to_anchor(self):
        row = sample("sample-x", "x")
        conversation = copy.deepcopy(row["conversation"])
        conversation["session_1"] = [
            {"speaker": "A", "dia_id": "q", "text": "Which fruit is your favorite?"},
            {"speaker": "B", "dia_id": "a", "text": "Mango."},
            {"speaker": "A", "dia_id": "n1", "text": "The weather is warm."},
            {"speaker": "B", "dia_id": "n2", "text": "Yes, very warm."},
        ]
        indices, anchors = v27.adjacency_indices(
            conversation, "session_1", "What is the favorite fruit?"
        )
        self.assertEqual(anchors[0], 0)
        self.assertIn(1, indices)
        self.assertIn("Mango", v27.selected_turn_text(conversation, "session_1", indices))

    def test_preregistration_freezes_one_variable_and_zero_model_calls(self):
        prereg = v27.load_json(v27.PREREG)
        self.assertEqual(
            prereg["independent_variable"]["name"],
            "source_projection_turn_selection",
        )
        self.assertEqual(prereg["adjacency_algorithm"]["anchor_count"], 2)
        self.assertEqual(prereg["adjacency_algorithm"]["window_offsets"], [-1, 0, 1])
        self.assertEqual(prereg["controlled_variables"]["model_calls"], 0)
        self.assertEqual(prereg["controlled_variables"]["reserve_sample_access_count"], 0)

    def test_success_thresholds_are_stric_and_runtime_remains_closed(self):
        prereg = v27.load_json(v27.PREREG)
        gates = prereg["success_gates"]
        self.assertEqual(gates["adjacency_target_answer_retention_count_at_least"], 8)
        self.assertEqual(gates["retention_delta_vs_control_at_least"], 4)
        self.assertEqual(gates["mean_target_projection_character_ratio_at_most"], 0.5)
        authorization = prereg["authorization"]
        self.assertFalse(authorization["preregister_reserve_fresh_holdout_after_pass"])
        self.assertFalse(authorization["model_generation"])
        self.assertFalse(authorization["runtime_change"])


if __name__ == "__main__":
    unittest.main()
