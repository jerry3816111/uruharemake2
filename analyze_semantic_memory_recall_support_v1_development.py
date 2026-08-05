#!/usr/bin/env python3
"""Analyze the preregistered semantic recall-support development experiment."""

from __future__ import annotations

import json
from pathlib import Path

import analyze_high_confidence_memory_recall_v1_development as recall_v1_analysis
import memory_item_causal_intervention_v1 as mici


ROOT = Path(__file__).resolve().parent
PREREG = ROOT / "configs/semantic_memory_recall_support_v1_preregistration.json"
BASELINE_RAW = ROOT / "analysis/local_memory_item_causal_intervention_v1/raw.jsonl"
RECALL_V1_RAW = ROOT / "analysis/local_high_confidence_memory_recall_v1_development/raw.jsonl"
CANDIDATE_RAW = ROOT / "analysis/local_semantic_memory_recall_support_v1_development/raw.jsonl"
REPORT_JSON = ROOT / "reports/semantic_memory_recall_support_v1_development.json"
REPORT_MD = ROOT / "reports/semantic_memory_recall_support_v1_development.md"


def load_jsonl(path):
    return [
        json.loads(line)
        for line in Path(path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def rate(rows, predicate):
    return sum(bool(predicate(row)) for row in rows) / len(rows) if rows else 0.0


def build_report(baseline_rows, recall_v1_rows, candidate_rows, prereg, metadata):
    baseline = recall_v1_analysis.summarize(baseline_rows)
    recall_v1 = recall_v1_analysis.summarize(recall_v1_rows)
    candidate = recall_v1_analysis.summarize(candidate_rows)
    by_condition = {
        condition: [row for row in candidate_rows if row.get("condition") == condition]
        for condition in mici.CONDITIONS
    }
    gates_spec = prereg["development_gates"]
    target_removed_fast = [
        row
        for row in by_condition[mici.T1]
        if row.get("planner_path") == "high_confidence_memory_recall_v1"
    ]
    valid_fast = [
        row
        for row in candidate_rows
        if row.get("condition") in {mici.C0, mici.T2, mici.N1}
        and row.get("planner_path") == "high_confidence_memory_recall_v1"
    ]
    fast_rows = [
        row
        for row in candidate_rows
        if row.get("planner_path") == "high_confidence_memory_recall_v1"
    ]
    probes = metadata.get("boundary_probes") or {}
    conditions = candidate["conditions"]
    gates = {
        "complete_32_rows": candidate["row_count"]
        == gates_spec["expected_decision_run_count"],
        "intact_target_plan_preserved": conditions[mici.C0]["target_plan_marker_rate"]
        >= gates_spec["intact_target_plan_marker_rate_min"],
        "removed_target_does_not_leak": conditions[mici.T1]["target_plan_marker_rate"]
        <= gates_spec["remove_target_plan_marker_rate_max"],
        "replacement_steers_plan": conditions[mici.T2]["replacement_plan_marker_rate"]
        >= gates_spec["replacement_plan_marker_rate_min"],
        "irrelevant_removal_preserves_target": conditions[mici.N1]["target_plan_marker_rate"]
        >= gates_spec["irrelevant_removed_target_plan_marker_rate_min"],
        "no_target_removed_fast_path": len(target_removed_fast)
        <= gates_spec["target_removed_fast_path_activation_count_max"],
        "valid_fast_path_coverage": len(valid_fast)
        >= gates_spec["valid_condition_fast_path_count_min"],
        "model_call_budget": candidate["leftbrain_model_call_count"]
        <= gates_spec["leftbrain_model_call_count_max"],
        "all_fast_paths_have_support": all(
            int((row.get("memory_recall_contract") or {}).get("shared_focus_unit_count") or 0)
            >= 1
            for row in fast_rows
        ),
        "no_sensitive_fast_path": int(bool((probes.get("sensitive") or {}).get("selected")))
        <= gates_spec["fast_path_sensitive_exposure_count_max"],
        "no_non_recall_fast_path": int(bool((probes.get("non_recall") or {}).get("selected")))
        <= gates_spec["fast_path_non_recall_activation_count_max"],
        "no_ambiguous_fast_path": int(bool((probes.get("ambiguous") or {}).get("selected")))
        <= gates_spec["fast_path_ambiguous_activation_count_max"],
        "boundary_preflight": bool((metadata.get("preflight") or {}).get("passed")),
        "no_transport_errors": not any(
            int(row.get("transport_error_count") or 0) for row in candidate_rows
        ),
        "no_production_writes": not any(
            int(row.get("production_memory_write_count") or 0) for row in candidate_rows
        ),
        "no_vrm_actions": not any(
            int(row.get("physical_vrm_action_count") or 0) for row in candidate_rows
        ),
    }
    return {
        "schema": "uruha_semantic_memory_recall_support_development_result_v1",
        "decision": "development_pass_requires_fresh_holdout"
        if all(gates.values())
        else "development_reject_or_inconclusive",
        "evidence_scope": "known eight-case mechanism fixture only",
        "baseline": baseline,
        "rejected_score_only_v1": recall_v1,
        "candidate": candidate,
        "causal_diagnostics": {
            "target_removed_fast_path_activation_count": len(target_removed_fast),
            "valid_condition_fast_path_count": len(valid_fast),
            "fast_path_support_evidence_rate": rate(
                fast_rows,
                lambda row: int(
                    (row.get("memory_recall_contract") or {}).get(
                        "shared_focus_unit_count"
                    )
                    or 0
                )
                >= 1,
            ),
        },
        "gates": gates,
        "run_metadata": metadata,
        "authorization": {
            "fresh_holdout": all(gates.values()),
            "production_default_enablement": False,
            "benchmark_claim": False,
            "persona_similarity_claim": False,
            "human_memory_equivalence_claim": False,
        },
    }


def markdown(report):
    base = report["baseline"]
    old = report["rejected_score_only_v1"]
    candidate = report["candidate"]
    diag = report["causal_diagnostics"]
    lines = [
        "# Semantic memory recall support V1 development result",
        "",
        f"- Decision: `{report['decision']}`",
        "- Scope: known eight-case mechanism fixture; not fresh generalization evidence.",
        "",
        "| Measure | Original planner | Rejected score-only V1 | Semantic-support V1 |",
        "|---|---:|---:|---:|",
        f"| LeftBrain model calls | {base['leftbrain_model_call_count']} | {old['leftbrain_model_call_count']} | {candidate['leftbrain_model_call_count']} |",
        f"| Fast-path rows | {base['fast_path_count']} | {old['fast_path_count']} | {candidate['fast_path_count']} |",
        f"| Median latency | {base['latency_seconds']['median']:.3f}s | {old['latency_seconds']['median']:.3f}s | {candidate['latency_seconds']['median']:.3f}s |",
        f"| Target-removed false fast paths | 0 | 8 | {diag['target_removed_fast_path_activation_count']} |",
        "",
        "## Causal conditions",
        "",
        "| Condition | Plan marker rate |",
        "|---|---:|",
        f"| Intact target | {candidate['conditions'][mici.C0]['target_plan_marker_rate']:.1%} |",
        f"| Target removed | {candidate['conditions'][mici.T1]['target_plan_marker_rate']:.1%} |",
        f"| Target replaced | {candidate['conditions'][mici.T2]['replacement_plan_marker_rate']:.1%} |",
        f"| Irrelevant removed | {candidate['conditions'][mici.N1]['target_plan_marker_rate']:.1%} |",
        "",
        "## Gates",
        "",
    ]
    lines.extend(
        f"- {name}: {'PASS' if passed else 'FAIL'}"
        for name, passed in report["gates"].items()
    )
    lines.extend(
        [
            "",
            "## Evidence boundary",
            "",
            "A pass authorizes only a disjoint fresh holdout. Production remains disabled.",
        ]
    )
    return "\n".join(lines) + "\n"


def main():
    prereg = json.loads(PREREG.read_text(encoding="utf-8"))
    metadata_path = CANDIDATE_RAW.parent / "run_metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    report = build_report(
        load_jsonl(BASELINE_RAW),
        load_jsonl(RECALL_V1_RAW),
        load_jsonl(CANDIDATE_RAW),
        prereg,
        metadata,
    )
    REPORT_JSON.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    REPORT_MD.write_text(markdown(report), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
