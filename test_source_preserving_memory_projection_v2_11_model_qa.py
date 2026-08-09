import copy
import json
import subprocess
import unittest

import run_source_preserving_memory_projection_v2_11_model_qa as v211


class ModelQAV211Tests(unittest.TestCase):
    def setUp(self):
        self.contract = v211.load_preregistration()

    def test_frozen_inputs_match_and_model_is_not_yet_authorized(self):
        v211.verify_frozen_inputs(self.contract)
        v211.verify_official_scorer_runtime(self.contract)
        authorization = self.contract["authorization"]
        self.assertTrue(authorization["run_local_model_evaluation_once_after_merge"])
        self.assertFalse(authorization["preregister_full_pipeline_memory_intervention"])
        self.assertFalse(authorization["runtime_change"])
        self.assertFalse(authorization["runtime_shadow"])
        self.assertFalse(authorization["production_enablement"])

    def test_local_scorer_hash_drift_is_rejected(self):
        contract = copy.deepcopy(self.contract)
        contract["frozen_local_implementation"]["scorer_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "locomo_official_qa_f1.py"):
            v211.verify_frozen_inputs(contract)

    def test_prompt_excludes_gold_and_condition_labels(self):
        case = {
            "speaker_a": "A",
            "speaker_b": "B",
            "question": "What fruit?",
            "answer": "SECRET_GOLD",
            "contexts": {"isolated": "A: mango", "adjacency": "A: mango"},
        }
        prompt = v211.build_prompt(case, "adjacency", self.contract)
        self.assertIn("What fruit?", prompt)
        self.assertIn("A: mango", prompt)
        self.assertNotIn("SECRET_GOLD", prompt)
        self.assertNotIn("adjacency", prompt)
        self.assertNotIn("evidence", prompt.lower())

    def test_call_order_is_counterbalanced(self):
        cases = [{"case_id": f"case-{index}"} for index in range(3)]
        order = [(case["case_id"], condition) for case, condition in v211.planned_calls(cases)]
        self.assertEqual(
            order,
            [
                ("case-0", "isolated"),
                ("case-0", "adjacency"),
                ("case-1", "adjacency"),
                ("case-1", "isolated"),
                ("case-2", "isolated"),
                ("case-2", "adjacency"),
            ],
        )

    def test_official_scorer_matches_known_category_two_examples(self):
        python = self.contract["official_scorer_runtime"]["python"]
        result = subprocess.run(
            [python, "locomo_official_qa_f1.py", "the mango", "Mango"],
            cwd=v211.ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertEqual(json.loads(result.stdout)["f1"], 1.0)

    def test_analysis_applies_paired_gates(self):
        contract = copy.deepcopy(self.contract)
        contract["official_scorer_runtime"]["bootstrap_samples"] = 1000
        contract["success_gates"].update(
            {
                "model_call_count_equals": 6,
                "row_count_per_condition_equals": 3,
                "complete_pair_count_equals": 3,
                "adjacency_mean_official_f1_at_least": 0.5,
                "adjacency_mean_f1_delta_vs_isolated_at_least": 0.03,
                "adjacency_only_evidence_gain_subgroup_count_equals": 3,
                "adjacency_only_evidence_gain_subgroup_f1_delta_at_least": 0.1,
            }
        )
        rows = []
        for index, (isolated, adjacency) in enumerate(((0.1, 0.9), (0.2, 0.8), (0.3, 0.7))):
            for condition, score in (("isolated", isolated), ("adjacency", adjacency)):
                rows.append(
                    {
                        "case_id": f"case-{index}",
                        "representation": condition,
                        "evidence_transition": "adjacency_only",
                        "official_f1": score,
                        "transport_error": None,
                        "prediction": "answer",
                        "eval_count": 2,
                        "production_memory_write_count": 0,
                        "physical_vrm_action_count": 0,
                    }
                )
        metrics, gates = v211.analyze_rows(rows, contract)
        self.assertEqual(metrics["complete_pair_count"], 3)
        self.assertTrue(all(gates.values()))

        incomplete_metrics, incomplete_gates = v211.analyze_rows(rows[:-1], contract)
        self.assertEqual(incomplete_metrics["complete_pair_count"], 2)
        self.assertFalse(incomplete_gates["complete_pair_count_equals"])

        wrong_subgroup = copy.deepcopy(rows)
        wrong_subgroup[1]["evidence_transition"] = "both"
        subgroup_metrics, subgroup_gates = v211.analyze_rows(wrong_subgroup, contract)
        self.assertEqual(
            subgroup_metrics["adjacency_only_evidence_gain_subgroup_count"], 2
        )
        self.assertFalse(
            subgroup_gates[
                "adjacency_only_evidence_gain_subgroup_count_equals"
            ]
        )


if __name__ == "__main__":
    unittest.main()
