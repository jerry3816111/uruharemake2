"""Evaluator for the frozen M39 semantic/persona surface reserve."""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import time
from pathlib import Path

from uruha_semantic_persona_surface_m39 import (
    formal_register_detected_m39,
    inspect_surface_m39,
    policy_act_matches_m39,
    verify_and_repair_surface_m39,
)


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_DATASET = BASE_DIR / "datasets/m39_semantic_persona_surface_reserve_v1.json"
DEFAULT_PROTOCOL = BASE_DIR / "research/m39_semantic_persona_surface_protocol_v1.json"


def _sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _digest(value):
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()[:16]


def _is_visible_japanese(reply):
    text = str(reply or "").strip()
    if not text or not re_search_japanese(text):
        return False
    return not bool(__import__("re").search(r"\b(?:I|you|the|and|please|sorry|okay)\b", text, __import__("re").IGNORECASE))


def re_search_japanese(text):
    return bool(__import__("re").search(r"[ぁ-んァ-ヶ一-龠]", str(text or "")))


def validate_reserve(dataset, protocol):
    errors = []
    cases = list(dataset.get("cases") or [])
    if dataset.get("schema") != "uruha_m39_semantic_persona_surface_reserve_v1":
        errors.append("unexpected_dataset_schema")
    if protocol.get("schema") != "uruha_m39_semantic_persona_surface_protocol_v1":
        errors.append("unexpected_protocol_schema")
    if int(dataset.get("case_count") or -1) != len(cases):
        errors.append("case_count_mismatch")
    case_ids = [str(case.get("case_id") or "") for case in cases]
    if len(case_ids) != len(set(case_ids)):
        errors.append("duplicate_case_id")
    valid_actions = {"accept", "repair", "not_applicable"}
    for case in cases:
        case_id = str(case.get("case_id") or "missing")
        if case.get("expected_action") not in valid_actions:
            errors.append(f"{case_id}:invalid_expected_action")
        if case.get("expected_action") != "not_applicable" and not case.get("selected_policy_id"):
            errors.append(f"{case_id}:missing_selected_policy")
        if case.get("expected_action") == "not_applicable" and case.get("semantic_route_selected_type") not in set(protocol.get("protected_routes") or []):
            errors.append(f"{case_id}:nonprotected_not_applicable")
    return {"valid": not errors, "errors": errors, "case_count": len(cases)}


def _logic_for_case(case):
    policy = case.get("selected_policy_id")
    return {
        "desired_response_policy_m18": policy,
        "semantic_route_m22": {
            "selected_type": case.get("semantic_route_selected_type"),
        },
        "counterfactual_pragmatic_branch_m34": {
            "selected_branch": {"policy_id": policy} if policy else {},
        },
    }


def _baseline_action(case):
    if case.get("semantic_route_selected_type") in {"safety_sensitive", "factual_or_memory", "deliberation"}:
        return "not_applicable"
    return "accept" if case.get("selected_policy_id") and str(case.get("proposed_reply_jp") or "").strip() else "not_applicable"


