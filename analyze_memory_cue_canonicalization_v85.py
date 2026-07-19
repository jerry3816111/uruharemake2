#!/usr/bin/env python3
"""Analyze the frozen V85 memory-cue canonicalization regression."""

from __future__ import annotations

import argparse
import json
import math
import statistics
from collections import Counter
from pathlib import Path

import memory_cue_canonicalization_v85 as v85
import planner_supervision_bounded_review_v82 as v82
import planner_supervision_v76 as v76
import run_memory_cue_canonicalization_v85 as runner
import run_rightbrain_pipeline_shadow_v61 as v61


ROOT = Path(__file__).resolve().parent
PREREG_PATH = ROOT / "configs/memory_cue_canonicalization_v85_preregistration.json"


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def percentile(values, quantile):
    values = sorted(float(value) for value in values if value is not None)
    return values[max(0, min(len(values) - 1, math.ceil(quantile * len(values)) - 1))] if values else None


def summarize(rows):
    count = len(rows)
    hits = sum(row["score"]["clean_required_hit_count"] for row in rows)
    total = sum(row["score"]["clean_required_count"] for row in rows)
    latencies = [row["elapsed_seconds"] for row in rows]
    return {
        "observation_count": count,
        "clean_semantic_recall": hits / max(1, total),
        "surface_pass_rate": sum(row["score"]["surface_pass"] for row in rows) / max(1, count),
        "transcript_label_leak_rate": sum(row["score"]["transcript_label_leak"] for row in rows) / max(1, count),
        "over_max_rate": sum(row["score"]["over_max"] for row in rows) / max(1, count),
        "forbidden_violation_rate": sum(row["score"]["forbidden_violation"] for row in rows) / max(1, count),
        "private_intrusion_rate": sum(row["score"]["private_memory_intrusion"] for row in rows) / max(1, count),
        "median_latency_seconds": statistics.median(latencies) if latencies else None,
        "p95_latency_seconds": percentile(latencies, 0.95),
        "peak_ollama_rss_bytes": max((row["peak_ollama_rss_bytes"] for row in rows if row.get("peak_ollama_rss_bytes") is not None), default=None),
        "failure_code_counts": dict(sorted(Counter(code for row in rows for code in row["score"]["failure_codes"]).items())),
    }


def decision(contract, integrity, summaries):
    if not integrity:
        return "inconclusive_integrity_failure", {}
    control = summaries[v85.C0]
    treatment = summaries[v85.T1]
    gates = contract["advance_gates"]
    latency_ratio = treatment["median_latency_seconds"] / max(control["median_latency_seconds"], 1e-9)
    checks = {
        "zero_transcript_labels": treatment["transcript_label_leak_rate"] <= gates["treatment_transcript_label_leak_rate_max"],
        "treatment_surface_pass": treatment["surface_pass_rate"] >= gates["treatment_surface_pass_rate_min"],
        "surface_delta": treatment["surface_pass_rate"] - control["surface_pass_rate"] >= gates["surface_pass_delta_min"],
        "treatment_clean_semantics": treatment["clean_semantic_recall"] >= gates["treatment_clean_semantic_recall_min"],
        "semantic_noninferiority": treatment["clean_semantic_recall"] - control["clean_semantic_recall"] >= gates["clean_semantic_recall_delta_min"],
        "over_max": treatment["over_max_rate"] <= gates["treatment_over_max_rate_max"],
        "forbidden_noninferiority": treatment["forbidden_violation_rate"] - control["forbidden_violation_rate"] <= gates["forbidden_violation_delta_max"],
        "private_noninferiority": treatment["private_intrusion_rate"] - control["private_intrusion_rate"] <= gates["private_intrusion_delta_max"],
        "latency_ratio": latency_ratio <= gates["latency_ratio_max"],
        "p95_latency": treatment["p95_latency_seconds"] <= gates["treatment_p95_latency_seconds_max"],
        "peak_rss": treatment["peak_ollama_rss_bytes"] <= gates["peak_ollama_rss_bytes_max"],
    }
    if all(checks.values()):
        return contract["authorizations"]["on_pass"], checks
    failure = contract["failure_rule"]
    if (
        treatment["surface_pass_rate"] - control["surface_pass_rate"] <= failure["surface_pass_delta_max"]
        or treatment["clean_semantic_recall"] - control["clean_semantic_recall"] < failure["clean_semantic_recall_delta_below"]
    ):
        return failure["decision"], checks
    return "inconclusive_effect_between_preregistered_gates", checks


