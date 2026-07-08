import json
import unittest
from pathlib import Path

from eval_rightbrain_casual_register_gate_v2 import build_report
from project_paths import (
    RIGHTBRAIN_CASUAL_REGISTER_GATE_V2_REPORT_JSON_PATH,
    RIGHTBRAIN_SAMPLING_SCHEDULE_ABLATION_V1_REPORT_JSON_PATH,
    RIGHTBRAIN_SAMPLING_SCHEDULE_NATURALNESS_AUDIT_V1_JSON_PATH,
)


class RightBrainCasualRegisterGateTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sampling = json.loads(
            Path(RIGHTBRAIN_SAMPLING_SCHEDULE_ABLATION_V1_REPORT_JSON_PATH).read_text(encoding="utf-8")
        )
        cls.audit = json.loads(
            Path(RIGHTBRAIN_SAMPLING_SCHEDULE_NATURALNESS_AUDIT_V1_JSON_PATH).read_text(encoding="utf-8")
        )
        cls.report = build_report(cls.sampling, cls.audit)

    def test_gate_passes_without_overclaiming_recall(self):
        self.assertTrue(self.report["gate_passed"], msg=self.report["gate"])
        self.assertEqual(self.report["metrics"]["failure_precision"], 1.0)
        self.assertEqual(self.report["metrics"]["failure_recall"], 0.2)
        self.assertEqual(self.report["metrics"]["false_positive_rate"], 0.0)

    def test_recorded_report_matches_recomputed_metrics(self):
        recorded = json.loads(
            Path(RIGHTBRAIN_CASUAL_REGISTER_GATE_V2_REPORT_JSON_PATH).read_text(encoding="utf-8")
        )
        self.assertEqual(recorded["confusion_matrix"], self.report["confusion_matrix"])
        self.assertEqual(recorded["metrics"], self.report["metrics"])
        self.assertEqual(recorded["gate"], self.report["gate"])


if __name__ == "__main__":
    unittest.main()
