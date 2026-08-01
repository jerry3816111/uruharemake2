#!/usr/bin/env python3
"""Freeze a 64-token versus 800-token full Qwen3 LM backward experiment."""

from __future__ import annotations

import hashlib
import json
import struct
from pathlib import Path

import numpy as np
from transformers import AutoTokenizer

import build_rightbrain_qwen3_4b_trainability_v1 as full_common
import build_rightbrain_qwen3_lora_span_repro_v1 as span_common
import run_rightbrain_mlx_gradient_repro_v1 as gradient_common


ROOT = Path(__file__).resolve().parent
EXPERIMENT_ID = "rightbrain_qwen3_lm_length_repro_v1"
DEFAULT_PREREGISTRATION = ROOT / "configs/rightbrain_qwen3_lm_length_repro_v1_preregistration.json"
DEFAULT_EXECUTION_LOCK = ROOT / "configs/rightbrain_qwen3_lm_length_repro_v1_execution_lock.json"
DEFAULT_CONSTRUCTION_JSON = ROOT / "reports/rightbrain_qwen3_lm_length_repro_v1_construction.json"
DEFAULT_CONSTRUCTION_MD = ROOT / "reports/rightbrain_qwen3_lm_length_repro_v1_construction.md"
RUNNER_PATH = ROOT / "run_rightbrain_qwen3_lm_length_repro_v1.py"
TEST_PATH = ROOT / "test_rightbrain_qwen3_lm_length_repro_v1.py"
PARENT_PREREGISTRATION = full_common.DEFAULT_PREREGISTRATION
PARENT_RESULT = ROOT / "reports/rightbrain_qwen3_4b_trainability_v1_result.json"
SPAN_RESULT = ROOT / "reports/rightbrain_qwen3_lora_span_repro_v1_result.json"

load_json = full_common.load_json
sha256_file = full_common.sha256_file
atomic_json = full_common.atomic_json
atomic_text = full_common.atomic_text
file_binding = full_common.file_binding


def canonical_batches(tokenizer, parent_preregistration):
    batches, details, _ = gradient_common._tokenize_exact_batch(
        parent_preregistration, tokenizer
    )
    if len(batches) != 1:
        raise RuntimeError("Expected exactly one frozen parent batch")
    input_ids, labels = batches[0]
    active_tokens = int(details[0]["active_tokens"])
    short_length = 64
    if active_tokens < short_length:
        raise RuntimeError("Parent batch is shorter than the frozen LM prefix")
    short_ids = np.ascontiguousarray(
        input_ids[active_tokens - short_length : active_tokens], dtype=np.int32
    )
    short_labels = np.ascontiguousarray(
        labels[active_tokens - short_length : active_tokens], dtype=np.int32
    )
    labelled_tokens = int(np.count_nonzero(short_labels != -100))
    if labelled_tokens <= 0:
        raise RuntimeError("Frozen short prefix contains no completion labels")
    pad_id = tokenizer.pad_token_id
    if pad_id is None:
        pad_id = tokenizer.eos_token_id
    result = {}
    for allocated in (64, 800):
        padding = allocated - short_length
        ids = np.concatenate(
            [short_ids, np.full(padding, pad_id, dtype=np.int32)]
        )
        current_labels = np.concatenate(
            [short_labels, np.full(padding, -100, dtype=np.int32)]
        )
        digest = hashlib.sha256()
        digest.update(struct.pack("<I", allocated))
        digest.update(ids.tobytes())
        digest.update(current_labels.tobytes())
        result[str(allocated)] = {
            "input_ids": ids,
            "labels": current_labels,
            "sha256": digest.hexdigest(),
            "allocated_tokens": allocated,
            "shared_prefix_tokens": short_length,
            "ignored_suffix_tokens": padding,
            "labelled_tokens": labelled_tokens,
        }
    if not np.array_equal(
        result["64"]["input_ids"], result["800"]["input_ids"][:64]
    ) or not np.array_equal(
        result["64"]["labels"], result["800"]["labels"][:64]
    ):
        raise RuntimeError("64-token prefix differs across length conditions")
    return result, {
        "parent_row_index": parent_preregistration["exact_probe"]["row_indices"][0],
        "parent_row_id": details[0]["row_id"],
        "parent_active_tokens": active_tokens,
        "slice": [active_tokens - short_length, active_tokens],
        "labelled_tokens": labelled_tokens,
    }


