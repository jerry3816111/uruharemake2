#!/usr/bin/env python3
"""Run the locked matched RightBrain curriculum pilot on the local model only."""

from __future__ import annotations

import argparse
import copy
import gc
import json
import math
import os
import random
import statistics
import time
from collections import Counter
from pathlib import Path

import psutil
import torch
from torch.utils.data import DataLoader, Dataset
from transformers import AutoTokenizer

import build_rightbrain_role_curriculum_training_pilot_v1 as construction
import build_rightbrain_role_specialization_curriculum_v1 as curriculum
import public_persona_scorer_contract_v4 as persona_scorer
import uruha_persona_policy as persona_policy
from persona_policy_local_model_pilot_v1 import EMPTY_MEMORY
from train_uruha_rightbrain_contract_v1 import build_model
from train_uruha_rightbrain_dpo_v18 import _tokenize_completion
from train_uruha_rightbrain_simpo_v19 import completion_average_log_prob, disable_dropout


ROOT = Path(__file__).resolve().parent
EXPERIMENT_ID = "rightbrain_role_curriculum_training_pilot_v1"
DEFAULT_PREREGISTRATION = construction.DEFAULT_PREREGISTRATION
DEFAULT_CONTROL = construction.DEFAULT_CONTROL
DEFAULT_TREATMENT = construction.DEFAULT_TREATMENT
DEFAULT_HOLDOUT = construction.DEFAULT_HOLDOUT
DEFAULT_CONSTRUCTION_REPORT = construction.DEFAULT_REPORT_JSON
DEFAULT_EXECUTION_LOCK = ROOT / "configs/rightbrain_role_curriculum_training_pilot_v1_execution_lock.json"
DEFAULT_RESULT_JSON = ROOT / "reports/rightbrain_role_curriculum_training_pilot_v1_result.json"
DEFAULT_RESULT_MD = ROOT / "reports/rightbrain_role_curriculum_training_pilot_v1_result.md"
CONDITIONS = (
    "initial_v10_reference",
    "policy_permuted_control",
    "policy_aligned_treatment",
)


class FixedLengthContractDataset(Dataset):
    """Tokenize canonical rows and allocate an identical masked tensor per item."""

    def __init__(self, rows, tokenizer, max_length):
        self.items = [self._tokenize(row, tokenizer, max_length) for row in rows]

    @staticmethod
    def _tokenize(row, tokenizer, max_length):
        prompt = tokenizer.apply_chat_template(
            row["messages"][:-1], tokenize=False, add_generation_prompt=True
        )
        answer = f"{construction.assistant_target(row)}<|im_end|>"
        prompt_ids = tokenizer(prompt, add_special_tokens=False).input_ids
        answer_ids = tokenizer(answer, add_special_tokens=False).input_ids
        active_ids = prompt_ids + answer_ids
        if len(active_ids) > max_length:
            raise ValueError(f"Sequence exceeds fixed allocation: {row['id']}")
        pad_id = tokenizer.pad_token_id
        if pad_id is None:
            pad_id = tokenizer.eos_token_id
        padding = max_length - len(active_ids)
        return {
            "input_ids": torch.tensor(active_ids + [pad_id] * padding, dtype=torch.long),
            "attention_mask": torch.tensor([1] * len(active_ids) + [0] * padding, dtype=torch.long),
            "labels": torch.tensor(
                [-100] * len(prompt_ids) + answer_ids + [-100] * padding,
                dtype=torch.long,
            ),
        }

    def __len__(self):
        return len(self.items)

    def __getitem__(self, index):
        return self.items[index]


def _seed_everything(seed):
    random.seed(seed)
    torch.manual_seed(seed)
    if torch.backends.mps.is_available() and hasattr(torch.mps, "manual_seed"):
        torch.mps.manual_seed(seed)


def _device(model):
    return next(model.parameters()).device


def _move(batch, device):
    return {key: value.to(device) for key, value in batch.items()}


