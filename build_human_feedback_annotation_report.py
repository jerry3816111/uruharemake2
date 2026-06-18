import argparse
import json
import os
from collections import Counter, defaultdict
from datetime import datetime

from project_paths import (
    FAILURE_TAXONOMY_SCHEMA_PATH,
    HUMAN_FEEDBACK_ANNOTATION_REPORT_JSON_PATH,
    HUMAN_FEEDBACK_ANNOTATION_REPORT_MD_PATH,
    HUMAN_FEEDBACK_ANNOTATIONS_JSONL_PATH,
)
from human_feedback_validation import invalid_reason_counts, split_valid_annotations


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


def _safe_rate(numerator, denominator, digits=4):
    if not denominator:
        return 0.0
    return round(float(numerator) / float(denominator), digits)


def _trim_text(text, limit=88):
    text = " ".join(str(text or "").split()).strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


def _sort_counter(counter):
    return [
        {"key": key, "count": count}
        for key, count in sorted(counter.items(), key=lambda item: (-item[1], str(item[0])))
    ]


def _taxonomy_maps(schema):
    failure_types = schema.get("failure_types") or []
    verdict_options = schema.get("verdict_options") or []
    severity_options = schema.get("severity_options") or []
    return {
        "failure_type_labels": {item.get("code"): item.get("label_zh") for item in failure_types},
        "failure_type_proxies": {item.get("code"): list(item.get("trace_proxies") or []) for item in failure_types},
        "failure_type_codes": [item.get("code") for item in failure_types],
        "verdict_labels": {item.get("value"): item.get("label_zh") for item in verdict_options},
        "severity_labels": {item.get("value"): item.get("label_zh") for item in severity_options},
    }


def _proxy_alignment(records, failure_type_proxies):
    rows = []
    for failure_code, proxies in failure_type_proxies.items():
        annotated = [record for record in records if failure_code in (record.get("failure_types") or [])]
        if not annotated:
            rows.append(
                {
                    "failure_type": failure_code,
                    "annotated_count": 0,
                    "proxy_support_count": 0,
                    "proxy_support_rate": 0.0,
                    "trace_proxies": proxies,
                }
            )
            continue
        supported = 0
        for record in annotated:
            flags = record.get("proxy_flags") or {}
            if any(bool(flags.get(proxy)) for proxy in proxies):
                supported += 1
        rows.append(
            {
                "failure_type": failure_code,
                "annotated_count": len(annotated),
                "proxy_support_count": supported,
                "proxy_support_rate": _safe_rate(supported, len(annotated)),
                "trace_proxies": proxies,
            }
        )
    return rows


def _bucket_breakdown(records, field_name):
    buckets = defaultdict(list)
    for record in records:
        value = str(((record.get("planner_debug") or {}).get(field_name) or (record.get("logic") or {}).get(field_name) or "unknown")).strip() or "unknown"
        buckets[value].append(record)
    rows = []
    for key, items in sorted(buckets.items(), key=lambda item: (-len(item[1]), str(item[0]))):
        fail_like = sum(1 for item in items if item.get("verdict") in {"mixed", "fail"})
        rows.append(
            {
                field_name: key,
                "count": len(items),
                "fail_like_count": fail_like,
                "fail_like_rate": _safe_rate(fail_like, len(items)),
            }
        )
    return rows


def _co_occurrence(records):
    pair_counter = Counter()
    for record in records:
        failure_types = sorted(set(record.get("failure_types") or []))
        for i, left in enumerate(failure_types):
            for right in failure_types[i + 1:]:
                pair_counter[(left, right)] += 1
    return [
        {"pair": list(pair), "count": count}
        for pair, count in pair_counter.most_common(12)
    ]


def _recent_annotations(records, limit):
    recent = sorted(records, key=lambda item: str(item.get("timestamp") or ""), reverse=True)[:limit]
    rows = []
    for record in recent:
        planner_debug = record.get("planner_debug") or {}
        selected_plan = record.get("selected_plan") or {}
        rows.append(
            {
                "timestamp": record.get("timestamp"),
                "session_id": record.get("session_id"),
                "turn_index": record.get("turn_index"),
                "verdict": record.get("verdict"),
                "severity": record.get("severity"),
                "failure_types": record.get("failure_types") or [],
                "intent": planner_debug.get("intent") or (record.get("logic") or {}).get("intent"),
                "scene": planner_debug.get("scene") or (record.get("logic") or {}).get("scene"),
                "focus_anchor": selected_plan.get("focus_anchor"),
                "user_text": _trim_text(record.get("user_text")),
                "assistant_reply": _trim_text(record.get("assistant_reply")),
                "notes": _trim_text(record.get("notes"), limit=120),
            }
        )
    return rows


