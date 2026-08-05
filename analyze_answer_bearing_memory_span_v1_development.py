#!/usr/bin/env python3
"""Analyze the preregistered answer-bearing memory span development run."""

import argparse
import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

from answer_bearing_memory_span import anchored_source_span, parse_answer_evidence
from run_answer_bearing_memory_span_v1_development import condition_candidates


ROOT = Path(__file__).resolve().parent
PREREG_PATH = ROOT / "configs/answer_bearing_memory_span_v1_development_preregistration.json"
DEFAULT_RAW = ROOT / "analysis/local_answer_bearing_memory_span_v1_development/raw.jsonl"
DEFAULT_METADATA = ROOT / "analysis/local_answer_bearing_memory_span_v1_development/run_metadata.json"
DEFAULT_JSON = ROOT / "reports/answer_bearing_memory_span_v1_development.json"
DEFAULT_MD = ROOT / "reports/answer_bearing_memory_span_v1_development.md"


def file_sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_jsonl(path):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line]


def rate(numerator, denominator):
    return round(numerator / denominator, 6) if denominator else 0.0


def percentile(values, quantile):
    values = sorted(float(value) for value in values)
    if not values:
        return 0.0
    position = (len(values) - 1) * float(quantile)
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return round(values[lower], 6)
    weight = position - lower
    return round(values[lower] * (1 - weight) + values[upper] * weight, 6)


def expected_row_keys(cases, prereg):
    return {
        (case["case_id"], condition["id"])
        for case in cases
        for condition in prereg["conditions"]
    }


def raw_span_grounding(rows, cases_by_id, conditions_by_id):
    supported_claims = 0
    grounded_claims = 0
    for row in rows:
        payload = parse_answer_evidence(row.get("model_output"))
        if payload is None:
            continue
        case = cases_by_id[row["case_id"]]
        candidates = condition_candidates(case, conditions_by_id[row["condition"]])
        for verdict in payload["verdicts"]:
            if not verdict["supports_answer"]:
                continue
            supported_claims += 1
            index = verdict["source_index"]
            if 0 <= index < len(candidates) and anchored_source_span(
                candidates[index]["text"], verdict["answer_span"]
            ):
                grounded_claims += 1
    return {
        "supported_claim_count": supported_claims,
        "grounded_supported_claim_count": grounded_claims,
        "exact_span_grounding_rate": rate(grounded_claims, supported_claims),
    }