def _release_model(model):
    del model
    gc.collect()
    if torch.backends.mps.is_available():
        torch.mps.empty_cache()


def load_tokenizer(preregistration):
    tokenizer = AutoTokenizer.from_pretrained(
        preregistration["local_model_contract"]["snapshot_root"],
        trust_remote_code=True,
        local_files_only=True,
    )
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"
    return tokenizer


def validate_lock(lock_path=DEFAULT_EXECUTION_LOCK):
    lock = construction.load_json(lock_path)
    if lock["experiment_id"] != EXPERIMENT_ID:
        raise RuntimeError("Execution lock belongs to another experiment")
    rows = []
    for binding in lock["bindings"]:
        path = ROOT / binding["path"]
        actual = construction.sha256_file(path) if path.is_file() else None
        rows.append(
            {
                "path": binding["path"],
                "expected_sha256": binding["sha256"],
                "actual_sha256": actual,
                "match": actual == binding["sha256"],
            }
        )
    report = construction.load_json(DEFAULT_CONSTRUCTION_REPORT)
    decision_match = report["decision"]["outcome"] == lock["required_construction_outcome"]
    return {
        "passed": all(row["match"] for row in rows)
        and decision_match
        and lock["authorization"]["exact_locked_pilot_execution"],
        "bindings": rows,
        "construction_decision_match": decision_match,
        "lock": lock,
    }


def preflight(lock_path=DEFAULT_EXECUTION_LOCK):
    validation = validate_lock(lock_path)
    preregistration = construction.load_json(DEFAULT_PREREGISTRATION)
    control = construction.load_json(DEFAULT_CONTROL)
    treatment = construction.load_json(DEFAULT_TREATMENT)
    holdout = construction.load_json(DEFAULT_HOLDOUT)
    tokenizer = load_tokenizer(preregistration)
    frozen_inputs = construction.validate_frozen_inputs(preregistration)
    matched = construction.audit_matched_training_data(
        treatment, control, tokenizer, preregistration
    )
    heldout = construction.audit_holdout(holdout, treatment)
    schedule = preregistration["training_schedule"]
    max_length = int(schedule["fixed_allocated_sequence_length"])
    control_set = FixedLengthContractDataset(control, tokenizer, max_length)
    treatment_set = FixedLengthContractDataset(treatment, tokenizer, max_length)
    allocation_shapes = {
        tuple(item["input_ids"].shape)
        for item in [*control_set.items, *treatment_set.items]
    }
    output_paths = {
        condition: ROOT / path
        for condition, path in schedule["output_directories"].items()
    }
    checks = {
        "execution_lock": validation["passed"],
        "frozen_model_and_source_inputs": frozen_inputs["passed"],
        "matched_training_data": matched["passed"],
        "heldout_evaluation": heldout["passed"],
        "fixed_allocation_shape": allocation_shapes == {(max_length,)},
        "row_count_each": len(control_set) == len(treatment_set) == 80,
        "micro_steps_exact": int(schedule["micro_steps_exact"]) == 80,
        "optimizer_updates_exact": int(schedule["optimizer_updates_exact"]) == 10,
        "output_directories_absent": all(not path.exists() for path in output_paths.values()),
    }
    return {
        "schema": "uruha_rightbrain_role_curriculum_training_pilot_preflight_v1",
        "experiment_id": EXPERIMENT_ID,
        "passed": all(checks.values()),
        "checks": checks,
        "lock_validation": validation,
        "frozen_input_validation": frozen_inputs,
        "matched_training_data": matched,
        "heldout_evaluation": heldout,
        "fixed_allocated_sequence_length": max_length,
        "output_directories": {key: str(path) for key, path in output_paths.items()},
    }


