#!/usr/bin/env python3
"""Analyze the frozen reflection pilot without modifying its thresholds."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from reflection_causal_pilot_v1_core import score_rows, summarize
from run_reflection_causal_pilot_v1 import (
    CONFIG_PATH,
    DATASET_PATH,
    DEFAULT_OUTPUT,
    LOCK_PATH,
    ROOT,
    load_json,
    sha256,
)


DEFAULT_JSON = ROOT / "reports" / "reflection_causal_pilot_v1_analysis.json"
DEFAULT_MD = ROOT / "reports" / "reflection_causal_pilot_v1_analysis.md"
TZ = ZoneInfo("Asia/Tokyo")


def validate_raw(raw):
    expected = {
        "preregistration_sha256": sha256(CONFIG_PATH),
        "harness_lock_sha256": sha256(LOCK_PATH),
        "dataset_sha256": sha256(DATASET_PATH),
    }
    for key, value in expected.items():
        if raw.get(key) != value:
            raise ValueError(f"raw reflection pilot {key} mismatch")


def markdown(report):
    summary = report["summary"]
    lines = [
        "# Reflection Causal Pilot V1",
        "",
        f"- decision: `{report['decision']}`",
        f"- all_gates_pass: `{summary['all_gates_pass']}`",
        "- claim boundary: only the marginal effect of the current reflection path on the 12 frozen paired cases",
        "",
        "## Metrics",
        "",
    ]
    for key in (
        "expected_rule_write_recall",
        "valid_rule_precision",
        "no_rule_specificity",
        "valid_rule_retrieval_rate",
        "control_behavior_success_rate",
        "treatment_behavior_success_rate",
        "treatment_behavior_delta",
        "paired_behavior_gains",
        "paired_behavior_regressions",
        "paired_behavior_net_gain",
        "interaction_category_paired_gains",
    ):
        lines.append(f"- {key}: `{summary[key]}`")
    lines.extend(["", "## Gates", ""])
    for key, passed in summary["gate_checks"].items():
        lines.append(f"- {key}: `{'PASS' if passed else 'FAIL'}`")
    lines.extend(["", "## Cases", ""])
    for row in report["scored_rows"]:
        lines.append(
            f"- `{row['id']}` category={row['category']} write={row['treatment_wrote_rule']} "
            f"valid={row['treatment_rule_valid']} retrieved={row['treatment_retrieved_reflection']} "
            f"control={row['control_behavior_success']} treatment={row['treatment_behavior_success']} "
            f"gain={row['paired_gain']} regression={row['paired_regression']}"
        )
        lines.append(f"  - reflection: {row['reflection_documents']}")
        lines.append(f"  - control: {row['control_reply']}")
        lines.append(f"  - treatment: {row['treatment_reply']}")
    return "\n".join(lines) + "\n"


def analyze(raw_path=DEFAULT_OUTPUT, json_path=DEFAULT_JSON, md_path=DEFAULT_MD):
    raw = load_json(raw_path)
    config = load_json(CONFIG_PATH)
    validate_raw(raw)
    scored = score_rows(raw["rows"])
    summary = summarize(scored, config["success_gates"])
    decision = (
        config["decision_rule"]["all_gates_pass"]
        if summary["all_gates_pass"]
        else config["decision_rule"]["any_gate_fails"]
    )
    report = {
        "schema": "uruha_reflection_causal_pilot_analysis_v1",
        "generated_at": datetime.now(TZ).isoformat(timespec="seconds"),
        "raw_report": str(raw_path.relative_to(ROOT)),
        "runner_commit": raw["runner_commit"],
        "model_snapshot": raw["model_snapshot"],
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
    print(json.dumps({"decision": decision, "summary": summary}, ensure_ascii=False, indent=2))
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
