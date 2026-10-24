#!/usr/bin/env python3
"""Run the frozen M3 structured-memory mechanism and single-component ablations."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import sys
from typing import Any

from longitudinal_human_model.memory import (
    COMPONENTS,
    MemoryQuery,
    MemoryRecord,
    MemoryStrengthConfig,
    retrieve_memories,
)
from longitudinal_human_model.registry import (
    git_snapshot,
    load_json,
    runtime_snapshot,
    sha256_file,
    verify_lock,
    write_json_atomic,
)


REPO_ROOT = Path(__file__).resolve().parent


def validate_fixture(dataset: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    if dataset.get("authorizations", {}).get("formal_target_claim") is not False:
        errors.append("dataset must explicitly refuse formal_target_claim")
    if dataset.get("authorizations", {}).get("mechanism_execution") is not True:
        errors.append("dataset does not authorize mechanism execution")
    if config.get("formal_target_claim") is not False:
        errors.append("config must explicitly refuse formal_target_claim")
    records_raw = dataset.get("records")
    queries_raw = dataset.get("queries")
    if not isinstance(records_raw, list) or not isinstance(queries_raw, list):
        errors.append("dataset requires records and queries arrays")
        records_raw = records_raw if isinstance(records_raw, list) else []
        queries_raw = queries_raw if isinstance(queries_raw, list) else []
    record_ids = [row.get("memory_id") for row in records_raw if isinstance(row, dict)]
    query_ids = [row.get("query_id") for row in queries_raw if isinstance(row, dict)]
    if len(record_ids) != len(set(record_ids)):
        errors.append("memory_id values must be unique")
    if len(query_ids) != len(set(query_ids)):
        errors.append("query_id values must be unique")
    try:
        records = [MemoryRecord.from_dict(row) for row in records_raw]
        queries = [MemoryQuery.from_dict(row) for row in queries_raw]
        MemoryStrengthConfig.from_dict(config["memory_strength"])
    except (KeyError, TypeError, ValueError) as exc:
        errors.append(f"schema validation failed: {exc}")
        records = []
        queries = []
    known = {record.memory_id for record in records}
    for row in queries_raw:
        relevant = row.get("relevant_memory_ids") if isinstance(row, dict) else None
        if not isinstance(relevant, list) or not relevant:
            errors.append(f"{row.get('query_id')}: relevant_memory_ids must be non-empty")
            continue
        unknown = sorted(set(relevant) - known)
        if unknown:
            errors.append(f"{row.get('query_id')}: unknown relevant memories {unknown}")
    contract = config.get("success_contract") or {}
    if len(records_raw) != int(contract.get("record_count") or -1):
        errors.append("record_count does not match success contract")
    if len(queries_raw) != int(contract.get("query_count") or -1):
        errors.append("query_count does not match success contract")
    ablations = config.get("ablations")
    expected_ablations = ["none", *COMPONENTS]
    if ablations != expected_ablations:
        errors.append(f"ablations must be exactly {expected_ablations}")
    return {
        "valid": not errors,
        "errors": errors,
        "record_count": len(records_raw),
        "query_count": len(queries_raw),
        "parsed_record_count": len(records),
        "parsed_query_count": len(queries),
    }


def _condition_metrics(rows: list[dict[str, Any]], *, top_k: int) -> dict[str, Any]:
    precisions = []
    recalls = []
    reciprocal_ranks = []
    for row in rows:
        relevant = set(row["relevant_memory_ids"])
        selected = row["selected_memory_ids"]
        hits = len(relevant & set(selected))
        precisions.append(hits / top_k)
        recalls.append(hits / len(relevant))
        ranked = row["eligible_ranked_memory_ids"]
        first_rank = next((index + 1 for index, item in enumerate(ranked) if item in relevant), None)
        reciprocal_ranks.append(1.0 / first_rank if first_rank else 0.0)
    return {
        "query_count": len(rows),
        "precision_at_k": sum(precisions) / len(precisions),
        "recall_at_k": sum(recalls) / len(recalls),
        "mean_reciprocal_rank": sum(reciprocal_ranks) / len(reciprocal_ranks),
    }


def run_memory_ablation(dataset: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    validation = validate_fixture(dataset, config)
    if not validation["valid"]:
        raise ValueError("invalid M3 fixture: " + "; ".join(validation["errors"]))
    records = [MemoryRecord.from_dict(row) for row in dataset["records"]]
    query_rows = {row["query_id"]: row for row in dataset["queries"]}
    queries = [MemoryQuery.from_dict(row) for row in dataset["queries"]]
    strength = MemoryStrengthConfig.from_dict(config["memory_strength"])
    top_k = int(config["retrieval"]["top_k"])
    conditions: dict[str, dict[str, Any]] = {}
    full_rankings: dict[str, list[str]] = {}
    full_scores: dict[tuple[str, str], float] = {}

    for condition in config["ablations"]:
        ablate = () if condition == "none" else (condition,)
        rows = []
        for query in queries:
            trace = retrieve_memories(records, query, strength, top_k=top_k, ablate=ablate)
            relevant = list(query_rows[query.query_id]["relevant_memory_ids"])
            selected_ids = [row["memory_id"] for row in trace["selected"]]
            ranked_ids = [row["memory_id"] for row in trace["eligible_ranked"]]
            rows.append(
                {
                    "query_id": query.query_id,
                    "relevant_memory_ids": relevant,
                    "selected_memory_ids": selected_ids,
                    "eligible_ranked_memory_ids": ranked_ids,
                    "selected": trace["selected"],
                    "excluded": trace["excluded"],
                }
            )
            if condition == "none":
                full_rankings[query.query_id] = ranked_ids
                for candidate in trace["eligible_ranked"]:
                    full_scores[(query.query_id, candidate["memory_id"])] = candidate["score"]
        metrics = _condition_metrics(rows, top_k=top_k)
        if condition == "none":
            metrics["rank_order_changed_queries"] = 0
            metrics["selected_set_changed_queries"] = 0
            metrics["mean_absolute_score_delta_from_full"] = 0.0
        else:
            rank_changes = 0
            selected_changes = 0
            score_deltas = []
            full_rows = {row["query_id"]: row for row in conditions["none"]["rows"]}
            for row in rows:
                query_id = row["query_id"]
                if row["eligible_ranked_memory_ids"] != full_rankings[query_id]:
                    rank_changes += 1
                if set(row["selected_memory_ids"]) != set(full_rows[query_id]["selected_memory_ids"]):
                    selected_changes += 1
                for candidate in row["selected"]:
                    score_deltas.append(
                        abs(
                            candidate["score"]
                            - full_scores[(query_id, candidate["memory_id"])]
                        )
                    )
            metrics["rank_order_changed_queries"] = rank_changes
            metrics["selected_set_changed_queries"] = selected_changes
            metrics["mean_absolute_score_delta_from_full"] = (
                sum(score_deltas) / len(score_deltas) if score_deltas else 0.0
            )
        conditions[condition] = {"metrics": metrics, "rows": rows}

    full_rows = conditions["none"]["rows"]
    selected_ids = [item for row in full_rows for item in row["selected_memory_ids"]]
    future_selected = selected_ids.count("m13_future")
    expired_selected = selected_ids.count("m14_expired")
    observed_component_nonzero = {
        component: any(
            candidate["contributions"][component] > 0
            for row in full_rows
            for candidate in row["selected"]
        )
        for component in COMPONENTS
    }
    any_ablation_effect = any(
        payload["metrics"]["rank_order_changed_queries"] > 0
        or payload["metrics"]["mean_absolute_score_delta_from_full"] > 0
        for name, payload in conditions.items()
        if name != "none"
    )
    contract = config["success_contract"]
    gates = {
        "query_count": len(queries) == int(contract["query_count"]),
        "record_count": len(records) == int(contract["record_count"]),
        "full_condition_recall_at_2": math.isclose(
            conditions["none"]["metrics"]["recall_at_k"],
            float(contract["full_condition_recall_at_2"]),
        ),
        "future_memory_selected_count": future_selected
        == int(contract["future_memory_selected_count"]),
        "expired_memory_selected_count": expired_selected
        == int(contract["expired_memory_selected_count"]),
        "all_components_have_nonzero_observed_contribution": all(
            observed_component_nonzero.values()
        ),
        "at_least_one_single_component_ablation_changes_a_rank_or_score": any_ablation_effect,
    }
    return {
        "schema": "ilhdt_m3_memory_result_v1",
        "status": "complete_mechanism_run" if all(gates.values()) else "failed_mechanism_gate",
        "claim_level": config["claim_level"],
        "formal_target_claim": False,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "dataset_id": dataset["dataset_id"],
        "semantic_relevance_provider": config["semantic_relevance_provider"],
        "parameters_not_fitted": bool(config["parameters_not_fitted"]),
        "memory_strength": config["memory_strength"],
        "validation": validation,
        "conditions": conditions,
        "gate_checks": gates,
        "gate_pass": all(gates.values()),
        "observed_component_nonzero": observed_component_nonzero,
        "future_memory_selected_count": future_selected,
        "expired_memory_selected_count": expired_selected,
        "limitations": [
            "All records and relevance labels are synthetic and author-designed.",
            "The lexical semantic proxy is not a learned semantic representation.",
            "Equal weights are not estimated person parameters.",
            "This memory-only mechanism run does not test behavior prediction lift.",
            "No Uruha or other real-person claim is authorized.",
        ],
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("validate", "run"), default="validate")
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--lock", required=True)
    parser.add_argument("--output")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    dataset_path = (REPO_ROOT / args.dataset).resolve()
    config_path = (REPO_ROOT / args.config).resolve()
    lock_path = (REPO_ROOT / args.lock).resolve()
    dataset = load_json(dataset_path)
    config = load_json(config_path)
    lock = load_json(lock_path)
    fixture_validation = validate_fixture(dataset, config)
    lock_errors = verify_lock(lock, repo_root=REPO_ROOT)
    validation = {
        "schema": "ilhdt_m3_validation_v1",
        "valid": fixture_validation["valid"] and not lock_errors,
        "fixture": fixture_validation,
        "lock_errors": lock_errors,
        "dataset_sha256": sha256_file(dataset_path),
        "config_sha256": sha256_file(config_path),
        "lock_sha256": sha256_file(lock_path),
    }
    if args.mode == "validate":
        print(json.dumps(validation, ensure_ascii=False, indent=2, sort_keys=True))
        return 0 if validation["valid"] else 2
    if not validation["valid"]:
        raise SystemExit("M3 frozen validation failed")
    if not args.output:
        raise SystemExit("--output is required in run mode")
    result = run_memory_ablation(dataset, config)
    result["experiment_lock"] = lock
    result["environment"] = runtime_snapshot()
    result["git"] = git_snapshot(REPO_ROOT)
    output_path = (REPO_ROOT / args.output).resolve()
    write_json_atomic(output_path, result)
    print(json.dumps({"output": str(output_path), "status": result["status"]}, indent=2))
    return 0 if result["gate_pass"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