def train_condition(condition, rows, preregistration, tokenizer):
    schedule = preregistration["training_schedule"]
    output_dir = ROOT / schedule["output_directories"][condition]
    if output_dir.exists():
        raise RuntimeError(f"Refusing to overwrite existing output: {output_dir}")
    seed = int(schedule["random_seed"])
    _seed_everything(seed)
    dataset = FixedLengthContractDataset(
        rows,
        tokenizer,
        int(schedule["fixed_allocated_sequence_length"]),
    )
    generator = torch.Generator().manual_seed(seed)
    loader = DataLoader(
        dataset,
        batch_size=int(schedule["batch_size"]),
        shuffle=True,
        generator=generator,
    )
    model_contract = preregistration["local_model_contract"]
    started = time.perf_counter()
    model = build_model(
        model_contract["snapshot_root"],
        str(ROOT / model_contract["initial_adapter"]["path"]),
        lora_r=32,
        lora_alpha=24,
        lora_dropout=float(schedule["adapter_dropout"]),
        dtype_name="bfloat16",
    )
    device = _device(model)
    optimizer = torch.optim.AdamW(
        [parameter for parameter in model.parameters() if parameter.requires_grad],
        lr=float(schedule["learning_rate"]),
        weight_decay=float(schedule["weight_decay"]),
        eps=float(schedule["optimizer_epsilon"]),
    )
    grad_accum = int(schedule["gradient_accumulation"])
    expected_steps = int(schedule["micro_steps_exact"])
    model.train()
    optimizer.zero_grad(set_to_none=True)
    micro_steps = updates = 0
    losses = []
    max_gradient_norm = 0.0
    for batch in loader:
        micro_steps += 1
        loss = model(**_move(batch, device)).loss
        if not torch.isfinite(loss):
            raise RuntimeError(f"Non-finite loss in {condition} at step {micro_steps}")
        (loss / grad_accum).backward()
        losses.append(float(loss.detach().cpu()))
        if micro_steps % grad_accum == 0:
            gradient_norm = torch.nn.utils.clip_grad_norm_(
                [parameter for parameter in model.parameters() if parameter.requires_grad],
                max_norm=float(schedule["maximum_gradient_norm"]),
            )
            gradient_norm = float(gradient_norm.detach().float().cpu())
            if not math.isfinite(gradient_norm):
                raise RuntimeError(f"Non-finite gradient in {condition} at step {micro_steps}")
            max_gradient_norm = max(max_gradient_norm, gradient_norm)
            optimizer.step()
            optimizer.zero_grad(set_to_none=True)
            updates += 1
        if torch.backends.mps.is_available():
            torch.mps.empty_cache()
    if micro_steps != expected_steps or updates != int(schedule["optimizer_updates_exact"]):
        raise RuntimeError(
            f"Schedule mismatch for {condition}: micro_steps={micro_steps}, updates={updates}"
        )
    output_dir.mkdir(parents=True, exist_ok=False)
    model.save_pretrained(output_dir)
    training_report = {
        "condition": condition,
        "dataset_sha256": construction.sha256_file(
            DEFAULT_CONTROL if condition == "policy_permuted_control" else DEFAULT_TREATMENT
        ),
        "rows": len(dataset),
        "micro_steps": micro_steps,
        "optimizer_updates": updates,
        "nonfinite_events": 0,
        "mean_training_loss": statistics.fmean(losses),
        "final_training_loss": losses[-1],
        "maximum_observed_gradient_norm_before_clipping": max_gradient_norm,
        "fixed_allocated_sequence_length": int(schedule["fixed_allocated_sequence_length"]),
        "duration_seconds": round(time.perf_counter() - started, 3),
        "output_adapter_config_sha256": construction.sha256_file(output_dir / "adapter_config.json"),
        "output_adapter_model_sha256": construction.sha256_file(output_dir / "adapter_model.safetensors"),
    }
    construction.atomic_json(output_dir / "training_run.json", training_report)
    _release_model(model)
    return training_report


def _prompt_messages(case, provider_id):
    logic = curriculum.logic_from_spec(case)
    payload, instruction = curriculum.build_payload(logic, case["context"], provider_id)
    return logic, [
        {"role": "system", "content": instruction},
        {"role": "user", "content": curriculum.canonical_json(payload)},
    ]


