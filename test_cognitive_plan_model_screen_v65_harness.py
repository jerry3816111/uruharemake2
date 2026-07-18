import hashlib
import json
import unittest
from pathlib import Path

import cognitive_plan_model_screen_v65_core as core
import run_cognitive_plan_model_screen_v65 as runner


ROOT = Path(__file__).resolve().parent


class CognitivePlanModelScreenV65HarnessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = json.loads(runner.PREREG_PATH.read_text(encoding="utf-8"))
        cls.dataset = json.loads(runner.DATASET_PATH.read_text(encoding="utf-8"))

    def test_tool_schema_has_exact_required_fields_and_no_extra_properties(self):
        tool = runner._tool_schema(self.config)["function"]
        parameters = tool["parameters"]
        self.assertFalse(parameters["additionalProperties"])
        self.assertEqual(set(parameters["required"]), set(core.ALL_FIELDS))
        self.assertEqual(set(parameters["properties"]), set(core.ALL_FIELDS))

    def test_request_contains_planning_packet_but_not_expected(self):
        case = self.dataset["cases"][0]
        body = runner.build_request(self.config, case["planning_packet"], core.CONTROL)
        encoded = json.dumps(body, ensure_ascii=False)
        self.assertIn(case["planning_packet"]["user_input"], encoded)
        self.assertNotIn('"expected"', encoded)
        runner.assert_gold_isolated(case["planning_packet"])

    def test_parser_accepts_dict_and_json_string_arguments(self):
        plan = self._expected_plan(self.dataset["cases"][0])
        for arguments in (plan, json.dumps(plan)):
            parsed = core.parse_tool_response({"message": {"tool_calls": [{"function": {"name": "emit_cognitive_plan", "arguments": arguments}}]}})
            self.assertTrue(parsed["tool_parse_success"])
            self.assertEqual(parsed["plan"], plan)

    def test_parser_rejects_missing_extra_or_wrong_tool_calls(self):
        self.assertFalse(core.parse_tool_response({"message": {}})["tool_parse_success"])
        plan = self._expected_plan(self.dataset["cases"][0])
        del plan["nonliteral"]
        parsed = core.parse_tool_response({"message": {"tool_calls": [{"function": {"name": "emit_cognitive_plan", "arguments": plan}}]}})
        self.assertFalse(parsed["tool_parse_success"])

    def test_referential_validation_rejects_invented_ids(self):
        case = self.dataset["cases"][0]
        plan = self._expected_plan(case)
        self.assertTrue(core.referentially_valid(plan, case["planning_packet"], self.config))
        plan["primary_actor_id"] = "invented_person"
        self.assertFalse(core.referentially_valid(plan, case["planning_packet"], self.config))

    def test_set_scoring_is_order_independent_and_exact(self):
        case = self.dataset["cases"][3]
        plan = self._expected_plan(case)
        plan["selected_evidence_ids"] = list(reversed(plan["selected_evidence_ids"]))
        score = core.score_plan(plan, case["expected"], True, True)
        self.assertTrue(score["exact_case"])
        plan["selected_evidence_ids"].append("extra")
        score = core.score_plan(plan, case["expected"], True, False)
        self.assertFalse(score["exact_case"])

    @staticmethod
    def _expected_plan(case):
        return {key: value[:] if isinstance(value, list) else value for key, value in case["expected"].items()}

    def _synthetic_rows(self, control_correct=7, candidate4_correct=10, candidate9_correct=11, candidate9_slow=False):
        rows = []
        counts = {core.CONTROL: control_correct, core.CANDIDATES[0]: candidate4_correct, core.CANDIDATES[1]: candidate9_correct}
        for condition in core.CONDITIONS:
            for index, case in enumerate(self.dataset["cases"]):
                plan = self._expected_plan(case)
                if condition == core.CANDIDATES[0] and counts[condition] == 10:
                    exact = index not in {6, 7}
                elif condition == core.CANDIDATES[1] and counts[condition] == 11:
                    exact = index != 7
                else:
                    exact = index < counts[condition]
                if not exact:
                    plan["response_act"] = "clarify" if plan["response_act"] != "clarify" else "answer"
                rows.append({
                    "case_id": case["id"],
                    "condition": condition,
                    "plan": plan,
                    "tool_parse_success": True,
                    "referentially_valid": True,
                    "wall_seconds": 3.0 if condition == core.CANDIDATES[0] else (13.0 if condition == core.CANDIDATES[1] and candidate9_slow else 4.0),
                    "ollama_rss_bytes": 5_000_000_000 if condition == core.CANDIDATES[0] else 7_000_000_000,
                })
        return rows

    def test_selection_prefers_4b_when_9b_is_within_one_case_but_slower(self):
        report = core.analyze(self._synthetic_rows(), self.dataset, self.config)
        self.assertTrue(report["pairwise"][core.CANDIDATES[0]]["eligible"])
        self.assertTrue(report["pairwise"][core.CANDIDATES[1]]["eligible"])
        self.assertEqual(report["selected_candidate"], core.CANDIDATES[0])

    def test_no_gain_or_resource_failure_selects_no_candidate(self):
        report = core.analyze(self._synthetic_rows(control_correct=9, candidate4_correct=9, candidate9_correct=10, candidate9_slow=True), self.dataset, self.config)
        self.assertIsNone(report["selected_candidate"])
        self.assertIn("freeze_negative_result", report["decision"])

    def test_harness_lock_binds_dependencies_and_forbids_runtime_change(self):
        lock_path = ROOT / "configs/cognitive_plan_model_screen_v65_harness_lock.json"
        self.assertTrue(lock_path.exists())
        lock = json.loads(lock_path.read_text(encoding="utf-8"))
        for name, artifact in lock["frozen_artifacts"].items():
            if name == "harness_test":
                continue
            self.assertEqual(hashlib.sha256((ROOT / artifact["path"]).read_bytes()).hexdigest(), artifact["sha256"], name)
        self.assertTrue(lock["formal_run"]["candidate_inference_authorized"])
        self.assertFalse(lock["runtime_change_authorized"])


if __name__ == "__main__":
    unittest.main()
