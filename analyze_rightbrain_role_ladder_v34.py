#!/usr/bin/env python3
"""Analyze the V34 development pilot without turning it into confirmation evidence."""

import argparse
import json
import math
import statistics
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "rightbrain_role_specialization_v34_preregistration.json"
DEFAULT_RAW = ROOT / "reports" / "rightbrain_role_ladder_v34_pilot_raw.json"
DEFAULT_JSON = ROOT / "reports" / "rightbrain_role_ladder_v34_pilot_analysis.json"
DEFAULT_MD = ROOT / "reports" / "rightbrain_role_ladder_v34_pilot_analysis.md"


def _rate(numerator, denominator):
    return round(numerator / denominator, 4) if denominator else None


def _percentile(values, quantile):
    values = sorted(float(value) for value in values)
    if not values:
        return None
    index = max(0, min(len(values) - 1, math.ceil(quantile * len(values)) - 1))
    return round(values[index], 4)


def _fmt_pct(value):
    return "n/a" if value is None else f"{100 * value:.1f}%"


def _summarize(rows, frozen):
    semantic_hits = sum(
        group["hit"] for row in rows for group in row["score"]["semantic_groups"]
    )
    semantic_groups = sum(
        len(row["score"]["semantic_groups"]) for row in rows
    )
    reason_counts = Counter(
        reason for row in rows for reason in row["score"]["current_gate_rejection_reasons"]
    )
    by_case = defaultdict(list)
    for row in rows:
        by_case[row["case_id"]].append(row["score"]["normalized_reply"])
    duplicate_count = sum(len(replies) - len(set(replies)) for replies in by_case.values())
    wall = [row["response_metrics"]["wall_seconds"] for row in rows]
    return {
        "row_count": len(rows),
        "case_count": len(by_case),
        "semantic_contract_pass_rate": _rate(
            sum(row["score"]["semantic_contract_pass"] for row in rows), len(rows)
        ),
        "semantic_group_recall": _rate(semantic_hits, semantic_groups),
        "raw_surface_gate_pass_rate": _rate(
            sum(row["score"]["current_gate_raw_pass"] for row in rows), len(rows)
        ),
        "hard_surface_failure_rate": _rate(
            sum(row["score"]["hard_surface_failure"] for row in rows), len(rows)
        ),
        "polite_or_service_register_rate": _rate(
            sum(row["score"]["polite_or_service_register"] for row in rows), len(rows)
        ),
        "private_memory_intrusion_count": sum(
            row["score"]["private_memory_intrusion"] for row in rows
        ),
        "over_max_chars_rate": _rate(reason_counts["over_max_chars"], len(rows)),
        "within_case_exact_duplicate_rate": _rate(duplicate_count, len(rows)),
        "warm_generation_median_seconds": (
            round(statistics.median(wall), 4) if wall else None
        ),
        "warm_generation_p95_seconds": _percentile(wall, 0.95),
        "median_character_count": (
            round(statistics.median(row["score"]["character_count"] for row in rows), 2)
            if rows
            else None
        ),
        "rejection_reason_counts": dict(reason_counts),
        "blob_bytes": frozen["blob_bytes"],
        "reported_parameter_size": frozen["reported_parameter_size"],
        "quantization": frozen["quantization"],
    }


def _gate_result(summary, gate):
    checks = {
        "semantic_contract_pass_rate": summary["semantic_contract_pass_rate"]
        >= gate["semantic_contract_pass_rate_at_least"],
        "semantic_group_recall": summary["semantic_group_recall"]
        >= gate["semantic_group_recall_at_least"],
        "raw_surface_gate_pass_rate": summary["raw_surface_gate_pass_rate"]
        >= gate["raw_surface_gate_pass_rate_at_least"],
        "hard_surface_failure_rate": summary["hard_surface_failure_rate"]
        <= gate["hard_surface_failure_rate_at_most"],
        "polite_or_service_register_rate": summary["polite_or_service_register_rate"]
        <= gate["polite_or_service_register_rate_at_most"],
        "private_memory_intrusion_count": summary["private_memory_intrusion_count"]
        == gate["private_memory_intrusion_count"],
        "warm_generation_median_seconds": summary["warm_generation_median_seconds"]
        <= gate["warm_generation_median_seconds_at_most"],
    }
    return {
        "eligible": all(checks.values()),
        "checks": checks,
        "failed_checks": [name for name, passed in checks.items() if not passed],
    }


