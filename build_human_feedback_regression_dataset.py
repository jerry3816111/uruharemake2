import argparse
import json
import os
from collections import Counter, defaultdict
from datetime import datetime

from project_paths import (
    FAILURE_TAXONOMY_SCHEMA_PATH,
    HUMAN_FEEDBACK_ANNOTATIONS_JSONL_PATH,
    HUMAN_FEEDBACK_REGRESSION_DATASET_PATH,
    HUMAN_FEEDBACK_REGRESSION_REPORT_JSON_PATH,
    HUMAN_FEEDBACK_REGRESSION_REPORT_MD_PATH,
    WEB_CONVERSATION_LOG_JSONL_PATH,
)
from human_feedback_validation import invalid_reason_counts, split_valid_annotations


FAIL_LIKE_VERDICTS = {"mixed", "fail"}
FAILURE_TARGETS = {
    "MISREAD_INTENT": [
        "identify_the_actual_social_move",
        "cover_the_user_focus_anchor",
        "fulfill_the_reply_obligation",
    ],
    "LOW_DENSITY": [
        "answer_the_core_request_directly",
        "increase_information_density",
        "avoid_short_hollow_stock_replies",
    ],
    "MISSED_VIBE": [
        "match_user_vibe_before_answering",
        "avoid_wrong_emotional_polarity",
        "respond_to_the_actual_social_move",
    ],
    "MISSED_JOKE_OR_CULTURE": [
        "recognize_possible_meme_lyric_or_irony",
        "ask_or_tease_when_context_is_unknown",
        "avoid_flat_literal_answering",
    ],
    "GENERIC_REPLY": [
        "make_reply_specific_to_this_user_input",
        "avoid_generic_reusable_lines",
        "include_the_focus_anchor_or_concrete_hook",
    ],
    "REPEATED_REPLY": [
        "avoid_repeating_recent_reply_structure",
        "vary_surface_form_without_losing_intent",
    ],
    "TOO_ROBOTIC_LOGIC": [
        "sound_colloquial_and_human",
        "avoid_customer_service_style_phrasing",
        "avoid_overly_generic_template_lines",
    ],
    "WRONG_BOUNDARY": [
        "choose_boundary_strategy_matching_the_social_move",
        "do_not_comply_with_abusive_or_sexualized_pushes",
        "avoid_unnecessary_refusal_when_a_normal_answer_is_expected",
    ],
    "GHOST_MEMORY": [
        "use_relevant_memory_when_available",
        "preserve_causal_continuity_with_context",
        "do_not_drop_salient_memory_anchor",
    ],
    "WRONG_MEMORY_USE": [
        "only_use_relevant_and_speakable_memory",
        "avoid_private_or_misplaced_memory_references",
    ],
    "RIGHTBRAIN_SURFACE_ERROR": [
        "produce_natural_casual_japanese_only",
        "avoid_english_leakage",
        "avoid_surface_form_breakage",
    ],
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


def _safe_rate(numerator, denominator, digits=4):
    if not denominator:
        return 0.0
    return round(float(numerator) / float(denominator), digits)


def _to_int(value, default=0):
    try:
        return int(value)
    except Exception:
        return default


def _collapse_text(value, limit=180):
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        try:
            value = json.dumps(value, ensure_ascii=False)
        except Exception:
            value = str(value)
    text = " ".join(str(value).split()).strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "..."


def _guess_language(text):
    text = str(text or "")
    has_hira_kata = any("\u3040" <= ch <= "\u30ff" for ch in text)
    has_han = any("\u4e00" <= ch <= "\u9fff" for ch in text)
    has_latin = any(("A" <= ch <= "Z") or ("a" <= ch <= "z") for ch in text)
    if has_hira_kata:
        return "ja"
    if has_han and not has_latin:
        return "zh"
    if has_latin and not has_han and not has_hira_kata:
        return "en"
    if has_han and has_latin:
        return "mixed"
    return "unknown"


def _make_turn_key(record):
    session_id = str(record.get("session_id") or "").strip()
    turn_index = record.get("turn_index")
    if session_id and turn_index is not None:
        return session_id, str(turn_index)
    timestamp = str(record.get("timestamp") or "")
    user_text = _collapse_text(record.get("user_text"), limit=60)
    return f"__fallback__:{timestamp}:{user_text}", str(turn_index or timestamp or "0")


def _taxonomy_maps(schema):
    failure_types = schema.get("failure_types") or []
    return {
        "labels": {item.get("code"): item.get("label_zh") for item in failure_types},
        "proxies": {item.get("code"): list(item.get("trace_proxies") or []) for item in failure_types},
        "codes": [item.get("code") for item in failure_types],
    }


def _dedupe_latest_annotations(records):
    latest_by_turn = {}
    for record in records:
        key = _make_turn_key(record)
        previous = latest_by_turn.get(key)
        if previous is None or str(record.get("timestamp") or "") >= str(previous.get("timestamp") or ""):
            latest_by_turn[key] = record
    return sorted(
        latest_by_turn.values(),
        key=lambda item: (
            str(item.get("timestamp") or ""),
            str(item.get("session_id") or ""),
            _to_int(item.get("turn_index"), default=0),
        ),
    )


def _index_web_logs(records):
    by_turn = {}
    by_session = defaultdict(list)
    for record in records:
        key = _make_turn_key(record)
        by_turn[key] = record
        session_id = str(record.get("session_id") or "").strip()
        if session_id:
            by_session[session_id].append(record)

    for session_id, items in by_session.items():
        by_session[session_id] = sorted(
            items,
            key=lambda item: (_to_int(item.get("turn_index"), default=0), str(item.get("timestamp") or "")),
        )
    return by_turn, by_session


def _build_seed_turns(session_rows, current_turn_index, max_seed_turns):
    current_turn_index = _to_int(current_turn_index, default=0)
    previous_rows = [
        row
        for row in (session_rows or [])
        if _to_int(row.get("turn_index"), default=0) < current_turn_index
    ]
    previous_rows = previous_rows[-max_seed_turns:]
    return [
        {
            "turn_index": row.get("turn_index"),
            "user": row.get("user_text"),
            "reply": row.get("assistant_reply"),
            "input_mode": row.get("input_mode"),
        }
        for row in previous_rows
    ]


def _memory_excerpt(annotation_record, web_log_record):
    memory = (
        annotation_record.get("memory_snapshot")
        or (web_log_record or {}).get("memory_snapshot")
        or {}
    )
    if not isinstance(memory, dict):
        return {}

    excerpt = {}
    for key in (
        "profile_summary",
        "short_term_summary",
        "working_memory_summary",
        "profile",
        "recent_dialogue",
        "wisdom",
    ):
        value = memory.get(key)
        if value:
            excerpt[key] = _collapse_text(value, limit=220)

    working_memory_items = memory.get("working_memory_items") or []
    if working_memory_items:
        excerpt["working_memory_items"] = working_memory_items[:3]

    recent_turns = memory.get("recent_turns") or []
    if recent_turns:
        excerpt["recent_turns"] = recent_turns[-3:]

    return excerpt


def _active_proxy_flags(record):
    return sorted(
        name
        for name, enabled in (record.get("proxy_flags") or {}).items()
        if enabled
    )


def _unique_keep_order(values):
    output = []
    seen = set()
    for value in values:
        key = str(value)
        if not key or key in seen:
            continue
        seen.add(key)
        output.append(value)
    return output


def _regression_targets(record, failure_type_proxies):
    failure_types = list(record.get("failure_types") or [])
    selected_plan = record.get("selected_plan") or {}
    post_check = selected_plan.get("post_check") or record.get("post_check") or {}
    targets = []
    trace_proxies = []

    for failure_type in failure_types:
        targets.extend(FAILURE_TARGETS.get(failure_type, []))
        trace_proxies.extend(failure_type_proxies.get(failure_type, []))

    focus_anchor = str(selected_plan.get("focus_anchor") or "").strip()
    if focus_anchor:
        targets.append(f"cover_focus_anchor:{focus_anchor}")

    reply_obligation = str(selected_plan.get("reply_obligation") or "").strip()
    if reply_obligation:
        targets.append(f"fulfill_reply_obligation:{reply_obligation}")

    if post_check.get("memory_use_expected") or "GHOST_MEMORY" in failure_types:
        targets.append("use_memory_explicitly_when_relevance_is_high")

    if not post_check.get("did_reply_cover_focus"):
        targets.append("do_not_ignore_the_user_focus")
    if not post_check.get("did_reply_follow_obligation"):
        targets.append("do_not_drop_the_reply_obligation")

    return _unique_keep_order(targets), _unique_keep_order(trace_proxies)


def _make_case(case_id, annotation_record, web_log_record, session_rows, taxonomy_meta, max_seed_turns):
    selected_plan = annotation_record.get("selected_plan") or {}
    planner_debug = annotation_record.get("planner_debug") or {}
    logic = annotation_record.get("logic") or {}
    cognition_trace = annotation_record.get("cognition_trace") or {}
    route_info = cognition_trace.get("route_info") or {}
    regression_targets, expected_trace_proxies = _regression_targets(
        annotation_record,
        taxonomy_meta["proxies"],
    )

    failure_types = list(annotation_record.get("failure_types") or [])
    failure_labels = [taxonomy_meta["labels"].get(code) for code in failure_types if taxonomy_meta["labels"].get(code)]
    seed_turns = _build_seed_turns(
        session_rows,
        annotation_record.get("turn_index"),
        max_seed_turns=max_seed_turns,
    )
    input_mode = annotation_record.get("input_mode") or (web_log_record or {}).get("input_mode")

    return {
        "id": case_id,
        "category": "human_feedback_regression",
        "language": _guess_language(annotation_record.get("user_text")),
        "prompt": annotation_record.get("user_text") or "",
        "observed_reply": annotation_record.get("assistant_reply") or "",
        "observed_response_mode": logic.get("response_mode"),
        "observed_intent": planner_debug.get("intent") or logic.get("intent"),
        "human_verdict": annotation_record.get("verdict"),
        "severity": annotation_record.get("severity"),
        "failure_types": failure_types,
        "failure_labels_zh": failure_labels,
        "notes": annotation_record.get("notes") or "",
        "regression_targets": regression_targets,
        "expected_trace_proxies": expected_trace_proxies,
        "expected_route": route_info.get("route"),
        "focus_anchor": selected_plan.get("focus_anchor"),
        "reply_obligation": selected_plan.get("reply_obligation"),
        "proxy_flags": _active_proxy_flags(annotation_record),
        "seed_turns": seed_turns,
        "replay_context": {
            "annotation_timestamp": annotation_record.get("timestamp"),
            "conversation_timestamp": (web_log_record or {}).get("timestamp"),
            "session_id": annotation_record.get("session_id"),
            "turn_index": annotation_record.get("turn_index"),
            "input_mode": input_mode,
            "joined_web_log": bool(web_log_record),
            "memory_excerpt": _memory_excerpt(annotation_record, web_log_record),
        },
        "source": {
            "annotation_path": HUMAN_FEEDBACK_ANNOTATIONS_JSONL_PATH,
            "web_log_path": WEB_CONVERSATION_LOG_JSONL_PATH if web_log_record else None,
        },
    }


def build_dataset(
    annotation_records,
    schema,
    web_log_records,
    include_pass=False,
    max_seed_turns=4,
    invalid_annotation_count=0,
):
    taxonomy_meta = _taxonomy_maps(schema)
    deduped_annotations = _dedupe_latest_annotations(annotation_records)
    if not include_pass:
        selected_annotations = [
            record for record in deduped_annotations if str(record.get("verdict") or "") in FAIL_LIKE_VERDICTS
        ]
    else:
        selected_annotations = list(deduped_annotations)

    web_log_by_turn, web_log_by_session = _index_web_logs(web_log_records)

    dataset = []
    joined_web_log_count = 0
    with_seed_turns_count = 0
    with_notes_count = 0
    for index, annotation_record in enumerate(selected_annotations, 1):
        key = _make_turn_key(annotation_record)
        web_log_record = web_log_by_turn.get(key)
        if web_log_record:
            joined_web_log_count += 1
        session_rows = web_log_by_session.get(str(annotation_record.get("session_id") or "").strip(), [])
        case = _make_case(
            index,
            annotation_record,
            web_log_record,
            session_rows,
            taxonomy_meta=taxonomy_meta,
            max_seed_turns=max_seed_turns,
        )
        if case.get("seed_turns"):
            with_seed_turns_count += 1
        if case.get("notes"):
            with_notes_count += 1
        dataset.append(case)

    report = build_report(
        dataset=dataset,
        annotation_records=annotation_records,
        deduped_annotations=deduped_annotations,
        taxonomy_meta=taxonomy_meta,
        include_pass=include_pass,
        joined_web_log_count=joined_web_log_count,
        with_seed_turns_count=with_seed_turns_count,
        with_notes_count=with_notes_count,
        invalid_annotation_count=invalid_annotation_count,
        invalid_annotation_reason_breakdown=[],
    )
    return dataset, report


def build_report(
    dataset,
    annotation_records,
    deduped_annotations,
    taxonomy_meta,
    include_pass,
    joined_web_log_count,
    with_seed_turns_count,
    with_notes_count,
    invalid_annotation_count=0,
    invalid_annotation_reason_breakdown=None,
):
    severity_counter = Counter()
    language_counter = Counter()
    failure_counter = Counter()
    route_counter = Counter()
    input_mode_counter = Counter()

    for case in dataset:
        severity_counter[str(case.get("severity") or "unknown")] += 1
        language_counter[str(case.get("language") or "unknown")] += 1
        route_counter[str(case.get("expected_route") or "unknown")] += 1
        input_mode_counter[str((case.get("replay_context") or {}).get("input_mode") or "unknown")] += 1
        for failure_type in case.get("failure_types") or []:
            failure_counter[failure_type] += 1

    report = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "summary": {
            "annotation_count_raw": len(annotation_records) + int(invalid_annotation_count or 0),
            "invalid_annotation_count": int(invalid_annotation_count or 0),
            "invalid_annotation_reason_breakdown": list(invalid_annotation_reason_breakdown or []),
            "valid_annotation_count": len(annotation_records),
            "annotation_count_latest_per_turn": len(deduped_annotations),
            "fail_like_annotation_count_latest": sum(
                1 for record in deduped_annotations if str(record.get("verdict") or "") in FAIL_LIKE_VERDICTS
            ),
            "regression_case_count": len(dataset),
            "include_pass": bool(include_pass),
            "joined_web_log_count": joined_web_log_count,
            "joined_web_log_rate": _safe_rate(joined_web_log_count, len(dataset)),
            "with_seed_turns_count": with_seed_turns_count,
            "with_seed_turns_rate": _safe_rate(with_seed_turns_count, len(dataset)),
            "with_notes_count": with_notes_count,
            "with_notes_rate": _safe_rate(with_notes_count, len(dataset)),
            "taxonomy_version": _load_json(FAILURE_TAXONOMY_SCHEMA_PATH).get("version") or "unknown",
            "annotation_source_path": HUMAN_FEEDBACK_ANNOTATIONS_JSONL_PATH,
            "web_log_source_path": WEB_CONVERSATION_LOG_JSONL_PATH,
        },
        "breakdowns": {
            "severity": [
                {
                    "value": key,
                    "count": severity_counter.get(key, 0),
                    "rate": _safe_rate(severity_counter.get(key, 0), len(dataset)),
                }
                for key in ("high", "medium", "low", "unknown")
                if key in severity_counter or key != "unknown"
            ],
            "language": [
                {
                    "value": key,
                    "count": count,
                    "rate": _safe_rate(count, len(dataset)),
                }
                for key, count in sorted(language_counter.items(), key=lambda item: (-item[1], str(item[0])))
            ],
            "failure_types": [
                {
                    "code": code,
                    "label_zh": taxonomy_meta["labels"].get(code),
                    "count": failure_counter.get(code, 0),
                    "rate": _safe_rate(failure_counter.get(code, 0), len(dataset)),
                }
                for code in taxonomy_meta["codes"]
            ],
            "expected_route": [
                {
                    "value": key,
                    "count": count,
                    "rate": _safe_rate(count, len(dataset)),
                }
                for key, count in sorted(route_counter.items(), key=lambda item: (-item[1], str(item[0])))
            ],
            "input_mode": [
                {
                    "value": key,
                    "count": count,
                    "rate": _safe_rate(count, len(dataset)),
                }
                for key, count in sorted(input_mode_counter.items(), key=lambda item: (-item[1], str(item[0])))
            ],
        },
        "samples": [
            {
                "id": case.get("id"),
                "prompt": _collapse_text(case.get("prompt"), limit=80),
                "observed_reply": _collapse_text(case.get("observed_reply"), limit=80),
                "failure_types": case.get("failure_types") or [],
                "notes": _collapse_text(case.get("notes"), limit=120),
            }
            for case in dataset[:10]
        ],
    }
    return report


