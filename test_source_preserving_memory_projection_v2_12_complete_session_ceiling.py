import copy
import json
import subprocess
import unittest

import build_source_preserving_memory_projection_v2_5_locomo_cases as v25
import run_source_preserving_memory_projection_v2_12_complete_session_ceiling as v212


class CompleteSessionCeilingV212Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = v212.load_preregistration()

    def test_frozen_inputs_runtime_and_authorization(self):
        v212.verify_frozen_inputs(self.contract)
        import run_source_preserving_memory_projection_v2_11_model_qa as v211

        v211.verify_official_scorer_runtime(self.contract)
        authorization = self.contract["authorization"]
        self.assertTrue(authorization["run_exposed_development_diagnostic_once_after_merge"])
        self.assertFalse(authorization["preregister_projection_coherence_development"])
        self.assertFalse(authorization["preregister_model_prompt_capacity_diagnostic"])
        self.assertFalse(authorization["preregister_full_pipeline_memory_intervention"])
        self.assertFalse(authorization["runtime_change"])
        self.assertFalse(authorization["runtime_shadow"])
        self.assertFalse(authorization["production_enablement"])

    def test_local_scorer_hash_drift_is_rejected(self):
        contract = copy.deepcopy(self.contract)
        contract["frozen_local_implementation"]["scorer_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "locomo_official_qa_f1.py"):
            v212.verify_frozen_inputs(contract)

    def test_reconstruction_has_57_complete_target_sessions(self):
        data = v25.ensure_official_dataset(v25.load_preregistration())
        cases = v212.final_case_specs(data, self.contract)
        v2_11_report = v212.load_json(
            v212.ROOT / self.contract["development_authorization"]["v2_11_report_path"]
        )
        v2_11_adjacency_prompt_hashes = {
            row["case_id"]: row["prompt_sha256"]
            for row in v2_11_report["rows"]
            if row["representation"] == "adjacency"
        }
        self.assertEqual(len(cases), 57)
        self.assertEqual(len(v212.planned_calls(cases)), 114)
        self.assertEqual(
            {case["evidence_transition"] for case in cases},
            {"both", "adjacency_only", "isolated_only", "neither"},
        )
        for case in cases:
            self.assertEqual(
                v25.text_sha256(v212.build_prompt(case, "adjacency", self.contract)),
                v2_11_adjacency_prompt_hashes[case["case_id"]],
            )
            self.assertGreaterEqual(
                len(case["contexts"]["complete_session"]),
                len(case["contexts"]["adjacency"]),
            )
            self.assertLessEqual(len(case["contexts"]["complete_session"]), 5085)

    def test_posthoc_stratification_matches_locked_v2_11_rows(self):
        report = v212.load_json(
            v212.ROOT / self.contract["development_authorization"]["v2_11_report_path"]
        )
        by_case = {}
        for row in report["rows"]:
            by_case.setdefault(row["case_id"], {})[row["representation"]] = row
        observed = {}
        for transition in ("both", "adjacency_only", "isolated_only", "neither"):
            pairs = [
                pair
                for pair in by_case.values()
                if pair["adjacency"]["evidence_transition"] == transition
            ]
            deltas = [
                pair["adjacency"]["official_f1"]
                - pair["isolated"]["official_f1"]
                for pair in pairs
            ]
            key_prefix = (
                f"{transition}_evidence"
                if transition in {"both", "neither"}
                else transition
            )
            observed[f"{key_prefix}_case_count"] = len(pairs)
            observed[f"{key_prefix}_mean_f1_delta"] = round(
                sum(deltas) / len(deltas), 6
            )
        self.assertEqual(
            observed,
            self.contract["development_authorization"][
                "posthoc_zero_call_stratification"
            ],
        )

    def test_prompt_excludes_gold_and_condition_labels(self):
        case = {
            "speaker_a": "A",
            "speaker_b": "B",
            "question": "What fruit?",
            "answer": "SECRET_GOLD",
            "contexts": {
                "adjacency": "A: mango",
                "complete_session": "A: mango\nB: kiwi",
            },
        }
        prompt = v212.build_prompt(case, "complete_session", self.contract)
        self.assertIn("What fruit?", prompt)
        self.assertIn("A: mango", prompt)
        self.assertNotIn("SECRET_GOLD", prompt)
        self.assertNotIn("complete_session", prompt)
        self.assertNotIn("adjacency", prompt)
        self.assertNotIn("evidence", prompt.lower())

    def test_call_order_is_counterbalanced(self):
        cases = [{"case_id": f"case-{index}"} for index in range(3)]
        order = [
            (case["case_id"], condition)
            for case, condition in v212.planned_calls(cases)
        ]
        self.assertEqual(
            order,
            [
                ("case-0", "adjacency"),
                ("case-0", "complete_session"),
                ("case-1", "complete_session"),
                ("case-1", "adjacency"),
                ("case-2", "adjacency"),
                ("case-2", "complete_session"),
            ],
        )

    def test_official_scorer_matches_known_category_two_example(self):
        python = self.contract["official_scorer_runtime"]["python"]
        result = subprocess.run(
            [python, "locomo_official_qa_f1.py", "the mango", "Mango"],
            cwd=v212.ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertEqual(json.loads(result.stdout)["f1"], 1.0)

    def test_analysis_classifies_projection_and_low_ceiling_outcomes(self):
        contract = copy.deepcopy(self.contract)
        contract["official_scorer_runtime"]["bootstrap_samples"] = 1000
        contract["development_authorization"]["v2_11_adjacency_mean_f1"] = 0.2
        contract["success_gates"].update(
            {
                "model_call_count_equals": 6,
                "row_count_per_condition_equals": 3,
                "complete_pair_count_equals": 3,
            }
        )

        def rows_for(complete_scores):
            rows = []
            for index, complete_score in enumerate(complete_scores):
                for condition, score in (
                    ("adjacency", 0.2),
                    ("complete_session", complete_score),
                ):
                    rows.append(
                        {
                            "case_id": f"case-{index}",
                            "representation": condition,
                            "official_f1": score,
                            "transport_error": None,
                            "prediction": f"answer-{condition}-{index}",
                            "prompt_eval_count": 100,
                            "eval_count": 2,
                            "latency_seconds": 0.1,
                            "production_memory_write_count": 0,
                            "physical_vrm_action_count": 0,
                        }
                    )
            return rows

        passing_rows = rows_for((0.8, 0.7, 0.6))
        passing_metrics, passing_gates = v212.analyze_rows(passing_rows, contract)
        self.assertTrue(all(passing_gates.values()))
        self.assertEqual(
            v212.classify_decision(passing_metrics, passing_gates, contract),
            contract["decision_rules"]["all_gates_pass"],
        )

        low_rows = rows_for((0.3, 0.3, 0.3))
        low_metrics, low_gates = v212.analyze_rows(low_rows, contract)
        self.assertFalse(low_gates["complete_session_mean_official_f1_at_least"])
        self.assertEqual(
            v212.classify_decision(low_metrics, low_gates, contract),
            contract["decision_rules"][
                "integrity_pass_but_complete_f1_below_0_45"
            ],
        )

        incomplete_metrics, incomplete_gates = v212.analyze_rows(
            passing_rows[:-1], contract
        )
        self.assertFalse(incomplete_gates["complete_pair_count_equals"])
        self.assertEqual(
            v212.classify_decision(incomplete_metrics, incomplete_gates, contract),
            contract["decision_rules"]["any_integrity_gate_fails"],
        )


if __name__ == "__main__":
    unittest.main()
