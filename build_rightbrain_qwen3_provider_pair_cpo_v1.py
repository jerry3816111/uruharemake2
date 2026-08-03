#!/usr/bin/env python3
"""Freeze a matched SFT-versus-provider-pair CPO objective probe."""

from __future__ import annotations

import copy
import hashlib
import json
import struct
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from transformers import AutoTokenizer

import build_rightbrain_qwen3_active_head_64step_v1 as model_parent
import build_rightbrain_qwen3_active_head_multibatch_v1 as data_parent
import build_rightbrain_qwen3_fresh_generation_v1 as evidence_parent


ROOT = Path(__file__).resolve().parent
EXPERIMENT_ID = "rightbrain_qwen3_provider_pair_cpo_v1"
CONDITIONS = ("sft_control", "provider_pair_cpo")
REPEATS = (1, 2, 3)
EXECUTION_SCHEDULE = (
    ("sft_control", 1),
    ("provider_pair_cpo", 1),
    ("provider_pair_cpo", 2),
    ("sft_control", 2),
    ("sft_control", 3),
    ("provider_pair_cpo", 3),
)
ALLOCATED_TOKENS = 512
TRAIN_ROW_INDICES = data_parent.TRAIN_ROW_INDICES
TRAIN_SCHEDULE = TRAIN_ROW_INDICES
TRAIN_EVAL_ROW_INDICES = (0, 2, 20, 22, 40, 42, 60, 62)
HOLDOUT_ROW_INDICES = (12, 14, 16, 18, 36, 38, 56, 58)
PAIRWISE_BETA = 1.0
PAIRWISE_WEIGHTS = {"sft_control": 0.0, "provider_pair_cpo": 1.0}
DEFAULT_PREREGISTRATION = (
    ROOT / "configs/rightbrain_qwen3_provider_pair_cpo_v1_preregistration.json"
)
DEFAULT_EXECUTION_LOCK = (
    ROOT / "configs/rightbrain_qwen3_provider_pair_cpo_v1_execution_lock.json"
)
DEFAULT_CONSTRUCTION_JSON = (
    ROOT / "reports/rightbrain_qwen3_provider_pair_cpo_v1_construction.json"
)
DEFAULT_CONSTRUCTION_MD = (
    ROOT / "reports/rightbrain_qwen3_provider_pair_cpo_v1_construction.md"
)
RUNNER_PATH = ROOT / "run_rightbrain_qwen3_provider_pair_cpo_v1.py"
TEST_PATH = ROOT / "test_rightbrain_qwen3_provider_pair_cpo_v1.py"
VERIFIER_PATH = ROOT / "verify_rightbrain_qwen3_provider_pair_cpo_v1_result.py"
PARENT_PREREGISTRATION = model_parent.DEFAULT_PREREGISTRATION
PARENT_FRESH_RESULT = (
    ROOT / "reports/rightbrain_qwen3_fresh_generation_v1_result.json"
)
PARENT_FRESH_RESULT_LOCK = (
    ROOT / "configs/rightbrain_qwen3_fresh_generation_v1_result_lock.json"
)
PARENT_FRESH_DIAGNOSIS = (
    ROOT / "reports/rightbrain_qwen3_fresh_generation_v1_diagnosis.md"
)
DATASET_PATH = data_parent.DATASET_PATH
DATASET_RESULT_LOCK = data_parent.DATASET_RESULT_LOCK
MODEL_SOURCE_PREREGISTRATION = data_parent.MODEL_SOURCE_PREREGISTRATION
MLX_OPTIMIZERS_PATH = data_parent.MLX_OPTIMIZERS_PATH

load_json = model_parent.load_json
sha256_file = model_parent.sha256_file
atomic_json = model_parent.atomic_json
atomic_text = model_parent.atomic_text
file_binding = model_parent.file_binding


def canonical_json_sha256(value):
    encoded = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _position_contract(labels):
    positions = [index for index, value in enumerate(labels[1:]) if value != -100]
    encoded = ",".join(str(value) for value in positions).encode("ascii")
    return {
        "positions": positions,
        "count": len(positions),
        "sha256": hashlib.sha256(encoded).hexdigest(),
    }


