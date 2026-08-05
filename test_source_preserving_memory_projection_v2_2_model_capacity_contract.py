import inspect
import json
import unittest
from pathlib import Path

import run_source_preserving_memory_projection_v2_2_model_capacity_development as runner


ROOT = Path(__file__).resolve().parent
CONTRACT = ROOT / "configs/source_preserving_memory_projection_v2_2_model_capacity_evaluation_contract.json"


class SourcePreservingMemoryProjectionV22CapacityContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        cls.prereg = json.loads(
            (ROOT / cls.contract["artifacts"]["preregistration"]["path"]).read_text(
                encoding="utf-8"
            )
        )

    def test_all_frozen_artifact_hashes_match(self):
        for name, artifact in self.contract["artifacts"].items():
            self.assertEqual(
                runner.file_sha256(ROOT / artifact["path"]), artifact["sha256"], name
            )

    def test_only_extractor_model_changes(self):
        variable = self.prereg["independent_variable"]
        self.assertEqual(variable["control"]["model"], "qwen3.5:4b")
        self.assertEqual(variable["intervention"]["model"], "qwen3.5:9b")
        self.assertEqual(self.prereg["controlled_variables"]["call_count"], 32)
        self.assertEqual(self.prereg["controlled_variables"]["temperature"], 0)
        self.assertFalse(self.prereg["controlled_variables"]["think"])
        self.assertEqual(self.prereg["controlled_variables"]["seed"], 20260805)

    def test_runner_has_no_runtime_or_gold_answer_access(self):
        source = inspect.getsource(runner)
        self.assertNotIn("uruha_memory_runtime", source)
        self.assertNotIn('case["official_answer"]', source)
        self.assertNotIn("production_enablement", source)

    def test_authorization_is_development_only(self):
        authorization = self.prereg["authorization"]
        self.assertTrue(authorization["run_frozen_9b_development_evaluation_once"])
        self.assertFalse(authorization["rerun_frozen_4b_control"])
        self.assertFalse(authorization["runtime_change"])
        self.assertFalse(authorization["production_enablement"])
        self.assertFalse(authorization["fresh_holdout_claim"])


if __name__ == "__main__":
    unittest.main()