def _samples_by_failure(records, failure_type_labels, limit):
    grouped = defaultdict(list)
    for record in records:
        for failure_type in record.get("failure_types") or []:
            grouped[failure_type].append(record)

    output = {}
    for failure_type, items in grouped.items():
        sorted_items = sorted(items, key=lambda item: str(item.get("timestamp") or ""), reverse=True)[:limit]
        output[failure_type] = {
            "label_zh": failure_type_labels.get(failure_type),
            "samples": [
                {
                    "timestamp": item.get("timestamp"),
                    "verdict": item.get("verdict"),
                    "severity": item.get("severity"),
                    "user_text": _trim_text(item.get("user_text")),
                    "assistant_reply": _trim_text(item.get("assistant_reply")),
                    "notes": _trim_text(item.get("notes"), limit=120),
                }
                for item in sorted_items
            ],
        }
    return output


def build_report(records, schema, source_path, max_recent=15, max_samples_per_type=3, invalid_records=None):
    meta = _taxonomy_maps(schema)
    invalid_records = list(invalid_records or [])
    verdict_options = [item.get("value") for item in (schema.get("verdict_options") or [])]
    severity_options = [item.get("value") for item in (schema.get("severity_options") or [])]
    failure_type_options = [item.get("code") for item in (schema.get("failure_types") or [])]
    verdict_counter = Counter(str(record.get("verdict") or "unknown") for record in records)
    severity_counter = Counter(str(record.get("severity") or "unknown") for record in records)
    failure_type_counter = Counter()
    proxy_flag_counter = Counter()
    focus_anchor_counter = Counter()
    for record in records:
        for failure_type in record.get("failure_types") or []:
            failure_type_counter[failure_type] += 1
        for proxy_name, enabled in (record.get("proxy_flags") or {}).items():
            if enabled:
                proxy_flag_counter[proxy_name] += 1
        focus_anchor = str(((record.get("selected_plan") or {}).get("focus_anchor") or "")).strip()
        if record.get("verdict") in {"mixed", "fail"} and focus_anchor:
            focus_anchor_counter[focus_anchor] += 1

    unique_turns = {(record.get("session_id"), record.get("turn_index")) for record in records}
    fail_like_records = [record for record in records if record.get("verdict") in {"mixed", "fail"}]
    memory_related_records = [
        record
        for record in records
        if "GHOST_MEMORY" in (record.get("failure_types") or [])
        or bool((record.get("proxy_flags") or {}).get("memory_misuse"))
        or bool((record.get("proxy_flags") or {}).get("memory_available_but_silent"))
    ]

    summary = {
        "raw_record_count": len(records) + len(invalid_records),
        "invalid_record_count": len(invalid_records),
        "valid_record_count": len(records),
        "annotation_count": len(records),
        "unique_sessions": len({record.get("session_id") for record in records if record.get("session_id")}),
        "unique_turns": len(unique_turns),
        "fail_like_count": len(fail_like_records),
        "fail_like_rate": _safe_rate(len(fail_like_records), len(records)),
        "memory_related_count": len(memory_related_records),
        "memory_related_rate": _safe_rate(len(memory_related_records), len(records)),
        "taxonomy_version": str(schema.get("version") or "unknown"),
        "source_path": source_path,
    }

    report = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "source_path": source_path,
        "schema_path": FAILURE_TAXONOMY_SCHEMA_PATH,
        "summary": summary,
        "breakdowns": {
            "verdict": [
                {
                    "value": key,
                    "label_zh": meta["verdict_labels"].get(key),
                    "count": verdict_counter.get(key, 0),
                    "rate": _safe_rate(count, len(records)),
                }
                for key, count in ((key, verdict_counter.get(key, 0)) for key in verdict_options)
            ],
            "severity": [
                {
                    "value": key,
                    "label_zh": meta["severity_labels"].get(key),
                    "count": severity_counter.get(key, 0),
                    "rate": _safe_rate(count, len(records)),
                }
                for key, count in ((key, severity_counter.get(key, 0)) for key in severity_options)
            ],
            "failure_types": [
                {
                    "code": key,
                    "label_zh": meta["failure_type_labels"].get(key),
                    "count": failure_type_counter.get(key, 0),
                    "rate": _safe_rate(count, len(records)),
                }
                for key, count in ((key, failure_type_counter.get(key, 0)) for key in failure_type_options)
            ],
            "proxy_flags": [
                {
                    "name": key,
                    "count": count,
                    "rate": _safe_rate(count, len(records)),
                }
                for key, count in proxy_flag_counter.items()
            ],
            "top_focus_anchors_fail_like": [
                {"focus_anchor": key, "count": count}
                for key, count in focus_anchor_counter.most_common(12)
            ],
            "by_intent": _bucket_breakdown(records, "intent")[:12],
            "by_scene": _bucket_breakdown(records, "scene")[:12],
        },
        "proxy_alignment": _proxy_alignment(records, meta["failure_type_proxies"]),
        "co_occurrence": _co_occurrence(records),
        "invalid_records": {
            "count": len(invalid_records),
            "reason_breakdown": invalid_reason_counts(invalid_records),
        },
        "recent_annotations": _recent_annotations(records, max_recent),
        "samples_by_failure_type": _samples_by_failure(records, meta["failure_type_labels"], max_samples_per_type),
    }
    return report


