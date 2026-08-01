#!/usr/bin/env python3
"""Freeze a one-layer versus all-layer Qwen3 LoRA-span experiment."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import mlx.core as mx
import numpy as np
from mlx.utils import tree_flatten
from mlx_lm.tuner.utils import linear_to_lora_layers

import build_rightbrain_qwen3_depth_repro_v1 as depth_common
import run_rightbrain_mlx_gradient_repro_v1 as gradient_common


ROOT = Path(__file__).resolve().parent
EXPERIMENT_ID = "rightbrain_qwen3_lora_span_repro_v1"
DEFAULT_PREREGISTRATION = ROOT / "configs/rightbrain_qwen3_lora_span_repro_v1_preregistration.json"
DEFAULT_EXECUTION_LOCK = ROOT / "configs/rightbrain_qwen3_lora_span_repro_v1_execution_lock.json"
DEFAULT_CONSTRUCTION_JSON = ROOT / "reports/rightbrain_qwen3_lora_span_repro_v1_construction.json"
DEFAULT_CONSTRUCTION_MD = ROOT / "reports/rightbrain_qwen3_lora_span_repro_v1_construction.md"
RUNNER_PATH = ROOT / "run_rightbrain_qwen3_lora_span_repro_v1.py"
TEST_PATH = ROOT / "test_rightbrain_qwen3_lora_span_repro_v1.py"

load_json = depth_common.load_json
sha256_file = depth_common.sha256_file
atomic_json = depth_common.atomic_json
atomic_text = depth_common.atomic_text
file_binding = depth_common.file_binding
canonical_input = depth_common.canonical_input


def _flat_sha256(rows):
    digest = hashlib.sha256()
    for name, value in sorted(rows, key=lambda row: row[0]):
        array = np.asarray(value.astype(mx.float32))
        digest.update(name.encode("utf-8"))
        digest.update(str(tuple(array.shape)).encode("ascii"))
        digest.update(array.tobytes())
    return digest.hexdigest()


def initialize_adapter_span(model, span, seed, rank, scale, dropout):
    if span not in (1, 36):
        raise ValueError("span must be 1 or 36")
    if span == 1:
        depth_common.initialize_first_layer_adapter(model, seed, rank, scale, dropout)
    else:
        model.freeze()
        mx.random.seed(seed)
        linear_to_lora_layers(
            model,
            36,
            {"rank": rank, "scale": scale, "dropout": dropout},
        )
        mx.eval(model.trainable_parameters())
    flat = tree_flatten(model.trainable_parameters())
    first_layer = [(name, value) for name, value in flat if name.startswith("layers.0.")]
    return {
        "span": span,
        "tensor_count": len(flat),
        "parameter_count": sum(value.size for _, value in flat),
        "dtypes": sorted({str(value.dtype) for _, value in flat}),
        "sha256": gradient_common._parameter_sha256(model.trainable_parameters()),
        "first_layer_tensor_count": len(first_layer),
        "first_layer_sha256": _flat_sha256(first_layer),
    }


def _base_contract(model, selected):
    flat = tree_flatten(model.parameters())
    return {
        "layer_count": 36,
        "selected_weight_tensor_count": selected,
        "parameter_count": sum(value.size for _, value in flat),
        "dtypes": sorted({str(value.dtype) for _, value in flat}),
        "sha256": gradient_common._parameter_sha256(model.parameters()),
    }


def build():
    for path in [depth_common.CONFIG_PATH, *depth_common.WEIGHT_SHARDS, RUNNER_PATH, TEST_PATH]:
        if not path.is_file():
            raise FileNotFoundError(path)

    spans = [1, 36]
    seed = 20260802
    rank = 32
    scale = 0.75
    dropout = 0.0
    sequence_length = 64
    standard_deviation = 0.02
    base_contract = None
    adapter_contracts = {}
    args = None
    for span in spans:
        model, args, selected = depth_common.load_official_stack(36, mx.gpu)
        current_base = _base_contract(model, selected)
        if base_contract is None:
            base_contract = current_base
        elif current_base != base_contract:
            raise RuntimeError("Frozen 36-layer base changed between LoRA-span conditions")
        adapter_contracts[str(span)] = initialize_adapter_span(
            model, span, seed, rank, scale, dropout
        )
        del model
        mx.clear_cache()
    if (
        adapter_contracts["1"]["first_layer_sha256"]
        != adapter_contracts["36"]["first_layer_sha256"]
    ):
        raise RuntimeError("First-layer LoRA initialization differs across span conditions")

    input_array, input_hash = canonical_input(
        sequence_length,
        args.hidden_size,
        seed,
        standard_deviation,
    )
    preregistration = {
        "schema": "uruha_rightbrain_qwen3_lora_span_repro_preregistration_v1",
        "experiment_id": EXPERIMENT_ID,
        "research_question": (
            "Does expanding trainable LoRA coverage from the same first Qwen3 layer "
            "to all 36 layers reproduce gradient drift while the 36-layer graph is fixed?"
        ),
        "causal_variable": {
            "name": "lora_enabled_transformer_layer_count",
            "levels": spans,
            "only_intended_change": True,
        },
        "evidence_parent": {
            "path": "reports/rightbrain_qwen3_depth_repro_v1_result.json",
            "sha256": sha256_file(ROOT / "reports/rightbrain_qwen3_depth_repro_v1_result.json"),
            "observed_outcome": "depth_alone_does_not_reproduce_full_model_drift",
            "causal_audit_reason": (
                "The failed full-model probe used LoRA on all 36 layers, whereas the "
                "depth probe held trainable LoRA to layer zero only."
            ),
        },
        "local_environment": gradient_common._environment(),
        "official_model_contract": {
            "base_model": "Qwen/Qwen3-4B-Instruct-2507",
            "revision": "cdbee75f17c01a7cc42f958dc650907174af0554",
            "snapshot_root": str(depth_common.SNAPSHOT_ROOT),
            "config_sha256": sha256_file(depth_common.CONFIG_PATH),
            "weight_shard_sha256": {
                shard.name: sha256_file(shard) for shard in depth_common.WEIGHT_SHARDS
            },
            "architecture": "Qwen3ForCausalLM",
            "fixed_transformer_layers": 36,
            "hidden_size": args.hidden_size,
            "base_dtype": "mlx.core.bfloat16",
        },
        "base_contract": base_contract,
        "adapter_contract": {
            "rank": rank,
            "scale": scale,
            "dropout": dropout,
            "initialization_seed": seed,
            "first_layer_initialization_exact_across_conditions": True,
            "by_span": adapter_contracts,
        },
        "input_contract": {
            "source": "synthetic_numpy_pcg64_normal_no_persona_or_benchmark_content",
            "shape": list(input_array.shape),
            "host_dtype": str(input_array.dtype),
            "runtime_dtype": "mlx.core.bfloat16",
            "seed": seed,
            "standard_deviation": standard_deviation,
            "sha256": input_hash,
        },
        "exact_probe": {
            "device": "gpu_metal",
            "fixed_transformer_layer_count": 36,
            "isolated_repetitions_per_level": [1, 2, 3],
            "micro_steps_each": 1,
            "optimizer_steps": 0,
            "gradient_checkpointing": False,
            "loss": "mean_square_of_stack_output_in_float32",
            "random_seed": seed,
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
                "one_stable_all_unstable": "full_lora_span_reproduces_gradient_drift",
                "one_stable_all_stable": "lora_span_alone_does_not_reproduce_full_model_drift",
                "one_unstable": "one_layer_lora_control_failed",
            },
        },
        "boundaries": {
            "persona_training": False,
            "optimizer_update": False,
            "adapter_or_model_save": False,
            "text_generation": False,
            "production_runtime_change": False,
            "persona_similarity_claim": False,
            "lm_head_or_cross_entropy_included": False,
            "scope": "qwen3_lora_span_localization_only",
        },
        "result_paths": {
            "repeat_prefix": "reports/rightbrain_qwen3_lora_span_repro_v1_",
            "aggregate_json": "reports/rightbrain_qwen3_lora_span_repro_v1_result.json",
            "aggregate_markdown": "reports/rightbrain_qwen3_lora_span_repro_v1_result.md",
            "result_lock": "configs/rightbrain_qwen3_lora_span_repro_v1_result_lock.json",
        },
    }
    atomic_json(DEFAULT_PREREGISTRATION, preregistration)
    construction = {
        "schema": "uruha_rightbrain_qwen3_lora_span_repro_construction_v1",
        "experiment_id": EXPERIMENT_ID,
        "preregistration": file_binding(DEFAULT_PREREGISTRATION),
        "base_contract": base_contract,
        "adapter_contracts": adapter_contracts,
        "input_contract": {"shape": list(input_array.shape), "sha256": input_hash},
        "ready": True,
    }
    atomic_json(DEFAULT_CONSTRUCTION_JSON, construction)
    atomic_text(
        DEFAULT_CONSTRUCTION_MD,
        "\n".join(
            [
                "# Qwen3 LoRA 覆蓋層數定位實驗",
                "",
                "- 唯一變因：36 層圖中有 1 層或全部 36 層啟用 LoRA。",
                "- 第 1 層 LoRA 初始化在兩組完全相同。",
                f"- 1 層 LoRA 參數：`{adapter_contracts['1']['parameter_count']}`。",
                f"- 36 層 LoRA 參數：`{adapter_contracts['36']['parameter_count']}`。",
                "- 固定 Metal、輸入、MSE、零 checkpoint 與零 optimizer update。",
            ]
        )
        + "\n",
    )
    lock = {
        "schema": "uruha_rightbrain_qwen3_lora_span_repro_execution_lock_v1",
        "experiment_id": EXPERIMENT_ID,
        "bindings": [
            file_binding(DEFAULT_PREREGISTRATION),
            file_binding(DEFAULT_CONSTRUCTION_JSON),
            file_binding(DEFAULT_CONSTRUCTION_MD),
            file_binding(Path(__file__).resolve()),
            file_binding(RUNNER_PATH),
            file_binding(TEST_PATH),
            file_binding(ROOT / preregistration["evidence_parent"]["path"]),
            file_binding(depth_common.CONFIG_PATH, "external_local"),
            *[file_binding(shard, "external_local") for shard in depth_common.WEIGHT_SHARDS],
        ],
        "authorization": {
            "lora_enabled_layer_counts": spans,
            "fixed_transformer_layers": 36,
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
