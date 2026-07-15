#!/usr/bin/env python3
"""Run the frozen V34 fresh RightBrain and VRM confirmation evaluation."""

import argparse
import hashlib
import json
import os
import subprocess
import urllib.request
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from run_rightbrain_qwen35_migration_v33 import (
    _call_ollama,
    _chat_body,
    _response_metrics,
    _unload_model,
    score_action_output,
    score_rightbrain_output,
)


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "rightbrain_role_specialization_v34_confirmation_preregistration.json"
DATASET_PATH = ROOT / "datasets" / "rightbrain_role_specialization_v34_confirmation.json"
DEFAULT_OUTPUT = ROOT / "reports" / "rightbrain_role_specialization_v34_confirmation_raw.json"
TZ = ZoneInfo("Asia/Tokyo")
BASE_RIGHTBRAIN_CONDITIONS = (
    "qwen2_5_7b_single_reference",
    "qwen3_5_9b_single_upper_reference",
    "qwen3_5_4b_single_ablation",
)


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _now():
    return datetime.now(TZ).isoformat(timespec="seconds")


def _git_head():
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def _atomic_write(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def _ollama_inventory():
    with urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=30) as response:
        payload = json.load(response)
    return {row["name"]: row for row in payload.get("models") or []}


def _validate_models(config):
    inventory = _ollama_inventory()
    snapshots = {}
    errors = []
    combined = {
        **config["rightbrain_conditions"],
        **config["action_conditions"],
    }
    for condition, frozen in combined.items():
        tag = frozen["ollama_tag"]
        actual = inventory.get(tag)
        if not actual:
            errors.append(f"missing:{condition}:{tag}")
            continue
        snapshots[tag] = {
            "digest": actual.get("digest"),
            "size": actual.get("size"),
            "details": actual.get("details") or {},
        }
        if actual.get("digest") != frozen["digest"]:
            errors.append(f"digest_mismatch:{condition}")
    if errors:
        raise ValueError("; ".join(errors))
    return snapshots


def _model_info(condition, frozen, snapshots):
    snapshot = snapshots[frozen["ollama_tag"]]
    return {
        "condition": condition,
        "model_tag": frozen["ollama_tag"],
        "blob_bytes": snapshot["size"],
        "thinking": frozen.get("thinking"),
    }


def _new_report(config, snapshots):
    return {
        "schema": "uruha_rightbrain_role_specialization_confirmation_raw_v34",
        "evidence_status": "fresh_frozen_confirmation",
        "started_at": _now(),
        "completed_at": None,
        "runner_commit": _git_head(),
        "preregistration_sha256": _sha256(CONFIG_PATH),
        "dataset_sha256": _sha256(DATASET_PATH),
        "model_snapshots": snapshots,
        "rightbrain_first_rows": [],
        "rightbrain_retry_rows": [],
        "action_rows": [],
    }


def _load_or_create(output, config, snapshots):
    if not output.exists():
        return _new_report(config, snapshots)
    report = json.loads(output.read_text(encoding="utf-8"))
    checks = {
        "runner_commit": _git_head(),
        "preregistration_sha256": _sha256(CONFIG_PATH),
        "dataset_sha256": _sha256(DATASET_PATH),
    }
    for field, expected in checks.items():
        if report.get(field) != expected:
            raise ValueError(f"Existing confirmation report {field} mismatch")
    return report


def _rightbrain_options(config, seed, retry=False):
    frozen = config["rightbrain_generation"]["guarded_retry" if retry else "first_attempt"]
    return {
        "temperature": frozen["temperature"],
        "top_p": frozen["top_p"],
        "top_k": frozen["top_k"],
        "repeat_penalty": frozen["repeat_penalty"],
        "seed": seed + (frozen.get("seed_offset") or 0),
        "num_ctx": frozen["context_tokens"],
        "num_predict": frozen["maximum_output_tokens"],
    }


