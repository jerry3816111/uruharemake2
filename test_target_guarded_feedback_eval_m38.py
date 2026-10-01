import unittest

from uruha_target_guarded_feedback_eval_m38 import summarize, validate_reserve


class TargetGuardedFeedbackEvalM38Tests(unittest.TestCase):
    def test_validator_rejects_duplicate_and_invalid_targets(self):
        cases = []
        for index in range(18):
            category = (
                "unique_target_correction"
                if index < 9
                else "ordinary_negation"
                if index < 15
                else "targetless_rejection"
            )
            language = ("zh", "en", "ja")[index % 3]
            cases.append(
                {
                    "case_id": f"dev-{index}",
                    "language": language,
                    "category": category,
                    "previous_policy": "playful_tease",
                    "feedback_input": f"dev input {index}",
                    "expected_linkage": "contradicted" if index < 9 else "uncertain",
                    "expected_replacement_policy": "listen_presence" if index < 9 else None,
                }
            )
        dataset = {
            "schema": "uruha_m38_target_guarded_multiscript_feedback_reserve_v1",
            "cases": cases,
        }
        protocol = {"schema": "uruha_m38_target_guarded_multiscript_feedback_protocol_v1"}
        prefreeze = {"dataset": {"sha256": "d"}, "protocol": {"sha256": "p"}}
        good = validate_reserve(dataset, protocol, prefreeze, m36_dataset={"cases": []})
        self.assertTrue(good["passed"])
        dataset["cases"][1]["case_id"] = dataset["cases"][0]["case_id"]
        dataset["cases"][2]["expected_replacement_policy"] = "playful_tease"
        bad = validate_reserve(dataset, protocol, prefreeze, m36_dataset={"cases": []})
        self.assertFalse(bad["passed"])
        self.assertIn("duplicate_or_empty_case_id", bad["errors"])
        self.assertTrue(any(error.startswith("invalid_correction_target") for error in bad["errors"]))

    def test_summary_keeps_linkage_and_revision_separate(self):
        rows = []
        categories = ["unique_target_correction"] * 9 + ["ordinary_negation"] * 6 + ["targetless_rejection"] * 3
        for index, category in enumerate(categories):
            target = "listen_presence" if category == "unique_target_correction" else None
            rows.append(
                {
                    "category": category,
                    "expected_replacement_policy": target,
                    "baseline": {"outcome_correct": index % 2 == 0},
                    "system": {
                        "outcome_correct": True,
                        "linked": category == "unique_target_correction",
                        "replacement_policy": target,
                        "m34_revision_correct": True,
                    },
                    "raw_dialogue_persisted": False,
                    "unverified_mental_fact_write_count": 0,
                }
            )
        protocol = {
            "frozen_gates": {
                "overall_linkage_accuracy_min": 1.0,
                "unique_target_correction_recall_min": 1.0,
                "replacement_policy_accuracy_min": 1.0,
                "ordinary_negation_false_linkage_max": 0,
                "targetless_rejection_false_linkage_max": 0,
                "m34_contradiction_revision_accuracy_min": 1.0,
                "raw_dialogue_persistence_max": 0,
                "unverified_mental_fact_write_max": 0,
                "p95_linkage_latency_seconds_max": 0.01,
            }
        }
        metrics, gates = summarize(rows, [0.001] * 18, protocol)
        self.assertEqual(metrics["system_linkage_outcome_accuracy"], 1.0)
        self.assertEqual(metrics["ordinary_negation_false_linkage_count"], 0)
        self.assertEqual(metrics["system_m34_revision_accuracy"], 1.0)
        self.assertTrue(all(gates.values()))


if __name__ == "__main__":
    unittest.main()
