import json
import os
from collections import Counter
from datetime import datetime

from project_paths import (
    ANNOTATION_CANDIDATE_QUEUE_JSON_PATH,
    ANNOTATION_DRAFT_QUEUE_JSON_PATH,
    ANNOTATION_DRAFT_QUEUE_MD_PATH,
    FAILURE_TAXONOMY_SCHEMA_PATH,
    HUMAN_FEEDBACK_ANNOTATIONS_JSONL_PATH,
    WEB_CONVERSATION_LOG_JSONL_PATH,
)


REASON_TO_FAILURE_TYPES = {
    "LOW_DENSITY": ["LOW_DENSITY"],
    "LOW_VARIETY": ["LOW_DENSITY", "GENERIC_REPLY"],
    "GENERIC_REPLY": ["GENERIC_REPLY", "LOW_DENSITY"],
    "REPEATED_REPLY": ["REPEATED_REPLY", "GENERIC_REPLY"],
    "ENGLISH_LEAK": ["RIGHTBRAIN_SURFACE_ERROR"],
    "HARSH_FIXED_TEMPLATE": ["WRONG_BOUNDARY", "TOO_ROBOTIC_LOGIC"],
    "MISREAD_ABUSE_AS_SUPPORT": ["MISSED_VIBE", "WRONG_BOUNDARY"],
    "COMFORT_ON_ABUSE": ["MISSED_VIBE", "WRONG_BOUNDARY"],
    "WRONG_BOUNDARY_COMPLIANCE": ["WRONG_BOUNDARY"],
    "MISREAD_SUPPORT_AS_REFUSAL": ["MISSED_VIBE", "WRONG_BOUNDARY"],
    "QUESTION_UNDERANSWERED": ["MISREAD_INTENT", "LOW_DENSITY"],
    "MISSED_CULTURE_CONTEXT": ["MISSED_JOKE_OR_CULTURE", "MISREAD_INTENT"],
}


def _load_json(path):
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _load_jsonl(path):
    rows = []
    if not os.path.exists(path):
        return rows
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except Exception:
                continue
    return rows


def _sort_counter(counter):
    return [
        {"key": key, "count": count}
        for key, count in sorted(counter.items(), key=lambda item: (-item[1], str(item[0])))
    ]


def _trim_text(text, limit=88):
    text = " ".join(str(text or "").split()).strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


def _make_turn_key(record):
    session_id = str(record.get("session_id") or "").strip()
    turn_index = str(record.get("turn_index") or "").strip()
    return session_id, turn_index


def _taxonomy_meta(schema):
    failure_types = schema.get("failure_types") or []
    return {
        "labels": {item.get("code"): item.get("label_zh") for item in failure_types},
        "valid_codes": {item.get("code") for item in failure_types if item.get("code")},
    }


def _suggest_failure_types(reason_codes, valid_codes):
    output = []
    seen = set()
    for reason_code in reason_codes or []:
        for failure_code in REASON_TO_FAILURE_TYPES.get(reason_code, []):
            if failure_code in valid_codes and failure_code not in seen:
                output.append(failure_code)
                seen.add(failure_code)
    return output


def _suggest_verdict(score, failure_types):
    if score >= 8 or len(failure_types) >= 2:
        return "fail"
    if score >= 4 or failure_types:
        return "mixed"
    return "pass"


def _suggest_severity(score, reason_codes):
    reason_codes = set(reason_codes or [])
    if score >= 12 or {"MISREAD_ABUSE_AS_SUPPORT", "ENGLISH_LEAK"} & reason_codes:
        return "high"
    if score >= 6:
        return "medium"
    return "low"


def _suggested_notes(reason_codes, failure_types):
    parts = []
    if reason_codes:
        parts.append("auto-draft from candidate queue: " + ", ".join(reason_codes))
    if failure_types:
        parts.append("suggested failure types: " + ", ".join(failure_types))
    return " | ".join(parts)


