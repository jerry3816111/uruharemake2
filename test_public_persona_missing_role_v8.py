import copy
import hashlib
import json
import unittest
from pathlib import Path

import public_persona_contract_v3 as v3
import public_persona_missing_role_v8 as missing_role
from run_public_persona_missing_role_v8 import (
    CONDITIONS,
    build_payload,
    build_request,
    without_missing_roles,
)
from uruha_brain_mac import RightBrain


ROOT = Path(__file__).resolve().parent
DATASET_PATH = ROOT / "datasets/public_persona_contract_v3_development.json"
PREREGISTRATION_PATH = ROOT / "configs/public_persona_missing_role_v8_preregistration.json"
LOCK_PATH = ROOT / "configs/public_persona_missing_role_v8_harness_lock.json"


class PublicPersonaMissingRoleV8Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dataset = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
        cls.preregistration = json.loads(PREREGISTRATION_PATH.read_text(encoding="utf-8"))
        cls.right_brain = RightBrain(load_model=False)

    def test_role_schemas_cover_all_and_only_v3_contexts(self):
        self.assertEqual(set(missing_role.ROLE_SCHEMAS), set(v3.POLICIES))

    def test_compiler_does_not_mutate_input(self):
        source = copy.deepcopy(self.dataset["cases"][0]["logic"])
        frozen = copy.deepcopy(source)
        missing_role.compile_missing_role_contract(source)
        self.assertEqual(source, frozen)

    def test_contract_has_no_fixed_reply_or_runtime_authorization(self):
        for case in self.dataset["cases"]:
            contract = missing_role.compile_missing_role_contract(case["logic"])
            self.assertFalse(contract["contains_fixed_reply"])
            self.assertFalse(contract["runtime_authorized"])
            self.assertFalse(contract["training_authorized"])

    def test_coverage_finds_exactly_one_missing_entry_point(self):
        contracts = [
            missing_role.compile_missing_role_contract(case["logic"])
            for case in self.dataset["cases"]
        ]
        missing = [contract for contract in contracts if contract["missing_roles"]]
        self.assertEqual(len(missing), 1)
        self.assertEqual(missing[0]["context"], "functional_stream_start_notification")
        self.assertEqual(missing[0]["missing_roles"], ["entry_point"])

    def test_role_evidence_markers_are_not_projected(self):
        evidence = {
            marker
            for policy in missing_role.ROLE_SCHEMAS.values()
            for role in policy
            for marker in role["evidence_markers"]
        }
        for case in self.dataset["cases"]:
            payload = build_payload(self.right_brain, case, CONDITIONS[1])[3]
            projected = payload["leftbrain_plan"].get("missing_dialogue_roles", [])
            self.assertTrue(evidence.isdisjoint(projected), case["case_id"])

    def test_all_treatments_reduce_exactly_to_control(self):
        for case in self.dataset["cases"]:
            control = build_payload(self.right_brain, case, CONDITIONS[0])[3]
            treatment = build_payload(self.right_brain, case, CONDITIONS[1])[3]
            self.assertEqual(without_missing_roles(treatment), control, case["case_id"])

    def test_complete_cases_keep_exact_payload_identity(self):
        identity_count = 0
        for case in self.dataset["cases"]:
            control = build_payload(self.right_brain, case, CONDITIONS[0])
            treatment = build_payload(self.right_brain, case, CONDITIONS[1])
            if not treatment[1]["missing_roles"]:
                self.assertEqual(control[2], treatment[2], case["case_id"])
                identity_count += 1
        self.assertEqual(identity_count, 19)

    def test_changed_case_adds_only_missing_dialogue_roles(self):
        changed = []
        for case in self.dataset["cases"]:
            control = build_payload(self.right_brain, case, CONDITIONS[0])[3]
            treatment = build_payload(self.right_brain, case, CONDITIONS[1])[3]
            if control != treatment:
                changed.append((case, control, treatment))
        self.assertEqual(len(changed), 1)
        case, control, treatment = changed[0]
        self.assertEqual(
            treatment["leftbrain_plan"]["missing_dialogue_roles"], ["entry_point"]
        )
        self.assertEqual(without_missing_roles(treatment), control)
        self.assertIn("notice", case["case_id"])

    def test_original_semantics_persona_memory_and_action_are_unchanged(self):
        for case in self.dataset["cases"]:
            control = build_payload(self.right_brain, case, CONDITIONS[0])[3]
            treatment = build_payload(self.right_brain, case, CONDITIONS[1])[3]
            for field in (
                "context",
                "required_marker_groups",
                "audited_memory_policy",
                "authorized_action",
                "tool_calls",
            ):
                self.assertEqual(treatment.get(field), control.get(field), case["case_id"])
            for field in (
                "scene",
                "intent",
                "surface_act",
                "dialogue_act",
                "meaning",
                "content_units",
                "style_operators",
                "grounding_terms",
            ):
                self.assertEqual(
                    treatment["leftbrain_plan"].get(field),
                    control["leftbrain_plan"].get(field),
                    case["case_id"],
                )

    def test_all_inactive_cases_are_exactly_identical(self):
        inactive_count = 0
        for case in self.dataset["cases"]:
            if case["context"] in v3.POLICIES:
                continue
            control = build_payload(self.right_brain, case, CONDITIONS[0])
            treatment = build_payload(self.right_brain, case, CONDITIONS[1])
            self.assertEqual(control[2], treatment[2], case["case_id"])
            inactive_count += 1
        self.assertEqual(inactive_count, 5)

    def test_scorers_and_evidence_schema_are_not_in_model_payload(self):
        forbidden = (
            '"required_groups"',
            '"ordered_pairs"',
            '"unsupported_concrete_markers"',
            '"expected_pass"',
            '"evidence_markers"',
        )
        for case in self.dataset["cases"]:
            payload = build_payload(self.right_brain, case, CONDITIONS[1])[3]
            serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True)
            for token in forbidden:
                self.assertNotIn(token, serialized, case["case_id"])

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

    def test_case_condition_change_and_model_call_counts_are_exact(self):
        scope = self.preregistration["scope"]
        self.assertEqual(len(CONDITIONS), 2)
        self.assertEqual(scope["case_count"], 20)
        self.assertEqual(scope["active_case_count"], 15)
        self.assertEqual(scope["inactive_case_count"], 5)
        self.assertEqual(scope["expected_changed_case_count"], 1)
        self.assertEqual(scope["expected_unchanged_case_count"], 19)
        self.assertEqual(scope["expected_model_call_count"], 40)

    def test_harness_lock_hashes_match(self):
        lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
        for artifact in lock["frozen_artifacts"].values():
            path = ROOT / artifact["path"]
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), artifact["sha256"])


if __name__ == "__main__":
    unittest.main()