def _run_rightbrain(config, dataset, report, snapshots, output):
    os.environ["URUHA_SKIP_AUTO_VENV"] = "1"
    from uruha_brain_mac import RIGHT_BRAIN_MODEL_SYSTEM_PROMPT, RightBrain

    brain = RightBrain(load_model=False)
    seeds = tuple(config["rightbrain_generation"]["seeds"])
    existing = {
        (row["condition"], row["case_id"], row["seed"])
        for row in report["rightbrain_first_rows"]
    }
    expected = len(BASE_RIGHTBRAIN_CONDITIONS) * len(dataset["rightbrain_cases"]) * len(seeds)
    completed = len(report["rightbrain_first_rows"])

    for condition in BASE_RIGHTBRAIN_CONDITIONS:
        frozen = config["rightbrain_conditions"][condition]
        model_info = _model_info(condition, frozen, snapshots)
        for other in BASE_RIGHTBRAIN_CONDITIONS:
            if other != condition:
                _unload_model(config["rightbrain_conditions"][other]["ollama_tag"])
        for case in dataset["rightbrain_cases"]:
            for seed in seeds:
                key = (condition, case["id"], seed)
                if key in existing:
                    continue
                logic = deepcopy(case["logic"])
                max_chars = int((logic.get("constraints") or {}).get("max_chars") or 48)
                payload = brain._build_model_surface_payload(
                    logic,
                    deepcopy(case.get("psyche") or {}),
                    max_chars,
                    memory_data=deepcopy(case.get("memory_data") or {}),
                )
                messages = [
                    {"role": "system", "content": RIGHT_BRAIN_MODEL_SYSTEM_PROMPT},
                    {"role": "user", "content": payload},
                ]
                options = _rightbrain_options(config, seed)
                response, elapsed, attempts, errors = _call_ollama(
                    _chat_body(model_info, messages, options=options)
                )
                raw_reply = str((response.get("message") or {}).get("content") or "").strip()
                report["rightbrain_first_rows"].append(
                    {
                        "condition": condition,
                        "model_tag": model_info["model_tag"],
                        "case_id": case["id"],
                        "category": case["category"],
                        "seed": seed,
                        "raw_reply": raw_reply,
                        "sampling": options,
                        "score": score_rightbrain_output(brain, case, logic, raw_reply),
                        "response_metrics": _response_metrics(response, elapsed),
                        "transport_attempts": attempts,
                        "prior_transport_errors": errors,
                    }
                )
                completed += 1
                _atomic_write(output, report)
                if completed % 24 == 0:
                    print(f"[rightbrain {completed}/{expected}] {condition} {case['id']}", flush=True)
        _unload_model(model_info["model_tag"])

    four_b_rows = [
        row
        for row in report["rightbrain_first_rows"]
        if row["condition"] == "qwen3_5_4b_single_ablation"
    ]
    retry_existing = {(row["case_id"], row["seed"]) for row in report["rightbrain_retry_rows"]}
    retry_condition = config["rightbrain_conditions"]["qwen3_5_4b_guarded_candidate"]
    model_info = _model_info("qwen3_5_4b_guarded_candidate", retry_condition, snapshots)
    cases = {case["id"]: case for case in dataset["rightbrain_cases"]}
    rejected = [row for row in four_b_rows if not row["score"]["current_gate_raw_pass"]]
    for index, first in enumerate(rejected, start=1):
        key = (first["case_id"], first["seed"])
        if key in retry_existing:
            continue
        case = cases[first["case_id"]]
        logic = deepcopy(case["logic"])
        max_chars = int((logic.get("constraints") or {}).get("max_chars") or 48)
        payload = brain._build_model_surface_payload(
            logic,
            deepcopy(case.get("psyche") or {}),
            max_chars,
            memory_data=deepcopy(case.get("memory_data") or {}),
        )
        messages = [
            {"role": "system", "content": RIGHT_BRAIN_MODEL_SYSTEM_PROMPT},
            {"role": "user", "content": payload},
        ]
        options = _rightbrain_options(config, first["seed"], retry=True)
        response, elapsed, attempts, errors = _call_ollama(
            _chat_body(model_info, messages, options=options)
        )
        raw_reply = str((response.get("message") or {}).get("content") or "").strip()
        report["rightbrain_retry_rows"].append(
            {
                "condition": "qwen3_5_4b_guarded_candidate",
                "model_tag": model_info["model_tag"],
                "case_id": case["id"],
                "category": case["category"],
                "seed": first["seed"],
                "raw_reply": raw_reply,
                "sampling": options,
                "score": score_rightbrain_output(brain, case, logic, raw_reply),
                "response_metrics": _response_metrics(response, elapsed),
                "transport_attempts": attempts,
                "prior_transport_errors": errors,
            }
        )
        _atomic_write(output, report)
        print(f"[retry {index}/{len(rejected)}] {case['id']}", flush=True)
    _unload_model(model_info["model_tag"])


