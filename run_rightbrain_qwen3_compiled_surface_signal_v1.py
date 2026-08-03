#!/usr/bin/env python3
"""Run and aggregate the frozen compiled surface-signal experiment."""

from __future__ import annotations

import argparse
import json
import math
import os
import resource
import statistics
import time
from pathlib import Path

import mlx.core as mx
from mlx_lm import generate, load
from mlx_lm.sample_utils import make_sampler

import build_rightbrain_qwen3_compiled_surface_signal_v1 as construction
import run_rightbrain_mlx_gradient_repro_v1 as environment_common
import run_rightbrain_qwen3_4b_trainability_v1 as model_common
import run_rightbrain_qwen3_fresh_generation_v1 as score_common


ROOT = Path(__file__).resolve().parent
EXPERIMENT_ID = construction.EXPERIMENT_ID
DEFAULT_PREREGISTRATION = construction.DEFAULT_PREREGISTRATION
DEFAULT_EXECUTION_LOCK = construction.DEFAULT_EXECUTION_LOCK


def _resolve_binding(binding):
    path = Path(binding["path"])
    if binding.get("scope") == "external_local" or path.is_absolute():
        return path
    return ROOT / path


def validate_lock(lock_path=DEFAULT_EXECUTION_LOCK):
    lock = construction.load_json(lock_path)
    prereg = construction.load_json(DEFAULT_PREREGISTRATION)
    bindings = []
    for binding in lock["bindings"]:
        path = _resolve_binding(binding)
        actual = construction.sha256_file(path) if path.is_file() else None
        bindings.append(
            {**binding, "actual_sha256": actual, "match": actual == binding["sha256"]}
        )
    environment = environment_common._environment()
    expected = prereg["local_environment"]
    environment_exact = (
        environment["python_executable"] == expected["python_executable"]
        and environment["python_version"] == expected["python_version"]
        and environment["packages"] == expected["packages"]
        and environment["pip_freeze_sha256"] == expected["pip_freeze_sha256"]
    )
    authorization = lock["authorization"]
    passed = (
        lock["experiment_id"] == EXPERIMENT_ID
        and all(binding["match"] for binding in bindings)
        and environment_exact
        and authorization["conditions"] == list(construction.CONDITIONS)
        and authorization["repetitions"] == list(construction.REPEATS)
        and authorization["condition_orders"]
        == prereg["generation_contract"]["condition_orders"]
        and authorization["primary_row_indices"]
        == list(construction.PRIMARY_ROW_INDICES)
        and authorization["reference_alt_row_indices"]
        == list(construction.REFERENCE_ALT_ROW_INDICES)
        and authorization["prior_source_overlap_exact"] == 0
        and authorization["prior_answer_overlap_exact"] == 0
        and authorization["base_model"]
        == prereg["local_model_contract"]["base_model"]
        and authorization["device"] == "gpu"
        and authorization["generation_contract"] == prereg["generation_contract"]
        and authorization["optimizer_updates"] == 0
        and authorization["adapter_initialized"] is False
        and authorization["adapter_or_model_save"] is False
        and authorization["target_person_utterance_training"] is False
        and authorization["benchmark_training"] is False
        and authorization["production_runtime_change"] is False
    )
    return {"passed": passed, "bindings": bindings, "environment": environment}


def _result_path(prereg, repeat):
    return ROOT / f"{prereg['result_paths']['repeat_prefix']}{repeat}.json"


def _prompt_cases(prereg, condition):
    key = f"{condition}_messages"
    return [
        {
            "row_index": frozen["row_index"],
            "row_id": frozen["row_id"],
            "source_id": frozen["source_id"],
            "provider_id": frozen["provider_id"],
            "memory_mode": frozen["memory_mode"],
            "variant_index": frozen["variant_index"],
            "payload": frozen["scoring_payload"],
            "messages": frozen[key],
        }
        for frozen in prereg["prompt_contract"]["cases"]
    ]