def _prompt_without_persona(row):
    if [message["role"] for message in row["messages"]] != [
        "system",
        "user",
        "assistant",
    ]:
        raise RuntimeError(f"Unexpected message contract for {row['id']}")
    payload = json.loads(row["messages"][1]["content"])
    persona = payload["context"].pop("persona_expression_brief")
    return {
        "system": row["messages"][0]["content"],
        "payload_without_persona": payload,
    }, persona


def provider_pair_map(rows, indices):
    grouped = defaultdict(lambda: defaultdict(dict))
    for index, row in enumerate(rows):
        grouped[row["source_id"]][row["provider_id"]][row["variant_index"]] = index
    selected = {}
    for index in indices:
        row = rows[index]
        providers = grouped[row["source_id"]]
        opposite = [name for name in providers if name != row["provider_id"]]
        if len(opposite) != 1:
            raise RuntimeError(f"Provider pair is not unique for {row['id']}")
        rejected_index = providers[opposite[0]].get(row["variant_index"])
        if rejected_index is None:
            raise RuntimeError(f"Variant pair is missing for {row['id']}")
        paired = rows[rejected_index]
        left_prompt, left_persona = _prompt_without_persona(row)
        right_prompt, right_persona = _prompt_without_persona(paired)
        if left_prompt != right_prompt:
            raise RuntimeError(f"Pair differs outside persona fields for {row['id']}")
        if left_persona == right_persona:
            raise RuntimeError(f"Pair persona fields are identical for {row['id']}")
        if row["messages"][-1]["content"] == paired["messages"][-1]["content"]:
            raise RuntimeError(f"Pair answers are identical for {row['id']}")
        selected[index] = rejected_index
    return selected


def _encode_completion(tokenizer, prompt_messages, answer):
    pad_id = tokenizer.pad_token_id
    if pad_id is None:
        pad_id = tokenizer.eos_token_id
    prompt = tokenizer.apply_chat_template(
        prompt_messages, tokenize=False, add_generation_prompt=True
    )
    answer_text = f"{str(answer).strip()}<|im_end|>"
    prompt_ids = tokenizer.encode(prompt, add_special_tokens=False)
    answer_ids = tokenizer.encode(answer_text, add_special_tokens=False)
    full_ids = prompt_ids + answer_ids
    full_labels = [-100] * len(prompt_ids) + answer_ids
    slice_start = max(0, len(full_ids) - ALLOCATED_TOKENS)
    input_ids = full_ids[slice_start:]
    labels = full_labels[slice_start:]
    padding = ALLOCATED_TOKENS - len(input_ids)
    if padding < 0:
        raise RuntimeError("Completion truncation failed")
    input_ids = np.asarray(input_ids + [pad_id] * padding, dtype=np.int32)
    labels = np.asarray(labels + [-100] * padding, dtype=np.int32)
    positions = _position_contract(labels)
    if positions["count"] != len(answer_ids):
        raise RuntimeError("Completion answer tokens were truncated")
    return {
        "input_ids": input_ids,
        "labels": labels,
        "positions": positions,
        "full_tokens": len(full_ids),
        "left_truncated_tokens": slice_start,
        "retained_prompt_tokens": len(prompt_ids) - slice_start,
        "answer_tokens": len(answer_ids),
    }