def build_markdown(report):
    summary = report.get("summary") or {}
    breakdowns = report.get("breakdowns") or {}
    lines = [
        "# Human Feedback Regression Dataset Report",
        "",
        f"- generated_at: {report.get('generated_at')}",
        f"- annotation_source_path: `{summary.get('annotation_source_path')}`",
        f"- web_log_source_path: `{summary.get('web_log_source_path')}`",
        "",
        "## Summary",
        "",
        f"- annotation_count_raw: {summary.get('annotation_count_raw', 0)}",
        f"- invalid_annotation_count: {summary.get('invalid_annotation_count', 0)}",
        f"- valid_annotation_count: {summary.get('valid_annotation_count', 0)}",
        f"- annotation_count_latest_per_turn: {summary.get('annotation_count_latest_per_turn', 0)}",
        f"- fail_like_annotation_count_latest: {summary.get('fail_like_annotation_count_latest', 0)}",
        f"- regression_case_count: {summary.get('regression_case_count', 0)}",
        f"- include_pass: {summary.get('include_pass', False)}",
        f"- joined_web_log_count: {summary.get('joined_web_log_count', 0)}",
        f"- joined_web_log_rate: {summary.get('joined_web_log_rate', 0.0)}",
        f"- with_seed_turns_count: {summary.get('with_seed_turns_count', 0)}",
        f"- with_seed_turns_rate: {summary.get('with_seed_turns_rate', 0.0)}",
        f"- with_notes_count: {summary.get('with_notes_count', 0)}",
        f"- with_notes_rate: {summary.get('with_notes_rate', 0.0)}",
        "",
        "## Failure Type Breakdown",
        "",
    ]
    for row in breakdowns.get("failure_types") or []:
        lines.append(f"- {row.get('code')} ({row.get('label_zh')}): count={row.get('count')} rate={row.get('rate')}")

    lines.extend(["", "## Invalid Annotation Breakdown", ""])
    invalid_reason_rows = summary.get("invalid_annotation_reason_breakdown") or []
    if not invalid_reason_rows:
        lines.append("- none")
    for row in invalid_reason_rows:
        lines.append(f"- {row.get('reason')}: count={row.get('count')}")

    lines.extend(["", "## Severity Breakdown", ""])
    for row in breakdowns.get("severity") or []:
        lines.append(f"- {row.get('value')}: count={row.get('count')} rate={row.get('rate')}")

    lines.extend(["", "## Language Breakdown", ""])
    for row in breakdowns.get("language") or []:
        lines.append(f"- {row.get('value')}: count={row.get('count')} rate={row.get('rate')}")
    if not (breakdowns.get("language") or []):
        lines.append("- none")

    lines.extend(["", "## Route Breakdown", ""])
    for row in breakdowns.get("expected_route") or []:
        lines.append(f"- {row.get('value')}: count={row.get('count')} rate={row.get('rate')}")
    if not (breakdowns.get("expected_route") or []):
        lines.append("- none")

    lines.extend(["", "## Sample Cases", ""])
    for row in report.get("samples") or []:
        lines.append(
            f"- id={row.get('id')} failure={row.get('failure_types')} prompt={row.get('prompt')} reply={row.get('observed_reply')}"
        )
        if row.get("notes"):
            lines.append(f"  - notes: {row.get('notes')}")
    if not (report.get("samples") or []):
        lines.append("- none")

    return "\n".join(lines) + "\n"


