import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
LOCK_PATH = ROOT / "configs/public_persona_realization_audit_v9_result_lock.json"


class PublicPersonaRealizationAuditV9ResultTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
        cls.report = json.loads(
            (ROOT / cls.lock["artifacts"]["audit_json"]["path"]).read_text(encoding="utf-8")
        )

    def test_artifact_hashes_match(self):
        for artifact in self.lock["artifacts"].values():
            path = ROOT / artifact["path"]
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), artifact["sha256"])

    def test_integrity_summary_and_decision_are_frozen(self):
        self.assertTrue(self.report["integrity"]["passed"])
        self.assertTrue(self.report["passed"])
        self.assertEqual(self.report["decision"], self.lock["decision"])
        self.assertEqual(self.report["summary"], self.lock["summary"])

    def test_attribution_separates_scorer_and_realization_failures(self):
        summary = self.report["summary"]
        self.assertEqual(summary["planner_role_missing_count"], 0)
        self.assertEqual(summary["lexical_scorer_gap_count"], 2)
        self.assertEqual(summary["planned_but_unrealized_count"], 1)
        self.assertEqual(summary["v8_target_roles_reclassified_as_planned_count"], 1)
        target = self.report["v8_target_failure_attribution"]
        self.assertEqual(len(target), 1)
        self.assertEqual(target[0]["role"], "entry_point")
        self.assertEqual(target[0]["classification"], "planned_but_unrealized")

    def test_only_planned_role_realization_research_is_authorized(self):
        self.assertEqual(self.report["authorizations"], self.lock["authorizations"])
        authorization = "planned_role_realization_research"
        self.assertTrue(self.report["authorizations"][authorization])
        for name, value in self.report["authorizations"].items():
            if name != authorization:
                self.assertFalse(value)


if __name__ == "__main__":
    unittest.main()
