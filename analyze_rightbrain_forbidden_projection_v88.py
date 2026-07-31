#!/usr/bin/env python3
"""Analyze the frozen V88 fresh-generation plus production-gate holdout."""

from __future__ import annotations

import argparse
import math
import json
import statistics
from collections import Counter
from pathlib import Path

import planner_supervision_bounded_review_v82 as v82
import planner_supervision_v76 as v76
import rightbrain_forbidden_projection_v88 as v88
import run_rightbrain_forbidden_projection_v88 as runner
import run_rightbrain_pipeline_shadow_v61 as v61


ROOT = Path(__file__).resolve().parent
PREREG_PATH = ROOT / "configs/rightbrain_forbidden_projection_v88_preregistration.json"


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def percentile(values, quantile):
    values = sorted(float(value) for value in values if value is not None)
    return values[max(0, min(len(values) - 1, math.ceil(quantile * len(values)) - 1))] if values else None


def _selected_rows(rows):
    selected = []
    grouped = {}
    for row in rows:
        grouped.setdefault(row["candidate_id"], []).append(row)
    for case_rows in grouped.values():
        accepted = [row for row in case_rows if row["gate_accepted"]]
        if accepted:
            selected.append(
                max(
                    accepted,
                    key=lambda row: (
                        float(row.get("production_candidate_score") or float("-inf")),
                        -int(row["sample_index"]),
                    ),
                )
            )
        else:
            selected.append(min(case_rows, key=lambda row: int(row["sample_index"])))
    return selected


def summarize(rows):
    selected = _selected_rows(rows)
    selected_hits = sum(
        row["prepared_score"]["clean_required_hit_count"] if row["gate_accepted"] else 0
        for row in selected
    )
    selected_total = sum(row["prepared_score"]["clean_required_count"] for row in selected)
    raw_hits = sum(row["raw_score"]["clean_required_hit_count"] for row in rows)
    raw_total = sum(row["raw_score"]["clean_required_count"] for row in rows)
    latencies = [row["elapsed_seconds"] for row in rows]
    case_count = len(selected)
    return {
        "sample_count": len(rows),
        "case_count": case_count,
        "sample_gate_accept_rate": sum(row["gate_accepted"] for row in rows) / max(1, len(rows)),
        "any_gate_accept_rate": sum(any(item["gate_accepted"] for item in rows if item["candidate_id"] == row["candidate_id"]) for row in selected) / max(1, case_count),
        "raw_clean_semantic_recall": raw_hits / max(1, raw_total),
        "selected_clean_semantic_recall": selected_hits / max(1, selected_total),
        "selected_surface_pass_rate": sum(row["gate_accepted"] and row["prepared_score"]["surface_pass"] for row in selected) / max(1, case_count),
        "selected_external_forbidden_violation_rate": sum(row["gate_accepted"] and row["prepared_score"]["forbidden_violation"] for row in selected) / max(1, case_count),
        "selected_private_intrusion_rate": sum(row["gate_accepted"] and row["prepared_score"]["private_memory_intrusion"] for row in selected) / max(1, case_count),
        "selected_over_max_rate": sum(row["gate_accepted"] and row["prepared_score"]["over_max"] for row in selected) / max(1, case_count),
        "median_latency_seconds": statistics.median(latencies) if latencies else None,
        "p95_latency_seconds": percentile(latencies, 0.95),
        "peak_ollama_rss_bytes": max(
            (row["peak_ollama_rss_bytes"] for row in rows if row.get("peak_ollama_rss_bytes") is not None),
            default=None,
        ),
        "gate_failure_code_counts": dict(
            sorted(Counter(code for row in rows for code in row["gate_rejection_reasons"]).items())
        ),
    }