def evaluate(dataset, protocol):
    validation = validate_reserve(dataset, protocol)
    if not validation["valid"]:
        raise ValueError("invalid M39 reserve: " + ", ".join(validation["errors"]))

    rows = []
    latencies = []
    for case in dataset.get("cases") or []:
        logic = _logic_for_case(case)
        source = str(case.get("source_utterance") or "")
        proposed = str(case.get("proposed_reply_jp") or "")
        started = time.perf_counter()
        final_reply, trace = verify_and_repair_surface_m39(source, proposed, logic)
        elapsed = time.perf_counter() - started
        latencies.append(elapsed)
        after = inspect_surface_m39(source, final_reply, logic)
        baseline_action = _baseline_action(case)
        expected_action = case.get("expected_action")
        forbidden_after = sorted(
            set(after.get("role_violations") or [])
            | set(after.get("unsupported_additions") or [])
            | ({"formal_register"} if after.get("formal_register_detected") else set())
        )
        required_policy = case.get("required_policy_act")
        policy_match = policy_act_matches_m39(final_reply, required_policy)
        row = {
            "case_id": case.get("case_id"),
            "language": case.get("language"),
            "category": case.get("category"),
            "source_digest": _digest(source),
            "proposed_reply_digest": _digest(proposed),
            "final_reply_digest": _digest(final_reply),
            "expected_action": expected_action,
            "baseline_action": baseline_action,
            "baseline_action_correct": baseline_action == expected_action,
            "system_action": trace.get("action"),
            "system_status": trace.get("status"),
            "system_action_correct": trace.get("action") == expected_action,
            "changed": trace.get("changed"),
            "violations_before": trace.get("violations_before") or [],
            "forbidden_concepts_after": forbidden_after,
            "post_repair_policy_act_match": policy_match,
            "visible_japanese_format": _is_visible_japanese(final_reply),
            "formal_register_after": formal_register_detected_m39(final_reply),
            "raw_dialogue_persisted": trace.get("raw_dialogue_persisted"),
            "unverified_mental_fact_write_count": trace.get("fact_memory_write_count"),
            "latency_seconds": round(elapsed, 6),
        }
        rows.append(row)

    count = len(rows)
    role_rows = [row for row in rows if row["category"] in {"speaker_role_inversion", "third_party_role_inversion"}]
    addition_rows = [row for row in rows if row["category"].startswith("unsupported_")]
    policy_rows = [row for row in rows if row["category"] == "selected_policy_not_realized"]
    safe_rows = [row for row in rows if row["category"] == "safe_noninterference"]
    protected_rows = [row for row in rows if row["category"] == "protected_route_noninterference"]

    def rate(items, predicate):
        return round(sum(1 for item in items if predicate(item)) / len(items), 4) if items else 1.0

    p95_index = max(0, min(len(latencies) - 1, int(len(latencies) * 0.95 + 0.999999) - 1))
    sorted_latencies = sorted(latencies)
    metrics = {
        "case_count": count,
        "baseline_expected_action_accuracy": rate(rows, lambda row: row["baseline_action_correct"]),
        "system_expected_action_accuracy": rate(rows, lambda row: row["system_action_correct"]),
        "role_inversion_repair_recall": rate(role_rows, lambda row: row["system_action"] == "repair"),
        "unsupported_addition_repair_recall": rate(addition_rows, lambda row: row["system_action"] == "repair"),
        "policy_realization_repair_recall": rate(policy_rows, lambda row: row["system_action"] == "repair"),
        "safe_noninterference_rate": rate(safe_rows, lambda row: row["system_action"] == "accept" and not row["changed"]),
        "protected_route_noninterference_rate": rate(protected_rows, lambda row: row["system_action"] == "not_applicable" and not row["changed"]),
        "post_repair_policy_act_match": rate([row for row in rows if row.get("category") != "protected_route_noninterference"], lambda row: row["post_repair_policy_act_match"]),
        "post_repair_forbidden_concept_rate": rate(rows, lambda row: bool(row["forbidden_concepts_after"])),
        "visible_japanese_format_rate": rate(rows, lambda row: row["visible_japanese_format"]),
        "formal_register_rate": rate(rows, lambda row: row["formal_register_after"]),
        "raw_dialogue_persistence_count": sum(bool(row["raw_dialogue_persisted"]) for row in rows),
        "unverified_mental_fact_write_count": sum(int(row["unverified_mental_fact_write_count"] or 0) for row in rows),
        "median_verifier_latency_seconds": round(statistics.median(latencies), 6),
        "p95_verifier_latency_seconds": round(sorted_latencies[p95_index], 6),
        "model_generation_call_count": 0,
    }
    gates = protocol.get("gates") or {}
    gate_results = {
        "overall_expected_action_accuracy_min": metrics["system_expected_action_accuracy"] >= gates["overall_expected_action_accuracy_min"],
        "role_inversion_repair_recall_min": metrics["role_inversion_repair_recall"] >= gates["role_inversion_repair_recall_min"],
        "unsupported_addition_repair_recall_min": metrics["unsupported_addition_repair_recall"] >= gates["unsupported_addition_repair_recall_min"],
        "policy_realization_repair_recall_min": metrics["policy_realization_repair_recall"] >= gates["policy_realization_repair_recall_min"],
        "safe_noninterference_rate_min": metrics["safe_noninterference_rate"] >= gates["safe_noninterference_rate_min"],
        "protected_route_noninterference_rate_min": metrics["protected_route_noninterference_rate"] >= gates["protected_route_noninterference_rate_min"],
        "post_repair_policy_act_match_min": metrics["post_repair_policy_act_match"] >= gates["post_repair_policy_act_match_min"],
        "post_repair_forbidden_concept_rate_max": metrics["post_repair_forbidden_concept_rate"] <= gates["post_repair_forbidden_concept_rate_max"],
        "visible_japanese_format_rate_min": metrics["visible_japanese_format_rate"] >= gates["visible_japanese_format_rate_min"],
        "formal_register_rate_max": metrics["formal_register_rate"] <= gates["formal_register_rate_max"],
        "raw_dialogue_persistence_max": metrics["raw_dialogue_persistence_count"] <= gates["raw_dialogue_persistence_count_max"],
        "unverified_mental_fact_write_max": metrics["unverified_mental_fact_write_count"] <= gates["unverified_mental_fact_write_count_max"],
        "p95_verifier_latency_seconds_max": metrics["p95_verifier_latency_seconds"] <= gates["p95_verifier_latency_seconds_max"],
    }
    return {
        "schema": "uruha_m39_semantic_persona_surface_reserve_result_v1",
        "reserve_validation": validation,
        "baseline": "pre_m39_metadata_only_surface_audit",
        "intervention": "m39_semantic_persona_surface_verifier",
        "metrics": metrics,
        "gate_results": gate_results,
        "decision": "pass_all_frozen_gates" if all(gate_results.values()) else "fail_one_or_more_frozen_gates",
        "rows": rows,
        "raw_source_or_reply_text_in_result_rows": False,
        "human_felt_understanding_evidence_available": False,
        "claim_boundary": protocol.get("claim_boundary"),
    }


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default=str(DEFAULT_DATASET))
    parser.add_argument("--protocol", default=str(DEFAULT_PROTOCOL))
    parser.add_argument("--output")
    args = parser.parse_args(argv)
    dataset_path = Path(args.dataset)
    protocol_path = Path(args.protocol)
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    result = evaluate(dataset, protocol)
    result["dataset_path"] = str(dataset_path.relative_to(BASE_DIR)) if dataset_path.is_relative_to(BASE_DIR) else str(dataset_path)
    result["dataset_sha256"] = _sha256(dataset_path)
    result["protocol_path"] = str(protocol_path.relative_to(BASE_DIR)) if protocol_path.is_relative_to(BASE_DIR) else str(protocol_path)
    result["protocol_sha256"] = _sha256(protocol_path)
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        output = Path(args.output)
        if output.exists():
            raise FileExistsError(f"refusing to overwrite formal result: {output}")
        output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