def parse_args():
    parser = argparse.ArgumentParser(description="Build regression dataset from human feedback annotations.")
    parser.add_argument("--input", default=HUMAN_FEEDBACK_ANNOTATIONS_JSONL_PATH)
    parser.add_argument("--web-log", default=WEB_CONVERSATION_LOG_JSONL_PATH)
    parser.add_argument("--out-dataset", default=HUMAN_FEEDBACK_REGRESSION_DATASET_PATH)
    parser.add_argument("--out-report-json", default=HUMAN_FEEDBACK_REGRESSION_REPORT_JSON_PATH)
    parser.add_argument("--out-report-md", default=HUMAN_FEEDBACK_REGRESSION_REPORT_MD_PATH)
    parser.add_argument("--include-pass", action="store_true")
    parser.add_argument("--max-seed-turns", type=int, default=4)
    return parser.parse_args()


def main():
    args = parse_args()
    schema = _load_json(FAILURE_TAXONOMY_SCHEMA_PATH)
    raw_annotation_records = _load_jsonl(args.input)
    taxonomy_meta = _taxonomy_maps(schema)
    annotation_records, invalid_records = split_valid_annotations(
        raw_annotation_records,
        valid_failure_types=taxonomy_meta["codes"],
    )
    web_log_records = _load_jsonl(args.web_log)
    dataset, report = build_dataset(
        annotation_records=annotation_records,
        schema=schema,
        web_log_records=web_log_records,
        include_pass=args.include_pass,
        max_seed_turns=max(0, int(args.max_seed_turns)),
        invalid_annotation_count=len(invalid_records),
    )
    report["summary"]["invalid_annotation_reason_breakdown"] = invalid_reason_counts(invalid_records)

    with open(args.out_dataset, "w", encoding="utf-8") as f:
        json.dump(dataset, f, ensure_ascii=False, indent=2)
    with open(args.out_report_json, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    with open(args.out_report_md, "w", encoding="utf-8") as f:
        f.write(build_markdown(report))

    print(args.out_dataset)
    print(args.out_report_json)
    print(args.out_report_md)
    print(json.dumps(report.get("summary") or {}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
