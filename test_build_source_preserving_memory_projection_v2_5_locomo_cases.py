import copy
import unittest

import build_source_preserving_memory_projection_v2_5_locomo_cases as builder


def sample(sample_id, prefix):
    conversation = {
        "speaker_a": "A",
        "speaker_b": "B",
        "session_1_date_time": "2024-01-01 10:00",
        "session_1": [
            {"speaker": "A", "dia_id": f"{prefix}-1", "text": "My favorite fruit is mango."},
            {"speaker": "B", "dia_id": f"{prefix}-2", "text": "That sounds good."},
            {"speaker": "A", "dia_id": f"{prefix}-3", "text": "I buy it every Friday."},
        ],
        "session_2_date_time": "2024-01-08 10:00",
        "session_2": [
            {"speaker": "A", "dia_id": f"{prefix}-4", "text": "I cooked soup yesterday."},
            {"speaker": "B", "dia_id": f"{prefix}-5", "text": "Was the soup spicy?"},
        ],
    }
    qas = []
    for index in range(3):
        qas.append(
            {
                "question": f"What is A's favorite fruit number {index}?",
                "answer": "mango",
                "category": 2,
                "evidence": [f"{prefix}-1"],
            }
        )
    return {"sample_id": sample_id, "conversation": conversation, "qa": qas}


class LocomoV25BuilderTests(unittest.TestCase):
    def setUp(self):
        self.prereg = builder.load_preregistration()
        self.data = [sample(f"sample-{index}", f"d{index}") for index in range(10)]

    def test_conversation_split_is_deterministic_and_disjoint(self):
        first_holdout, first_reserve = builder.split_conversations(self.data, self.prereg)
        second_holdout, second_reserve = builder.split_conversations(
            list(reversed(self.data)), self.prereg
        )
        self.assertEqual(
            [row["sample_id"] for row in first_holdout],
            [row["sample_id"] for row in second_holdout],
        )
        self.assertEqual(
            [row["sample_id"] for row in first_reserve],
            [row["sample_id"] for row in second_reserve],
        )
        self.assertFalse(
            {row["sample_id"] for row in first_holdout}
            & {row["sample_id"] for row in first_reserve}
        )

    def test_manifest_has_three_cases_per_holdout_and_no_source_text(self):
        manifest = builder.build_manifest(self.data, self.prereg)
        checks = builder.validate_construction_gates(manifest, self.prereg)
        self.assertTrue(all(checks.values()))
        self.assertEqual(manifest["case_count"], 12)
        self.assertFalse(manifest["contains_official_text"])
        self.assertFalse(manifest["contains_official_answers"])
        for case in manifest["cases"]:
            self.assertNotIn("question", case)
            self.assertNotIn("answer", case)
            self.assertNotIn("text", case)

    def test_projection_is_source_preserving_and_uses_at_most_three_turns(self):
        row = self.data[0]
        indices = builder.projection_indices(
            row["conversation"],
            "session_1",
            "What is the favorite fruit?",
        )
        self.assertLessEqual(len(indices), 3)
        self.assertEqual(indices, sorted(indices))
        projected = builder.serialize_session(row["conversation"], "session_1", indices)
        for index in indices:
            self.assertIn(row["conversation"]["session_1"][index]["text"], projected)

    def test_answer_retention_is_not_an_eligibility_filter(self):
        modified = copy.deepcopy(self.data[0])
        modified["conversation"]["session_1"].extend(
            [
                {
                    "speaker": "B",
                    "dia_id": f"extra-{index}",
                    "text": "favorite fruit question fruit favorite " + str(index),
                }
                for index in range(5)
            ]
        )
        eligible = builder.eligible_cases_for_sample(modified, self.prereg)
        self.assertEqual(len(eligible), 3)

    def test_missing_official_evidence_id_is_ineligible(self):
        modified = copy.deepcopy(self.data[0])
        modified["qa"][0]["evidence"].append("missing-dialog-id")
        eligible = builder.eligible_cases_for_sample(modified, self.prereg)
        self.assertEqual(len(eligible), 2)


if __name__ == "__main__":
    unittest.main()