def evaluate_policy_discrimination(model, tokenizer, holdout, preregistration):
    device = _device(model)
    max_length = int(preregistration["training_schedule"]["maximum_sequence_length"])
    rows = []
    model.eval()
    disable_dropout(model)
    with torch.inference_mode():
        for case in holdout["cases"]:
            for provider_id in construction.PROVIDERS:
                _, messages = _prompt_messages(case, provider_id)
                scores = {}
                token_counts = {}
                for reference_provider, reference in case["policy_references"].items():
                    sequence = _tokenize_completion(
                        messages,
                        reference,
                        tokenizer,
                        max_length,
                    )
                    score = completion_average_log_prob(model, sequence, device)
                    scores[reference_provider] = float(score.detach().cpu().item())
                    token_counts[reference_provider] = int(sequence["completion_token_count"])
                desired = provider_id
                other = next(provider for provider in construction.PROVIDERS if provider != desired)
                margin = scores[desired] - scores[other]
                rows.append(
                    {
                        "case_id": case["case_id"],
                        "context": case["context"],
                        "memory_mode": case["memory_mode"],
                        "provider_id": provider_id,
                        "desired_reference_provider": desired,
                        "reference_average_log_prob": scores,
                        "completion_token_count": token_counts,
                        "signed_policy_margin": margin,
                        "correct": margin > 0,
                    }
                )
                if torch.backends.mps.is_available():
                    torch.mps.empty_cache()

    def accuracy(items):
        return sum(row["correct"] for row in items) / len(items)

    provider_accuracy = {
        provider: accuracy([row for row in rows if row["provider_id"] == provider])
        for provider in construction.PROVIDERS
    }
    per_context = {
        context: accuracy([row for row in rows if row["context"] == context])
        for context in sorted({row["context"] for row in rows})
    }
    per_memory_mode = {
        mode: accuracy([row for row in rows if row["memory_mode"] == mode])
        for mode in sorted({row["memory_mode"] for row in rows})
    }
    return {
        "comparison_count": len(rows),
        "bidirectional_policy_discrimination_accuracy": accuracy(rows),
        "target_provider_discrimination_accuracy": provider_accuracy[persona_policy.TARGET_PROVIDER],
        "neutral_provider_discrimination_accuracy": provider_accuracy[persona_policy.NEUTRAL_PROVIDER],
        "mean_signed_policy_margin": statistics.fmean(row["signed_policy_margin"] for row in rows),
        "per_context_accuracy": per_context,
        "per_memory_mode_accuracy": per_memory_mode,
        "rows": rows,
    }


def _prepare_generation_inputs(tokenizer, messages, budget, device):
    prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer(prompt, return_tensors="pt")
    active = int(inputs["input_ids"].shape[1])
    if active > budget:
        raise RuntimeError(f"Generation prompt exceeds fixed budget: {active}>{budget}")
    pad_id = tokenizer.pad_token_id if tokenizer.pad_token_id is not None else tokenizer.eos_token_id
    padding = budget - active
    input_ids = torch.cat(
        [torch.full((1, padding), int(pad_id), dtype=torch.long), inputs["input_ids"]],
        dim=1,
    )
    attention_mask = torch.cat(
        [torch.zeros((1, padding), dtype=torch.long), inputs["attention_mask"]],
        dim=1,
    )
    return {
        "input_ids": input_ids.to(device),
        "attention_mask": attention_mask.to(device),
    }, active


def _semantic_pass(reply, case):
    return all(any(marker in reply for marker in group) for group in case["required_marker_groups"])


def _memory_pass(reply, case):
    return bool(reply) and construction._memory_policy_pass(case, reply)


