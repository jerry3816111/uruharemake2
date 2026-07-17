import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONFIG = ROOT / "configs" / "reflection_causal_replay_v2_preregistration.json"
LOCK = ROOT / "configs" / "reflection_causal_replay_v2_harness_lock.json"


class ReflectionCausalReplayV2Test(unittest.TestCase):
    def test_replay_is_explicitly_not_an_independent_holdout(self):
        payload = json.loads(CONFIG.read_text(encoding="utf-8"))
        self.assertEqual(payload["case_count"], 12)
        self.assertEqual(
            payload["dataset_reuse_status"],
            "exact_seen_v1_replay_not_an_independent_holdout",
        )
        self.assertFalse(payload["post_run_case_editing_authorized"])
        self.assertFalse(payload["post_run_threshold_change_authorized"])
        self.assertFalse(payload["runtime_reflection_change_authorized_before_result"])

    def test_harness_lock_matches_current_pre_run_artifacts(self):
        payload = json.loads(LOCK.read_text(encoding="utf-8"))
        self.assertEqual(payload["required_run_branch"], "main")
        for relative, expected in payload["frozen_artifacts"].items():
            actual = hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
            self.assertEqual(actual, expected, relative)


if __name__ == "__main__":
    unittest.main()