def build_markdown(report):
    summary = report.get("summary") or {}
    verdict_rows = (report.get("breakdowns") or {}).get("verdict") or []
    failure_rows = (report.get("breakdowns") or {}).get("failure_types") or []
    proxy_rows = (report.get("breakdowns") or {}).get("proxy_flags") or []
    alignment_rows = report.get("proxy_alignment") or []
    invalid_rows = (report.get("invalid_records") or {}).get("reason_breakdown") or []
    recent_rows = report.get("recent_annotations") or []

    lines = [
        "# Human Feedback Annotation Report",
        "",
        f"- generated_at: {report.get('generated_at')}",
        f"- taxonomy_version: {summary.get('taxonomy_version')}",
        f"- source_path: `{report.get('source_path')}`",
        "",
        "## Summary",
        "",
        f"- raw_record_count: {summary.get('raw_record_count', 0)}",
        f"- invalid_record_count: {summary.get('invalid_record_count', 0)}",
        f"- valid_record_count: {summary.get('valid_record_count', 0)}",
        f"- annotation_count: {summary.get('annotation_count', 0)}",
        f"- unique_sessions: {summary.get('unique_sessions', 0)}",
        f"- unique_turns: {summary.get('unique_turns', 0)}",
        f"- fail_like_count: {summary.get('fail_like_count', 0)}",
        f"- fail_like_rate: {summary.get('fail_like_rate', 0.0)}",
        f"- memory_related_count: {summary.get('memory_related_count', 0)}",
        f"- memory_related_rate: {summary.get('memory_related_rate', 0.0)}",
        "",
        "## Verdict Breakdown",
        "",
    ]
    for row in verdict_rows:
        lines.append(f"- {row.get('value')} ({row.get('label_zh')}): count={row.get('count')} rate={row.get('rate')}")

    lines.extend(["", "## Failure Type Breakdown", ""])
    for row in failure_rows:
        lines.append(f"- {row.get('code')} ({row.get('label_zh')}): count={row.get('count')} rate={row.get('rate')}")

    lines.extend(["", "## Proxy Flag Breakdown", ""])
    for row in proxy_rows:
        lines.append(f"- {row.get('name')}: count={row.get('count')} rate={row.get('rate')}")

    lines.extend(["", "## Proxy Alignment", ""])
    for row in alignment_rows:
        lines.append(
            f"- {row.get('failure_type')}: annotated={row.get('annotated_count')} "
            f"proxy_support={row.get('proxy_support_count')} "
            f"proxy_support_rate={row.get('proxy_support_rate')} "
            f"proxies={row.get('trace_proxies')}"
        )

    lines.extend(["", "## Invalid Record Breakdown", ""])
    if not invalid_rows:
        lines.append("- none")
    for row in invalid_rows:
        lines.append(f"- {row.get('reason')}: count={row.get('count')}")

    lines.extend(["", "## Recent Annotations", ""])
    if not recent_rows:
        lines.append("- none")
    for row in recent_rows[:10]:
        lines.append(
            f"- [{row.get('timestamp')}] session={row.get('session_id')} turn={row.get('turn_index')} "
            f"verdict={row.get('verdict')} severity={row.get('severity')} "
            f"failure={row.get('failure_types')} "
            f"user={row.get('user_text')} "
            f"reply={row.get('assistant_reply')}"
        )
        if row.get("notes"):
            lines.append(f"  - notes: {row.get('notes')}")

    return "\n".join(lines) + "\n"


def parse_args():
    parser = argparse.ArgumentParser(description="Aggregate human feedback annotations into a report.")
    parser.add_argument("--input", default=HUMAN_FEEDBACK_ANNOTATIONS_JSONL_PATH)
    parser.add_argument("--out-json", default=HUMAN_FEEDBACK_ANNOTATION_REPORT_JSON_PATH)
    parser.add_argument("--out-md", default=HUMAN_FEEDBACK_ANNOTATION_REPORT_MD_PATH)
    parser.add_argument("--max-recent", type=int, default=15)
    parser.add_argument("--max-samples-per-type", type=int, default=3)
    return parser.parse_args()


def main():
    args = parse_args()
    schema = _load_json(FAILURE_TAXONOMY_SCHEMA_PATH)
    raw_records = _load_jsonl(args.input)
    taxonomy_meta = _taxonomy_maps(schema)
    records, invalid_records = split_valid_annotations(
        raw_records,
        valid_failure_types=taxonomy_meta["failure_type_codes"],
    )
    report = build_report(
        records,
        schema=schema,
        source_path=args.input,
        max_recent=max(1, args.max_recent),
        max_samples_per_type=max(1, args.max_samples_per_type),
        invalid_records=invalid_records,
    )

    with open(args.out_json, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    with open(args.out_md, "w", encoding="utf-8") as f:
        f.write(build_markdown(report))

    print(args.out_json)
    print(args.out_md)
    print(json.dumps(report.get("summary") or {}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
