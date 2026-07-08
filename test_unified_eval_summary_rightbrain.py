import unittest

from build_unified_eval_summary import _rightbrain_model_maturity_evidence


class UnifiedRightBrainSummaryTest(unittest.TestCase):
    def test_promotion_gate_is_stronger_than_single_holdout(self):
        multiseed = {
            "promotion_recommended": True,
            "promoted_adapter": "promoted-multiseed",
            "aggregate": {
                "promoted": {
                    "raw_candidate_acceptance_rate": 0.3,
                    "model_selected_case_rate": 0.1364,
                    "final_quality_pass_rate": 1.0,
                }
            },
        }

        evidence = _rightbrain_model_maturity_evidence({}, {}, multiseed)

        self.assertEqual(evidence["adapter_ref"], "promoted-multiseed")
        self.assertEqual(evidence["raw_candidate_acceptance_rate"], 0.3)
        self.assertEqual(evidence["source"], "rightbrain_runtime_adapter_multiseed_report.json")

    def test_model_loaded_holdout_is_the_maturity_source(self):
        gate = {
            "adapter_ref": "legacy",
            "summary": {
                "raw_candidate_acceptance_rate": 0.0,
                "model_selected_case_rate": 0.0,
                "final_contract_pass_rate": 1.0,
            },
        }
        holdout = {
            "load_model": True,
            "adapter_ref": "promoted",
            "summary": {
                "model_loaded": True,
                "raw_candidate_acceptance_rate": 0.5,
                "model_selected_case_rate": 0.0909,
                "final_quality_pass_rate": 1.0,
            },
        }

        evidence = _rightbrain_model_maturity_evidence(gate, holdout)

        self.assertEqual(evidence["adapter_ref"], "promoted")
        self.assertEqual(evidence["raw_candidate_acceptance_rate"], 0.5)
        self.assertEqual(evidence["source"], "rightbrain_model_surface_holdout_report.json")

    def test_missing_model_holdout_falls_back_to_gate(self):
        gate = {
            "adapter_ref": "legacy",
            "summary": {
                "raw_candidate_acceptance_rate": 0.25,
                "model_selected_case_rate": 0.1,
                "final_contract_pass_rate": 1.0,
            },
        }
        holdout = {"load_model": False, "summary": {"model_loaded": False}}

        evidence = _rightbrain_model_maturity_evidence(gate, holdout)

        self.assertEqual(evidence["adapter_ref"], "legacy")
        self.assertEqual(evidence["raw_candidate_acceptance_rate"], 0.25)
        self.assertEqual(evidence["source"], "rightbrain_model_gate_report.json")


if __name__ == "__main__":
    unittest.main()
