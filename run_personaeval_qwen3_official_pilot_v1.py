#!/usr/bin/env python3
"""Run and score the frozen local Qwen3 PersonaEval pilot."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import resource
import statistics
import sys
import time
from pathlib import Path

import mlx.core as mx
from mlx_lm import batch_generate, load
from mlx_lm.sample_utils import make_sampler

import build_personaeval_qwen3_official_pilot_v1 as construction


ROOT = Path(__file__).resolve().parent
EXPERIMENT_ID = construction.EXPERIMENT_ID

if str(construction.JSON_REPAIR_TARGET) not in sys.path:
    sys.path.insert(0, str(construction.JSON_REPAIR_TARGET))
import json_repair  # noqa: E402


def _resolve_binding(binding):
    path = Path(binding["path"])
    if binding.get("scope") == "external_local" or path.is_absolute():
        return path
    return ROOT / path


def validate_lock(lock_path=construction.HARNESS_LOCK_PATH):
    lock = construction.load_json(lock_path)
    preregistration = construction.load_json(construction.PREREGISTRATION_PATH)
    bindings = []
    for binding in lock["bindings"]:
        path = _resolve_binding(binding)
        actual = construction.sha256_file(path) if path.is_file() else None
        bindings.append(
            {**binding, "actual_sha256": actual, "match": actual == binding["sha256"]}
        )
    environment = construction.local_environment()
    expected_environment = preregistration["local_environment"]
    authorization = lock["authorization"]
    pilot = preregistration["pilot_design"]
    passed = (
        lock["experiment_id"] == EXPERIMENT_ID
        and all(binding["match"] for binding in bindings)
        and environment == expected_environment
        and authorization["official_dataset_commit"]
        == construction.HF_DATASET_COMMIT
        and authorization["official_code_commit"]
        == construction.OFFICIAL_REPOSITORY_COMMIT
        and authorization["primary_row_count"] == pilot["primary_row_count"]
        and authorization["repeat_audit_row_count"]
        == len(pilot["repeat_audit_row_ids"])
        and authorization["generation_call_count"] == pilot["generation_call_count"]
        and authorization["label_file_loaded_after_all_generation_calls"] is True
        and authorization["training_updates"] == 0
        and authorization["memory_enabled"] is False
        and authorization["persona_prompt_enabled"] is False
        and authorization["production_runtime_change"] is False
    )
    return {
        "passed": passed,
        "bindings": bindings,
        "environment": environment,
        "lock": lock,
    }


def parse_official_probability_response(response, options):
    """Mirror PersonaEval parsing while enforcing actual probability bounds."""
    matches = re.findall(r"```\s*(.+?)\s*```", response, re.DOTALL)
    json_text = matches[-1] if matches else response
    parsed = json_repair.loads(json_text)
    if not isinstance(parsed, dict):
        raise ValueError("response JSON is not an object")
    probabilities = {}
    for option in options:
        if option not in parsed:
            raise ValueError(f"missing option: {option}")
        probability = float(parsed[option])
        if not math.isfinite(probability) or probability < 0.0 or probability > 1.0:
            raise ValueError(f"invalid probability for {option}: {probability}")
        probabilities[option] = probability
    total = sum(probabilities.values())
    if abs(total - 1.0) > 1e-5:
        raise ValueError(f"probabilities do not sum to one: {total}")
    return probabilities


def _prediction(probabilities):
    return max(probabilities, key=probabilities.get)


def _prompt_case(row):
    return {
        "row_id": row["row_id"],
        "track": row["track"],
        "source_row_index": row["source_row_index"],
        "option_count": row["option_count"],
        "options": row["options"],
        "prompt": row["prompt"],
        "prompt_sha256": row["prompt_sha256"],
    }


def _generate_cases(model, tokenizer, cases, preregistration, *, phase, repetition):
    controls = preregistration["controlled_variables"]
    prepared = []
    for case in cases:
        messages = [
            {"role": "system", "content": construction.SYSTEM_MESSAGE},
            {"role": "user", "content": case["prompt"]},
        ]
        rendered = tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        token_ids = tokenizer.encode(rendered)
        if len(token_ids) > int(controls["maximum_prompt_tokens"]):
            raise RuntimeError(
                f"prompt exceeds frozen token limit for {case['row_id']}: {len(token_ids)}"
            )
        prepared.append((case, token_ids))
    outputs = []
    batch_size = int(controls["batch_size"])
    batch_total = math.ceil(len(prepared) / batch_size)
    for batch_index, start in enumerate(range(0, len(prepared), batch_size), start=1):
        batch = prepared[start : start + batch_size]
        started = time.perf_counter()
        response = batch_generate(
            model,
            tokenizer,
            [token_ids for _, token_ids in batch],
            max_tokens=int(controls["maximum_new_tokens"]),
            sampler=make_sampler(temp=float(controls["temperature"])),
            verbose=False,
        )
        elapsed = time.perf_counter() - started
        if len(response.texts) != len(batch):
            raise RuntimeError("batch generation response count mismatch")
        for (case, token_ids), text in zip(batch, response.texts):
            output = text.strip()
            outputs.append(
                {
                    "row_id": case["row_id"],
                    "track": case["track"],
                    "source_row_index": case["source_row_index"],
                    "prompt_sha256": case["prompt_sha256"],
                    "phase": phase,
                    "repetition": repetition,
                    "batch_index": batch_index,
                    "batch_size": len(batch),
                    "batch_generation_seconds": round(elapsed, 6),
                    "output": output,
                    "output_sha256": hashlib.sha256(output.encode("utf-8")).hexdigest(),
                    "prompt_tokens": len(token_ids),
                    "completion_tokens": len(tokenizer.encode(output)),
                    "generation_seconds": round(elapsed / len(batch), 6),
                }
            )
        print(
            f"{phase} repeat={repetition} batch {batch_index}/{batch_total} "
            f"rows={len(batch)} seconds={elapsed:.3f}",
            flush=True,
        )
    return outputs


def _score_output(generated, prompt, label):
    try:
        probabilities = parse_official_probability_response(
            generated["output"], prompt["options"]
        )
        prediction = _prediction(probabilities)
        sorted_options = sorted(
            prompt["options"], key=lambda option: probabilities[option], reverse=True
        )
        rank = sorted_options.index(label["ground_truth"]) + 1
        parse_success = True
        parse_error = None
    except Exception as error:
        probabilities = None
        prediction = None
        rank = None
        parse_success = False
        parse_error = f"{type(error).__name__}: {error}"
    return {
        **generated,
        "option_count": prompt["option_count"],
        "options": prompt["options"],
        "ground_truth": label["ground_truth"],
        "label_sha256": label["label_sha256"],
        "parse_success": parse_success,
        "parse_error": parse_error,
        "probabilities": probabilities,
        "prediction": prediction,
        "correct": prediction == label["ground_truth"],
        "ground_truth_rank": rank,
    }


def _wilson_interval(successes, total, z=1.959963984540054):
    if total <= 0:
        return [0.0, 1.0]
    proportion = successes / total
    denominator = 1.0 + z * z / total
    center = (proportion + z * z / (2.0 * total)) / denominator
    radius = (
        z
        * math.sqrt(
            proportion * (1.0 - proportion) / total + z * z / (4.0 * total * total)
        )
        / denominator
    )
    return [max(0.0, center - radius), min(1.0, center + radius)]


def _poisson_binomial_tail(probabilities, observed_successes):
    distribution = [1.0] + [0.0] * len(probabilities)
    for probability in probabilities:
        updated = [0.0] * len(distribution)
        for successes in range(len(distribution)):
            updated[successes] += distribution[successes] * (1.0 - probability)
            if successes:
                updated[successes] += distribution[successes - 1] * probability
        distribution = updated
    return sum(distribution[observed_successes:])


def _ece(rows, bins=20):
    parsed = [row for row in rows if row["parse_success"]]
    if not parsed:
        return None
    total = len(parsed)
    ece = 0.0
    for bin_index in range(bins):
        low = bin_index / bins
        high = (bin_index + 1) / bins
        bucket = []
        for row in parsed:
            confidence = max(row["probabilities"].values())
            if (confidence > low or (bin_index == 0 and confidence == 0.0)) and confidence <= high:
                bucket.append((confidence, float(row["correct"])))
        if bucket:
            average_confidence = statistics.fmean(item[0] for item in bucket)
            average_accuracy = statistics.fmean(item[1] for item in bucket)
            ece += len(bucket) / total * abs(average_confidence - average_accuracy)
    return ece


def _metrics(rows):
    total = len(rows)
    parsed = [row for row in rows if row["parse_success"]]
    correct = sum(row["correct"] for row in rows)
    top2_correct = sum(
        row["parse_success"] and row["ground_truth_rank"] <= 2 for row in rows
    )
    brier_terms = []
    for row in parsed:
        for option in row["options"]:
            target = 1.0 if option == row["ground_truth"] else 0.0
            brier_terms.append((row["probabilities"][option] - target) ** 2)
    chance_probabilities = [1.0 / row["option_count"] for row in rows]
    return {
        "row_count": total,
        "parsed_count": len(parsed),
        "parse_success_rate": len(parsed) / total if total else 0.0,
        "correct_count": correct,
        "unconditional_top1_accuracy": correct / total if total else 0.0,
        "unconditional_top1_wilson_95": _wilson_interval(correct, total),
        "conditional_top1_accuracy": correct / len(parsed) if parsed else 0.0,
        "unconditional_top2_accuracy": top2_correct / total if total else 0.0,
        "mean_ground_truth_rank_parsed": statistics.fmean(
            row["ground_truth_rank"] for row in parsed
        )
        if parsed
        else None,
        "brier_score_parsed": statistics.fmean(brier_terms) if brier_terms else None,
        "expected_calibration_error_parsed": _ece(rows),
        "random_choice_expected_accuracy": statistics.fmean(chance_probabilities)
        if chance_probabilities
        else None,
        "exact_chance_superiority_p_value": _poisson_binomial_tail(
            chance_probabilities, correct
        )
        if rows
        else None,
        "total_prompt_tokens": sum(row["prompt_tokens"] for row in rows),
        "total_completion_tokens": sum(row["completion_tokens"] for row in rows),
        "generation_seconds": sum(row["generation_seconds"] for row in rows),
    }


def _repeat_metrics(primary_rows, repeat_rows, audit_ids):
    by_key = {
        (row["row_id"], row["repetition"]): row
        for row in primary_rows + repeat_rows
        if row["row_id"] in audit_ids
    }
    details = []
    for row_id in audit_ids:
        rows = [by_key[(row_id, repetition)] for repetition in (1, 2, 3)]
        exact = len({row["output_sha256"] for row in rows}) == 1
        all_parsed = all(row["parse_success"] for row in rows)
        prediction_agreement = all_parsed and len(
            {row["prediction"] for row in rows}
        ) == 1
        details.append(
            {
                "row_id": row_id,
                "exact_output_agreement": exact,
                "all_repetitions_parsed": all_parsed,
                "prediction_agreement": prediction_agreement,
                "output_sha256": [row["output_sha256"] for row in rows],
                "predictions": [row["prediction"] for row in rows],
            }
        )
    return {
        "row_count": len(details),
        "exact_output_agreement_count": sum(
            row["exact_output_agreement"] for row in details
        ),
        "exact_output_agreement_rate": sum(
            row["exact_output_agreement"] for row in details
        )
        / len(details),
        "prediction_agreement_count": sum(
            row["prediction_agreement"] for row in details
        ),
        "prediction_agreement_rate": sum(
            row["prediction_agreement"] for row in details
        )
        / len(details),
        "details": details,
    }


def _decision(preregistration, metrics, repeat_metrics, lock_passed):
    gate = preregistration["decision_gate"]
    checks = {
        "lock_exact": lock_passed,
        "parse_success_gate": metrics["parse_success_rate"]
        >= gate["minimum_parse_success_rate"],
        "above_chance_gate": metrics["exact_chance_superiority_p_value"]
        <= gate["maximum_chance_superiority_p_value"],
        "wilson_lower_above_random_gate": metrics["unconditional_top1_wilson_95"][0]
        > metrics["random_choice_expected_accuracy"],
        "prediction_repeat_gate": repeat_metrics["prediction_agreement_rate"]
        >= gate["minimum_prediction_repeat_agreement"],
    }
    passed = all(checks.values())
    if passed:
        outcome = "pilot_supports_larger_official_personaeval_validation_only"
        next_step = "preregister_larger_official_personaeval_validation"
    elif not checks["lock_exact"]:
        outcome = "frozen_harness_contract_failed"
        next_step = "repair_harness_without_interpreting_model_scores"
    elif not checks["parse_success_gate"]:
        outcome = "local_persona_judge_not_operationally_parse_reliable"
        next_step = "diagnose_output_contract_or_reject_local_automated_judge"
    elif not checks["above_chance_gate"]:
        outcome = "local_persona_judge_not_significantly_above_random_choice"
        next_step = "reject_current_local_model_as_persona_judge"
    elif not checks["wilson_lower_above_random_gate"]:
        outcome = "local_persona_judge_accuracy_interval_overlaps_random_choice"
        next_step = "do_not_use_for_target_person_scoring"
    else:
        outcome = "local_persona_judge_not_reproducible"
        next_step = "diagnose_local_generation_nondeterminism"
    return {
        "experiment_complete": True,
        "passed": passed,
        "outcome": outcome,
        "checks": checks,
        "authorized_next_step": next_step,
        "authorize_larger_official_validation": passed,
        "authorize_target_person_judging": False,
        "authorize_human_rater_replacement": False,
        "authorize_training": False,
        "authorize_production": False,
    }


def run(lock_path=construction.HARNESS_LOCK_PATH):
    if construction.RAW_RESULT_PATH.exists() or construction.RESULT_PATH.exists():
        raise RuntimeError("refusing to overwrite existing formal PersonaEval result")
    if os.getenv("HF_HUB_OFFLINE") != "1" or os.getenv("TRANSFORMERS_OFFLINE") != "1":
        raise RuntimeError("PersonaEval pilot requires offline local-model mode")
    validation = validate_lock(lock_path)
    if not validation["passed"]:
        raise RuntimeError("frozen PersonaEval harness lock validation failed")
    preregistration = construction.load_json(construction.PREREGISTRATION_PATH)
    prompts_payload = construction.load_json(construction.PROMPTS_PATH)
    prompt_rows = [_prompt_case(row) for row in prompts_payload["rows"]]
    prompt_by_id = {row["row_id"]: row for row in prompt_rows}
    audit_ids = preregistration["pilot_design"]["repeat_audit_row_ids"]
    controls = preregistration["controlled_variables"]
    if len(prompt_rows) != preregistration["pilot_design"]["primary_row_count"]:
        raise RuntimeError("prompt row count does not match preregistration")

    started = time.perf_counter()
    event_order = []
    mx.set_default_device(mx.gpu)
    mx.set_memory_limit(32212254720)
    mx.set_wired_limit(22906503168)
    mx.reset_peak_memory()
    mx.random.seed(int(controls["seed"]))
    model, tokenizer = load(
        preregistration["model_contract"]["snapshot_root"],
        tokenizer_config={"trust_remote_code": True},
    )
    model.eval()
    mx.eval(model.parameters())
    event_order.append("model_loaded_without_adapter")

    generated = _generate_cases(
        model,
        tokenizer,
        prompt_rows,
        preregistration,
        phase="primary",
        repetition=1,
    )
    event_order.append("all_primary_generation_complete")

    repeat_generated = []
    for repetition, ordered_ids in (
        (2, list(reversed(audit_ids))),
        (3, list(audit_ids)),
    ):
        repeat_generated.extend(
            _generate_cases(
                model,
                tokenizer,
                [prompt_by_id[row_id] for row_id in ordered_ids],
                preregistration,
                phase="repeat_audit",
                repetition=repetition,
            )
        )
    event_order.append("all_generation_calls_complete")

    labels_payload = construction.load_json(construction.LABELS_PATH)
    event_order.append("labels_loaded_after_all_generation_calls")
    labels = {row["row_id"]: row for row in labels_payload["rows"]}
    if set(labels) != set(prompt_by_id):
        raise RuntimeError("label IDs do not match prompt IDs")

    scored_primary = [
        _score_output(row, prompt_by_id[row["row_id"]], labels[row["row_id"]])
        for row in generated
    ]
    scored_repeats = [
        _score_output(row, prompt_by_id[row["row_id"]], labels[row["row_id"]])
        for row in repeat_generated
    ]
    event_order.append("scoring_complete")

    overall = _metrics(scored_primary)
    per_track = {
        track: _metrics([row for row in scored_primary if row["track"] == track])
        for track in construction.TRACKS
    }
    repeat_metrics = _repeat_metrics(
        scored_primary, scored_repeats, audit_ids
    )
    decision = _decision(preregistration, overall, repeat_metrics, validation["passed"])
    raw = {
        "schema": "personaeval_qwen3_official_pilot_raw_v1",
        "experiment_id": EXPERIMENT_ID,
        "execution_success": True,
        "preregistration_sha256": construction.sha256_file(
            construction.PREREGISTRATION_PATH
        ),
        "harness_lock_sha256": construction.sha256_file(
            construction.HARNESS_LOCK_PATH
        ),
        "runtime_contract": {
            "model": construction.MODEL_NAME,
            "model_snapshot": construction.MODEL_SNAPSHOT.name,
            "device": str(mx.default_device()),
            "system_message": construction.SYSTEM_MESSAGE,
            "generic_json_only_transport_adapter": True,
            "official_prompt_changed": False,
            "temperature": controls["temperature"],
            "maximum_new_tokens": controls["maximum_new_tokens"],
            "generation_calls": len(generated) + len(repeat_generated),
            "optimizer_created": False,
            "optimizer_updates": 0,
            "adapter_initialized": False,
            "memory_loaded": False,
            "persona_prompt_loaded": False,
            "labels_loaded_after_all_generation_calls": True,
            "ground_truth_passed_to_model": False,
            "event_order": event_order,
        },
        "environment": validation["environment"],
        "primary": scored_primary,
        "repeat_audit": scored_repeats,
        "resource": {
            "duration_seconds": round(time.perf_counter() - started, 3),
            "mlx_peak_memory_bytes": mx.get_peak_memory(),
            "mlx_active_memory_bytes": mx.get_active_memory(),
            "mlx_cache_memory_bytes": mx.get_cache_memory(),
            "process_peak_resident_memory_bytes": resource.getrusage(
                resource.RUSAGE_SELF
            ).ru_maxrss,
        },
        "boundaries": preregistration["boundaries"],
    }
    construction.atomic_json(construction.RAW_RESULT_PATH, raw)
    result = {
        "schema": "personaeval_qwen3_official_pilot_result_v1",
        "experiment_id": EXPERIMENT_ID,
        "official_source": preregistration["official_provenance"],
        "pilot_design": preregistration["pilot_design"],
        "raw_result": construction.relative_binding(
            construction.RAW_RESULT_PATH, role="formal_raw_outputs_and_scores"
        ),
        "measurements": {
            "overall_balanced_pilot": overall,
            "per_track": per_track,
            "repeat_audit": repeat_metrics,
            "resource": raw["resource"],
        },
        "decision": decision,
        "evidence_boundary": preregistration["boundaries"],
    }
    construction.atomic_json(construction.RESULT_PATH, result)
    markdown = "\n".join(
        [
            "# PersonaEval Qwen3 official pilot result",
            "",
            f"- Outcome: `{decision['outcome']}`",
            f"- Passed pilot gate: `{decision['passed']}`",
            f"- Official balanced rows: `{overall['row_count']}`",
            f"- Parse success: `{overall['parsed_count']}/{overall['row_count']}` ({overall['parse_success_rate']:.3f})",
            f"- Unconditional Top-1: `{overall['correct_count']}/{overall['row_count']}` ({overall['unconditional_top1_accuracy']:.3f})",
            f"- Random-choice expectation: `{overall['random_choice_expected_accuracy']:.3f}`",
            f"- Exact above-chance p-value: `{overall['exact_chance_superiority_p_value']:.6f}`",
            f"- Prediction repeat agreement: `{repeat_metrics['prediction_agreement_count']}/{repeat_metrics['row_count']}` ({repeat_metrics['prediction_agreement_rate']:.3f})",
            f"- Exact-output repeat agreement: `{repeat_metrics['exact_output_agreement_count']}/{repeat_metrics['row_count']}` ({repeat_metrics['exact_output_agreement_rate']:.3f})",
            f"- Target-person judging / human replacement / production authorization: `False`",
            "",
        ]
    )
    construction.atomic_text(construction.RESULT_MD_PATH, markdown)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--lock", type=Path, default=construction.HARNESS_LOCK_PATH
    )
    args = parser.parse_args()
    result = run(args.lock)
    print(json.dumps(result["decision"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
