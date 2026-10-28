"""Reproducible M33 source-anchored semantic atom evaluation."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import uruha_adaptive_person_model as uapm
import uruha_literal_topic_fidelity_m30 as m30
import uruha_semantic_authorization_eval_m31 as m31
import uruha_semantic_commit_eval_m32 as m32
import uruha_source_semantic_atoms_m33 as m33


ROOT = Path(__file__).resolve().parent
RESERVE_PATH = ROOT / "datasets/m33_source_anchored_semantic_atom_reserve_v1.json"
PROTOCOL_PATH = ROOT / "research/m33_source_anchored_semantic_atom_reserve_protocol.json"
FREEZE_PATH = ROOT / "research/m33_implementation_freeze_2026-08-25.json"
M32_EXPOSED_PATH = ROOT / "datasets/m32_semantic_commit_routing_reserve_v1.json"


def _sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _load_cases(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))["cases"]


def _candidate_for_case(case):
    return m32._candidate_for_case(case)[0]


def evaluate_cases(cases):
    left = m30.build_actual_left_brain()
    rows = []
    for case in cases:
        candidate = _candidate_for_case(case)
        ledger = m33.extract_source_semantic_atoms_m33(case["input"], candidate)
        direct_identity = bool(
            ledger.get("status") == "source_atoms_extracted"
            and ledger.get("direct_japanese_identity")
        )
        if candidate.get("projection_required") and not direct_identity:
            _m31_plan, authorization = left.authorize_literal_topic_m31(
                case["input"],
                candidate,
            )
            _m32_plan, repair = uapm.build_deterministic_semantic_commit_m32(
                authorization
            )
        else:
            authorization = {
                "schema": uapm.SEMANTIC_AUTHORIZATION_SCHEMA_M31,
                "status": "not_applicable",
                "reason": (
                    "direct_japanese_identity_m33"
                    if direct_identity
                    else "m29_projection_not_required"
                ),
                "surface_authority": False,
                "raw_dialogue_persisted": False,
                "model_response_raw_persisted": False,
            }
            repair = {
                "schema": uapm.SEMANTIC_COMMIT_REPAIR_SCHEMA_M32,
                "status": "not_applicable",
                "reason": "m31_not_authoritative_or_bypassed",
                "surface_authority": False,
                "raw_dialogue_persisted": False,
                "model_response_raw_persisted": False,
            }
        _m33_plan, verification, commitment = (
            m33.build_source_anchored_semantic_commit_m33(
                case["input"],
                ledger,
                authorization,
                repair,
            )
        )
        final_contract = (
            commitment
            if commitment.get("surface_authority")
            else repair
            if repair.get("surface_authority")
            else authorization
        )
        row = m30.score_case(case, candidate, final_contract)
        required_types = set(case.get("required_atom_types") or [])
        extracted_types = set(ledger.get("atom_types") or [])
        atom_trace_complete = bool(
            not case.get("authority_expected")
            or required_types.issubset(extracted_types)
        )
        final_source = (
            "m33"
            if commitment.get("surface_authority")
            else "m32"
            if repair.get("surface_authority")
            else "m31"
            if authorization.get("surface_authority")
            else "none"
        )
        unresolved_conflict_authority = bool(
            verification.get("source_conflict_detected")
            and final_source in {"m31", "m32"}
        )
        row.update(
            {
                "candidate_context": case.get("candidate_context")
                or "previous_unlinked_unknown",
                "required_atom_types": sorted(required_types),
                "source_atom_types": sorted(extracted_types),
                "source_atom_trace_complete": atom_trace_complete,
                "source_atom_ledger_status": ledger.get("status"),
                "source_rule_id": ledger.get("rule_id"),
                "direct_japanese_identity": direct_identity,
                "m31_status": authorization.get("status"),
                "m31_seconds": float(authorization.get("elapsed_seconds") or 0),
                "m32_status": repair.get("status"),
                "m33_verification_status": verification.get("status"),
                "m33_source_conflict_detected": bool(
                    verification.get("source_conflict_detected")
                ),
                "m33_status": commitment.get("status"),
                "m33_repair_kind": commitment.get("repair_kind"),
                "m33_surface_authority": bool(commitment.get("surface_authority")),
                "final_authority_source": final_source,
                "unresolved_source_conflict_authority": unresolved_conflict_authority,
                "total_seconds": round(
                    float(authorization.get("elapsed_seconds") or 0), 4
                ),
                "raw_dialogue_persisted": bool(
                    ledger.get("raw_dialogue_persisted")
                    or authorization.get("raw_dialogue_persisted")
                    or repair.get("raw_dialogue_persisted")
                    or commitment.get("raw_dialogue_persisted")
                ),
                "model_response_raw_persisted": bool(
                    authorization.get("model_response_raw_persisted")
                    or repair.get("model_response_raw_persisted")
                    or commitment.get("model_response_raw_persisted")
                ),
            }
        )
        rows.append(row)
    return rows


def summarize(rows, gates):
    normalized_rows = []
    for row in rows:
        normalized = dict(row)
        normalized.setdefault(
            "surface_authority",
            normalized.get("final_authority_source") not in {None, "none"},
        )
        normalized.setdefault(
            "authorization_checks",
            {"unsupported_addition_absent": True},
        )
        normalized.setdefault(
            "polarity_passed",
            normalized.get("expected_polarity")
            == normalized.get("observed_polarity"),
        )
        normalized_rows.append(normalized)
    rows = normalized_rows
    metrics, gate_results = m31.summarize(rows, gates)
    valid = [row for row in rows if row["authority_expected"]]
    fresh = [row for row in valid if row["candidate_context"] == "fresh_session"]
    direct_ja = [row for row in valid if row["language"] == "ja"]
    changes = [row for row in valid if "change" in row["category"]]
    quantity_negation = [
        row
        for row in valid
        if row["category"]
        in {"negated_object_quantity", "limited_quantity", "negation_quantity"}
    ]

    def faithful_rate(subset):
        if not subset:
            return None
        return round(
            sum(row["outcome"] == "faithful_authority" for row in subset)
            / len(subset),
            4,
        )

    atom_coverage = (
        round(sum(row["source_atom_trace_complete"] for row in valid) / len(valid), 4)
        if valid
        else None
    )
    metrics.update(
        {
            "fresh_session_valid_count": len(fresh),
            "fresh_session_faithful_rate": faithful_rate(fresh),
            "direct_japanese_valid_count": len(direct_ja),
            "direct_japanese_faithful_rate": faithful_rate(direct_ja),
            "change_operator_valid_count": len(changes),
            "change_operator_faithful_rate": faithful_rate(changes),
            "negated_or_limited_quantity_valid_count": len(quantity_negation),
            "negated_or_limited_quantity_faithful_rate": faithful_rate(
                quantity_negation
            ),
            "required_source_atom_trace_coverage": atom_coverage,
            "source_conflict_authority_count": sum(
                row["unresolved_source_conflict_authority"] for row in rows
            ),
            "m31_authority_count": sum(
                row["final_authority_source"] == "m31" for row in rows
            ),
            "m32_authority_count": sum(
                row["final_authority_source"] == "m32" for row in rows
            ),
            "m33_authority_count": sum(
                row["final_authority_source"] == "m33" for row in rows
            ),
            "m33_conflict_repair_count": sum(
                row["m33_source_conflict_detected"]
                and row["final_authority_source"] == "m33"
                for row in rows
            ),
        }
    )
    gate_results.update(
        {
            "fresh_session_faithful_valid_rate": (
                metrics["fresh_session_faithful_rate"] is not None
                and metrics["fresh_session_faithful_rate"]
                >= gates["fresh_session_faithful_valid_rate_min"]
            ),
            "direct_japanese_faithful_valid_rate": (
                metrics["direct_japanese_faithful_rate"] is not None
                and metrics["direct_japanese_faithful_rate"]
                >= gates["direct_japanese_faithful_valid_rate_min"]
            ),
            "change_operator_faithful_rate": (
                metrics["change_operator_faithful_rate"] is not None
                and metrics["change_operator_faithful_rate"]
                >= gates["change_operator_faithful_rate_min"]
            ),
            "negated_or_limited_quantity_faithful_rate": (
                metrics["negated_or_limited_quantity_faithful_rate"] is not None
                and metrics["negated_or_limited_quantity_faithful_rate"]
                >= gates["negated_or_limited_quantity_faithful_rate_min"]
            ),
            "required_source_atom_trace_coverage": (
                metrics["required_source_atom_trace_coverage"] is not None
                and metrics["required_source_atom_trace_coverage"]
                >= gates["required_source_atom_trace_coverage_min"]
            ),
            "source_conflict_authority_count": (
                metrics["source_conflict_authority_count"]
                <= gates["source_conflict_authority_count_max"]
            ),
        }
    )
    decision = (
        "pass_all_frozen_gates"
        if all(gate_results.values())
        else "fail_one_or_more_frozen_gates"
    )
    return metrics, gate_results, decision


def run(mode):
    if mode == "reserve":
        dataset_path = RESERVE_PATH
        protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
        gates = protocol["frozen_success_gates"]
        output_path = (
            ROOT
            / "analysis/m33_source_anchored_semantic_atom_reserve_raw_2026-08-25.json"
        )
    else:
        dataset_path = M32_EXPOSED_PATH
        protocol = json.loads(
            (ROOT / "research/m32_semantic_commit_routing_reserve_protocol.json").read_text(
                encoding="utf-8"
            )
        )
        gates = protocol["frozen_success_gates"]
        gates.update(
            {
                "direct_japanese_faithful_valid_rate_min": 0.0,
                "change_operator_faithful_rate_min": 0.0,
                "negated_or_limited_quantity_faithful_rate_min": 0.0,
                "required_source_atom_trace_coverage_min": 0.0,
                "source_conflict_authority_count_max": 99,
            }
        )
        output_path = (
            ROOT
            / "analysis/m33_m32_exposed_development_replay_raw_2026-08-25.json"
        )
    cases = _load_cases(dataset_path)
    rows = evaluate_cases(cases)
    metrics, gate_results, decision = summarize(rows, gates)
    payload = {
        "schema": "uruha_source_anchored_semantic_atom_evaluation_m33_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": mode,
        "dataset_path": str(dataset_path.relative_to(ROOT)),
        "dataset_sha256": _sha256(dataset_path),
        "protocol_path": (
            str(PROTOCOL_PATH.relative_to(ROOT)) if mode == "reserve" else None
        ),
        "protocol_sha256": _sha256(PROTOCOL_PATH) if mode == "reserve" else None,
        "implementation_freeze_sha256": (
            _sha256(FREEZE_PATH) if mode == "reserve" and FREEZE_PATH.exists() else None
        ),
        "decision": decision,
        "metrics": metrics,
        "gate_results": gate_results,
        "rows": rows,
        "claim_boundary": (
            "first sealed controlled reserve" if mode == "reserve" else "exposed development replay only"
        ),
    }
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"decision": decision, **metrics}, ensure_ascii=False, indent=2))
    return payload


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("reserve", "m32-replay"), required=True)
    args = parser.parse_args()
    run(args.mode)


if __name__ == "__main__":
    main()
