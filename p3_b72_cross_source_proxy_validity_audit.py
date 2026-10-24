"""B72 read-only cross-source validity audit for the exposed caption-marker proxy."""

from __future__ import annotations

from copy import deepcopy
import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "p3_b72_cross_source_proxy_validity_audit_v1.json"
FREEZE_PATH = ROOT / "research" / "p3_b72_cross_source_proxy_validity_audit_implementation_freeze_2026-09-20.json"
CONDITIONS = ("BASELINE_LITERAL", "SYSTEM_PRAGMATIC_STATE")


class B72Error(RuntimeError):
    pass


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(path: str | Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise B72Error(f"not_object:{path}")
    return value


def load_contract() -> dict[str, Any]:
    return load_json(CONFIG_PATH)


def validate_contract(contract: dict[str, Any] | None = None, *, root: Path = ROOT) -> dict[str, Any]:
    contract = deepcopy(contract or load_contract())
    errors: list[str] = []
    if contract.get("schema") != "uruha_p3_b72_cross_source_proxy_validity_audit_contract_v1":
        errors.append("schema")
    if contract.get("status") != "post_result_diagnostic_audit_frozen_before_execution_not_preregistered_effect_test":
        errors.append("status")
    for name, binding in (contract.get("bindings") or {}).items():
        path = Path(root) / str(binding.get("path") or "")
        if not path.is_file():
            errors.append(f"binding_missing:{name}")
        elif sha256_file(path) != binding.get("sha256"):
            errors.append(f"binding_hash:{name}")
    expected_sources = [
        {"source_key": "source1", "source_id": "youtube_4y5GiQpgJgo", "row_count": 4},
        {"source_key": "source3", "source_id": "youtube_j6Hlk9cY9LQ", "row_count": 4},
    ]
    if contract.get("sources") != expected_sources:
        errors.append("sources")
    diagnostics = contract.get("diagnostics") or {}
    if diagnostics.get("minimum_distinct_actual_labels_per_source") != 2:
        errors.append("minimum_label_diversity")
    if diagnostics.get("require_nonzero_marker_hit_per_source") is not True:
        errors.append("marker_requirement")
    if diagnostics.get("require_primary_metric_direction_agreement") is not True:
        errors.append("direction_requirement")
    if diagnostics.get("primary_metrics") != [
        "row_wins", "mean_actual_label_probability", "mean_multiclass_brier", "mean_log_loss", "top1_hits"
    ]:
        errors.append("primary_metrics")
    limits = contract.get("execution_limits") or {}
    if set(limits) != {
        "network_access_count", "new_source_or_future_access_count", "model_human_or_llm_judge_call_count",
        "prediction_mutation_count", "training_or_production_memory_write_count",
    } or any(value != 0 for value in limits.values()):
        errors.append("execution_limits")
    decision = contract.get("decision") or {}
    if decision.get("adequate_only_if_all_diagnostics_pass") is not True or decision.get("source_expansion_allowed_on_failure") is not False:
        errors.append("decision")
    return {"valid": not errors, "errors": errors}


def validate_implementation_freeze(*, root: Path = ROOT) -> dict[str, Any]:
    freeze_path = Path(root) / FREEZE_PATH.relative_to(ROOT)
    freeze = load_json(freeze_path)
    errors = []
    if freeze.get("status") != "frozen_before_b72_read_only_audit_execution":
        errors.append("status")
    for name, artifact in (freeze.get("frozen_artifacts") or {}).items():
        path = Path(root) / artifact["path"]
        if not path.is_file() or sha256_file(path) != artifact.get("sha256"):
            errors.append(name)
    if errors:
        raise B72Error("freeze:" + ";".join(errors))
    return {"valid": True}


def _condition_scores(rows: list[dict[str, Any]], condition: str) -> list[dict[str, Any]]:
    scores = []
    for row in rows:
        matches = [score for score in row.get("scores", []) if score.get("condition") == condition]
        if len(matches) != 1:
            raise B72Error(f"condition_score_count:{row.get('row_id')}:{condition}")
        scores.append(matches[0])
    return scores


def _favored_direction(baseline: float, system: float, *, lower_is_better: bool = False) -> str:
    if baseline == system:
        return "TIE"
    system_better = system < baseline if lower_is_better else system > baseline
    return "SYSTEM_PRAGMATIC_STATE" if system_better else "BASELINE_LITERAL"


def _source_summary(source_key: str, source_id: str, result: dict[str, Any], expected_rows: int) -> dict[str, Any]:
    rows = result.get("rows")
    if result.get("status") != "aggregate_scored" or not isinstance(rows, list) or len(rows) != expected_rows:
        raise B72Error(f"invalid_source_result:{source_key}")
    baseline_scores = _condition_scores(rows, "BASELINE_LITERAL")
    system_scores = _condition_scores(rows, "SYSTEM_PRAGMATIC_STATE")
    distinct_labels = sorted({str(row.get("actual_proxy_label")) for row in rows})
    marker_hits = sum(row.get("matched_proxy_marker") is not None for row in rows)
    row_wins = {
        condition: sum(row.get("proxy_winner") == condition for row in rows)
        for condition in (*CONDITIONS, "TIE")
    }
    means = {}
    for condition, scores in zip(CONDITIONS, (baseline_scores, system_scores), strict=True):
        means[condition] = {
            "mean_actual_label_probability": round(sum(float(score["actual_label_probability"]) for score in scores) / len(scores), 12),
            "mean_multiclass_brier": round(sum(float(score["multiclass_brier"]) for score in scores) / len(scores), 12),
            "mean_log_loss": round(sum(float(score["log_loss"]) for score in scores) / len(scores), 12),
            "top1_hits": sum(bool(score["selected_label_hit"]) for score in scores),
        }
    directions = {
        "row_wins": _favored_direction(row_wins["BASELINE_LITERAL"], row_wins["SYSTEM_PRAGMATIC_STATE"]),
        "mean_actual_label_probability": _favored_direction(means["BASELINE_LITERAL"]["mean_actual_label_probability"], means["SYSTEM_PRAGMATIC_STATE"]["mean_actual_label_probability"]),
        "mean_multiclass_brier": _favored_direction(means["BASELINE_LITERAL"]["mean_multiclass_brier"], means["SYSTEM_PRAGMATIC_STATE"]["mean_multiclass_brier"], lower_is_better=True),
        "mean_log_loss": _favored_direction(means["BASELINE_LITERAL"]["mean_log_loss"], means["SYSTEM_PRAGMATIC_STATE"]["mean_log_loss"], lower_is_better=True),
        "top1_hits": _favored_direction(means["BASELINE_LITERAL"]["top1_hits"], means["SYSTEM_PRAGMATIC_STATE"]["top1_hits"]),
    }
    return {
        "source_key": source_key,
        "source_id": source_id,
        "row_count": len(rows),
        "distinct_actual_labels": distinct_labels,
        "distinct_actual_label_count": len(distinct_labels),
        "marker_hit_count": marker_hits,
        "marker_hit_rate": round(marker_hits / len(rows), 12),
        "row_wins": row_wins,
        "condition_metrics": means,
        "metric_directions": directions,
    }


def audit(contract: dict[str, Any] | None = None, *, root: Path = ROOT) -> dict[str, Any]:
    contract = contract or load_contract()
    validation = validate_contract(contract, root=root)
    if not validation["valid"]:
        raise B72Error("contract:" + ";".join(validation["errors"]))
    summaries = []
    for source in contract["sources"]:
        binding = contract["bindings"][f"{source['source_key']}_result"]
        result = load_json(Path(root) / binding["path"])
        summaries.append(_source_summary(source["source_key"], source["source_id"], result, source["row_count"]))

    total_rows = sum(summary["row_count"] for summary in summaries)
    aggregate_metrics: dict[str, Any] = {}
    for condition in CONDITIONS:
        aggregate_metrics[condition] = {
            "mean_actual_label_probability": round(sum(summary["condition_metrics"][condition]["mean_actual_label_probability"] * summary["row_count"] for summary in summaries) / total_rows, 12),
            "mean_multiclass_brier": round(sum(summary["condition_metrics"][condition]["mean_multiclass_brier"] * summary["row_count"] for summary in summaries) / total_rows, 12),
            "mean_log_loss": round(sum(summary["condition_metrics"][condition]["mean_log_loss"] * summary["row_count"] for summary in summaries) / total_rows, 12),
            "top1_hits": sum(summary["condition_metrics"][condition]["top1_hits"] for summary in summaries),
        }
    aggregate_wins = {
        condition: sum(summary["row_wins"][condition] for summary in summaries)
        for condition in (*CONDITIONS, "TIE")
    }
    aggregate_directions = {
        "row_wins": _favored_direction(aggregate_wins["BASELINE_LITERAL"], aggregate_wins["SYSTEM_PRAGMATIC_STATE"]),
        "mean_actual_label_probability": _favored_direction(aggregate_metrics["BASELINE_LITERAL"]["mean_actual_label_probability"], aggregate_metrics["SYSTEM_PRAGMATIC_STATE"]["mean_actual_label_probability"]),
        "mean_multiclass_brier": _favored_direction(aggregate_metrics["BASELINE_LITERAL"]["mean_multiclass_brier"], aggregate_metrics["SYSTEM_PRAGMATIC_STATE"]["mean_multiclass_brier"], lower_is_better=True),
        "mean_log_loss": _favored_direction(aggregate_metrics["BASELINE_LITERAL"]["mean_log_loss"], aggregate_metrics["SYSTEM_PRAGMATIC_STATE"]["mean_log_loss"], lower_is_better=True),
        "top1_hits": _favored_direction(aggregate_metrics["BASELINE_LITERAL"]["top1_hits"], aggregate_metrics["SYSTEM_PRAGMATIC_STATE"]["top1_hits"]),
    }
    failures = []
    minimum_labels = contract["diagnostics"]["minimum_distinct_actual_labels_per_source"]
    for summary in summaries:
        if summary["distinct_actual_label_count"] < minimum_labels:
            failures.append(f"label_diversity:{summary['source_key']}")
        if contract["diagnostics"]["require_nonzero_marker_hit_per_source"] and summary["marker_hit_count"] == 0:
            failures.append(f"marker_hit:{summary['source_key']}")
    non_tie_directions = {direction for direction in aggregate_directions.values() if direction != "TIE"}
    if contract["diagnostics"]["require_primary_metric_direction_agreement"] and len(non_tie_directions) > 1:
        failures.append("aggregate_metric_direction_conflict")
    reversals = []
    for metric in contract["diagnostics"]["primary_metrics"]:
        directions = [summary["metric_directions"][metric] for summary in summaries]
        non_ties = {direction for direction in directions if direction != "TIE"}
        if len(non_ties) > 1:
            reversals.append(metric)
    if reversals:
        failures.append("source_direction_reversal")

    status = contract["decision"]["failure_status"] if failures else contract["decision"]["success_status"]
    result = {
        "schema": "uruha_p3_b72_cross_source_proxy_validity_audit_result_v1",
        "version": "1.0.0",
        "status": status,
        "audit_is_post_result_not_preregistered_effect_test": True,
        "source_summaries": summaries,
        "cross_source_aggregate": {
            "row_count": total_rows,
            "row_wins": aggregate_wins,
            "condition_metrics": aggregate_metrics,
            "metric_directions": aggregate_directions,
        },
        "source_direction_reversal_metrics": reversals,
        "diagnostic_failures": failures,
        "source_expansion_authorized": False if failures else None,
        "network_access_count": 0,
        "new_source_or_future_access_count": 0,
        "model_human_or_llm_judge_call_count": 0,
        "prediction_mutation_count": 0,
        "training_or_production_memory_write_count": 0,
        "claim_boundary": contract["claim_boundary"],
    }
    result["result_hash"] = sha256_bytes(canonical_json(result).encode("utf-8"))
    return result


def validate_result(result: dict[str, Any]) -> dict[str, Any]:
    errors = []
    if result.get("schema") != "uruha_p3_b72_cross_source_proxy_validity_audit_result_v1":
        errors.append("schema")
    if result.get("status") not in {
        "proxy_not_adequate_for_system_advantage_claim",
        "proxy_diagnostics_pass_but_effect_still_not_established",
    }:
        errors.append("status")
    if len(result.get("source_summaries") or []) != 2 or (result.get("cross_source_aggregate") or {}).get("row_count") != 8:
        errors.append("scope")
    for field in (
        "network_access_count", "new_source_or_future_access_count", "model_human_or_llm_judge_call_count",
        "prediction_mutation_count", "training_or_production_memory_write_count",
    ):
        if result.get(field) != 0:
            errors.append(field)
    candidate = deepcopy(result)
    expected_hash = candidate.pop("result_hash", None)
    if expected_hash != sha256_bytes(canonical_json(candidate).encode("utf-8")):
        errors.append("result_hash")
    return {"valid": not errors, "errors": errors}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate-contract", action="store_true")
    parser.add_argument("--validate-freeze", action="store_true")
    parser.add_argument("--run", action="store_true")
    args = parser.parse_args()
    if args.validate_contract:
        output = validate_contract()
    elif args.validate_freeze:
        output = validate_implementation_freeze()
    elif args.run:
        validate_implementation_freeze()
        output = audit()
        result_validation = validate_result(output)
        if not result_validation["valid"]:
            raise B72Error("result:" + ";".join(result_validation["errors"]))
    else:
        parser.error("choose one action")
    print(json.dumps(output, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
