#!/usr/bin/env python3
"""Analyze V84 paired memory-integration causal outcomes."""

from __future__ import annotations

import argparse
import json
import math
import random
import statistics
from collections import Counter, defaultdict
from pathlib import Path

import planner_memory_causality_v84 as v84
import planner_supervision_bounded_review_v82 as v82
import planner_supervision_v76 as v76
import run_planner_memory_causality_v84 as runner
import run_rightbrain_pipeline_shadow_v61 as v61


ROOT = Path(__file__).resolve().parent
PREREG_PATH = ROOT / "configs/planner_memory_causality_v84_preregistration.json"


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def percentile(values, quantile):
    values = sorted(float(value) for value in values if value is not None)
    if not values:
        return None
    return values[max(0, min(len(values) - 1, math.ceil(quantile * len(values)) - 1))]


def condition_summary(rows):
    count = len(rows)
    hits = sum(row["score"]["required_group_hit_count"] for row in rows)
    groups = sum(row["score"]["required_group_count"] for row in rows)
    latencies = [row["elapsed_seconds"] for row in rows]
    return {
        "observation_count": count,
        "required_group_hit_count": hits,
        "required_group_count": groups,
        "required_group_recall": hits / max(1, groups),
        "semantic_complete_rate": sum(row["score"]["semantic_complete"] for row in rows) / max(1, count),
        "outcome_pass_rate": sum(row["score"]["outcome_pass"] for row in rows) / max(1, count),
        "surface_pass_rate": sum(row["score"]["surface_pass"] for row in rows) / max(1, count),
        "forbidden_violation_rate": sum(row["score"]["forbidden_violation"] for row in rows) / max(1, count),
        "private_memory_intrusion_rate": sum(row["score"]["private_memory_intrusion"] for row in rows) / max(1, count),
        "median_latency_seconds": statistics.median(latencies) if latencies else None,
        "p95_latency_seconds": percentile(latencies, 0.95),
        "median_prompt_eval_count": statistics.median(
            row["prompt_eval_count"] for row in rows if row.get("prompt_eval_count") is not None
        ) if any(row.get("prompt_eval_count") is not None for row in rows) else None,
        "peak_ollama_rss_bytes": max(
            (row["peak_ollama_rss_bytes"] for row in rows if row.get("peak_ollama_rss_bytes") is not None),
            default=None,
        ),
        "failure_code_counts": dict(sorted(Counter(
            code for row in rows for code in row["score"]["failure_codes"]
        ).items())),
    }


def paired_summary(rows, bootstrap_samples=10000, bootstrap_seed=20260784):
    grouped = defaultdict(dict)
    for row in rows:
        grouped[(row["candidate_id"], row["seed"])][row["condition"]] = row
    pairs = []
    for conditions in grouped.values():
        if set(conditions) != set(v84.CONDITIONS):
            continue
        intact = conditions[v84.C0]
        removed = conditions[v84.T1]
        pairs.append({
            "delta": intact["score"]["required_group_recall"] - removed["score"]["required_group_recall"],
            "identical": intact["score"]["normalized_reply"] == removed["score"]["normalized_reply"],
        })
    deltas = [pair["delta"] for pair in pairs]
    observed = statistics.mean(deltas) if deltas else 0.0
    rng = random.Random(bootstrap_seed)
    bootstrapped = []
    for _ in range(bootstrap_samples):
        sample = [deltas[rng.randrange(len(deltas))] for _ in deltas]
        bootstrapped.append(statistics.mean(sample))
    bootstrapped.sort()
    return {
        "pair_count": len(pairs),
        "intact_win_count": sum(delta > 0 for delta in deltas),
        "tie_count": sum(delta == 0 for delta in deltas),
        "intact_loss_count": sum(delta < 0 for delta in deltas),
        "intact_win_rate": sum(delta > 0 for delta in deltas) / max(1, len(deltas)),
        "mean_recall_delta_intact_minus_removed": observed,
        "identical_reply_rate": sum(pair["identical"] for pair in pairs) / max(1, len(pairs)),
        "bootstrap_samples": bootstrap_samples,
        "bootstrap_seed": bootstrap_seed,
        "bootstrap_ci95": [
            bootstrapped[int(0.025 * (len(bootstrapped) - 1))] if bootstrapped else 0.0,
            bootstrapped[int(0.975 * (len(bootstrapped) - 1))] if bootstrapped else 0.0,
        ],
    }


