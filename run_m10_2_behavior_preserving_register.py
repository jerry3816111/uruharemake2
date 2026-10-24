#!/usr/bin/env python3
"""Run the source-disjoint M10.2 casual-register remediation."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import random
import sys
from typing import Any, Callable

from longitudinal_human_model.realization import (
    PREDICTED,
    build_classifier_prompt,
    build_realization_packet,
    normalize_reply,
    render_realization_prompt,
    sha256_text,
)
from longitudinal_human_model.realization_parser_v1_1 import ClassifierAliasParser
from longitudinal_human_model.register_repair import (
    CONDITIONS,
    ONE_PASS,
    REGISTER_REPAIR,
    build_register_repair_packet,
    render_register_repair_prompt,
)
from longitudinal_human_model.registry import (
    git_snapshot,
    load_json,
    runtime_snapshot,
    sha256_file,
    verify_lock,
    write_json_atomic,
)
import run_m10_behavior_authoritative_language as m10


ROOT = Path(__file__).resolve().parent


class M102ExecutionFailure(RuntimeError):
    def __init__(self, stage, completed, cause):
        super().__init__(f"M10.2 failed during {stage}: {cause}")
        self.stage = stage
        self.completed = completed
        self.cause = cause


def _record(result, prompt, stage):
    return {
        "stage": stage,
        "prompt_sha256": sha256_text(prompt),
        "raw_response": str(result.get("text") or ""),
        "raw_response_sha256": sha256_text(str(result.get("text") or "")),
        "latency_seconds": round(float(result.get("latency_seconds") or 0.0), 6),
        "prompt_tokens": int(result.get("prompt_tokens") or 0),
        "completion_tokens": int(result.get("completion_tokens") or 0),
        "total_duration_ns": int(result.get("total_duration_ns") or 0),
        "model_reported": result.get("model_reported"),
    }


def _call(provider, *, model, prompt, options, stage, completed):
    try:
        response = provider(model=model, prompt=prompt, options=options)
    except Exception as exc:
        raise M102ExecutionFailure(stage, completed, exc) from exc
    record = _record(response, prompt, stage)
    completed.append(record)
    return response, record


def validate_inputs(fixture, m10_result_lock, m10_result, persona, persona_lock, config):
    errors = []
    cases = list(fixture.get("cases") or [])
    expected = int(config["engineering_contract"]["case_count"])
    if len(cases) != expected:
        errors.append(f"case count {len(cases)} != {expected}")
    languages = {language: sum(row.get("language") == language for row in cases) for language in ("zh", "en", "ja")}
    if languages != {"zh": 6, "en": 6, "ja": 6}:
        errors.append(f"language imbalance: {languages}")
    labels = list(fixture.get("taxonomy", {}).get("labels") or [])
    label_counts = {label: sum(row.get("authoritative_behavior") == label for row in cases) for label in labels}
    if len(labels) != 6 or any(count != 3 for count in label_counts.values()):
        errors.append(f"label imbalance: {label_counts}")
    old_texts = {row.get("event_context") for row in m10_result.get("rows") or []}
    overlap = sorted({row.get("event_context") for row in cases} & old_texts)
    if overlap:
        errors.append(f"M10 event overlap: {overlap}")
    if m10_result_lock.get("result", {}).get("sha256") != hashlib.sha256(
        json.dumps(m10_result, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8") + b"\n"
    ).hexdigest():
        errors.append("M10 result does not match its result lock")
    authorizations = persona_lock.get("authorizations") or {}
    if authorizations.get("development_hypothesis_use") is not True:
        errors.append("persona development use unavailable")
    if any(authorizations.get(key) is not False for key in (
        "runtime_persona_activation", "public_persona_fidelity_claim", "private_person_copy_claim"
    )):
        errors.append("persona boundary authorization drift")
    evidence_ids = {row["evidence_id"] for row in persona.get("evidence") or []}
    refs = sorted({"persona_dev_v1_002", "persona_dev_v1_003", "persona_dev_v1_004"})
    if not set(refs).issubset(evidence_ids):
        errors.append("required style evidence missing")
    return {
        "valid": not errors,
        "errors": errors,
        "case_count": len(cases),
        "language_counts": languages,
        "label_counts": label_counts,
        "m10_event_overlap_count": len(overlap),
        "persona_evidence_refs": refs,
        "created_after_m10_failure_type_known": fixture.get("source_disjointness", {}).get("created_after_m10_failure_type_known"),
    }


def _authoritative_initial_packet(case, labels, persona_refs):
    behavior = case["authoritative_behavior"]
    one_hot = {label: float(label == behavior) for label in labels}
    event = {
        "observable_text": case["event_context"],
        "actual_observed_behavior": behavior,
        "previous_state": {},
    }
    prediction = {
        "selected_behavior": behavior,
        "probabilities": one_hot,
        "previous_state": {},
        "features": {},
    }
    packet = build_realization_packet(
        condition=PREDICTED,
        event=event,
        prediction=prediction,
        labels=labels,
        persona_evidence_refs=persona_refs,
    )
    packet["behavior_authority"]["source"] = "m10_2_fixture_authority_language_only"
    packet["relationship_context"] = case["relationship_context"]
    return packet


def _metrics(rows):
    count = len(rows)
    return {
        "row_count": count,
        "visible_contract_pass_count": sum(row["visible_contract_pass"] for row in rows),
        "visible_contract_pass_rate": round(sum(row["visible_contract_pass"] for row in rows) / count, 6),
        "authority_alignment_count": sum(row["authority_alignment"] for row in rows),
        "authority_alignment_rate": round(sum(row["authority_alignment"] for row in rows) / count, 6),
        "prompt_tokens": sum(row["generation"]["prompt_tokens"] for row in rows),
        "completion_tokens": sum(row["generation"]["completion_tokens"] for row in rows),
        "latency_seconds": round(sum(row["generation"]["latency_seconds"] for row in rows), 6),
    }


def run_experiment(
    fixture,
    m10_result_lock,
    m10_result,
    persona,
    persona_lock,
    config,
    *,
    provider: Callable[..., dict[str, Any]],
):
    validation = validate_inputs(fixture, m10_result_lock, m10_result, persona, persona_lock, config)
    if not validation["valid"]:
        raise ValueError("invalid M10.2 inputs: " + "; ".join(validation["errors"]))
    labels = list(fixture["taxonomy"]["labels"])
    completed = []
    parser = ClassifierAliasParser()
    rows = []
    pairs = []
    for case in sorted(fixture["cases"], key=lambda row: row["case_id"]):
        case_id = case["case_id"]
        initial_packet = _authoritative_initial_packet(case, labels, validation["persona_evidence_refs"])
        initial_prompt = render_realization_prompt(initial_packet)
        initial_response, initial_record = _call(
            provider,
            model=config["model"],
            prompt=initial_prompt,
            options=dict(config["generation_options"]),
            stage=f"initial::{case_id}",
            completed=completed,
        )
        initial_reply = normalize_reply(initial_response["text"])
        repair_packet = build_register_repair_packet(
            event_context=case["event_context"],
            relationship_context=case["relationship_context"],
            authoritative_behavior=case["authoritative_behavior"],
            original_utterance=initial_reply,
            persona_evidence_refs=validation["persona_evidence_refs"],
        )
        repair_prompt = render_register_repair_prompt(repair_packet)
        repair_response, repair_record = _call(
            provider,
            model=config["model"],
            prompt=repair_prompt,
            options=dict(config["generation_options"]),
            stage=f"repair::{case_id}",
            completed=completed,
        )
        repaired_reply = normalize_reply(repair_response["text"])
        case_rows = []
        for condition, reply, generation in (
            (ONE_PASS, initial_reply, initial_record),
            (REGISTER_REPAIR, repaired_reply, repair_record),
        ):
            classifier_prompt = build_classifier_prompt(case["event_context"], reply, labels)
            classifier_response, classifier_record = _call(
                provider,
                model=config["model"],
                prompt=classifier_prompt,
                options=dict(config["classifier_options"]),
                stage=f"classifier::{case_id}::{condition}",
                completed=completed,
            )
            try:
                decoded = parser(classifier_response["text"], labels)
            except Exception as exc:
                raise M102ExecutionFailure(f"classifier_parse::{case_id}::{condition}", completed, exc) from exc
            contract = m10.visible_contract(reply)
            row = {
                "case_id": case_id,
                "language": case["language"],
                "condition": condition,
                "event_context": case["event_context"],
                "relationship_context": case["relationship_context"],
                "authoritative_behavior": case["authoritative_behavior"],
                "reply": reply,
                "decoded_behavior": decoded["selected_behavior"],
                "decoded_probabilities": decoded["probabilities"],
                "authority_alignment": decoded["selected_behavior"] == case["authoritative_behavior"],
                "visible_contract": contract,
                "visible_contract_pass": all(contract.values()),
                "generation": generation,
                "classifier": classifier_record,
                "generation_prompt_sha256": sha256_text(initial_prompt if condition == ONE_PASS else repair_prompt),
                "persona_scope": "development_surface_hypothesis_only",
            }
            rows.append(row)
            case_rows.append(row)
        pairs.append({
            "case_id": case_id,
            "reply_changed": initial_reply != repaired_reply,
            "one_pass_aligned": case_rows[0]["authority_alignment"],
            "repair_aligned": case_rows[1]["authority_alignment"],
            "aligned_to_misaligned_regression": case_rows[0]["authority_alignment"] and not case_rows[1]["authority_alignment"],
            "surface_changed_from_pass_to_fail": case_rows[0]["visible_contract_pass"] and not case_rows[1]["visible_contract_pass"],
        })
    metrics = {
        condition: _metrics([row for row in rows if row["condition"] == condition])
        for condition in CONDITIONS
    }
    regression_count = sum(pair["aligned_to_misaligned_regression"] for pair in pairs)
    changed_count = sum(pair["reply_changed"] for pair in pairs)
    private_or_mindreading_count = sum(
        not row["visible_contract"]["no_private_person_claim"]
        or not row["visible_contract"]["no_mindreading_claim"]
        for row in rows
    )
    contract = config["engineering_contract"]
    resources = {
        "initial_generation_calls": sum(row["stage"].startswith("initial::") for row in completed),
        "register_repair_calls": sum(row["stage"].startswith("repair::") for row in completed),
        "classifier_calls": sum(row["stage"].startswith("classifier::") for row in completed),
        "total_model_calls": len(completed),
        "prompt_tokens": sum(row["prompt_tokens"] for row in completed),
        "completion_tokens": sum(row["completion_tokens"] for row in completed),
        "model_latency_seconds": round(sum(row["latency_seconds"] for row in completed), 6),
        "scored_retries": 0,
        "production_memory_writes": 0,
    }
    all_calls_complete = (
        resources["initial_generation_calls"] == int(contract["initial_generation_calls"])
        and resources["register_repair_calls"] == int(contract["register_repair_calls"])
        and resources["classifier_calls"] == int(contract["classifier_calls"])
        and resources["total_model_calls"] == int(contract["total_model_calls"])
    )
    hypotheses = {
        "repair_visible_contract_at_least": metrics[REGISTER_REPAIR]["visible_contract_pass_rate"]
        >= float(config["falsifiable_hypotheses"]["repair_visible_contract_at_least"]),
        "repair_authority_alignment_at_least": metrics[REGISTER_REPAIR]["authority_alignment_rate"]
        >= float(config["falsifiable_hypotheses"]["repair_authority_alignment_at_least"]),
        "repair_authority_alignment_at_least_one_pass": metrics[REGISTER_REPAIR]["authority_alignment_rate"]
        >= metrics[ONE_PASS]["authority_alignment_rate"],
        "aligned_to_misaligned_regression_count": regression_count
        == int(config["falsifiable_hypotheses"]["aligned_to_misaligned_regression_count"]),
        "changed_reply_count_at_least": changed_count
        >= int(config["falsifiable_hypotheses"]["changed_reply_count_at_least"]),
        "private_or_mindreading_claim_count": private_or_mindreading_count
        == int(config["falsifiable_hypotheses"]["private_or_mindreading_claim_count"]),
        "all_calls_complete": all_calls_complete,
    }
    return {
        "schema": "ilhdt_m10_2_behavior_preserving_register_result_v1",
        "status": "complete_hypothesis_run" if all_calls_complete else "failed_engineering_gate",
        "claim_level": config["claim_level"],
        "formal_target_claim": False,
        "validation": validation,
        "rows": rows,
        "pairs": pairs,
        "metrics": metrics,
        "hypothesis_checks": hypotheses,
        "all_hypotheses_supported": all(hypotheses.values()),
        "changed_reply_count": changed_count,
        "aligned_to_misaligned_regression_count": regression_count,
        "surface_pass_to_fail_count": sum(pair["surface_changed_from_pass_to_fail"] for pair in pairs),
        "classifier_alias_normalizations": parser.normalizations,
        "classifier_evidence_boundary": "Same-model structured proxy only; not human naturalness or preference evidence.",
        "human_preference_supported": False,
        "human_preference_reason": "No independent ratings have been collected for the M10.2 blind packet.",
        "resources": resources,
        "provider_records": completed,
        "non_claims": list(config["non_claims"]),
    }


def build_blind_packet(result, *, seed=20260815):
    by_case = {}
    for row in result["rows"]:
        by_case.setdefault(row["case_id"], []).append(row)
    items, key_items = [], []
    for index, case_id in enumerate(sorted(by_case), start=1):
        rows = list(by_case[case_id])
        random.Random(int(seed) + index).shuffle(rows)
        labels = ("A", "B")
        items.append({
            "item_id": f"m10-2-blind-{index:03d}",
            "case_id": case_id,
            "event_context": rows[0]["event_context"],
            "authoritative_behavior": rows[0]["authoritative_behavior"],
            "candidates": {label: row["reply"] for label, row in zip(labels, rows)},
            "dimensions": ["semantic_preservation", "behavior_fit", "natural_casual_japanese", "non_overclaiming"],
        })
        key_items.append({
            "item_id": f"m10-2-blind-{index:03d}",
            "mapping": {label: row["condition"] for label, row in zip(labels, rows)},
        })
    return (
        {
            "schema": "ilhdt_m10_2_blind_register_packet_v1",
            "status": "instrument_only_human_ratings_pending",
            "minimum_complete_independent_raters_for_claim": 3,
            "items": items,
            "evidence_boundary": "Instrument only; no human preference result.",
        },
        {"schema": "ilhdt_m10_2_blind_register_key_v1", "seed": int(seed), "items": key_items},
    )


def parse_args(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("validate", "run"), default="validate")
    parser.add_argument("--config", required=True)
    parser.add_argument("--lock", required=True)
    parser.add_argument("--output")
    parser.add_argument("--blind-packet")
    parser.add_argument("--blind-key")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv or sys.argv[1:])
    config_path, lock_path = ROOT / args.config, ROOT / args.lock
    config, lock = load_json(config_path), load_json(lock_path)
    loaded = {name: load_json(ROOT / record["path"]) for name, record in config["inputs"].items()}
    result_path = ROOT / loaded["m10_result_lock"]["result"]["path"]
    m10_result = load_json(result_path)
    validation = validate_inputs(
        loaded["fixture"], loaded["m10_result_lock"], m10_result,
        loaded["persona_evidence"], loaded["persona_evidence_result_lock"], config,
    )
    errors = verify_lock(lock, repo_root=ROOT)
    for name, record in config["inputs"].items():
        if sha256_file(ROOT / record["path"]) != record["sha256"]:
            errors.append(f"input hash mismatch: {name}")
    validation["lock_errors"] = errors
    validation["valid"] = validation["valid"] and not errors
    validation["config_sha256"] = sha256_file(config_path)
    validation["lock_sha256"] = sha256_file(lock_path)
    if args.mode == "validate":
        print(json.dumps(validation, ensure_ascii=False, indent=2, sort_keys=True))
        return 0 if validation["valid"] else 2
    if not validation["valid"]:
        raise SystemExit("M10.2 frozen validation failed")
    if not args.output or not args.blind_packet or not args.blind_key:
        raise SystemExit("--output, --blind-packet, and --blind-key are required")
    provider = m10.OllamaTextProvider(timeout=int(config["provider_timeout_seconds"]))
    try:
        result = run_experiment(
            loaded["fixture"], loaded["m10_result_lock"], m10_result,
            loaded["persona_evidence"], loaded["persona_evidence_result_lock"], config,
            provider=provider,
        )
    except M102ExecutionFailure as exc:
        result = {
            "schema": "ilhdt_m10_2_behavior_preserving_register_result_v1",
            "status": "provider_failed_no_retry",
            "failed_stage": exc.stage,
            "error": str(exc.cause),
            "completed_records": exc.completed,
            "all_hypotheses_supported": False,
            "human_preference_supported": False,
        }
    result["validation"] = validation
    result["experiment_lock"] = lock
    result["environment"] = runtime_snapshot()
    result["git"] = git_snapshot(ROOT)
    write_json_atomic(ROOT / args.output, result)
    if result.get("status") == "complete_hypothesis_run":
        packet, key = build_blind_packet(result, seed=int(config["generation_options"]["seed"]))
        write_json_atomic(ROOT / args.blind_packet, packet)
        write_json_atomic(ROOT / args.blind_key, key)
    print(json.dumps({
        "output": str(ROOT / args.output),
        "status": result["status"],
        "all_hypotheses_supported": result.get("all_hypotheses_supported"),
        "metrics": result.get("metrics"),
        "resources": result.get("resources"),
    }, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "complete_hypothesis_run" else 3


if __name__ == "__main__":
    raise SystemExit(main())
