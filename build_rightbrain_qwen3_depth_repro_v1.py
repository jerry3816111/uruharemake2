#!/usr/bin/env python3
"""Freeze a 1-layer versus 36-layer Qwen3 Metal backward experiment."""

from __future__ import annotations

import json
from pathlib import Path

import mlx.core as mx
import mlx.nn as nn
from mlx.utils import tree_flatten
from mlx_lm.models.qwen3 import ModelArgs, TransformerBlock

import build_rightbrain_qwen3_block_backend_repro_v1 as block_common
import run_rightbrain_mlx_gradient_repro_v1 as gradient_common


ROOT = Path(__file__).resolve().parent
EXPERIMENT_ID = "rightbrain_qwen3_depth_repro_v1"
DEFAULT_PREREGISTRATION = ROOT / "configs/rightbrain_qwen3_depth_repro_v1_preregistration.json"
DEFAULT_EXECUTION_LOCK = ROOT / "configs/rightbrain_qwen3_depth_repro_v1_execution_lock.json"
DEFAULT_CONSTRUCTION_JSON = ROOT / "reports/rightbrain_qwen3_depth_repro_v1_construction.json"
DEFAULT_CONSTRUCTION_MD = ROOT / "reports/rightbrain_qwen3_depth_repro_v1_construction.md"
SNAPSHOT_ROOT = block_common.SNAPSHOT_ROOT
CONFIG_PATH = block_common.CONFIG_PATH
WEIGHT_SHARDS = [
    SNAPSHOT_ROOT / f"model-{index:05d}-of-00003.safetensors"
    for index in (1, 2, 3)
]
RUNNER_PATH = ROOT / "run_rightbrain_qwen3_depth_repro_v1.py"
TEST_PATH = ROOT / "test_rightbrain_qwen3_depth_repro_v1.py"

load_json = block_common.load_json
sha256_file = block_common.sha256_file
atomic_json = block_common.atomic_json
atomic_text = block_common.atomic_text
file_binding = block_common.file_binding
canonical_input = block_common.canonical_input


class LayerStackModel(nn.Module):
    def __init__(self, args, layer_count):
        super().__init__()
        self.layers = [TransformerBlock(args) for _ in range(layer_count)]

    def __call__(self, hidden, mask):
        for layer in self.layers:
            hidden = layer(hidden, mask)
        return hidden


def load_official_stack(layer_count, device=mx.gpu):
    if layer_count not in (1, 36):
        raise ValueError("layer_count must be 1 or 36")
    mx.set_default_device(device)
    args = ModelArgs.from_dict(load_json(CONFIG_PATH))
    model = LayerStackModel(args, layer_count)
    selected = []
    prefixes = tuple(f"model.layers.{index}." for index in range(layer_count))
    for shard in WEIGHT_SHARDS:
        weights = mx.load(str(shard))
        selected.extend(
            (name[len("model.") :], value)
            for name, value in weights.items()
            if name.startswith(prefixes)
        )
    model.load_weights(selected, strict=True)
    mx.eval(model.parameters())
    return model, args, len(selected)


def _base_contract(model, layer_count, selected_weight_count):
    flat = tree_flatten(model.parameters())
    return {
        "layer_count": layer_count,
        "selected_weight_tensor_count": selected_weight_count,
        "parameter_count": sum(value.size for _, value in flat),
        "dtypes": sorted({str(value.dtype) for _, value in flat}),
        "sha256": gradient_common._parameter_sha256(model.parameters()),
    }


def _adapter_contract(model, layer_count, seed, rank, scale, dropout):
    actual = initialize_first_layer_adapter(model, seed, rank, scale, dropout)
    return {"layer_count": layer_count, **actual}


def initialize_first_layer_adapter(model, seed, rank, scale, dropout):
    model.freeze()
    first_layer = block_common.OneBlockModel(model.layers[0])
    block_common.initialize_adapter(first_layer, seed, rank, scale, dropout)
    flat = tree_flatten(model.trainable_parameters())
    return {
        "tensor_count": len(flat),
        "parameter_count": sum(value.size for _, value in flat),
        "dtypes": sorted({str(value.dtype) for _, value in flat}),
        "sha256": gradient_common._parameter_sha256(model.trainable_parameters()),
    }