def _generate_condition(model, tokenizer, cases, contract):
    model.eval()
    sampler = make_sampler(temp=float(contract["temperature"]))
    outputs = []
    for case in cases:
        prompt = tokenizer.apply_chat_template(
            case["messages"], tokenize=False, add_generation_prompt=True
        )
        started = time.perf_counter()
        output = generate(
            model,
            tokenizer,
            prompt,
            max_tokens=int(contract["maximum_new_tokens"]),
            sampler=sampler,
            verbose=False,
        ).strip()
        outputs.append(
            {
                "row_index": case["row_index"],
                "row_id": case["row_id"],
                "source_id": case["source_id"],
                "provider_id": case["provider_id"],
                "memory_mode": case["memory_mode"],
                "variant_index": case["variant_index"],
                "output": output,
                "character_count": len(output),
                "generation_seconds": round(time.perf_counter() - started, 6),
            }
        )
    return outputs


def _references():
    rows = construction.load_json(construction.DEFAULT_DATASET)
    references = construction._references_by_row(rows)
    digest = construction.canonical_json_sha256(
        [references[row_id] for row_id in sorted(references)]
    )
    return references, digest


def _score_rows(cases, outputs, references):
    cases_by_id = {case["row_id"]: case for case in cases}
    scored = []
    for generated in outputs:
        row_id = generated["row_id"]
        reference = references[row_id]
        base = score_common._score_output(
            cases_by_id[row_id], generated, reference["own"]
        )
        own_similarity = max(
            score_common._char_bigram_f1(generated["output"], text)
            for text in reference["own"]
        )
        opposite_similarity = max(
            score_common._char_bigram_f1(generated["output"], text)
            for text in reference["opposite"]
        )
        normalized = score_common._normalized(generated["output"])
        exact_copy = any(
            normalized == score_common._normalized(text)
            for text in reference["own"] + reference["opposite"]
        )
        scored.append(
            {
                **base,
                "own_provider_reference_f1": own_similarity,
                "opposite_provider_reference_f1": opposite_similarity,
                "provider_alignment_margin": own_similarity - opposite_similarity,
                "correct_provider_alignment": own_similarity > opposite_similarity,
                "exact_reference_copy": exact_copy,
            }
        )
    return scored


def _aggregate_scores(rows):
    aggregate = score_common._aggregate_scores(rows)
    aggregate.update(
        {
            "provider_alignment_margin_mean": statistics.fmean(
                row["provider_alignment_margin"] for row in rows
            ),
            "correct_provider_alignment_rate": sum(
                row["correct_provider_alignment"] for row in rows
            )
            / len(rows),
            "correct_provider_alignment_count": sum(
                row["correct_provider_alignment"] for row in rows
            ),
            "exact_reference_copy_count": sum(
                row["exact_reference_copy"] for row in rows
            ),
        }
    )
    return aggregate


def _comparison(control_rows, candidate_rows, control_scores, candidate_scores):
    control = {row["row_id"]: row for row in control_rows}
    candidate = {row["row_id"]: row for row in candidate_rows}
    if set(control) != set(candidate):
        raise RuntimeError("Condition row IDs differ")
    pairs = []
    changed = improvements = regressions = 0
    for row_id in sorted(control):
        before = control[row_id]
        after = candidate[row_id]
        output_changed = score_common._normalized(before["output"]) != (
            score_common._normalized(after["output"])
        )
        improved = not before["joint_contract_pass"] and after["joint_contract_pass"]
        regressed = before["joint_contract_pass"] and not after["joint_contract_pass"]
        changed += output_changed
        improvements += improved
        regressions += regressed
        pairs.append(
            {
                "row_id": row_id,
                "control_output": before["output"],
                "candidate_output": after["output"],
                "output_changed": output_changed,
                "joint_contract_improved": improved,
                "joint_contract_regressed": regressed,
            }
        )
    delta_keys = (
        "provider_pair_difference_rate",
        "provider_alignment_margin_mean",
        "correct_provider_alignment_rate",
        "joint_contract_pass_rate",
        "semantic_complete_rate",
        "memory_policy_pass_rate",
        "forbidden_pass_rate",
    )
    result = {
        "changed_output_count": changed,
        "joint_contract_improvement_count": improvements,
        "joint_contract_regression_count": regressions,
        "pairs": pairs,
    }
    for key in delta_keys:
        result[f"{key}_delta"] = candidate_scores[key] - control_scores[key]
    return result


