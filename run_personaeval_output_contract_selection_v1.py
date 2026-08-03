#!/usr/bin/env python3
"""Run the frozen PersonaEval output-contract selection pilot."""

from __future__ import annotations

import hashlib
import json
import math
import os
import resource
import time
from pathlib import Path

import mlx.core as mx
from mlx_lm import batch_generate, load
from mlx_lm.sample_utils import make_sampler

import build_personaeval_output_contract_selection_v1 as construction
import build_personaeval_qwen3_official_pilot_v1 as base
import run_personaeval_qwen3_official_pilot_v1 as base_runner


ROOT = Path(__file__).resolve().parent


def _resolve_binding(binding):
    path = Path(binding["path"])
    if binding.get("scope") == "external_local" or path.is_absolute():
        return path
    return ROOT / path


def validate_lock(lock_path=construction.HARNESS_LOCK_PATH):
    lock = base.load_json(lock_path)
    prereg = base.load_json(construction.PREREGISTRATION_PATH)
    bindings = []
    for binding in lock["bindings"]:
        path = _resolve_binding(binding)
        actual = base.sha256_file(path) if path.is_file() else None
        bindings.append(
            {**binding, "actual_sha256": actual, "match": actual == binding["sha256"]}
        )
    auth = lock["authorization"]
    pilot = prereg["pilot_design"]
    passed = (
        lock["experiment_id"] == construction.EXPERIMENT_ID
        and all(binding["match"] for binding in bindings)
        and base.local_environment() == prereg["local_environment"]
        and auth["condition_order"] == list(construction.CONDITION_ORDER)
        and auth["primary_row_count"] == pilot["primary_row_count"]
        and auth["repeat_audit_row_count"] == len(pilot["repeat_audit_row_ids"])
        and auth["total_generation_calls"] == pilot["total_generation_calls"]
        and auth["batch_size"] == 1
        and auth["labels_loaded_after_all_generation"] is True
        and auth["training_updates"] == 0
        and auth["production_runtime_change"] is False
    )
    return {"passed": passed, "bindings": bindings, "lock": lock}


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


def _generate_cases(model, tokenizer, cases, prereg, *, condition, phase, repetition):
    controls = prereg["controlled_variables"]
    outputs = []
    for index, case in enumerate(cases, start=1):
        messages = [
            {"role": "system", "content": construction.SYSTEM_MESSAGES[condition]},
            {"role": "user", "content": case["prompt"]},
        ]
        rendered = tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        token_ids = tokenizer.encode(rendered)
        if len(token_ids) > controls["maximum_prompt_tokens"]:
            raise RuntimeError(f"prompt exceeds token limit: {case['row_id']}")
        started = time.perf_counter()
        response = batch_generate(
            model,
            tokenizer,
            [token_ids],
            max_tokens=controls["maximum_new_tokens"],
            sampler=make_sampler(temp=controls["temperature"]),
            verbose=False,
        ).texts[0].strip()
        elapsed = time.perf_counter() - started
        outputs.append(
            {
                "row_id": case["row_id"],
                "track": case["track"],
                "source_row_index": case["source_row_index"],
                "option_count": case["option_count"],
                "prompt_sha256": case["prompt_sha256"],
                "condition": condition,
                "phase": phase,
                "repetition": repetition,
                "output": response,
                "output_sha256": hashlib.sha256(response.encode("utf-8")).hexdigest(),
                "prompt_tokens": len(token_ids),
                "completion_tokens": len(tokenizer.encode(response)),
                "generation_seconds": round(elapsed, 6),
            }
        )
        print(
            f"{condition} {phase} repeat={repetition} row {index}/{len(cases)} "
            f"seconds={elapsed:.3f}",
            flush=True,
        )
    return outputs


def parse_candidate_name(response, options):
    if response not in options:
        raise ValueError("response is not exactly one official candidate name")
    return response


