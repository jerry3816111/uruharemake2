#!/usr/bin/env python3
"""Freeze a ten-repeat refinement of the Qwen3 length-instability bracket."""

from __future__ import annotations

import hashlib
import json
import struct
from pathlib import Path

import numpy as np
from transformers import AutoTokenizer

import build_rightbrain_qwen3_4b_trainability_v1 as full_common
import build_rightbrain_qwen3_length_boundary_v1 as boundary_common
import run_rightbrain_mlx_gradient_repro_v1 as gradient_common


ROOT = Path(__file__).resolve().parent
EXPERIMENT_ID = "rightbrain_qwen3_length_boundary_refine_v1"
LENGTH_LEVELS = (640, 656, 672, 688, 704)
REPEATS = tuple(range(1, 11))
DEFAULT_PREREGISTRATION = ROOT / "configs/rightbrain_qwen3_length_boundary_refine_v1_preregistration.json"
DEFAULT_EXECUTION_LOCK = ROOT / "configs/rightbrain_qwen3_length_boundary_refine_v1_execution_lock.json"
DEFAULT_CONSTRUCTION_JSON = ROOT / "reports/rightbrain_qwen3_length_boundary_refine_v1_construction.json"
DEFAULT_CONSTRUCTION_MD = ROOT / "reports/rightbrain_qwen3_length_boundary_refine_v1_construction.md"
RUNNER_PATH = ROOT / "run_rightbrain_qwen3_length_boundary_refine_v1.py"
TEST_PATH = ROOT / "test_rightbrain_qwen3_length_boundary_refine_v1.py"
PARENT_PREREGISTRATION = full_common.DEFAULT_PREREGISTRATION
PARENT_BOUNDARY_RESULT = ROOT / "reports/rightbrain_qwen3_length_boundary_v1_result.json"

load_json = full_common.load_json
sha256_file = full_common.sha256_file
atomic_json = full_common.atomic_json
atomic_text = full_common.atomic_text
file_binding = full_common.file_binding


def canonical_batches(tokenizer, parent_preregistration):
    parent_batches, source = boundary_common.canonical_batches(
        tokenizer, parent_preregistration
    )
    short_ids = parent_batches["64"]["input_ids"]
    short_labels = parent_batches["64"]["labels"]
    pad_id = tokenizer.pad_token_id
    if pad_id is None:
        pad_id = tokenizer.eos_token_id
    batches = {}
    for allocated in LENGTH_LEVELS:
        padding = allocated - 64
        ids = np.concatenate(
            [short_ids, np.full(padding, pad_id, dtype=np.int32)]
        )
        labels = np.concatenate(
            [short_labels, np.full(padding, -100, dtype=np.int32)]
        )
        digest = hashlib.sha256()
        digest.update(struct.pack("<I", allocated))
        digest.update(ids.tobytes())
        digest.update(labels.tobytes())
        batches[str(allocated)] = {
            "input_ids": np.ascontiguousarray(ids, dtype=np.int32),
            "labels": np.ascontiguousarray(labels, dtype=np.int32),
            "sha256": digest.hexdigest(),
            "allocated_tokens": allocated,
            "shared_prefix_tokens": 64,
            "ignored_suffix_tokens": padding,
            "labelled_tokens": parent_batches["64"]["labelled_tokens"],
        }
    for allocated in LENGTH_LEVELS:
        row = batches[str(allocated)]
        if not np.array_equal(row["input_ids"][:64], short_ids):
            raise RuntimeError(f"Input prefix drift at length {allocated}")
        if not np.array_equal(row["labels"][:64], short_labels):
            raise RuntimeError(f"Label prefix drift at length {allocated}")
        if np.any(row["labels"][64:] != -100):
            raise RuntimeError(f"Non-ignored suffix at length {allocated}")
    return batches, source


