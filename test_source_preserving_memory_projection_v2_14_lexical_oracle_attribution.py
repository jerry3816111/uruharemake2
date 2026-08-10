import copy
import inspect
import unittest

import analyze_source_preserving_memory_projection_v2_14_lexical_oracle_attribution as v214


class LexicalOracleAttributionV214Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = v214.load_preregistration()

    def test_frozen_inputs_and_authorization(self):
        v214.verify_frozen_inputs(self.contract)
        authorization = self.contract["authorization"]
        self.assertTrue(authorization["run_zero_call_attribution_once_after_merge"])
        self.assertFalse(
            authorization[
                "preregister_source_disjoint_deterministic_span_selection_mechanism"
            ]
        )
        self.assertFalse(authorization["preregister_fresh_model_generation"])
        self.assertFalse(
            authorization["preregister_full_pipeline_memory_intervention"]
        )
        self.assertFalse(authorization["runtime_change"])
        self.assertFalse(authorization["runtime_shadow"])
        self.assertFalse(authorization["production_enablement"])

    def test_official_token_oracle_and_tie_break(self):
        oracle = v214.best_contiguous_source_span(
            "Time: 2023-01-01\nA: the red mango arrived\nB: mango",
            "red mango",
        )
        self.assertEqual(oracle["official_f1"], 1.0)
        self.assertEqual(oracle["source_unit_index"], 1)
        self.assertEqual(oracle["span_token_count"], 2)
        self.assertEqual(oracle["whole_context_answer_token_recall"], 1.0)

    def test_oracle_distinguishes_partial_and_absent_source_evidence(self):
        partial = v214.best_contiguous_source_span(
            "A: mango", "mango orchard trip tomorrow"
        )
        absent = v214.best_contiguous_source_span(
            "A: kiwi", "mango orchard trip tomorrow"
        )
        self.assertGreater(partial["whole_context_answer_token_recall"], 0)
        self.assertEqual(absent["whole_context_answer_token_recall"], 0)
        threshold = self.contract["lexical_oracle"]["case_quality_threshold"]
        self.assertEqual(
            v214.availability_category(partial, threshold),
            "partial_lexical_overlap",
        )
        self.assertEqual(
            v214.availability_category(absent, threshold), "no_lexical_overlap"
        )

    def test_attribution_is_ordered_and_exhaustive(self):
        threshold = self.contract["lexical_oracle"]["case_quality_threshold"]
        exact = {
            "official_f1": 1.0,
            "whole_context_answer_token_recall": 1.0,
        }
        partial = {
            "official_f1": 0.2,
            "whole_context_answer_token_recall": 0.5,
        }
        absent = {
            "official_f1": 0.0,
            "whole_context_answer_token_recall": 0.0,
        }
        self.assertEqual(
            v214.attribute_failure(0.6, exact, threshold), "model_quality_pass"
        )
        self.assertEqual(
            v214.attribute_failure(0.0, exact, threshold),
            "lexical_answer_available_model_miss",
        )
        self.assertEqual(
            v214.attribute_failure(0.0, partial, threshold),
            "partial_lexical_evidence_inference_or_composition_needed",
        )
        self.assertEqual(
            v214.attribute_failure(0.0, absent, threshold),
            "no_lexical_answer_evidence_in_target_session",
        )

    def test_question_operator_priority(self):
        self.assertEqual(v214.question_operator("When did it happen?"), "temporal")
        self.assertEqual(v214.question_operator("How many cats?"), "quantity")
        self.assertEqual(v214.question_operator("Where was it?"), "location")
        self.assertEqual(v214.question_operator("Who said that?"), "person")
        self.assertEqual(v214.question_operator("Did they go?"), "boolean")
        self.assertEqual(v214.question_operator("What color was it?"), "entity_or_attribute")

    def test_decision_rules_do_not_authorize_generation(self):
        contract = copy.deepcopy(self.contract)
        gates = {"integrity": True}
        base = {
            "conditions": {
                v214.CANDIDATE: {
                    "attribution_counts": {
                        "lexical_answer_available_model_miss": 29,
                        "partial_lexical_evidence_inference_or_composition_needed": 28,
                    }
                }
            }
        }
        self.assertEqual(
            v214.classify_decision(base, gates, contract),
            contract["decision_rules"]["candidate_lexical_available_miss_at_least_29"],
        )
        base["conditions"][v214.CANDIDATE]["attribution_counts"] = {
            "lexical_answer_available_model_miss": 28,
            "partial_lexical_evidence_inference_or_composition_needed": 29,
        }
        self.assertEqual(
            v214.classify_decision(base, gates, contract),
            contract["decision_rules"][
                "candidate_partial_or_absent_lexical_evidence_at_least_29"
            ],
        )

    def test_summarize_integrity_gate_mapping(self):
        rows = []
        for index in range(57):
            rows.append(
                {
                    "case_id": f"case-{index}",
                    "question_operator": "other",
                    "availability_category": "exact_lexical_span",
                    "lexical_oracle": {
                        "official_f1": 1.0,
                        "whole_context_answer_token_recall": 1.0,
                    },
                    "conditions": {
                        model: {
                            "official_f1": 0.5,
                            "model_minus_lexical_oracle_f1": -0.5,
                            "attribution": "model_quality_pass",
                        }
                        for model in (v214.CONTROL, v214.CANDIDATE)
                    },
                }
            )
        audit = {
            f"{v214.CONTROL}_rows": 57,
            f"{v214.CANDIDATE}_rows": 57,
            "prompt_hash_matches": 114,
            "answer_hash_matches": 114,
            "official_f1_matches": 114,
        }
        source_report = {
            "metrics": {
                "production_memory_write_count": 0,
                "physical_vrm_action_count": 0,
            }
        }
        _, gates = v214.summarize_rows(
            rows, audit, source_report, self.contract
        )
        self.assertTrue(all(gates.values()))

    def test_analyzer_has_no_model_or_network_call_path(self):
        source = inspect.getsource(v214)
        self.assertNotIn("urllib", source)
        self.assertNotIn("requests", source)
        self.assertNotIn("ensure_official_dataset", source)
        self.assertNotIn("post_json", source)
        self.assertNotIn("call_candidate_model", source)

    def test_frozen_dataset_load_is_offline_and_hash_verified(self):
        data = v214.load_official_dataset_offline()
        self.assertEqual(len(data), 10)


if __name__ == "__main__":
    unittest.main()
