"""Frozen M34 counterfactual pragmatic branch reserve evaluator."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import statistics
import time
from pathlib import Path

from test_personhood_loop_v2_13 import _IsolatedContractBrain


ROOT = Path(__file__).resolve().parent
RESERVE_PATH = ROOT / "datasets/m34_counterfactual_pragmatic_branch_reserve_v1.json"
PROTOCOL_PATH = ROOT / "research/m34_counterfactual_pragmatic_branch_reserve_protocol.json"
FREEZE_PATH = ROOT / "research/m34_implementation_freeze_2026-08-25.json"
OUTPUT_PATH = ROOT / "analysis/m34_counterfactual_pragmatic_branch_reserve_raw_2026-08-25.json"


def _sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _digest(value):
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()[:16]


def _rate(numerator, denominator):
    return round(numerator / denominator, 4) if denominator else 0.0


def _p95(values):
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int(0.95 * len(ordered) + 0.9999) - 1))
    return round(float(ordered[index]), 4)


def _visible_japanese(text):
    value = str(text or "").strip()
    return bool(
        value
        and re.search(r"[ぁ-んァ-ヶ]", value)
        and not re.search(r"\b[A-Za-z]{2,}\b", value)
    )


def _run_case(case):
    started = time.perf_counter()
    brain = _IsolatedContractBrain()
    brain.run_turn_debug(case["seed_input"])
    brain.run_turn_debug(case["seed_feedback"])
    current = brain.run_turn_debug(case["current_input"])
    current_branch = (
        (current.get("runtime_trace") or {}).get(
            "counterfactual_pragmatic_branch_m34"
        )
        or {}
    )
    feedback = brain.run_turn_debug(case["feedback_input"])
    feedback_branch = (
        (feedback.get("runtime_trace") or {}).get(
            "counterfactual_pragmatic_branch_m34"
        )
        or {}
    )
    selected = current_branch.get("selected_branch") or {}
    context = current_branch.get("context_evidence") or {}
    prediction = current_branch.get("observable_prediction") or {}
    verification = feedback_branch.get("previous_branch_verification") or {}
    revision = feedback_branch.get("revision") or {}
    adaptive_serialized = json.dumps(
        brain.runtime.adaptive_person_model,
        ensure_ascii=False,
        sort_keys=True,
    )
    forbidden_raw = [
        case["seed_input"],
        case["seed_feedback"],
        case["current_input"],
        case["feedback_input"],
        current.get("reply") or "",
        feedback.get("reply") or "",
    ]
    raw_persisted = any(value and value in adaptive_serialized for value in forbidden_raw)
    ledger_serialized = json.dumps(current_branch, ensure_ascii=False, sort_keys=True)
    model_response_raw_persisted = bool(
        (current.get("reply") or "")
        and (current.get("reply") or "") in ledger_serialized
    )
    candidate_rows = current_branch.get("candidate_branches") or []
    elapsed = round(time.perf_counter() - started, 4)
    return {
        "case_id": case["case_id"],
        "pair_id": case["pair_id"],
        "language": case["language"],
        "context_condition": case["context_condition"],
        "current_input_digest": _digest(case["current_input"]),
        "literal_observation_digest": (
            (current_branch.get("literal_observation") or {}).get(
                "current_input_digest"
            )
        ),
        "selected_policy": selected.get("policy_id"),
        "selected_mode": selected.get("mode"),
        "authority_basis": selected.get("authority_basis"),
        "bounded_alternative_policy": (
            (current_branch.get("bounded_alternative") or {}).get("policy_id")
        ),
        "candidate_count": len(candidate_rows),
        "context_evidence_traced": bool(
            context.get("verified_context_authority")
            and context.get("verified_reversible_atoms")
            and context.get("used_scopes")
        ),
        "observable_prediction_traced": bool(
            prediction.get("branch_id")
            and prediction.get("expected_next_observable_behavior")
            and prediction.get("verification_window") == "next_user_turn"
            and prediction.get("private_state_prediction") is False
        ),
        "previous_outcome": verification.get("status"),
        "replacement_policy": revision.get("replacement_policy_id"),
        "original_evidence_rewritten": bool(
            revision.get("original_evidence_rewritten")
        ),
        "current_surface_status": current_branch.get("surface_status"),
        "current_reply_digest": _digest(current.get("reply")),
        "feedback_reply_digest": _digest(feedback.get("reply")),
        "current_visible_japanese": _visible_japanese(current.get("reply")),
        "feedback_visible_japanese": _visible_japanese(feedback.get("reply")),
        "unverified_mental_fact_write_count": int(
            current_branch.get("fact_memory_write_count") or 0
        )
        + int(feedback_branch.get("fact_memory_write_count") or 0),
        "raw_dialogue_persisted": raw_persisted,
        "model_response_raw_persisted": model_response_raw_persisted,
        "elapsed_seconds": elapsed,
    }


def summarize(rows, cases, gates):
    case_by_id = {case["case_id"]: case for case in cases}
    count = len(rows)
    policy_correct = sum(
        row["selected_policy"] == case_by_id[row["case_id"]]["expected_policy"]
        for row in rows
    )
    mode_correct = sum(
        row["selected_mode"] == case_by_id[row["case_id"]]["expected_mode"]
        for row in rows
    )
    outcome_correct = sum(
        row["previous_outcome"]
        == case_by_id[row["case_id"]]["expected_previous_outcome"]
        for row in rows
    )
    contradiction_rows = [
        row
        for row in rows
        if case_by_id[row["case_id"]]["expected_previous_outcome"]
        == "contradicted"
    ]
    contradiction_replacement_correct = sum(
        row["replacement_policy"]
        == case_by_id[row["case_id"]]["expected_replacement_policy"]
        and not row["original_evidence_rewritten"]
        for row in contradiction_rows
    )
    pair_groups = {}
    for row in rows:
        pair_groups.setdefault(row["pair_id"], []).append(row)
    divergent_pairs = sum(
        len(group) == 2
        and len({row["selected_policy"] for row in group}) == 2
        for group in pair_groups.values()
    )
    invariant_pairs = sum(
        len(group) == 2
        and len({row["current_input_digest"] for row in group}) == 1
        and len({row["literal_observation_digest"] for row in group}) == 1
        for group in pair_groups.values()
    )
    visible_checks = [
        flag
        for row in rows
        for flag in (
            row["current_visible_japanese"],
            row["feedback_visible_japanese"],
        )
    ]
    elapsed = [row["elapsed_seconds"] for row in rows]
    metrics = {
        "case_count": count,
        "pair_count": len(pair_groups),
        "selected_policy_accuracy": _rate(policy_correct, count),
        "selected_mode_accuracy": _rate(mode_correct, count),
        "counterfactual_pair_divergence_rate": _rate(
            divergent_pairs,
            len(pair_groups),
        ),
        "current_literal_invariance_rate": _rate(
            invariant_pairs,
            len(pair_groups),
        ),
        "verified_context_evidence_trace_coverage": _rate(
            sum(row["context_evidence_traced"] for row in rows),
            count,
        ),
        "candidate_alternative_trace_coverage": _rate(
            sum(
                row["candidate_count"] >= 2
                and bool(row["bounded_alternative_policy"])
                for row in rows
            ),
            count,
        ),
        "observable_prediction_trace_coverage": _rate(
            sum(row["observable_prediction_traced"] for row in rows),
            count,
        ),
        "previous_outcome_verification_accuracy": _rate(
            outcome_correct,
            count,
        ),
        "contradiction_replacement_accuracy": _rate(
            contradiction_replacement_correct,
            len(contradiction_rows),
        ),
        "selected_branch_surface_match_rate": _rate(
            sum(row["current_surface_status"] == "matched" for row in rows),
            count,
        ),
        "visible_japanese_rate": _rate(sum(visible_checks), len(visible_checks)),
        "unverified_mental_fact_write_count": sum(
            row["unverified_mental_fact_write_count"] for row in rows
        ),
        "raw_dialogue_persisted_count": sum(
            row["raw_dialogue_persisted"] for row in rows
        ),
        "model_response_raw_persisted_count": sum(
            row["model_response_raw_persisted"] for row in rows
        ),
        "median_case_seconds": round(statistics.median(elapsed), 4) if elapsed else 0.0,
        "p95_case_seconds": _p95(elapsed),
    }
    gate_results = {
        "selected_policy_accuracy_min": metrics["selected_policy_accuracy"]
        >= gates["selected_policy_accuracy_min"],
        "selected_mode_accuracy_min": metrics["selected_mode_accuracy"]
        >= gates["selected_mode_accuracy_min"],
        "counterfactual_pair_divergence_rate_min": metrics[
            "counterfactual_pair_divergence_rate"
        ]
        >= gates["counterfactual_pair_divergence_rate_min"],
        "current_literal_invariance_rate_min": metrics[
            "current_literal_invariance_rate"
        ]
        >= gates["current_literal_invariance_rate_min"],
        "verified_context_evidence_trace_coverage_min": metrics[
            "verified_context_evidence_trace_coverage"
        ]
        >= gates["verified_context_evidence_trace_coverage_min"],
        "candidate_alternative_trace_coverage_min": metrics[
            "candidate_alternative_trace_coverage"
        ]
        >= gates["candidate_alternative_trace_coverage_min"],
        "observable_prediction_trace_coverage_min": metrics[
            "observable_prediction_trace_coverage"
        ]
        >= gates["observable_prediction_trace_coverage_min"],
        "previous_outcome_verification_accuracy_min": metrics[
            "previous_outcome_verification_accuracy"
        ]
        >= gates["previous_outcome_verification_accuracy_min"],
        "contradiction_replacement_accuracy_min": metrics[
            "contradiction_replacement_accuracy"
        ]
        >= gates["contradiction_replacement_accuracy_min"],
        "selected_branch_surface_match_rate_min": metrics[
            "selected_branch_surface_match_rate"
        ]
        >= gates["selected_branch_surface_match_rate_min"],
        "visible_japanese_rate_min": metrics["visible_japanese_rate"]
        >= gates["visible_japanese_rate_min"],
        "unverified_mental_fact_write_count_max": metrics[
            "unverified_mental_fact_write_count"
        ]
        <= gates["unverified_mental_fact_write_count_max"],
        "raw_dialogue_persisted_count_max": metrics[
            "raw_dialogue_persisted_count"
        ]
        <= gates["raw_dialogue_persisted_count_max"],
        "model_response_raw_persisted_count_max": metrics[
            "model_response_raw_persisted_count"
        ]
        <= gates["model_response_raw_persisted_count_max"],
        "median_case_seconds_max": metrics["median_case_seconds"]
        <= gates["median_case_seconds_max"],
        "p95_case_seconds_max": metrics["p95_case_seconds"]
        <= gates["p95_case_seconds_max"],
    }
    return metrics, gate_results


def run_reserve():
    dataset = json.loads(RESERVE_PATH.read_text(encoding="utf-8"))
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    cases = dataset["cases"]
    rows = [_run_case(case) for case in cases]
    metrics, gate_results = summarize(
        rows,
        cases,
        protocol["frozen_success_gates"],
    )
    payload = {
        "schema": "uruha_counterfactual_pragmatic_branch_evaluation_m34_v1",
        "mode": "reserve",
        "dataset_path": str(RESERVE_PATH.relative_to(ROOT)),
        "dataset_sha256": _sha256(RESERVE_PATH),
        "protocol_path": str(PROTOCOL_PATH.relative_to(ROOT)),
        "protocol_sha256": _sha256(PROTOCOL_PATH),
        "implementation_freeze_sha256": (
            _sha256(FREEZE_PATH) if FREEZE_PATH.exists() else None
        ),
        "decision": (
            "pass_all_frozen_gates"
            if all(gate_results.values())
            else "fail_one_or_more_frozen_gates"
        ),
        "metrics": metrics,
        "gate_results": gate_results,
        "rows": rows,
        "claim_boundary": protocol["claim_boundary"],
    }
    OUTPUT_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return payload


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("reserve",), required=True)
    parser.parse_args()
    payload = run_reserve()
    print(
        json.dumps(
            {
                "decision": payload["decision"],
                **payload["metrics"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