def summarize(rows, prereg, cases, metadata):
    cases_by_id = {case["case_id"]: case for case in cases}
    conditions_by_id = {row["id"]: row for row in prereg["conditions"]}
    expected = expected_row_keys(cases, prereg)
    actual = [(row["case_id"], row["condition"]) for row in rows]
    actual_set = set(actual)
    duplicate_count = len(actual) - len(actual_set)
    parse_count = sum(row["evidence_validation"].get("valid", False) for row in rows)
    span = raw_span_grounding(rows, cases_by_id, conditions_by_id)
    baseline = prereg["baseline_locked_values"]

    by_condition = {}
    for condition in prereg["conditions"]:
        selected = [row for row in rows if row["condition"] == condition["id"]]
        by_condition[condition["id"]] = {
            "count": len(selected),
            "safe_count": sum(row["safe_outcome"] for row in selected),
            "safe_rate": rate(sum(row["safe_outcome"] for row in selected), len(selected)),
            "selected_count": sum(row["selected"] for row in selected),
            "wrong_trace_selection_count": sum(
                row["wrong_trace_selected"] for row in selected
            ),
            "status_counts": dict(Counter(row["status"] for row in selected)),
        }

    wrong_trace_count = sum(row["wrong_trace_selected"] for row in rows)
    target_removed_rows = [
        row for row in rows if row["condition"] == "t1_remove_exact_target"
    ]
    target_removed_selection_count = sum(row["selected"] for row in target_removed_rows)
    transport_error_count = sum(row["transport_error_count"] for row in rows)
    production_write_count = sum(row["production_memory_write_count"] for row in rows)
    physical_action_count = sum(row["physical_vrm_action_count"] for row in rows)
    latencies = [row["latency_seconds"] for row in rows]

    language_rows = defaultdict(list)
    for row in rows:
        language_rows[row["language"]].append(row)
    by_language = {
        language: {
            "decision_count": len(items),
            "safe_rate": rate(sum(row["safe_outcome"] for row in items), len(items)),
            "wrong_trace_selection_count": sum(
                row["wrong_trace_selected"] for row in items
            ),
            "contract_valid_rate": rate(
                sum(row["evidence_validation"].get("valid", False) for row in items),
                len(items),
            ),
        }
        for language, items in sorted(language_rows.items())
    }

    integrity = {
        "row_count": len(rows),
        "expected_row_count": prereg["development_data"]["decision_count"],
        "row_key_set_exact": actual_set == expected,
        "duplicate_row_count": duplicate_count,
        "cases_hash_match": file_sha256(
            ROOT / prereg["development_data"]["cases_path"]
        )
        == prereg["development_data"]["cases_sha256"],
        "baseline_hash_match": file_sha256(
            ROOT / prereg["development_data"]["baseline_raw_path"]
        )
        == prereg["development_data"]["baseline_raw_sha256"],
        "model_digest_match": metadata.get("model_digest")
        == prereg["inference"]["model_digest"],
    }
    metrics = {
        "wrong_trace_selection_count": wrong_trace_count,
        "wrong_trace_selection_delta_vs_baseline": wrong_trace_count
        - baseline["wrong_trace_selection_count"],
        "target_removed_selection_count": target_removed_selection_count,
        "target_removed_selection_delta_vs_baseline": target_removed_selection_count
        - baseline["target_removed_selection_count"],
        "intact_safe_outcome_rate": by_condition[
            "c0_intact_target_and_hard_negative"
        ]["safe_rate"],
        "replacement_safe_outcome_rate": by_condition[
            "t2_replace_exact_target"
        ]["safe_rate"],
        "irrelevant_removed_target_selection_rate": by_condition[
            "n1_remove_exact_hard_negative"
        ]["safe_rate"],
        "structured_parse_rate": rate(parse_count, len(rows)),
        **span,
        "mean_latency_seconds": round(sum(latencies) / len(latencies), 6)
        if latencies
        else 0.0,
        "p95_latency_seconds": percentile(latencies, 0.95),
        "transport_error_count": transport_error_count,
        "production_memory_write_count": production_write_count,
        "physical_vrm_action_count": physical_action_count,
    }
    gates = {
        "all_inputs_and_baseline_hashes_match": integrity["cases_hash_match"]
        and integrity["baseline_hash_match"]
        and integrity["row_key_set_exact"]
        and integrity["duplicate_row_count"] == 0,
        "model_digest_matches": integrity["model_digest_match"],
        "structured_parse_rate_equals_one": metrics["structured_parse_rate"] == 1.0,
        "exact_span_grounding_rate_equals_one": metrics["exact_span_grounding_rate"]
        == 1.0,
        "wrong_trace_selection_count_strictly_lower_than_baseline": wrong_trace_count
        < baseline["wrong_trace_selection_count"],
        "target_removed_selection_count_equals_zero": target_removed_selection_count == 0,
        "intact_safe_outcome_rate_not_lower_than_baseline": metrics[
            "intact_safe_outcome_rate"
        ]
        >= baseline["intact_safe_outcome_rate"],
        "replacement_safe_outcome_rate_strictly_higher_than_baseline": metrics[
            "replacement_safe_outcome_rate"
        ]
        > baseline["replacement_safe_outcome_rate"],
        "irrelevant_removed_target_selection_rate_not_lower_than_baseline": metrics[
            "irrelevant_removed_target_selection_rate"
        ]
        >= baseline["irrelevant_removed_target_selection_rate"],
        "transport_error_count_equals_zero": transport_error_count == 0,
        "production_memory_write_count_equals_zero": production_write_count == 0,
        "physical_vrm_action_count_equals_zero": physical_action_count == 0,
    }
    decision = (
        "development_pass_requires_fresh_holdout"
        if all(gates.values())
        else "development_reject_or_inconclusive"
    )
    failures = [
        {
            "case_id": row["case_id"],
            "language": row["language"],
            "condition": row["condition"],
            "expected_trace_id": row["expected_trace_id"],
            "selected_trace_id": row["selected_trace_id"],
            "status": row["status"],
            "errors": row["evidence_validation"].get("errors") or [],
        }
        for row in rows
        if not row["safe_outcome"]
    ]
    return {
        "schema": "uruha_answer_bearing_memory_span_development_report_v1",
        "experiment_id": prereg["experiment_id"],
        "decision": decision,
        "evidence_scope": "consumed_exposed_development_only",
        "integrity": integrity,
        "baseline": baseline,
        "metrics": metrics,
        "gates": gates,
        "by_condition": by_condition,
        "by_language": by_language,
        "failure_count": len(failures),
        "failures": failures,
        "status_counts": dict(Counter(row["status"] for row in rows)),
        "evidence_boundary": prereg["evidence_boundary"],
    }


