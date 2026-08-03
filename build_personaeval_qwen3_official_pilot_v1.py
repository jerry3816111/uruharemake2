#!/usr/bin/env python3
"""Freeze a source-balanced official PersonaEval pilot for local Qwen3."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import platform
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from importlib import metadata
from pathlib import Path


ROOT = Path(__file__).resolve().parent
EXPERIMENT_ID = "personaeval_qwen3_official_pilot_v1"
SELECTION_SEED = EXPERIMENT_ID
SAMPLE_COUNT_PER_TRACK = 20
TRACKS = {
    "Drama": {"row_count": 1658, "option_count": 4},
    "Expertise": {"row_count": 699, "option_count": 5},
    "Literary": {"row_count": 26208, "option_count": 4},
}
HF_DATASET = "lingfengzhou/PersonaEval"
HF_DATASET_COMMIT = "f65c77a992414af9de49debdc6f607b4a2e472d8"
OFFICIAL_REPOSITORY = "https://github.com/maple-zhou/PersonaEval.git"
OFFICIAL_REPOSITORY_COMMIT = "19f7568a84f52e206dccdf67146235c8376cec9c"
OFFICIAL_CODE_VERSION = "0.1.0"
OFFICIAL_JSON_REPAIR_VERSION = "0.47.8"
OFFICIAL_PAPER_URL = "https://arxiv.org/abs/2508.10014"
OFFICIAL_DATASET_URL = "https://huggingface.co/datasets/lingfengzhou/PersonaEval"
OFFICIAL_CODE_URL = "https://github.com/maple-zhou/PersonaEval"
OFFICIAL_DATASET_LICENSE = "CC-BY-4.0"
OFFICIAL_CODE_LICENSE = "MIT"
SYSTEM_MESSAGE = (
    "Execute the user's role-identification task. Return only the final JSON "
    "object requested by the user. Do not output analysis, explanations, "
    "markdown, or code fences. Preserve every candidate name exactly. Use a "
    "finite probability from 0 to 1 for every candidate. Before returning, "
    "recalculate the total; if needed, set the final candidate to 1 minus the "
    "sum of the others so the probabilities total exactly 1.0."
)

HF_SOURCE_OBJECTS = {
    "Drama.csv": {
        "size": 33711931,
        "git_oid": "f3c8356689070062817c42a1d7fe4a429c30c9be",
        "lfs_sha256": "655de08e0df8e2780856900bcaf7e47f3baa0c4c9c421ad393d157c7752c96d0",
    },
    "Expertise.csv": {
        "size": 2319938,
        "git_oid": "2478b6b8b484bb9711457ebb9f57ede653e2ff6d",
        "lfs_sha256": None,
    },
    "Literary.csv": {
        "size": 581316853,
        "git_oid": "23a5d470963de377cf395cf2c0cc0a739ccec5ab",
        "lfs_sha256": "04cfa3116d64694b72f921012bb60787dbd7ae6aec5114d0faaa4fe13e6accd3",
    },
}

MODEL_NAME = "Qwen/Qwen3-4B-Instruct-2507"
MODEL_SNAPSHOT = Path(
    "/Users/jerrychang/.cache/huggingface/hub/"
    "models--Qwen--Qwen3-4B-Instruct-2507/snapshots/"
    "cdbee75f17c01a7cc42f958dc650907174af0554"
)
PYTHON_EXECUTABLE = Path(
    "/Users/jerrychang/.cache/uruhabrain/mlx-lm-0.31.3-venv/bin/python"
)
JSON_REPAIR_TARGET = Path(
    "/Users/jerrychang/.cache/uruhabrain/personaeval-official-pilot-v1-deps"
)
SOURCE_CACHE_ROOT = Path(
    f"/Users/jerrychang/.cache/uruhabrain/personaeval-{HF_DATASET_COMMIT}"
)

PROMPTS_PATH = ROOT / "datasets/personaeval_qwen3_official_pilot_v1_prompts.json"
LABELS_PATH = ROOT / "datasets/personaeval_qwen3_official_pilot_v1_labels.json"
PREREGISTRATION_PATH = (
    ROOT / "configs/personaeval_qwen3_official_pilot_v1_preregistration.json"
)
HARNESS_LOCK_PATH = (
    ROOT / "configs/personaeval_qwen3_official_pilot_v1_harness_lock.json"
)
CONSTRUCTION_JSON_PATH = (
    ROOT / "reports/personaeval_qwen3_official_pilot_v1_construction.json"
)
CONSTRUCTION_MD_PATH = (
    ROOT / "reports/personaeval_qwen3_official_pilot_v1_construction.md"
)
RAW_RESULT_PATH = ROOT / "reports/personaeval_qwen3_official_pilot_v1_raw.json"
RESULT_PATH = ROOT / "reports/personaeval_qwen3_official_pilot_v1_result.json"
RESULT_MD_PATH = ROOT / "reports/personaeval_qwen3_official_pilot_v1_result.md"

RUNNER_PATH = ROOT / "run_personaeval_qwen3_official_pilot_v1.py"
TEST_PATH = ROOT / "test_personaeval_qwen3_official_pilot_v1.py"
VERIFIER_PATH = ROOT / "verify_personaeval_qwen3_official_pilot_v1_result.py"
BUILDER_PATH = Path(__file__).resolve()

MODEL_FILES = (
    "config.json",
    "generation_config.json",
    "model.safetensors.index.json",
    "model-00001-of-00003.safetensors",
    "model-00002-of-00003.safetensors",
    "model-00003-of-00003.safetensors",
    "tokenizer.json",
    "tokenizer_config.json",
)


def canonical_json_bytes(value):
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def canonical_json_sha256(value):
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, delete=False
    ) as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        temporary = Path(handle.name)
    os.replace(temporary, path)
    path.chmod(0o644)


def atomic_text(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, delete=False
    ) as handle:
        handle.write(value)
        temporary = Path(handle.name)
    os.replace(temporary, path)
    path.chmod(0o644)


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def relative_binding(path, *, role):
    path = Path(path)
    return {
        "path": str(path.relative_to(ROOT)),
        "scope": "repository",
        "role": role,
        "sha256": sha256_file(path),
    }


def external_binding(path, *, role):
    path = Path(path)
    return {
        "path": str(path),
        "scope": "external_local",
        "role": role,
        "sha256": sha256_file(path),
    }


def selected_indices(track, row_count, sample_count=SAMPLE_COUNT_PER_TRACK):
    """Select one unseen-content index from every equal-width row-order stratum."""
    selected = []
    for stratum in range(sample_count):
        start = (stratum * row_count) // sample_count
        end = ((stratum + 1) * row_count) // sample_count
        width = end - start
        if width <= 0:
            raise ValueError("sample count exceeds track rows")
        token = f"{SELECTION_SEED}|{track}|{stratum}".encode("utf-8")
        offset = int.from_bytes(hashlib.sha256(token).digest(), "big") % width
        selected.append(start + offset)
    if len(selected) != len(set(selected)):
        raise RuntimeError(f"duplicate selected indices for {track}")
    return selected


def repeat_audit_row_ids(prompt_rows):
    """Choose four deterministic primary rows per track without reading labels."""
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
        result.extend(row["row_id"] for row in ranked[:4])
    return result


def _fetch_json(url):
    request = urllib.request.Request(url, headers={"User-Agent": "UruhaBrain-eval/1"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response)


def _git_blob_oid(path):
    path = Path(path)
    digest = hashlib.sha1()
    digest.update(f"blob {path.stat().st_size}\0".encode("ascii"))
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _source_file_exact(path, expected):
    path = Path(path)
    if not path.is_file() or path.stat().st_size != expected["size"]:
        return False
    if expected["lfs_sha256"]:
        return sha256_file(path) == expected["lfs_sha256"]
    return _git_blob_oid(path) == expected["git_oid"]


def ensure_source_file(filename, max_attempts=5):
    """Cache the original CSV at the exact official dataset commit."""
    expected = HF_SOURCE_OBJECTS[filename]
    SOURCE_CACHE_ROOT.mkdir(parents=True, exist_ok=True)
    destination = SOURCE_CACHE_ROOT / filename
    if _source_file_exact(destination, expected):
        return destination
    url = (
        f"https://huggingface.co/datasets/{HF_DATASET}/resolve/"
        f"{HF_DATASET_COMMIT}/{filename}?download=true"
    )
    for attempt in range(1, max_attempts + 1):
        temporary = SOURCE_CACHE_ROOT / f".{filename}.download-{os.getpid()}"
        try:
            request = urllib.request.Request(
                url, headers={"User-Agent": "UruhaBrain-eval/1"}
            )
            with urllib.request.urlopen(request, timeout=120) as response:
                with temporary.open("wb") as handle:
                    while True:
                        block = response.read(1024 * 1024)
                        if not block:
                            break
                        handle.write(block)
            if not _source_file_exact(temporary, expected):
                raise RuntimeError(f"downloaded official source hash mismatch: {filename}")
            os.replace(temporary, destination)
            return destination
        except (urllib.error.URLError, TimeoutError, RuntimeError):
            if temporary.exists():
                temporary.unlink()
            if attempt == max_attempts:
                raise
            time.sleep(2 ** attempt)
    raise RuntimeError(f"failed to cache official source: {filename}")


def read_selected_source_rows(track):
    filename = f"{track}.csv"
    path = ensure_source_file(filename)
    wanted = set(selected_indices(track, TRACKS[track]["row_count"]))
    rows = {}
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row_index, row in enumerate(reader):
            if row_index in wanted:
                rows[row_index] = row
            if len(rows) == len(wanted):
                break
    if set(rows) != wanted:
        missing = sorted(wanted - set(rows))
        raise RuntimeError(f"official source rows missing for {track}: {missing}")
    return rows


def verify_upstream():
    hf = _fetch_json(
        f"https://huggingface.co/api/datasets/{HF_DATASET}/revision/"
        f"{HF_DATASET_COMMIT}"
    )
    if hf.get("sha") != HF_DATASET_COMMIT:
        raise RuntimeError(f"Hugging Face commit drifted: {hf.get('sha')}")
    if hf.get("cardData", {}).get("license") != "cc-by-4.0":
        raise RuntimeError("PersonaEval dataset license drifted")

    tree = _fetch_json(
        f"https://huggingface.co/api/datasets/{HF_DATASET}/tree/"
        f"{HF_DATASET_COMMIT}?recursive=true&expand=true"
    )
    actual = {entry["path"]: entry for entry in tree}
    for filename, expected in HF_SOURCE_OBJECTS.items():
        entry = actual.get(filename)
        if not entry:
            raise RuntimeError(f"missing official source object: {filename}")
        if entry.get("size") != expected["size"] or entry.get("oid") != expected["git_oid"]:
            raise RuntimeError(f"official source object drifted: {filename}")
        expected_lfs = expected["lfs_sha256"]
        actual_lfs = (entry.get("lfs") or {}).get("oid")
        if expected_lfs != actual_lfs:
            raise RuntimeError(f"official LFS object drifted: {filename}")

    commit_api = _fetch_json(
        "https://api.github.com/repos/maple-zhou/PersonaEval/commits/"
        f"{OFFICIAL_REPOSITORY_COMMIT}"
    )
    if commit_api.get("sha") != OFFICIAL_REPOSITORY_COMMIT:
        raise RuntimeError(f"official code commit drifted: {commit_api.get('sha')}")
    return {
        "huggingface_commit": hf["sha"],
        "github_commit": commit_api["sha"],
        "dataset_license": hf["cardData"]["license"],
        "source_objects": HF_SOURCE_OBJECTS,
    }


def _validate_and_split_row(track, row_index, source):
    contract = TRACKS[track]
    option_count = contract["option_count"]
    options = [source[f"option{i}"] for i in range(1, option_count + 1)]
    if any(not isinstance(option, str) or not option for option in options):
        raise ValueError(f"invalid options for {track}:{row_index}")
    if len(options) != len(set(options)):
        raise ValueError(f"duplicate options for {track}:{row_index}")
    if source.get("gt") not in options:
        raise ValueError(f"ground truth outside options for {track}:{row_index}")
    if not isinstance(source.get("prompt"), str) or not source["prompt"]:
        raise ValueError(f"missing official prompt for {track}:{row_index}")
    if option_count == 4 and source.get("option5") not in (None, ""):
        raise ValueError(f"unexpected fifth option for {track}:{row_index}")
    row_id = f"{track.lower()}_{row_index:05d}"
    prompt = {
        "row_id": row_id,
        "track": track,
        "source_row_index": row_index,
        "option_count": option_count,
        "options": options,
        "prompt": source["prompt"],
        "prompt_sha256": hashlib.sha256(source["prompt"].encode("utf-8")).hexdigest(),
    }
    label = {
        "row_id": row_id,
        "track": track,
        "source_row_index": row_index,
        "ground_truth": source["gt"],
    }
    label["label_sha256"] = canonical_json_sha256(
        {key: label[key] for key in ("row_id", "track", "source_row_index", "ground_truth")}
    )
    return prompt, label


def build_dataset(refresh=False):
    if PROMPTS_PATH.exists() and LABELS_PATH.exists() and not refresh:
        prompts = load_json(PROMPTS_PATH)
        labels = load_json(LABELS_PATH)
        return prompts, labels
    prompt_rows = []
    label_rows = []
    for track, contract in TRACKS.items():
        source_rows = read_selected_source_rows(track)
        for row_index in selected_indices(track, contract["row_count"]):
            prompt, label = _validate_and_split_row(
                track, row_index, source_rows[row_index]
            )
            prompt_rows.append(prompt)
            label_rows.append(label)
    prompts = {
        "schema": "personaeval_official_pilot_prompts_v1",
        "experiment_id": EXPERIMENT_ID,
        "source": {
            "dataset": HF_DATASET,
            "commit": HF_DATASET_COMMIT,
            "license": OFFICIAL_DATASET_LICENSE,
        },
        "selection": {
            "method": "one_hash_selected_row_per_equal_width_row_order_stratum",
            "seed": SELECTION_SEED,
            "sample_count_per_track": SAMPLE_COUNT_PER_TRACK,
            "content_and_labels_unread_before_index_selection": True,
        },
        "rows": prompt_rows,
    }
    labels = {
        "schema": "personaeval_official_pilot_labels_v1",
        "experiment_id": EXPERIMENT_ID,
        "source": {"dataset": HF_DATASET, "commit": HF_DATASET_COMMIT},
        "rows": label_rows,
    }
    atomic_json(PROMPTS_PATH, prompts)
    atomic_json(LABELS_PATH, labels)
    return prompts, labels


def _distribution_version(name, path=None):
    if path is None:
        return metadata.version(name)
    distributions = list(metadata.distributions(path=[str(path)]))
    for distribution in distributions:
        if distribution.metadata["Name"].lower().replace("_", "-") == name.lower().replace("_", "-"):
            return distribution.version
    raise RuntimeError(f"distribution not found: {name} in {path}")


def local_environment():
    script = (
        "import json,platform,sys;from importlib import metadata;"
        "names=['mlx','mlx-lm','mlx-metal','numpy','safetensors','transformers'];"
        "print(json.dumps({'python_executable':sys.executable,'python_version':platform.python_version(),"
        "'packages':{name:metadata.version(name) for name in names}},sort_keys=True))"
    )
    output = subprocess.check_output(
        [str(PYTHON_EXECUTABLE), "-c", script], text=True
    )
    base = json.loads(output)
    base["json_repair"] = {
        "version": _distribution_version("json-repair", JSON_REPAIR_TARGET),
        "target": str(JSON_REPAIR_TARGET),
    }
    base["platform"] = platform.platform()
    return base


def _model_contract():
    files = []
    for filename in MODEL_FILES:
        path = MODEL_SNAPSHOT / filename
        if not path.is_file():
            raise RuntimeError(f"missing local model file: {path}")
        files.append(external_binding(path, role="frozen_local_model"))
    return {
        "model": MODEL_NAME,
        "snapshot_root": str(MODEL_SNAPSHOT),
        "snapshot_revision": MODEL_SNAPSHOT.name,
        "files": files,
    }


def _preregistration(prompts, labels, upstream):
    row_count = len(prompts["rows"])
    if row_count != SAMPLE_COUNT_PER_TRACK * len(TRACKS):
        raise RuntimeError("unexpected frozen pilot row count")
    if any("ground_truth" in row or "gt" in row for row in prompts["rows"]):
        raise RuntimeError("prompt-only dataset contains labels")
    prompt_ids = [row["row_id"] for row in prompts["rows"]]
    label_ids = [row["row_id"] for row in labels["rows"]]
    if prompt_ids != label_ids:
        raise RuntimeError("prompt/label row order mismatch")
    repeat_ids = repeat_audit_row_ids(prompts["rows"])
    return {
        "schema": "personaeval_qwen3_official_pilot_preregistration_v1",
        "experiment_id": EXPERIMENT_ID,
        "research_question": (
            "Can the fixed local Qwen3-4B model, with one generic JSON-only "
            "transport adapter and otherwise unchanged official PersonaEval prompts, "
            "parse and identify roles on a source-balanced frozen official subset "
            "well enough to justify a larger evaluator validation?"
        ),
        "official_provenance": {
            "paper_url": OFFICIAL_PAPER_URL,
            "dataset_url": OFFICIAL_DATASET_URL,
            "dataset": HF_DATASET,
            "dataset_commit": HF_DATASET_COMMIT,
            "dataset_license": OFFICIAL_DATASET_LICENSE,
            "source_objects": HF_SOURCE_OBJECTS,
            "code_url": OFFICIAL_CODE_URL,
            "code_commit": OFFICIAL_REPOSITORY_COMMIT,
            "code_version": OFFICIAL_CODE_VERSION,
            "code_license": OFFICIAL_CODE_LICENSE,
            "json_repair_version_from_official_lock": OFFICIAL_JSON_REPAIR_VERSION,
            "upstream_verified": upstream,
        },
        "official_harness_compatibility": {
            "unchanged_official_prompt": True,
            "official_user_prompt_exact": True,
            "generic_json_only_system_transport_adapter": SYSTEM_MESSAGE,
            "direct_official_leaderboard_comparability": False,
            "prediction_rule": "argmax_over_returned_candidate_probabilities",
            "probability_sum_tolerance": 1e-5,
            "json_repair_behavior": "official_dependency_version_0.47.8",
            "intentional_corrections": [
                {
                    "issue": "official_v0.1.0_result_frame_omits_prob5_for_Expertise",
                    "correction": "store_and_score_all_five_Expertise_options",
                },
                {
                    "issue": "official_accuracy_can_exclude_generation_or_parse_errors",
                    "correction": "primary_unconditional_accuracy_counts_every_error_as_incorrect",
                },
                {
                    "issue": "exact_official_prompt_required_2445_output_tokens_on_unscored_local_smoke_row",
                    "correction": "add_generic_json_only_transport_system_message_without_task_hints",
                },
                {
                    "issue": "initial_transport_adapter_returned_probability_total_1.1_on_nonpilot_smoke",
                    "correction": "require_explicit_final_probability_sum_recalculation_without_answer_hints",
                },
            ],
        },
        "pilot_design": {
            "tracks": TRACKS,
            "sample_count_per_track": SAMPLE_COUNT_PER_TRACK,
            "primary_row_count": row_count,
            "selection_method": prompts["selection"],
            "primary_row_ids": prompt_ids,
            "repeat_audit_row_ids": repeat_ids,
            "repeat_audit_repetitions": 3,
            "generation_call_count": row_count + 2 * len(repeat_ids),
        },
        "independent_variable": "none_single_condition_evaluator_validation",
        "controlled_variables": {
            "model_snapshot": MODEL_SNAPSHOT.name,
            "user_prompt": "official_prompt_exactly_as_released",
            "system_message": SYSTEM_MESSAGE,
            "temperature": 0.0,
            "sampler": "greedy",
            "maximum_new_tokens": 256,
            "maximum_prompt_tokens": 65536,
            "batch_size": 4,
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
            "label_file_loaded_after_all_generation_calls": True,
            "ground_truth_passed_to_model": False,
            "correct_answer_used_for_retry_or_prompt_repair": False,
        },
        "primary_metrics": {
            "unconditional_top1_accuracy": "correct_primary_rows / 60; all errors count wrong",
            "parse_success_rate": "valid_probability_distributions / 60",
            "chance_superiority": "exact_poisson_binomial_one_sided_tail",
            "prediction_repeat_agreement": "same_argmax_across_three_greedy_outputs",
        },
        "secondary_metrics": [
            "conditional_top1_accuracy",
            "top2_accuracy",
            "mean_rank",
            "brier_score",
            "expected_calibration_error",
            "per_track_metrics",
            "exact_output_repeat_agreement",
            "generation_seconds",
            "prompt_and_completion_tokens",
            "peak_memory_bytes",
        ],
        "decision_gate": {
            "minimum_parse_success_rate": 0.95,
            "maximum_chance_superiority_p_value": 0.05,
            "require_wilson_95_lower_above_random_expectation": True,
            "minimum_prediction_repeat_agreement": 1.0,
            "published_best_llm_reference_accuracy_approximate": 0.69,
            "published_human_reference_accuracy": 0.908,
            "published_references_are_descriptive_not_thresholds_because_transport_differs": True,
            "pilot_pass_authorizes_only": "preregister_larger_official_personaeval_validation",
            "pilot_failure_authorizes_only": "diagnose_or_reject_local_automated_persona_judge",
        },
        "model_contract": _model_contract(),
        "local_environment": local_environment(),
        "dataset_contract": {
            "prompts": relative_binding(PROMPTS_PATH, role="label_free_official_prompts"),
            "labels": relative_binding(LABELS_PATH, role="isolated_official_labels"),
            "prompt_rows_sha256": canonical_json_sha256(prompts["rows"]),
            "label_rows_sha256": canonical_json_sha256(labels["rows"]),
        },
        "result_paths": {
            "raw": str(RAW_RESULT_PATH.relative_to(ROOT)),
            "result": str(RESULT_PATH.relative_to(ROOT)),
            "markdown": str(RESULT_MD_PATH.relative_to(ROOT)),
        },
        "boundaries": [
            "This pilot validates only a local automated role-identification evaluator on 60 official rows.",
            "A pass does not validate UruhaBrain, target-person similarity, RightBrain quality, or production readiness.",
            "PersonaEval data is evaluation-only and is not training, prompt-memory, retrieval, or runtime persona data.",
            "Even a pass cannot replace target-familiar and general-Japanese human blind raters.",
            "The balanced pilot score is not the official full-dataset leaderboard score.",
            "The generic JSON-only system transport adapter prevents direct score comparison with the paper's exact prompt condition.",
        ],
        "prohibited_actions": {
            "benchmark_training": True,
            "benchmark_answer_in_prompt_or_memory": True,
            "target_person_training": True,
            "adapter_or_model_save": True,
            "production_runtime_change": True,
            "persona_similarity_claim": True,
            "human_rater_replacement": True,
        },
    }


def _harness_lock(preregistration):
    bindings = [
        relative_binding(BUILDER_PATH, role="construction_code"),
        relative_binding(RUNNER_PATH, role="generation_and_scoring_code"),
        relative_binding(TEST_PATH, role="unit_and_contract_tests"),
        relative_binding(VERIFIER_PATH, role="independent_result_verifier"),
        relative_binding(PROMPTS_PATH, role="label_free_official_prompts"),
        relative_binding(LABELS_PATH, role="isolated_official_labels"),
        relative_binding(PREREGISTRATION_PATH, role="frozen_preregistration"),
    ]
    bindings.extend(preregistration["model_contract"]["files"])
    json_repair_files = sorted((JSON_REPAIR_TARGET / "json_repair").rglob("*.py"))
    json_repair_files.extend(
        sorted(JSON_REPAIR_TARGET.glob("json_repair-*.dist-info/METADATA"))
    )
    json_repair_files.extend(
        sorted(JSON_REPAIR_TARGET.glob("json_repair-*.dist-info/RECORD"))
    )
    if not json_repair_files:
        raise RuntimeError("official json-repair dependency files are missing")
    bindings.extend(
        external_binding(path, role="official_json_repair_dependency")
        for path in json_repair_files
    )
    return {
        "schema": "personaeval_qwen3_official_pilot_harness_lock_v1",
        "experiment_id": EXPERIMENT_ID,
        "bindings": bindings,
        "authorization": {
            "official_dataset_commit": HF_DATASET_COMMIT,
            "official_code_commit": OFFICIAL_REPOSITORY_COMMIT,
            "primary_row_count": preregistration["pilot_design"]["primary_row_count"],
            "repeat_audit_row_count": len(
                preregistration["pilot_design"]["repeat_audit_row_ids"]
            ),
            "generation_call_count": preregistration["pilot_design"]["generation_call_count"],
            "label_file_loaded_after_all_generation_calls": True,
            "training_updates": 0,
            "memory_enabled": False,
            "persona_prompt_enabled": False,
            "production_runtime_change": False,
        },
    }


def _construction_report(preregistration, harness_lock):
    prompt_rows = preregistration["pilot_design"]["primary_row_ids"]
    return {
        "schema": "personaeval_qwen3_official_pilot_construction_v1",
        "experiment_id": EXPERIMENT_ID,
        "constructed": True,
        "official_dataset_commit": HF_DATASET_COMMIT,
        "official_code_commit": OFFICIAL_REPOSITORY_COMMIT,
        "primary_row_count": len(prompt_rows),
        "rows_per_track": SAMPLE_COUNT_PER_TRACK,
        "repeat_audit_row_count": len(
            preregistration["pilot_design"]["repeat_audit_row_ids"]
        ),
        "prompts_contain_labels": False,
        "unchanged_official_prompts": True,
        "expertise_fifth_option_supported": True,
        "errors_count_incorrect_in_primary_accuracy": True,
        "preregistration_sha256": sha256_file(PREREGISTRATION_PATH),
        "harness_lock_sha256": sha256_file(HARNESS_LOCK_PATH),
        "decision": {
            "authorized_next_step": "run_frozen_local_qwen3_personaeval_pilot_only",
            "training_authorized": False,
            "target_person_judging_authorized": False,
            "production_authorized": False,
        },
    }


def build(refresh=False):
    upstream = verify_upstream()
    prompts, labels = build_dataset(refresh=refresh)
    preregistration = _preregistration(prompts, labels, upstream)
    atomic_json(PREREGISTRATION_PATH, preregistration)
    harness_lock = _harness_lock(preregistration)
    atomic_json(HARNESS_LOCK_PATH, harness_lock)
    report = _construction_report(preregistration, harness_lock)
    atomic_json(CONSTRUCTION_JSON_PATH, report)
    markdown = "\n".join(
        [
            "# PersonaEval Qwen3 official pilot construction",
            "",
            f"- Official dataset commit: `{HF_DATASET_COMMIT}`",
            f"- Official code commit: `{OFFICIAL_REPOSITORY_COMMIT}`",
            f"- Primary rows: `{report['primary_row_count']}` ({SAMPLE_COUNT_PER_TRACK} per track)",
            f"- Repeat-audit rows: `{report['repeat_audit_row_count']}`",
            "- Official prompts changed: `False`",
            "- Labels available during generation: `False`",
            "- Training / target-person judging / production authorization: `False`",
            "",
        ]
    )
    atomic_text(CONSTRUCTION_MD_PATH, markdown)
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()
    report = build(refresh=args.refresh)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
