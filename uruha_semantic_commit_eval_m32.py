"""M32 exposed replay and sealed reserve evaluation harness."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import uruha_adaptive_person_model as uapm
import uruha_literal_topic_fidelity_m30 as m30
import uruha_personhood_loop as upl
import uruha_semantic_authorization_eval_m31 as m31


ROOT = Path(__file__).resolve().parent
DEFAULT_PROTOCOL = ROOT / "research/m32_semantic_commit_routing_reserve_protocol.json"
DEFAULT_RESERVE_OUTPUT = ROOT / "analysis/m32_semantic_commit_routing_reserve_raw_2026-08-25.json"
DEFAULT_REPLAY_OUTPUT = ROOT / "analysis/m32_m31_exposed_development_replay_raw_2026-08-25.json"


def _sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_dataset(protocol_path, dataset_key="reserve"):
    protocol_path = Path(protocol_path)
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    spec = protocol[dataset_key]
    dataset_path = ROOT / spec["path"]
    if _sha256(dataset_path) != spec["sha256"]:
        raise ValueError(f"{dataset_key} hash mismatch")
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    if len(dataset.get("cases") or []) != int(spec["case_count"]):
        raise ValueError(f"{dataset_key} case count mismatch")
    return protocol, dataset, protocol_path, dataset_path


def _feedback_for_context(context):
    if context == "fresh_session":
        return {}
    return {
        "previous_prediction_id": "m32-development-previous",
        "status": "uncertain",
        "reason": "new_current_topic_not_linked_to_previous_prediction",
        "feedback_linked_to_previous_prediction": False,
        "causal_outcome_calibration_m27": {
            "status": "resolved_unknown_excluded"
        },
    }


def _candidate_for_case(case):
    text = case["input"]
    context = case.get("candidate_context") or "previous_unlinked_unknown"
    feedback = _feedback_for_context(context)
    pragmatic = upl.build_human_pragmatic_understanding(text, turn_index=1)
    transition = uapm.build_feedback_topic_transition_m28(
        text,
        feedback,
        pragmatic,
    )
    candidate = uapm.build_literal_topic_projection_candidate_m29(
        text,
        feedback,
        pragmatic,
        transition,
    )
    return candidate, pragmatic, transition


def evaluate_cases(cases):
    left = m30.build_actual_left_brain()
    rows = []
    for case in cases:
        candidate, pragmatic, _transition = _candidate_for_case(case)
        if candidate.get("projection_required"):
            _m31_plan, authorization = left.authorize_literal_topic_m31(
                case["input"],
                candidate,
            )
        else:
            authorization = {
                "schema": uapm.SEMANTIC_AUTHORIZATION_SCHEMA_M31,
                "status": "not_applicable",
                "reason": "m29_projection_not_required",
                "surface_authority": False,
                "raw_dialogue_persisted": False,
                "model_response_raw_persisted": False,
            }
        _m32_plan, repair = uapm.build_deterministic_semantic_commit_m32(
            authorization
        )
        final_contract = (
            repair
            if repair.get("surface_authority")
            else authorization
        )
        row = m30.score_case(case, candidate, final_contract)
        final_checks = (
            final_contract.get("authorization_checks")
            or final_contract.get("commit_checks")
            or {}
        )
        row.update(
            {
                "candidate_context": case.get("candidate_context")
                or "previous_unlinked_unknown",
                "pragmatic_label": pragmatic.get("pragmatic_label"),
                "text_visible_hesitation": bool(
                    pragmatic.get("text_visible_hesitation")
                ),
                "m31_status": authorization.get("status"),
                "m31_reason": authorization.get("reason"),
                "m31_seconds": float(authorization.get("elapsed_seconds") or 0),
                "m32_status": repair.get("status"),
                "m32_reason": repair.get("reason"),
                "m32_surface_authority": bool(repair.get("surface_authority")),
                "final_authority_source": (
                    "m32"
                    if repair.get("surface_authority")
                    else "m31"
                    if authorization.get("surface_authority")
                    else "none"
                ),
                "total_seconds": round(
                    float(authorization.get("elapsed_seconds") or 0), 4
                ),
                "authorization_checks": final_checks,
                "m31_failed_authorization_checks": list(
                    (
                        authorization.get("m32_repair_candidate") or {}
                    ).get("failed_authorization_checks")
                    or []
                ),
                "raw_dialogue_persisted": bool(
                    authorization.get("raw_dialogue_persisted")
                    or repair.get("raw_dialogue_persisted")
                ),
                "model_response_raw_persisted": bool(
                    authorization.get("model_response_raw_persisted")
                    or repair.get("model_response_raw_persisted")
                ),
            }
        )
        rows.append(row)
    return rows


def summarize(rows, gates):
    metrics, gate_results = m31.summarize(rows, gates)
    valid = [row for row in rows if row["authority_expected"]]
    fresh = [row for row in valid if row["candidate_context"] == "fresh_session"]
    ordinary_negation = [
        row for row in valid if row["category"] == "ordinary_negation"
    ]

    def rate(subset):
        if not subset:
            return None
        return round(
            sum(row["outcome"] == "faithful_authority" for row in subset)
            / len(subset),
            4,
        )

    metrics.update(
        {
            "fresh_session_valid_count": len(fresh),
            "fresh_session_faithful_rate": rate(fresh),
            "ordinary_negation_valid_count": len(ordinary_negation),
            "ordinary_negation_faithful_rate": rate(ordinary_negation),
            "m31_authority_count": sum(
                row["final_authority_source"] == "m31" for row in rows
            ),
            "m32_repair_authority_count": sum(
                row["final_authority_source"] == "m32" for row in rows
            ),
        }
    )
    if "fresh_session_faithful_valid_rate_min" in gates:
        gate_results["fresh_session_faithful_valid_rate_min"] = bool(
            metrics["fresh_session_faithful_rate"] is not None
            and metrics["fresh_session_faithful_rate"]
            >= gates["fresh_session_faithful_valid_rate_min"]
        )
    if "ordinary_negation_faithful_rate_min" in gates:
        gate_results["ordinary_negation_faithful_rate_min"] = bool(
            metrics["ordinary_negation_faithful_rate"] is not None
            and metrics["ordinary_negation_faithful_rate"]
            >= gates["ordinary_negation_faithful_rate_min"]
        )
    for metric_name in (
        "raw_dialogue_persisted_count",
        "model_response_raw_persisted_count",
    ):
        gate_name = f"{metric_name}_max"
        if gate_name in gates:
            gate_results[gate_name] = metrics[metric_name] <= gates[gate_name]
    return metrics, gate_results


def run(protocol_path, dataset_key, evidence_scope):
    protocol, dataset, protocol_path, dataset_path = load_dataset(
        protocol_path,
        dataset_key,
    )
    rows = evaluate_cases(dataset["cases"])
    metrics, gate_results = summarize(rows, protocol["frozen_success_gates"])
    return {
        "schema": "uruha_semantic_commit_routing_evaluation_m32_v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "evidence_scope": evidence_scope,
        "protocol_path": str(protocol_path.relative_to(ROOT)),
        "protocol_sha256": _sha256(protocol_path),
        "dataset_path": str(dataset_path.relative_to(ROOT)),
        "dataset_sha256": _sha256(dataset_path),
        "semantic_model": m30.brain_runtime.M31_SEMANTIC_VERIFIER_MODEL,
        "commit_model_calls": 0,
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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("reserve", "m31-replay"), default="reserve")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.mode == "reserve":
        protocol = DEFAULT_PROTOCOL
        dataset_key = "reserve"
        output = args.output or DEFAULT_RESERVE_OUTPUT
        scope = "sealed_m32_reserve_confirmation"
    else:
        protocol = m31.DEFAULT_RESERVE_PROTOCOL
        dataset_key = "reserve"
        output = args.output or DEFAULT_REPLAY_OUTPUT
        scope = "post_hoc_m31_reserve_development_replay_not_holdout"
    result = run(protocol, dataset_key, scope)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {"decision": result["decision"], **result["metrics"]},
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
