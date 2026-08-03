#!/usr/bin/env python3
"""Freeze a prompt-only provider-signal position experiment."""

from __future__ import annotations

import copy
import hashlib
import json
from collections import Counter
from pathlib import Path

import build_rightbrain_qwen3_4b_trainability_v1 as model_parent
import build_rightbrain_qwen3_active_head_multibatch_v1 as data_parent
import build_rightbrain_qwen3_fresh_generation_v1 as fresh_parent
import build_rightbrain_qwen3_provider_pair_cpo_v1 as cpo_parent


ROOT = Path(__file__).resolve().parent
EXPERIMENT_ID = "rightbrain_qwen3_provider_signal_position_v1"
CONDITIONS = ("nested_control", "top_level_signal")
REPEATS = (1, 2, 3)
CONDITION_ORDERS = {
    1: CONDITIONS,
    2: tuple(reversed(CONDITIONS)),
    3: CONDITIONS,
}
PROBE_ROW_INDICES = (8, 10, 28, 30, 32, 34, 52, 54)
REFERENCE_ALT_ROW_INDICES = (9, 11, 29, 31, 33, 35, 53, 55)
MAX_GENERATION_TOKENS = 80
DEFAULT_PREREGISTRATION = (
    ROOT / "configs/rightbrain_qwen3_provider_signal_position_v1_preregistration.json"
)
DEFAULT_EXECUTION_LOCK = (
    ROOT / "configs/rightbrain_qwen3_provider_signal_position_v1_execution_lock.json"
)
DEFAULT_CONSTRUCTION_JSON = (
    ROOT / "reports/rightbrain_qwen3_provider_signal_position_v1_construction.json"
)
DEFAULT_CONSTRUCTION_MD = (
    ROOT / "reports/rightbrain_qwen3_provider_signal_position_v1_construction.md"
)
RUNNER_PATH = ROOT / "run_rightbrain_qwen3_provider_signal_position_v1.py"
TEST_PATH = ROOT / "test_rightbrain_qwen3_provider_signal_position_v1.py"
VERIFIER_PATH = ROOT / "verify_rightbrain_qwen3_provider_signal_position_v1_result.py"
MODEL_PREREGISTRATION = model_parent.DEFAULT_PREREGISTRATION
DATASET_PATH = data_parent.DATASET_PATH
DATASET_RESULT_LOCK = data_parent.DATASET_RESULT_LOCK
PARENT_RESULT = ROOT / "reports/rightbrain_qwen3_provider_pair_cpo_v1_result.json"
PARENT_RESULT_LOCK = (
    ROOT / "configs/rightbrain_qwen3_provider_pair_cpo_v1_result_lock.json"
)
PARENT_DIAGNOSIS = ROOT / "reports/rightbrain_qwen3_provider_pair_cpo_v1_diagnosis.md"

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


