import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
RESULT_LOCK = (
    ROOT / "configs/rightbrain_forbidden_projection_shadow_v90_result_lock.json"
)


def sha256_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class RightBrainForbiddenProjectionShadowV90ResultTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lock = json.loads(RESULT_LOCK.read_text(encoding="utf-8"))
        report_path = ROOT / cls.lock["frozen_artifacts"]["report_json"]["path"]
        cls.report = json.loads(report_path.read_text(encoding="utf-8"))

    def test_result_lock_binds_every_formal_artifact(self):
        for artifact in self.lock["frozen_artifacts"].values():
            self.assertEqual(
                sha256_file(ROOT / artifact["path"]), artifact["sha256"]
            )

    def test_frozen_outcome_matches_the_report(self):
        outcome = self.lock["frozen_outcome"]
        self.assertTrue(self.report["construction_passed"])
        self.assertEqual(self.report["decision"], outcome["decision"])
        self.assertEqual(
            self.report["summary"]["check_count"], outcome["check_count"]
        )
        self.assertEqual(
            self.report["summary"]["check_pass_count"],
            outcome["check_pass_count"],
        )
        self.assertEqual(self.report["summary"]["model_load_count"], 0)
        self.assertEqual(self.report["summary"]["model_call_count"], 0)
        self.assertEqual(self.report["summary"]["visible_reply_change_count"], 0)

    def test_result_authorizes_collection_only(self):
        authorizations = self.report["authorizations"]
        self.assertTrue(
            authorizations["current_main_observe_only_live_shadow_collection"]
        )
        for key in (
            "limited_activation_review",
            "projection_runtime_enable",
            "production_default_enable",
            "training_data",
            "persona_fidelity_claim",
        ):
            self.assertFalse(authorizations[key])
        self.assertEqual(
            self.report["summary"]["new_live_shadow_trace_count"], 0
        )


if __name__ == "__main__":
    unittest.main()
