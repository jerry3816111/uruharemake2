#!/usr/bin/env python3
"""Freeze a disjoint PersonaEval pilot comparing two output contracts."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

import build_personaeval_qwen3_official_pilot_v1 as base


ROOT = Path(__file__).resolve().parent
EXPERIMENT_ID = "personaeval_output_contract_selection_v1"
SELECTION_SEED = EXPERIMENT_ID
SAMPLE_COUNT_PER_TRACK = 10
REPEAT_COUNT_PER_TRACK = 3
TRACKS = base.TRACKS
CONDITION_ORDER = ("strict_probability", "candidate_name")
SYSTEM_MESSAGES = {
    "strict_probability": base.SYSTEM_MESSAGE,
    "candidate_name": (
        "Perform the user's role-identification task, but replace the requested "
        "probability JSON with this transport contract: return exactly one candidate "
        "name copied verbatim from the candidate list. Return no analysis, JSON, "
        "probability, punctuation, quotes, markdown, or extra text."
    ),
}

PREVIOUS_PROMPT_PATHS = (
    base.PROMPTS_PATH,
    ROOT / "datasets/personaeval_local_judge_model_selection_v1_prompts.json",
)
SMOKE_EXCLUSIONS = {"Drama": {0, 1, 2, 3, 4}, "Expertise": set(), "Literary": set()}

PROMPTS_PATH = ROOT / "datasets/personaeval_output_contract_selection_v1_prompts.json"
LABELS_PATH = ROOT / "datasets/personaeval_output_contract_selection_v1_labels.json"
PREREGISTRATION_PATH = (
    ROOT / "configs/personaeval_output_contract_selection_v1_preregistration.json"
)
HARNESS_LOCK_PATH = (
    ROOT / "configs/personaeval_output_contract_selection_v1_harness_lock.json"
)
CONSTRUCTION_JSON_PATH = (
    ROOT / "reports/personaeval_output_contract_selection_v1_construction.json"
)
CONSTRUCTION_MD_PATH = (
    ROOT / "reports/personaeval_output_contract_selection_v1_construction.md"
)
RAW_RESULT_PATH = ROOT / "reports/personaeval_output_contract_selection_v1_raw.json"
RESULT_PATH = ROOT / "reports/personaeval_output_contract_selection_v1_result.json"
RESULT_MD_PATH = ROOT / "reports/personaeval_output_contract_selection_v1_result.md"
VERIFICATION_JSON_PATH = (
    ROOT / "reports/personaeval_output_contract_selection_v1_verification.json"
)
VERIFICATION_MD_PATH = (
    ROOT / "reports/personaeval_output_contract_selection_v1_verification.md"
)

BUILDER_PATH = Path(__file__).resolve()
RUNNER_PATH = ROOT / "run_personaeval_output_contract_selection_v1.py"
TEST_PATH = ROOT / "test_personaeval_output_contract_selection_v1.py"
VERIFIER_PATH = ROOT / "verify_personaeval_output_contract_selection_v1_result.py"
BASE_BUILDER_PATH = ROOT / "build_personaeval_qwen3_official_pilot_v1.py"
BASE_RUNNER_PATH = ROOT / "run_personaeval_qwen3_official_pilot_v1.py"


def excluded_indices():
    result = {track: set(SMOKE_EXCLUSIONS[track]) for track in TRACKS}
    for path in PREVIOUS_PROMPT_PATHS:
        payload = base.load_json(path)
        for row in payload["rows"]:
            result[row["track"]].add(row["source_row_index"])
    return result


def selected_indices(track, sample_count=SAMPLE_COUNT_PER_TRACK):
    excluded = excluded_indices()[track]
    eligible = [
        index for index in range(TRACKS[track]["row_count"]) if index not in excluded
    ]
    selected = []
    for stratum in range(sample_count):
        start = (stratum * len(eligible)) // sample_count
        end = ((stratum + 1) * len(eligible)) // sample_count
        token = f"{SELECTION_SEED}|{track}|{stratum}".encode("utf-8")
        offset = int.from_bytes(hashlib.sha256(token).digest(), "big") % (end - start)
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


def _read_rows(track, indices):
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
        source_rows = _read_rows(track, indices)
        for row_index in indices:
            prompt, label = base._validate_and_split_row(
                track, row_index, source_rows[row_index]
            )
            prompt_rows.append(prompt)
            label_rows.append(label)
    prompts = {
        "schema": "personaeval_output_contract_selection_prompts_v1",
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
            "excluded_all_previous_personaeval_primary_rows": True,
            "excluded_all_transport_smoke_rows": True,
            "content_and_labels_unread_before_index_selection": True,
        },
        "rows": prompt_rows,
    }
    labels = {
        "schema": "personaeval_output_contract_selection_labels_v1",
        "experiment_id": EXPERIMENT_ID,
        "source": {"dataset": base.HF_DATASET, "commit": base.HF_DATASET_COMMIT},
        "rows": label_rows,
    }
    base.atomic_json(PROMPTS_PATH, prompts)
    base.atomic_json(LABELS_PATH, labels)
    return prompts, labels


def _model_contract():
    files = []
    for filename in base.MODEL_FILES:
        path = base.MODEL_SNAPSHOT / filename
        if not path.is_file():
            raise RuntimeError(f"missing local model file: {path}")
        files.append(base.external_binding(path, role="frozen_qwen3_4b_model"))
    return {
        "name": base.MODEL_NAME,
        "snapshot_root": str(base.MODEL_SNAPSHOT),
        "snapshot_revision": base.MODEL_SNAPSHOT.name,
        "files": files,
    }


def _preregistration(prompts, labels, upstream):
    prompt_ids = [row["row_id"] for row in prompts["rows"]]
    label_ids = [row["row_id"] for row in labels["rows"]]
    if prompt_ids != label_ids or len(prompt_ids) != 30:
        raise RuntimeError("unexpected prompt/label contract")
    if any("gt" in row or "ground_truth" in row for row in prompts["rows"]):
        raise RuntimeError("prompt file contains labels")
    previous = set()
    for path in PREVIOUS_PROMPT_PATHS:
        previous.update(
            (row["track"], row["source_row_index"])
            for row in base.load_json(path)["rows"]
        )
    current = {
        (row["track"], row["source_row_index"]) for row in prompts["rows"]
    }
    if previous & current:
        raise RuntimeError("new pilot overlaps an earlier PersonaEval pilot")
    repeat_ids = repeat_audit_row_ids(prompts["rows"])
    calls = len(prompt_ids) + 2 * len(repeat_ids)
    return {
        "schema": "personaeval_output_contract_selection_preregistration_v1",
        "experiment_id": EXPERIMENT_ID,
        "research_question": (
            "Does a candidate-name output contract improve local Qwen3-4B role "
            "identification reliability without reducing accuracy on a new official holdout?"
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
        },
        "compatibility_boundary": {
            "official_user_prompt_exact_in_both_conditions": True,
            "strict_probability_condition_uses_official_parser": True,
            "candidate_name_condition_is_adapted_transport": True,
            "direct_official_leaderboard_comparability": False,
            "all_generation_or_parse_errors_count_wrong": True,
        },
        "pilot_design": {
            "tracks": TRACKS,
            "sample_count_per_track": SAMPLE_COUNT_PER_TRACK,
            "primary_row_count": len(prompt_ids),
            "primary_row_ids": prompt_ids,
            "repeat_audit_row_ids": repeat_ids,
            "repeat_audit_repetitions": 3,
            "generation_calls_per_condition": calls,
            "total_generation_calls": calls * len(CONDITION_ORDER),
            "disjoint_from_all_previous_personaeval_pilots": True,
        },
        "independent_variable": {
            "name": "output_contract",
            "levels": list(CONDITION_ORDER),
            "strict_probability_system_message": SYSTEM_MESSAGES["strict_probability"],
            "candidate_name_system_message": SYSTEM_MESSAGES["candidate_name"],
        },
        "controlled_variables": {
            "condition_order": list(CONDITION_ORDER),
            "model_snapshot": base.MODEL_SNAPSHOT.name,
            "official_user_prompt": "unchanged",
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
            "label_file_loaded_after_both_conditions_finish_all_generation": True,
            "ground_truth_passed_to_model": False,
            "correct_answer_used_for_retry_or_prompt_repair": False,
        },
        "decision_rule": {
            "candidate_minimum_parse_success_rate": 0.98,
            "candidate_maximum_chance_superiority_p_value": 0.05,
            "candidate_require_wilson_lower_above_random": True,
            "candidate_minimum_prediction_repeat_agreement": 1.0,
            "minimum_parse_improvement_over_strict": 0.05,
            "candidate_accuracy_must_not_be_below_strict": True,
            "pass_authorizes_only": "larger_disjoint_adapted_evaluator_validation",
            "failure_action": "stop_output_contract_line_or_redesign_local_judge",
        },
        "model_contract": _model_contract(),
        "local_environment": base.local_environment(),
        "dataset_contract": {
            "prompts": base.relative_binding(PROMPTS_PATH, role="label_free_official_prompts"),
            "labels": base.relative_binding(LABELS_PATH, role="isolated_official_labels"),
            "prompt_rows_sha256": base.canonical_json_sha256(prompts["rows"]),
            "label_rows_sha256": base.canonical_json_sha256(labels["rows"]),
        },
        "boundaries": [
            "This pilot evaluates an output interface, not UruhaBrain or target-person similarity.",
            "The candidate-name condition is adapted and is not an official leaderboard score.",
            "A pass authorizes only a larger disjoint adapted evaluator validation.",
            "No result authorizes target-person judging, human-rater replacement, training, or production.",
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
        base.relative_binding(PREVIOUS_PROMPT_PATHS[0], role="previous_pilot_prompt_exclusion"),
        base.relative_binding(PREVIOUS_PROMPT_PATHS[1], role="previous_model_pilot_prompt_exclusion"),
        base.relative_binding(PROMPTS_PATH, role="label_free_official_prompts"),
        base.relative_binding(LABELS_PATH, role="isolated_official_labels"),
        base.relative_binding(PREREGISTRATION_PATH, role="frozen_preregistration"),
    ]
    bindings.extend(preregistration["model_contract"]["files"])
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
        "schema": "personaeval_output_contract_selection_harness_lock_v1",
        "experiment_id": EXPERIMENT_ID,
        "bindings": bindings,
        "authorization": {
            "condition_order": list(CONDITION_ORDER),
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
    prompts, labels = build_dataset(refresh=refresh)
    preregistration = _preregistration(prompts, labels, upstream)
    base.atomic_json(PREREGISTRATION_PATH, preregistration)
    lock = _harness_lock(preregistration)
    base.atomic_json(HARNESS_LOCK_PATH, lock)
    report = {
        "schema": "personaeval_output_contract_selection_construction_v1",
        "experiment_id": EXPERIMENT_ID,
        "constructed": True,
        "primary_row_count": len(prompts["rows"]),
        "rows_per_track": SAMPLE_COUNT_PER_TRACK,
        "repeat_audit_row_count": len(
            preregistration["pilot_design"]["repeat_audit_row_ids"]
        ),
        "generation_calls_per_condition": preregistration["pilot_design"][
            "generation_calls_per_condition"
        ],
        "total_generation_calls": preregistration["pilot_design"][
            "total_generation_calls"
        ],
        "conditions": list(CONDITION_ORDER),
        "disjoint_from_previous_pilots": True,
        "prompts_contain_labels": False,
        "preregistration_sha256": base.sha256_file(PREREGISTRATION_PATH),
        "harness_lock_sha256": base.sha256_file(HARNESS_LOCK_PATH),
        "authorization": "run_frozen_output_contract_pilot_only",
    }
    base.atomic_json(CONSTRUCTION_JSON_PATH, report)
    base.atomic_text(
        CONSTRUCTION_MD_PATH,
        "\n".join(
            [
                "# PersonaEval output-contract selection construction",
                "",
                f"- Disjoint primary rows: `{report['primary_row_count']}`",
                f"- Repeat-audit rows: `{report['repeat_audit_row_count']}`",
                f"- Conditions: `{', '.join(CONDITION_ORDER)}`",
                "- Only independent variable: output contract",
                "- Labels available during generation: `False`",
                "- Target-person / training / production authorization: `False`",
                "",
            ]
        ),
    )
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()
    print(json.dumps(build(refresh=args.refresh), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