def build():
    for path in [CONFIG_PATH, *WEIGHT_SHARDS, RUNNER_PATH, TEST_PATH]:
        if not path.is_file():
            raise FileNotFoundError(path)

    layer_counts = [1, 36]
    adapter_seed = 20260802
    input_seed = 20260802
    rank = 32
    scale = 0.75
    dropout = 0.0
    sequence_length = 64
    standard_deviation = 0.02

    base_contracts = {}
    adapter_contracts = {}
    args = None
    for layer_count in layer_counts:
        model, args, selected = load_official_stack(layer_count, mx.gpu)
        base_contracts[str(layer_count)] = _base_contract(model, layer_count, selected)
        adapter_contracts[str(layer_count)] = _adapter_contract(
            model, layer_count, adapter_seed, rank, scale, dropout
        )
        del model
        mx.clear_cache()

    input_array, input_hash = canonical_input(
        sequence_length,
        args.hidden_size,
        input_seed,
        standard_deviation,
    )
    preregistration = {
        "schema": "uruha_rightbrain_qwen3_depth_repro_preregistration_v1",
        "experiment_id": EXPERIMENT_ID,
        "research_question": (
            "Does increasing the same official Qwen3 Metal graph from one to all 36 "
            "transformer layers reproduce the previously observed gradient drift?"
        ),
        "causal_variable": {
            "name": "active_transformer_layer_count",
            "levels": layer_counts,
            "only_intended_change": True,
        },
        "evidence_parent": {
            "path": "reports/rightbrain_qwen3_block_backend_repro_v1_result.json",
            "sha256": sha256_file(
                ROOT / "reports/rightbrain_qwen3_block_backend_repro_v1_result.json"
            ),
            "authorized_next_step": "preregister_layer_count_scaling_localization",
        },
        "local_environment": gradient_common._environment(),
        "official_model_contract": {
            "base_model": "Qwen/Qwen3-4B-Instruct-2507",
            "revision": "cdbee75f17c01a7cc42f958dc650907174af0554",
            "snapshot_root": str(SNAPSHOT_ROOT),
            "config_sha256": sha256_file(CONFIG_PATH),
            "weight_shard_sha256": {
                shard.name: sha256_file(shard) for shard in WEIGHT_SHARDS
            },
            "architecture": "Qwen3ForCausalLM",
            "total_transformer_layers": args.num_hidden_layers,
            "hidden_size": args.hidden_size,
            "base_dtype": "mlx.core.bfloat16",
        },
        "base_contracts": base_contracts,
        "adapter_contract": {
            "placement": "same_first_transformer_layer_only",
            "rank": rank,
            "scale": scale,
            "dropout": dropout,
            "initialization_seed": adapter_seed,
            "by_layer_count": adapter_contracts,
        },
        "input_contract": {
            "source": "synthetic_numpy_pcg64_normal_no_persona_or_benchmark_content",
            "shape": list(input_array.shape),
            "host_dtype": str(input_array.dtype),
            "runtime_dtype": "mlx.core.bfloat16",
            "seed": input_seed,
            "standard_deviation": standard_deviation,
            "sha256": input_hash,
        },
        "exact_probe": {
            "device": "gpu_metal",
            "isolated_repetitions_per_level": [1, 2, 3],
            "micro_steps_each": 1,
            "optimizer_steps": 0,
            "gradient_checkpointing": False,
            "loss": "mean_square_of_stack_output_in_float32",
            "trainable_adapter_layer_index": 0,
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
                "one_stable_thirty_six_unstable": "depth_reproduces_gradient_drift",
                "one_stable_thirty_six_stable": "depth_alone_does_not_reproduce_full_model_drift",
                "one_unstable": "one_layer_control_failed_to_reproduce_parent",
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
            "scope": "qwen3_transformer_depth_localization_only",
        },
        "result_paths": {
            "repeat_prefix": "reports/rightbrain_qwen3_depth_repro_v1_",
            "aggregate_json": "reports/rightbrain_qwen3_depth_repro_v1_result.json",
            "aggregate_markdown": "reports/rightbrain_qwen3_depth_repro_v1_result.md",
            "result_lock": "configs/rightbrain_qwen3_depth_repro_v1_result_lock.json",
        },
    }
    atomic_json(DEFAULT_PREREGISTRATION, preregistration)
    construction = {
        "schema": "uruha_rightbrain_qwen3_depth_repro_construction_v1",
        "experiment_id": EXPERIMENT_ID,
        "preregistration": file_binding(DEFAULT_PREREGISTRATION),
        "base_contracts": base_contracts,
        "adapter_contracts": adapter_contracts,
        "input_contract": {"shape": list(input_array.shape), "sha256": input_hash},
        "ready": True,
    }
    atomic_json(DEFAULT_CONSTRUCTION_JSON, construction)
    atomic_text(
        DEFAULT_CONSTRUCTION_MD,
        "\n".join(
            [
                "# Qwen3 1 層 / 36 層深度定位實驗",
                "",
                "- 唯一變因：啟用 1 層或完整 36 層 Transformer。",
                "- 固定 Metal、官方權重、LoRA、輸入、loss 與零更新。",
                f"- 1 層參數：`{base_contracts['1']['parameter_count']}`。",
                f"- 36 層參數：`{base_contracts['36']['parameter_count']}`。",
                "- 不含 LM head 或 cross entropy，不授權人格訓練。",
            ]
        )
        + "\n",
    )
    lock = {
        "schema": "uruha_rightbrain_qwen3_depth_repro_execution_lock_v1",
        "experiment_id": EXPERIMENT_ID,
        "bindings": [
            file_binding(DEFAULT_PREREGISTRATION),
            file_binding(DEFAULT_CONSTRUCTION_JSON),
            file_binding(DEFAULT_CONSTRUCTION_MD),
            file_binding(Path(__file__).resolve()),
            file_binding(RUNNER_PATH),
            file_binding(TEST_PATH),
            file_binding(ROOT / preregistration["evidence_parent"]["path"]),
            file_binding(CONFIG_PATH, "external_local"),
            *[file_binding(shard, "external_local") for shard in WEIGHT_SHARDS],
        ],
        "authorization": {
            "layer_counts": layer_counts,
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
