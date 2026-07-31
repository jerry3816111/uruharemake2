import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
LOCK_PATH = ROOT / "configs/public_persona_planner_policy_v6_construction_result_lock.json"


class PublicPersonaPlannerPolicyV6ConstructionResultTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
        cls.report = json.loads(
            (ROOT / cls.lock["artifacts"]["construction_json"]["path"]).read_text(
                encoding="utf-8"
            )
        )

    def test_artifact_hashes_match(self):
        for artifact in self.lock["artifacts"].values():
            path = ROOT / artifact["path"]
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), artifact["sha256"])

    def test_summary_and_decision_are_frozen(self):
        self.assertTrue(self.report["passed"])
        self.assertEqual(self.report["decision"], self.lock["decision"])
        self.assertEqual(self.report["summary"], self.lock["summary"])

    def test_only_planner_changes_and_protected_data_is_identical(self):
        summary = self.report["summary"]
        self.assertEqual(summary["protected_logic_identity_count"], 20)
        self.assertEqual(summary["persona_brief_identity_count"], 20)
        self.assertEqual(summary["active_planner_changed_count"], 15)
        self.assertEqual(summary["inactive_full_identity_count"], 5)
        self.assertEqual(summary["scorer_contract_exposed_count"], 0)

    def test_authorization_is_model_screen_only(self):
        self.assertEqual(self.report["authorizations"], self.lock["authorizations"])
        self.assertTrue(self.report["authorizations"]["merged_main_model_screen"])
        for name, value in self.report["authorizations"].items():
            if name != "merged_main_model_screen":
                self.assertFalse(value)


if __name__ == "__main__":
    unittest.main()
