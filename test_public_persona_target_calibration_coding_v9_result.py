import hashlib
import json
import tempfile
import unittest
from collections import Counter
from pathlib import Path

import public_persona_target_calibration_coding_v9 as v9


ROOT = Path(__file__).resolve().parent
LOCK_PATH = ROOT / "configs/public_persona_target_calibration_coding_v9_result_lock.json"


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha256_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class TargetCalibrationCodingV9ResultTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lock = load_json(LOCK_PATH)
        cls.report = load_json(
            ROOT / cls.lock["frozen_artifacts"]["construction_json"]["path"]
        )
        cls.frame = load_json(
            ROOT / cls.lock["frozen_artifacts"]["sampling_frame"]["path"]
        )

    def test_all_frozen_artifact_hashes_match(self):
        for binding in self.lock["frozen_artifacts"].values():
            path = ROOT / binding["path"]
            self.assertTrue(path.is_file(), binding["path"])
            self.assertEqual(binding["sha256"], sha256_file(path), binding["path"])

    def test_construction_passed_all_nine_checks(self):
        self.assertEqual(
            "999226ac3bf491bee578cd562f8ac05e9ff8556d",
            self.lock["formal_git_head"],
        )
        self.assertTrue(self.report["construction_passed"])
        self.assertEqual(9, self.report["summary"]["check_count"])
        self.assertEqual(9, self.report["summary"]["check_pass_count"])
        self.assertEqual([], self.report["violations"])
        self.assertEqual(v9.PASS_DECISION, self.report["decision"])

    def test_frame_has_three_sources_and_thirty_content_free_slots(self):
        slots = self.frame["sampling_slots"]
        self.assertEqual(30, len(slots))
        self.assertEqual(
            Counter({source_id: 10 for source_id in v9.AUTHORIZED_SOURCE_IDS}),
            Counter(row["source_id"] for row in slots),
        )
        self.assertEqual([], v9._find_prohibited_keys(self.frame))
        self.assertFalse(
            {row["source_id"] for row in slots} & v9.FORBIDDEN_HOLDOUT_SOURCE_IDS
        )

    def test_all_human_behavior_model_score_and_holdout_counts_are_zero(self):
        summary = self.report["summary"]
        for field in (
            "private_ledger_count",
            "content_reviewed_source_count",
            "selected_event_count",
            "coded_event_count",
            "independently_reviewed_event_count",
            "human_coder_count",
            "raw_or_verbatim_record_count",
            "model_output_count",
            "persona_score_count",
            "holdout_content_review_count",
            "model_call_count",
            "production_memory_write_count",
        ):
            self.assertEqual(0, summary[field], field)

    def test_authorization_is_frame_and_tool_only(self):
        authorization = self.report["authorizations"]
        self.assertTrue(authorization["frozen_target_calibration_sampling_frame"])
        self.assertTrue(authorization["local_two_coder_tool_installed"])
        self.assertFalse(authorization["target_human_coding_now"])
        for field in (
            "model_execution",
            "runtime_change",
            "prompt_change",
            "memory_change",
            "model_training",
            "sealed_holdout_unsealing",
            "formal_persona_scoring",
            "public_persona_fidelity_claim",
        ):
            self.assertFalse(authorization[field], field)

    def test_report_inputs_are_hash_bound(self):
        for binding in self.report["inputs"].values():
            path = ROOT / binding["path"]
            self.assertTrue(path.is_file(), binding["path"])
            self.assertEqual(binding["sha256"], sha256_file(path), binding["path"])

    def test_missing_v7_reliability_lock_still_blocks_human_ledger(self):
        with tempfile.TemporaryDirectory() as temporary:
            missing = Path(temporary) / "v7_missing.json"
            authorized, _ = v9.human_use_authorized(missing)
            self.assertFalse(authorized)
            with self.assertRaises(PermissionError):
                v9.initialize_target_ledger(
                    "coder_a", "coder_a.json", missing, Path(temporary) / "private"
                )

    def test_result_lock_does_not_overclaim_persona_evidence(self):
        self.assertFalse(self.lock["formal_result"]["human_coding_completed"])
        self.assertFalse(self.lock["formal_result"]["reliability_computed"])
        self.assertFalse(self.lock["formal_result"]["persona_score_computed"])
        self.assertFalse(self.lock["authorizations"]["target_human_coding_now"])
        self.assertFalse(self.lock["authorizations"]["public_persona_fidelity_claim"])
        self.assertIn("V7", self.lock["next_required_evidence"])

    def test_markdown_explains_why_human_work_is_not_started(self):
        markdown = (
            ROOT / "reports/public_persona_target_calibration_coding_v9_construction.md"
        ).read_text(encoding="utf-8")
        self.assertIn("30 個內容無關搜尋起點", markdown)
        self.assertIn("V7 共用 codebook", markdown)
        self.assertIn("人工作業保持關閉", markdown)


if __name__ == "__main__":
    unittest.main()
