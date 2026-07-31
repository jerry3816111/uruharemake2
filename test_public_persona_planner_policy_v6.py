import copy
import hashlib
import json
import unittest
from pathlib import Path

import public_persona_contract_v3 as v3
import public_persona_planner_policy_v6 as planner
from run_public_persona_planner_policy_v6 import (
    CONDITIONS,
    build_payload,
    build_request,
    planner_projection,
    protected_logic,
)
from uruha_brain_mac import RightBrain


ROOT = Path(__file__).resolve().parent
DATASET_PATH = ROOT / "datasets/public_persona_contract_v3_development.json"
PREREGISTRATION_PATH = ROOT / "configs/public_persona_planner_policy_v6_preregistration.json"
LOCK_PATH = ROOT / "configs/public_persona_planner_policy_v6_harness_lock.json"


class PublicPersonaPlannerPolicyV6Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dataset = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
        cls.preregistration = json.loads(PREREGISTRATION_PATH.read_text(encoding="utf-8"))
        cls.right_brain = RightBrain(load_model=False)

    def test_blueprints_cover_all_and_only_v3_contexts(self):
        self.assertEqual(set(planner.PLANNING_BLUEPRINTS), set(v3.POLICIES))

    def test_compiler_does_not_mutate_input(self):
        source = copy.deepcopy(self.dataset["cases"][0]["logic"])
        frozen = copy.deepcopy(source)
        planner.apply_planning_policy(source)
        self.assertEqual(source, frozen)

    def test_active_context_compiles_order_and_boundary(self):
        logic, trace = planner.apply_planning_policy(self.dataset["cases"][12]["logic"])
        self.assertEqual(trace["status"], "active_development_hypothesis")
        self.assertEqual(len(logic["human_speech_plan"]["content_units"]), 3)
        self.assertEqual(len(logic["human_speech_plan"]["speech_moves"]), 3)
        self.assertIn("epistemic_boundary", logic["human_speech_plan"])
        self.assertTrue(any("見て" in group for group in logic["required_marker_groups"]))

    def test_inactive_context_returns_exact_logic_and_payload(self):
        for case in self.dataset["cases"]:
            if case["context"] in v3.POLICIES:
                continue
            logic, trace = planner.apply_planning_policy(case["logic"])
            self.assertEqual(logic, case["logic"], case["case_id"])
            self.assertEqual(trace["status"], "inactive_no_supported_context")
            control = build_payload(self.right_brain, case, CONDITIONS[0])
            treatment = build_payload(self.right_brain, case, CONDITIONS[1])
            self.assertEqual(control[2], treatment[2], case["case_id"])

    def test_active_cases_change_planner_projection(self):
        for case in self.dataset["cases"]:
            if case["context"] not in v3.POLICIES:
                continue
            control = build_payload(self.right_brain, case, CONDITIONS[0])
            treatment = build_payload(self.right_brain, case, CONDITIONS[1])
            self.assertNotEqual(
                planner_projection(control[0]), planner_projection(treatment[0]), case["case_id"]
            )

    def test_protected_core_memory_and_action_are_identical(self):
        for case in self.dataset["cases"]:
            control = build_payload(self.right_brain, case, CONDITIONS[0])
            treatment = build_payload(self.right_brain, case, CONDITIONS[1])
            self.assertEqual(
                protected_logic(control[0]), protected_logic(treatment[0]), case["case_id"]
            )

    def test_static_rightbrain_persona_carrier_is_identical(self):
        for case in self.dataset["cases"]:
            control = build_payload(self.right_brain, case, CONDITIONS[0])[3]
            treatment = build_payload(self.right_brain, case, CONDITIONS[1])[3]
            self.assertEqual(
                control["context"]["persona_expression_brief"],
                treatment["context"]["persona_expression_brief"],
                case["case_id"],
            )

    def test_scorer_contract_is_not_in_model_payload(self):
        for case in self.dataset["cases"]:
            payload = build_payload(self.right_brain, case, CONDITIONS[1])[3]
            serialized = json.dumps(payload, ensure_ascii=False)
            self.assertNotIn('"required_groups"', serialized)
            self.assertNotIn('"ordered_pairs"', serialized)
            self.assertNotIn('"expected_pass"', serialized)

    def test_requests_fix_model_prompt_sampling_and_seed(self):
        case = self.dataset["cases"][0]
        requests = [
            build_request(
                self.preregistration,
                build_payload(self.right_brain, case, condition)[2],
                0,
            )
            for condition in CONDITIONS
        ]
        self.assertEqual(requests[0]["model"], requests[1]["model"])
        self.assertEqual(requests[0]["options"], requests[1]["options"])
        self.assertEqual(requests[0]["messages"][0], requests[1]["messages"][0])

    def test_preregistration_forbids_runtime_training_model_and_holdout_changes(self):
        decision = self.preregistration["decision_policy"]
        self.assertFalse(decision["runtime_default_enable"])
        self.assertFalse(decision["model_change"])
        self.assertFalse(decision["rightbrain_carrier_change"])
        self.assertFalse(decision["scorer_change"])
        self.assertFalse(decision["training"])
        self.assertFalse(decision["v2_holdout_unsealing"])
        self.assertFalse(decision["persona_fidelity_claim"])

    def test_case_condition_and_model_call_counts_are_exact(self):
        self.assertEqual(len(CONDITIONS), 2)
        self.assertEqual(self.preregistration["scope"]["case_count"], 20)
        self.assertEqual(self.preregistration["scope"]["active_case_count"], 15)
        self.assertEqual(self.preregistration["scope"]["inactive_case_count"], 5)
        self.assertEqual(self.preregistration["scope"]["expected_model_call_count"], 40)

    def test_harness_lock_hashes_match(self):
        lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
        for artifact in lock["frozen_artifacts"].values():
            path = ROOT / artifact["path"]
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), artifact["sha256"])


if __name__ == "__main__":
    unittest.main()