def build():
    for path in (
        PARENT_PREREGISTRATION,
        PARENT_RESULT,
        SPAN_RESULT,
        RUNNER_PATH,
        TEST_PATH,
    ):
        if not path.is_file():
            raise FileNotFoundError(path)
    parent = load_json(PARENT_PREREGISTRATION)
    parent_result = load_json(PARENT_RESULT)
    span_result = load_json(SPAN_RESULT)
    if parent_result["decision"]["outcome"] != "qwen3_4b_candidate_trainability_gate_failed":
        raise RuntimeError("Unexpected parent trainability result")
    if span_result["decision"]["outcome"] != "lora_span_alone_does_not_reproduce_full_model_drift":
        raise RuntimeError("Unexpected LoRA-span result")
    tokenizer = AutoTokenizer.from_pretrained(
        parent["local_model_contract"]["snapshot_root"],
        local_files_only=True,
        trust_remote_code=True,
    )
    batches, source = canonical_batches(tokenizer, parent)
    batch_contracts = {
        length: {
            key: value
            for key, value in row.items()
            if key not in ("input_ids", "labels")
        }
        for length, row in batches.items()
    }
    preregistration = {
        "schema": "uruha_rightbrain_qwen3_lm_length_repro_preregistration_v1",
        "experiment_id": EXPERIMENT_ID,
        "research_question": (
            "Does extending an otherwise identical full Qwen3 language-model graph "
            "from 64 to 800 tokens with ignored suffix padding reproduce gradient drift?"
        ),
        "causal_variable": {
            "name": "allocated_sequence_length",
            "levels": [64, 800],
            "only_intended_change": True,
        },
        "evidence_parents": [
            {
                "path": str(PARENT_RESULT.relative_to(ROOT)),
                "sha256": sha256_file(PARENT_RESULT),
                "outcome": parent_result["decision"]["outcome"],
            },
            {
                "path": str(SPAN_RESULT.relative_to(ROOT)),
                "sha256": sha256_file(SPAN_RESULT),
                "outcome": span_result["decision"]["outcome"],
            },
        ],
        "local_environment": gradient_common._environment(),
        "local_model_contract": parent["local_model_contract"],
        "adapter_initialization_contract": parent["adapter_initialization_contract"],
        "batch_contracts": batch_contracts,
        "batch_source": {
            **source,
            "dataset": parent["exact_probe"]["dataset"],
            "dataset_sha256": sha256_file(ROOT / parent["exact_probe"]["dataset"]),
            "synthetic_source_independent": True,
            "contains_target_utterance": False,
            "contains_benchmark_item_or_answer": False,
            "same_labelled_prefix_across_conditions": True,
            "suffix_labels": -100,
        },
        "exact_probe": {
            "device": "gpu_metal",
            "full_transformer_layers": 36,
            "lora_enabled_layers": 36,
            "full_language_model_path": [
                "token_embedding",
                "36_transformer_layers",
                "final_rms_norm",
                "tied_lm_head",
                "masked_cross_entropy",
            ],
            "isolated_repetitions_per_level": [1, 2, 3],
            "micro_steps_each": 1,
            "optimizer_steps": 0,
            "gradient_checkpointing": False,
            "random_seed": 20260802,
            "memory_limit_bytes": 30 * 1024**3,
            "wired_limit_bytes": 20 * 1024**3,
        },
        "falsifiable_outcomes": {
            "within_level_reproducibility": {
                "gradient_norm_coefficient_of_variation_maximum": 0.005,
                "gradient_norm_max_to_min_ratio_maximum": 1.02,
                "minimum_pairwise_group_profile_cosine": 0.9999,
            },
            "classifications": {
                "short_stable_long_unstable": "ignored_padding_length_reproduces_gradient_drift",
                "short_unstable_long_unstable": "full_lm_objective_unstable_even_at_short_length",
                "short_stable_long_stable": "ignored_padding_length_alone_does_not_reproduce_parent_drift",
                "short_unstable_long_stable": "short_length_control_invalid",
            },
        },
        "boundaries": {
            "persona_training": False,
            "optimizer_update": False,
            "adapter_or_model_save": False,
            "text_generation": False,
            "production_runtime_change": False,
            "persona_similarity_claim": False,
            "active_context_length_claim": False,
            "scope": "full_lm_ignored_padding_length_localization_only",
        },
        "result_paths": {
            "repeat_prefix": "reports/rightbrain_qwen3_lm_length_repro_v1_",
            "aggregate_json": "reports/rightbrain_qwen3_lm_length_repro_v1_result.json",
            "aggregate_markdown": "reports/rightbrain_qwen3_lm_length_repro_v1_result.md",
            "result_lock": "configs/rightbrain_qwen3_lm_length_repro_v1_result_lock.json",
        },
    }
    atomic_json(DEFAULT_PREREGISTRATION, preregistration)
    construction = {
        "schema": "uruha_rightbrain_qwen3_lm_length_repro_construction_v1",
        "experiment_id": EXPERIMENT_ID,
        "preregistration": file_binding(DEFAULT_PREREGISTRATION),
        "batch_contracts": batch_contracts,
        "batch_source": preregistration["batch_source"],
        "model_parameter_count": parent["local_model_contract"]["base_parameter_count"],
        "adapter_parameter_count": parent["adapter_initialization_contract"]["trainable_parameter_count"],
        "ready": True,
    }
    atomic_json(DEFAULT_CONSTRUCTION_JSON, construction)
    atomic_text(
        DEFAULT_CONSTRUCTION_MD,
        "\n".join(
            [
                "# Qwen3 完整 LM 64 / 800 token 定位實驗",
                "",
                "- 唯一變因：64 或 800 token 計算圖。",
                "- 兩組前 64 token、有效標籤與所有模型元件完全相同。",
                "- 800-token 組只追加 736 個 label=-100 的 padding。",
                "- 固定 36 層、全 LoRA、LM head、交叉熵、Metal 與零更新。",
                "- 不包含人格、benchmark 或 production 修改。",
            ]
        )
        + "\n",
    )
    lock = {
        "schema": "uruha_rightbrain_qwen3_lm_length_repro_execution_lock_v1",
        "experiment_id": EXPERIMENT_ID,
        "bindings": [
            file_binding(DEFAULT_PREREGISTRATION),
            file_binding(DEFAULT_CONSTRUCTION_JSON),
            file_binding(DEFAULT_CONSTRUCTION_MD),
            file_binding(Path(__file__).resolve()),
            file_binding(RUNNER_PATH),
            file_binding(TEST_PATH),
            file_binding(PARENT_PREREGISTRATION),
            file_binding(PARENT_RESULT),
            file_binding(SPAN_RESULT),
            file_binding(ROOT / parent["exact_probe"]["dataset"]),
            *[
                {**binding}
                for binding in load_json(full_common.DEFAULT_EXECUTION_LOCK)["bindings"]
                if binding["scope"] == "external_local"
            ],
        ],
        "authorization": {
            "allocated_sequence_lengths": [64, 800],
            "fixed_shared_prefix_tokens": 64,
            "full_language_model_path": True,
            "device": "gpu",
            "repetitions_each": [1, 2, 3],
            "optimizer_steps": 0,
            "gradient_checkpointing": False,
            "adapter_or_model_save": False,
            "text_generation": False,
            "production_runtime_change": False,
        },
    }
    atomic_json(DEFAULT_EXECUTION_LOCK, lock)
    return construction


def main():
    print(json.dumps(build(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
