import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
RAW_PATH = ROOT / "reports/rightbrain_pipeline_shadow_v61_raw.json"
ANALYSIS_PATH = ROOT / "reports/rightbrain_pipeline_shadow_v61_analysis.json"
AUDIT_PATH = ROOT / "reports/rightbrain_pipeline_shadow_v61_validity_audit.json"
LOCK_PATH = ROOT / "configs/rightbrain_pipeline_shadow_v61_result_lock.json"


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class RightBrainPipelineShadowV61ResultTest(unittest.TestCase):
    def test_frozen_run_accounting_and_stop_decision(self):
        raw = _load(RAW_PATH)
        analysis = _load(ANALYSIS_PATH)

        self.assertEqual(raw["plan_capture_count"], 30)
        self.assertEqual(raw["logical_model_call_count"], 60)
        self.assertEqual(raw["transport_attempt_count"], 60)
        self.assertEqual(raw["transport_error_count"], 0)
        self.assertEqual(raw["production_memory_write_count"], 0)
        self.assertEqual(raw["physical_vrm_action_count"], 0)
        self.assertFalse(analysis["automatic_gates"]["passed"])
        self.assertFalse(analysis["human_blind_review_authorized"])
        self.assertFalse(analysis["runtime_shadow_authorized"])
        self.assertFalse(
            analysis["production_rightbrain_replacement_authorized"]
        )

    def test_capture_violated_preregistered_plan_prerequisite(self):
        raw = _load(RAW_PATH)
        c1_rows = {
            row["case_id"]: row
            for row in raw["model_rows"]
            if row["condition"] == "c1_qwen2_5_7b_one_pass"
        }

        self.assertEqual(len(raw["captures"]), 30)
        self.assertEqual(
            sum(
                bool(capture["logic"].get("human_speech_plan"))
                for capture in raw["captures"]
            ),
            0,
        )
        semantic_group_counts = [
            c1_rows[capture["case_id"]]["raw_score"][
                "semantic_group_count"
            ]
            for capture in raw["captures"]
        ]
        self.assertEqual(sum(count > 0 for count in semantic_group_counts), 4)
        self.assertEqual(sum(count == 0 for count in semantic_group_counts), 26)

    def test_production_eligible_candidates_never_reached_final_reply(self):
        raw = _load(RAW_PATH)
        for condition, expected_strict in (
            ("c1_qwen2_5_7b_one_pass", 2),
            ("t1_qwen3_5_9b_one_pass", 3),
        ):
            eligible = [
                row
                for row in raw["model_rows"]
                if row["condition"] == condition
                and row["raw_score"]["semantic_group_count"] > 0
            ]
            self.assertEqual(len(eligible), 4)
            self.assertEqual(
                sum(
                    row["strict_takeover_before_self_monitor"]
                    for row in eligible
                ),
                expected_strict,
            )
            self.assertEqual(
                sum(row["model_takeover"] for row in eligible),
                0,
            )
            self.assertTrue(
                all(
                    "missing_human_speech_plan"
                    in row["runtime"]["self_monitor_before"]["issues"]
                    for row in eligible
                )
            )

    def test_validity_audit_and_result_lock_bind_immutable_artifacts(self):
        audit = _load(AUDIT_PATH)
        lock = _load(LOCK_PATH)

        self.assertEqual(
            audit["audit_status"],
            "invalid_primary_pipeline_measurement",
        )
        self.assertEqual(
            audit["final_interpretation"]["decision"],
            "freeze_invalid_harness_result_and_stop_v61_dataset",
        )
        for key in (
            "same_dataset_retest_authorized",
            "human_blind_review_authorized",
            "runtime_shadow_authorized",
            "production_rightbrain_replacement_authorized",
            "broad_human_likeness_claim_authorized",
        ):
            self.assertFalse(audit["final_interpretation"][key])

        frozen = lock["frozen_artifacts"]
        for name in (
            "raw_result",
            "analysis_json",
            "analysis_md",
            "validity_audit_json",
            "validity_audit_md",
        ):
            path = ROOT / frozen[name]
            self.assertEqual(_sha256(path), frozen[f"{name}_sha256"])
        self.assertFalse(lock["same_dataset_retest_authorized"])
        self.assertFalse(lock["production_rightbrain_replacement_authorized"])
