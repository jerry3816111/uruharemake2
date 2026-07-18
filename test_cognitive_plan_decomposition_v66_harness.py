import hashlib
import json
import unittest
from pathlib import Path

import cognitive_plan_decomposition_v66_core as core
import run_cognitive_plan_decomposition_v66 as runner


ROOT = Path(__file__).resolve().parent


class CognitivePlanDecompositionV66HarnessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = json.loads(runner.PREREG_PATH.read_text(encoding="utf-8"))
        cls.dataset = json.loads(runner.DATASET_PATH.read_text(encoding="utf-8"))

    def test_tool_schemas_have_exact_non_overlapping_responsibilities(self):
        full = runner.full_tool_schema(self.config)["function"]["parameters"]
        selection = runner.selection_tool_schema(self.config)["function"]["parameters"]
        decision = runner.decision_tool_schema(self.config)["function"]["parameters"]
        self.assertEqual(set(full["required"]), set(core.ALL_FIELDS))
        self.assertEqual(set(selection["required"]), set(core.SELECTION_FIELDS))
        self.assertEqual(set(decision["required"]), set(core.DECISION_FIELDS))
        self.assertFalse(set(selection["required"]) & set(decision["required"]))
        self.assertEqual(set(selection["required"]) | set(decision["required"]), set(core.ALL_FIELDS))
        self.assertFalse(full["additionalProperties"])

    def test_requests_contain_no_gold_or_case_metadata(self):
        case = self.dataset["cases"][0]
        requests = (
            runner.build_full_request(self.config, case["planning_packet"]),
            runner.build_selection_request(self.config, case["planning_packet"]),
        )
        for body in requests:
            encoded = json.dumps(body, ensure_ascii=False)
            self.assertIn(case["planning_packet"]["user_input"], encoded)
            self.assertNotIn('"expected"', encoded)
            self.assertNotIn(case["id"], encoded)
            self.assertNotIn(case["scenario_family"], encoded)

    def test_decision_stage_receives_only_selected_context(self):
        case = self.dataset["cases"][2]
        selection = {key: self._copy(case["expected"][key]) for key in core.SELECTION_FIELDS}
        payload = runner.build_decision_payload(case["planning_packet"], selection)
        encoded = json.dumps(payload, ensure_ascii=False)
        self.assertIn("memory_fever_current", encoded)
        self.assertIn("memory_morning_run_old", encoded)
        self.assertNotIn("普段は夕方に長く走るのが好き", encoded)
        self.assertEqual(payload["suppressed_memory_ids"], ["memory_morning_run_old"])

    def test_parser_accepts_dict_and_json_string_arguments(self):
        expected = self._expected_plan(self.dataset["cases"][0])
        for arguments in (expected, json.dumps(expected)):
            response = {"message": {"tool_calls": [{"function": {"name": "emit_cognitive_plan", "arguments": arguments}}]}}
            parsed = core.parse_tool_response(response, "emit_cognitive_plan", core.ALL_FIELDS)
            self.assertTrue(parsed["tool_parse_success"])
            self.assertEqual(parsed["values"], expected)

    def test_parser_rejects_missing_or_wrong_tool(self):
        expected = self._expected_plan(self.dataset["cases"][0])
        del expected["nonliteral"]
        response = {"message": {"tool_calls": [{"function": {"name": "emit_cognitive_plan", "arguments": expected}}]}}
        self.assertFalse(core.parse_tool_response(response, "emit_cognitive_plan", core.ALL_FIELDS)["tool_parse_success"])
        response["message"]["tool_calls"][0]["function"]["name"] = "wrong_tool"
        self.assertFalse(core.parse_tool_response(response, "emit_cognitive_plan", core.ALL_FIELDS)["tool_parse_success"])

    def test_referential_validation_requires_complete_memory_partition(self):
        case = self.dataset["cases"][2]
        plan = self._expected_plan(case)
        self.assertTrue(core.referentially_valid(plan, case["planning_packet"], self.config))
        plan["suppressed_memory_ids"] = []
        self.assertFalse(core.referentially_valid(plan, case["planning_packet"], self.config))

    def test_scoring_separates_selection_and_decision(self):
        case = self.dataset["cases"][0]
        plan = self._expected_plan(case)
        plan["response_act"] = "clarify"
        score = core.score_plan(plan, case["expected"], True, True)
        self.assertTrue(score["selection_stage_exact"])
        self.assertFalse(score["decision_stage_exact"])
        self.assertFalse(score["exact_case"])

    def test_run_case_uses_one_or_two_calls_as_preregistered(self):
        case = self.dataset["cases"][0]
        expected = self._expected_plan(case)

        def fake_call(_config, body):
            function = body["tools"][0]["function"]
            fields = function["parameters"]["required"]
            arguments = {field: self._copy(expected[field]) for field in fields}
            response = {
                "message": {"tool_calls": [{"function": {"name": function["name"], "arguments": arguments}}]},
                "prompt_eval_count": 10,
                "eval_count": 5,
            }
            return response, 1.0, None

        one = runner.run_case(self.config, case["planning_packet"], core.ONE_CALL, fake_call)
        control = runner.run_case(self.config, case["planning_packet"], core.MATCHED_CONTROL, fake_call)
        treatment = runner.run_case(self.config, case["planning_packet"], core.TREATMENT, fake_call)
        self.assertEqual(one["transport_attempts"], 1)
        self.assertEqual(control["transport_attempts"], 2)
        self.assertEqual(treatment["transport_attempts"], 2)
        self.assertEqual(treatment["plan"], expected)

    def test_analysis_accepts_only_a_large_matched_control_gain(self):
        report = core.analyze(self._synthetic_rows(treatment_mode="passes"), self.dataset, self.config)
        pair = report["pairwise"]["treatment_vs_matched_control"]
        self.assertTrue(pair["eligible"], pair["checks"])
        self.assertEqual(pair["newly_correct"], 4)
        self.assertEqual(pair["regressions"], 0)
        self.assertIn("authorize_fresh", report["decision"])

    def test_analysis_rejects_extra_compute_without_decomposition_gain(self):
        report = core.analyze(self._synthetic_rows(treatment_mode="no_gain"), self.dataset, self.config)
        pair = report["pairwise"]["treatment_vs_matched_control"]
        self.assertFalse(pair["eligible"])
        self.assertFalse(pair["checks"]["newly_correct"])
        self.assertIn("freeze_result", report["decision"])

    def test_harness_lock_binds_dependencies_and_forbids_runtime_change(self):
        lock_path = ROOT / "configs/cognitive_plan_decomposition_v66_harness_lock.json"
        self.assertTrue(lock_path.exists())
        lock = json.loads(lock_path.read_text(encoding="utf-8"))
        for name, artifact in lock["frozen_artifacts"].items():
            if name == "harness_test":
                continue
            digest = hashlib.sha256((ROOT / artifact["path"]).read_bytes()).hexdigest()
            self.assertEqual(digest, artifact["sha256"], name)
        self.assertTrue(lock["formal_run"]["model_inference_authorized"])
        self.assertFalse(lock["runtime_change_authorized"])

    @staticmethod
    def _copy(value):
        return value[:] if isinstance(value, list) else value

    @classmethod
    def _expected_plan(cls, case):
        return {key: cls._copy(value) for key, value in case["expected"].items()}

    def _synthetic_rows(self, treatment_mode):
        rows = []
        for condition in core.CONDITIONS:
            for index, case in enumerate(self.dataset["cases"]):
                plan = self._expected_plan(case)
                if condition == core.ONE_CALL:
                    exact = index < 3
                elif condition == core.MATCHED_CONTROL:
                    exact = index < (9 if treatment_mode == "no_gain" else 5)
                elif treatment_mode == "no_gain":
                    exact = index < 9
                else:
                    exact = index < 9

                if not exact:
                    if condition == core.TREATMENT and treatment_mode == "passes" and index == 9:
                        plan["response_act"] = "clarify" if plan["response_act"] != "clarify" else "answer"
                    elif condition == core.TREATMENT and treatment_mode == "passes" and index == 10:
                        plan["nonliteral"] = not plan["nonliteral"]
                    else:
                        plan["response_act"] = "clarify" if plan["response_act"] != "clarify" else "answer"
                        plan["nonliteral"] = not plan["nonliteral"]
                rows.append({
                    "case_id": case["id"],
                    "condition": condition,
                    "plan": plan,
                    "all_required_tools_parse": True,
                    "referentially_valid": True,
                    "wall_seconds": 6.0 if condition == core.ONE_CALL else 12.0,
                    "transport_attempts": 1 if condition == core.ONE_CALL else 2,
                    "ollama_rss_bytes": 5_500_000_000,
                })
        return rows


if __name__ == "__main__":
    unittest.main()
