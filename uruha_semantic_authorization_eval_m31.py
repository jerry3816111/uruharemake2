"""M31 development replay and sealed reserve evaluation harness."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import uruha_literal_topic_fidelity_m30 as m30


ROOT = Path(__file__).resolve().parent
DEFAULT_RESERVE_PROTOCOL = ROOT / "research/m31_semantic_authorization_reserve_protocol.json"
DEFAULT_RESERVE_OUTPUT = ROOT / "analysis/m31_semantic_authorization_reserve_raw_2026-08-25.json"
DEFAULT_REPLAY_OUTPUT = ROOT / "analysis/m31_m30_development_replay_raw_2026-08-25.json"


def _sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_dataset_protocol(protocol_path, dataset_key):
    protocol_path = Path(protocol_path)
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    spec = protocol[dataset_key]
    dataset_path = ROOT / spec["path"]
    if _sha256(dataset_path) != spec["sha256"]:
        raise ValueError(f"{dataset_key} hash mismatch")
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    cases = dataset.get("cases") or []
    if len(cases) != int(spec["case_count"]):
        raise ValueError(f"{dataset_key} case count mismatch")
    return protocol, dataset, protocol_path, dataset_path


def _rate(a, b):
    return round(a / b, 4) if b else None


def _p95(values):
    if not values:
        return None
    ordered = sorted(values)
    return round(float(ordered[max(0, math.ceil(len(ordered) * 0.95) - 1)]), 4)


def summarize(rows, gates):
    valid = [row for row in rows if row["authority_expected"]]
    incomplete = [row for row in rows if not row["authority_expected"]]
    counts = Counter(row["outcome"] for row in rows)
    by_language = {}
    for language in ("zh", "en", "ja"):
        subset = [row for row in valid if row["language"] == language]
        faithful = sum(row["outcome"] == "faithful_authority" for row in subset)
        by_language[language] = {
            "valid_count": len(subset),
            "faithful_count": faithful,
            "faithful_rate": _rate(faithful, len(subset)),
        }
    negation = [row for row in valid if row["expected_polarity"] == "negated"]
    latency = [row["total_seconds"] for row in rows if row["total_seconds"] > 0]
    unsupported_authority = sum(
        row["surface_authority"]
        and not (row.get("authorization_checks") or {}).get(
            "unsupported_addition_absent", False
        )
        for row in rows
    )
    metrics = {
        "case_count": len(rows),
        "valid_count": len(valid),
        "incomplete_count": len(incomplete),
        "outcome_counts": dict(sorted(counts.items())),
        "overall_faithful_valid_rate": _rate(counts["faithful_authority"], len(valid)),
        "false_authority_valid_rate": _rate(counts["false_authority"], len(valid)),
        "false_reject_valid_rate": _rate(counts["false_reject"], len(valid)),
        "unsafe_incomplete_authority_count": counts["unsafe_incomplete_authority"],
        "negation_polarity_accuracy": _rate(
            sum(row["polarity_passed"] for row in negation), len(negation)
        ),
        "unsupported_addition_authority_count": unsupported_authority,
        "by_language": by_language,
        "median_total_seconds": round(float(statistics.median(latency)), 4) if latency else None,
        "p95_total_seconds": _p95(latency),
        "raw_dialogue_persisted_count": sum(row["raw_dialogue_persisted"] for row in rows),
        "model_response_raw_persisted_count": sum(row["model_response_raw_persisted"] for row in rows),
    }
    gate_results = {
        "overall_faithful_valid_rate_min": metrics["overall_faithful_valid_rate"] >= gates["overall_faithful_valid_rate_min"],
        "per_language_faithful_valid_rate_min": all(
            row["faithful_rate"] is not None
            and row["faithful_rate"] >= gates["per_language_faithful_valid_rate_min"]
            for row in by_language.values()
        ),
        "false_authority_valid_rate_max": metrics["false_authority_valid_rate"] <= gates["false_authority_valid_rate_max"],
        "false_reject_valid_rate_max": metrics["false_reject_valid_rate"] <= gates["false_reject_valid_rate_max"],
        "unsafe_incomplete_authority_count_max": metrics["unsafe_incomplete_authority_count"] <= gates["unsafe_incomplete_authority_count_max"],
        "negation_polarity_accuracy_min": metrics["negation_polarity_accuracy"] is not None and metrics["negation_polarity_accuracy"] >= gates["negation_polarity_accuracy_min"],
        "unsupported_addition_authority_count_max": metrics["unsupported_addition_authority_count"] <= gates.get("unsupported_addition_authority_count_max", 0),
        "median_total_seconds_max": metrics["median_total_seconds"] is not None and metrics["median_total_seconds"] <= gates.get("median_total_seconds_max", gates.get("median_projection_seconds_max", 0)),
        "p95_total_seconds_max": metrics["p95_total_seconds"] is not None and metrics["p95_total_seconds"] <= gates.get("p95_total_seconds_max", gates.get("p95_projection_seconds_max", 0)),
    }
    return metrics, gate_results


def evaluate_cases(cases):
    left = m30.build_actual_left_brain()
    rows = []
    for case in cases:
        candidate, _pragmatic, _transition = m30._candidate_for_case(case["input"])
        if candidate.get("projection_required"):
            _m31_plan, authorization = left.authorize_literal_topic_m31(
                case["input"], candidate
            )
            proposal = {
                **candidate,
                "status": "candidate_superseded_by_source_first_m31",
                "reason": "m31_uses_exact_source_before_untrusted_generation",
                "elapsed_seconds": 0.0,
            }
        else:
            proposal = {
                **candidate,
                "status": "projection_not_attempted",
                "surface_authority": False,
                "raw_dialogue_persisted": False,
                "model_response_raw_persisted": False,
            }
            authorization = {
                "status": "not_applicable",
                "reason": "m29_projection_not_required",
                "surface_authority": False,
                "raw_dialogue_persisted": False,
                "model_response_raw_persisted": False,
            }
        row = m30.score_case(case, candidate, authorization)
        row.update(
            {
                "m29_projection_status": proposal.get("status"),
                "m29_projection_reason": proposal.get("reason"),
                "m29_seconds": float(proposal.get("elapsed_seconds") or 0),
                "m31_authorization_status": authorization.get("status"),
                "m31_authorization_reason": authorization.get("reason"),
                "m31_seconds": float(authorization.get("elapsed_seconds") or 0),
                "total_seconds": round(
                    float(proposal.get("elapsed_seconds") or 0)
                    + float(authorization.get("elapsed_seconds") or 0),
                    4,
                ),
                "authorization_checks": authorization.get("authorization_checks") or {},
                "error_tags": authorization.get("error_tags") or [],
                "repair_mode": authorization.get("repair_mode"),
                "surface_self_checks": authorization.get("surface_self_checks") or {},
            }
        )
        rows.append(row)
    return rows


def run(protocol_path, dataset_key, evidence_scope):
    protocol, dataset, resolved_protocol, dataset_path = load_dataset_protocol(
        protocol_path, dataset_key
    )
    rows = evaluate_cases(dataset["cases"])
    metrics, gate_results = summarize(rows, protocol["frozen_success_gates"])
    return {
        "schema": "uruha_semantic_authorization_evaluation_m31_v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "evidence_scope": evidence_scope,
        "protocol_path": str(resolved_protocol.relative_to(ROOT)),
        "protocol_sha256": _sha256(resolved_protocol),
        "dataset_path": str(dataset_path.relative_to(ROOT)),
        "dataset_sha256": _sha256(dataset_path),
        "proposal_model": "deterministic_m29_candidate_gate",
        "authorization_model": m30.brain_runtime.M31_SEMANTIC_VERIFIER_MODEL,
        "decision": "pass_all_frozen_gates" if all(gate_results.values()) else "fail_one_or_more_frozen_gates",
        "metrics": metrics,
        "gate_results": gate_results,
        "rows": rows,
        "claim_boundary": protocol["claim_boundary"],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("reserve", "m30-replay"), default="reserve")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.mode == "reserve":
        protocol = DEFAULT_RESERVE_PROTOCOL
        dataset_key = "reserve"
        output = args.output or DEFAULT_RESERVE_OUTPUT
        scope = "sealed_reserve_confirmation"
    else:
        protocol = m30.DEFAULT_PROTOCOL_PATH
        dataset_key = "holdout"
        output = args.output or DEFAULT_REPLAY_OUTPUT
        scope = "post_hoc_development_replay_not_holdout"
    result = run(protocol, dataset_key, scope)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"decision": result["decision"], **result["metrics"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
