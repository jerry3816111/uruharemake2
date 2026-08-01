import copy
import json
import tempfile
import unittest
from pathlib import Path

import run_rightbrain_carrier_model_screen_v1 as screen


ROOT = Path(__file__).resolve().parent


def summary(*, strict, pollution, missing, polite, latency):
    return {
        "nonempty_raw_generation_count": 10,
        "strict_valid_generation_count": strict,
        "rejection_families": {
            "language_or_script_pollution": pollution,
            "required_semantics_missing": missing,
            "polite_register_drift": polite,
        },
        "warm_wall_latency_median_seconds": latency,
    }


class RightbrainCarrierModelScreenV1Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.preregistration = screen.load_json(screen.PREREGISTRATION_PATH)
        cls.cases = screen.load_json(screen.CASES_PATH)["cases"]

    def test_frozen_sources_assets_and_payloads_are_present(self):
        checks, details = screen.validate_frozen_inputs(
            self.preregistration,
            deep_model_hash=False,
        )
        self.assertTrue(all(checks.values()), checks)
        self.assertEqual(len(details["payload_rows"]), 10)
        self.assertEqual(set(details["model_assets"]), set(screen.CONDITION_ARTIFACTS))

    def test_preflight_performs_no_model_generation(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "preflight.json"
            report = screen.run_preflight(deep_model_hash=False, output=output)
        self.assertEqual(report["status"], "preflight_passed")
        self.assertEqual(report["actual_model_generation_call_count"], 0)
        self.assertEqual(report["production_memory_write_count"], 0)
        self.assertEqual(report["formal_persona_score_count"], 0)

    def test_ollama_request_contract_disables_qwen35_thinking_only(self):
        options = self.preregistration["runtime"]["options"]
        messages = [{"role": "system", "content": "x"}, {"role": "user", "content": "y"}]
        control = screen.chat_body(
            self.preregistration["model_inventory"]["qwen2_5_7b_q4_control"],
            messages,
            options,
            7,
        )
        candidate = screen.chat_body(
            self.preregistration["model_inventory"]["qwen3_5_4b_q4_candidate"],
            messages,
            options,
            7,
        )
        self.assertNotIn("think", control)
        self.assertIs(candidate["think"], False)
        self.assertEqual(control["options"], candidate["options"])
        self.assertEqual(control["messages"], candidate["messages"])

    def test_current_gate_accepts_semantic_casual_japanese_and_rejects_pollution(self):
        case = self.cases[0]
        valid = screen.score_raw_generation(
            "配信してる。みんなよろしく。",
            case,
            "structured_target_public_persona",
        )
        invalid = screen.score_raw_generation(
            "配信快来围观。みんなよろしく。",
            case,
            "structured_target_public_persona",
        )
        self.assertTrue(valid["strict_valid"], valid)
        self.assertFalse(invalid["strict_valid"])
        self.assertIn("nonstandard_cjk_surface", invalid["rejection_reasons"])

    def test_gate_requires_joint_quality_and_resource_improvement(self):
        control = summary(strict=2, pollution=4, missing=7, polite=4, latency=1.0)
        model_info = self.preregistration["model_inventory"][
            "qwen3_5_4b_q4_candidate"
        ]
        passing = screen.candidate_gate(
            summary(strict=6, pollution=2, missing=4, polite=4, latency=3.0),
            control,
            model_info,
            True,
        )
        failing = screen.candidate_gate(
            summary(strict=6, pollution=2, missing=4, polite=5, latency=3.0),
            control,
            model_info,
            True,
        )
        self.assertTrue(passing["passed"])
        self.assertFalse(failing["passed"])
        self.assertFalse(failing["requirements"]["polite_drift_not_worse"])

    def test_four_billion_parameter_candidate_is_preferred_only_when_comparable(self):
        gates = {
            "qwen3_5_4b_q4_candidate": {"passed": True},
            "qwen3_5_9b_q4_candidate": {"passed": True},
        }
        comparable = {
            "qwen3_5_4b_q4_candidate": summary(
                strict=7, pollution=1, missing=2, polite=1, latency=2.0
            ),
            "qwen3_5_9b_q4_candidate": summary(
                strict=8, pollution=1, missing=2, polite=1, latency=4.0
            ),
        }
        selected, decision = screen.select_candidate(gates, comparable)
        self.assertEqual(selected, "qwen3_5_4b_q4_candidate")
        self.assertIn("authorize_disjoint", decision)

        weaker = copy.deepcopy(comparable)
        weaker["qwen3_5_4b_q4_candidate"]["strict_valid_generation_count"] = 6
        selected, _ = screen.select_candidate(gates, weaker)
        self.assertEqual(selected, "qwen3_5_9b_q4_candidate")

    def test_preregistration_contains_no_answer_key_or_production_authorization(self):
        text = json.dumps(self.preregistration, ensure_ascii=False).lower()
        self.assertNotIn("fixed_reply", text)
        self.assertFalse(
            self.preregistration["authorizations"]["change_production_default"]
        )
        self.assertFalse(
            self.preregistration["authorizations"]["claim_persona_similarity"]
        )


if __name__ == "__main__":
    unittest.main()