def _failure_result(prereg, repeat, started, error):
    return {
        "schema": "uruha_rightbrain_qwen3_compiled_surface_signal_repeat_v1",
        "experiment_id": EXPERIMENT_ID,
        "repeat": repeat,
        "execution_success": False,
        "failure": {"error_type": type(error).__name__, "message": str(error)},
        "resource": {"duration_seconds": round(time.perf_counter() - started, 3)},
        "boundaries": prereg["boundaries"],
    }


def run_repeat(repeat, lock_path=DEFAULT_EXECUTION_LOCK):
    if repeat not in construction.REPEATS:
        raise ValueError("repeat outside preregistered values")
    if os.getenv("HF_HUB_OFFLINE") != "1" or os.getenv("TRANSFORMERS_OFFLINE") != "1":
        raise RuntimeError("Compiled surface-signal probe requires offline mode")
    validation = validate_lock(lock_path)
    if not validation["passed"]:
        raise RuntimeError("Compiled surface-signal execution lock failed")
    prereg = construction.load_json(DEFAULT_PREREGISTRATION)
    output_path = _result_path(prereg, repeat)
    if output_path.exists():
        raise RuntimeError(f"Refusing to overwrite repeat {repeat}")
    started = time.perf_counter()
    probe = prereg["exact_probe"]
    mx.set_default_device(mx.gpu)
    mx.set_memory_limit(int(probe["memory_limit_bytes"]))
    mx.set_wired_limit(int(probe["wired_limit_bytes"]))
    mx.reset_peak_memory()
    try:
        model, tokenizer = load(
            prereg["local_model_contract"]["snapshot_root"],
            tokenizer_config={"trust_remote_code": True},
        )
        mx.eval(model.parameters())
        base_before = model_common._base_contract(model, prereg)
        if not base_before["exact"]:
            raise RuntimeError(f"Base contract mismatch: {base_before}")
        generated = {}
        prompt_hashes = {}
        for condition in construction.CONDITION_ORDERS[repeat]:
            cases = _prompt_cases(prereg, condition)
            prompt_hashes[condition] = construction.canonical_json_sha256(
                [case["messages"] for case in cases]
            )
            expected = prereg["prompt_contract"][f"{condition}_prompt_sha256"]
            if prompt_hashes[condition] != expected:
                raise RuntimeError(f"Prompt hash drifted for {condition}")
            mx.random.seed(int(probe["random_seed"]))
            generated[condition] = _generate_condition(
                model, tokenizer, cases, prereg["generation_contract"]
            )
        references, reference_hash = _references()
        if reference_hash != prereg["reference_contract"]["sha256"]:
            raise RuntimeError("Reference hash drifted")
        scored = {}
        scores = {}
        for condition in construction.CONDITIONS:
            cases = _prompt_cases(prereg, condition)
            scored[condition] = _score_rows(cases, generated[condition], references)
            scores[condition] = _aggregate_scores(scored[condition])
        control_name, candidate_name = construction.CONDITIONS
        comparison = _comparison(
            scored[control_name],
            scored[candidate_name],
            scores[control_name],
            scores[candidate_name],
        )
        base_after = model_common._base_contract(model, prereg)
        peak = mx.get_peak_memory()
        if peak > int(probe["memory_limit_bytes"]):
            raise RuntimeError(f"Peak memory exceeded limit: {peak}")
        result = {
            "schema": "uruha_rightbrain_qwen3_compiled_surface_signal_repeat_v1",
            "experiment_id": EXPERIMENT_ID,
            "repeat": repeat,
            "execution_success": True,
            "environment": validation["environment"],
            "runtime_contract": {
                "device": str(mx.default_device()),
                "condition_order": list(construction.CONDITION_ORDERS[repeat]),
                "generation_calls": sum(len(value) for value in generated.values()),
                "optimizer_updates": 0,
                "adapter_initialized": False,
                "references_loaded_after_all_generation_conditions": True,
                "assistant_reference_passed_to_model": False,
                "adapter_or_model_saved": False,
            },
            "base_contract_before": base_before,
            "base_contract_after": base_after,
            "prompt_hashes": prompt_hashes,
            "reference_hash": reference_hash,
            "conditions": {
                condition: {
                    "outputs": scored[condition],
                    "scores": scores[condition],
                    "output_sha256": score_common._output_sha256(scored[condition]),
                }
                for condition in construction.CONDITIONS
            },
            "comparison": comparison,
            "resource": {
                "duration_seconds": round(time.perf_counter() - started, 3),
                "mlx_active_memory_bytes": mx.get_active_memory(),
                "mlx_cache_memory_bytes": mx.get_cache_memory(),
                "mlx_peak_memory_bytes": peak,
                "process_peak_resident_memory_bytes": resource.getrusage(
                    resource.RUSAGE_SELF
                ).ru_maxrss,
            },
            "boundaries": prereg["boundaries"],
        }
        if not all(
            math.isfinite(value)
            for condition in construction.CONDITIONS
            for value in scores[condition].values()
            if isinstance(value, float)
        ):
            raise RuntimeError("Non-finite aggregate score")
        construction.atomic_json(output_path, result)
        return result
    except Exception as error:
        construction.atomic_json(
            output_path, _failure_result(prereg, repeat, started, error)
        )
        raise