def canonical_pair_batches(tokenizer, rows):
    selected = tuple(dict.fromkeys(TRAIN_ROW_INDICES + HOLDOUT_ROW_INDICES))
    pairs = provider_pair_map(rows, selected)
    batches = {}
    details = []
    combined = hashlib.sha256()
    for index in selected:
        row = rows[index]
        rejected_index = pairs[index]
        rejected = rows[rejected_index]
        prompt_messages = row["messages"][:-1]
        preferred = _encode_completion(
            tokenizer, prompt_messages, row["messages"][-1]["content"]
        )
        rejected_batch = _encode_completion(
            tokenizer, prompt_messages, rejected["messages"][-1]["content"]
        )
        digest = hashlib.sha256()
        digest.update(struct.pack("<II", index, rejected_index))
        for batch in (preferred, rejected_batch):
            digest.update(batch["input_ids"].tobytes())
            digest.update(batch["labels"].tobytes())
        row_hash = digest.hexdigest()
        combined.update(bytes.fromhex(row_hash))
        batches[index] = {
            "preferred": preferred,
            "rejected": rejected_batch,
            "rejected_index": rejected_index,
        }
        details.append(
            {
                "row_index": index,
                "row_id": row["id"],
                "source_id": row["source_id"],
                "provider_id": row["provider_id"],
                "memory_mode": row["memory_mode"],
                "variant_index": row["variant_index"],
                "rejected_row_index": rejected_index,
                "rejected_row_id": rejected["id"],
                "rejected_provider_id": rejected["provider_id"],
                "preferred": {
                    key: preferred[key]
                    for key in (
                        "full_tokens",
                        "left_truncated_tokens",
                        "retained_prompt_tokens",
                        "answer_tokens",
                        "positions",
                    )
                },
                "rejected": {
                    key: rejected_batch[key]
                    for key in (
                        "full_tokens",
                        "left_truncated_tokens",
                        "retained_prompt_tokens",
                        "answer_tokens",
                        "positions",
                    )
                },
                "sha256": row_hash,
            }
        )
    return batches, details, combined.hexdigest()


def _source_counts(rows, indices):
    return dict(sorted(Counter(rows[index]["source_id"] for index in indices).items()))