def evaluate_fresh_generation(model, tokenizer, holdout, preregistration):
    config = preregistration["fresh_generation_evaluation"]
    device = _device(model)
    model.eval()
    disable_dropout(model)
    if hasattr(model, "gradient_checkpointing_disable"):
        model.gradient_checkpointing_disable()
    model.config.use_cache = True
    process = psutil.Process()
    peak_rss = process.memory_info().rss
    rows = []
    for case in holdout["cases"]:
        for provider_id in construction.PROVIDERS:
            logic, messages = _prompt_messages(case, provider_id)
            for seed in config["seeds"]:
                _seed_everything(int(seed))
                inputs, active_tokens = _prepare_generation_inputs(
                    tokenizer,
                    messages,
                    int(config["prompt_allocation_budget_tokens"]),
                    device,
                )
                started = time.perf_counter()
                with torch.inference_mode():
                    output = model.generate(
                        **inputs,
                        max_new_tokens=int(config["maximum_new_tokens"]),
                        do_sample=True,
                        temperature=float(config["temperature"]),
                        top_p=float(config["top_p"]),
                        top_k=int(config["top_k"]),
                        repetition_penalty=float(config["repetition_penalty"]),
                        no_repeat_ngram_size=3,
                        renormalize_logits=True,
                        pad_token_id=tokenizer.eos_token_id,
                    )
                latency = time.perf_counter() - started
                raw = tokenizer.decode(
                    output[0][int(config["prompt_allocation_budget_tokens"]):],
                    skip_special_tokens=False,
                ).split("<|im_end|>")[0].strip()
                rightbrain = curriculum.brain_module.RightBrain(
                    load_model=False,
                    persona_policy_provider=persona_policy.build_persona_policy_provider(provider_id),
                )
                rightbrain.structured_payload_mode = curriculum.surface_payload.LEGACY_JSON_V1
                rightbrain.surface_watchlist_enabled = False
                rightbrain.explicit_length_contract_enabled = False
                rightbrain.memory_cue_canonicalization_enabled = False
                rightbrain.forbidden_conflict_projection_enabled = False
                visible, rejection_reasons = rightbrain._prepare_model_surface_candidate(
                    raw,
                    logic,
                    case["user_input"],
                    copy.deepcopy(EMPTY_MEMORY),
                    int(case["max_chars"]),
                )
                strict_pass = bool(visible) and not rejection_reasons
                reply = visible if strict_pass else ""
                private_terms = (
                    case.get("memory", {}).get("terms") or []
                    if case["memory_mode"] == "do_not_mention"
                    else []
                )
                v4 = persona_scorer.score_reply(
                    reply,
                    persona_scorer.compile_scorer_contract(case["context"]),
                )
                rows.append(
                    {
                        "case_id": case["case_id"],
                        "context": case["context"],
                        "memory_mode": case["memory_mode"],
                        "provider_id": provider_id,
                        "seed": int(seed),
                        "active_prompt_tokens": active_tokens,
                        "allocated_prompt_tokens": int(config["prompt_allocation_budget_tokens"]),
                        "raw_generation": raw,
                        "visible_reply": visible,
                        "normalized_output": construction.normalized_text(reply),
                        "strict_candidate_gate_pass": strict_pass,
                        "semantic_contract_pass": _semantic_pass(reply, case),
                        "memory_policy_pass": _memory_pass(reply, case),
                        "private_memory_intrusion": any(term in raw for term in private_terms),
                        "language_or_script_pollution": any(
                            reason
                            in {
                                "cjk_language_leak",
                                "nonstandard_cjk_surface",
                                "foreign_script_leak",
                                "unexpected_ascii_leak",
                                "missing_japanese_surface",
                            }
                            for reason in rejection_reasons
                        ),
                        "polite_register_drift": any(
                            reason in {"polite_tone_drift", "formal_register_drift"}
                            for reason in rejection_reasons
                        ),
                        "public_persona_v4_contract_pass_descriptive_only": bool(v4["passed"]),
                        "rejection_reasons": rejection_reasons,
                        "latency_seconds": latency,
                    }
                )
                peak_rss = max(peak_rss, process.memory_info().rss)
                if torch.backends.mps.is_available():
                    torch.mps.empty_cache()

    count = len(rows)
    row_map = {
        (row["case_id"], row["seed"], row["provider_id"]): row for row in rows
    }
    pair_differences = []
    for case in holdout["cases"]:
        for seed in config["seeds"]:
            target = row_map[(case["case_id"], int(seed), persona_policy.TARGET_PROVIDER)]
            neutral = row_map[(case["case_id"], int(seed), persona_policy.NEUTRAL_PROVIDER)]
            pair_differences.append(
                bool(target["normalized_output"])
                and bool(neutral["normalized_output"])
                and target["normalized_output"] != neutral["normalized_output"]
            )
    latencies = sorted(row["latency_seconds"] for row in rows)
    p95_index = max(0, math.ceil(0.95 * len(latencies)) - 1)
    return {
        "generation_count": count,
        "strict_candidate_gate_pass_rate": sum(row["strict_candidate_gate_pass"] for row in rows) / count,
        "semantic_contract_pass_rate": sum(row["semantic_contract_pass"] for row in rows) / count,
        "memory_policy_pass_rate": sum(row["memory_policy_pass"] for row in rows) / count,
        "language_or_script_pollution_rate": sum(row["language_or_script_pollution"] for row in rows) / count,
        "polite_register_drift_rate": sum(row["polite_register_drift"] for row in rows) / count,
        "private_memory_intrusion_count": sum(row["private_memory_intrusion"] for row in rows),
        "normalized_output_unique_rate": len({row["normalized_output"] for row in rows if row["normalized_output"]}) / count,
        "target_neutral_pair_difference_rate": sum(pair_differences) / len(pair_differences),
        "public_persona_v4_contract_pass_rate_descriptive_only": sum(
            row["public_persona_v4_contract_pass_descriptive_only"] for row in rows
        )
        / count,
        "median_generation_latency_seconds": statistics.median(latencies),
        "p95_generation_latency_seconds": latencies[p95_index],
        "peak_process_resident_memory_bytes": peak_rss,
        "rejection_reason_counts": dict(
            Counter(reason for row in rows for reason in row["rejection_reasons"])
        ),
        "rows": rows,
    }


