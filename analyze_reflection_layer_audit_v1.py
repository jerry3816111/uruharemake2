#!/usr/bin/env python3
"""Analyze the frozen reflection-layer atomic judge calibration."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from reflection_layer_audit_v1 import score_rows, summarize
from run_reflection_layer_audit_v1 import (
    CONFIG_PATH,
    DATASET_PATH,
    DEFAULT_OUTPUT,
    LOCK_PATH,
    ROOT,
    load_json,
    sha256,
)


DEFAULT_JSON = ROOT / "reports" / "reflection_layer_audit_v1_analysis.json"
DEFAULT_MD = ROOT / "reports" / "reflection_layer_audit_v1_analysis.md"
TZ = ZoneInfo("Asia/Tokyo")


def validate_raw(raw):
    for key, path in (
        ("preregistration_sha256", CONFIG_PATH),
        ("dataset_sha256", DATASET_PATH),
        ("harness_lock_sha256", LOCK_PATH),
    ):
        if raw.get(key) != sha256(path):
            raise ValueError(f"raw reflection audit {key} mismatch")


def markdown(report):
    summary = report["summary"]
    lines = [
        "# Reflection Layer Audit V1 Calibration",
        "",
        f"- decision: `{report['decision']}`",
        f"- all_gates_pass: `{summary['all_gates_pass']}`",
        "- boundary: authored calibration only; not runtime or independent evidence",
        "",
        "## Metrics",
        "",
    ]
    for key, value in summary.items():
        if key != "gate_checks":
            lines.append(f"- {key}: `{value}`")
    lines.extend(["", "## Gates", ""])
    for key, passed in summary["gate_checks"].items():
        lines.append(f"- {key}: `{'PASS' if passed else 'FAIL'}`")
    lines.extend(["", "## Cases", ""])
    for row in report["scored_rows"]:
        lines.append(
            f"- `{row['id']}` expected={row['expected_accept']} "
            f"observed={row['observed_accept']} surface={row['surface_report']['clean']}"
        )
        for claim in row["claims"]:
            lines.append(
                f"  - `{claim['id']}` gold={claim['gold_relation']} "
                f"observed={claim['observed_relation']} correct={claim['correct']}"
            )
    return "\n".join(lines) + "\n"


def analyze(raw_path=DEFAULT_OUTPUT, json_path=DEFAULT_JSON, md_path=DEFAULT_MD):
    raw = load_json(raw_path)
    config = load_json(CONFIG_PATH)
    validate_raw(raw)
    scored = score_rows(raw["rows"])
    summary = summarize(scored, config, raw["model_call_count"])
    decision = (
        config["decision_rule"]["all_gates_pass"]
        if summary["all_gates_pass"]
        else config["decision_rule"]["any_gate_fails"]
    )
    report = {
        "schema": "uruha_reflection_layer_audit_analysis_v1",
        "generated_at": datetime.now(TZ).isoformat(timespec="seconds"),
        "raw_report": str(raw_path.relative_to(ROOT)),
        "runner_commit": raw["runner_commit"],
        "judge_snapshot": raw["judge_snapshot"],
        "summary": summary,
        "decision": decision,
        "evidence_boundary": config["claim_boundary"],
        "scored_rows": scored,
    }
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    md_path.write_text(markdown(report), encoding="utf-8")
    print(json.dumps({"decision": decision, "summary": summary}, indent=2))
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MD)
    args = parser.parse_args()
    analyze(args.raw, args.json, args.markdown)


if __name__ == "__main__":
    main()
