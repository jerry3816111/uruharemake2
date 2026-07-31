import copy
import hashlib
import json
import unittest
from pathlib import Path

import public_persona_contract_v3 as v3
import public_persona_operational_carrier_v5 as carrier
from run_public_persona_operational_carrier_v5 import CONDITIONS, build_payload, build_request, without_persona
from uruha_brain_mac import RightBrain


ROOT = Path(__file__).resolve().parent
DATASET_PATH = ROOT / "datasets/public_persona_contract_v3_development.json"
PREREGISTRATION_PATH = ROOT / "configs/public_persona_operational_carrier_v5_preregistration.json"
LOCK_PATH = ROOT / "configs/public_persona_operational_carrier_v5_harness_lock.json"


class PublicPersonaOperationalCarrierV5Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dataset = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
        cls.preregistration = json.loads(PREREGISTRATION_PATH.read_text(encoding="utf-8"))
        cls.right_brain = RightBrain(load_model=False)

    def test_operational_rules_cover_all_and_only_v3_contexts(self):
        self.assertEqual(set(carrier.OPERATIONAL_RULES_JP), set(v3.POLICIES))

    def test_inactive_context_returns_exact_baseline(self):
        case = next(row for row in self.dataset["cases"] if not row["expected_contract_status"].startswith("active"))
        brief, contract = carrier.operational_expression_brief(case["logic"], case["psyche"])
        self.assertEqual(brief, v3.baseline_expression_brief(case["psyche"]))
        self.assertEqual(contract["status"], "inactive_no_supported_context")

    def test_active_carrier_is_japanese_surface_only(self):
        case = self.dataset["cases"][0]
        brief, contract = carrier.operational_expression_brief(case["logic"], case["psyche"])
        serialized = json.dumps(brief, ensure_ascii=False)
        self.assertEqual(contract["status"], "active_development_hypothesis")
        self.assertIn("実行規則", serialized)
        self.assertIn("です・ます調にしない", serialized)
        self.assertNotIn("planning_policy", brief)
        self.assertNotIn("source_observation_ids", brief)

    def test_all_conditions_change_only_persona_brief(self):
        for case in self.dataset["cases"]:
            packets = {condition: build_payload(self.right_brain, case, condition) for condition in CONDITIONS}
            nonpersona = [without_persona(packet[2]) for packet in packets.values()]
            self.assertTrue(all(item == nonpersona[0] for item in nonpersona[1:]), case["case_id"])

    def test_inactive_payload_is_exactly_identical_for_all_conditions(self):
        for case in self.dataset["cases"]:
            if case["context"] in v3.POLICIES:
                continue
            payloads = [build_payload(self.right_brain, case, condition)[1] for condition in CONDITIONS]
            self.assertEqual(len(set(payloads)), 1, case["case_id"])

    def test_scorer_contract_is_not_in_model_payload(self):
        for case in self.dataset["cases"]:
            payload = build_payload(self.right_brain, case, CONDITIONS[2])[2]
            serialized = json.dumps(payload, ensure_ascii=False)
            self.assertNotIn("required_groups", serialized)
            self.assertNotIn("ordered_pairs", serialized)
            self.assertNotIn("expected_pass", serialized)

    def test_requests_fix_model_prompt_sampling_and_seed_across_conditions(self):
        case = self.dataset["cases"][0]
        requests = []
        for condition in CONDITIONS:
            _, payload_text, _ = build_payload(self.right_brain, case, condition)
            requests.append(build_request(self.preregistration, payload_text, 0))
        for request in requests[1:]:
            self.assertEqual(request["model"], requests[0]["model"])
            self.assertEqual(request["options"], requests[0]["options"])
            self.assertEqual(request["messages"][0], requests[0]["messages"][0])

    def test_preregistration_forbids_runtime_training_model_and_holdout_changes(self):
        decision = self.preregistration["decision_policy"]
        self.assertFalse(decision["runtime_default_enable"])
        self.assertFalse(decision["model_change"])
        self.assertFalse(decision["training"])
        self.assertFalse(decision["v2_holdout_unsealing"])
        self.assertFalse(decision["persona_fidelity_claim"])

    def test_condition_count_and_model_call_count_are_exact(self):
        self.assertEqual(len(CONDITIONS), 3)
        self.assertEqual(self.preregistration["scope"]["case_count"], 20)
        self.assertEqual(self.preregistration["scope"]["expected_model_call_count"], 60)

    def test_harness_lock_hashes_match(self):
        lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
        for artifact in lock["frozen_artifacts"].values():
            path = ROOT / artifact["path"]
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), artifact["sha256"])


if __name__ == "__main__":
    unittest.main()