def classify_decision(contract, integrity_passed, conditions, paired):
    if not integrity_passed:
        return "inconclusive_integrity_failure", {}
    intact = conditions[v84.C0]
    removed = conditions[v84.T1]
    gates = contract["advance_gates"]
    checks = {
        "intact_required_group_recall": intact["required_group_recall"] >= gates["intact_required_group_recall_min"],
        "paired_recall_delta": paired["mean_recall_delta_intact_minus_removed"] >= gates["paired_recall_delta_min"],
        "bootstrap_delta_lower_95": paired["bootstrap_ci95"][0] > gates["bootstrap_delta_lower_95_min_exclusive"],
        "intact_win_rate": paired["intact_win_rate"] >= gates["intact_win_rate_min"],
        "intact_surface_pass_rate": intact["surface_pass_rate"] >= gates["intact_surface_pass_rate_min"],
        "surface_noninferiority": intact["surface_pass_rate"] - removed["surface_pass_rate"] >= gates["intact_surface_delta_vs_removed_min"],
        "forbidden_noninferiority": intact["forbidden_violation_rate"] - removed["forbidden_violation_rate"] <= gates["intact_forbidden_violation_delta_vs_removed_max"],
        "private_memory_noninferiority": intact["private_memory_intrusion_rate"] - removed["private_memory_intrusion_rate"] <= gates["intact_private_intrusion_delta_vs_removed_max"],
        "median_latency": intact["median_latency_seconds"] <= gates["median_latency_seconds_max"],
        "p95_latency": intact["p95_latency_seconds"] <= gates["p95_latency_seconds_max"],
        "peak_rss": intact["peak_ollama_rss_bytes"] <= gates["peak_ollama_rss_bytes_max"],
    }
    if all(checks.values()):
        return "memory_integration_signal_causally_supported_bounded", checks
    failure = contract["failure_rule"]
    if (
        paired["mean_recall_delta_intact_minus_removed"] <= failure["paired_recall_delta_max"]
        or paired["intact_win_rate"] < failure["intact_win_rate_below"]
    ):
        return failure["decision"], checks
    return "inconclusive_effect_between_preregistered_gates", checks


def analyze(contract, packets, rows, source_checks, installed_digest, expected_packets=None):
    sequence = v84.validate_resume_prefix(packets, rows, contract)
    expected = int(contract["scope"]["expected_model_call_count"])
    sequence_complete = len(rows) == len(sequence) == expected
    integrity_checks = {
        "private_source_hashes": all(source_checks.values()),
        "packet_count": len(packets) == int(contract["scope"]["fresh_case_count"]),
        "packet_self_hashes": all(
            packet.get("packet_sha256") == v76.canonical_sha256(
                {key: value for key, value in packet.items() if key != "packet_sha256"}
            )
            for packet in packets
        ),
        "packet_recalculation": expected_packets is not None and [
            packet["packet_sha256"] for packet in packets
        ] == [packet["packet_sha256"] for packet in expected_packets],
        "sequence_complete": sequence_complete,
        "model_digest": installed_digest == contract["model"]["digest"] and all(
            row.get("model_digest") == contract["model"]["digest"] for row in rows
        ),
        "response_identity": all(
            row.get("response_model") == contract["model"]["ollama_tag"] and row.get("done") is True
            for row in rows
        ),
        "transport": all(not row.get("transport_error") for row in rows),
        "resource_metrics_complete": all(
            row.get("elapsed_seconds") is not None
            and row.get("prompt_eval_count") is not None
            and row.get("peak_ollama_rss_bytes") is not None
            for row in rows
        ),
        "payload_binding": all(
            row.get("payload_sha256") == packet["payload_sha256"][row["condition"]]
            for packet in packets for row in rows if row.get("candidate_id") == packet["candidate_id"]
        ),
        "no_runtime_side_effects": all(
            row.get("production_memory_write_count") == 0 and row.get("physical_vrm_action_count") == 0
            for row in rows
        ),
        "score_recalculation": all(
            row.get("score") == v84.score_reply(packet, row.get("raw_reply"))
            for packet in packets for row in rows if row.get("candidate_id") == packet["candidate_id"]
        ),
    }
    integrity_passed = all(integrity_checks.values())
    by_condition = {
        condition: condition_summary([row for row in rows if row["condition"] == condition])
        for condition in v84.CONDITIONS
    }
    paired = paired_summary(rows)
    decision, gate_checks = classify_decision(contract, integrity_passed, by_condition, paired)
    return {
        "schema": "uruha_planner_memory_causality_analysis_v84",
        "experiment_id": contract["experiment_id"],
        "decision": decision,
        "integrity_passed": integrity_passed,
        "integrity_checks": integrity_checks,
        "case_count": len(packets),
        "scenario_family_distribution": dict(sorted(Counter(packet["scenario_family"] for packet in packets).items())),
        "condition_summaries": by_condition,
        "paired_effect": paired,
        "advance_gate_checks": gate_checks,
        "training_data_authorized": False,
        "production_runtime_change_authorized": False,
        "human_rating_required": False,
        "evidence_boundary": contract["evidence_boundary"],
    }