def _score_output(generated, prompt, label):
    condition = generated["condition"]
    try:
        if condition == "strict_probability":
            probabilities = base_runner.parse_official_probability_response(
                generated["output"], prompt["options"]
            )
            prediction = max(probabilities, key=probabilities.get)
        elif condition == "candidate_name":
            prediction = parse_candidate_name(generated["output"], prompt["options"])
            probabilities = None
        else:
            raise ValueError(f"unknown condition: {condition}")
        parse_success = True
        parse_error = None
    except Exception as exc:
        probabilities = None
        prediction = None
        parse_success = False
        parse_error = f"{type(exc).__name__}: {exc}"
    return {
        **generated,
        "ground_truth": label["ground_truth"],
        "label_sha256": label["label_sha256"],
        "parse_success": parse_success,
        "parse_error": parse_error,
        "probabilities": probabilities,
        "prediction": prediction,
        "correct": prediction == label["ground_truth"],
    }


def _metrics(rows):
    row_count = len(rows)
    parsed = sum(row["parse_success"] for row in rows)
    correct = sum(row["correct"] for row in rows)
    chance_probabilities = [1.0 / row["option_count"] for row in rows]
    return {
        "row_count": row_count,
        "parsed_count": parsed,
        "parse_success_rate": parsed / row_count,
        "correct_count": correct,
        "unconditional_top1_accuracy": correct / row_count,
        "unconditional_top1_wilson_95": base_runner._wilson_interval(correct, row_count),
        "random_choice_expected_accuracy": sum(chance_probabilities) / row_count,
        "exact_chance_superiority_p_value": base_runner._poisson_binomial_tail(
            chance_probabilities, correct
        ),
        "total_prompt_tokens": sum(row["prompt_tokens"] for row in rows),
        "total_completion_tokens": sum(row["completion_tokens"] for row in rows),
        "generation_seconds": sum(row["generation_seconds"] for row in rows),
    }