def _compact_json(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def condition_messages(row, condition):
    if condition not in CONDITIONS:
        raise ValueError(f"Unknown condition: {condition}")
    if [message["role"] for message in row["messages"]] != [
        "system",
        "user",
        "assistant",
    ]:
        raise RuntimeError(f"Unexpected message contract: {row['id']}")
    payload = json.loads(row["messages"][1]["content"])
    if condition == "top_level_signal":
        persona = payload["context"].pop("persona_expression_brief")
        payload = {"persona_expression_brief": persona, **payload}
    return [
        copy.deepcopy(row["messages"][0]),
        {"role": "user", "content": _compact_json(payload)},
    ]


def _payload_without_persona(payload):
    payload = copy.deepcopy(payload)
    if "persona_expression_brief" in payload:
        persona = payload.pop("persona_expression_brief")
    else:
        persona = payload["context"].pop("persona_expression_brief")
    return payload, persona


def _opposite_provider_map(rows, indices):
    return cpo_parent.provider_pair_map(rows, indices)


def _references_by_row(rows):
    alt_by_primary = dict(
        zip(PROBE_ROW_INDICES, REFERENCE_ALT_ROW_INDICES, strict=True)
    )
    opposite = _opposite_provider_map(rows, PROBE_ROW_INDICES)
    references = {}
    for row_index in PROBE_ROW_INDICES:
        opposite_index = opposite[row_index]
        references[rows[row_index]["id"]] = {
            "own": [
                rows[row_index]["messages"][-1]["content"],
                rows[alt_by_primary[row_index]]["messages"][-1]["content"],
            ],
            "opposite": [
                rows[opposite_index]["messages"][-1]["content"],
                rows[alt_by_primary[opposite_index]]["messages"][-1]["content"],
            ],
        }
    return references


def prompt_contract(rows):
    cases = []
    for row_index in PROBE_ROW_INDICES:
        row = rows[row_index]
        nested_messages = condition_messages(row, "nested_control")
        top_messages = condition_messages(row, "top_level_signal")
        nested_payload = json.loads(nested_messages[1]["content"])
        top_payload = json.loads(top_messages[1]["content"])
        nested_rest, nested_persona = _payload_without_persona(nested_payload)
        top_rest, top_persona = _payload_without_persona(top_payload)
        if nested_rest != top_rest or nested_persona != top_persona:
            raise RuntimeError(f"Position intervention changed content: {row['id']}")
        if "persona_expression_brief" not in nested_payload["context"]:
            raise RuntimeError(f"Nested signal missing: {row['id']}")
        if "persona_expression_brief" not in top_payload:
            raise RuntimeError(f"Top-level signal missing: {row['id']}")
        if "persona_expression_brief" in top_payload["context"]:
            raise RuntimeError(f"Top-level signal remained nested: {row['id']}")
        cases.append(
            {
                "row_index": row_index,
                "row_id": row["id"],
                "source_id": row["source_id"],
                "provider_id": row["provider_id"],
                "memory_mode": row["memory_mode"],
                "variant_index": row["variant_index"],
                "scoring_payload": json.loads(row["messages"][1]["content"]),
                "nested_control_messages": nested_messages,
                "top_level_signal_messages": top_messages,
            }
        )
    return {
        "cases": cases,
        "case_count": len(cases),
        "nested_prompt_sha256": canonical_json_sha256(
            [case["nested_control_messages"] for case in cases]
        ),
        "top_level_prompt_sha256": canonical_json_sha256(
            [case["top_level_signal_messages"] for case in cases]
        ),
        "all_content_outside_signal_equal": True,
        "all_signal_objects_equal_between_conditions": True,
        "assistant_references_in_prompt": False,
    }


def build():
    required = (
        MODEL_PREREGISTRATION,
        DATASET_PATH,
        DATASET_RESULT_LOCK,
        PARENT_RESULT,
        PARENT_RESULT_LOCK,
        PARENT_DIAGNOSIS,
        RUNNER_PATH,
        TEST_PATH,
        VERIFIER_PATH,
    )
    for path in required:
        if not path.is_file():
            raise FileNotFoundError(path)

    base = load_json(MODEL_PREREGISTRATION)
    parent_result = load_json(PARENT_RESULT)
    parent_lock = load_json(PARENT_RESULT_LOCK)
    parent_decision = parent_result["decision"]
    if parent_decision["outcome"] != "provider_pair_cpo_holdout_margin_not_improved":
        raise RuntimeError("Unexpected CPO parent outcome")
    if parent_decision["authorized_next_step"] != (
        "diagnose_provider_pair_cpo_objective_failure"
    ):
        raise RuntimeError("CPO parent does not authorize interface diagnosis")
    if any(parent_lock["authorization"].values()):
        raise RuntimeError("CPO parent unexpectedly grants persistent authorization")

    rows = load_json(DATASET_PATH)
    if len(rows) != 80:
        raise RuntimeError("Unexpected curriculum row count")
    selected = PROBE_ROW_INDICES + REFERENCE_ALT_ROW_INDICES
    prior_indices = tuple(
        dict.fromkeys(
            data_parent.TRAIN_ROW_INDICES
            + data_parent.HOLDOUT_ROW_INDICES
            + fresh_parent.FRESH_GENERATION_ROW_INDICES
            + fresh_parent.FRESH_REFERENCE_ALT_ROW_INDICES
            + cpo_parent.HOLDOUT_ROW_INDICES
        )
    )
    selected_sources = {rows[index]["source_id"] for index in selected}
    prior_sources = {rows[index]["source_id"] for index in prior_indices}
    if selected_sources & prior_sources:
        raise RuntimeError("Position probe source overlaps prior experiments")
    prior_answers = {
        rows[index]["messages"][-1]["content"].strip() for index in prior_indices
    }
    selected_answers = {
        rows[index]["messages"][-1]["content"].strip() for index in selected
    }
    if selected_answers & prior_answers:
        raise RuntimeError("Position probe references overlap prior answers")
    if not all(
        rows[index]["provenance"]["synthetic"] is True
        and rows[index]["provenance"]["source_independent"] is True
        and rows[index]["provenance"]["contains_target_utterance"] is False
        and rows[index]["provenance"]["contains_benchmark_item"] is False
        for index in selected
    ):
        raise RuntimeError("Position probe violates provenance boundary")
    providers = Counter(rows[index]["provider_id"] for index in PROBE_ROW_INDICES)
    memories = Counter(rows[index]["memory_mode"] for index in PROBE_ROW_INDICES)
    if providers != {
        "structured_target_public_persona": 4,
        "structured_neutral_dialogue": 4,
    }:
        raise RuntimeError("Position probe provider split is not balanced")
    if set(memories.values()) != {2}:
        raise RuntimeError("Position probe memory split is not balanced")
    if len(selected_sources) != 4:
        raise RuntimeError("Position probe does not contain four sources")
    prompt = prompt_contract(rows)
    references = _references_by_row(rows)
    reference_hash = canonical_json_sha256(
        [references[row_id] for row_id in sorted(references)]
    )

    prereg = {
        "schema": "uruha_rightbrain_qwen3_provider_signal_position_preregistration_v1",
        "experiment_id": EXPERIMENT_ID,
        "research_question": (
            "Does relocating the exact persona_expression_brief object from a nested "
            "context field to the first top-level JSON field improve provider-conditioned "
            "generation on four never-used sources without changing model weights?"
        ),
        "conditions": {
            "nested_control": "persona_expression_brief remains under context",
            "top_level_signal": "the identical object is moved to the first top-level field",
        },
        "causal_scope": {
            "only_changed_variable": "persona_expression_brief_json_path",
            "control_value": "context.persona_expression_brief",
            "candidate_value": "persona_expression_brief",
            "unchanged": [
                "signal_object_and_values",
                "system_message",
                "all_non_signal_payload_fields",
                "base_model_snapshot",
                "greedy_decoding",
                "probe_rows_and_order",
                "references_and_scoring",
                "device_and_environment",
            ],
        },
        "evidence_parent": {
            "result": file_binding(PARENT_RESULT),
            "result_lock": file_binding(PARENT_RESULT_LOCK),
            "diagnosis": file_binding(PARENT_DIAGNOSIS),
            "outcome": parent_decision["outcome"],
            "failed_gate": "candidate_train_final_margin_exceeds_control",
        },
        "local_environment": base["local_environment"],
        "local_model_contract": base["local_model_contract"],
        "external_model_bindings": base["external_model_bindings"],
        "dataset_contract": {
            "path": str(DATASET_PATH.relative_to(ROOT)),
            "sha256": sha256_file(DATASET_PATH),
            "row_count": len(rows),
            "synthetic_source_independent": True,
            "contains_target_utterances": False,
            "contains_benchmark_items_or_answers": False,
        },
        "source_split_contract": {
            "probe_row_indices": list(PROBE_ROW_INDICES),
            "reference_alt_row_indices": list(REFERENCE_ALT_ROW_INDICES),
            "probe_source_ids": sorted(selected_sources),
            "prior_experiment_source_overlap": 0,
            "prior_experiment_exact_answer_overlap": 0,
            "provider_counts": dict(sorted(providers.items())),
            "memory_mode_counts": dict(sorted(memories.items())),
        },
        "prompt_contract": prompt,
        "reference_contract": {
            "sha256": reference_hash,
            "loaded_only_after_all_generation_conditions": True,
            "passed_to_model": False,
        },
        "generation_contract": {
            "decode_mode": "greedy",
            "temperature": 0.0,
            "top_p": 0.0,
            "maximum_new_tokens": MAX_GENERATION_TOKENS,
            "repetitions": list(REPEATS),
            "condition_orders": {
                str(key): list(value) for key, value in CONDITION_ORDERS.items()
            },
        },
        "exact_probe": {
            "conditions": list(CONDITIONS),
            "repetitions": list(REPEATS),
            "generation_calls_each_repeat": len(CONDITIONS) * len(PROBE_ROW_INDICES),
            "model_loads_each_repeat": 1,
            "optimizer_updates": 0,
            "adapter_initialized": False,
            "memory_limit_bytes": base["exact_probe"]["memory_limit_bytes"],
            "wired_limit_bytes": base["exact_probe"]["wired_limit_bytes"],
            "random_seed": 20260803,
        },
        "falsifiable_hypothesis": {
            "confirm_if_all": {
                "all_repetitions_successful": True,
                "each_condition_reproducible": True,
                "candidate_changed_output_count_minimum": 2,
                "provider_pair_difference_rate_gain_minimum": 0.25,
                "provider_alignment_margin_gain_minimum": 0.01,
                "candidate_correct_provider_alignment_rate_not_below_control": True,
                "candidate_joint_contract_rate_regression_maximum": 0.125,
                "candidate_joint_contract_regression_count_maximum": 1,
                "exact_reference_copy_count_maximum": 0,
                "peak_memory_bytes_maximum": base["exact_probe"]["memory_limit_bytes"],
            },
            "success_outcome": "provider_signal_position_effect_confirmed",
            "failure_outcomes": [
                "provider_signal_position_execution_failed",
                "provider_signal_position_not_reproducible",
                "provider_signal_position_contract_regressed",
                "provider_signal_position_differentiation_not_improved",
            ],
        },
        "success_authorization": {
            "maximum_positive_next_step": (
                "preregister_top_level_provider_signal_full_pipeline_holdout"
            ),
            "persistent_training": False,
            "persona_training": False,
            "adapter_save": False,
            "runtime_activation": False,
            "persona_similarity_claim": False,
        },
        "boundaries": {
            "text_generation": True,
            "training": False,
            "optimizer_updates": 0,
            "adapter_or_model_save": False,
            "target_person_utterance_training": False,
            "benchmark_training": False,
            "production_runtime_change": False,
            "scope": "qwen3_prompt_only_provider_signal_position_probe",
        },
        "interpretation_limits": [
            "A pass would show only that this local model reads the same provider signal more effectively at a top-level JSON path.",
            "It would not prove target-person fidelity, persistent learning, full-pipeline benefit, or production readiness.",
            "The references are synthetic acceptable outputs used after generation only.",
        ],
        "result_paths": {
            "repeat_prefix": "reports/rightbrain_qwen3_provider_signal_position_v1_repeat_",
            "aggregate_json": "reports/rightbrain_qwen3_provider_signal_position_v1_result.json",
            "aggregate_markdown": "reports/rightbrain_qwen3_provider_signal_position_v1_result.md",
            "result_lock": "configs/rightbrain_qwen3_provider_signal_position_v1_result_lock.json",
        },
    }
    atomic_json(DEFAULT_PREREGISTRATION, prereg)
    construction = {
        "schema": "uruha_rightbrain_qwen3_provider_signal_position_construction_v1",
        "experiment_id": EXPERIMENT_ID,
        "preregistration": file_binding(DEFAULT_PREREGISTRATION),
        "causal_scope": prereg["causal_scope"],
        "source_split_contract": prereg["source_split_contract"],
        "prompt_hashes": {
            "nested_control": prompt["nested_prompt_sha256"],
            "top_level_signal": prompt["top_level_prompt_sha256"],
        },
        "ready": True,
    }
    atomic_json(DEFAULT_CONSTRUCTION_JSON, construction)
    atomic_text(
        DEFAULT_CONSTRUCTION_MD,
        "\n".join(
            [
                "# Qwen3 provider signal position probe",
                "",
                "- Only variable: the JSON path of the exact same persona expression object.",
                "- Eight prompts from four sources unused by all prior Qwen3 experiments.",
                "- Base Qwen3-4B, greedy decoding, three isolated repeats, no training.",
                "- References are loaded after generation and are never model inputs.",
            ]
        )
        + "\n",
    )
    external_bindings = [
        {**binding, "scope": "external_local"}
        for binding in prereg["external_model_bindings"]
    ]
    lock = {
        "schema": "uruha_rightbrain_qwen3_provider_signal_position_execution_lock_v1",
        "experiment_id": EXPERIMENT_ID,
        "bindings": [
            file_binding(DEFAULT_PREREGISTRATION),
            file_binding(DEFAULT_CONSTRUCTION_JSON),
            file_binding(DEFAULT_CONSTRUCTION_MD),
            file_binding(Path(__file__).resolve()),
            file_binding(RUNNER_PATH),
            file_binding(TEST_PATH),
            file_binding(VERIFIER_PATH),
            file_binding(MODEL_PREREGISTRATION),
            file_binding(DATASET_PATH),
            file_binding(DATASET_RESULT_LOCK),
            file_binding(PARENT_RESULT),
            file_binding(PARENT_RESULT_LOCK),
            file_binding(PARENT_DIAGNOSIS),
            *external_bindings,
        ],
        "authorization": {
            "conditions": list(CONDITIONS),
            "repetitions": list(REPEATS),
            "condition_orders": prereg["generation_contract"]["condition_orders"],
            "probe_row_indices": list(PROBE_ROW_INDICES),
            "reference_alt_row_indices": list(REFERENCE_ALT_ROW_INDICES),
            "prior_source_overlap_exact": 0,
            "prior_answer_overlap_exact": 0,
            "base_model": prereg["local_model_contract"]["base_model"],
            "device": "gpu",
            "generation_contract": prereg["generation_contract"],
            "optimizer_updates": 0,
            "adapter_initialized": False,
            "adapter_or_model_save": False,
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
