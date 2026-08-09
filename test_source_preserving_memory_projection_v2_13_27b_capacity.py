import copy
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import run_source_preserving_memory_projection_v2_13_27b_capacity as v213


class ModelCapacityV213Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = v213.load_preregistration()

    def test_frozen_inputs_runtime_model_and_authorization(self):
        v213.verify_frozen_inputs(self.contract)
        import run_source_preserving_memory_projection_v2_11_model_qa as v211

        v211.verify_official_scorer_runtime(self.contract)
        v213.verify_candidate_model(self.contract)
        authorization = self.contract["authorization"]
        self.assertTrue(authorization["run_57_candidate_calls_once_after_merge"])
        self.assertFalse(
            authorization["preregister_new_external_dataset_capacity_validation"]
        )
        self.assertFalse(authorization["preregister_prompt_carrier_diagnostic"])
        self.assertFalse(authorization["preregister_full_pipeline_memory_intervention"])
        self.assertFalse(authorization["runtime_change"])
        self.assertFalse(authorization["runtime_shadow"])
        self.assertFalse(authorization["production_enablement"])

    def test_formal_run_requires_candidate_to_start_unloaded(self):
        with patch.object(v213, "running_models", return_value=[]):
            v213.verify_candidate_model_unloaded(self.contract)
        with patch.object(
            v213,
            "running_models",
            return_value=[{"name": self.contract["candidate_model"]["model"]}],
        ):
            with self.assertRaisesRegex(ValueError, "cold-start latency"):
                v213.verify_candidate_model_unloaded(self.contract)

    def test_historical_controls_and_prompts_are_frozen(self):
        cases, controls, v212_contract = v213.reconstruct_cases_and_controls(
            self.contract
        )
        self.assertEqual(len(cases), 57)
        self.assertEqual(len(controls), 57)
        for case in cases:
            prompt = v213.v212.build_prompt(case, "complete_session", v212_contract)
            self.assertEqual(
                controls[case["case_id"]]["prompt_sha256"],
                v213.v25.text_sha256(prompt),
            )

    def test_candidate_prompts_exclude_gold_and_prior_results(self):
        case = {
            "speaker_a": "A",
            "speaker_b": "B",
            "question": "What fruit?",
            "answer": "SECRET_GOLD",
            "contexts": {"complete_session": "A: mango\nB: kiwi"},
        }
        v212_contract = v213.v212.load_preregistration()
        prompt = v213.v212.build_prompt(case, "complete_session", v212_contract)
        self.assertIn("What fruit?", prompt)
        self.assertIn("A: mango", prompt)
        self.assertNotIn("SECRET_GOLD", prompt)
        self.assertNotIn("qwen3.5", prompt)
        self.assertNotIn("F1", prompt)
        self.assertNotIn("evidence", prompt.lower())

    def test_official_scorer_matches_known_category_two_example(self):
        python = self.contract["official_scorer_runtime"]["python"]
        result = subprocess.run(
            [python, "locomo_official_qa_f1.py", "the mango", "Mango"],
            cwd=v213.ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertEqual(json.loads(result.stdout)["f1"], 1.0)

    def test_candidate_checkpoint_resumes_without_repeating_calls(self):
        case = {
            "case_id": "case-0",
            "sample_alias": "sample",
            "qa_index": 0,
            "question": "What fruit?",
            "answer": "mango",
            "speaker_a": "A",
            "speaker_b": "B",
            "contexts": {"complete_session": "A: mango"},
        }
        v212_contract = v213.v212.load_preregistration()
        calls = []

        def fake_model(prompt, contract):
            calls.append(prompt)
            return {
                "prediction": "mango",
                "prompt_eval_count": 20,
                "eval_count": 1,
                "load_duration_ns": 1,
                "prompt_eval_duration_ns": 1,
                "eval_duration_ns": 1,
                "total_duration_ns": 3,
                "latency_seconds": 0.1,
            }

        with tempfile.TemporaryDirectory() as directory:
            raw_path = Path(directory) / "raw.jsonl"
            first = v213.execute_candidate_calls(
                [case],
                self.contract,
                v212_contract,
                raw_path,
                model_call=fake_model,
            )
            second = v213.execute_candidate_calls(
                [case],
                self.contract,
                v212_contract,
                raw_path,
                model_call=fake_model,
            )
        self.assertEqual(len(first), 1)
        self.assertEqual(first, second)
        self.assertEqual(len(calls), 1)

    def test_analysis_classifies_capacity_and_resource_outcomes(self):
        contract = copy.deepcopy(self.contract)
        contract["official_scorer_runtime"]["bootstrap_samples"] = 1000
        contract["success_gates"].update(
            {
                "new_candidate_model_call_count_equals": 3,
                "historical_control_row_count_equals": 3,
                "combined_row_count_equals": 6,
                "complete_pair_count_equals": 3,
            }
        )

        def rows_for(candidate_scores, candidate_latency=10.0):
            rows = []
            for index, candidate_score in enumerate(candidate_scores):
                for condition, score, source, latency in (
                    (v213.CONTROL, 0.2, "locked_v2_12_historical_control", 4.0),
                    (
                        v213.CANDIDATE,
                        candidate_score,
                        "fresh_v2_13_candidate_call",
                        candidate_latency,
                    ),
                ):
                    rows.append(
                        {
                            "case_id": f"case-{index}",
                            "model_condition": condition,
                            "row_source": source,
                            "official_f1": score,
                            "transport_error": None,
                            "prediction": f"answer-{condition}-{index}",
                            "prompt_eval_count": 100,
                            "eval_count": 2,
                            "latency_seconds": latency,
                            "production_memory_write_count": 0,
                            "physical_vrm_action_count": 0,
                        }
                    )
            return rows

        passing_rows = rows_for((0.8, 0.7, 0.6))
        passing_metrics, passing_gates = v213.analyze_rows(passing_rows, contract)
        self.assertTrue(all(passing_gates.values()))
        self.assertEqual(
            v213.classify_decision(passing_gates, contract),
            contract["decision_rules"]["all_gates_pass"],
        )

        low_rows = rows_for((0.3, 0.3, 0.3))
        low_metrics, low_gates = v213.analyze_rows(low_rows, contract)
        self.assertFalse(low_gates["candidate_mean_official_f1_at_least"])
        self.assertEqual(
            v213.classify_decision(low_gates, contract),
            contract["decision_rules"][
                "integrity_pass_but_candidate_f1_below_0_45"
            ],
        )

        slow_rows = rows_for((0.8, 0.7, 0.6), candidate_latency=50.0)
        slow_metrics, slow_gates = v213.analyze_rows(slow_rows, contract)
        self.assertFalse(slow_gates["candidate_max_latency_seconds_at_most"])
        self.assertEqual(
            v213.classify_decision(slow_gates, contract),
            contract["decision_rules"]["any_integrity_or_resource_gate_fails"],
        )


if __name__ == "__main__":
    unittest.main()