def evaluate_adapter(condition, adapter_path, preregistration, tokenizer, holdout):
    model = build_model(
        preregistration["local_model_contract"]["snapshot_root"],
        str(adapter_path),
        lora_r=32,
        lora_alpha=24,
        lora_dropout=float(preregistration["training_schedule"]["adapter_dropout"]),
        dtype_name="bfloat16",
    )
    likelihood = evaluate_policy_discrimination(model, tokenizer, holdout, preregistration)
    generation = evaluate_fresh_generation(model, tokenizer, holdout, preregistration)
    _release_model(model)
    return {
        "condition": condition,
        "adapter": {
            "path": str(Path(adapter_path).relative_to(ROOT)),
            "adapter_config_sha256": construction.sha256_file(Path(adapter_path) / "adapter_config.json"),
            "adapter_model_sha256": construction.sha256_file(Path(adapter_path) / "adapter_model.safetensors"),
        },
        "policy_discrimination": likelihood,
        "fresh_generation": generation,
    }


def decide(preregistration, training, evaluations):
    gates = preregistration["success_gate"]
    initial = evaluations["initial_v10_reference"]
    control = evaluations["policy_permuted_control"]
    treatment = evaluations["policy_aligned_treatment"]
    primary = gates["primary_requirements"]
    generation = gates["generation_noninferiority_requirements"]
    td = treatment["policy_discrimination"]
    cd = control["policy_discrimination"]
    id_ = initial["policy_discrimination"]
    tg = treatment["fresh_generation"]
    cg = control["fresh_generation"]
    ig = initial["fresh_generation"]
    integrity = {
        "training_micro_steps_and_updates": all(
            row["micro_steps"] == 80 and row["optimizer_updates"] == 10
            for row in training.values()
        ),
        "zero_nonfinite_events": all(row["nonfinite_events"] == 0 for row in training.values()),
        "all_fresh_generations_accounted": sum(
            row["fresh_generation"]["generation_count"] for row in evaluations.values()
        )
        == 240,
    }
    primary_checks = {
        "treatment_bidirectional_minimum": td["bidirectional_policy_discrimination_accuracy"]
        >= primary["treatment_bidirectional_policy_discrimination_accuracy_minimum"],
        "delta_vs_control": td["bidirectional_policy_discrimination_accuracy"]
        - cd["bidirectional_policy_discrimination_accuracy"]
        >= primary["treatment_delta_vs_policy_permuted_control_minimum"],
        "delta_vs_initial": td["bidirectional_policy_discrimination_accuracy"]
        - id_["bidirectional_policy_discrimination_accuracy"]
        >= primary["treatment_delta_vs_initial_v10_minimum"],
        "target_provider_minimum": td["target_provider_discrimination_accuracy"]
        >= primary["treatment_target_provider_discrimination_accuracy_minimum"],
        "neutral_provider_minimum": td["neutral_provider_discrimination_accuracy"]
        >= primary["treatment_neutral_provider_discrimination_accuracy_minimum"],
    }
    generation_checks = {
        "strict_gate_minimum": tg["strict_candidate_gate_pass_rate"]
        >= generation["treatment_strict_candidate_gate_pass_rate_minimum"],
        "semantic_minimum": tg["semantic_contract_pass_rate"]
        >= generation["treatment_semantic_contract_pass_rate_minimum"],
        "memory_minimum": tg["memory_policy_pass_rate"]
        >= generation["treatment_memory_policy_pass_rate_minimum"],
        "private_intrusion_maximum": tg["private_memory_intrusion_count"]
        <= generation["treatment_private_memory_intrusion_count_maximum"],
        "pollution_maximum": tg["language_or_script_pollution_rate"]
        <= generation["treatment_language_or_script_pollution_rate_maximum"],
        "polite_drift_maximum": tg["polite_register_drift_rate"]
        <= generation["treatment_polite_register_drift_rate_maximum"],
        "unique_rate_minimum": tg["normalized_output_unique_rate"]
        >= generation["treatment_normalized_output_unique_rate_minimum"],
        "strict_noninferiority": tg["strict_candidate_gate_pass_rate"]
        - cg["strict_candidate_gate_pass_rate"]
        >= generation["treatment_strict_gate_delta_vs_control_minimum"],
        "semantic_noninferiority": tg["semantic_contract_pass_rate"]
        - cg["semantic_contract_pass_rate"]
        >= generation["treatment_semantic_delta_vs_control_minimum"],
        "memory_noninferiority": tg["memory_policy_pass_rate"]
        - cg["memory_policy_pass_rate"]
        >= generation["treatment_memory_policy_delta_vs_control_minimum"],
        "latency_ratio": tg["median_generation_latency_seconds"]
        / max(ig["median_generation_latency_seconds"], 1e-9)
        <= generation["treatment_median_latency_ratio_vs_initial_maximum"],
        "peak_rss": tg["peak_process_resident_memory_bytes"]
        <= generation["peak_process_resident_memory_bytes_maximum"],
    }
    passed = all(integrity.values()) and all(primary_checks.values()) and all(generation_checks.values())
    return {
        "passed": passed,
        "outcome": (
            "authorize_small_source_blind_human_policy_direction_review_only"
            if passed
            else "reject_role_curriculum_promotion"
        ),
        "integrity_checks": integrity,
        "primary_checks": primary_checks,
        "generation_checks": generation_checks,
        "authorize_production": False,
        "authorize_persona_similarity_claim": False,
        "authorize_public_impersonation": False,
    }


