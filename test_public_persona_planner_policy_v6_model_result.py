import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
LOCK_PATH = ROOT / "configs/public_persona_planner_policy_v6_model_result_lock.json"


class PublicPersonaPlannerPolicyV6ModelResultTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
        cls.raw = json.loads(
            (ROOT / cls.lock["artifacts"]["raw"]["path"]).read_text(encoding="utf-8")
        )
        cls.analysis = json.loads(
            (ROOT / cls.lock["artifacts"]["analysis_json"]["path"]).read_text(
                encoding="utf-8"
            )
        )

    def test_artifact_hashes_match(self):
        for artifact in self.lock["artifacts"].values():
            path = ROOT / artifact["path"]
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), artifact["sha256"])

    def test_exact_execution_and_negative_decision(self):
        self.assertEqual(self.raw["git_head"], self.lock["git_head"])
        self.assertEqual(self.raw["completed_model_call_count"], 40)
        self.assertEqual(len(self.raw["rows"]), 40)
        self.assertTrue(self.analysis["integrity"]["passed"])
        self.assertFalse(self.analysis["passed"])
        self.assertEqual(self.analysis["decision"], self.lock["decision"])

    def test_locked_metrics_match(self):
        metrics = self.analysis["metrics"]
        self.assertEqual(metrics["c0_existing_speech_plan"]["v4_persona_pass_count"], 12)
        self.assertEqual(metrics["t1_persona_planning_policy"]["v4_persona_pass_count"], 13)
        self.assertEqual(metrics["c0_existing_speech_plan"]["surface_gate_pass_count"], 14)
        self.assertEqual(metrics["t1_persona_planning_policy"]["surface_gate_pass_count"], 17)
        self.assertEqual(self.analysis["comparison"]["v4_persona_regressions"], 1)
        self.assertEqual(self.analysis["comparison"]["semantic_regressions"], 1)
        self.assertEqual(self.analysis["comparison"]["surface_gate_regressions"], 1)
        self.assertEqual(self.analysis["inactive_identity_count"], 5)

    def test_only_incremental_planner_research_is_authorized(self):
        self.assertTrue(self.lock["authorizations"]["incremental_planner_projection_research"])
        for name, value in self.lock["authorizations"].items():
            if name != "incremental_planner_projection_research":
                self.assertFalse(value)
        self.assertEqual(self.raw["v2_holdout_content_review_count"], 0)
        self.assertEqual(self.raw["production_memory_write_count"], 0)
        self.assertEqual(self.raw["physical_vrm_action_count"], 0)


if __name__ == "__main__":
    unittest.main()
