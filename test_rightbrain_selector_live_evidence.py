import json
import tempfile
import unittest
from pathlib import Path

from build_rightbrain_selector_live_evidence import build_report, extract_shadow_case, load_jsonl


def make_record(index, *, disagree=False, learned_valid=True, selected_rejected=False, visible_matches=True):
    current = f"現在の返事{index}"
    learned = f"別の返事{index}" if disagree else current
    assistant = current if visible_matches else f"漏れた返事{index}"
    return {
        "timestamp": f"2026-07-07T14:00:{index % 60:02d}",
        "session_id": "session-a",
        "turn_index": index,
        "input_mode": "text",
        "user_text": f"質問{index}",
        "assistant_reply": assistant,
        "planner_debug": {"scene": "casual", "intent": "direct_answer"},
        "logic": {
            "scene": "casual",
            "intent": "direct_answer",
            "model_surface_selection": {
                "selected_source": "deterministic",
                "selected_candidate": current,
            },
            "model_surface_selector_shadow": {
                "mode": "observe_only",
                "status": "active",
                "changes_user_visible_reply": False,
                "candidate_count": 2,
                "candidate_scores": [
                    {"source": "deterministic", "text": current, "probability": 0.8},
                    {"source": "accepted:initial", "text": learned, "probability": 0.9 if disagree else 0.7},
                ],
                "current_selected_text": current,
                "current_selected_strict_valid": True,
                "learned_selected_source": "rejected:initial:0" if selected_rejected else "accepted:initial",
                "learned_selected_text": learned,
                "learned_selected_probability": 0.9,
                "learned_selected_strict_valid": learned_valid,
                "learned_selected_was_gate_rejected": selected_rejected,
                "agrees_with_current": not disagree,
                "would_change_output": disagree,
            },
        },
    }


class RightBrainSelectorLiveEvidenceTest(unittest.TestCase):
    def test_legacy_record_without_active_shadow_is_ignored(self):
        record = {"session_id": "old", "turn_index": 1, "logic": {}}
        self.assertIsNone(extract_shadow_case(record))
        report = build_report([record], min_multi_candidate_cases=1, min_disagreements=1)
        self.assertEqual(report["status"], "waiting_for_live_shadow_data")
        self.assertFalse(report["quality_comparison_ready"])
        self.assertFalse(report["safety_gate_passed"])
        self.assertFalse(report["gate"]["safety_has_multi_candidate_observations"])

    def test_safe_sample_reaches_quality_comparison_threshold(self):
        records = [make_record(index, disagree=index < 2) for index in range(5)]
        report = build_report(records, min_multi_candidate_cases=5, min_disagreements=2)

        self.assertEqual(report["status"], "ready_for_quality_comparison")
        self.assertTrue(report["quality_comparison_ready"])
        self.assertTrue(report["safety_gate_passed"])
        self.assertEqual(report["summary"]["multi_candidate_case_count"], 5)
        self.assertEqual(report["summary"]["disagreement_count"], 2)
        self.assertEqual(report["summary"]["learned_invalid_count"], 0)

    def test_any_invalid_or_gate_rejected_selection_blocks_readiness(self):
        records = [make_record(index, disagree=index < 2) for index in range(5)]
        records[-1] = make_record(4, disagree=True, learned_valid=False, selected_rejected=True)
        report = build_report(records, min_multi_candidate_cases=5, min_disagreements=2)

        self.assertEqual(report["status"], "blocked_by_shadow_safety_failure")
        self.assertFalse(report["quality_comparison_ready"])
        self.assertEqual(report["summary"]["learned_invalid_count"], 1)
        self.assertEqual(report["summary"]["learned_gate_rejected_selection_count"], 1)

    def test_visible_output_mismatch_blocks_readiness(self):
        records = [make_record(index, disagree=index < 2) for index in range(5)]
        records[-1] = make_record(4, visible_matches=False)
        report = build_report(records, min_multi_candidate_cases=5, min_disagreements=2)

        self.assertEqual(report["status"], "blocked_by_shadow_safety_failure")
        self.assertFalse(report["gate"]["shadow_never_changes_visible_output"])
        self.assertEqual(report["summary"]["visible_change_violation_count"], 1)

    def test_duplicate_turn_uses_latest_record(self):
        old = make_record(1, disagree=False)
        new = make_record(1, disagree=True)
        new["timestamp"] = "2026-07-07T15:00:00"
        report = build_report([old, new], min_multi_candidate_cases=1, min_disagreements=1)

        self.assertEqual(report["summary"]["active_shadow_case_count"], 1)
        self.assertEqual(report["summary"]["disagreement_count"], 1)

    def test_jsonl_loader_counts_invalid_lines_without_failing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "log.jsonl"
            path.write_text(json.dumps(make_record(1), ensure_ascii=False) + "\nnot-json\n", encoding="utf-8")
            records, meta = load_jsonl(path)

        self.assertEqual(len(records), 1)
        self.assertEqual(meta["invalid_line_count"], 1)
        self.assertEqual(meta["nonempty_line_count"], 2)

    def test_parse_errors_block_quality_readiness(self):
        records = [make_record(index, disagree=index < 2) for index in range(5)]
        report = build_report(
            records,
            source_meta={"exists": True, "invalid_line_count": 1, "nonempty_line_count": 6},
            min_multi_candidate_cases=5,
            min_disagreements=2,
        )

        self.assertEqual(report["status"], "blocked_by_source_log_parse_errors")
        self.assertFalse(report["quality_comparison_ready"])
        self.assertFalse(report["gate"]["source_log_has_no_invalid_lines"])


if __name__ == "__main__":
    unittest.main()
