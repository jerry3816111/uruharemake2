from build_human_feedback_annotation_report import build_report as build_annotation_report
from build_human_feedback_regression_dataset import build_dataset as build_regression_dataset
from human_feedback_validation import (
    invalid_annotation_reason,
    is_valid_annotation_record,
    split_valid_annotations,
)


SCHEMA = {
    "version": "test",
    "verdict_options": [
        {"value": "pass", "label_zh": "通過"},
        {"value": "mixed", "label_zh": "部分失敗"},
        {"value": "fail", "label_zh": "失敗"},
    ],
    "severity_options": [
        {"value": "low", "label_zh": "低"},
        {"value": "medium", "label_zh": "中"},
        {"value": "high", "label_zh": "高"},
    ],
    "failure_types": [
        {
            "code": "LOW_DENSITY",
            "label_zh": "資訊空洞",
            "trace_proxies": ["focus_anchor_miss"],
        }
    ],
}


VALID_RECORD = {
    "timestamp": "2026-04-29T12:00:00",
    "taxonomy_version": "test",
    "session_id": "sess-a",
    "turn_index": 1,
    "input_mode": "text",
    "verdict": "fail",
    "severity": "high",
    "failure_types": ["LOW_DENSITY"],
    "notes": "太空。",
    "user_text": "你要不要吃蘋果派",
    "assistant_reply": "そうなんだ。",
    "memory_snapshot": {},
    "planner_debug": {"intent": "food_offer", "scene": "casual"},
    "selected_plan": {
        "focus_anchor": "蘋果派",
        "reply_obligation": "answer_food_offer",
        "post_check": {
            "did_reply_cover_focus": False,
            "did_reply_follow_obligation": False,
        },
    },
    "proxy_flags": {"focus_anchor_miss": True},
    "logic": {"intent": "food_offer"},
    "cognition_trace": {"route_info": {"route": "high_road"}},
}


INVALID_PLACEHOLDER = {
    "timestamp": "2026-04-29T12:01:00",
    "session_id": None,
    "turn_index": None,
    "verdict": "mixed",
    "severity": "medium",
    "failure_types": [],
    "user_text": None,
    "assistant_reply": None,
}


def test_placeholder_rows_are_rejected():
    assert not is_valid_annotation_record(INVALID_PLACEHOLDER, valid_failure_types={"LOW_DENSITY"})
    assert "missing session_id" in invalid_annotation_reason(INVALID_PLACEHOLDER, valid_failure_types={"LOW_DENSITY"})


def test_valid_rows_drive_reports_and_regression_dataset():
    valid, invalid = split_valid_annotations(
        [INVALID_PLACEHOLDER, VALID_RECORD],
        valid_failure_types={"LOW_DENSITY"},
    )
    assert valid == [VALID_RECORD]
    assert len(invalid) == 1

    annotation_report = build_annotation_report(
        valid,
        schema=SCHEMA,
        source_path="memory",
        invalid_records=invalid,
    )
    assert annotation_report["summary"]["raw_record_count"] == 2
    assert annotation_report["summary"]["invalid_record_count"] == 1
    assert annotation_report["summary"]["annotation_count"] == 1

    dataset, regression_report = build_regression_dataset(
        annotation_records=valid,
        schema=SCHEMA,
        web_log_records=[VALID_RECORD],
        invalid_annotation_count=len(invalid),
    )
    assert len(dataset) == 1
    assert dataset[0]["prompt"] == VALID_RECORD["user_text"]
    assert regression_report["summary"]["annotation_count_raw"] == 2
    assert regression_report["summary"]["invalid_annotation_count"] == 1
    assert regression_report["summary"]["regression_case_count"] == 1


if __name__ == "__main__":
    test_placeholder_rows_are_rejected()
    test_valid_rows_drive_reports_and_regression_dataset()
    print("human feedback validation smoke tests passed")