def build():
    required = (
        PARENT_PREREGISTRATION,
        PARENT_FRESH_RESULT,
        PARENT_FRESH_RESULT_LOCK,
        PARENT_FRESH_DIAGNOSIS,
        DATASET_PATH,
        DATASET_RESULT_LOCK,
        MODEL_SOURCE_PREREGISTRATION,
        MLX_OPTIMIZERS_PATH,
        RUNNER_PATH,
        TEST_PATH,
        VERIFIER_PATH,
    )
    for path in required:
        if not path.is_file():
            raise FileNotFoundError(path)

    parent = load_json(PARENT_PREREGISTRATION)
    failed_generation = load_json(PARENT_FRESH_RESULT)
    failed_lock = load_json(PARENT_FRESH_RESULT_LOCK)
    decision = failed_generation["decision"]
    if decision["outcome"] != "fresh_generation_contract_not_improved":
        raise RuntimeError("Unexpected fresh-generation parent outcome")
    if decision["authorized_next_step"] != "diagnose_fresh_generation_behavior_failure":
        raise RuntimeError("Parent does not authorize failure diagnosis")
    if any(failed_lock["authorization"].values()):
        raise RuntimeError("Parent unexpectedly grants persistent authorization")

    rows = load_json(DATASET_PATH)
    if len(rows) != 80:
        raise RuntimeError("Unexpected curriculum row count")
    train_sources = {rows[index]["source_id"] for index in TRAIN_ROW_INDICES}
    holdout_sources = {rows[index]["source_id"] for index in HOLDOUT_ROW_INDICES}
    previously_used = set(
        data_parent.TRAIN_ROW_INDICES
        + data_parent.HOLDOUT_ROW_INDICES
        + evidence_parent.FRESH_GENERATION_ROW_INDICES
        + evidence_parent.FRESH_REFERENCE_ALT_ROW_INDICES
    )
    previous_sources = {rows[index]["source_id"] for index in previously_used}
    if train_sources & holdout_sources:
        raise RuntimeError("Train and CPO holdout sources overlap")
    if holdout_sources & previous_sources:
        raise RuntimeError("CPO holdout sources were used by prior experiments")
    if len(train_sources) != 4 or len(holdout_sources) != 4:
        raise RuntimeError("Expected four train and four CPO holdout sources")
    train_answers = {
        rows[index]["messages"][-1]["content"].strip()
        for index in TRAIN_ROW_INDICES
    }
    holdout_answers = {
        rows[index]["messages"][-1]["content"].strip()
        for index in HOLDOUT_ROW_INDICES
    }
    if train_answers & holdout_answers:
        raise RuntimeError("Train and CPO holdout answers overlap exactly")
    train_pairs = provider_pair_map(rows, TRAIN_ROW_INDICES)
    holdout_pairs = provider_pair_map(rows, HOLDOUT_ROW_INDICES)
    if set(train_pairs) != set(TRAIN_ROW_INDICES):
        raise RuntimeError("Train pair map is incomplete")
    if set(holdout_pairs) != set(HOLDOUT_ROW_INDICES):
        raise RuntimeError("Holdout pair map is incomplete")
    selected_rows = [rows[index] for index in TRAIN_ROW_INDICES + HOLDOUT_ROW_INDICES]
    if not all(
        row["provenance"]["synthetic"] is True
        and row["provenance"]["source_independent"] is True
        and row["provenance"]["contains_target_utterance"] is False
        and row["provenance"]["contains_benchmark_item"] is False
        for row in selected_rows
    ):
        raise RuntimeError("Selected rows violate source-independent provenance")
    if Counter(rows[index]["provider_id"] for index in HOLDOUT_ROW_INDICES) != {
        "structured_target_public_persona": 4,
        "structured_neutral_dialogue": 4,
    }:
        raise RuntimeError("CPO holdout provider split is not balanced")
    if Counter(rows[index]["memory_mode"] for index in HOLDOUT_ROW_INDICES) != {
        "background_only": 2,
        "do_not_mention": 2,
        "explicit_allowed": 2,
        "no_memory": 2,
    }:
        raise RuntimeError("CPO holdout memory split is not balanced")

    tokenizer = AutoTokenizer.from_pretrained(
        parent["local_model_contract"]["snapshot_root"],
        local_files_only=True,
        trust_remote_code=True,
    )
    _, token_details, token_hash = canonical_pair_batches(tokenizer, rows)
    prereg = copy.deepcopy(parent)
    prereg.update(
        {
            "schema": "uruha_rightbrain_qwen3_provider_pair_cpo_preregistration_v1",
            "experiment_id": EXPERIMENT_ID,
            "research_question": (
                "Does adding only a condition-matched opposite-provider preference term "
                "improve provider-specific likelihood margins on four never-used sources "
                "relative to a compute-matched SFT control?"
            ),
            "conditions": {
                "sft_control": {
                    "preferred_sft_weight": 1.0,
                    "pairwise_weight": 0.0,
                    "pairwise_beta": PAIRWISE_BETA,
                },
                "provider_pair_cpo": {
                    "preferred_sft_weight": 1.0,
                    "pairwise_weight": 1.0,
                    "pairwise_beta": PAIRWISE_BETA,
                },
            },
            "causal_scope": {
                "name": "provider_pairwise_objective_weight",
                "control_value": 0.0,
                "candidate_value": 1.0,
                "only_changed_variable": "pairwise_weight",
                "unchanged": [
                    "base_model_and_snapshot",
                    "fresh_lora_initialization",
                    "preferred_and_rejected_pair_batches",
                    "train_rows_and_order",
                    "optimizer_and_gradient_clipping",
                    "update_count",
                    "sequence_length",
                    "device_and_environment",
                    "holdout_rows_and_scoring",
                ],
                "persistent_artifact_written": False,
            },
            "evidence_parent": {
                "result": file_binding(PARENT_FRESH_RESULT),
                "result_lock": file_binding(PARENT_FRESH_RESULT_LOCK),
                "diagnosis": file_binding(PARENT_FRESH_DIAGNOSIS),
                "outcome": decision["outcome"],
                "observed_provider_pair_difference_delta": -0.25,
            },
            "pair_contract": {
                "train_row_indices": list(TRAIN_ROW_INDICES),
                "train_schedule": list(TRAIN_SCHEDULE),
                "train_eval_row_indices": list(TRAIN_EVAL_ROW_INDICES),
                "train_pair_map": {str(key): value for key, value in sorted(train_pairs.items())},
                "holdout_row_indices": list(HOLDOUT_ROW_INDICES),
                "holdout_pair_map": {str(key): value for key, value in sorted(holdout_pairs.items())},
                "train_source_counts": _source_counts(rows, TRAIN_ROW_INDICES),
                "holdout_source_counts": _source_counts(rows, HOLDOUT_ROW_INDICES),
                "train_holdout_source_overlap": 0,
                "train_holdout_exact_answer_overlap": 0,
                "holdout_prior_experiment_source_overlap": 0,
                "holdout_provider_counts": dict(
                    sorted(Counter(rows[index]["provider_id"] for index in HOLDOUT_ROW_INDICES).items())
                ),
                "holdout_memory_mode_counts": dict(
                    sorted(Counter(rows[index]["memory_mode"] for index in HOLDOUT_ROW_INDICES).items())
                ),
                "prompt_differences_outside_persona": 0,
                "target_person_utterances": 0,
                "benchmark_items": 0,
            },
            "token_contract": {
                "allocated_tokens": ALLOCATED_TOKENS,
                "sha256": token_hash,
                "details": token_details,
            },
        }
    )
    prereg["exact_probe"] = {
        **parent["exact_probe"],
        "conditions": list(CONDITIONS),
        "isolated_repetitions": list(REPEATS),
        "execution_schedule": [list(item) for item in EXECUTION_SCHEDULE],
        "train_rows": len(TRAIN_ROW_INDICES),
        "holdout_rows": len(HOLDOUT_ROW_INDICES),
        "epochs": 1,
        "micro_steps_each": len(TRAIN_SCHEDULE),
        "optimizer_updates_each": len(TRAIN_SCHEDULE),
        "pre_and_post_evaluation_rows_each": len(HOLDOUT_ROW_INDICES),
        "allocated_sequence_length": ALLOCATED_TOKENS,
        "preferred_and_rejected_backward_each_update": True,
    }
    prereg["optimizer_contract"] = {
        **parent["optimizer_contract"],
        "optimizer_updates_exact": len(TRAIN_SCHEDULE),
    }
    prereg["falsifiable_hypothesis"] = {
        "confirm_if_all": {
            "all_six_runs_successful": True,
            "all_values_finite": True,
            "initial_parameter_hash_equal_between_conditions": True,
            "pre_holdout_metrics_equal_between_conditions": True,
            "control_and_candidate_each_reproducible": True,
            "optimizer_step_exact": len(TRAIN_SCHEDULE),
            "candidate_holdout_margin_delta_positive": True,
            "candidate_holdout_margin_delta_exceeds_control": True,
            "candidate_post_holdout_margin_exceeds_control": True,
            "candidate_post_correct_preference_rate_not_below_control": True,
            "candidate_post_preferred_nll_regression_vs_control_maximum": 0.02,
            "candidate_train_final_margin_exceeds_control": True,
            "parameter_delta_l2_maximum": 0.5,
            "parameter_relative_delta_maximum": 0.02,
            "parameter_max_absolute_delta_maximum": 0.001,
            "clipped_gradient_norm_maximum": 0.300001,
            "peak_memory_bytes_maximum": parent["exact_probe"]["memory_limit_bytes"],
        },
        "success_outcome": "provider_pair_cpo_holdout_margin_confirmed",
        "failure_outcomes": [
            "provider_pair_cpo_execution_failed",
            "provider_pair_cpo_not_reproducible",
            "provider_pair_cpo_holdout_margin_not_improved",
            "provider_pair_cpo_preferred_likelihood_regressed",
            "provider_pair_cpo_mutation_out_of_bounds",
        ],
    }
    prereg["success_authorization"] = {
        "maximum_positive_next_step": (
            "preregister_provider_pair_cpo_64step_fresh_generation_probe"
        ),
        "persistent_training": False,
        "persona_training": False,
        "adapter_save": False,
        "runtime_activation": False,
        "persona_similarity_claim": False,
    }
    prereg["boundaries"] = {
        **parent["boundaries"],
        "ephemeral_optimizer_updates_exact": len(TRAIN_SCHEDULE),
        "text_generation": False,
        "target_person_utterance_training": False,
        "benchmark_training": False,
        "adapter_or_model_save": False,
        "production_runtime_change": False,
        "scope": "qwen3_provider_pair_cpo_16update_likelihood_probe_only",
    }
    prereg["interpretation_limits"] = [
        "A pass shows only that the pairwise objective improves source-disjoint provider-conditioned likelihood margins after 16 updates.",
        "It does not prove generation quality, target-person fidelity, persistent save/reload equivalence, or production readiness.",
        "All preferred and rejected answers are synthetic source-independent curriculum data, not target-person utterances or benchmark items.",
    ]
    prereg["result_paths"] = {
        "condition_prefix": "reports/rightbrain_qwen3_provider_pair_cpo_v1_",
        "aggregate_json": "reports/rightbrain_qwen3_provider_pair_cpo_v1_result.json",
        "aggregate_markdown": "reports/rightbrain_qwen3_provider_pair_cpo_v1_result.md",
        "result_lock": "configs/rightbrain_qwen3_provider_pair_cpo_v1_result_lock.json",
    }
    atomic_json(DEFAULT_PREREGISTRATION, prereg)
    construction = {
        "schema": "uruha_rightbrain_qwen3_provider_pair_cpo_construction_v1",
        "experiment_id": EXPERIMENT_ID,
        "preregistration": file_binding(DEFAULT_PREREGISTRATION),
        "conditions": prereg["conditions"],
        "pair_contract": prereg["pair_contract"],
        "token_contract_sha256": token_hash,
        "ready": True,
    }
    atomic_json(DEFAULT_CONSTRUCTION_JSON, construction)
    atomic_text(
        DEFAULT_CONSTRUCTION_MD,
        "\n".join(
            [
                "# Qwen3 provider-pair CPO objective probe",
                "",
                "- 唯一變因：pairwise objective weight `0` 或 `1`。",
                "- 16 個平衡 train rows，各做 16 次更新。",
                "- 8 個 holdout prompts 來自四個先前完全未使用來源。",
                "- 不生成文字、不保存 adapter、不使用本人原句或 benchmark。",
            ]
        )
        + "\n",
    )
    lock = {
        "schema": "uruha_rightbrain_qwen3_provider_pair_cpo_execution_lock_v1",
        "experiment_id": EXPERIMENT_ID,
        "bindings": [
            file_binding(DEFAULT_PREREGISTRATION),
            file_binding(DEFAULT_CONSTRUCTION_JSON),
            file_binding(DEFAULT_CONSTRUCTION_MD),
            file_binding(Path(__file__).resolve()),
            file_binding(RUNNER_PATH),
            file_binding(TEST_PATH),
            file_binding(VERIFIER_PATH),
            file_binding(PARENT_PREREGISTRATION),
            file_binding(PARENT_FRESH_RESULT),
            file_binding(PARENT_FRESH_RESULT_LOCK),
            file_binding(PARENT_FRESH_DIAGNOSIS),
            file_binding(DATASET_PATH),
            file_binding(DATASET_RESULT_LOCK),
            file_binding(MODEL_SOURCE_PREREGISTRATION),
            file_binding(MLX_OPTIMIZERS_PATH),
        ],
        "authorization": {
            "conditions": list(CONDITIONS),
            "repetitions": list(REPEATS),
            "execution_schedule": [list(item) for item in EXECUTION_SCHEDULE],
            "train_row_indices": list(TRAIN_ROW_INDICES),
            "train_schedule": list(TRAIN_SCHEDULE),
            "train_eval_row_indices": list(TRAIN_EVAL_ROW_INDICES),
            "holdout_row_indices": list(HOLDOUT_ROW_INDICES),
            "pairwise_beta": PAIRWISE_BETA,
            "pairwise_weights": PAIRWISE_WEIGHTS,
            "allocated_sequence_length": ALLOCATED_TOKENS,
            "full_transformer_layers": 36,
            "lora_enabled_layers": 36,
            "device": "gpu",
            "optimizer_contract": prereg["optimizer_contract"],
            "optimizer_updates_each": len(TRAIN_SCHEDULE),
            "gradient_checkpointing": False,
            "adapter_or_model_save": False,
            "text_generation": False,
            "target_person_utterance_training": False,
            "benchmark_training": False,
            "production_runtime_change": False,
        },
    }
    atomic_json(DEFAULT_EXECUTION_LOCK, lock)
    return construction


def main():
    print(json.dumps(build(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
