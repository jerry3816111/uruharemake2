import json
import unittest
from pathlib import Path

import public_persona_contract_v3 as v3
import public_persona_scorer_contract_v4 as scorer
from build_public_persona_scorer_v4_calibration import build_dataset


ROOT = Path(__file__).resolve().parent
DATASET_PATH = ROOT / "datasets/public_persona_scorer_v4_calibration.json"
PREREGISTRATION_PATH = ROOT / "configs/public_persona_scorer_contract_v4_preregistration.json"
V3_RESULT_LOCK_PATH = ROOT / "configs/public_persona_contract_v3_model_result_lock.json"
HARNESS_LOCK_PATH = ROOT / "configs/public_persona_scorer_contract_v4_harness_lock.json"


class PublicPersonaScorerContractV4Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dataset = json.loads(DATASET_PATH.read_text(encoding="utf-8"))

    def test_generated_dataset_matches_frozen_file(self):
        self.assertEqual(build_dataset(), self.dataset)

    def test_probe_accounting_is_exact_and_balanced(self):
        accounting = self.dataset["accounting"]
        self.assertEqual(accounting["probe_count"], 30)
        self.assertEqual(accounting["expected_pass_count"], 15)
        self.assertEqual(accounting["expected_fail_count"], 15)
        self.assertEqual(set(accounting["context_counts"].values()), {6})

    def test_contexts_match_all_and_only_v3_development_policies(self):
        self.assertEqual(set(scorer.SCORER_POLICIES), set(v3.POLICIES))
        for context in scorer.SCORER_POLICIES:
            contract = scorer.compile_scorer_contract(context)
            self.assertEqual(contract["status"], "active_evaluation_only")
            self.assertEqual(
                contract["source_observation_ids"],
                v3.POLICIES[context]["source_observation_ids"],
            )

    def test_optional_self_tease_is_not_required(self):
        contract = scorer.compile_scorer_contract("informal_public_self_introduction")
        required = {group["id"] for group in contract["required_groups"]}
        optional = {group["id"] for group in contract["optional_groups"]}
        self.assertNotIn("mild_self_tease", required)
        self.assertIn("mild_self_tease", optional)
        probe = next(
            row for row in self.dataset["probes"] if row["mutation_type"] == "optional_omission"
        )
        result = scorer.score_reply(probe["calibration_text"], contract)
        self.assertTrue(result["passed"])
        self.assertFalse(result["optional_hits"]["mild_self_tease"])

    def test_order_uses_marker_groups_not_one_literal_pair(self):
        contract = scorer.compile_scorer_contract("minor_delay_then_positive_promotion")
        reply = "今さらだけど、見て。"
        result = scorer.score_reply(reply, contract)
        self.assertTrue(result["passed"])
        self.assertTrue(result["ordering_checks"][0]["passed"])

    def test_all_calibration_labels_and_primary_reasons_match(self):
        for probe in self.dataset["probes"]:
            contract = scorer.compile_scorer_contract(probe["context"])
            result = scorer.score_reply(probe["calibration_text"], contract)
            self.assertIs(result["passed"], probe["expected_pass"], probe["probe_id"])
            if probe["expected_primary_reason"]:
                self.assertIn(probe["expected_primary_reason"], result["reasons"], probe["probe_id"])

    def test_unsupported_context_is_not_scored(self):
        contract = scorer.compile_scorer_contract("factual_answer")
        result = scorer.score_reply("一週間は七日。", contract)
        self.assertFalse(result["scored"])
        self.assertIsNone(result["passed"])

    def test_calibration_text_is_not_authorized_for_model_runtime_or_training(self):
        construction = self.dataset["construction"]
        self.assertFalse(construction["model_input_authorized"])
        self.assertFalse(construction["runtime_authorized"])
        self.assertFalse(construction["training_authorized"])
        for probe in self.dataset["probes"]:
            self.assertFalse(probe["model_input_authorized"])
            self.assertFalse(probe["runtime_authorized"])
            self.assertFalse(probe["training_authorized"])

    def test_v3_negative_result_is_the_locked_dependency(self):
        preregistration = json.loads(PREREGISTRATION_PATH.read_text(encoding="utf-8"))
        v3_lock = json.loads(V3_RESULT_LOCK_PATH.read_text(encoding="utf-8"))
        self.assertFalse(v3_lock["passed"])
        self.assertEqual(v3_lock["decision"], preregistration["depends_on"]["required_decision"])
        self.assertFalse(preregistration["decision_policy"]["runtime_default_enable"])
        self.assertFalse(preregistration["decision_policy"]["training"])
        self.assertFalse(preregistration["decision_policy"]["holdout_unsealing"])

    def test_harness_lock_hashes_match(self):
        import hashlib

        lock = json.loads(HARNESS_LOCK_PATH.read_text(encoding="utf-8"))
        for artifact in lock["frozen_artifacts"].values():
            path = ROOT / artifact["path"]
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), artifact["sha256"])


if __name__ == "__main__":
    unittest.main()
