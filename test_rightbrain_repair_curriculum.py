import json
import unittest
from pathlib import Path

from build_rightbrain_repair_curriculum_v1 import (
    DEFAULT_HOLDOUT_REPORT,
    DEFAULT_ROW_LIMIT,
    _contract_fingerprint,
    _payload_for_holdout_case,
    _target_errors,
    build_curriculum,
)
from eval_rightbrain_model_surface_holdout import _case_inputs
from project_paths import RIGHTBRAIN_CONTRACT_V1_TRAIN_DATASET_PATH
from uruha_brain_mac import RIGHT_BRAIN_MODEL_REPAIR_SYSTEM_PROMPT, RightBrain


class RightBrainRepairCurriculumTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source_rows = json.loads(
            Path(RIGHTBRAIN_CONTRACT_V1_TRAIN_DATASET_PATH).read_text(encoding="utf-8")
        )
        holdout_report = json.loads(Path(DEFAULT_HOLDOUT_REPORT).read_text(encoding="utf-8"))
        cls.rows, cls.summary = build_curriculum(source_rows, holdout_report)

    def test_builds_balanced_general_repair_rows(self):
        self.assertEqual(len(self.rows), DEFAULT_ROW_LIMIT)
        self.assertEqual(self.summary["curriculum_row_count"], DEFAULT_ROW_LIMIT)
        self.assertGreaterEqual(len(self.summary["category_counts"]), 18)
        self.assertGreaterEqual(len(self.summary["repair_reason_family_counts"]), 12)
        for rare_category in (
            "birthday_repair",
            "clarify_previous",
            "direct_social_action",
            "direct_status",
            "identity",
        ):
            self.assertEqual(self.summary["category_counts"][rare_category], 4)
        for reason in (
            "unexpected_ascii_leak",
            "cjk_language_leak",
            "nonstandard_cjk_surface",
            "polite_tone_drift",
            "instruction_or_plan_leak",
            "over_max_chars",
            "duplicate_candidate",
        ):
            self.assertIn(reason, self.summary["repair_reason_counts"])

    def test_runtime_repair_schema_and_targets_are_valid(self):
        source_ids = set()
        for row in self.rows:
            self.assertNotIn(row["source_id"], source_ids)
            source_ids.add(row["source_id"])
            self.assertEqual(
                row["messages"][0]["content"],
                RIGHT_BRAIN_MODEL_REPAIR_SYSTEM_PROMPT,
            )
            payload = json.loads(row["messages"][1]["content"])
            self.assertEqual(payload["task"], "repair_rejected_user_facing_japanese_reply")
            self.assertTrue(payload["repair_feedback"]["rejection_reasons"])
            self.assertNotIn("previous_draft", payload["repair_feedback"])
            self.assertEqual(
                _target_errors(row["messages"][-1]["content"], payload),
                [],
            )

    def test_holdout_inputs_contracts_and_targets_are_not_in_training(self):
        rightbrain = RightBrain(load_model=False)
        holdout_payloads = [
            _payload_for_holdout_case(rightbrain, case)
            for case in _case_inputs()
        ]
        training_payloads = [
            json.loads(row["messages"][1]["content"])
            for row in self.rows
        ]
        holdout_inputs = {payload["user_input"] for payload in holdout_payloads}
        holdout_fingerprints = {
            _contract_fingerprint(payload)
            for payload in holdout_payloads
        }
        training_inputs = {payload["user_input"] for payload in training_payloads}
        training_fingerprints = {
            _contract_fingerprint(payload)
            for payload in training_payloads
        }
        self.assertFalse(holdout_inputs & training_inputs)
        self.assertFalse(holdout_fingerprints & training_fingerprints)
        self.assertEqual(self.summary["holdout_user_input_overlap_count"], 0)
        self.assertEqual(self.summary["holdout_contract_overlap_count"], 0)
        self.assertEqual(self.summary["holdout_target_overlap_count"], 0)

    def test_generation_is_deterministic(self):
        source_rows = json.loads(
            Path(RIGHTBRAIN_CONTRACT_V1_TRAIN_DATASET_PATH).read_text(encoding="utf-8")
        )
        holdout_report = json.loads(Path(DEFAULT_HOLDOUT_REPORT).read_text(encoding="utf-8"))
        second_rows, second_summary = build_curriculum(source_rows, holdout_report)
        self.assertEqual(self.rows, second_rows)
        for key in (
            "category_counts",
            "repair_reason_family_counts",
            "repair_reason_counts",
            "skipped_counts",
        ):
            self.assertEqual(self.summary[key], second_summary[key])

    def test_target_validator_rejects_actual_model_cjk_and_mojibake(self):
        payload = {
            "required_marker_groups": [["休", "無理"]],
            "forbidden_markers": [],
            "context": {"max_chars": 80},
        }

        simplified = _target_errors("今日は无理しないで休め。", payload)
        replacement = _target_errors("今日は範�だけ決めて休め。", payload)

        self.assertIn("nonstandard_cjk_surface", simplified)
        self.assertIn("unicode_replacement_character", replacement)


if __name__ == "__main__":
    unittest.main()
