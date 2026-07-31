import copy
import hashlib
import json
import unittest
from pathlib import Path

import public_persona_contract_v3 as v3
import public_persona_incremental_planner_v7 as incremental
import public_persona_specificity_scorer_v7 as specificity
from run_public_persona_incremental_planner_v7 import (
    CONDITIONS,
    build_payload,
    build_request,
    without_incremental_fields,
)
from uruha_brain_mac import RightBrain


ROOT = Path(__file__).resolve().parent
DATASET_PATH = ROOT / "datasets/public_persona_contract_v3_development.json"
PREREGISTRATION_PATH = ROOT / "configs/public_persona_incremental_planner_v7_preregistration.json"
LOCK_PATH = ROOT / "configs/public_persona_incremental_planner_v7_harness_lock.json"


class PublicPersonaIncrementalPlannerV7Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dataset = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
        cls.preregistration = json.loads(PREREGISTRATION_PATH.read_text(encoding="utf-8"))
        cls.right_brain = RightBrain(load_model=False)

    def test_obligation_policies_cover_all_and_only_v3_contexts(self):
        self.assertEqual(set(incremental.OBLIGATION_POLICIES), set(v3.POLICIES))

    def test_compiler_does_not_mutate_input(self):
        source = copy.deepcopy(self.dataset["cases"][0]["logic"])
        frozen = copy.deepcopy(source)
        incremental.compile_incremental_contract(source)
        self.assertEqual(source, frozen)

    def test_contract_has_no_fixed_reply_or_runtime_authorization(self):
        for case in self.dataset["cases"]:
            contract = incremental.compile_incremental_contract(case["logic"])
            self.assertFalse(contract["contains_fixed_reply"])
            self.assertFalse(contract["runtime_authorized"])
            self.assertFalse(contract["training_authorized"])

    def test_active_payload_changes_only_two_incremental_fields(self):
        for case in self.dataset["cases"]:
            if case["context"] not in v3.POLICIES:
                continue
            control = build_payload(self.right_brain, case, CONDITIONS[0])
            treatment = build_payload(self.right_brain, case, CONDITIONS[1])
            self.assertEqual(without_incremental_fields(treatment[3]), control[3], case["case_id"])
            self.assertTrue(treatment[3]["leftbrain_plan"]["dialogue_obligations"])
            self.assertTrue(treatment[3]["leftbrain_plan"]["epistemic_boundary"])

    def test_original_content_units_and_semantic_groups_are_unchanged(self):
        for case in self.dataset["cases"]:
            control = build_payload(self.right_brain, case, CONDITIONS[0])[3]
            treatment = build_payload(self.right_brain, case, CONDITIONS[1])[3]
            self.assertEqual(
                treatment["leftbrain_plan"]["content_units"],
                control["leftbrain_plan"]["content_units"],
                case["case_id"],
            )
            self.assertEqual(
                treatment["required_marker_groups"],
                control["required_marker_groups"],
                case["case_id"],
            )

    def test_memory_action_and_persona_carrier_are_unchanged(self):
        for case in self.dataset["cases"]:
            control = build_payload(self.right_brain, case, CONDITIONS[0])[3]
            treatment = build_payload(self.right_brain, case, CONDITIONS[1])[3]
            self.assertEqual(treatment["context"], control["context"], case["case_id"])
            self.assertEqual(
                treatment["leftbrain_plan"]["meaning"],
                control["leftbrain_plan"]["meaning"],
                case["case_id"],
            )

    def test_inactive_payload_is_exactly_identical(self):
        for case in self.dataset["cases"]:
            if case["context"] in v3.POLICIES:
                continue
            control = build_payload(self.right_brain, case, CONDITIONS[0])
            treatment = build_payload(self.right_brain, case, CONDITIONS[1])
            self.assertEqual(control[2], treatment[2], case["case_id"])

    def test_scorers_are_not_in_model_payload(self):
        for case in self.dataset["cases"]:
            payload = build_payload(self.right_brain, case, CONDITIONS[1])[3]
            serialized = json.dumps(payload, ensure_ascii=False)
            self.assertNotIn('"required_groups"', serialized)
            self.assertNotIn('"ordered_pairs"', serialized)
            self.assertNotIn('"unsupported_concrete_markers"', serialized)

    def test_specificity_scorer_catches_health_sibling_intrusion(self):
        case = next(row for row in self.dataset["cases"] if row["case_id"] == "persona_v3_health_03")
        self.assertTrue(specificity.score_specificity("胃の調子を見て後で決める", case)["passed"])
        result = specificity.score_specificity("喉は平気だけど胃の調子を見て後で決める", case)
        self.assertFalse(result["passed"])
        self.assertEqual(result["unsupported_concrete_markers"], ["喉"])

    def test_specificity_scorer_catches_notice_sibling_intrusion(self):
        case = next(row for row in self.dataset["cases"] if row["case_id"] == "persona_v3_notice_01")
        self.assertTrue(specificity.score_specificity("ゲーム配信を始めたから見て", case)["passed"])
        result = specificity.score_specificity("イベントも始めたから見て", case)
        self.assertFalse(result["passed"])
        self.assertEqual(result["unsupported_concrete_markers"], ["イベント"])

    def test_specificity_scorer_catches_fatigue_action_intrusion(self):
        case = next(row for row in self.dataset["cases"] if row["case_id"] == "persona_v3_fatigue_02")
        self.assertTrue(specificity.score_specificity("疲れたから休んで戻る", case)["passed"])
        result = specificity.score_specificity("疲れたからご飯を食べて戻る", case)
        self.assertFalse(result["passed"])
        self.assertEqual(result["unsupported_concrete_markers"], ["食べ", "ご飯"])

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