def _measure(rows, prereg):
    representative = rows[0]
    outputs_reproducible = all(
        len({row["conditions"][condition]["output_sha256"] for row in rows}) == 1
        for condition in construction.CONDITIONS
    )
    comparisons_reproducible = len(
        {construction.canonical_json_sha256(row["comparison"]) for row in rows}
    ) == 1
    control_name, candidate_name = construction.CONDITIONS
    control = representative["conditions"][control_name]["scores"]
    candidate = representative["conditions"][candidate_name]["scores"]
    comparison = representative["comparison"]
    gates = prereg["falsifiable_hypothesis"]["confirm_if_all"]
    all_contracts = all(
        row["runtime_contract"]["optimizer_updates"] == 0
        and row["runtime_contract"]["adapter_initialized"] is False
        and row["runtime_contract"]["references_loaded_after_all_generation_conditions"]
        and row["runtime_contract"]["assistant_reference_passed_to_model"] is False
        and row["runtime_contract"]["adapter_or_model_saved"] is False
        and row["base_contract_before"]["exact"]
        and row["base_contract_after"] == row["base_contract_before"]
        and all(
            row["prompt_hashes"][condition]
            == prereg["prompt_contract"][f"{condition}_prompt_sha256"]
            for condition in construction.CONDITIONS
        )
        and row["reference_hash"] == prereg["reference_contract"]["sha256"]
        for row in rows
    )
    measurements = {
        "abstract_top_level_control": control,
        "compiled_surface_signal": candidate,
        "candidate_minus_control": {
            key: value for key, value in comparison.items() if key != "pairs"
        },
        "condition_output_hashes": {
            condition: [
                row["conditions"][condition]["output_sha256"] for row in rows
            ]
            for condition in construction.CONDITIONS
        },
        "peak_memory_bytes_maximum": max(
            row["resource"]["mlx_peak_memory_bytes"] for row in rows
        ),
        "duration_seconds": [row["resource"]["duration_seconds"] for row in rows],
    }
    checks = {
        "each_condition_reproducible": outputs_reproducible
        and comparisons_reproducible,
        "candidate_outputs_changed": comparison["changed_output_count"]
        >= gates["candidate_changed_output_count_minimum"],
        "provider_pair_difference_not_regressed": comparison[
            "provider_pair_difference_rate_delta"
        ]
        >= gates["provider_pair_difference_rate_delta_minimum"],
        "provider_alignment_margin_improved": comparison[
            "provider_alignment_margin_mean_delta"
        ]
        >= gates["provider_alignment_margin_gain_minimum"],
        "correct_provider_alignment_improved": comparison[
            "correct_provider_alignment_rate_delta"
        ]
        >= gates["correct_provider_alignment_rate_gain_minimum"],
        "joint_contract_not_regressed": comparison[
            "joint_contract_pass_rate_delta"
        ]
        >= gates["joint_contract_pass_rate_delta_minimum"]
        and comparison["joint_contract_regression_count"]
        <= gates["joint_contract_regression_count_maximum"],
        "semantic_complete_not_regressed": comparison[
            "semantic_complete_rate_delta"
        ]
        >= gates["semantic_complete_rate_delta_minimum"],
        "memory_policy_not_regressed": comparison[
            "memory_policy_pass_rate_delta"
        ]
        >= gates["memory_policy_pass_rate_delta_minimum"],
        "forbidden_pass_not_regressed": comparison[
            "forbidden_pass_rate_delta"
        ]
        >= gates["forbidden_pass_rate_delta_minimum"],
        "no_exact_reference_copy": control["exact_reference_copy_count"]
        <= gates["exact_reference_copy_count_maximum"]
        and candidate["exact_reference_copy_count"]
        <= gates["exact_reference_copy_count_maximum"],
        "resource_within_limit": measurements["peak_memory_bytes_maximum"]
        <= gates["peak_memory_bytes_maximum"],
        "all_contracts_exact": all_contracts,
    }
    return measurements, checks