def render_result_markdown(result):
    lines = [
        "# RightBrain 角色課程公平訓練試驗",
        "",
        f"- 決策：`{result['decision']['outcome']}`",
        "- 正式 runtime 修改：`0`",
        "",
        "## 政策方向判別",
        "",
        "| 條件 | 雙向正確率 | target 方向 | neutral 方向 |",
        "|---|---:|---:|---:|",
    ]
    for condition in CONDITIONS:
        metrics = result["evaluations"][condition]["policy_discrimination"]
        lines.append(
            f"| {condition} | {metrics['bidirectional_policy_discrimination_accuracy']:.1%} | "
            f"{metrics['target_provider_discrimination_accuracy']:.1%} | "
            f"{metrics['neutral_provider_discrimination_accuracy']:.1%} |"
        )
    lines.extend(
        [
            "",
            "## 全新生成品質",
            "",
            "| 條件 | 嚴格閘門 | 語意 | 記憶政策 | 唯一輸出 |",
            "|---|---:|---:|---:|---:|",
        ]
    )
    for condition in CONDITIONS:
        metrics = result["evaluations"][condition]["fresh_generation"]
        lines.append(
            f"| {condition} | {metrics['strict_candidate_gate_pass_rate']:.1%} | "
            f"{metrics['semantic_contract_pass_rate']:.1%} | "
            f"{metrics['memory_policy_pass_rate']:.1%} | "
            f"{metrics['normalized_output_unique_rate']:.1%} |"
        )
    lines.extend(
        [
            "",
            "## 證據邊界",
            "",
            "通過只代表政策對應在獨立案例上可被模型學到，且未明顯破壞語意或記憶契約。這不是特定人物相似度、完整聊天品質或正式上線證據。",
        ]
    )
    return "\n".join(lines)


