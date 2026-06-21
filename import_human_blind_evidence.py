"""Import completed blind ratings into reproducible research evidence.

All candidate systems remain in the comparison report. Only human ratings for
the actual Uruha system become annotation/regression inputs.
"""

import csv
import hashlib
import json
import os
import re
from collections import Counter, defaultdict
from datetime import datetime

from human_feedback_validation import invalid_annotation_reason
from project_paths import (
    HUMAN_BLIND_DATA_DIR,
    HUMAN_BLIND_EVIDENCE_REPORT_JSON_PATH,
    HUMAN_BLIND_EVIDENCE_REPORT_MD_PATH,
    HUMAN_FEEDBACK_ANNOTATIONS_JSONL_PATH,
)


S0_SYSTEM_ID = "S0_URUHA_RIGHTBRAIN"
DECISION_TO_VERDICT = {"yes": "pass", "borderline": "mixed", "no": "fail"}


def _source_path(filename):
    return os.path.join(HUMAN_BLIND_DATA_DIR, filename)


DEFAULT_SOURCE_SPECS = [
    {
        "source_id": "v15_fresh_after_reply_priority_repair_partial_2026_05_24",
        "source_package": "rightbrain_meaning_unseen_v15_fresh_after_reply_priority_repair",
        "ratings_path": _source_path("v15_partial_ratings.csv"),
        "key_path": _source_path("v15_rating_key.jsonl"),
        "sheet_path": _source_path("v15_rating_sheet.csv"),
        "score_fields": [
            "semantic_completeness_1_5",
            "naturalness_1_5",
            "style_consistency_1_5",
            "user_facing_ok_1_5",
        ],
        "decision_field": "chat_ready",
        "semantic_field": "semantic_completeness_1_5",
        "naturalness_field": "naturalness_1_5",
        "rated_at": "2026-05-24T00:00:00+09:00",
        "timestamp_precision": "date_only",
        "designed_task_count": 40,
    },
    {
        "source_id": "v16_followup_compact_partial_2026_05_24",
        "source_package": "rightbrain_meaning_v16_followup_compact_blind_rating",
        "ratings_path": _source_path("v16_partial_ratings.csv"),
        "key_path": _source_path("v16_rating_key.jsonl"),
        "sheet_path": _source_path("v16_rating_sheet.csv"),
        "score_fields": ["semantic_understanding_1_5", "human_likeness_1_5"],
        "decision_field": "direct_chat_ok",
        "semantic_field": "semantic_understanding_1_5",
        "naturalness_field": "human_likeness_1_5",
        "rated_at": "2026-05-24T00:00:00+09:00",
        "timestamp_precision": "date_only",
        "designed_task_count": 12,
    },
]