def _repeat_metrics(primary, repeats, audit_ids):
    by_key = {(row["row_id"], row["repetition"]): row for row in primary + repeats}
    details = []
    for row_id in audit_ids:
        rows = [by_key[(row_id, repetition)] for repetition in (1, 2, 3)]
        predictions = [row["prediction"] for row in rows]
        details.append(
            {
                "row_id": row_id,
                "exact_output_agreement": len({row["output_sha256"] for row in rows}) == 1,
                "all_repetitions_parsed": all(row["parse_success"] for row in rows),
                "prediction_agreement": (
                    all(row["parse_success"] for row in rows)
                    and len(set(predictions)) == 1
                ),
                "predictions": predictions,
                "output_sha256": [row["output_sha256"] for row in rows],
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


def paired_exact_mcnemar(strict_rows, candidate_rows):
    strict = {row["row_id"]: bool(row["correct"]) for row in strict_rows}
    candidate = {row["row_id"]: bool(row["correct"]) for row in candidate_rows}
    if set(strict) != set(candidate):
        raise ValueError("paired row IDs differ")
    strict_only = sum(strict[row_id] and not candidate[row_id] for row_id in strict)
    candidate_only = sum(candidate[row_id] and not strict[row_id] for row_id in strict)
    discordant = strict_only + candidate_only
    if discordant:
        tail = sum(
            math.comb(discordant, k)
            for k in range(min(strict_only, candidate_only) + 1)
        ) / (2**discordant)
        p_value = min(1.0, 2.0 * tail)
    else:
        p_value = 1.0
    return {
        "row_count": len(strict),
        "strict_only_correct": strict_only,
        "candidate_only_correct": candidate_only,
        "discordant_count": discordant,
        "exact_two_sided_mcnemar_p_value": p_value,
        "accuracy_delta_candidate_minus_strict": (candidate_only - strict_only)
        / len(strict),
    }


def _decision(prereg, measurements, paired, lock_passed):
    rule = prereg["decision_rule"]
    strict = measurements["strict_probability"]["overall"]
    candidate = measurements["candidate_name"]["overall"]
    repeat = measurements["candidate_name"]["repeat_audit"]
    checks = {
        "lock_exact": lock_passed,
        "candidate_parse_gate": candidate["parse_success_rate"]
        >= rule["candidate_minimum_parse_success_rate"],
        "candidate_above_chance_gate": candidate["exact_chance_superiority_p_value"]
        <= rule["candidate_maximum_chance_superiority_p_value"],
        "candidate_wilson_lower_above_random_gate": candidate[
            "unconditional_top1_wilson_95"
        ][0]
        > candidate["random_choice_expected_accuracy"],
        "candidate_repeat_gate": repeat["prediction_agreement_rate"]
        >= rule["candidate_minimum_prediction_repeat_agreement"],
        "parse_improvement_gate": candidate["parse_success_rate"]
        - strict["parse_success_rate"]
        >= rule["minimum_parse_improvement_over_strict"],
        "accuracy_noninferiority_point_gate": candidate["unconditional_top1_accuracy"]
        >= strict["unconditional_top1_accuracy"],
    }
    passed = all(checks.values())
    return {
        "experiment_complete": True,
        "passed": passed,
        "checks": checks,
        "paired_accuracy": paired,
        "selected_contract_for_larger_validation": "candidate_name" if passed else None,
        "authorize_larger_disjoint_adapted_evaluator_validation": passed,
        "authorize_target_person_judging": False,
        "authorize_human_rater_replacement": False,
        "authorize_training": False,
        "authorize_production": False,
    }


def run(lock_path=construction.HARNESS_LOCK_PATH):
    if construction.RAW_RESULT_PATH.exists() or construction.RESULT_PATH.exists():
        raise RuntimeError("refusing to overwrite formal output-contract result")
    if os.getenv("HF_HUB_OFFLINE") != "1" or os.getenv("TRANSFORMERS_OFFLINE") != "1":
        raise RuntimeError("output-contract pilot requires offline local-model mode")
    validation = validate_lock(lock_path)
    if not validation["passed"]:
        raise RuntimeError("frozen output-contract harness lock validation failed")
    prereg = base.load_json(construction.PREREGISTRATION_PATH)
    prompts_payload = base.load_json(construction.PROMPTS_PATH)
    prompt_rows = [_prompt_case(row) for row in prompts_payload["rows"]]
    prompt_by_id = {row["row_id"]: row for row in prompt_rows}
    audit_ids = prereg["pilot_design"]["repeat_audit_row_ids"]

    mx.set_default_device(mx.gpu)
    mx.set_memory_limit(32212254720)
    mx.set_wired_limit(22906503168)
    mx.reset_peak_memory()
    mx.random.seed(prereg["controlled_variables"]["seed"])
    model, tokenizer = load(
        prereg["model_contract"]["snapshot_root"],
        tokenizer_config={"trust_remote_code": True},
    )
    model.eval()
    mx.eval(model.parameters())
    started = time.perf_counter()
    generated = {}
    event_order = []
    for condition in construction.CONDITION_ORDER:
        primary = _generate_cases(
            model,
            tokenizer,
            prompt_rows,
            prereg,
            condition=condition,
            phase="primary",
            repetition=1,
        )
        repeats = []
        for repetition, ordered_ids in (
            (2, list(reversed(audit_ids))),
            (3, list(audit_ids)),
        ):
            repeats.extend(
                _generate_cases(
                    model,
                    tokenizer,
                    [prompt_by_id[row_id] for row_id in ordered_ids],
                    prereg,
                    condition=condition,
                    phase="repeat_audit",
                    repetition=repetition,
                )
            )
        generated[condition] = {"primary": primary, "repeat_audit": repeats}
        event_order.append(f"{condition}_all_generation_complete")
    event_order.append("both_conditions_all_generation_complete")

    labels_payload = base.load_json(construction.LABELS_PATH)
    event_order.append("labels_loaded_after_both_conditions_all_generation")
    labels = {row["row_id"]: row for row in labels_payload["rows"]}
    scored = {}
    measurements = {}
    for condition in construction.CONDITION_ORDER:
        primary = [
            _score_output(row, prompt_by_id[row["row_id"]], labels[row["row_id"]])
            for row in generated[condition]["primary"]
        ]
        repeats = [
            _score_output(row, prompt_by_id[row["row_id"]], labels[row["row_id"]])
            for row in generated[condition]["repeat_audit"]
        ]
        scored[condition] = {"primary": primary, "repeat_audit": repeats}
        measurements[condition] = {
            "overall": _metrics(primary),
            "per_track": {
                track: _metrics([row for row in primary if row["track"] == track])
                for track in construction.TRACKS
            },
            "repeat_audit": _repeat_metrics(primary, repeats, audit_ids),
        }
    paired = paired_exact_mcnemar(
        scored["strict_probability"]["primary"], scored["candidate_name"]["primary"]
    )
    decision = _decision(prereg, measurements, paired, validation["passed"])
    resource_result = {
        "duration_seconds": round(time.perf_counter() - started, 3),
        "mlx_peak_memory_bytes": mx.get_peak_memory(),
        "process_peak_resident_memory_bytes": resource.getrusage(
            resource.RUSAGE_SELF
        ).ru_maxrss,
    }
    raw = {
        "schema": "personaeval_output_contract_selection_raw_v1",
        "experiment_id": construction.EXPERIMENT_ID,
        "execution_success": True,
        "preregistration_sha256": base.sha256_file(construction.PREREGISTRATION_PATH),
        "harness_lock_sha256": base.sha256_file(construction.HARNESS_LOCK_PATH),
        "runtime_contract": {
            "condition_order": list(construction.CONDITION_ORDER),
            "system_messages": construction.SYSTEM_MESSAGES,
            "official_user_prompt_changed": False,
            "batch_size": 1,
            "temperature": 0.0,
            "generation_calls": sum(
                len(rows["primary"]) + len(rows["repeat_audit"])
                for rows in scored.values()
            ),
            "optimizer_created": False,
            "optimizer_updates": 0,
            "adapter_initialized": False,
            "memory_loaded": False,
            "persona_prompt_loaded": False,
            "labels_loaded_after_both_conditions_finish": True,
            "ground_truth_passed_to_model": False,
            "event_order": event_order,
        },
        "environment": base.local_environment(),
        "conditions": scored,
        "resource": resource_result,
        "boundaries": prereg["boundaries"],
    }
    base.atomic_json(construction.RAW_RESULT_PATH, raw)
    result = {
        "schema": "personaeval_output_contract_selection_result_v1",
        "experiment_id": construction.EXPERIMENT_ID,
        "official_source": prereg["official_provenance"],
        "pilot_design": prereg["pilot_design"],
        "measurements": {
            "conditions": measurements,
            "paired": paired,
            "resource": resource_result,
        },
        "decision": decision,
        "raw_result": base.relative_binding(
            construction.RAW_RESULT_PATH, role="formal_paired_output_contract_scores"
        ),
        "evidence_boundary": prereg["boundaries"],
    }
    base.atomic_json(construction.RESULT_PATH, result)
    lines = ["# PersonaEval output-contract selection result", ""]
    for condition in construction.CONDITION_ORDER:
        overall = measurements[condition]["overall"]
        repeat = measurements[condition]["repeat_audit"]
        lines.extend(
            [
                f"- `{condition}` parse: `{overall['parsed_count']}/30` ({overall['parse_success_rate']:.3f})",
                f"- `{condition}` Top-1: `{overall['correct_count']}/30` ({overall['unconditional_top1_accuracy']:.3f})",
                f"- `{condition}` repeat agreement: `{repeat['prediction_agreement_count']}/9` ({repeat['prediction_agreement_rate']:.3f})",
            ]
        )
    lines.extend(
        [
            f"- Candidate-minus-strict accuracy delta: `{paired['accuracy_delta_candidate_minus_strict']:.3f}`",
            f"- Pilot gate passed: `{decision['passed']}`",
            "- Target-person / human replacement / training / production authorization: `False`",
            "",
        ]
    )
    base.atomic_text(construction.RESULT_MD_PATH, "\n".join(lines))
    return result


def main():
    print(json.dumps(run()["decision"], indent=2))


if __name__ == "__main__":
    main()
