#!/usr/bin/env python3
"""Analyze the frozen typed-reflection V3 development pilot."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from run_typed_reflection_v3_development import (
    CONFIG_PATH,
    CONTROL,
    DATASET_PATH,
    DEFAULT_OUTPUT,
    LOCK_PATH,
    ROOT,
    TREATMENT,
    load_json,
    sha256,
)
from typed_reflection_v3_core import decision_for, score_rows, summarize


DEFAULT_JSON = ROOT / "reports" / "typed_reflection_v3_development_analysis.json"
DEFAULT_MD = ROOT / "reports" / "typed_reflection_v3_development_analysis.md"
TZ = ZoneInfo("Asia/Tokyo")


def validate_raw(raw):
    expected = {
        "preregistration_sha256": sha256(CONFIG_PATH),
        "harness_lock_sha256": sha256(LOCK_PATH),
        "dataset_sha256": sha256(DATASET_PATH),
    }
    for key, value in expected.items():
        if raw.get(key) != value:
            raise ValueError(f"raw typed-reflection pilot {key} mismatch")


def markdown(report):
    summary = report["summary"]
    lines = [
        "# Typed Reflection V3 Development Pilot",
        "",
        f"- decision: `{report['decision']}`",
        f"- all_gates_pass: `{summary['all_gates_pass']}`",
        "- boundary: controlled development cases, not an independent holdout or broad human-likeness result",
        "",
        "## Metrics",
        "",
    ]
    for key in (
        "reflection_type_accuracy",
        "valid_rule_precision",
        "expected_rule_write_recall",
        "no_rule_specificity",
        "collection_routing_accuracy",
        "source_provenance_rate",
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
            f"- `{row['id']}` expected={row['expected_reflection_type']} "
            f"observed={row['reflection_type_observed']} valid={row['treatment_reflection_valid']} "
            f"retrieved={row['treatment_retrieved_reflection']} "
            f"control={row['control_behavior_success']} treatment={row['treatment_behavior_success']} "
            f"gain={row['paired_gain']} regression={row['paired_regression']}"
        )
        lines.append(f"  - control: {row['control_reply']}")
        lines.append(f"  - treatment: {row['treatment_reply']}")
        lines.append(f"  - reflections: {row['reflection_records']}")
    return "\n".join(lines) + "\n"


def analyze(raw_path=DEFAULT_OUTPUT, json_path=DEFAULT_JSON, md_path=DEFAULT_MD):
    raw = load_json(raw_path)
    config = load_json(CONFIG_PATH)
    validate_raw(raw)
    scored = score_rows(raw["rows"], CONTROL, TREATMENT)
    summary = summarize(scored, config["success_gates"])
    decision = decision_for(summary, config["decision_rule"])
    report = {
        "schema": "uruha_typed_reflection_development_analysis_v3",
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