def _classify(checks, completed=True):
    if not completed:
        return "compiled_surface_signal_execution_failed"
    if not checks.get("each_condition_reproducible", False):
        return "compiled_surface_signal_not_reproducible"
    if not checks.get("all_contracts_exact", False):
        return "compiled_surface_signal_execution_failed"
    contract_checks = (
        "joint_contract_not_regressed",
        "semantic_complete_not_regressed",
        "memory_policy_not_regressed",
        "forbidden_pass_not_regressed",
    )
    if not all(checks.get(key, False) for key in contract_checks):
        return "compiled_surface_signal_contract_regressed"
    alignment_checks = (
        "candidate_outputs_changed",
        "provider_pair_difference_not_regressed",
        "provider_alignment_margin_improved",
        "correct_provider_alignment_improved",
        "no_exact_reference_copy",
        "resource_within_limit",
    )
    if not all(checks.get(key, False) for key in alignment_checks):
        return "compiled_surface_signal_alignment_not_improved"
    return "compiled_surface_signal_effect_confirmed"


def _expected_next_step(outcome, passed):
    if passed:
        return "preregister_compiled_signal_source_disjoint_full_pipeline_holdout"
    return "diagnose_compiled_surface_signal_failure"


def aggregate():
    prereg = construction.load_json(DEFAULT_PREREGISTRATION)
    rows = [
        construction.load_json(_result_path(prereg, repeat))
        for repeat in construction.REPEATS
    ]
    completed = all(row.get("execution_success") is True for row in rows)
    if completed:
        measurements, checks = _measure(rows, prereg)
    else:
        measurements = {
            "failures": [
                row.get("failure") for row in rows if not row.get("execution_success")
            ]
        }
        checks = {
            "each_condition_reproducible": False,
            "candidate_outputs_changed": False,
            "provider_pair_difference_not_regressed": False,
            "provider_alignment_margin_improved": False,
            "correct_provider_alignment_improved": False,
            "joint_contract_not_regressed": False,
            "semantic_complete_not_regressed": False,
            "memory_policy_not_regressed": False,
            "forbidden_pass_not_regressed": False,
            "no_exact_reference_copy": False,
            "resource_within_limit": False,
            "all_contracts_exact": False,
        }
    outcome = _classify(checks, completed)
    passed = completed and all(checks.values())
    next_step = _expected_next_step(outcome, passed)
    decision = {
        "experiment_complete": completed,
        "passed": passed,
        "outcome": outcome,
        "authorized_next_step": next_step,
        "full_pipeline_holdout_authorized": passed,
        "authorize_persistent_training": False,
        "authorize_persona_training": False,
        "authorize_adapter_save": False,
        "authorize_production": False,
        "authorize_persona_similarity_claim": False,
    }
    result = {
        "schema": "uruha_rightbrain_qwen3_compiled_surface_signal_result_v1",
        "experiment_id": EXPERIMENT_ID,
        "preregistration": construction.file_binding(DEFAULT_PREREGISTRATION),
        "execution_lock": construction.file_binding(DEFAULT_EXECUTION_LOCK),
        "repeat_results": [
            construction.file_binding(_result_path(prereg, repeat))
            for repeat in construction.REPEATS
        ],
        "measurements": measurements,
        "checks": {"all_repetitions_complete": completed, **checks},
        "decision": decision,
        "evidence_boundary": prereg["interpretation_limits"],
    }
    aggregate_path = ROOT / prereg["result_paths"]["aggregate_json"]
    markdown_path = ROOT / prereg["result_paths"]["aggregate_markdown"]
    construction.atomic_json(aggregate_path, result)
    delta = measurements.get("candidate_minus_control", {})
    construction.atomic_text(
        markdown_path,
        "\n".join(
            [
                "# Qwen3 compiled surface-signal result",
                "",
                f"- Outcome: `{outcome}`",
                f"- Passed: `{passed}`",
                f"- Changed outputs: `{delta.get('changed_output_count')}` / 8",
                f"- Provider alignment margin delta: `{delta.get('provider_alignment_margin_mean_delta')}`",
                f"- Correct provider alignment delta: `{delta.get('correct_provider_alignment_rate_delta')}`",
                f"- Joint contract delta: `{delta.get('joint_contract_pass_rate_delta')}`",
                f"- Joint contract regressions: `{delta.get('joint_contract_regression_count')}`",
                "- Training / adapter save / production authorization: `False`",
            ]
        )
        + "\n",
    )
    result_lock = {
        "schema": "uruha_rightbrain_qwen3_compiled_surface_signal_result_lock_v1",
        "experiment_id": EXPERIMENT_ID,
        "result_bindings": [
            construction.file_binding(DEFAULT_PREREGISTRATION),
            construction.file_binding(DEFAULT_EXECUTION_LOCK),
            construction.file_binding(construction.DEFAULT_DATASET),
            construction.file_binding(construction.DEFAULT_CONSTRUCTION_JSON),
            construction.file_binding(construction.DEFAULT_CONSTRUCTION_MD),
            *[
                construction.file_binding(_result_path(prereg, repeat))
                for repeat in construction.REPEATS
            ],
            construction.file_binding(aggregate_path),
            construction.file_binding(markdown_path),
        ],
        "decision": decision,
        "authorization": {
            "persistent_training": False,
            "persona_training": False,
            "adapter_save": False,
            "runtime_activation": False,
            "persona_similarity_claim": False,
        },
    }
    construction.atomic_json(
        ROOT / prereg["result_paths"]["result_lock"], result_lock
    )
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repeat", type=int)
    parser.add_argument("--aggregate", action="store_true")
    args = parser.parse_args()
    if args.aggregate:
        print(json.dumps(aggregate(), ensure_ascii=False, indent=2))
    elif args.repeat is not None:
        print(json.dumps(run_repeat(args.repeat), ensure_ascii=False, indent=2))
    else:
        parser.error("use --repeat N or --aggregate")


if __name__ == "__main__":
    main()