def execute(preflight_report):
    if not preflight_report["passed"]:
        raise RuntimeError("Preflight failed; refusing model execution")
    if os.getenv("HF_HUB_OFFLINE") != "1" or os.getenv("TRANSFORMERS_OFFLINE") != "1":
        raise RuntimeError("Execution requires HF_HUB_OFFLINE=1 and TRANSFORMERS_OFFLINE=1")
    preregistration = construction.load_json(DEFAULT_PREREGISTRATION)
    tokenizer = load_tokenizer(preregistration)
    control = construction.load_json(DEFAULT_CONTROL)
    treatment = construction.load_json(DEFAULT_TREATMENT)
    holdout = construction.load_json(DEFAULT_HOLDOUT)
    training = {}
    training["policy_permuted_control"] = train_condition(
        "policy_permuted_control", control, preregistration, tokenizer
    )
    training["policy_aligned_treatment"] = train_condition(
        "policy_aligned_treatment", treatment, preregistration, tokenizer
    )
    adapter_paths = {
        "initial_v10_reference": ROOT / preregistration["local_model_contract"]["initial_adapter"]["path"],
        "policy_permuted_control": ROOT
        / preregistration["training_schedule"]["output_directories"]["policy_permuted_control"],
        "policy_aligned_treatment": ROOT
        / preregistration["training_schedule"]["output_directories"]["policy_aligned_treatment"],
    }
    evaluations = {}
    for condition in CONDITIONS:
        evaluations[condition] = evaluate_adapter(
            condition,
            adapter_paths[condition],
            preregistration,
            tokenizer,
            holdout,
        )
    decision = decide(preregistration, training, evaluations)
    result = {
        "schema": "uruha_rightbrain_role_curriculum_training_pilot_result_v1",
        "experiment_id": EXPERIMENT_ID,
        "preflight": preflight_report,
        "training": training,
        "evaluations": evaluations,
        "decision": decision,
    }
    construction.atomic_json(DEFAULT_RESULT_JSON, result)
    construction.atomic_text(DEFAULT_RESULT_MD, render_result_markdown(result))
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--execution-lock", default=str(DEFAULT_EXECUTION_LOCK))
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    report = preflight(args.execution_lock)
    print(json.dumps({"preflight_passed": report["passed"], "checks": report["checks"]}, indent=2))
    if not report["passed"]:
        raise SystemExit(1)
    if args.execute:
        result = execute(report)
        print(json.dumps(result["decision"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
