#!/usr/bin/env python3
"""Compare the post-fix diagnostic replay with the frozen V1 result."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from reflection_causal_pilot_v1_core import score_rows, summarize
from run_reflection_causal_pilot_v1 import load_json, sha256
from run_reflection_causal_replay_v2 import (
    CONFIG_PATH,
    DATASET_PATH,
    DEFAULT_OUTPUT,
    LOCK_PATH,
    ROOT,
)


V1_ANALYSIS = ROOT / "reports" / "reflection_causal_pilot_v1_analysis.json"
DEFAULT_JSON = ROOT / "reports" / "reflection_causal_replay_v2_analysis.json"
DEFAULT_MD = ROOT / "reports" / "reflection_causal_replay_v2_analysis.md"
TZ = ZoneInfo("Asia/Tokyo")


def validate_raw(raw):
    expected = {
        "preregistration_sha256": sha256(CONFIG_PATH),
        "harness_lock_sha256": sha256(LOCK_PATH),
        "dataset_sha256": sha256(DATASET_PATH),
    }
    for key, value in expected.items():
        if raw.get(key) != value:
            raise ValueError(f"V2 reflection replay {key} mismatch")
    if raw.get("dataset_reuse_status") != "exact_seen_v1_replay_not_an_independent_holdout":
        raise ValueError("V2 reflection replay is missing its seen-case boundary")


def delta(current, baseline, key):
    return round(float(current[key]) - float(baseline[key]), 4)


def markdown(report):
    current = report["summary"]
    comparison = report["comparison_to_v1"]
    lines = [
        "# Reflection Causal Replay V2",
        "",
        f"- decision: `{report['decision']}`",
        "- evidence: exact seen V1 replay, not an independent holdout",
        "",
        "## V1 -> V2",
        "",
    ]
    for key in (
        "valid_rule_retrieval_rate",
        "control_behavior_success_rate",
        "treatment_behavior_success_rate",
        "treatment_behavior_delta",
        "paired_behavior_gains",
        "paired_behavior_regressions",
        "paired_behavior_net_gain",
    ):
        row = comparison[key]
        lines.append(f"- {key}: `{row['v1']}` -> `{row['v2']}` (delta `{row['delta']}`)")
    lines.extend(["", "## V2 Gates", ""])
    for key, passed in current["gate_checks"].items():
        lines.append(f"- {key}: `{'PASS' if passed else 'FAIL'}`")
    lines.extend(["", "## Cases", ""])
    for row in report["scored_rows"]:
        lines.append(
            f"- `{row['id']}` write={row['treatment_wrote_rule']} valid={row['treatment_rule_valid']} "
            f"retrieved={row['treatment_retrieved_reflection']} control={row['control_behavior_success']} "
            f"treatment={row['treatment_behavior_success']} gain={row['paired_gain']} "
            f"regression={row['paired_regression']}"
        )
    return "\n".join(lines) + "\n"


def analyze(raw_path=DEFAULT_OUTPUT, json_path=DEFAULT_JSON, md_path=DEFAULT_MD):
    raw = load_json(raw_path)
    config = load_json(CONFIG_PATH)
    v1 = load_json(V1_ANALYSIS)
    validate_raw(raw)
    scored = score_rows(raw["rows"])
    summary = summarize(scored, config["success_gates"])
    v1_summary = v1["summary"]
    compare_keys = (
        "valid_rule_retrieval_rate",
        "control_behavior_success_rate",
        "treatment_behavior_success_rate",
        "treatment_behavior_delta",
        "paired_behavior_gains",
        "paired_behavior_regressions",
        "paired_behavior_net_gain",
    )
    comparison = {
        key: {
            "v1": v1_summary[key],
            "v2": summary[key],
            "delta": delta(summary, v1_summary, key),
        }
        for key in compare_keys
    }
    channel_pass = summary["valid_rule_retrieval_rate"] >= config["channel_repair_gate"]["valid_rule_retrieval_rate_min"]
    if summary["all_gates_pass"]:
        decision = config["decision_rule"]["all_reflection_gates_pass"]
    elif channel_pass:
        decision = config["decision_rule"]["channel_passes_but_reflection_fails"]
    else:
        decision = config["decision_rule"]["channel_fails"]
    report = {
        "schema": "uruha_reflection_causal_replay_analysis_v2",
        "generated_at": datetime.now(TZ).isoformat(timespec="seconds"),
        "raw_report": str(raw_path.relative_to(ROOT)),
        "runner_commit": raw["runner_commit"],
        "model_snapshot": raw["model_snapshot"],
        "dataset_reuse_status": config["dataset_reuse_status"],
        "summary": summary,
        "comparison_to_v1": comparison,
        "channel_repair_gate_pass": channel_pass,
        "decision": decision,
        "evidence_boundary": config["claim_boundary"],
        "scored_rows": scored,
    }
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(markdown(report), encoding="utf-8")
    print(json.dumps({"decision": decision, "summary": summary, "comparison_to_v1": comparison}, ensure_ascii=False, indent=2))
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