def build_report(candidate_payload, web_logs, annotations, schema):
    meta = _taxonomy_meta(schema)
    candidate_rows = candidate_payload.get("candidates") or []
    web_by_turn = {_make_turn_key(record): record for record in web_logs}
    annotated_turns = {_make_turn_key(record) for record in annotations}

    drafts = []
    reason_counter = Counter()
    failure_counter = Counter()

    for candidate in candidate_rows:
        turn_key = (str(candidate.get("session_id") or "").strip(), str(candidate.get("turn_index") or "").strip())
        if turn_key in annotated_turns:
            continue
        source_record = web_by_turn.get(turn_key)
        if not source_record:
            continue

        reason_codes = list(candidate.get("reason_codes") or [])
        failure_types = _suggest_failure_types(reason_codes, meta["valid_codes"])
        verdict = _suggest_verdict(int(candidate.get("score") or 0), failure_types)
        severity = _suggest_severity(int(candidate.get("score") or 0), reason_codes)
        notes = _suggested_notes(reason_codes, failure_types)
        draft_id = f"{turn_key[0]}:{turn_key[1]}"

        reason_counter.update(reason_codes)
        failure_counter.update(failure_types)

        drafts.append(
            {
                "draft_id": draft_id,
                "score": int(candidate.get("score") or 0),
                "suggested_verdict": verdict,
                "suggested_severity": severity,
                "suggested_failure_types": failure_types,
                "suggested_failure_labels": [meta["labels"].get(code) for code in failure_types if meta["labels"].get(code)],
                "reason_codes": reason_codes,
                "reason_details": candidate.get("reasons") or [],
                "suggested_notes": notes,
                "compact_context": {
                    "timestamp": source_record.get("timestamp"),
                    "session_id": source_record.get("session_id"),
                    "turn_index": source_record.get("turn_index"),
                    "user_text": _trim_text(source_record.get("user_text"), 120),
                    "assistant_reply": _trim_text(source_record.get("assistant_reply"), 120),
                    "intent": ((source_record.get("planner_debug") or {}).get("intent") or (source_record.get("logic") or {}).get("intent")),
                    "scene": ((source_record.get("planner_debug") or {}).get("scene") or (source_record.get("logic") or {}).get("scene")),
                },
                "source_record": source_record,
            }
        )

    drafts.sort(key=lambda row: (row.get("score", 0), row.get("compact_context", {}).get("timestamp") or ""), reverse=True)

    report = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "source_paths": {
            "candidate_queue": ANNOTATION_CANDIDATE_QUEUE_JSON_PATH,
            "web_logs": WEB_CONVERSATION_LOG_JSONL_PATH,
            "annotations": HUMAN_FEEDBACK_ANNOTATIONS_JSONL_PATH,
            "schema": FAILURE_TAXONOMY_SCHEMA_PATH,
        },
        "summary": {
            "candidate_count": len(candidate_rows),
            "annotated_turn_count": len(annotated_turns),
            "draft_count": len(drafts),
            "high_priority_draft_count": sum(1 for row in drafts if row.get("score", 0) >= 8),
        },
        "breakdowns": {
            "reason_codes": _sort_counter(reason_counter),
            "suggested_failure_types": [
                {
                    "code": key,
                    "label_zh": meta["labels"].get(key),
                    "count": count,
                }
                for key, count in sorted(failure_counter.items(), key=lambda item: (-item[1], str(item[0])))
            ],
        },
        "drafts": drafts[:100],
    }
    return report


def build_markdown(report):
    summary = report.get("summary") or {}
    lines = [
        "# Annotation Draft Queue",
        "",
        f"- generated_at: {report.get('generated_at')}",
        f"- candidate_count: {summary.get('candidate_count', 0)}",
        f"- annotated_turn_count: {summary.get('annotated_turn_count', 0)}",
        f"- draft_count: {summary.get('draft_count', 0)}",
        f"- high_priority_draft_count: {summary.get('high_priority_draft_count', 0)}",
        "",
        "## Suggested Failure Types",
        "",
    ]
    for row in (report.get("breakdowns") or {}).get("suggested_failure_types") or []:
        lines.append(f"- {row.get('code')} ({row.get('label_zh')}): {row.get('count')}")
    if not ((report.get("breakdowns") or {}).get("suggested_failure_types") or []):
        lines.append("- none")

    lines.extend(["", "## Drafts", ""])
    for row in report.get("drafts") or []:
        compact = row.get("compact_context") or {}
        lines.append(
            f"- draft_id={row.get('draft_id')} score={row.get('score')} "
            f"verdict={row.get('suggested_verdict')} severity={row.get('suggested_severity')} "
            f"failure={row.get('suggested_failure_types')} reasons={row.get('reason_codes')} "
            f"user={compact.get('user_text')} reply={compact.get('assistant_reply')}"
        )
    if not (report.get("drafts") or []):
        lines.append("- none")
    return "\n".join(lines) + "\n"


def main():
    candidate_payload = _load_json(ANNOTATION_CANDIDATE_QUEUE_JSON_PATH)
    web_logs = _load_jsonl(WEB_CONVERSATION_LOG_JSONL_PATH)
    annotations = _load_jsonl(HUMAN_FEEDBACK_ANNOTATIONS_JSONL_PATH)
    schema = _load_json(FAILURE_TAXONOMY_SCHEMA_PATH)

    report = build_report(candidate_payload, web_logs, annotations, schema)

    with open(ANNOTATION_DRAFT_QUEUE_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    with open(ANNOTATION_DRAFT_QUEUE_MD_PATH, "w", encoding="utf-8") as f:
        f.write(build_markdown(report))

    print(ANNOTATION_DRAFT_QUEUE_JSON_PATH)
    print(ANNOTATION_DRAFT_QUEUE_MD_PATH)
    print(json.dumps(report.get("summary") or {}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
