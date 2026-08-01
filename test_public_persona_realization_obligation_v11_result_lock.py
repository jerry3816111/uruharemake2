import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
LOCK = ROOT / "configs/public_persona_realization_obligation_v11_result_lock.json"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class RealizationObligationV11ResultLockTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lock = json.loads(LOCK.read_text(encoding="utf-8"))

    def test_all_result_hashes_match(self):
        for artifact in self.lock["frozen_artifacts"].values():
            self.assertEqual(sha(ROOT / artifact["path"]), artifact["sha256"])

    def test_negative_decision_and_metrics_match_analysis(self):
        analysis = json.loads(
            (ROOT / "reports/public_persona_realization_obligation_v11_analysis.json")
            .read_text(encoding="utf-8")
        )
        self.assertFalse(analysis["passed"])
        self.assertEqual(analysis["decision"], self.lock["decision"])
        self.assertFalse(analysis["target_entry_point_recovered"])
        self.assertEqual(analysis["comparison"]["role_slot_regressions"], 1)

    def test_raw_call_count_and_git_head_are_frozen(self):
        raw = json.loads(
            (ROOT / "reports/public_persona_realization_obligation_v11_raw.json")
            .read_text(encoding="utf-8")
        )
        self.assertEqual(raw["completed_model_call_count"], 40)
        self.assertEqual(raw["git_head"], self.lock["formal_git_head"])

    def test_no_authorization_was_granted(self):
        self.assertFalse(any(self.lock["authorizations"].values()))


if __name__ == "__main__":
    unittest.main()
