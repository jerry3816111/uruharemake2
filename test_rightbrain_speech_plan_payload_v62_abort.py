import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
ABORT_PATH = ROOT / "reports/rightbrain_speech_plan_payload_v62_abort.json"
LOCK_PATH = ROOT / "configs/rightbrain_speech_plan_payload_v62_abort_lock.json"
RUNNER_PATH = ROOT / "run_rightbrain_speech_plan_payload_v62.py"
BRAIN_PATH = ROOT / "uruha_brain_mac.py"
RAW_PATH = ROOT / "reports/rightbrain_speech_plan_payload_v62_raw.json"
ANALYSIS_PATH = ROOT / "reports/rightbrain_speech_plan_payload_v62_analysis.json"


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class RightBrainSpeechPlanPayloadV62AbortTest(unittest.TestCase):
    def test_abort_is_pre_inference_and_has_no_score_artifacts(self):
        report = _load(ABORT_PATH)
        accounting = report["observed_accounting"]

        self.assertEqual(report["status"], "pre_rightbrain_inference_abort")
        self.assertEqual(report["formal_attempt"]["formal_attempt_count"], 1)
        self.assertEqual(accounting["dataset_case_count"], 14)
        self.assertEqual(accounting["observed_leftbrain_model_call_count"], 12)
        self.assertEqual(accounting["rightbrain_model_call_count"], 0)
        self.assertEqual(accounting["transport_attempt_count"], 0)
        self.assertFalse(RAW_PATH.exists())
        self.assertFalse(ANALYSIS_PATH.exists())

    def test_runner_guard_precedes_rightbrain_loop_and_raw_construction(self):
        source = RUNNER_PATH.read_text(encoding="utf-8")
        guard = source.index("if len(leftbrain_calls) != 14:")
        rightbrain_loop = source.index("for condition in CONDITIONS:", guard)
        raw_construction = source.index("raw = {", rightbrain_loop)

        self.assertLess(guard, rightbrain_loop)
        self.assertLess(rightbrain_loop, raw_construction)

    def test_runtime_allows_rule_plan_without_leftbrain_model_call(self):
        source = BRAIN_PATH.read_text(encoding="utf-8")
        low_road = source.index('if route_info.get("route") == "low_road":')
        rule_plan = source.index("_build_low_road_plan", low_road)
        model_plan = source.index("self.left_brain.think", rule_plan)

        self.assertLess(low_road, rule_plan)
        self.assertLess(rule_plan, model_plan)

    def test_lock_binds_evidence_and_forbids_posthoc_retest(self):
        report = _load(ABORT_PATH)
        lock = _load(LOCK_PATH)

        self.assertFalse(report["control_failure"]["ability_hypothesis_tested"])
        self.assertEqual(
            lock["decision"],
            "freeze_pre_inference_abort_and_stop_v62_dataset",
        )
        for artifact in lock["frozen_artifacts"].values():
            path = ROOT / artifact["path"]
            self.assertTrue(path.exists(), artifact["path"])
            self.assertEqual(_sha256(path), artifact["sha256"])
        for key in (
            "same_dataset_retest_authorized",
            "threshold_change_authorized",
            "human_blind_review_authorized",
            "runtime_change_authorized",
            "production_rightbrain_replacement_authorized",
            "broad_human_likeness_claim_authorized",
        ):
            self.assertFalse(lock[key])


if __name__ == "__main__":
    unittest.main()