def analyze(raw_path=DEFAULT_RAW):
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    raw = json.loads(Path(raw_path).read_text(encoding="utf-8"))
    conditions = config["development_pilot"]["conditions"]
    gate = config["development_pilot"]["finalist_gate"]
    expected = len(config["development_pilot"]["case_ids"]) * len(
        config["development_pilot"]["generation"]["seeds"]
    )
    summaries = {}
    for condition, frozen in conditions.items():
        rows = [row for row in raw["rows"] if row["condition"] == condition]
        if len(rows) != expected:
            raise ValueError(f"Incomplete V34 pilot condition {condition}: {len(rows)}/{expected}")
        summary = _summarize(rows, frozen)
        summary["gate"] = _gate_result(summary, gate)
        summaries[condition] = summary

    eligible = [
        condition for condition, summary in summaries.items() if summary["gate"]["eligible"]
    ]
    eligible.sort(key=lambda condition: conditions[condition]["blob_bytes"])
    selected = eligible[0] if eligible else None
    return {
        "schema": "uruha_rightbrain_role_ladder_pilot_analysis_v34",
        "evidence_status": "development_only_not_formal_confirmation",
        "source_raw_report": str(Path(raw_path).relative_to(ROOT)),
        "complete": raw.get("completed_at") is not None,
        "condition_summaries": summaries,
        "eligible_finalists": eligible,
        "smallest_eligible_deployment_candidate": selected,
        "decision": (
            "author_fresh_confirmation_holdout_for_all_eligible_finalists"
            if eligible
            else "no_model_is_authorized_for_confirmation_or_runtime_change"
        ),
        "interpretation": (
            "The pilot may choose which models deserve a fresh confirmation test. It cannot authorize a runtime change, persona training, or a human-likeness claim."
        ),
    }


def _markdown(report):
    lines = [
        "# V34 RightBrain model ladder development pilot",
        "",
        "> This is development evidence. It selects confirmation candidates but cannot change runtime.",
        "",
        "| condition | semantic contract | semantic groups | raw gate | hard failure | polite drift | p50 latency | eligible |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for condition, summary in report["condition_summaries"].items():
        lines.append(
            "| "
            + " | ".join(
                [
                    condition,
                    _fmt_pct(summary["semantic_contract_pass_rate"]),
                    _fmt_pct(summary["semantic_group_recall"]),
                    _fmt_pct(summary["raw_surface_gate_pass_rate"]),
                    _fmt_pct(summary["hard_surface_failure_rate"]),
                    _fmt_pct(summary["polite_or_service_register_rate"]),
                    f"{summary['warm_generation_median_seconds']:.2f}s",
                    "yes" if summary["gate"]["eligible"] else "no",
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Decision",
            "",
            f"- `{report['decision']}`",
            f"- Smallest eligible candidate: `{report['smallest_eligible_deployment_candidate']}`",
            "",
            "## Failed gates",
            "",
        ]
    )
    for condition, summary in report["condition_summaries"].items():
        failures = ", ".join(summary["gate"]["failed_checks"]) or "none"
        lines.append(f"- `{condition}`: {failures}")
    lines.extend(["", report["interpretation"], ""])
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", type=Path, default=DEFAULT_RAW)
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown-output", type=Path, default=DEFAULT_MD)
    args = parser.parse_args()
    report = analyze(args.raw)
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    args.markdown_output.write_text(_markdown(report), encoding="utf-8")
    print(json.dumps({"decision": report["decision"], "output": str(args.json_output)}, indent=2))


if __name__ == "__main__":
    main()
