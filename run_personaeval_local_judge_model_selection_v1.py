#!/usr/bin/env python3
"""Run the frozen paired PersonaEval local-judge model selection pilot."""

from __future__ import annotations

import gc
import json
import math
import os
import resource
import time
from pathlib import Path

import mlx.core as mx
from mlx_lm import load

import build_personaeval_local_judge_model_selection_v1 as construction
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
        and auth["official_dataset_commit"] == base.HF_DATASET_COMMIT
        and auth["official_code_commit"] == base.OFFICIAL_REPOSITORY_COMMIT
        and auth["model_ids"] == list(construction.MODEL_ORDER)
        and auth["primary_row_count"] == pilot["primary_row_count"]
        and auth["repeat_audit_row_count"] == len(pilot["repeat_audit_row_ids"])
        and auth["total_generation_calls"] == pilot["total_generation_calls"]
        and auth["batch_size"] == 1
        and auth["labels_loaded_after_all_generation"] is True
        and auth["training_updates"] == 0
        and auth["production_runtime_change"] is False
    )
    return {"passed": passed, "bindings": bindings, "lock": lock}


def paired_exact_mcnemar(rows_a, rows_b):
    by_id_a = {row["row_id"]: row for row in rows_a}
    by_id_b = {row["row_id"]: row for row in rows_b}
    if set(by_id_a) != set(by_id_b):
        raise ValueError("paired row IDs differ")
    both_correct = 0
    only_a = 0
    only_b = 0
    neither = 0
    details = []
    for row_id in sorted(by_id_a):
        correct_a = bool(by_id_a[row_id]["correct"])
        correct_b = bool(by_id_b[row_id]["correct"])
        if correct_a and correct_b:
            both_correct += 1
        elif correct_a:
            only_a += 1
        elif correct_b:
            only_b += 1
        else:
            neither += 1
        details.append(
            {"row_id": row_id, "qwen3_4b_correct": correct_a, "qwen25_7b_correct": correct_b}
        )
    discordant = only_a + only_b
    if discordant == 0:
        p_value = 1.0
    else:
        tail = sum(
            math.comb(discordant, k) for k in range(min(only_a, only_b) + 1)
        ) / (2**discordant)
        p_value = min(1.0, 2.0 * tail)
    total = len(details)
    return {
        "row_count": total,
        "both_correct": both_correct,
        "qwen3_4b_only_correct": only_a,
        "qwen25_7b_only_correct": only_b,
        "neither_correct": neither,
        "discordant_count": discordant,
        "exact_two_sided_mcnemar_p_value": p_value,
        "accuracy_delta_qwen25_7b_minus_qwen3_4b": (only_b - only_a) / total,
        "details": details,
    }


def _model_gate(prereg, metrics, repeat_metrics, lock_passed):
    rule = prereg["decision_rule"]
    checks = {
        "lock_exact": lock_passed,
        "parse_success_gate": metrics["parse_success_rate"]
        >= rule["per_model_minimum_parse_success_rate"],
        "above_chance_gate": metrics["exact_chance_superiority_p_value"]
        <= rule["per_model_maximum_chance_superiority_p_value"],
        "wilson_lower_above_random_gate": metrics["unconditional_top1_wilson_95"][0]
        > metrics["random_choice_expected_accuracy"],
        "prediction_repeat_gate": repeat_metrics["prediction_agreement_rate"]
        >= rule["per_model_minimum_prediction_repeat_agreement"],
    }
    return {"passed": all(checks.values()), "checks": checks}


