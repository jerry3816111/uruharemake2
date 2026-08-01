import hashlib
import json
import unittest
from pathlib import Path

import audit_rightbrain_forbidden_projection_shadow_v90 as v90


ROOT = Path(__file__).resolve().parent
PREREG = ROOT / "configs/rightbrain_forbidden_projection_shadow_v90_preregistration.json"
LOCK = ROOT / "configs/rightbrain_forbidden_projection_shadow_v90_harness_lock.json"


def sha256_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class RightBrainForbiddenProjectionShadowV90Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.preregistration = json.loads(PREREG.read_text(encoding="utf-8"))

    def test_current_main_revalidation_passes_every_frozen_check(self):
        report = v90.build_revalidation_report()
        self.assertTrue(report["construction_passed"])
        self.assertEqual(report["summary"]["check_count"], 21)
        self.assertEqual(report["summary"]["check_pass_count"], 21)
        self.assertTrue(all(report["checks"].values()))

    def test_speak_probe_compares_actual_visible_replies(self):
        probe = v90.run_visible_reply_noninterference_probe()
        self.assertTrue(probe["visible_replies_equal"])
        self.assertTrue(probe["enabled_trace_is_active"])
        self.assertTrue(probe["disabled_trace_is_explicit"])
        self.assertTrue(probe["enabled_trace_hash_matches_reply"])
        self.assertTrue(probe["disabled_trace_hash_matches_reply"])
        self.assertEqual(probe["real_model_load_count"], 0)
        self.assertEqual(probe["real_model_call_count"], 0)

    def test_revalidation_does_not_authorize_runtime_activation_or_persona_claim(self):
        report = v90.build_revalidation_report()
        self.assertEqual(
            report["decision"],
            "authorize_current_main_observe_only_live_shadow_collection_only",
        )
        self.assertTrue(
            report["authorizations"][
                "current_main_observe_only_live_shadow_collection"
            ]
        )
        for key in (
            "limited_activation_review",
            "projection_runtime_enable",
            "production_default_enable",
            "training_data",
            "persona_fidelity_claim",
        ):
            self.assertFalse(report["authorizations"][key])

    def test_report_contains_no_live_effect_or_reused_legacy_evidence(self):
        report = v90.build_revalidation_report()
        summary = report["summary"]
        self.assertEqual(summary["new_live_shadow_trace_count"], 0)
        self.assertEqual(summary["legacy_log_record_count_used_as_v89_evidence"], 0)
        self.assertEqual(summary["persona_score_count"], 0)
        self.assertNotIn(
            "raw_candidate", json.dumps(report, ensure_ascii=False)
        )

    def test_preregistration_keeps_the_single_variable_and_zero_change_boundary(self):
        self.assertIn(
            "replace only the stale historical V89 source-hash harness",
            self.preregistration["single_changed_variable"],
        )
        contract = self.preregistration["revalidation_contract"]
        self.assertFalse(contract["model_load_allowed"])
        self.assertFalse(contract["runtime_file_change_allowed"])
        self.assertEqual(contract["visible_reply_change_count_exact"], 0)
        self.assertEqual(contract["extra_model_call_count_exact"], 0)
        self.assertFalse(
            self.preregistration["decision_policy"]["projection_runtime_enable"]
        )

    def test_harness_lock_hashes_match(self):
        lock = json.loads(LOCK.read_text(encoding="utf-8"))
        for artifact in lock["frozen_artifacts"].values():
            self.assertEqual(
                sha256_file(ROOT / artifact["path"]), artifact["sha256"]
            )


if __name__ == "__main__":
    unittest.main()
