import hashlib
import json
import unittest
from pathlib import Path

import public_persona_missing_role_v8 as role_schema
from run_public_persona_payload_format_v10 import CONDITIONS, build_payload, build_request
from uruha_brain_mac import RightBrain


ROOT = Path(__file__).resolve().parent
DATASET = ROOT / "datasets/public_persona_contract_v3_development.json"
PREREGISTRATION = ROOT / "configs/public_persona_payload_format_v10_preregistration.json"
V9_RESULT_LOCK = ROOT / "configs/public_persona_realization_audit_v9_result_lock.json"
HARNESS_LOCK = ROOT / "configs/public_persona_payload_format_v10_harness_lock.json"
CONSTRUCTION_LOCK = ROOT / "configs/public_persona_payload_format_v10_construction_lock.json"


class PublicPersonaPayloadFormatV10Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dataset = json.loads(DATASET.read_text(encoding="utf-8"))
        cls.preregistration = json.loads(PREREGISTRATION.read_text(encoding="utf-8"))
        cls.v9_lock = json.loads(V9_RESULT_LOCK.read_text(encoding="utf-8"))
        cls.right_brain = RightBrain(load_model=False)

    def paired(self, case):
        return [build_payload(self.right_brain, case, condition) for condition in CONDITIONS]

    def test_conditions_are_exactly_json_and_lines(self):
        self.assertEqual(CONDITIONS, ("c0_compact_json", "t1_mixed_lines"))

    def test_control_exactly_matches_canonical_json(self):
        for case in self.dataset["cases"]:
            control, _ = self.paired(case)
            self.assertTrue(control[3]["control_exact_text_matches"], case["case_id"])

    def test_both_conditions_share_exact_canonical_payload(self):
        for case in self.dataset["cases"]:
            control, treatment = self.paired(case)
            self.assertEqual(control[0], treatment[0], case["case_id"])
            self.assertEqual(control[1], treatment[1], case["case_id"])
            self.assertEqual(
                control[3]["canonical_payload_sha256"],
                treatment[3]["canonical_payload_sha256"],
                case["case_id"],
            )

    def test_representations_differ_for_every_case(self):
        for case in self.dataset["cases"]:
            control, treatment = self.paired(case)
            self.assertNotEqual(control[2], treatment[2], case["case_id"])
            self.assertIn("\n", treatment[2], case["case_id"])

    def test_representation_integrity_passes_for_all_pairs(self):
        for case in self.dataset["cases"]:
            for packet in self.paired(case):
                self.assertTrue(packet[3]["representation_integrity_pass"], case["case_id"])

    def test_leaf_counts_are_identical(self):
        for case in self.dataset["cases"]:
            control, treatment = self.paired(case)
            counts = {
                control[3]["canonical_leaf_count"],
                control[3]["represented_leaf_count"],
                treatment[3]["canonical_leaf_count"],
                treatment[3]["represented_leaf_count"],
            }
            self.assertEqual(len(counts), 1, case["case_id"])

    def test_requests_fix_model_system_prompt_options_and_seed(self):
        case = self.dataset["cases"][0]
        requests = [
            build_request(self.preregistration, packet[2], 0) for packet in self.paired(case)
        ]
        self.assertEqual(requests[0]["model"], requests[1]["model"])
        self.assertEqual(requests[0]["messages"][0], requests[1]["messages"][0])
        self.assertEqual(requests[0]["options"], requests[1]["options"])

    def test_model_user_messages_differ_only_by_representation(self):
        case = self.dataset["cases"][0]
        packets = self.paired(case)
        requests = [build_request(self.preregistration, packet[2], 0) for packet in packets]
        self.assertNotEqual(requests[0]["messages"][1], requests[1]["messages"][1])
        left = dict(requests[0]); right = dict(requests[1])
        left["messages"] = left["messages"][:1]
        right["messages"] = right["messages"][:1]
        self.assertEqual(left, right)

    def test_role_schema_has_36_frozen_slots(self):
        slots = sum(len(role_schema.ROLE_SCHEMAS[case["context"]]) for case in self.dataset["cases"] if case["context"] in role_schema.ROLE_SCHEMAS)
        self.assertEqual(slots, 36)
        self.assertEqual(slots, self.preregistration["scope"]["planned_role_slot_count"])

    def test_role_schema_recognizes_general_entry_forms(self):
        markers = next(item["evidence_markers"] for item in role_schema.ROLE_SCHEMAS["functional_stream_start_notification"] if item["role"] == "entry_point")
        self.assertTrue(any(marker in "今から見て" for marker in markers))
        self.assertTrue(any(marker in "ルームに参加して" for marker in markers))

    def test_model_payload_does_not_contain_evaluation_contracts(self):
        forbidden = ('"ordered_pairs"', '"entry_point"', '"unsupported_concrete_markers"', 'reply_concept_hits')
        for case in self.dataset["cases"]:
            for packet in self.paired(case):
                for token in forbidden:
                    self.assertNotIn(token, packet[2], case["case_id"])

    def test_v9_dependency_authorizes_planned_role_realization_research(self):
        self.assertTrue(self.v9_lock["authorizations"]["planned_role_realization_research"])
        self.assertFalse(self.v9_lock["authorizations"]["runtime_default_enable"])

    def test_preregistration_forbids_runtime_model_scorer_training_and_holdout_changes(self):
        decision = self.preregistration["decision_policy"]
        self.assertFalse(decision["runtime_default_enable"])
        self.assertFalse(decision["model_change"])
        self.assertFalse(decision["scorer_change"])
        self.assertFalse(decision["training"])
        self.assertFalse(decision["v2_holdout_unsealing"])
        self.assertFalse(decision["persona_fidelity_claim"])

    def test_case_condition_and_model_call_counts_are_exact(self):
        scope = self.preregistration["scope"]
        self.assertEqual(scope["case_count"], 20)
        self.assertEqual(scope["active_case_count"], 15)
        self.assertEqual(scope["inactive_case_count"], 5)
        self.assertEqual(scope["condition_count"], 2)
        self.assertEqual(scope["expected_model_call_count"], 40)

    def test_harness_lock_hashes_match(self):
        lock = json.loads(HARNESS_LOCK.read_text(encoding="utf-8"))
        for artifact in lock["frozen_artifacts"].values():
            path = ROOT / artifact["path"]
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), artifact["sha256"])

    def test_construction_lock_freezes_passing_zero_model_audit(self):
        lock = json.loads(CONSTRUCTION_LOCK.read_text(encoding="utf-8"))
        self.assertTrue(lock["passed"])
        self.assertEqual(lock["decision"], "authorize_merged_main_v10_model_screen_only")
        self.assertEqual(lock["summary"]["model_call_count"], 0)
        self.assertEqual(lock["summary"]["representation_integrity_count"], 40)
        self.assertFalse(lock["authorizations"]["runtime_default_enable"])
        for artifact in lock["artifacts"].values():
            path = ROOT / artifact["path"]
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), artifact["sha256"])


if __name__ == "__main__":
    unittest.main()