def _decision(prereg, model_measurements, paired, lock_passed):
    gates = {
        model_id: _model_gate(
            prereg,
            model_measurements[model_id]["overall"],
            model_measurements[model_id]["repeat_audit"],
            lock_passed,
        )
        for model_id in construction.MODEL_ORDER
    }
    passing = [model_id for model_id, gate in gates.items() if gate["passed"]]
    selected = None
    reason = None
    if len(passing) == 1:
        selected = passing[0]
        reason = "only_model_passing_all_preregistered_reliability_and_ability_gates"
    elif len(passing) == 2:
        p_value = paired["exact_two_sided_mcnemar_p_value"]
        delta = paired["accuracy_delta_qwen25_7b_minus_qwen3_4b"]
        if p_value <= 0.05 and delta != 0.0:
            selected = "qwen25_7b" if delta > 0 else "qwen3_4b"
            reason = "significantly_more_accurate_among_two_passing_models"
        else:
            selected = "qwen3_4b"
            reason = "both_pass_without_significant_difference_choose_lower_resource_model"
    else:
        reason = "neither_model_passed_all_preregistered_gates"
    return {
        "experiment_complete": True,
        "model_gates": gates,
        "selected_model_for_larger_validation": selected,
        "selection_reason": reason,
        "passed": selected is not None,
        "authorize_larger_disjoint_official_evaluator_validation": selected is not None,
        "authorize_target_person_judging": False,
        "authorize_human_rater_replacement": False,
        "authorize_training": False,
        "authorize_production": False,
    }


def _generate_model(model_id, prereg, prompt_rows, prompt_by_id, audit_ids):
    contract = prereg["model_contracts"][model_id]
    mx.reset_peak_memory()
    model, tokenizer = load(
        contract["snapshot_root"], tokenizer_config={"trust_remote_code": True}
    )
    model.eval()
    mx.eval(model.parameters())
    started = time.perf_counter()
    primary = base_runner._generate_cases(
        model,
        tokenizer,
        prompt_rows,
        prereg,
        phase=f"{model_id}_primary",
        repetition=1,
    )
    repeats = []
    for repetition, ordered_ids in (
        (2, list(reversed(audit_ids))),
        (3, list(audit_ids)),
    ):
        repeats.extend(
            base_runner._generate_cases(
                model,
                tokenizer,
                [prompt_by_id[row_id] for row_id in ordered_ids],
                prereg,
                phase=f"{model_id}_repeat_audit",
                repetition=repetition,
            )
        )
    resource_result = {
        "duration_seconds": round(time.perf_counter() - started, 3),
        "mlx_peak_memory_bytes": mx.get_peak_memory(),
        "mlx_active_memory_bytes_before_unload": mx.get_active_memory(),
        "mlx_cache_memory_bytes_before_unload": mx.get_cache_memory(),
    }
    del model
    del tokenizer
    gc.collect()
    mx.clear_cache()
    return primary, repeats, resource_result


