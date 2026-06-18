import argparse
import json
import os
from datetime import datetime

from human_feedback_validation import invalid_reason_counts, split_valid_annotations
from project_paths import (
    FAILURE_TAXONOMY_SCHEMA_PATH,
    HUMAN_FEEDBACK_ANNOTATION_CLEANUP_REPORT_JSON_PATH,
    HUMAN_FEEDBACK_ANNOTATION_CLEANUP_REPORT_MD_PATH,
    HUMAN_FEEDBACK_ANNOTATIONS_JSONL_PATH,
    HUMAN_FEEDBACK_INVALID_ANNOTATION_ARCHIVE_DIR,
)


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
                rows.append({"__invalid_json_line__": line})
    return rows


def _write_jsonl(path, records):
    with open(path, "w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


def _valid_failure_codes(schema):
    return {
        item.get("code")
        for item in (schema.get("failure_types") or [])
        if item.get("code")
    }


def build_cleanup_report(input_path, valid_records, invalid_records, archive_path=None, applied=False):
    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "input_path": input_path,
        "archive_path": archive_path,
        "applied": bool(applied),
        "summary": {
            "raw_record_count": len(valid_records) + len(invalid_records),
            "valid_record_count": len(valid_records),
            "invalid_record_count": len(invalid_records),
            "invalid_reason_breakdown": invalid_reason_counts(invalid_records),
        },
    }


def build_markdown(report):
    summary = report.get("summary") or {}
    lines = [
        "# Human Feedback Annotation Cleanup Report",
        "",
        f"- generated_at: {report.get('generated_at')}",
        f"- input_path: `{report.get('input_path')}`",
        f"- archive_path: `{report.get('archive_path') or '-'}`",
        f"- applied: `{report.get('applied')}`",
        "",
        "## Summary",
        "",
        f"- raw_record_count: {summary.get('raw_record_count', 0)}",
        f"- valid_record_count: {summary.get('valid_record_count', 0)}",
        f"- invalid_record_count: {summary.get('invalid_record_count', 0)}",
        "",
        "## Invalid Reason Breakdown",
        "",
    ]
    rows = summary.get("invalid_reason_breakdown") or []
    if not rows:
        lines.append("- none")
    for row in rows:
        lines.append(f"- {row.get('reason')}: count={row.get('count')}")
    return "\n".join(lines) + "\n"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Archive invalid human-feedback annotations and optionally rewrite the main JSONL with valid rows only."
    )
    parser.add_argument("--input", default=HUMAN_FEEDBACK_ANNOTATIONS_JSONL_PATH)
    parser.add_argument("--apply", action="store_true", help="Rewrite input file and archive invalid rows.")
    parser.add_argument("--out-json", default=HUMAN_FEEDBACK_ANNOTATION_CLEANUP_REPORT_JSON_PATH)
    parser.add_argument("--out-md", default=HUMAN_FEEDBACK_ANNOTATION_CLEANUP_REPORT_MD_PATH)
    return parser.parse_args()


def main():
    args = parse_args()
    schema = _load_json(FAILURE_TAXONOMY_SCHEMA_PATH)
    records = _load_jsonl(args.input)
    valid_records, invalid_records = split_valid_annotations(
        records,
        valid_failure_types=_valid_failure_codes(schema),
    )

    archive_path = None
    if args.apply and invalid_records:
        os.makedirs(HUMAN_FEEDBACK_INVALID_ANNOTATION_ARCHIVE_DIR, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_path = os.path.join(
            HUMAN_FEEDBACK_INVALID_ANNOTATION_ARCHIVE_DIR,
            f"invalid_annotations_{stamp}.jsonl",
        )
        _write_jsonl(
            archive_path,
            [
                {
                    "reason": item.get("reason"),
                    "record": item.get("record"),
                }
                for item in invalid_records
            ],
        )
        _write_jsonl(args.input, valid_records)

    report = build_cleanup_report(
        input_path=args.input,
        valid_records=valid_records,
        invalid_records=invalid_records,
        archive_path=archive_path,
        applied=args.apply,
    )

    with open(args.out_json, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    with open(args.out_md, "w", encoding="utf-8") as f:
        f.write(build_markdown(report))

    print(args.out_json)
    print(args.out_md)
    print(json.dumps(report.get("summary") or {}, ensure_ascii=False, indent=2))
    if archive_path:
        print(archive_path)


if __name__ == "__main__":
    main()
