#!/usr/bin/env python3
"""Run the M10 behavior-authoritative language-realization diagnostic."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import random
import re
import sys
import time
from typing import Any, Callable
from urllib import error, request

from longitudinal_human_model.metrics import normalize_distribution
from longitudinal_human_model.realization import (
    CONDITIONS,
    DIRECT,
    ORACLE,
    PREDICTED,
    BEHAVIOR_JP,
    build_classifier_prompt,
    build_realization_packet,
    insert_padding,
    normalize_reply,
    padding_for_prompt_token_delta,
    parse_classifier_reply,
    render_realization_prompt,
    sha256_text,
)
from longitudinal_human_model.registry import (
    git_snapshot,
    load_json,
    runtime_snapshot,
    sha256_file,
    verify_lock,
    write_json_atomic,
)
import rightbrain_language_quality as rblq


ROOT = Path(__file__).resolve().parent


class M10ExecutionFailure(RuntimeError):
    def __init__(self, stage: str, completed: list[dict[str, Any]], cause: Exception):
        super().__init__(f"M10 failed during {stage}: {cause}")
        self.stage = stage
        self.completed = completed
        self.cause = cause


class OllamaTextProvider:
    def __init__(self, endpoint="http://127.0.0.1:11434/api/generate", timeout=240):
        self.endpoint = endpoint
        self.timeout = int(timeout)

    def __call__(self, *, model: str, prompt: str, options: dict[str, Any]) -> dict[str, Any]:
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "think": False,
            "options": dict(options),
        }
        http_request = request.Request(
            self.endpoint,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        started = time.perf_counter()
        try:
            with request.urlopen(http_request, timeout=self.timeout) as response:
                body = json.loads(response.read().decode("utf-8"))
        except (error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"Ollama text request failed: {exc}") from exc
        if not isinstance(body, dict) or not isinstance(body.get("response"), str):
            raise RuntimeError("Ollama text response did not contain response text")
        return {
            "text": body["response"],
            "latency_seconds": time.perf_counter() - started,
            "prompt_tokens": int(body.get("prompt_eval_count") or 0),
            "completion_tokens": int(body.get("eval_count") or 0),
            "total_duration_ns": int(body.get("total_duration") or 0),
            "model_reported": body.get("model"),
        }


def _provider_record(result: dict[str, Any], prompt: str, *, stage: str) -> dict[str, Any]:
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


def visible_contract(reply: str) -> dict[str, bool]:
    text = str(reply or "").strip()
    return {
        "nonempty": bool(text),
        "japanese_present": rblq.has_japanese(text),
        "no_foreign_or_nonstandard_language": not rblq.has_bad_language(
            text, reject_latin=True, include_audited_residue=True
        ),
        "no_polite_register": not bool(rblq.POLITE_RE.search(text)),
        "no_watashi_first_person": "私" not in text,
        "no_quote_wrapper": not bool(re.search(r"[\"'“”‘’「」『』]", text)),
        "no_analysis_or_label_dump": not any(
            marker.lower() in text.lower()
            for marker in ("probabilities", "selected_behavior", "confidence", "JSON", "分析")
        ),
        "no_private_person_claim": not any(
            marker in text for marker in ("子供の頃", "幼い頃", "家族との思い出", "本当の記憶")
        ),
        "no_mindreading_claim": not any(
            marker in text for marker in ("全部分かる", "心が読める", "絶対そう")
        ),
        "within_96_characters": len(text) <= 96,
    }


def _case_maps(dataset: dict[str, Any], result: dict[str, Any], config: dict[str, Any]):
    labels = list(dataset["taxonomy"]["labels"])
    events = {row["event_id"]: row for row in dataset["events"]}
    predictions = {
        row["sample_id"]: row
        for row in result["rows"]
        if row.get("condition") == config["case_contract"]["source_condition"]
    }
    return labels, events, predictions


def validate_inputs(
    dataset: dict[str, Any],
    result: dict[str, Any],
    persona: dict[str, Any],
    persona_lock: dict[str, Any],
    config: dict[str, Any],
) -> dict[str, Any]:
    errors = []
    labels, events, predictions = _case_maps(dataset, result, config)
    if set(labels) != set(BEHAVIOR_JP):
        errors.append("taxonomy differs from realization contract")
    expected = int(config["case_contract"]["case_count"])
    if len(predictions) != expected:
        errors.append(f"M9 source prediction count {len(predictions)} != {expected}")
    missing_events = sorted(set(predictions) - set(events))
    if missing_events:
        errors.append(f"missing dataset events: {missing_events}")
    cutoff_counts = Counter(row.get("cutoff_id") for row in predictions.values())
    if dict(sorted(cutoff_counts.items())) != config["case_contract"]["cutoff_counts"]:
        errors.append(f"cutoff counts differ: {dict(cutoff_counts)}")
    if result.get("language_realization_performed") is not False:
        errors.append("M9 source result already performed language realization")
    authorizations = persona_lock.get("authorizations") or {}
    if authorizations.get("development_hypothesis_use") is not True:
        errors.append("persona development hypothesis use is not authorized")
    for forbidden in ("runtime_persona_activation", "public_persona_fidelity_claim", "private_person_copy_claim"):
        if authorizations.get(forbidden) is not False:
            errors.append(f"persona authorization unexpectedly true: {forbidden}")
    evidence_ids = {row["evidence_id"] for row in persona.get("evidence") or []}
    required_ids = {"persona_dev_v1_002", "persona_dev_v1_003", "persona_dev_v1_004"}
    if not required_ids.issubset(evidence_ids):
        errors.append("required development surface evidence missing")
    return {
        "valid": not errors,
        "errors": errors,
        "case_count": len(predictions),
        "cutoff_counts": dict(sorted(cutoff_counts.items())),
        "label_count": len(labels),
        "persona_evidence_refs": sorted(required_ids),
        "source_language_realization_performed": result.get("language_realization_performed"),
    }


def _call_provider(
    provider: Callable[..., dict[str, Any]],
    *,
    model: str,
    prompt: str,
    options: dict[str, Any],
    stage: str,
    completed: list[dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    try:
        response = provider(model=model, prompt=prompt, options=options)
    except Exception as exc:
        raise M10ExecutionFailure(stage, completed, exc) from exc
    record = _provider_record(response, prompt, stage=stage)
    completed.append(record)
    return response, record


def _balanced_prompts(
    prompts: dict[str, str],
    *,
    config: dict[str, Any],
    provider: Callable[..., dict[str, Any]],
    sample_id: str,
    completed: list[dict[str, Any]],
) -> tuple[dict[str, str], dict[str, Any]]:
    options = dict(config["generation_options"])
    options["num_predict"] = int(config["prompt_balance"]["preflight_num_predict"])
    counts = {}
    records = {}
    for condition in CONDITIONS:
        _, record = _call_provider(
            provider,
            model=config["model"],
            prompt=prompts[condition],
            options=options,
            stage=f"preflight::{sample_id}::{condition}",
            completed=completed,
        )
        counts[condition] = record["prompt_tokens"]
        records[condition] = record
    target = max(counts.values())
    balanced = {
        condition: insert_padding(
            prompts[condition], padding_for_prompt_token_delta(target - counts[condition])
        )
        for condition in CONDITIONS
    }
    return balanced, {
        "initial_prompt_tokens": counts,
        "target_prompt_tokens": target,
        "one_preflight_each_condition": True,
        "records": records,
    }


def _condition_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    count = len(rows)
    authority_rows = [row for row in rows if row["authority_behavior"]]
    return {
        "row_count": count,
        "visible_contract_pass_count": sum(row["visible_contract_pass"] for row in rows),
        "visible_contract_pass_rate": round(
            sum(row["visible_contract_pass"] for row in rows) / count, 6
        ) if count else 0.0,
        "authority_alignment_count": sum(row["authority_alignment"] is True for row in authority_rows),
        "authority_alignment_rate": (
            round(sum(row["authority_alignment"] is True for row in authority_rows) / len(authority_rows), 6)
            if authority_rows else None
        ),
        "outcome_alignment_count": sum(row["outcome_alignment"] for row in rows),
        "outcome_alignment_rate": round(
            sum(row["outcome_alignment"] for row in rows) / count, 6
        ) if count else 0.0,
        "prompt_tokens": sum(row["generation"]["prompt_tokens"] for row in rows),
        "completion_tokens": sum(row["generation"]["completion_tokens"] for row in rows),
        "generation_latency_seconds": round(
            sum(row["generation"]["latency_seconds"] for row in rows), 6
        ),
        "classifier_latency_seconds": round(
            sum(row["classifier"]["latency_seconds"] for row in rows), 6
        ),
    }


def run_experiment(
    dataset: dict[str, Any],
    m9_result: dict[str, Any],
    persona: dict[str, Any],
    persona_lock: dict[str, Any],
    config: dict[str, Any],
    *,
    text_provider: Callable[..., dict[str, Any]],
    classifier_provider: Callable[..., dict[str, Any]],
) -> dict[str, Any]:
    validation = validate_inputs(dataset, m9_result, persona, persona_lock, config)
    if not validation["valid"]:
        raise ValueError("invalid M10 inputs: " + "; ".join(validation["errors"]))
    labels, events, predictions = _case_maps(dataset, m9_result, config)
    completed: list[dict[str, Any]] = []
    rows = []
    prompt_ranges = {}
    case_ids = sorted(predictions, key=lambda sample: (predictions[sample]["cutoff_id"], sample))
    for case_index, sample_id in enumerate(case_ids):
        event = events[sample_id]
        prediction = predictions[sample_id]
        packets = {
            condition: build_realization_packet(
                condition=condition,
                event=event,
                prediction=prediction,
                labels=labels,
                persona_evidence_refs=validation["persona_evidence_refs"],
            )
            for condition in CONDITIONS
        }
        prompts = {condition: render_realization_prompt(packets[condition]) for condition in CONDITIONS}
        prompts, preflight = _balanced_prompts(
            prompts,
            config=config,
            provider=text_provider,
            sample_id=sample_id,
            completed=completed,
        )
        order = list(CONDITIONS)
        random.Random(int(config["generation_options"]["seed"]) + case_index).shuffle(order)
        case_rows = []
        for condition in order:
            response, generation = _call_provider(
                text_provider,
                model=config["model"],
                prompt=prompts[condition],
                options=dict(config["generation_options"]),
                stage=f"generation::{sample_id}::{condition}",
                completed=completed,
            )
            reply = normalize_reply(response["text"])
            classifier_prompt = build_classifier_prompt(event["observable_text"], reply, labels)
            classifier_response, classifier_record = _call_provider(
                classifier_provider,
                model=config["model"],
                prompt=classifier_prompt,
                options=dict(config["classifier_options"]),
                stage=f"classifier::{sample_id}::{condition}",
                completed=completed,
            )
            try:
                decoded = parse_classifier_reply(classifier_response["text"], labels)
            except Exception as exc:
                raise M10ExecutionFailure(
                    f"classifier_parse::{sample_id}::{condition}", completed, exc
                ) from exc
            authority = packets[condition]["behavior_authority"]
            contract = visible_contract(reply)
            row = {
                "sample_id": sample_id,
                "cutoff_id": prediction["cutoff_id"],
                "condition": condition,
                "event_context": event["observable_text"],
                "actual_observed_behavior": event["actual_observed_behavior"],
                "authority_behavior": authority["selected_behavior"],
                "authority_source": authority["source"],
                "future_information_used": authority["future_information_used"],
                "upstream_probabilities": authority["probabilities"],
                "reply": reply,
                "visible_contract": contract,
                "visible_contract_pass": all(contract.values()),
                "decoded_behavior": decoded["selected_behavior"],
                "decoded_probabilities": decoded["probabilities"],
                "decoder_brief_evidence": decoded["brief_evidence"],
                "authority_alignment": (
                    None
                    if not authority["selected_behavior"]
                    else decoded["selected_behavior"] == authority["selected_behavior"]
                ),
                "outcome_alignment": decoded["selected_behavior"] == event["actual_observed_behavior"],
                "generation": generation,
                "classifier": classifier_record,
                "prompt_sha256": sha256_text(prompts[condition]),
                "packet_sha256": sha256_text(
                    json.dumps(packets[condition], ensure_ascii=False, sort_keys=True, separators=(",", ":"))
                ),
                "persona_scope": "development_surface_hypothesis_only",
            }
            case_rows.append(row)
            rows.append(row)
        scored_counts = {row["condition"]: row["generation"]["prompt_tokens"] for row in case_rows}
        prompt_range = max(scored_counts.values()) - min(scored_counts.values())
        prompt_ranges[sample_id] = {
            "preflight": preflight,
            "scored_prompt_tokens": scored_counts,
            "scored_prompt_token_range": prompt_range,
            "gate_passed": prompt_range <= int(config["prompt_balance"]["scored_prompt_token_range_at_most"]),
        }

    metrics = {
        condition: _condition_metrics([row for row in rows if row["condition"] == condition])
        for condition in CONDITIONS
    }
    private_or_mindreading_count = sum(
        not row["visible_contract"]["no_private_person_claim"]
        or not row["visible_contract"]["no_mindreading_claim"]
        for row in rows
    )
    hypotheses = {
        "all_scored_prompt_token_ranges_at_most": all(
            record["gate_passed"] for record in prompt_ranges.values()
        ),
        "predicted_authority_alignment_at_least": metrics[PREDICTED]["authority_alignment_rate"]
        >= float(config["falsifiable_hypotheses"]["predicted_authority_alignment_at_least"]),
        "oracle_authority_alignment_at_least": metrics[ORACLE]["authority_alignment_rate"]
        >= float(config["falsifiable_hypotheses"]["oracle_authority_alignment_at_least"]),
        "predicted_visible_contract_at_least": metrics[PREDICTED]["visible_contract_pass_rate"]
        >= float(config["falsifiable_hypotheses"]["predicted_visible_contract_at_least"]),
        "oracle_visible_contract_at_least": metrics[ORACLE]["visible_contract_pass_rate"]
        >= float(config["falsifiable_hypotheses"]["oracle_visible_contract_at_least"]),
        "oracle_outcome_alignment_at_least_predicted": metrics[ORACLE]["outcome_alignment_rate"]
        >= metrics[PREDICTED]["outcome_alignment_rate"],
        "oracle_outcome_alignment_strictly_above_direct": metrics[ORACLE]["outcome_alignment_rate"]
        > metrics[DIRECT]["outcome_alignment_rate"],
        "predicted_outcome_alignment_at_least_direct": metrics[PREDICTED]["outcome_alignment_rate"]
        >= metrics[DIRECT]["outcome_alignment_rate"],
        "private_or_mindreading_claim_count": private_or_mindreading_count
        == int(config["falsifiable_hypotheses"]["private_or_mindreading_claim_count"]),
    }
    resources = {
        "preflight_calls": sum(record["stage"].startswith("preflight::") for record in completed),
        "generation_calls": sum(record["stage"].startswith("generation::") for record in completed),
        "classifier_calls": sum(record["stage"].startswith("classifier::") for record in completed),
        "total_model_calls": len(completed),
        "prompt_tokens": sum(record["prompt_tokens"] for record in completed),
        "completion_tokens": sum(record["completion_tokens"] for record in completed),
        "model_latency_seconds": round(sum(record["latency_seconds"] for record in completed), 6),
        "production_memory_writes": 0,
        "tool_or_physical_actions": 0,
    }
    return {
        "schema": "ilhdt_m10_behavior_authoritative_language_result_v1",
        "status": "complete_hypothesis_run",
        "claim_level": config["claim_level"],
        "formal_target_claim": False,
        "validation": validation,
        "conditions": list(CONDITIONS),
        "rows": rows,
        "metrics": metrics,
        "prompt_balance": prompt_ranges,
        "hypothesis_checks": hypotheses,
        "all_hypotheses_supported": all(hypotheses.values()),
        "classifier_evidence_boundary": "Same-model structured classifier proxy only; not human behavior-fit, naturalness, or persona evidence.",
        "human_preference_supported": False,
        "human_preference_reason": "No independent blind ratings have been collected for the M10 packet.",
        "persona_boundary": config["persona_boundary"],
        "resources": resources,
        "provider_records": completed,
        "non_claims": list(config["non_claims"]),
    }


def build_blind_packet(result: dict[str, Any], *, seed=20260815):
    by_case = {}
    for row in result["rows"]:
        by_case.setdefault(row["sample_id"], []).append(row)
    items, key_items = [], []
    for index, sample_id in enumerate(sorted(by_case), start=1):
        rows = list(by_case[sample_id])
        random.Random(int(seed) + index).shuffle(rows)
        labels = ["A", "B", "C"]
        candidates = {label: row["reply"] for label, row in zip(labels, rows)}
        mapping = {label: row["condition"] for label, row in zip(labels, rows)}
        first = rows[0]
        items.append(
            {
                "item_id": f"m10-blind-{index:03d}",
                "sample_id": sample_id,
                "event_context": first["event_context"],
                "observable_outcome_label": first["actual_observed_behavior"],
                "observable_outcome_description_jp": BEHAVIOR_JP[first["actual_observed_behavior"]],
                "candidates": candidates,
                "rating_dimensions": [
                    "behavior_fit",
                    "natural_japanese",
                    "non_overclaiming",
                    "development_surface_naturalness",
                ],
                "instruction": "条件名を推測せず、各候補を1〜5で評価し、最も自然に観察行動を表す候補を一つ選ぶ。",
            }
        )
        key_items.append({"item_id": f"m10-blind-{index:03d}", "mapping": mapping})
    packet = {
        "schema": "ilhdt_m10_blind_three_way_language_packet_v1",
        "status": "instrument_only_human_ratings_pending",
        "condition_labels_hidden": True,
        "minimum_complete_independent_raters_for_claim": 3,
        "items": items,
        "evidence_boundary": "This packet is an instrument, not a human-preference result or Uruha-fidelity score.",
    }
    key = {
        "schema": "ilhdt_m10_blind_three_way_language_key_v1",
        "seed": int(seed),
        "items": key_items,
    }
    return packet, key


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
    loaded = {
        name: load_json(ROOT / record["path"])
        for name, record in config["inputs"].items()
    }
    validation = validate_inputs(
        loaded["second_person_dataset"],
        loaded["m9_result"],
        loaded["persona_evidence"],
        loaded["persona_evidence_result_lock"],
        config,
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
        raise SystemExit("M10 frozen validation failed")
    if not args.output or not args.blind_packet or not args.blind_key:
        raise SystemExit("--output, --blind-packet, and --blind-key are required")
    text_provider = OllamaTextProvider(timeout=int(config["provider_timeout_seconds"]))
    classifier_provider = OllamaTextProvider(timeout=int(config["provider_timeout_seconds"]))
    try:
        result = run_experiment(
            loaded["second_person_dataset"],
            loaded["m9_result"],
            loaded["persona_evidence"],
            loaded["persona_evidence_result_lock"],
            config,
            text_provider=text_provider,
            classifier_provider=classifier_provider,
        )
    except M10ExecutionFailure as exc:
        result = {
            "schema": "ilhdt_m10_behavior_authoritative_language_result_v1",
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
    print(
        json.dumps(
            {
                "output": str(ROOT / args.output),
                "status": result["status"],
                "all_hypotheses_supported": result.get("all_hypotheses_supported"),
                "resources": result.get("resources"),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if result.get("status") == "complete_hypothesis_run" else 3


if __name__ == "__main__":
    raise SystemExit(main())
