#!/usr/bin/env python3
"""Freeze a disjoint official PersonaEval pilot for local judge selection."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

import build_personaeval_qwen3_official_pilot_v1 as base


ROOT = Path(__file__).resolve().parent
EXPERIMENT_ID = "personaeval_local_judge_model_selection_v1"
SELECTION_SEED = EXPERIMENT_ID
SAMPLE_COUNT_PER_TRACK = 10
REPEAT_COUNT_PER_TRACK = 3
TRACKS = base.TRACKS
SYSTEM_MESSAGE = base.SYSTEM_MESSAGE

MODEL_CONTRACTS = {
    "qwen3_4b": {
        "name": "Qwen/Qwen3-4B-Instruct-2507",
        "snapshot": base.MODEL_SNAPSHOT,
        "revision": base.MODEL_SNAPSHOT.name,
    },
    "qwen25_7b": {
        "name": "Qwen/Qwen2.5-7B-Instruct",
        "snapshot": Path(
            "/Users/jerrychang/.cache/huggingface/hub/"
            "models--Qwen--Qwen2.5-7B-Instruct/snapshots/"
            "a09a35458c702b33eeacc393d103063234e8bc28"
        ),
        "revision": "a09a35458c702b33eeacc393d103063234e8bc28",
    },
}
MODEL_ORDER = ("qwen3_4b", "qwen25_7b")
SMOKE_EXCLUSIONS = {"Drama": {0, 1, 2, 3}, "Expertise": set(), "Literary": set()}

PROMPTS_PATH = ROOT / "datasets/personaeval_local_judge_model_selection_v1_prompts.json"
LABELS_PATH = ROOT / "datasets/personaeval_local_judge_model_selection_v1_labels.json"
PREREGISTRATION_PATH = (
    ROOT / "configs/personaeval_local_judge_model_selection_v1_preregistration.json"
)
HARNESS_LOCK_PATH = (
    ROOT / "configs/personaeval_local_judge_model_selection_v1_harness_lock.json"
)
CONSTRUCTION_JSON_PATH = (
    ROOT / "reports/personaeval_local_judge_model_selection_v1_construction.json"
)
CONSTRUCTION_MD_PATH = (
    ROOT / "reports/personaeval_local_judge_model_selection_v1_construction.md"
)
RAW_RESULT_PATH = ROOT / "reports/personaeval_local_judge_model_selection_v1_raw.json"
RESULT_PATH = ROOT / "reports/personaeval_local_judge_model_selection_v1_result.json"
RESULT_MD_PATH = ROOT / "reports/personaeval_local_judge_model_selection_v1_result.md"
VERIFICATION_JSON_PATH = (
    ROOT / "reports/personaeval_local_judge_model_selection_v1_verification.json"
)
VERIFICATION_MD_PATH = (
    ROOT / "reports/personaeval_local_judge_model_selection_v1_verification.md"
)

BUILDER_PATH = Path(__file__).resolve()
RUNNER_PATH = ROOT / "run_personaeval_local_judge_model_selection_v1.py"
TEST_PATH = ROOT / "test_personaeval_local_judge_model_selection_v1.py"
VERIFIER_PATH = ROOT / "verify_personaeval_local_judge_model_selection_v1_result.py"
BASE_BUILDER_PATH = ROOT / "build_personaeval_qwen3_official_pilot_v1.py"
BASE_RUNNER_PATH = ROOT / "run_personaeval_qwen3_official_pilot_v1.py"


def _prior_indices():
    payload = base.load_json(base.PROMPTS_PATH)
    result = {track: set() for track in TRACKS}
    for row in payload["rows"]:
        result[row["track"]].add(row["source_row_index"])
    return result


def excluded_indices():
    previous = _prior_indices()
    return {
        track: previous[track] | set(SMOKE_EXCLUSIONS[track]) for track in TRACKS
    }


def selected_indices(track, sample_count=SAMPLE_COUNT_PER_TRACK):
    """Select unseen indices before reading content or labels."""
    excluded = excluded_indices()[track]
    eligible = [
        index for index in range(TRACKS[track]["row_count"]) if index not in excluded
    ]
    selected = []
    for stratum in range(sample_count):
        start = (stratum * len(eligible)) // sample_count
        end = ((stratum + 1) * len(eligible)) // sample_count
        width = end - start
        if width <= 0:
            raise ValueError("sample count exceeds eligible rows")
        token = f"{SELECTION_SEED}|{track}|{stratum}".encode("utf-8")
        offset = int.from_bytes(hashlib.sha256(token).digest(), "big") % width
        selected.append(eligible[start + offset])
    if len(selected) != len(set(selected)) or set(selected) & excluded:
        raise RuntimeError(f"invalid disjoint selection for {track}")
    return selected


def repeat_audit_row_ids(prompt_rows):
    by_track = {track: [] for track in TRACKS}
    for row in prompt_rows:
        by_track[row["track"]].append(row)
    result = []
    for track in TRACKS:
        ranked = sorted(
            by_track[track],
            key=lambda row: hashlib.sha256(
                f"{EXPERIMENT_ID}|repeat|{row['row_id']}".encode("utf-8")
            ).hexdigest(),
        )
        result.extend(row["row_id"] for row in ranked[:REPEAT_COUNT_PER_TRACK])
    return result


def _read_source_rows(track, indices):
    path = base.ensure_source_file(f"{track}.csv")
    wanted = set(indices)
    rows = {}
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row_index, row in enumerate(csv.DictReader(handle)):
            if row_index in wanted:
                rows[row_index] = row
            if len(rows) == len(wanted):
                break
    if set(rows) != wanted:
        raise RuntimeError(f"missing official rows for {track}")
    return rows


def build_dataset(refresh=False):
    if PROMPTS_PATH.exists() and LABELS_PATH.exists() and not refresh:
        return base.load_json(PROMPTS_PATH), base.load_json(LABELS_PATH)
    prompt_rows = []
    label_rows = []
    for track in TRACKS:
        indices = selected_indices(track)
        source_rows = _read_source_rows(track, indices)
        for row_index in indices:
            prompt, label = base._validate_and_split_row(
                track, row_index, source_rows[row_index]
            )
            prompt_rows.append(prompt)
            label_rows.append(label)
    prompts = {
        "schema": "personaeval_local_judge_model_selection_prompts_v1",
        "experiment_id": EXPERIMENT_ID,
        "source": {
            "dataset": base.HF_DATASET,
            "commit": base.HF_DATASET_COMMIT,
            "license": base.OFFICIAL_DATASET_LICENSE,
        },
        "selection": {
            "method": "one_hash_selected_disjoint_row_per_equal_width_eligible_stratum",
            "seed": SELECTION_SEED,
            "sample_count_per_track": SAMPLE_COUNT_PER_TRACK,
            "excluded_previous_primary_rows": True,
            "excluded_transport_smoke_rows": True,
            "content_and_labels_unread_before_index_selection": True,
        },
        "rows": prompt_rows,
    }
    labels = {
        "schema": "personaeval_local_judge_model_selection_labels_v1",
        "experiment_id": EXPERIMENT_ID,
        "source": {"dataset": base.HF_DATASET, "commit": base.HF_DATASET_COMMIT},
        "rows": label_rows,
    }
    base.atomic_json(PROMPTS_PATH, prompts)
    base.atomic_json(LABELS_PATH, labels)
    return prompts, labels


def _model_file_names(model_id):
    if model_id == "qwen3_4b":
        return base.MODEL_FILES
    return (
        "config.json",
        "generation_config.json",
        "merges.txt",
        "model.safetensors.index.json",
        "model-00001-of-00004.safetensors",
        "model-00002-of-00004.safetensors",
        "model-00003-of-00004.safetensors",
        "model-00004-of-00004.safetensors",
        "tokenizer.json",
        "tokenizer_config.json",
        "vocab.json",
    )


def _model_contracts():
    contracts = {}
    for model_id in MODEL_ORDER:
        contract = MODEL_CONTRACTS[model_id]
        files = []
        for filename in _model_file_names(model_id):
            path = contract["snapshot"] / filename
            if not path.is_file():
                raise RuntimeError(f"missing local model file: {path}")
            files.append(base.external_binding(path, role=f"frozen_{model_id}_model"))
        contracts[model_id] = {
            "name": contract["name"],
            "snapshot_root": str(contract["snapshot"]),
            "snapshot_revision": contract["revision"],
            "files": files,
        }
    return contracts


def verify_upstream_models():
    verified = {}
    for model_id in MODEL_ORDER:
        contract = MODEL_CONTRACTS[model_id]
        payload = base._fetch_json(
            f"https://huggingface.co/api/models/{contract['name']}/revision/"
            f"{contract['revision']}"
        )
        if payload.get("sha") != contract["revision"]:
            raise RuntimeError(f"model revision drifted for {model_id}")
        verified[model_id] = payload["sha"]
    return verified


def _preregistration(prompts, labels, upstream, model_upstream):
    prompt_ids = [row["row_id"] for row in prompts["rows"]]
    label_ids = [row["row_id"] for row in labels["rows"]]
    if prompt_ids != label_ids or len(prompt_ids) != 30:
        raise RuntimeError("unexpected prompt/label contract")
    if any("gt" in row or "ground_truth" in row for row in prompts["rows"]):
        raise RuntimeError("prompt file contains labels")
    previous_ids = {
        (row["track"], row["source_row_index"])
        for row in base.load_json(base.PROMPTS_PATH)["rows"]
    }
    current_ids = {
        (row["track"], row["source_row_index"]) for row in prompts["rows"]
    }
    if previous_ids & current_ids:
        raise RuntimeError("new pilot overlaps previous official pilot")
    repeat_ids = repeat_audit_row_ids(prompts["rows"])
    return {
        "schema": "personaeval_local_judge_model_selection_preregistration_v1",
        "experiment_id": EXPERIMENT_ID,
        "research_question": (
            "With batch size fixed to one, which already-local model is a reliable "
            "PersonaEval role-identification judge on a disjoint official pilot?"
        ),
        "official_provenance": {
            "paper_url": base.OFFICIAL_PAPER_URL,
            "dataset_url": base.OFFICIAL_DATASET_URL,
            "dataset": base.HF_DATASET,
            "dataset_commit": base.HF_DATASET_COMMIT,
            "dataset_license": base.OFFICIAL_DATASET_LICENSE,
            "code_url": base.OFFICIAL_CODE_URL,
            "code_commit": base.OFFICIAL_REPOSITORY_COMMIT,
            "code_license": base.OFFICIAL_CODE_LICENSE,
            "upstream_verified": upstream,
            "model_revisions_verified": model_upstream,
        },
        "official_harness_compatibility": {
            "official_user_prompt_exact": True,
            "generic_json_only_system_transport_adapter": SYSTEM_MESSAGE,
            "direct_official_leaderboard_comparability": False,
            "strict_official_probability_sum_parser": True,
            "expertise_all_five_options_scored": True,
            "all_generation_or_parse_errors_count_wrong": True,
        },
        "pilot_design": {
            "tracks": TRACKS,
            "sample_count_per_track": SAMPLE_COUNT_PER_TRACK,
            "primary_row_count": len(prompt_ids),
            "selection_method": prompts["selection"],
            "primary_row_ids": prompt_ids,
            "repeat_audit_row_ids": repeat_ids,
            "repeat_audit_repetitions": 3,
            "generation_calls_per_model": len(prompt_ids) + 2 * len(repeat_ids),
            "total_generation_calls": len(MODEL_ORDER)
            * (len(prompt_ids) + 2 * len(repeat_ids)),
            "disjoint_from_previous_personaeval_pilot": True,
        },
        "independent_variable": {
            "name": "local_judge_model_snapshot",
            "levels": list(MODEL_ORDER),
        },
        "controlled_variables": {
            "model_order": list(MODEL_ORDER),
            "user_prompt": "official_prompt_exactly_as_released",
            "system_message": SYSTEM_MESSAGE,
            "temperature": 0.0,
            "sampler": "greedy",
            "maximum_new_tokens": 256,
            "maximum_prompt_tokens": 65536,
            "batch_size": 1,
            "memory": "disabled",
            "retrieval": "disabled",
            "persona_prompt": "disabled",
            "adapter": "none",
            "training_updates": 0,
            "device": "mlx_gpu",
            "seed": 20260803,
        },
        "label_isolation": {
            "prompt_dataset_contains_ground_truth": False,
            "label_file_loaded_after_both_models_finish_all_generation": True,
            "ground_truth_passed_to_model": False,
            "correct_answer_used_for_retry_or_prompt_repair": False,
        },
        "primary_metrics": [
            "unconditional_top1_accuracy",
            "strict_parse_success_rate",
            "exact_poisson_binomial_chance_superiority",
            "prediction_repeat_agreement",
            "paired_exact_mcnemar",
        ],
        "decision_rule": {
            "per_model_minimum_parse_success_rate": 0.95,
            "per_model_maximum_chance_superiority_p_value": 0.05,
            "per_model_require_wilson_lower_above_random": True,
            "per_model_minimum_prediction_repeat_agreement": 1.0,
            "if_only_one_model_passes": "select_that_model_for_larger_validation",
            "if_both_pass_and_mcnemar_p_le_0_05": "select_more_accurate_model",
            "if_both_pass_without_significant_accuracy_difference": "select_qwen3_4b_lower_resource_model",
            "if_neither_passes": "reject_both_as_target_person_judges",
            "pass_authorizes_only": "larger_disjoint_official_evaluator_validation",
        },
        "model_contracts": _model_contracts(),
        "local_environment": base.local_environment(),
        "dataset_contract": {
            "prompts": base.relative_binding(PROMPTS_PATH, role="label_free_official_prompts"),
            "labels": base.relative_binding(LABELS_PATH, role="isolated_official_labels"),
            "prompt_rows_sha256": base.canonical_json_sha256(prompts["rows"]),
            "label_rows_sha256": base.canonical_json_sha256(labels["rows"]),
        },
        "result_paths": {
            "raw": str(RAW_RESULT_PATH.relative_to(ROOT)),
            "result": str(RESULT_PATH.relative_to(ROOT)),
            "markdown": str(RESULT_MD_PATH.relative_to(ROOT)),
        },
        "boundaries": [
            "This pilot selects an evaluator model; it does not evaluate UruhaBrain.",
            "The 30-row balanced pilot is not an official full-dataset leaderboard score.",
            "The generic system transport adapter prevents direct paper-score comparison.",
            "A pass authorizes only a larger disjoint evaluator validation.",
            "No result authorizes target-person scoring, human-rater replacement, training, or production.",
        ],
    }


def _harness_lock(preregistration):
    bindings = [
        base.relative_binding(BUILDER_PATH, role="construction_code"),
        base.relative_binding(RUNNER_PATH, role="generation_and_scoring_code"),
        base.relative_binding(TEST_PATH, role="unit_and_contract_tests"),
        base.relative_binding(VERIFIER_PATH, role="independent_result_verifier"),
        base.relative_binding(BASE_BUILDER_PATH, role="imported_frozen_base_builder"),
        base.relative_binding(BASE_RUNNER_PATH, role="imported_frozen_base_runner"),
        base.relative_binding(PROMPTS_PATH, role="label_free_official_prompts"),
        base.relative_binding(LABELS_PATH, role="isolated_official_labels"),
        base.relative_binding(PREREGISTRATION_PATH, role="frozen_preregistration"),
    ]
    for contract in preregistration["model_contracts"].values():
        bindings.extend(contract["files"])
    json_repair_files = sorted((base.JSON_REPAIR_TARGET / "json_repair").rglob("*.py"))
    json_repair_files.extend(
        sorted(base.JSON_REPAIR_TARGET.glob("json_repair-*.dist-info/METADATA"))
    )
    json_repair_files.extend(
        sorted(base.JSON_REPAIR_TARGET.glob("json_repair-*.dist-info/RECORD"))
    )
    bindings.extend(
        base.external_binding(path, role="official_json_repair_dependency")
        for path in json_repair_files
    )
    pilot = preregistration["pilot_design"]
    return {
        "schema": "personaeval_local_judge_model_selection_harness_lock_v1",
        "experiment_id": EXPERIMENT_ID,
        "bindings": bindings,
        "authorization": {
            "official_dataset_commit": base.HF_DATASET_COMMIT,
            "official_code_commit": base.OFFICIAL_REPOSITORY_COMMIT,
            "model_ids": list(MODEL_ORDER),
            "primary_row_count": pilot["primary_row_count"],
            "repeat_audit_row_count": len(pilot["repeat_audit_row_ids"]),
            "total_generation_calls": pilot["total_generation_calls"],
            "batch_size": 1,
            "labels_loaded_after_all_generation": True,
            "training_updates": 0,
            "production_runtime_change": False,
        },
    }


def build(refresh=False):
    upstream = base.verify_upstream()
    model_upstream = verify_upstream_models()
    prompts, labels = build_dataset(refresh=refresh)
    preregistration = _preregistration(prompts, labels, upstream, model_upstream)
    base.atomic_json(PREREGISTRATION_PATH, preregistration)
    harness_lock = _harness_lock(preregistration)
    base.atomic_json(HARNESS_LOCK_PATH, harness_lock)
    report = {
        "schema": "personaeval_local_judge_model_selection_construction_v1",
        "experiment_id": EXPERIMENT_ID,
        "constructed": True,
        "official_dataset_commit": base.HF_DATASET_COMMIT,
        "official_code_commit": base.OFFICIAL_REPOSITORY_COMMIT,
        "model_revisions": model_upstream,
        "primary_row_count": len(prompts["rows"]),
        "rows_per_track": SAMPLE_COUNT_PER_TRACK,
        "repeat_audit_row_count": len(
            preregistration["pilot_design"]["repeat_audit_row_ids"]
        ),
        "generation_calls_per_model": preregistration["pilot_design"][
            "generation_calls_per_model"
        ],
        "total_generation_calls": preregistration["pilot_design"][
            "total_generation_calls"
        ],
        "disjoint_from_previous_pilot": True,
        "prompts_contain_labels": False,
        "preregistration_sha256": base.sha256_file(PREREGISTRATION_PATH),
        "harness_lock_sha256": base.sha256_file(HARNESS_LOCK_PATH),
        "authorization": "run_frozen_model_selection_pilot_only",
    }
    base.atomic_json(CONSTRUCTION_JSON_PATH, report)
    markdown = "\n".join(
        [
            "# PersonaEval local judge model-selection construction",
            "",
            f"- Official dataset commit: `{base.HF_DATASET_COMMIT}`",
            f"- Official code commit: `{base.OFFICIAL_REPOSITORY_COMMIT}`",
            f"- Disjoint primary rows: `{report['primary_row_count']}`",
            f"- Repeat-audit rows: `{report['repeat_audit_row_count']}`",
            f"- Models: `{', '.join(MODEL_ORDER)}`",
            "- Only independent variable: local model snapshot",
            "- Labels available during generation: `False`",
            "- Target-person / training / production authorization: `False`",
            "",
        ]
    )
    base.atomic_text(CONSTRUCTION_MD_PATH, markdown)
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()
    print(json.dumps(build(refresh=args.refresh), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
