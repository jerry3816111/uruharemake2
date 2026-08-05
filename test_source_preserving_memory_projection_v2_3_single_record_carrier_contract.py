import inspect
import json
import unittest
from pathlib import Path

import answer_bearing_memory_single_record as single
import run_source_preserving_memory_projection_v2_3_single_record_carrier_development as runner


ROOT = Path(__file__).resolve().parent
CONTRACT = ROOT / "configs/source_preserving_memory_projection_v2_3_single_record_carrier_evaluation_contract.json"


class SourcePreservingMemoryProjectionV23ContractTests(unittest.TestCase):
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

    def test_carrier_removes_only_model_generated_index(self):
        self.assertNotIn("source_index", str(single.json_schema()))
        controlled = self.prereg["controlled_variables"]
        self.assertEqual(controlled["model"], "qwen3.5:9b")
        self.assertEqual(controlled["call_count"], 32)
        self.assertEqual(controlled["temperature"], 0)
        self.assertFalse(controlled["think"])

    def test_runner_cannot_read_gold_or_runtime(self):
        source = inspect.getsource(runner)
        self.assertNotIn('case["official_answer"]', source)
        self.assertNotIn("uruha_memory_runtime", source)

    def test_runtime_authorization_remains_false(self):
        authorization = self.prereg["authorization"]
        self.assertTrue(authorization["run_frozen_single_record_carrier_evaluation_once"])
        self.assertFalse(authorization["runtime_change"])
        self.assertFalse(authorization["production_enablement"])
        self.assertFalse(authorization["fresh_holdout_claim"])


if __name__ == "__main__":
    unittest.main()