def analyze(contract, packets, rows, source_checks, installed_digest, expected_packets):
    sequence = v85.validate_resume_prefix(packets, rows, contract)
    integrity_checks = {
        "private_sources": all(source_checks.values()),
        "packet_count": len(packets) == int(contract["scope"]["case_count"]),
        "packet_recalculation": [p["packet_sha256"] for p in packets] == [p["packet_sha256"] for p in expected_packets],
        "sequence_complete": len(rows) == len(sequence) == int(contract["scope"]["expected_model_call_count"]),
        "model_digest": installed_digest == contract["model"]["digest"] and all(row.get("model_digest") == contract["model"]["digest"] for row in rows),
        "responses_complete": all(row.get("response_model") == contract["model"]["ollama_tag"] and row.get("done") is True and not row.get("transport_error") for row in rows),
        "resources_complete": all(row.get("prompt_eval_count") is not None and row.get("peak_ollama_rss_bytes") is not None for row in rows),
        "scores_recalculate": all(
            row.get("score") == v85.score_reply(packet, row.get("raw_reply"))
            for packet in packets for row in rows if row.get("candidate_id") == packet["candidate_id"]
        ),
        "no_side_effects": all(row.get("production_memory_write_count") == 0 and row.get("physical_vrm_action_count") == 0 for row in rows),
    }
    integrity = all(integrity_checks.values())
    summaries = {condition: summarize([row for row in rows if row["condition"] == condition]) for condition in v85.CONDITIONS}
    final_decision, gate_checks = decision(contract, integrity, summaries)
    return {
        "schema": "uruha_memory_cue_canonicalization_analysis_v85",
        "experiment_id": contract["experiment_id"],
        "decision": final_decision,
        "integrity_passed": integrity,
        "integrity_checks": integrity_checks,
        "condition_summaries": summaries,
        "advance_gate_checks": gate_checks,
        "production_default_enable_authorized": False,
        "training_data_authorized": False,
        "next_step": "Run a fresh disjoint V86 holdout." if final_decision == contract["authorizations"]["on_pass"] else "Do not expand until the failed gate has new evidence.",
        "evidence_boundary": contract["evidence_boundary"],
    }


def render_markdown(report):
    control = report["condition_summaries"][v85.C0]
    treatment = report["condition_summaries"][v85.T1]
    return "\n".join([
        "# V85 Memory Cue Canonicalization Regression",
        "",
        f"- Decision: `{report['decision']}`",
        f"- Integrity: {'PASS' if report['integrity_passed'] else 'FAIL'}",
        "",
        "| Metric | Legacy cue | Canonical cue |",
        "|---|---:|---:|",
        f"| Clean semantic recall | {control['clean_semantic_recall']:.1%} | {treatment['clean_semantic_recall']:.1%} |",
        f"| Surface pass | {control['surface_pass_rate']:.1%} | {treatment['surface_pass_rate']:.1%} |",
        f"| Transcript-label leak | {control['transcript_label_leak_rate']:.1%} | {treatment['transcript_label_leak_rate']:.1%} |",
        f"| Over max length | {control['over_max_rate']:.1%} | {treatment['over_max_rate']:.1%} |",
        f"| Median latency | {control['median_latency_seconds']:.2f}s | {treatment['median_latency_seconds']:.2f}s |",
        "",
        "A pass authorizes only a fresh V86 holdout; the production default remains disabled.",
        "",
        report["evidence_boundary"],
        "",
    ])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", type=Path, default=ROOT / "reports/memory_cue_canonicalization_v85.json")
    parser.add_argument("--md", type=Path, default=ROOT / "reports/memory_cue_canonicalization_v85.md")
    args = parser.parse_args()
    contract = load_json(PREREG_PATH)
    local = {name: ROOT / value for name, value in contract["local_paths"].items()}
    packets = v76.load_jsonl(local["packet_queue"])
    rows = v76.load_jsonl(local["raw_results"])
    sources = v85.verify_private_sources(contract, ROOT)
    with v61._isolated_brain(contract) as (bot, calls, _):
        expected_packets = runner.build_packets(contract, bot.right_brain)
    if calls:
        raise SystemExit("V85 analyzer reconstruction unexpectedly called LeftBrain")
    installed = v82.installed_model_digests()
    report = analyze(contract, packets, rows, sources, installed.get(contract["model"]["ollama_tag"]), expected_packets)
    local["local_analysis"].parent.mkdir(parents=True, exist_ok=True)
    local["local_analysis"].write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.md.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps({"decision": report["decision"], "integrity": report["integrity_passed"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
