import inspect
import json
import unittest
from pathlib import Path

import answer_bearing_memory_single_record_normalization as normalization
import replay_source_preserving_memory_projection_v2_4_empty_normalization as replay


ROOT = Path(__file__).resolve().parent
CONTRACT = ROOT / "configs/source_preserving_memory_projection_v2_4_empty_normalization_replay_contract.json"


class EmptyNormalizationReplayContractTests(unittest.TestCase):
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
                replay.file_sha256(ROOT / artifact["path"]), artifact["sha256"], name
            )

    def test_rule_is_narrow_and_model_free(self):
        self.assertEqual(
            normalization.QUOTE_ONLY_EMPTY_PLACEHOLDERS,
            frozenset({'""', "''", "“”", "‘’"}),
        )
        self.assertEqual(self.prereg["controlled_variables"]["model_calls"], 0)
        self.assertEqual(self.prereg["success_gates"]["normalized_row_count_equals"], 1)

    def test_replay_does_not_call_model_or_runtime(self):
        source = inspect.getsource(replay)
        self.assertNotIn("post_ollama", source)
        self.assertNotIn("urllib", source)
        self.assertNotIn("uruha_memory_runtime", source)

    def test_authorization_is_replay_only(self):
        authorization = self.prereg["authorization"]
        self.assertTrue(authorization["run_deterministic_replay_once"])
        self.assertFalse(authorization["model_calls"])
        self.assertFalse(authorization["runtime_change"])
        self.assertFalse(authorization["production_enablement"])
        self.assertFalse(authorization["fresh_generation_claim"])


if __name__ == "__main__":
    unittest.main()