def paired_identity(rows, stratum):
    by_key = {}
    for row in rows:
        if row["stratum"] != stratum:
            continue
        by_key.setdefault((row["candidate_id"], row["sample_index"]), {})[row["condition"]] = row
    complete = [pair for pair in by_key.values() if set(pair) == set(v88.CONDITIONS)]
    return {
        "pair_count": len(complete),
        "raw_reply_identity_rate": sum(pair[v88.C0]["raw_reply_sha256"] == pair[v88.T1]["raw_reply_sha256"] for pair in complete) / max(1, len(complete)),
        "gate_decision_identity_rate": sum(
            pair[v88.C0]["gate_accepted"] == pair[v88.T1]["gate_accepted"]
            and pair[v88.C0]["gate_rejection_reasons"] == pair[v88.T1]["gate_rejection_reasons"]
            for pair in complete
        ) / max(1, len(complete)),
    }


def decision(contract, integrity, summaries, identities):
    if not integrity:
        return "inconclusive_integrity_failure", {}
    conflict_c = summaries[v88.STRATUM_CONFLICT][v88.C0]
    conflict_t = summaries[v88.STRATUM_CONFLICT][v88.T1]
    safe_c = summaries[v88.STRATUM_NONCONFLICT][v88.C0]
    safe_t = summaries[v88.STRATUM_NONCONFLICT][v88.T1]
    identity = identities[v88.STRATUM_NONCONFLICT]
    gates = contract["advance_gates"]
    checks = {
        "treatment_conflict_any_gate_accept": conflict_t["any_gate_accept_rate"] >= gates["treatment_conflict_any_gate_accept_rate_min"],
        "conflict_any_gate_accept_delta": conflict_t["any_gate_accept_rate"] - conflict_c["any_gate_accept_rate"] >= gates["conflict_any_gate_accept_delta_min"],
        "treatment_conflict_selected_semantics": conflict_t["selected_clean_semantic_recall"] >= gates["treatment_conflict_selected_semantic_recall_min"],
        "conflict_selected_semantic_delta": conflict_t["selected_clean_semantic_recall"] - conflict_c["selected_clean_semantic_recall"] >= gates["conflict_selected_semantic_recall_delta_min"],
        "conflict_external_forbidden_noninferiority": conflict_t["selected_external_forbidden_violation_rate"] - conflict_c["selected_external_forbidden_violation_rate"] <= gates["conflict_external_forbidden_violation_delta_max"],
        "conflict_private_noninferiority": conflict_t["selected_private_intrusion_rate"] - conflict_c["selected_private_intrusion_rate"] <= gates["conflict_private_intrusion_delta_max"],
        "nonconflict_raw_identity": identity["raw_reply_identity_rate"] >= gates["nonconflict_raw_reply_identity_rate_min"],
        "nonconflict_gate_identity": identity["gate_decision_identity_rate"] >= gates["nonconflict_gate_decision_identity_rate_min"],
        "nonconflict_semantic_noninferiority": safe_t["selected_clean_semantic_recall"] - safe_c["selected_clean_semantic_recall"] >= gates["nonconflict_selected_semantic_recall_delta_min"],
        "nonconflict_external_forbidden_noninferiority": safe_t["selected_external_forbidden_violation_rate"] - safe_c["selected_external_forbidden_violation_rate"] <= gates["nonconflict_external_forbidden_violation_delta_max"],
        "latency_ratio": conflict_t["median_latency_seconds"] / max(conflict_c["median_latency_seconds"], 1e-9) <= gates["treatment_median_latency_ratio_max"],
        "p95_latency": max(conflict_t["p95_latency_seconds"], safe_t["p95_latency_seconds"]) <= gates["treatment_p95_latency_seconds_max"],
        "peak_rss": max(conflict_t["peak_ollama_rss_bytes"], safe_t["peak_ollama_rss_bytes"]) <= gates["peak_ollama_rss_bytes_max"],
    }
    if all(checks.values()):
        return contract["authorizations"]["on_pass"], checks
    failure = contract["failure_rule"]
    if failure["stop_on_any_nonconflict_identity_regression"] and (
        identity["raw_reply_identity_rate"] < 1.0 or identity["gate_decision_identity_rate"] < 1.0
    ):
        return failure["decision"], checks
    if failure["stop_if_conflict_accept_and_semantic_deltas_nonpositive"] and (
        conflict_t["any_gate_accept_rate"] - conflict_c["any_gate_accept_rate"] <= 0
        and conflict_t["selected_clean_semantic_recall"] - conflict_c["selected_clean_semantic_recall"] <= 0
    ):
        return failure["decision"], checks
    return "inconclusive_effect_between_preregistered_gates", checks