def _run_actions(config, dataset, report, snapshots, output):
    existing = {(row["condition"], row["case_id"]) for row in report["action_rows"]}
    conditions = config["action_conditions"]
    generation = config["action_generation"]
    expected = len(conditions) * len(dataset["action_cases"])
    completed = len(report["action_rows"])
    for condition, frozen in conditions.items():
        model_info = _model_info(condition, frozen, snapshots)
        for other, other_frozen in conditions.items():
            if other != condition:
                _unload_model(other_frozen["ollama_tag"])
        for case in dataset["action_cases"]:
            key = (condition, case["id"])
            if key in existing:
                continue
            messages = [
                {"role": "system", "content": dataset["tool_system_prompt"]},
                {"role": "user", "content": case["user_input"]},
            ]
            options = {
                "temperature": generation["temperature"],
                "top_p": 1.0,
                "seed": generation["seed"],
                "num_ctx": generation["context_tokens"],
                "num_predict": generation["maximum_output_tokens"],
            }
            response, elapsed, attempts, errors = _call_ollama(
                _chat_body(model_info, messages, options=options, tools=dataset["tool_schemas"])
            )
            message = response.get("message") or {}
            calls = message.get("tool_calls") or []
            report["action_rows"].append(
                {
                    "condition": condition,
                    "model_tag": model_info["model_tag"],
                    "case_id": case["id"],
                    "family": case["family"],
                    "raw_content": str(message.get("content") or ""),
                    "score": score_action_output(case, calls),
                    "response_metrics": _response_metrics(response, elapsed),
                    "transport_attempts": attempts,
                    "prior_transport_errors": errors,
                }
            )
            completed += 1
            _atomic_write(output, report)
            if completed % 12 == 0:
                print(f"[action {completed}/{expected}] {condition} {case['id']}", flush=True)
        _unload_model(model_info["model_tag"])


def run(output=DEFAULT_OUTPUT):
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    dataset = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    snapshots = _validate_models(config)
    report = _load_or_create(output, config, snapshots)
    _run_rightbrain(config, dataset, report, snapshots, output)
    _run_actions(config, dataset, report, snapshots, output)

    first_expected = (
        len(BASE_RIGHTBRAIN_CONDITIONS)
        * len(dataset["rightbrain_cases"])
        * len(config["rightbrain_generation"]["seeds"])
    )
    retry_expected = sum(
        row["condition"] == "qwen3_5_4b_single_ablation"
        and not row["score"]["current_gate_raw_pass"]
        for row in report["rightbrain_first_rows"]
    )
    action_expected = len(config["action_conditions"]) * len(dataset["action_cases"])
    if (
        len(report["rightbrain_first_rows"]) == first_expected
        and len(report["rightbrain_retry_rows"]) == retry_expected
        and len(report["action_rows"]) == action_expected
    ):
        report["completed_at"] = _now()
    _atomic_write(output, report)
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    report = run(args.output)
    print(
        json.dumps(
            {
                "rightbrain_first_rows": len(report["rightbrain_first_rows"]),
                "rightbrain_retry_rows": len(report["rightbrain_retry_rows"]),
                "action_rows": len(report["action_rows"]),
                "completed_at": report["completed_at"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
