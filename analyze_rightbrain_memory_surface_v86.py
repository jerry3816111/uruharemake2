#!/usr/bin/env python3
"""Analyze the frozen V86 fresh disjoint RightBrain memory-surface holdout."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import analyze_rightbrain_length_contract_v85_1 as v851_analyzer
import planner_supervision_bounded_review_v82 as v82
import planner_supervision_v76 as v76
import rightbrain_memory_surface_v86 as v86
import run_rightbrain_memory_surface_v86 as runner
import run_rightbrain_pipeline_shadow_v61 as v61


ROOT = Path(__file__).resolve().parent
PREREG_PATH = ROOT / "configs/rightbrain_memory_surface_v86_preregistration.json"


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


summarize = v851_analyzer.summarize


def decision(contract, integrity, summaries):
    if not integrity:
        return "inconclusive_integrity_failure", {}
    legacy = summaries[v86.C0]
    canonical = summaries[v86.C1]
    treatment = summaries[v86.T2]
    gates = contract["advance_gates"]
    checks = {
        "treatment_surface_pass": treatment["surface_pass_rate"] >= gates["treatment_surface_pass_rate_min"],
        "combined_surface_delta": treatment["surface_pass_rate"] - legacy["surface_pass_rate"] >= gates["combined_surface_pass_delta_min"],
        "treatment_clean_semantics": treatment["clean_semantic_recall"] >= gates["treatment_clean_semantic_recall_min"],
        "semantic_vs_legacy": treatment["clean_semantic_recall"] - legacy["clean_semantic_recall"] >= gates["semantic_delta_vs_legacy_min"],
        "semantic_vs_canonical": treatment["clean_semantic_recall"] - canonical["clean_semantic_recall"] >= gates["semantic_delta_vs_canonical_min"],
        "zero_treatment_transcript_labels": treatment["transcript_label_leak_rate"] <= gates["treatment_transcript_label_leak_rate_max"],
        "canonical_label_noninferiority": canonical["transcript_label_leak_rate"] - legacy["transcript_label_leak_rate"] <= gates["canonical_label_leak_delta_vs_legacy_max"],
        "treatment_over_max": treatment["over_max_rate"] <= gates["treatment_over_max_rate_max"],
        "length_noninferiority": treatment["over_max_rate"] - canonical["over_max_rate"] <= gates["treatment_over_max_delta_vs_canonical_max"],
        "forbidden_vs_legacy": treatment["forbidden_violation_rate"] - legacy["forbidden_violation_rate"] <= gates["forbidden_violation_delta_max"],
        "forbidden_vs_canonical": treatment["forbidden_violation_rate"] - canonical["forbidden_violation_rate"] <= gates["forbidden_violation_delta_max"],
        "private_vs_legacy": treatment["private_intrusion_rate"] - legacy["private_intrusion_rate"] <= gates["private_intrusion_delta_max"],
        "private_vs_canonical": treatment["private_intrusion_rate"] - canonical["private_intrusion_rate"] <= gates["private_intrusion_delta_max"],
        "latency_ratio": treatment["median_latency_seconds"] / max(legacy["median_latency_seconds"], 1e-9) <= gates["latency_ratio_vs_legacy_max"],
        "p95_latency": treatment["p95_latency_seconds"] <= gates["treatment_p95_latency_seconds_max"],
        "peak_rss": treatment["peak_ollama_rss_bytes"] <= gates["peak_ollama_rss_bytes_max"],
    }
    if all(checks.values()):
        return contract["authorizations"]["on_pass"], checks
    failure = contract["failure_rule"]
    if (
        treatment["surface_pass_rate"] - legacy["surface_pass_rate"] <= failure["combined_surface_pass_delta_max"]
        or treatment["clean_semantic_recall"] - legacy["clean_semantic_recall"] < failure["semantic_delta_vs_legacy_below"]
    ):
        return failure["decision"], checks
    return "inconclusive_effect_between_preregistered_gates", checks


def analyze(contract, packets, rows, source_checks, installed_digest, expected_packets):
    sequence = v86.validate_resume_prefix(packets, rows, contract)
    integrity_checks = {
        "private_sources": all(source_checks.values()),
        "packet_count": len(packets) == int(contract["scope"]["case_count"]),
        "fresh_session_coverage": len({packet["source_session_id"] for packet in packets}) >= int(contract["selection"]["minimum_session_count"]),
        "packet_recalculation": [p["packet_sha256"] for p in packets] == [p["packet_sha256"] for p in expected_packets],
        "sequence_complete": len(rows) == len(sequence) == int(contract["scope"]["expected_model_call_count"]),
        "model_digest": installed_digest == contract["model"]["digest"] and all(row.get("model_digest") == contract["model"]["digest"] for row in rows),
        "responses_complete": all(row.get("response_model") == contract["model"]["ollama_tag"] and row.get("done") is True and not row.get("transport_error") for row in rows),
        "resources_complete": all(row.get("prompt_eval_count") is not None and row.get("peak_ollama_rss_bytes") is not None for row in rows),
        "scores_recalculate": all(
            row.get("score") == v86.score_reply(packet, row.get("raw_reply"))
            for packet in packets
            for row in rows
            if row.get("candidate_id") == packet["candidate_id"]
        ),
        "no_side_effects": all(row.get("production_memory_write_count") == 0 and row.get("physical_vrm_action_count") == 0 for row in rows),
    }
    integrity = all(integrity_checks.values())
    summaries = {
        condition: summarize([row for row in rows if row["condition"] == condition])
        for condition in v86.CONDITIONS
    }
    final_decision, gate_checks = decision(contract, integrity, summaries)
    return {
        "schema": "uruha_rightbrain_memory_surface_analysis_v86",
        "experiment_id": contract["experiment_id"],
        "decision": final_decision,
        "integrity_passed": integrity,
        "integrity_checks": integrity_checks,
        "condition_summaries": summaries,
        "component_deltas": {
            "canonicalization_surface_delta": summaries[v86.C1]["surface_pass_rate"] - summaries[v86.C0]["surface_pass_rate"],
            "length_contract_surface_delta": summaries[v86.T2]["surface_pass_rate"] - summaries[v86.C1]["surface_pass_rate"],
            "combined_surface_delta": summaries[v86.T2]["surface_pass_rate"] - summaries[v86.C0]["surface_pass_rate"],
        },
        "advance_gate_checks": gate_checks,
        "production_default_enable_authorized": False,
        "production_shadow_authorized": final_decision == contract["authorizations"]["on_pass"],
        "training_data_authorized": False,
        "evidence_boundary": contract["evidence_boundary"],
    }


def render_markdown(report):
    rows = report["condition_summaries"]
    return "\n".join(
        [
            "# V86 Fresh Disjoint Memory-Surface Holdout",
            "",
            f"- Decision: `{report['decision']}`",
            f"- Integrity: {'PASS' if report['integrity_passed'] else 'FAIL'}",
            "",
            "| Metric | Legacy | Canonical cue | Canonical + length |",
            "|---|---:|---:|---:|",
            f"| Clean semantic recall | {rows[v86.C0]['clean_semantic_recall']:.1%} | {rows[v86.C1]['clean_semantic_recall']:.1%} | {rows[v86.T2]['clean_semantic_recall']:.1%} |",
            f"| Surface pass | {rows[v86.C0]['surface_pass_rate']:.1%} | {rows[v86.C1]['surface_pass_rate']:.1%} | {rows[v86.T2]['surface_pass_rate']:.1%} |",
            f"| Transcript-label leak | {rows[v86.C0]['transcript_label_leak_rate']:.1%} | {rows[v86.C1]['transcript_label_leak_rate']:.1%} | {rows[v86.T2]['transcript_label_leak_rate']:.1%} |",
            f"| Over max length | {rows[v86.C0]['over_max_rate']:.1%} | {rows[v86.C1]['over_max_rate']:.1%} | {rows[v86.T2]['over_max_rate']:.1%} |",
            f"| Median latency | {rows[v86.C0]['median_latency_seconds']:.2f}s | {rows[v86.C1]['median_latency_seconds']:.2f}s | {rows[v86.T2]['median_latency_seconds']:.2f}s |",
            "",
            f"- Canonicalization surface delta: {report['component_deltas']['canonicalization_surface_delta']:+.1%}",
            f"- Length-contract surface delta: {report['component_deltas']['length_contract_surface_delta']:+.1%}",
            f"- Combined surface delta: {report['component_deltas']['combined_surface_delta']:+.1%}",
            "",
            report["evidence_boundary"],
            "",
        ]
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", type=Path, default=ROOT / "reports/rightbrain_memory_surface_v86.json")
    parser.add_argument("--md", type=Path, default=ROOT / "reports/rightbrain_memory_surface_v86.md")
    args = parser.parse_args()
    contract = load_json(PREREG_PATH)
    local = {name: ROOT / value for name, value in contract["local_paths"].items()}
    packets = v76.load_jsonl(local["packet_queue"])
    rows = v76.load_jsonl(local["raw_results"])
    sources = v86.verify_private_sources(contract, ROOT)
    with v61._isolated_brain(contract) as (bot, calls, _):
        expected_packets = runner.build_packets(contract, bot.right_brain)
    if calls:
        raise SystemExit("V86 analyzer reconstruction unexpectedly called LeftBrain")
    installed = v82.installed_model_digests()
    report = analyze(contract, packets, rows, sources, installed.get(contract["model"]["ollama_tag"]), expected_packets)
    local["local_analysis"].parent.mkdir(parents=True, exist_ok=True)
    local["local_analysis"].write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.md.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps({"decision": report["decision"], "integrity": report["integrity_passed"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
