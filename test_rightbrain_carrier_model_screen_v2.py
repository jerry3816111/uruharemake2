import copy
import unittest

import analyze_rightbrain_carrier_model_screen_v2 as analysis


def explicit_summary(*, strict, raw_pollution, missing, polite, latency):
    return {
        "nonempty_raw_generation_count": 10,
        "strict_valid_generation_count": strict,
        "raw_language_or_script_pollution_count": raw_pollution,
        "final_required_semantics_missing_count": missing,
        "final_polite_register_drift_count": polite,
        "warm_wall_latency_median_seconds": latency,
        "model_blob_bytes": 4_000_000_000,
    }


class RightbrainCarrierModelScreenV2Test(unittest.TestCase):
    def test_sequential_preregistration_is_frozen_and_bound(self):
        preregistration = analysis.load_json(analysis.PREREGISTRATION_PATH)
        checks, _ = analysis.validate_preregistration(preregistration)
        self.assertTrue(all(checks.values()), checks)
        calibration = analysis.load_json(analysis.CALIBRATION_PATH)
        self.assertEqual(calibration["status"], "stopped_before_candidate_inference")
        self.assertEqual(
            calibration["invalidity"]["candidate_model_generation_call_count"], 0
        )

    def test_control_raw_pollution_is_explicitly_recomputed(self):
        artifact = analysis.load_json(
            analysis.generation.CONDITION_ARTIFACTS[analysis.CONTROL_ID]
        )
        self.assertEqual(analysis.raw_pollution_count(artifact["generations"]), 4)
        self.assertEqual(
            analysis.explicit_summary(artifact)[
                "final_required_semantics_missing_count"
            ],
            2,
        )

    def test_candidate_gate_is_feasible_but_joint(self):
        control = explicit_summary(
            strict=6,
            raw_pollution=4,
            missing=2,
            polite=2,
            latency=2.2623,
        )
        passing = analysis.candidate_gate(
            explicit_summary(
                strict=9,
                raw_pollution=2,
                missing=1,
                polite=2,
                latency=4.0,
            ),
            control,
            True,
        )
        failing = analysis.candidate_gate(
            explicit_summary(
                strict=9,
                raw_pollution=2,
                missing=2,
                polite=2,
                latency=4.0,
            ),
            control,
            True,
        )
        self.assertTrue(passing["passed"], passing)
        self.assertFalse(failing["passed"])
        self.assertFalse(failing["requirements"]["semantic_failure_reduction"])

    def test_four_billion_parameter_model_requires_comparable_quality(self):
        gates = {condition_id: {"passed": True} for condition_id in analysis.CANDIDATE_IDS}
        summaries = {
            "qwen3_5_4b_q4_candidate": explicit_summary(
                strict=9,
                raw_pollution=1,
                missing=1,
                polite=1,
                latency=2.0,
            ),
            "qwen3_5_9b_q4_candidate": explicit_summary(
                strict=10,
                raw_pollution=1,
                missing=1,
                polite=1,
                latency=4.0,
            ),
        }
        selected, _ = analysis.select_candidate(gates, summaries)
        self.assertEqual(selected, "qwen3_5_4b_q4_candidate")

        weaker = copy.deepcopy(summaries)
        weaker["qwen3_5_4b_q4_candidate"]["raw_language_or_script_pollution_count"] = 2
        selected, _ = analysis.select_candidate(gates, weaker)
        self.assertEqual(selected, "qwen3_5_9b_q4_candidate")


if __name__ == "__main__":
    unittest.main()
