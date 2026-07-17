#!/usr/bin/env python3
"""Analyze the frozen V61 matched RightBrain pipeline shadow."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import statistics
from collections import Counter
from pathlib import Path

from run_rightbrain_pipeline_shadow_v61 import C0, C1, CONDITIONS, T1


ROOT = Path(__file__).resolve().parent
PREREG_PATH = (
    ROOT / "configs" / "rightbrain_pipeline_shadow_v61_preregistration.json"
)
DATASET_PATH = (
    ROOT / "datasets" / "rightbrain_pipeline_shadow_v61.json"
)
LOCK_PATH = (
    ROOT / "configs" / "rightbrain_pipeline_shadow_v61_harness_lock.json"
)
DEFAULT_RAW = (
    ROOT / "reports" / "rightbrain_pipeline_shadow_v61_raw.json"
)
DEFAULT_JSON = (
    ROOT / "reports" / "rightbrain_pipeline_shadow_v61_analysis.json"
)
DEFAULT_MARKDOWN = (
    ROOT / "reports" / "rightbrain_pipeline_shadow_v61_analysis.md"
)


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _ratio(numerator, denominator):
    return numerator / denominator if denominator else 1.0


def _p95(values):
    if not values:
        return 0.0
    ordered = sorted(float(value) for value in values)
    index = max(0, math.ceil(0.95 * len(ordered)) - 1)
    return round(ordered[index], 6)


def _two_sided_exact_mcnemar(fixes, regressions):
    discordant = fixes + regressions
    if discordant == 0:
        return 1.0
    smaller = min(fixes, regressions)
    tail = sum(
        math.comb(discordant, value)
        for value in range(smaller + 1)
    ) / (2**discordant)
    return min(1.0, 2 * tail)


def _paired_counts(control_values, candidate_values):
    if len(control_values) != len(candidate_values):
        raise ValueError("V61 paired vector length mismatch")
    both_pass = 0
    both_fail = 0
    fixes = 0
    regressions = 0
    for control, candidate in zip(
        control_values,
        candidate_values,
    ):
        if control and candidate:
            both_pass += 1
        elif not control and not candidate:
            both_fail += 1
        elif candidate:
            fixes += 1
        else:
            regressions += 1
    return {
        "both_pass": both_pass,
        "both_fail": both_fail,
        "candidate_fixes": fixes,
        "candidate_regressions": regressions,
        "two_sided_exact_mcnemar_p": _two_sided_exact_mcnemar(
            fixes,
            regressions,
        ),
    }


def _bootstrap_delta(control_values, candidate_values, seed, samples):
    if len(control_values) != len(candidate_values):
        raise ValueError("V61 bootstrap vector length mismatch")
    count = len(control_values)
    deltas = []
    rng = random.Random(seed)
    for _ in range(samples):
        indices = [rng.randrange(count) for _ in range(count)]
        control_rate = sum(control_values[index] for index in indices) / count
        candidate_rate = (
            sum(candidate_values[index] for index in indices) / count
        )
        deltas.append(candidate_rate - control_rate)
    deltas.sort()
    lower = deltas[max(0, int(0.025 * samples) - 1)]
    upper = deltas[min(samples - 1, math.ceil(0.975 * samples) - 1)]
    observed = (
        sum(candidate_values) / count
        - sum(control_values) / count
    )
    return {
        "observed_delta": round(observed, 6),
        "bootstrap_samples": samples,
        "bootstrap_seed": seed,
        "ci95": [round(lower, 6), round(upper, 6)],
    }


def _duplicate_rate(normalized_replies):
    values = [
        value
        for value in normalized_replies
        if value
    ]
    if not values:
        return 0.0
    counts = Counter(values)
    duplicate_rows = sum(
        count - 1 for count in counts.values() if count > 1
    )
    return _ratio(duplicate_rows, len(values))


def _control_rows(raw):
    return [
        {
            "case_id": capture["case_id"],
            "scenario_family": capture["scenario_family"],
            "condition": C0,
            "shared_plan_sha256": capture["shared_plan_sha256"],
            "runtime": capture["deterministic_control"]["runtime"],
            "final_score": capture["deterministic_control"]["score"],
        }
        for capture in raw["captures"]
    ]


def _condition_rows(raw, condition):
    return [
        row
        for row in raw["model_rows"]
        if row["condition"] == condition
    ]


def _summarize_final(rows):
    final_scores = [row["final_score"] for row in rows]
    monitors = [
        row["runtime"]["self_monitor_after"] for row in rows
    ]
    required_hits = sum(
        score["required_meaning_hit_count"]
        for score in final_scores
    )
    required_count = sum(
        score["required_meaning_count"]
        for score in final_scores
    )
    forbidden_hits = sum(
        score["forbidden_meaning_hit_count"]
        for score in final_scores
    )
    forbidden_count = sum(
        len(score["forbidden_meaning_propositions"])
        for score in final_scores
    )
    return {
        "case_count": len(rows),
        "semantic_contract_pass_count": sum(
            score["semantic_contract_pass"]
            for score in final_scores
        ),
        "semantic_contract_pass_rate": _ratio(
            sum(
                score["semantic_contract_pass"]
                for score in final_scores
            ),
            len(rows),
        ),
        "surface_gate_pass_count": sum(
            score["current_gate_pass"]
            for score in final_scores
        ),
        "surface_gate_pass_rate": _ratio(
            sum(
                score["current_gate_pass"]
                for score in final_scores
            ),
            len(rows),
        ),
        "meaning_proposition_recall": _ratio(
            required_hits,
            required_count,
        ),
        "forbidden_proposition_violation_rate": _ratio(
            forbidden_hits,
            forbidden_count,
        ),
        "private_memory_intrusion_count": sum(
            score["private_memory_intrusion"]
            for score in final_scores
        ),
        "self_monitor_pass_count": sum(
            not monitor["needs_repair"] for monitor in monitors
        ),
        "self_monitor_pass_rate": _ratio(
            sum(
                not monitor["needs_repair"]
                for monitor in monitors
            ),
            len(monitors),
        ),
        "normalized_duplicate_reply_rate": _duplicate_rate(
            [
                score["normalized_reply"]
                for score in final_scores
            ]
        ),
        "repair_changed_reply_count": sum(
            row["runtime"]["repair_changed_reply"] for row in rows
        ),
    }


def _summarize_model_condition(rows):
    raw_scores = [row["raw_score"] for row in rows]
    required_hits = sum(
        score["required_meaning_hit_count"]
        for score in raw_scores
    )
    required_count = sum(
        score["required_meaning_count"]
        for score in raw_scores
    )
    forbidden_hits = sum(
        score["forbidden_meaning_hit_count"]
        for score in raw_scores
    )
    forbidden_count = sum(
        len(score["forbidden_meaning_propositions"])
        for score in raw_scores
    )
    latencies = [
        row["generation_metrics"]["wall_seconds"]
        for row in rows
    ]
    rss_values = [
        row["peak_ollama_rss_bytes"]
        for row in rows
        if row["peak_ollama_rss_bytes"] is not None
    ]
    return {
        "condition": rows[0]["condition"] if rows else "",
        "raw": {
            "semantic_contract_pass_count": sum(
                score["semantic_contract_pass"]
                for score in raw_scores
            ),
            "semantic_contract_pass_rate": _ratio(
                sum(
                    score["semantic_contract_pass"]
                    for score in raw_scores
                ),
                len(rows),
            ),
            "surface_gate_pass_count": sum(
                score["current_gate_pass"]
                for score in raw_scores
            ),
            "surface_gate_pass_rate": _ratio(
                sum(
                    score["current_gate_pass"]
                    for score in raw_scores
                ),
                len(rows),
            ),
            "meaning_proposition_recall": _ratio(
                required_hits,
                required_count,
            ),
            "forbidden_proposition_violation_rate": _ratio(
                forbidden_hits,
                forbidden_count,
            ),
            "private_memory_intrusion_count": sum(
                score["private_memory_intrusion"]
                for score in raw_scores
            ),
        },
        "strict_takeover_before_self_monitor_count": sum(
            row["strict_takeover_before_self_monitor"]
            for row in rows
        ),
        "model_takeover_count": sum(
            row["model_takeover"] for row in rows
        ),
        "model_takeover_rate": _ratio(
            sum(row["model_takeover"] for row in rows),
            len(rows),
        ),
        "final": _summarize_final(rows),
        "model_latency_median_seconds": round(
            statistics.median(latencies),
            6,
        ),
        "model_latency_p95_seconds": _p95(latencies),
        "peak_ollama_rss_bytes": max(rss_values)
        if rss_values
        else None,
        "transport_error_count": sum(
            bool(row["transport_error"]) for row in rows
        ),
    }


def _artifact_checks(raw, dataset, prereg, lock):
    cases = dataset["cases"]
    case_ids = [case["id"] for case in cases]
    captures = raw["captures"]
    capture_by_id = {
        capture["case_id"]: capture for capture in captures
    }
    rows = raw["model_rows"]
    expected_pairs = {
        (case_id, condition)
        for case_id in case_ids
        for condition in (C1, T1)
    }
    observed_pairs = {
        (row["case_id"], row["condition"]) for row in rows
    }
    calls = raw["logical_model_calls"]
    expected_system_prompt_hash = lock["environment"][
        "rightbrain_system_prompt_sha256"
    ]
    forbidden_payload_keys = {
        "required_meaning_propositions",
        "forbidden_meaning_propositions",
        "expected_obligation",
        "private_memory_terms",
        "case_id",
    }
    payloads = [
        json.loads(capture["model_payload"])
        for capture in captures
    ]
    checks = {
        "experiment_id": (
            raw["experiment_id"] == prereg["experiment_id"]
        ),
        "runner_branch_main": raw["runner_branch"] == "main",
        "condition_order_exact": tuple(raw["conditions"])
        == CONDITIONS,
        "case_count_exact": len(cases)
        == prereg["fresh_dataset"]["case_count"],
        "plan_capture_count_exact": len(captures) == len(cases),
        "plan_capture_ids_exact": set(capture_by_id) == set(case_ids),
        "fixture_retrieval_complete": all(
            set(capture["retrieved_fixture_ids"])
            == set(capture["expected_fixture_ids"])
            for capture in captures
        ),
        "temporary_database_per_capture": all(
            capture["temporary_database"]
            and not capture["production_database_opened"]
            for capture in captures
        ),
        "model_row_pairs_exact": observed_pairs == expected_pairs
        and len(rows) == len(expected_pairs),
        "logical_model_calls_exact": len(calls) == 60
        == raw["logical_model_call_count"],
        "transport_attempts_exact": (
            raw["transport_attempt_count"] == 60
            == sum(call["transport_attempts"] for call in calls)
        ),
        "shared_plan_reused": all(
            row["shared_plan_sha256"]
            == capture_by_id[row["case_id"]]["shared_plan_sha256"]
            for row in rows
        ),
        "shared_payload_reused": all(
            row["model_payload_sha256"]
            == capture_by_id[row["case_id"]][
                "model_payload_sha256"
            ]
            for row in rows
        ),
        "gold_not_passed_to_model": not raw[
            "gold_or_expected_outcome_passed_to_model"
        ],
        "model_payload_has_no_holdout_gold_fields": all(
            not forbidden_payload_keys.intersection(payload)
            for payload in payloads
        ),
        "production_memory_writes_zero": (
            raw["production_memory_write_count"] == 0
            and raw["database_isolation"][
                "production_database_writes"
            ]
            == 0
            and not raw["database_isolation"][
                "production_database_opened"
            ]
        ),
        "physical_vrm_actions_zero": (
            raw["physical_vrm_action_count"] == 0
        ),
        "no_inflight_request": (
            raw["inflight_request_at_completion"] is None
        ),
        "preflight_passed": bool(raw["preflight"]["passed"]),
        "harness_lock_hash": (
            raw["harness_lock_sha256"] == _sha256(LOCK_PATH)
        ),
        "system_prompt_hash": (
            raw["system_prompt_sha256"]
            == expected_system_prompt_hash
        ),
        "ollama_version": (
            raw["ollama_version"]
            == lock["environment"]["ollama_version"]
        ),
    }
    for name, artifact in lock["frozen_artifacts"].items():
        checks[f"artifact_{name}"] = (
            _sha256(ROOT / artifact["path"])
            == artifact["sha256"]
            == raw["frozen_artifact_hashes"][name]
        )
    for condition in (C1, T1):
        frozen = prereg["conditions"][condition]
        observed = raw["model_snapshots"][condition]
        checks[f"model_{condition}"] = (
            observed["ollama_tag"] == frozen["ollama_tag"]
            and observed["digest"] == frozen["digest"]
        )
    return checks


def analyze(raw, dataset, prereg, lock):
    artifact_checks = _artifact_checks(
        raw,
        dataset,
        prereg,
        lock,
    )
    control_rows = _control_rows(raw)
    c1_rows = _condition_rows(raw, C1)
    t1_rows = _condition_rows(raw, T1)
    case_order = [case["id"] for case in dataset["cases"]]

    def ordered(rows):
        by_id = {row["case_id"]: row for row in rows}
        return [by_id[case_id] for case_id in case_order]

    c1_rows = ordered(c1_rows)
    t1_rows = ordered(t1_rows)
    control_rows = ordered(control_rows)
    c0_summary = {
        "condition": C0,
        "final": _summarize_final(control_rows),
    }
    c1_summary = _summarize_model_condition(c1_rows)
    t1_summary = _summarize_model_condition(t1_rows)

    c1_raw_semantic = [
        row["raw_score"]["semantic_contract_pass"]
        for row in c1_rows
    ]
    t1_raw_semantic = [
        row["raw_score"]["semantic_contract_pass"]
        for row in t1_rows
    ]
    c1_raw_surface = [
        row["raw_score"]["current_gate_pass"]
        for row in c1_rows
    ]
    t1_raw_surface = [
        row["raw_score"]["current_gate_pass"]
        for row in t1_rows
    ]
    statistics_report = {
        "raw_semantic_contract": {
            "paired_counts": _paired_counts(
                c1_raw_semantic,
                t1_raw_semantic,
            ),
            "bootstrap": _bootstrap_delta(
                c1_raw_semantic,
                t1_raw_semantic,
                prereg["generation"]["seed"],
                lock["statistics"]["bootstrap_samples"],
            ),
        },
        "raw_surface_gate": {
            "paired_counts": _paired_counts(
                c1_raw_surface,
                t1_raw_surface,
            ),
            "bootstrap": _bootstrap_delta(
                c1_raw_surface,
                t1_raw_surface,
                prereg["generation"]["seed"] + 1,
                lock["statistics"]["bootstrap_samples"],
            ),
        },
    }

    gates = prereg["automatic_advance_gates"]
    peak_rss = t1_summary["peak_ollama_rss_bytes"]
    checks = {
        "all_hash_shape_freshness_and_plan_capture_checks_pass": all(
            artifact_checks.values()
        ),
        "t1_raw_semantic_contract_pass_rate_at_least": (
            t1_summary["raw"]["semantic_contract_pass_rate"]
            >= gates[
                "t1_raw_semantic_contract_pass_rate_at_least"
            ]
        ),
        "t1_raw_surface_gate_pass_rate_at_least": (
            t1_summary["raw"]["surface_gate_pass_rate"]
            >= gates["t1_raw_surface_gate_pass_rate_at_least"]
        ),
        "t1_raw_meaning_proposition_recall_at_least": (
            t1_summary["raw"]["meaning_proposition_recall"]
            >= gates[
                "t1_raw_meaning_proposition_recall_at_least"
            ]
        ),
        "t1_raw_forbidden_proposition_violation_rate_at_most": (
            t1_summary["raw"][
                "forbidden_proposition_violation_rate"
            ]
            <= gates[
                "t1_raw_forbidden_proposition_violation_rate_at_most"
            ]
        ),
        "t1_raw_private_memory_intrusion_count": (
            t1_summary["raw"]["private_memory_intrusion_count"]
            == gates["t1_raw_private_memory_intrusion_count"]
        ),
        "t1_model_takeover_rate_at_least": (
            t1_summary["model_takeover_rate"]
            >= gates["t1_model_takeover_rate_at_least"]
        ),
        "t1_final_semantic_contract_pass_rate_at_least": (
            t1_summary["final"]["semantic_contract_pass_rate"]
            >= gates[
                "t1_final_semantic_contract_pass_rate_at_least"
            ]
        ),
        "t1_final_surface_gate_pass_rate_at_least": (
            t1_summary["final"]["surface_gate_pass_rate"]
            >= gates[
                "t1_final_surface_gate_pass_rate_at_least"
            ]
        ),
        "t1_final_self_monitor_pass_rate_at_least": (
            t1_summary["final"]["self_monitor_pass_rate"]
            >= gates[
                "t1_final_self_monitor_pass_rate_at_least"
            ]
        ),
        "t1_final_duplicate_rate_not_higher_than_c0": (
            t1_summary["final"][
                "normalized_duplicate_reply_rate"
            ]
            <= c0_summary["final"][
                "normalized_duplicate_reply_rate"
            ]
        ),
        "t1_raw_semantic_delta_vs_c1_at_least": (
            t1_summary["raw"]["semantic_contract_pass_rate"]
            - c1_summary["raw"]["semantic_contract_pass_rate"]
            >= gates["t1_raw_semantic_delta_vs_c1_at_least"]
        ),
        "t1_raw_surface_delta_vs_c1_at_least": (
            t1_summary["raw"]["surface_gate_pass_rate"]
            - c1_summary["raw"]["surface_gate_pass_rate"]
            >= gates["t1_raw_surface_delta_vs_c1_at_least"]
        ),
        "t1_model_latency_median_seconds_at_most": (
            t1_summary["model_latency_median_seconds"]
            <= gates["t1_model_latency_median_seconds_at_most"]
        ),
        "t1_model_latency_p95_seconds_at_most": (
            t1_summary["model_latency_p95_seconds"]
            <= gates["t1_model_latency_p95_seconds_at_most"]
        ),
        "t1_peak_ollama_rss_bytes_at_most": (
            peak_rss is not None
            and peak_rss
            <= gates["t1_peak_ollama_rss_bytes_at_most"]
        ),
        "logical_model_call_count_exact": (
            raw["logical_model_call_count"]
            == gates["logical_model_call_count_exact"]
        ),
        "transport_error_count_exact": (
            raw["transport_error_count"]
            == gates["transport_error_count_exact"]
        ),
        "production_memory_write_count_exact": (
            raw["production_memory_write_count"]
            == gates["production_memory_write_count_exact"]
        ),
        "physical_vrm_action_count_exact": (
            raw["physical_vrm_action_count"]
            == gates["physical_vrm_action_count_exact"]
        ),
    }
    passed = all(checks.values())
    return {
        "schema": "uruha_rightbrain_pipeline_shadow_analysis_v61",
        "experiment_id": prereg["experiment_id"],
        "evidence_boundary": prereg["causal_boundary"],
        "artifact_checks": artifact_checks,
        "condition_summaries": {
            C0: c0_summary,
            C1: c1_summary,
            T1: t1_summary,
        },
        "paired_statistics": statistics_report,
        "automatic_gates": {
            "passed": passed,
            "checks": checks,
            "failed_checks": [
                name for name, value in checks.items() if not value
            ],
        },
        "decision": (
            "authorize_preregistered_human_blind_stage"
            if passed
            else "freeze_negative_result_and_stop_v61_hypothesis"
        ),
        "human_blind_review_authorized": passed,
        "runtime_shadow_authorized": False,
        "production_rightbrain_replacement_authorized": False,
        "broad_human_likeness_claim_authorized": False,
    }


def _pct(value):
    return f"{value:.1%}"


def render_markdown(report):
    summaries = report["condition_summaries"]
    c0 = summaries[C0]["final"]
    c1 = summaries[C1]
    t1 = summaries[T1]
    return "\n".join(
        [
            "# V61 matched RightBrain pipeline shadow",
            "",
            "All three conditions reused one captured LeftBrain plan per case. "
            "No production memory or VRM action was used.",
            "",
            "| Metric | Current deterministic | Qwen2.5 7B | Qwen3.5 9B |",
            "|---|---:|---:|---:|",
            f"| Raw plan-semantic pass | n/a | {_pct(c1['raw']['semantic_contract_pass_rate'])} | {_pct(t1['raw']['semantic_contract_pass_rate'])} |",
            f"| Raw surface-gate pass | n/a | {_pct(c1['raw']['surface_gate_pass_rate'])} | {_pct(t1['raw']['surface_gate_pass_rate'])} |",
            f"| Raw holdout meaning recall | n/a | {_pct(c1['raw']['meaning_proposition_recall'])} | {_pct(t1['raw']['meaning_proposition_recall'])} |",
            f"| Final plan-semantic pass | {_pct(c0['semantic_contract_pass_rate'])} | {_pct(c1['final']['semantic_contract_pass_rate'])} | {_pct(t1['final']['semantic_contract_pass_rate'])} |",
            f"| Model takeover | n/a | {_pct(c1['model_takeover_rate'])} | {_pct(t1['model_takeover_rate'])} |",
            f"| Final duplicate rate | {_pct(c0['normalized_duplicate_reply_rate'])} | {_pct(c1['final']['normalized_duplicate_reply_rate'])} | {_pct(t1['final']['normalized_duplicate_reply_rate'])} |",
            f"| Median model latency | n/a | {c1['model_latency_median_seconds']:.3f}s | {t1['model_latency_median_seconds']:.3f}s |",
            f"| P95 model latency | n/a | {c1['model_latency_p95_seconds']:.3f}s | {t1['model_latency_p95_seconds']:.3f}s |",
            "",
            f"- Automatic gate: {'PASS' if report['automatic_gates']['passed'] else 'FAIL'}",
            f"- Decision: `{report['decision']}`",
            f"- Failed checks: {', '.join(report['automatic_gates']['failed_checks']) or 'none'}",
            "",
            "This result estimates only RightBrain realization after one shared "
            "cognitive-plan capture. It does not establish whole-system human likeness.",
            "",
        ]
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", type=Path, default=DEFAULT_RAW)
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    parser.add_argument(
        "--markdown",
        type=Path,
        default=DEFAULT_MARKDOWN,
    )
    args = parser.parse_args()
    report = analyze(
        _load(args.raw),
        _load(DATASET_PATH),
        _load(PREREG_PATH),
        _load(LOCK_PATH),
    )
    args.json.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    args.markdown.write_text(
        render_markdown(report),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "decision": report["decision"],
                "automatic_gate_passed": report[
                    "automatic_gates"
                ]["passed"],
                "failed_checks": report["automatic_gates"][
                    "failed_checks"
                ],
                "human_blind_review_authorized": report[
                    "human_blind_review_authorized"
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