def build():
    for path in (
        PARENT_PREREGISTRATION,
        PARENT_BOUNDARY_RESULT,
        RUNNER_PATH,
        TEST_PATH,
    ):
        if not path.is_file():
            raise FileNotFoundError(path)
    parent = load_json(PARENT_PREREGISTRATION)
    parent_result = load_json(PARENT_BOUNDARY_RESULT)
    decision = parent_result["decision"]
    if decision["outcome"] != "allocated_length_instability_bracket_localized":
        raise RuntimeError("Unexpected parent boundary result")
    if decision["bracket"] != {
        "highest_tested_stable_length": 640,
        "lowest_tested_unstable_length": 704,
    }:
        raise RuntimeError("Unexpected parent boundary")
    if decision["authorized_next_step"] != "refine_allocated_length_bracket":
        raise RuntimeError("Parent result does not authorize bracket refinement")
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
        "schema": "uruha_rightbrain_qwen3_length_boundary_refine_preregistration_v1",
        "experiment_id": EXPERIMENT_ID,
        "research_question": (
            "Which adjacent 16-token interval inside the frozen 640-704 bracket "
            "separates reproducible from drifting full-Qwen3 gradients?"
        ),
        "causal_variable": {
            "name": "allocated_sequence_length",
            "levels": list(LENGTH_LEVELS),
            "only_intended_change": True,
        },
        "evidence_parent": {
            "path": str(PARENT_BOUNDARY_RESULT.relative_to(ROOT)),
            "sha256": sha256_file(PARENT_BOUNDARY_RESULT),
            "outcome": decision["outcome"],
            "bracket": decision["bracket"],
            "authorized_next_step": decision["authorized_next_step"],
        },
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
            "same_labelled_prefix_across_all_levels": True,
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
            "isolated_repetitions_per_level": list(REPEATS),
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
                "gradient_hashes_must_be_identical": True,
            },
            "anchor_requirements": {
                "640_must_be_stable": True,
                "704_must_be_unstable": True,
            },
            "stability_scope": (
                "Observed reproducibility across ten isolated processes; not a "
                "proof that a length is safe for optimizer-based training."
            ),
            "classifications": {
                "adjacent_monotonic_bracket": "allocated_length_instability_bracket_refined_to_16_tokens",
                "nonmonotonic": "nonmonotonic_refined_length_instability_observed",
                "anchor_failure": "refined_length_boundary_anchor_not_reproduced",
                "execution_failure": "refined_length_boundary_execution_failed",
            },
        },
        "boundaries": {
            "persona_training": False,
            "optimizer_update": False,
            "adapter_or_model_save": False,
            "text_generation": False,
            "production_runtime_change": False,
            "persona_similarity_claim": False,
            "safe_training_length_claim": False,
            "scope": "full_lm_allocated_sequence_length_boundary_refinement_only",
        },
        "result_paths": {
            "repeat_prefix": "reports/rightbrain_qwen3_length_boundary_refine_v1_",
            "aggregate_json": "reports/rightbrain_qwen3_length_boundary_refine_v1_result.json",
            "aggregate_markdown": "reports/rightbrain_qwen3_length_boundary_refine_v1_result.md",
            "result_lock": "configs/rightbrain_qwen3_length_boundary_refine_v1_result_lock.json",
        },
    }
    atomic_json(DEFAULT_PREREGISTRATION, preregistration)
    construction = {
        "schema": "uruha_rightbrain_qwen3_length_boundary_refine_construction_v1",
        "experiment_id": EXPERIMENT_ID,
        "preregistration": file_binding(DEFAULT_PREREGISTRATION),
        "tested_lengths": list(LENGTH_LEVELS),
        "repetitions_each": list(REPEATS),
        "batch_contracts": batch_contracts,
        "ready": True,
    }
    atomic_json(DEFAULT_CONSTRUCTION_JSON, construction)
    atomic_text(
        DEFAULT_CONSTRUCTION_MD,
        "\n".join(
            [
                "# Qwen3 640-704 token 邊界精煉實驗",
                "",
                f"- 長度：`{list(LENGTH_LEVELS)}`。",
                "- 每個長度十個獨立程序，各執行一次 backward。",
                "- 唯一變因是 allocated sequence length。",
                "- 所有條件共享相同 64-token 有效前綴與 16 個 labels。",
                "- 追加內容全部為 label=-100，不參與 loss。",
                "- 不授權訓練、儲存、生成、人格或 production 主張。",
            ]
        )
        + "\n",
    )
    lock = {
        "schema": "uruha_rightbrain_qwen3_length_boundary_refine_execution_lock_v1",
        "experiment_id": EXPERIMENT_ID,
        "bindings": [
            file_binding(DEFAULT_PREREGISTRATION),
            file_binding(DEFAULT_CONSTRUCTION_JSON),
            file_binding(DEFAULT_CONSTRUCTION_MD),
            file_binding(Path(__file__).resolve()),
            file_binding(RUNNER_PATH),
            file_binding(TEST_PATH),
            file_binding(PARENT_PREREGISTRATION),
            file_binding(PARENT_BOUNDARY_RESULT),
            file_binding(ROOT / parent["exact_probe"]["dataset"]),
            *[
                {**binding}
                for binding in load_json(full_common.DEFAULT_EXECUTION_LOCK)["bindings"]
                if binding["scope"] == "external_local"
            ],
        ],
        "authorization": {
            "allocated_sequence_lengths": list(LENGTH_LEVELS),
            "fixed_shared_prefix_tokens": 64,
            "full_language_model_path": True,
            "device": "gpu",
            "repetitions_each": list(REPEATS),
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