def analyze(
    contract,
    packets,
    rows,
    source_checks,
    installed_digest,
    expected_packets,
    gate_recalculation_matches,
):
    sequence = v88.validate_resume_prefix(packets, rows, contract)
    integrity_checks = {
        "sources": all(source_checks.values()),
        "packet_count": len(packets) == int(contract["scope"]["case_count"]),
        "stratum_counts": Counter(packet["stratum"] for packet in packets) == Counter({v88.STRATUM_CONFLICT: 12, v88.STRATUM_NONCONFLICT: 12}),
        "session_coverage": all(
            len({packet["source_session_id"] for packet in packets if packet["stratum"] == stratum}) >= int(contract["selection"]["minimum_sessions_per_stratum"])
            for stratum in (v88.STRATUM_CONFLICT, v88.STRATUM_NONCONFLICT)
        ),
        "packet_recalculation": [packet["packet_sha256"] for packet in packets] == [packet["packet_sha256"] for packet in expected_packets],
        "sequence_complete": len(rows) == len(sequence) == int(contract["scope"]["expected_model_call_count"]),
        "model_digest": installed_digest == contract["model"]["digest"] and all(row.get("model_digest") == contract["model"]["digest"] for row in rows),
        "responses_complete": all(row.get("response_model") == contract["model"]["ollama_tag"] and row.get("done") is True and not row.get("transport_error") for row in rows),
        "resources_complete": all(row.get("prompt_eval_count") is not None and row.get("peak_ollama_rss_bytes") is not None for row in rows),
        "scores_recalculate": all(
            row.get("raw_score") == v88.score_reply(packet, row.get("raw_reply"))
            and row.get("prepared_score") == v88.score_reply(packet, row.get("prepared_reply"))
            for packet in packets
            for row in rows
            if row.get("candidate_id") == packet["candidate_id"]
        ),
        "production_gate_recalculates": gate_recalculation_matches,
        "gate_scope_matches_payload": all(row.get("effective_forbidden_matches_payload") is True for row in rows),
        "no_side_effects": all(row.get("production_memory_write_count") == 0 and row.get("physical_vrm_action_count") == 0 for row in rows),
    }
    integrity = all(integrity_checks.values())
    summaries = {
        stratum: {
            condition: summarize(
                [row for row in rows if row["stratum"] == stratum and row["condition"] == condition]
            )
            for condition in v88.CONDITIONS
        }
        for stratum in (v88.STRATUM_CONFLICT, v88.STRATUM_NONCONFLICT)
    }
    identities = {
        stratum: paired_identity(rows, stratum)
        for stratum in (v88.STRATUM_CONFLICT, v88.STRATUM_NONCONFLICT)
    }
    final_decision, checks = decision(contract, integrity, summaries, identities)
    return {
        "schema": "uruha_rightbrain_forbidden_projection_analysis_v88",
        "experiment_id": contract["experiment_id"],
        "decision": final_decision,
        "integrity_passed": integrity,
        "integrity_checks": integrity_checks,
        "stratum_condition_summaries": summaries,
        "paired_identity": identities,
        "advance_gate_checks": checks,
        "production_shadow_authorized": final_decision == contract["authorizations"]["on_pass"],
        "production_default_enable_authorized": False,
        "training_data_authorized": False,
        "persona_fidelity_claim_authorized": False,
        "evidence_boundary": contract["evidence_boundary"],
    }