def tracked_report(analysis):
    return analysis


def render_markdown(report):
    intact = report["condition_summaries"][v84.C0]
    removed = report["condition_summaries"][v84.T1]
    paired = report["paired_effect"]
    lines = [
        "# V84 Planner Memory Causality Pilot",
        "",
        f"- Decision: `{report['decision']}`",
        f"- Integrity: {'PASS' if report['integrity_passed'] else 'FAIL'}",
        f"- Cases: {report['case_count']} fresh private memory cases; two matched replicates each",
        "",
        "| Observable result | Intact memory plan | Memory integration removed |",
        "|---|---:|---:|",
        f"| Required-group recall | {intact['required_group_recall']:.1%} | {removed['required_group_recall']:.1%} |",
        f"| Semantic-complete rate | {intact['semantic_complete_rate']:.1%} | {removed['semantic_complete_rate']:.1%} |",
        f"| Surface pass rate | {intact['surface_pass_rate']:.1%} | {removed['surface_pass_rate']:.1%} |",
        f"| Median latency | {intact['median_latency_seconds']:.2f}s | {removed['median_latency_seconds']:.2f}s |",
        "",
        f"Paired recall delta (intact minus removed): **{paired['mean_recall_delta_intact_minus_removed']:+.1%}**; "
        f"95% bootstrap CI [{paired['bootstrap_ci95'][0]:+.1%}, {paired['bootstrap_ci95'][1]:+.1%}].",
        "",
        "## Evidence Boundary",
        "",
        report["evidence_boundary"],
        "",
    ]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", type=Path, default=ROOT / "reports/planner_memory_causality_v84.json")
    parser.add_argument("--md", type=Path, default=ROOT / "reports/planner_memory_causality_v84.md")
    args = parser.parse_args()
    contract = load_json(PREREG_PATH)
    local = {name: ROOT / value for name, value in contract["local_paths"].items()}
    packets = v76.load_jsonl(local["packet_queue"])
    rows = v76.load_jsonl(local["raw_results"])
    source_checks = v84.verify_private_sources(contract, ROOT)
    installed = v82.installed_model_digests()
    with v61._isolated_brain(contract) as (bot, leftbrain_calls, _isolation):
        expected_packets = runner.build_packets(contract, bot.right_brain)
    if leftbrain_calls:
        raise SystemExit("V84 analyzer packet reconstruction unexpectedly called LeftBrain")
    report = analyze(
        contract,
        packets,
        rows,
        source_checks,
        installed.get(contract["model"]["ollama_tag"]),
        expected_packets=expected_packets,
    )
    local["local_analysis"].parent.mkdir(parents=True, exist_ok=True)
    local["local_analysis"].write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    args.json.write_text(json.dumps(tracked_report(report), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.md.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps({"decision": report["decision"], "integrity": report["integrity_passed"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
