import json
import unittest
from pathlib import Path

import diagnose_planner_memory_causality_v84 as diagnosis
import planner_memory_causality_v84 as v84


ROOT = Path(__file__).resolve().parent


class PlannerMemoryCausalityV84DiagnosisTests(unittest.TestCase):
    def test_mechanism_requires_anchor_to_output_path_and_removed_control(self):
        packet = {
            "scenario_family": "memory_recall_update",
            "payloads": {
                v84.C0: {
                    "context": {
                        "audited_memory_brief": {
                            "allowed_memory_cues": [{"jp_anchor": "User: sample -> Uruha: sample"}]
                        }
                    }
                }
            },
        }
        score = {"failure_codes": ["unexpected_ascii_leak"]}
        rows = [
            {"condition": v84.C0, "raw_reply": "User: sample を見た。", "score": score},
            {"condition": v84.T1, "raw_reply": "何か見たな。", "score": {"failure_codes": []}},
        ]
        report = diagnosis.diagnose([packet], rows)
        self.assertTrue(report["mechanism_supported"])
        self.assertEqual(report["intact_output_transcript_label_count"], 1)
        self.assertEqual(report["removed_output_transcript_label_count"], 0)

    def test_tracked_diagnosis_is_aggregate_only(self):
        path = ROOT / "reports/planner_memory_causality_v84_diagnosis.json"
        if not path.exists():
            self.skipTest("formal V84 diagnosis not generated")
        text = path.read_text(encoding="utf-8")
        for forbidden in ('"raw_reply":', '"jp_anchor":', '"candidate_id":', '"source_session_id":'):
            self.assertNotIn(forbidden, text)
        report = json.loads(text)
        self.assertFalse(report["authorizations"]["v84_decision_override"])


if __name__ == "__main__":
    unittest.main()