def render_markdown(report):
    conflict = report["stratum_condition_summaries"][v88.STRATUM_CONFLICT]
    safe = report["stratum_condition_summaries"][v88.STRATUM_NONCONFLICT]
    identity = report["paired_identity"][v88.STRATUM_NONCONFLICT]
    return "\n".join(
        [
            "# V88 Fresh-Generation Forbidden Projection Holdout",
            "",
            f"- Decision: `{report['decision']}`",
            f"- Integrity: {'PASS' if report['integrity_passed'] else 'FAIL'}",
            "",
            "## Conflict cases (12)",
            "",
            "| Metric | Projection off | Projection on | Delta |",
            "|---|---:|---:|---:|",
            f"| Any production-gate candidate | {conflict[v88.C0]['any_gate_accept_rate']:.1%} | {conflict[v88.T1]['any_gate_accept_rate']:.1%} | {conflict[v88.T1]['any_gate_accept_rate'] - conflict[v88.C0]['any_gate_accept_rate']:+.1%} |",
            f"| Selected semantic recall | {conflict[v88.C0]['selected_clean_semantic_recall']:.1%} | {conflict[v88.T1]['selected_clean_semantic_recall']:.1%} | {conflict[v88.T1]['selected_clean_semantic_recall'] - conflict[v88.C0]['selected_clean_semantic_recall']:+.1%} |",
            f"| Selected surface pass | {conflict[v88.C0]['selected_surface_pass_rate']:.1%} | {conflict[v88.T1]['selected_surface_pass_rate']:.1%} | {conflict[v88.T1]['selected_surface_pass_rate'] - conflict[v88.C0]['selected_surface_pass_rate']:+.1%} |",
            "",
            "## Nonconflict safety cases (12)",
            "",
            f"- Raw reply identity: {identity['raw_reply_identity_rate']:.1%}",
            f"- Gate decision identity: {identity['gate_decision_identity_rate']:.1%}",
            f"- Selected semantic recall: {safe[v88.C0]['selected_clean_semantic_recall']:.1%} -> {safe[v88.T1]['selected_clean_semantic_recall']:.1%}",
            "",
            report["evidence_boundary"],
            "",
        ]
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", type=Path, default=ROOT / "reports/rightbrain_forbidden_projection_v88.json")
    parser.add_argument("--md", type=Path, default=ROOT / "reports/rightbrain_forbidden_projection_v88.md")
    args = parser.parse_args()
    contract = load_json(PREREG_PATH)
    local = {name: ROOT / value for name, value in contract["local_paths"].items()}
    packets = v76.load_jsonl(local["packet_queue"])
    rows = v76.load_jsonl(local["raw_results"])
    source_checks = v88.verify_sources(contract, ROOT)
    with v61._isolated_brain(contract) as (bot, calls, _):
        selected, expected_packets = runner.build_packets(contract, bot.right_brain)
        packets_by_id = {packet["candidate_id"]: packet for packet in packets}
        candidates_by_id = {candidate["id"]: candidate for candidate in selected}
        gate_fields = {
            "prepared_reply",
            "gate_rejection_reasons",
            "gate_accepted",
            "production_candidate_score",
            "effective_forbidden_sha256",
            "effective_forbidden_matches_payload",
            "dropped_marker_count",
            "prepared_score",
        }
        gate_recalculation_matches = all(
            {
                key: value
                for key, value in v88.evaluate_production_gate(
                    bot.right_brain,
                    candidates_by_id[row["candidate_id"]],
                    packets_by_id[row["candidate_id"]],
                    row["condition"],
                    row.get("raw_reply"),
                ).items()
                if key in gate_fields
            }
            == {key: row.get(key) for key in gate_fields}
            for row in rows
        )
    if calls:
        raise SystemExit("V88 analyzer reconstruction unexpectedly called LeftBrain")
    installed = v82.installed_model_digests()
    report = analyze(
        contract,
        packets,
        rows,
        source_checks,
        installed.get(contract["model"]["ollama_tag"]),
        expected_packets,
        gate_recalculation_matches,
    )
    local["local_analysis"].parent.mkdir(parents=True, exist_ok=True)
    local["local_analysis"].write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.md.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps({"decision": report["decision"], "integrity": report["integrity_passed"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