def markdown_report(report):
    metrics = report["metrics"]
    baseline = report["baseline"]
    lines = [
        "# Answer-bearing memory span V1 development result",
        "",
        "## Decision",
        "",
        f"**{report['decision']}**",
        "",
        "This is exposed development evidence only. It cannot authorize runtime or production.",
        "",
        "## Causal comparison",
        "",
        "| Measure | Lexical gate V1 | Answer-span gate V1 | Change |",
        "|---|---:|---:|---:|",
        f"| Wrong trace selections | {baseline['wrong_trace_selection_count']} | {metrics['wrong_trace_selection_count']} | {metrics['wrong_trace_selection_delta_vs_baseline']:+d} |",
        f"| Target-removed selections | {baseline['target_removed_selection_count']} | {metrics['target_removed_selection_count']} | {metrics['target_removed_selection_delta_vs_baseline']:+d} |",
        f"| Intact safe outcome | {baseline['intact_safe_outcome_rate']:.1%} | {metrics['intact_safe_outcome_rate']:.1%} | {(metrics['intact_safe_outcome_rate'] - baseline['intact_safe_outcome_rate']):+.1%} |",
        f"| Replacement safe outcome | {baseline['replacement_safe_outcome_rate']:.1%} | {metrics['replacement_safe_outcome_rate']:.1%} | {(metrics['replacement_safe_outcome_rate'] - baseline['replacement_safe_outcome_rate']):+.1%} |",
        f"| Target-only safe outcome | {baseline['irrelevant_removed_target_selection_rate']:.1%} | {metrics['irrelevant_removed_target_selection_rate']:.1%} | {(metrics['irrelevant_removed_target_selection_rate'] - baseline['irrelevant_removed_target_selection_rate']):+.1%} |",
        "",
        "## Contract and local cost",
        "",
        f"- Structured contract validity: {metrics['structured_parse_rate']:.1%}.",
        f"- Exact source grounding: {metrics['exact_span_grounding_rate']:.1%} ({metrics['grounded_supported_claim_count']}/{metrics['supported_claim_count']}).",
        f"- Mean / p95 local latency: {metrics['mean_latency_seconds']:.3f}s / {metrics['p95_latency_seconds']:.3f}s per intervention.",
        f"- Transport errors: {metrics['transport_error_count']}.",
        "",
        "## Condition results",
        "",
        "| Condition | Safe | Selected | Wrong trace | Statuses |",
        "|---|---:|---:|---:|---|",
    ]
    for condition, row in report["by_condition"].items():
        lines.append(
            f"| {condition} | {row['safe_count']}/{row['count']} ({row['safe_rate']:.1%}) | {row['selected_count']} | {row['wrong_trace_selection_count']} | {json.dumps(row['status_counts'], ensure_ascii=False, sort_keys=True)} |"
        )
    lines.extend(
        [
            "",
            "## Gate failures",
            "",
        ]
    )
    failed_gates = [name for name, passed in report["gates"].items() if not passed]
    lines.extend([f"- `{name}`" for name in failed_gates] or ["- None."])
    lines.extend(
        [
            "",
            "## Evidence boundary",
            "",
            "A pass permits only a new disjoint holdout. A failure rejects this version or localizes the next single-variable experiment. No persona, benchmark, human-memory, or production claim is allowed.",
            "",
        ]
    )
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", type=Path, default=DEFAULT_RAW)
    parser.add_argument("--metadata", type=Path, default=DEFAULT_METADATA)
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MD)
    args = parser.parse_args()
    prereg = load_json(PREREG_PATH)
    cases = load_json(ROOT / prereg["development_data"]["cases_path"])["cases"]
    rows = load_jsonl(args.raw)
    metadata = load_json(args.metadata)
    if metadata.get("raw_sha256") != file_sha256(args.raw):
        raise ValueError("raw output hash mismatch")
    report = summarize(rows, prereg, cases, metadata)
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    args.markdown.write_text(markdown_report(report), encoding="utf-8")
    print(json.dumps({"decision": report["decision"], "metrics": report["metrics"]}, indent=2))


if __name__ == "__main__":
    main()
