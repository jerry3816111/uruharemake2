#!/usr/bin/env python3
"""Freeze a CPU-versus-Metal Qwen3 block backward localization experiment."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path

import mlx.core as mx
import mlx.nn as nn
import numpy as np
from mlx.utils import tree_flatten
from mlx_lm.models.qwen3 import ModelArgs, TransformerBlock
from mlx_lm.tuner.utils import linear_to_lora_layers

import run_rightbrain_mlx_gradient_repro_v1 as common


ROOT = Path(__file__).resolve().parent
EXPERIMENT_ID = "rightbrain_qwen3_block_backend_repro_v1"
DEFAULT_PREREGISTRATION = (
    ROOT / "configs/rightbrain_qwen3_block_backend_repro_v1_preregistration.json"
)
DEFAULT_EXECUTION_LOCK = (
    ROOT / "configs/rightbrain_qwen3_block_backend_repro_v1_execution_lock.json"
)
DEFAULT_CONSTRUCTION_JSON = (
    ROOT / "reports/rightbrain_qwen3_block_backend_repro_v1_construction.json"
)
DEFAULT_CONSTRUCTION_MD = (
    ROOT / "reports/rightbrain_qwen3_block_backend_repro_v1_construction.md"
)
SNAPSHOT_ROOT = Path(
    "/Users/jerrychang/.cache/huggingface/hub/"
    "models--Qwen--Qwen3-4B-Instruct-2507/snapshots/"
    "cdbee75f17c01a7cc42f958dc650907174af0554"
)
CONFIG_PATH = SNAPSHOT_ROOT / "config.json"
WEIGHT_SHARD_PATH = SNAPSHOT_ROOT / "model-00001-of-00003.safetensors"
SOURCE_QWEN3_PATH = Path(
    "/Users/jerrychang/.cache/uruhabrain/mlx-lm-0.31.3-venv/lib/python3.12/"
    "site-packages/mlx_lm/models/qwen3.py"
)
SOURCE_LORA_PATH = Path(
    "/Users/jerrychang/.cache/uruhabrain/mlx-lm-0.31.3-venv/lib/python3.12/"
    "site-packages/mlx_lm/tuner/lora.py"
)
RUNNER_PATH = ROOT / "run_rightbrain_qwen3_block_backend_repro_v1.py"
TEST_PATH = ROOT / "test_rightbrain_qwen3_block_backend_repro_v1.py"


class OneBlockModel(nn.Module):
    def __init__(self, block):
        super().__init__()
        self.layers = [block]

    def __call__(self, hidden, mask):
        return self.layers[0](hidden, mask)


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_text(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def atomic_json(path, payload):
    atomic_text(path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def file_binding(path, scope="repository"):
    path = Path(path)
    display = str(path if scope == "external_local" else path.relative_to(ROOT))
    return {"path": display, "scope": scope, "sha256": sha256_file(path)}


def canonical_input(sequence_length, hidden_size, seed, standard_deviation):
    rng = np.random.default_rng(seed)
    array = rng.normal(
        loc=0.0,
        scale=standard_deviation,
        size=(1, sequence_length, hidden_size),
    ).astype(np.float32)
    return array, hashlib.sha256(array.tobytes()).hexdigest()


def _load_official_block(device):
    mx.set_default_device(device)
    args = ModelArgs.from_dict(load_json(CONFIG_PATH))
    block = TransformerBlock(args)
    weights = mx.load(str(WEIGHT_SHARD_PATH))
    prefix = "model.layers.0."
    selected = [
        (name[len(prefix) :], value)
        for name, value in weights.items()
        if name.startswith(prefix)
    ]
    block.load_weights(selected, strict=True)
    mx.eval(block.parameters())
    return OneBlockModel(block), args, len(selected)


def initialize_adapter(model, seed, rank, scale, dropout):
    model.freeze()
    mx.random.seed(seed)
    linear_to_lora_layers(
        model,
        1,
        {"rank": rank, "scale": scale, "dropout": dropout},
    )
    mx.eval(model.trainable_parameters())
    flat = tree_flatten(model.trainable_parameters())
    return {
        "tensor_count": len(flat),
        "parameter_count": sum(value.size for _, value in flat),
        "dtypes": sorted({str(value.dtype) for _, value in flat}),
        "sha256": common._parameter_sha256(model.trainable_parameters()),
    }


def build():
    for required in (
        CONFIG_PATH,
        WEIGHT_SHARD_PATH,
        SOURCE_QWEN3_PATH,
        SOURCE_LORA_PATH,
        RUNNER_PATH,
        TEST_PATH,
    ):
        if not required.is_file():
            raise FileNotFoundError(required)

    sequence_length = 64
    input_seed = 20260802
    adapter_seed = 20260802
    standard_deviation = 0.02
    rank = 32
    scale = 0.75
    dropout = 0.0

    model, args, selected_weight_count = _load_official_block(mx.cpu)
    base_flat = tree_flatten(model.parameters())
    base_contract = {
        "layer_index": 0,
        "selected_weight_tensor_count": selected_weight_count,
        "parameter_count": sum(value.size for _, value in base_flat),
        "dtypes": sorted({str(value.dtype) for _, value in base_flat}),
        "sha256": common._parameter_sha256(model.parameters()),
    }
    adapter_contract = initialize_adapter(
        model,
        adapter_seed,
        rank,
        scale,
        dropout,
    )
    input_array, input_sha256 = canonical_input(
        sequence_length,
        args.hidden_size,
        input_seed,
        standard_deviation,
    )

    preregistration = {
        "schema": "uruha_rightbrain_qwen3_block_backend_repro_preregistration_v1",
        "experiment_id": EXPERIMENT_ID,
        "research_question": (
            "Does the same official Qwen3 transformer block produce reproducible "
            "LoRA gradients on MLX CPU and Metal when every non-device input is fixed?"
        ),
        "causal_variable": {
            "name": "mlx_execution_device",
            "levels": ["cpu", "gpu_metal"],
            "only_intended_change": True,
        },
        "official_sources": [
            {
                "claim": "MLX exposes CPU and GPU devices plus set_default_device.",
                "url": "https://ml-explore.github.io/mlx/build/html/python/devices_and_streams.html",
            },
            {
                "claim": "MLX 0.32.0 includes a Metal layer-norm VJP hazard fix.",
                "url": "https://github.com/ml-explore/mlx/releases/tag/v0.32.0",
            },
            {
                "claim": "Qwen3-4B Instruct 2507 is the fixed official candidate model.",
                "url": "https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507",
            },
        ],
        "local_environment": common._environment(),
        "official_model_contract": {
            "base_model": "Qwen/Qwen3-4B-Instruct-2507",
            "revision": "cdbee75f17c01a7cc42f958dc650907174af0554",
            "snapshot_root": str(SNAPSHOT_ROOT),
            "config_sha256": sha256_file(CONFIG_PATH),
            "weight_shard_sha256": sha256_file(WEIGHT_SHARD_PATH),
            "architecture": "Qwen3ForCausalLM",
            "hidden_size": args.hidden_size,
            "intermediate_size": args.intermediate_size,
            "attention_heads": args.num_attention_heads,
            "key_value_heads": args.num_key_value_heads,
            "head_dim": args.head_dim,
            "base_dtype": "mlx.core.bfloat16",
        },
        "block_contract": base_contract,
        "adapter_contract": {
            "converted_layers": 1,
            "rank": rank,
            "scale": scale,
            "dropout": dropout,
            "initialization_seed": adapter_seed,
            **adapter_contract,
        },
        "input_contract": {
            "source": "synthetic_numpy_pcg64_normal_no_persona_or_benchmark_content",
            "shape": list(input_array.shape),
            "host_dtype": str(input_array.dtype),
            "runtime_dtype": "mlx.core.bfloat16",
            "seed": input_seed,
            "standard_deviation": standard_deviation,
            "sha256": input_sha256,
        },
        "exact_probe": {
            "devices": ["cpu", "gpu"],
            "isolated_repetitions_per_device": [1, 2, 3],
            "micro_steps_each": 1,
            "optimizer_steps": 0,
            "gradient_checkpointing": False,
            "loss": "mean_square_of_one_block_output_in_float32",
            "random_seed": 20260802,
            "memory_limit_bytes": 30 * 1024**3,
            "wired_limit_bytes": 24 * 1024**3,
        },
        "falsifiable_outcomes": {
            "within_device_reproducibility": {
                "gradient_norm_coefficient_of_variation_maximum": 0.005,
                "gradient_norm_max_to_min_ratio_maximum": 1.02,
                "minimum_pairwise_group_profile_cosine": 0.9999,
            },
            "classifications": {
                "cpu_stable_gpu_unstable": "metal_backend_implicated",
                "cpu_unstable_gpu_unstable": "framework_or_probe_still_unstable",
                "cpu_stable_gpu_stable": "reduced_block_does_not_reproduce_full_graph_drift",
                "cpu_unstable_gpu_stable": "cpu_reference_invalid_or_cpu_specific_failure",
            },
        },
        "boundaries": {
            "persona_training": False,
            "optimizer_update": False,
            "adapter_or_model_save": False,
            "text_generation": False,
            "production_runtime_change": False,
            "persona_similarity_claim": False,
            "full_model_backend_claim": False,
            "scope": "one_real_qwen3_block_backward_localization_only",
        },
        "result_paths": {
            "repeat_prefix": "reports/rightbrain_qwen3_block_backend_repro_v1_",
            "aggregate_json": "reports/rightbrain_qwen3_block_backend_repro_v1_result.json",
            "aggregate_markdown": "reports/rightbrain_qwen3_block_backend_repro_v1_result.md",
            "result_lock": "configs/rightbrain_qwen3_block_backend_repro_v1_result_lock.json",
        },
    }
    atomic_json(DEFAULT_PREREGISTRATION, preregistration)

    construction = {
        "schema": "uruha_rightbrain_qwen3_block_backend_repro_construction_v1",
        "experiment_id": EXPERIMENT_ID,
        "preregistration": file_binding(DEFAULT_PREREGISTRATION),
        "base_contract": base_contract,
        "adapter_contract": adapter_contract,
        "input_contract": {
            "shape": list(input_array.shape),
            "sha256": input_sha256,
        },
        "device_preflight": {
            "default_before_build": str(mx.default_device()),
            "cpu": mx.device_info(mx.cpu),
            "gpu": mx.device_info(mx.gpu),
        },
        "ready": True,
    }
    atomic_json(DEFAULT_CONSTRUCTION_JSON, construction)
    atomic_text(
        DEFAULT_CONSTRUCTION_MD,
        "\n".join(
            [
                "# Qwen3 單層 CPU / Metal 後向定位實驗",
                "",
                "- 唯一變因：MLX 執行裝置（CPU 或 Metal GPU）。",
                f"- 官方 Qwen3 第 1 層參數：`{base_contract['parameter_count']}`。",
                f"- LoRA 可訓練參數：`{adapter_contract['parameter_count']}`。",
                f"- 固定輸入：`{list(input_array.shape)}`。",
                "- 每個裝置獨立執行三次，零 optimizer update。",
                "- 本實驗只定位後端，不授權人格訓練或 production 修改。",
            ]
        )
        + "\n",
    )

    lock = {
        "schema": "uruha_rightbrain_qwen3_block_backend_repro_execution_lock_v1",
        "experiment_id": EXPERIMENT_ID,
        "bindings": [
            file_binding(DEFAULT_PREREGISTRATION),
            file_binding(DEFAULT_CONSTRUCTION_JSON),
            file_binding(DEFAULT_CONSTRUCTION_MD),
            file_binding(Path(__file__).resolve()),
            file_binding(RUNNER_PATH),
            file_binding(TEST_PATH),
            file_binding(CONFIG_PATH, "external_local"),
            file_binding(WEIGHT_SHARD_PATH, "external_local"),
            file_binding(SOURCE_QWEN3_PATH, "external_local"),
            file_binding(SOURCE_LORA_PATH, "external_local"),
        ],
        "authorization": {
            "devices": ["cpu", "gpu"],
            "exact_zero_update_repetitions_each": [1, 2, 3],
            "micro_steps_each": 1,
            "optimizer_steps": 0,
            "gradient_checkpointing": False,
            "one_official_qwen3_block": True,
            "adapter_or_model_save": False,
            "text_generation": False,
            "production_runtime_change": False,
        },
    }
    atomic_json(DEFAULT_EXECUTION_LOCK, lock)
    return construction


def main():
    result = build()
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