def _read_csv(path):
    with open(path, "r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _read_jsonl(path):
    rows = []
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _load_jsonl_if_exists(path):
    if not os.path.exists(path):
        return []
    return _read_jsonl(path)


def _sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_score(value):
    try:
        score = float(value)
    except (TypeError, ValueError):
        return None
    return score if 1.0 <= score <= 5.0 else None


def _mean(values):
    values = [float(value) for value in values if value is not None]
    return round(sum(values) / len(values), 4) if values else None


def _parse_marker_groups(value):
    try:
        groups = json.loads(str(value or "[]"))
    except (TypeError, ValueError, json.JSONDecodeError):
        return []
    output = []
    for group in groups if isinstance(groups, list) else []:
        markers = [str(marker).strip() for marker in (group if isinstance(group, list) else [])]
        markers = [marker for marker in markers if marker]
        if markers:
            output.append(markers)
    return output


def _split_markers(value):
    return [marker.strip() for marker in re.split(r"[,，\n]", str(value or "")) if marker.strip()]


def _rate(numerator, denominator):
    return round(float(numerator) / float(denominator), 4) if denominator else 0.0


def _complete_rating(row, spec):
    decision = str(row.get(spec["decision_field"]) or "").strip().lower()
    if decision not in DECISION_TO_VERDICT:
        return False
    return all(_safe_score(row.get(field)) is not None for field in spec["score_fields"])


def _failure_types(processed):
    if processed["verdict"] == "pass":
        return []

    failures = ["RIGHTBRAIN_SURFACE_ERROR"]
    source_id = processed["source_id"]
    scores = processed["scores"]
    note = str(processed.get("notes") or "")
    semantic_score = scores.get(processed["semantic_field"])
    naturalness_score = scores.get(processed["naturalness_field"])

    if semantic_score is not None and semantic_score <= 2.0:
        failures.append("LOW_DENSITY" if source_id.startswith("v15") else "MISREAD_INTENT")
    if naturalness_score is not None and naturalness_score <= 2.0:
        failures.append("TOO_ROBOTIC_LOGIC")
    if "模板" in note:
        failures.append("GENERIC_REPLY")
    if "重複" in note or "重复" in note:
        failures.append("REPEATED_REPLY")
    if any(marker in note for marker in ("廁所不是浴室", "厕所不是浴室", "理解錯", "理解错", "答錯", "答错")):
        failures.append("MISREAD_INTENT")
    if any(marker in note for marker in ("只把", "只是說", "只是说", "沒有說", "没有说", "沒回答", "没回答", "太短")):
        failures.append("LOW_DENSITY")

    return list(dict.fromkeys(failures))


def _build_annotation(processed):
    verdict = processed["verdict"]
    severity = "low" if verdict == "pass" else ("medium" if verdict == "mixed" else "high")
    note = str(processed.get("notes") or "").strip()
    if not note:
        note = (
            f"blind score={processed['mean_score_1_5']}/5; "
            f"decision={processed['decision']}"
        )
    record = {
        "timestamp": processed["rated_at"],
        "session_id": f"human_blind:{processed['source_id']}",
        "turn_index": processed["task_id"],
        "input_mode": "human_blind_import",
        "user_text": processed["input"],
        "assistant_reply": processed["output_text"],
        "verdict": verdict,
        "severity": severity,
        "failure_types": [],
        "notes": note,
        "proxy_flags": {},
        "planner_debug": {
            "intent": processed.get("category") or "unknown",
            "scene": "human_blind",
        },
        "logic": {
            "intent": processed.get("category") or "unknown",
            "scene": "human_blind",
            "response_mode": "blind_candidate_output",
        },
        "selected_plan": {},
        "source_kind": "human_blind_import",
        "provenance": {
            "source_id": processed["source_id"],
            "review_id": processed["review_id"],
            "task_id": processed["task_id"],
            "system_id": processed["system_id"],
            "output_label": processed["output_label"],
            "source_hashes": processed["source_hashes"],
            "timestamp_precision": processed.get("timestamp_precision", "unknown"),
        },
        "human_ratings": {
            "scores": processed["scores"],
            "mean_score_1_5": processed["mean_score_1_5"],
            "decision": processed["decision"],
        },
        "human_contract": {
            "required_meaning": processed.get("required_meaning") or "",
            "required_marker_groups": processed.get("required_marker_groups") or [],
            "forbidden_markers": processed.get("forbidden_markers") or [],
        },
    }
    record["failure_types"] = _failure_types(processed)
    reason = invalid_annotation_reason(record)
    if reason:
        raise ValueError(f"invalid imported annotation {processed['review_id']}: {reason}")
    return record


def load_blind_evidence(source_specs=None):
    source_specs = list(source_specs or DEFAULT_SOURCE_SPECS)
    processed_rows = []
    source_summaries = []
    seen_review_ids = set()

    for spec in source_specs:
        ratings = _read_csv(spec["ratings_path"])
        keys = {row["review_id"]: row for row in _read_jsonl(spec["key_path"])}
        sheet_rows = {row["review_id"]: row for row in _read_csv(spec["sheet_path"])}
        hashes = {
            "ratings_sha256": _sha256(spec["ratings_path"]),
            "key_sha256": _sha256(spec["key_path"]),
            "sheet_sha256": _sha256(spec["sheet_path"]),
        }
        complete_rows = [row for row in ratings if _complete_rating(row, spec)]
        incomplete_rows = [row for row in ratings if row not in complete_rows]
        missing_join_ids = []

        for rating in complete_rows:
            review_id = str(rating.get("review_id") or "").strip()
            if review_id in seen_review_ids:
                raise ValueError(f"duplicate completed review_id: {review_id}")
            key = keys.get(review_id)
            sheet = sheet_rows.get(review_id)
            if not key or not sheet:
                missing_join_ids.append(review_id)
                continue
            seen_review_ids.add(review_id)
            scores = {field: _safe_score(rating.get(field)) for field in spec["score_fields"]}
            decision = str(rating.get(spec["decision_field"]) or "").strip().lower()
            processed_rows.append(
                {
                    "source_id": spec["source_id"],
                    "rated_at": spec["rated_at"],
                    "timestamp_precision": spec.get("timestamp_precision", "unknown"),
                    "review_id": review_id,
                    "task_id": str(rating.get("task_id") or sheet.get("task_id") or "").strip(),
                    "output_label": str(rating.get("output_label") or key.get("output_label") or "").strip(),
                    "system_id": key.get("system_id"),
                    "category": sheet.get("category"),
                    "input": sheet.get("input"),
                    "output_text": sheet.get("output_text"),
                    "required_meaning": sheet.get("leftbrain_required_meaning"),
                    "required_marker_groups": _parse_marker_groups(sheet.get("required_marker_groups")),
                    "forbidden_markers": _split_markers(sheet.get("forbidden_markers")),
                    "scores": scores,
                    "semantic_field": spec["semantic_field"],
                    "naturalness_field": spec["naturalness_field"],
                    "mean_score_1_5": _mean(scores.values()),
                    "decision": decision,
                    "verdict": DECISION_TO_VERDICT[decision],
                    "notes": str(rating.get("notes") or "").strip(),
                    "source_hashes": hashes,
                }
            )

        source_summaries.append(
            {
                "source_id": spec["source_id"],
                "source_package": spec.get("source_package", spec["source_id"]),
                "designed_task_count": int(spec.get("designed_task_count") or 0),
                "rating_row_count": len(ratings),
                "completed_candidate_count": len(complete_rows),
                "completed_task_count": len({row.get("task_id") for row in complete_rows}),
                "incomplete_candidate_count": len(incomplete_rows),
                "missing_join_count": len(missing_join_ids),
                "missing_join_ids": missing_join_ids,
                "hashes": hashes,
                "timestamp_precision": spec.get("timestamp_precision", "unknown"),
            }
        )

    s0_annotations = [_build_annotation(row) for row in processed_rows if row["system_id"] == S0_SYSTEM_ID]
    return processed_rows, s0_annotations, source_summaries


def _aggregate_by_system(rows):
    grouped = defaultdict(list)
    for row in rows:
        grouped[str(row.get("system_id") or "unknown")].append(row)
    output = []
    for system_id, items in sorted(grouped.items()):
        decisions = Counter(item["decision"] for item in items)
        output.append(
            {
                "system_id": system_id,
                "n": len(items),
                "mean_score_1_5": _mean(item["mean_score_1_5"] for item in items),
                "normalized_mean_score": _mean(item["mean_score_1_5"] / 5.0 for item in items),
                "chat_ready_yes_count": decisions.get("yes", 0),
                "chat_ready_yes_rate": _rate(decisions.get("yes", 0), len(items)),
                "chat_ready_acceptable_count": decisions.get("yes", 0) + decisions.get("borderline", 0),
                "chat_ready_acceptable_rate": _rate(
                    decisions.get("yes", 0) + decisions.get("borderline", 0), len(items)
                ),
                "decision_breakdown": dict(sorted(decisions.items())),
            }
        )
    return output


def _pairwise_s0(rows):
    by_task = defaultdict(dict)
    for row in rows:
        by_task[(row["source_id"], row["task_id"])][row["system_id"]] = row
    controls = sorted({row["system_id"] for row in rows if row["system_id"] != S0_SYSTEM_ID})
    output = []
    for control in controls:
        wins = ties = losses = paired = 0
        for systems in by_task.values():
            if S0_SYSTEM_ID not in systems or control not in systems:
                continue
            paired += 1
            delta = systems[S0_SYSTEM_ID]["mean_score_1_5"] - systems[control]["mean_score_1_5"]
            if delta > 1e-9:
                wins += 1
            elif delta < -1e-9:
                losses += 1
            else:
                ties += 1
        output.append(
            {
                "control_system_id": control,
                "paired_task_count": paired,
                "s0_wins": wins,
                "ties": ties,
                "s0_losses": losses,
                "s0_win_rate_excluding_ties": _rate(wins, wins + losses),
            }
        )
    return output


def build_evidence_report(rows, annotations, source_summaries):
    by_system = _aggregate_by_system(rows)
    system_map = {row["system_id"]: row for row in by_system}
    s0 = system_map.get(S0_SYSTEM_ID) or {}
    fail_like = [record for record in annotations if record["verdict"] in {"mixed", "fail"}]
    low_cases = sorted(
        [row for row in rows if row["system_id"] == S0_SYSTEM_ID],
        key=lambda row: (row["mean_score_1_5"], row["review_id"]),
    )[:8]
    return {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "scope": "partial_human_blind_evidence",
        "method": {
            "blinding": "Candidate labels were joined to system IDs only after human ratings were completed.",
            "empty_row_policy": "Rows missing any required score or final decision are excluded.",
            "annotation_policy": "Only S0_URUHA_RIGHTBRAIN rows enter the Uruha annotation stream.",
            "verdict_mapping": DECISION_TO_VERDICT,
        },
        "summary": {
            "source_count": len(source_summaries),
            "completed_task_count": len({(row["source_id"], row["task_id"]) for row in rows}),
            "completed_candidate_rating_count": len(rows),
            "s0_annotation_count": len(annotations),
            "s0_fail_like_annotation_count": len(fail_like),
            "s0_mean_score_1_5": s0.get("mean_score_1_5"),
            "s0_normalized_mean_score": s0.get("normalized_mean_score"),
            "s0_chat_ready_yes_rate": s0.get("chat_ready_yes_rate"),
            "s0_chat_ready_acceptable_rate": s0.get("chat_ready_acceptable_rate"),
        },
        "sources": source_summaries,
        "by_system": by_system,
        "pairwise_s0_vs_controls": _pairwise_s0(rows),
        "s0_low_cases": [
            {
                "source_id": row["source_id"],
                "review_id": row["review_id"],
                "task_id": row["task_id"],
                "category": row.get("category"),
                "input": row.get("input"),
                "output_text": row.get("output_text"),
                "mean_score_1_5": row.get("mean_score_1_5"),
                "decision": row.get("decision"),
                "notes": row.get("notes"),
            }
            for row in low_cases
        ],
        "processed_ratings": rows,
    }


def build_markdown(report):
    summary = report["summary"]
    lines = [
        "# Human Blind Evidence Report",
        "",
        f"- completed tasks: `{summary['completed_task_count']}`",
        f"- completed candidate ratings: `{summary['completed_candidate_rating_count']}`",
        f"- Uruha annotations imported: `{summary['s0_annotation_count']}`",
        f"- Uruha fail-like regression candidates: `{summary['s0_fail_like_annotation_count']}`",
        f"- Uruha mean human score: `{summary['s0_mean_score_1_5']} / 5`",
        f"- Uruha chat-ready yes rate: `{summary['s0_chat_ready_yes_rate']}`",
        "",
        "## System comparison",
        "",
        "| system | n | mean / 5 | chat-ready yes | acceptable |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in report["by_system"]:
        lines.append(
            f"| {row['system_id']} | {row['n']} | {row['mean_score_1_5']:.3f} | "
            f"{row['chat_ready_yes_rate']:.3f} | {row['chat_ready_acceptable_rate']:.3f} |"
        )
    lines.extend(["", "## Paired S0 comparison", "", "| control | paired | wins | ties | losses |", "|---|---:|---:|---:|---:|"])
    for row in report["pairwise_s0_vs_controls"]:
        lines.append(
            f"| {row['control_system_id']} | {row['paired_task_count']} | "
            f"{row['s0_wins']} | {row['ties']} | {row['s0_losses']} |"
        )
    lines.extend(
        [
            "",
            "## Evidence boundary",
            "",
            "This is a partial single-rater pilot. It is valid evidence of the completed items, "
            "but it is not a population estimate and does not replace interactive conversation evaluation.",
        ]
    )
    return "\n".join(lines) + "\n"


def merge_annotation_stream(existing_records, imported_records):
    retained = [record for record in existing_records if record.get("source_kind") != "human_blind_import"]
    return retained + sorted(
        imported_records,
        key=lambda record: (record["session_id"], str(record["turn_index"])),
    )


def _write_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def _write_jsonl(path, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def main():
    rows, annotations, sources = load_blind_evidence()
    report = build_evidence_report(rows, annotations, sources)
    merged_annotations = merge_annotation_stream(
        _load_jsonl_if_exists(HUMAN_FEEDBACK_ANNOTATIONS_JSONL_PATH),
        annotations,
    )
    _write_jsonl(HUMAN_FEEDBACK_ANNOTATIONS_JSONL_PATH, merged_annotations)
    _write_json(HUMAN_BLIND_EVIDENCE_REPORT_JSON_PATH, report)
    with open(HUMAN_BLIND_EVIDENCE_REPORT_MD_PATH, "w", encoding="utf-8") as handle:
        handle.write(build_markdown(report))
    print(
        json.dumps(
            {
                "completed_candidate_ratings": len(rows),
                "s0_annotations": len(annotations),
                "s0_fail_like": report["summary"]["s0_fail_like_annotation_count"],
                "report": HUMAN_BLIND_EVIDENCE_REPORT_JSON_PATH,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
