import hashlib
import json
import unittest
from pathlib import Path

import audit_leftbrain_meaning_contract_v64_dataset as audit_module


ROOT = Path(__file__).resolve().parent


class LeftBrainMeaningContractV64DatasetTests(unittest.TestCase):
    def test_construction_audit_passes(self):
        audit = audit_module.build_audit()
        self.assertTrue(audit["passed"], audit["failures"])
        self.assertEqual(audit["counts"]["case_count"], 14)
        self.assertEqual(audit["counts"]["required_commitment_count"], 28)
        self.assertEqual(audit["counts"]["required_frame_relation_count"], 14)

    def test_gold_is_scoring_only_and_not_benchmark_content(self):
        prereg = json.loads((ROOT / "configs/leftbrain_meaning_contract_v64_preregistration.json").read_text(encoding="utf-8"))
        dataset = json.loads((ROOT / "datasets/leftbrain_meaning_contract_v64.json").read_text(encoding="utf-8"))
        self.assertFalse(dataset["official_benchmark_items"])
        self.assertFalse(dataset["benchmark_answers_present"])
        self.assertFalse(prereg["gold_isolation"]["case_specific_examples_in_prompt"])
        self.assertFalse(prereg["authorizations"]["model_inference"])

    def test_written_audit_and_closure_bind_frozen_inputs(self):
        report_path = ROOT / "reports/leftbrain_meaning_contract_v64_dataset_audit.json"
        closure_path = ROOT / "configs/leftbrain_meaning_contract_v64_dataset_closure.json"
        self.assertTrue(report_path.exists())
        self.assertTrue(closure_path.exists())
        report = json.loads(report_path.read_text(encoding="utf-8"))
        closure = json.loads(closure_path.read_text(encoding="utf-8"))
        self.assertTrue(report["passed"])
        for name, relative in (
            ("preregistration", "configs/leftbrain_meaning_contract_v64_preregistration.json"),
            ("dataset", "datasets/leftbrain_meaning_contract_v64.json"),
        ):
            digest = hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
            self.assertEqual(closure["frozen_artifacts"][name], digest)
        self.assertFalse(closure["authorizations"]["model_inference"])


if __name__ == "__main__":
    unittest.main()
