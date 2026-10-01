"""M38 sealed reserve evaluator.

The evaluator compares the frozen pre-M38 observer with the target-guarded
adapter on identical pending predictions and feedback turns.  It makes no LLM
call; the intervention is feedback linkage, not surface generation quality.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import time
from copy import deepcopy
from pathlib import Path

import uruha_adaptive_person_model as uapm
import uruha_counterfactual_pragmatic_branch_m34 as m34
from uruha_runtime import RuntimeState  # noqa: F401 - installs M38
from uruha_target_guarded_feedback_m38 import (
    adapt_observe_next_turn_m38,
    original_observe_next_turn_m38,
)


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_DATASET = BASE_DIR / "datasets/m38_target_guarded_multiscript_feedback_reserve_v1.json"
DEFAULT_PROTOCOL = BASE_DIR / "research/m38_target_guarded_multiscript_feedback_protocol_v1.json"
DEFAULT_PREFREEZE = BASE_DIR / "research/m38_preimplementation_reserve_freeze_2026-08-26.json"
DEFAULT_OUTPUT = BASE_DIR / "analysis/m38_target_guarded_multiscript_feedback_reserve_raw_2026-08-26.json"


def _sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _normalise_overlap(text):
    return "".join(character for character in str(text or "").lower() if character.isalnum())


def validate_reserve(dataset, protocol, prefreeze, *, m36_dataset=None):
    errors = []
    cases = list(dataset.get("cases") or [])
    if dataset.get("schema") != "uruha_m38_target_guarded_multiscript_feedback_reserve_v1":
        errors.append("unexpected_dataset_schema")
    if protocol.get("schema") != "uruha_m38_target_guarded_multiscript_feedback_protocol_v1":
        errors.append("unexpected_protocol_schema")
    if len(cases) != 18:
        errors.append(f"case_count:{len(cases)}")
    ids = [str(row.get("case_id") or "") for row in cases]
    if len(set(ids)) != len(ids) or any(not case_id for case_id in ids):
        errors.append("duplicate_or_empty_case_id")
    language_counts = {
        language: sum(row.get("language") == language for row in cases)
        for language in ("zh", "en", "ja")
    }
    if language_counts != {"zh": 6, "en": 6, "ja": 6}:
        errors.append(f"language_counts:{language_counts}")
    category_counts = {
        category: sum(row.get("category") == category for row in cases)
        for category in (
            "unique_target_correction",
            "ordinary_negation",
            "targetless_rejection",
        )
    }
    if category_counts != {
        "unique_target_correction": 9,
        "ordinary_negation": 6,
        "targetless_rejection": 3,
    }:
        errors.append(f"category_counts:{category_counts}")
    for row in cases:
        contradicted = row.get("expected_linkage") == "contradicted"
        replacement = row.get("expected_replacement_policy")
        if contradicted and (
            replacement not in {"listen_presence", "solve_regulation", "share_arousal", "playful_tease"}
            or replacement == row.get("previous_policy")
        ):
            errors.append(f"invalid_correction_target:{row.get('case_id')}")
        if not contradicted and replacement is not None:
            errors.append(f"noncorrection_has_target:{row.get('case_id')}")
    if m36_dataset:
        prior = {
            _normalise_overlap(row.get("feedback_input"))
            for row in (m36_dataset.get("cases") or [])
        }
        overlap = [
            row.get("case_id")
            for row in cases
            if _normalise_overlap(row.get("feedback_input")) in prior
        ]
        if overlap:
            errors.append(f"normalised_m36_overlap:{overlap}")
    return {
        "passed": not errors,
        "errors": errors,
        "case_count": len(cases),
        "language_counts": language_counts,
        "category_counts": category_counts,
        "prefreeze_dataset_sha256": ((prefreeze.get("dataset") or {}).get("sha256")),
        "prefreeze_protocol_sha256": ((prefreeze.get("protocol") or {}).get("sha256")),
    }


def _pending_model(policy_id, case_id):
    return uapm.set_pending_prediction(
        uapm.empty_model(),
        {
            "prediction_id": f"m38-{case_id}-pending",
            "selected": {
                "policy_id": policy_id,
                "expected_utility": 0.8,
                "response_dimensions": {},
                "realization": {},
            },
            "utility_margin": 0.2,
            "state": {
                "input_digest": hashlib.sha256(case_id.encode("utf-8")).hexdigest()[:16],
                "context_scope": {
                    "domain": "general_conversation",
                    "scene": "emotional_support",
                    "topic": "current_disclosure",
                    "relationship_band": "familiar",
                },
            },
            "implicit_desired_response_m26": {
                "status": "execute_implicit",
                "implicit_top_policy": policy_id,
                "implicit_top_mode": "m38_feedback_linkage_eval",
                "top_probability": 0.8,
                "probability_margin": 0.2,
                "evidence_quality": 0.8,
            },
        },
        turn_index=3,
    )


def _m34_revision(feedback, previous_policy, case_id):
    replacement = feedback.get("explicit_target_policy") or "listen_presence"
    decision_policy = replacement if replacement in {"listen_presence", "solve_regulation", "share_arousal", "playful_tease"} else "listen_presence"
    ledger = m34.build_counterfactual_pragmatic_branch_m34(
        pragmatic_understanding={"pragmatic_label": "feedback_linkage_eval"},
        desired_response_state={
            "input_digest": hashlib.sha256((case_id + "-feedback").encode("utf-8")).hexdigest()[:16],
            "context_scope": {"scope_id": "general:emotional_support"},
            "scope_match": {"status": "exact", "used": []},
        },
        desired_response_decision={
            "prediction_id": f"m38-{case_id}-new",
            "selected": {"policy_id": decision_policy, "expected_utility": 0.8},
            "candidates": [
                {"policy_id": decision_policy, "expected_utility": 0.8},
                {"policy_id": previous_policy, "expected_utility": 0.2},
            ],
        },
        implicit_response_contract={"execute_implicit": False, "distribution": []},
        adaptive_feedback=feedback,
        previous_branch_m34={
            "branch_id": f"m34-{case_id}-previous",
            "prediction_id": f"m38-{case_id}-pending",
            "selected_branch": {"policy_id": previous_policy},
        },
        turn_index=4,
    )
    return ledger.get("previous_branch_verification") or {}, ledger.get("revision") or {}


def _score_feedback(feedback, expected_outcome, expected_replacement):
    linked = bool(feedback.get("feedback_linked_to_previous_prediction"))
    status = str(feedback.get("status") or "not_available")
    replacement = feedback.get("explicit_target_policy")
    if expected_outcome == "contradicted":
        return linked and status == "contradicted" and replacement == expected_replacement
    return (not linked) and status in {"uncertain", "not_available"} and replacement in {None, ""}


def evaluate(dataset):
    original = original_observe_next_turn_m38()
    rows = []
    system_latencies = []
    for case in dataset.get("cases") or []:
        model = _pending_model(case["previous_policy"], case["case_id"])
        baseline_started = time.perf_counter()
        baseline_model, baseline_feedback = original(
            deepcopy(model), case["feedback_input"], turn_index=4
        )
        baseline_latency = time.perf_counter() - baseline_started
        system_started = time.perf_counter()
        system_model, system_feedback = adapt_observe_next_turn_m38(
            original,
            deepcopy(model),
            case["feedback_input"],
            turn_index=4,
        )
        system_latency = time.perf_counter() - system_started
        system_latencies.append(system_latency)
        baseline_verification, baseline_revision = _m34_revision(
            baseline_feedback, case["previous_policy"], case["case_id"]
        )
        system_verification, system_revision = _m34_revision(
            system_feedback, case["previous_policy"], case["case_id"]
        )
        expected = case["expected_linkage"]
        target = case.get("expected_replacement_policy")
        expected_revision = expected == "contradicted"
        rows.append(
            {
                "case_id": case["case_id"],
                "language": case["language"],
                "category": case["category"],
                "feedback_input_digest": hashlib.sha256(case["feedback_input"].encode("utf-8")).hexdigest()[:16],
                "expected_linkage": expected,
                "expected_replacement_policy": target,
                "baseline": {
                    "status": baseline_feedback.get("status"),
                    "linked": bool(baseline_feedback.get("feedback_linked_to_previous_prediction")),
                    "replacement_policy": baseline_feedback.get("explicit_target_policy"),
                    "outcome_correct": _score_feedback(baseline_feedback, expected, target),
                    "m34_verification": baseline_verification.get("status"),
                    "m34_revision": baseline_revision.get("status"),
                    "m34_replacement": baseline_revision.get("replacement_policy_id"),
                    "latency_seconds": round(baseline_latency, 6),
                },
                "system": {
                    "status": system_feedback.get("status"),
                    "linked": bool(system_feedback.get("feedback_linked_to_previous_prediction")),
                    "replacement_policy": system_feedback.get("explicit_target_policy"),
                    "m38_status": (system_feedback.get("target_guarded_feedback_m38") or {}).get("status"),
                    "outcome_correct": _score_feedback(system_feedback, expected, target),
                    "m34_verification": system_verification.get("status"),
                    "m34_revision": system_revision.get("status"),
                    "m34_replacement": system_revision.get("replacement_policy_id"),
                    "m34_revision_correct": (
                        system_revision.get("status") == "branch_revised"
                        and system_revision.get("replacement_policy_id") == target
                        if expected_revision
                        else system_revision.get("status") == "no_revision"
                    ),
                    "latency_seconds": round(system_latency, 6),
                },
                "raw_dialogue_persisted": case["feedback_input"] in json.dumps(system_model, ensure_ascii=False),
                "baseline_raw_dialogue_persisted": case["feedback_input"] in json.dumps(baseline_model, ensure_ascii=False),
                "unverified_mental_fact_write_count": int(system_revision.get("fact_memory_write_count") or 0),
            }
        )
    return rows, system_latencies


def summarize(rows, latencies, protocol):
    total = len(rows)
    corrections = [row for row in rows if row["category"] == "unique_target_correction"]
    ordinary = [row for row in rows if row["category"] == "ordinary_negation"]
    targetless = [row for row in rows if row["category"] == "targetless_rejection"]
    metrics = {
        "case_count": total,
        "baseline_linkage_outcome_accuracy": round(sum(row["baseline"]["outcome_correct"] for row in rows) / total, 4),
        "system_linkage_outcome_accuracy": round(sum(row["system"]["outcome_correct"] for row in rows) / total, 4),
        "system_unique_target_correction_recall": round(sum(row["system"]["outcome_correct"] for row in corrections) / len(corrections), 4),
        "system_replacement_policy_accuracy": round(sum(row["system"]["replacement_policy"] == row["expected_replacement_policy"] for row in corrections) / len(corrections), 4),
        "ordinary_negation_false_linkage_count": sum(row["system"]["linked"] for row in ordinary),
        "targetless_rejection_false_linkage_count": sum(row["system"]["linked"] for row in targetless),
        "system_m34_revision_accuracy": round(sum(row["system"]["m34_revision_correct"] for row in rows) / total, 4),
        "raw_dialogue_persistence_count": sum(row["raw_dialogue_persisted"] for row in rows),
        "unverified_mental_fact_write_count": sum(row["unverified_mental_fact_write_count"] for row in rows),
        "median_linkage_latency_seconds": round(statistics.median(latencies), 6),
        "p95_linkage_latency_seconds": round(sorted(latencies)[max(0, int(len(latencies) * 0.95) - 1)], 6),
        "model_generation_call_count": 0,
    }
    gates = protocol["frozen_gates"]
    gate_results = {
        "overall_linkage_accuracy_min": metrics["system_linkage_outcome_accuracy"] >= gates["overall_linkage_accuracy_min"],
        "unique_target_correction_recall_min": metrics["system_unique_target_correction_recall"] >= gates["unique_target_correction_recall_min"],
        "replacement_policy_accuracy_min": metrics["system_replacement_policy_accuracy"] >= gates["replacement_policy_accuracy_min"],
        "ordinary_negation_false_linkage_max": metrics["ordinary_negation_false_linkage_count"] <= gates["ordinary_negation_false_linkage_max"],
        "targetless_rejection_false_linkage_max": metrics["targetless_rejection_false_linkage_count"] <= gates["targetless_rejection_false_linkage_max"],
        "m34_contradiction_revision_accuracy_min": metrics["system_m34_revision_accuracy"] >= gates["m34_contradiction_revision_accuracy_min"],
        "raw_dialogue_persistence_max": metrics["raw_dialogue_persistence_count"] <= gates["raw_dialogue_persistence_max"],
        "unverified_mental_fact_write_max": metrics["unverified_mental_fact_write_count"] <= gates["unverified_mental_fact_write_max"],
        "p95_linkage_latency_seconds_max": metrics["p95_linkage_latency_seconds"] <= gates["p95_linkage_latency_seconds_max"],
    }
    return metrics, gate_results


def run(dataset_path, protocol_path, prefreeze_path, output_path):
    dataset_path = Path(dataset_path)
    protocol_path = Path(protocol_path)
    prefreeze_path = Path(prefreeze_path)
    output_path = Path(output_path)
    if output_path.exists():
        raise FileExistsError(f"formal output already exists: {output_path}")
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    prefreeze = json.loads(prefreeze_path.read_text(encoding="utf-8"))
    m36_dataset = json.loads((BASE_DIR / "datasets/m36_compositional_multilingual_pragmatic_reserve_v1.json").read_text(encoding="utf-8"))
    validation = validate_reserve(dataset, protocol, prefreeze, m36_dataset=m36_dataset)
    dataset_sha = _sha256(dataset_path)
    protocol_sha = _sha256(protocol_path)
    if dataset_sha != validation["prefreeze_dataset_sha256"]:
        validation["errors"].append("dataset_hash_differs_from_prefreeze")
    if protocol_sha != validation["prefreeze_protocol_sha256"]:
        validation["errors"].append("protocol_hash_differs_from_prefreeze")
    validation["passed"] = not validation["errors"]
    if not validation["passed"]:
        raise ValueError(f"reserve validation failed: {validation['errors']}")
    rows, latencies = evaluate(dataset)
    metrics, gate_results = summarize(rows, latencies, protocol)
    result = {
        "schema": "uruha_m38_target_guarded_multiscript_feedback_reserve_result_v1",
        "dataset_path": str(dataset_path.relative_to(BASE_DIR)),
        "dataset_sha256": dataset_sha,
        "protocol_path": str(protocol_path.relative_to(BASE_DIR)),
        "protocol_sha256": protocol_sha,
        "reserve_validation": validation,
        "intervention": protocol["intervention"],
        "baseline": protocol["baseline"],
        "metrics": metrics,
        "gate_results": gate_results,
        "decision": "pass_all_frozen_gates" if all(gate_results.values()) else "fail_one_or_more_frozen_gates",
        "rows": rows,
        "raw_feedback_text_in_result_rows": False,
        "human_felt_understanding_evidence_available": False,
        "claim_boundary": protocol["evidence_boundary"],
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default=str(DEFAULT_DATASET))
    parser.add_argument("--protocol", default=str(DEFAULT_PROTOCOL))
    parser.add_argument("--prefreeze", default=str(DEFAULT_PREFREEZE))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()
    result = run(args.dataset, args.protocol, args.prefreeze, args.output)
    print(json.dumps({"decision": result["decision"], "metrics": result["metrics"], "gate_results": result["gate_results"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
