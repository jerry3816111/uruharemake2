import inspect
import json
import unittest
from pathlib import Path

import run_source_preserving_memory_projection_v2_1_development as runner


ROOT = Path(__file__).resolve().parent
CONTRACT = ROOT / "configs/source_preserving_memory_projection_v2_1_evaluation_contract.json"


class SourcePreservingMemoryProjectionV21EvaluationContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payload = json.loads(CONTRACT.read_text(encoding="utf-8"))

    def test_all_frozen_artifact_hashes_match(self):
        for name, artifact in self.payload["artifacts"].items():
            self.assertEqual(
                runner.file_sha256(ROOT / artifact["path"]),
                artifact["sha256"],
                name,
            )

    def test_runner_does_not_import_runtime_or_use_gold_label(self):
        source = inspect.getsource(runner)
        self.assertNotIn("import uruha_memory_runtime", source)
        self.assertNotIn('case["official_answer"]', source)
        self.assertNotIn("assess_memory_speakability", source)

    def test_staged_call_budget_and_failure_action_are_frozen(self):
        execution = self.payload["frozen_execution"]
        self.assertEqual(execution["phase_1_call_count"], 32)
        self.assertEqual(execution["phase_2_call_count_if_phase_1_passes"], 16)
        self.assertEqual(execution["maximum_total_model_calls"], 48)
        self.assertIn("Stop after 32 calls", self.payload["phase_1_gate"]["failure_action"])

    def test_contract_authorizes_only_the_frozen_evaluation(self):
        authorization = self.payload["authorization"]
        self.assertTrue(authorization["run_frozen_model_evaluation_once"])
        self.assertFalse(authorization["runtime_change"])
        self.assertFalse(authorization["production_enablement"])
        self.assertFalse(authorization["fresh_holdout_claim"])
        self.assertFalse(authorization["official_benchmark_score_claim"])

    def test_integrity_gate_rejects_missing_duplicate_or_drifted_results(self):
        gate = self.payload["integrity_gate"]
        self.assertTrue(gate["all_frozen_artifact_hashes_match"])
        self.assertTrue(gate["official_source_hash_match"])
        self.assertTrue(gate["exact_expected_row_key_set"])
        self.assertTrue(gate["no_duplicate_row_keys"])
        self.assertTrue(gate["model_digest_match"])
        self.assertTrue(gate["phase_1_metadata_match"])


if __name__ == "__main__":
    unittest.main()