def run(lock_path=construction.HARNESS_LOCK_PATH):
    if construction.RAW_RESULT_PATH.exists() or construction.RESULT_PATH.exists():
        raise RuntimeError("refusing to overwrite existing formal model-selection result")
    if os.getenv("HF_HUB_OFFLINE") != "1" or os.getenv("TRANSFORMERS_OFFLINE") != "1":
        raise RuntimeError("model-selection pilot requires offline local-model mode")
    validation = validate_lock(lock_path)
    if not validation["passed"]:
        raise RuntimeError("frozen model-selection harness lock validation failed")
    prereg = base.load_json(construction.PREREGISTRATION_PATH)
    prompts_payload = base.load_json(construction.PROMPTS_PATH)
    prompt_rows = [base_runner._prompt_case(row) for row in prompts_payload["rows"]]
    prompt_by_id = {row["row_id"]: row for row in prompt_rows}
    audit_ids = prereg["pilot_design"]["repeat_audit_row_ids"]
    if len(prompt_rows) != prereg["pilot_design"]["primary_row_count"]:
        raise RuntimeError("prompt row count differs from preregistration")

    mx.set_default_device(mx.gpu)
    mx.set_memory_limit(32212254720)
    mx.set_wired_limit(22906503168)
    mx.random.seed(int(prereg["controlled_variables"]["seed"]))
    generated_by_model = {}
    event_order = []
    overall_started = time.perf_counter()
    for model_id in construction.MODEL_ORDER:
        primary, repeats, resources = _generate_model(
            model_id, prereg, prompt_rows, prompt_by_id, audit_ids
        )
        generated_by_model[model_id] = {
            "primary": primary,
            "repeat_audit": repeats,
            "resource": resources,
        }
        event_order.append(f"{model_id}_all_generation_complete")
    event_order.append("both_models_all_generation_complete")

    labels_payload = base.load_json(construction.LABELS_PATH)
    event_order.append("labels_loaded_after_both_models_all_generation")
    labels = {row["row_id"]: row for row in labels_payload["rows"]}
    if set(labels) != set(prompt_by_id):
        raise RuntimeError("label IDs differ from prompt IDs")

    scored = {}
    measurements = {}
    for model_id in construction.MODEL_ORDER:
        generated = generated_by_model[model_id]
        primary = [
            base_runner._score_output(
                row, prompt_by_id[row["row_id"]], labels[row["row_id"]]
            )
            for row in generated["primary"]
        ]
        repeats = [
            base_runner._score_output(
                row, prompt_by_id[row["row_id"]], labels[row["row_id"]]
            )
            for row in generated["repeat_audit"]
        ]
        scored[model_id] = {"primary": primary, "repeat_audit": repeats}
        measurements[model_id] = {
            "overall": base_runner._metrics(primary),
            "per_track": {
                track: base_runner._metrics(
                    [row for row in primary if row["track"] == track]
                )
                for track in construction.TRACKS
            },
            "repeat_audit": base_runner._repeat_metrics(primary, repeats, audit_ids),
            "resource": generated["resource"],
        }
    paired = paired_exact_mcnemar(
        scored["qwen3_4b"]["primary"], scored["qwen25_7b"]["primary"]
    )
    decision = _decision(prereg, measurements, paired, validation["passed"])
    raw = {
        "schema": "personaeval_local_judge_model_selection_raw_v1",
        "experiment_id": construction.EXPERIMENT_ID,
        "execution_success": True,
        "preregistration_sha256": base.sha256_file(construction.PREREGISTRATION_PATH),
        "harness_lock_sha256": base.sha256_file(construction.HARNESS_LOCK_PATH),
        "runtime_contract": {
            "model_order": list(construction.MODEL_ORDER),
            "system_message": construction.SYSTEM_MESSAGE,
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
            "labels_loaded_after_both_models_finish": True,
            "ground_truth_passed_to_model": False,
            "event_order": event_order,
        },
        "environment": base.local_environment(),
        "models": scored,
        "resource": {
            "duration_seconds": round(time.perf_counter() - overall_started, 3),
            "process_peak_resident_memory_bytes": resource.getrusage(
                resource.RUSAGE_SELF
            ).ru_maxrss,
        },
        "boundaries": prereg["boundaries"],
    }
    base.atomic_json(construction.RAW_RESULT_PATH, raw)
    result = {
        "schema": "personaeval_local_judge_model_selection_result_v1",
        "experiment_id": construction.EXPERIMENT_ID,
        "official_source": prereg["official_provenance"],
        "pilot_design": prereg["pilot_design"],
        "measurements": {"models": measurements, "paired": paired},
        "decision": decision,
        "raw_result": base.relative_binding(
            construction.RAW_RESULT_PATH, role="formal_paired_outputs_and_scores"
        ),
        "evidence_boundary": prereg["boundaries"],
    }
    base.atomic_json(construction.RESULT_PATH, result)
    lines = [
        "# PersonaEval local judge model selection result",
        "",
    ]
    for model_id in construction.MODEL_ORDER:
        overall = measurements[model_id]["overall"]
        repeat = measurements[model_id]["repeat_audit"]
        lines.extend(
            [
                f"- `{model_id}` parse: `{overall['parsed_count']}/{overall['row_count']}` ({overall['parse_success_rate']:.3f})",
                f"- `{model_id}` Top-1: `{overall['correct_count']}/{overall['row_count']}` ({overall['unconditional_top1_accuracy']:.3f})",
                f"- `{model_id}` repeat agreement: `{repeat['prediction_agreement_count']}/{repeat['row_count']}` ({repeat['prediction_agreement_rate']:.3f})",
                f"- `{model_id}` gate passed: `{decision['model_gates'][model_id]['passed']}`",
            ]
        )
    lines.extend(
        [
            f"- Paired McNemar p: `{paired['exact_two_sided_mcnemar_p_value']:.6f}`",
            f"- Selected for larger validation: `{decision['selected_model_for_larger_validation']}`",
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
