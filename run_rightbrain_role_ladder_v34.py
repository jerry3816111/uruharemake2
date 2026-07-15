#!/usr/bin/env python3
"""Run the V34 development-only local RightBrain model ladder."""

import argparse
import hashlib
import json
import os
import subprocess
import time
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
    score_rightbrain_output,
)


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "rightbrain_role_specialization_v34_preregistration.json"
SOURCE_DATASET_PATH = ROOT / "datasets" / "rightbrain_qwen35_migration_v33_holdout.json"
DEFAULT_OUTPUT = ROOT / "reports" / "rightbrain_role_ladder_v34_pilot_raw.json"
TZ = ZoneInfo("Asia/Tokyo")


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


def _validate_local_models(conditions):
    inventory = _ollama_inventory()
    errors = []
    snapshots = {}
    for condition, frozen in conditions.items():
        tag = frozen["ollama_tag"]
        actual = inventory.get(tag)
        if not actual:
            errors.append(f"missing_model:{condition}:{tag}")
            continue
        snapshots[condition] = {
            "name": actual.get("name"),
            "digest": actual.get("digest"),
            "size": actual.get("size"),
            "details": actual.get("details") or {},
        }
        if actual.get("digest") != frozen["digest"]:
            errors.append(f"digest_mismatch:{condition}")
        if int(actual.get("size") or 0) != int(frozen["blob_bytes"]):
            errors.append(f"size_mismatch:{condition}")
    if errors:
        raise ValueError("; ".join(errors))
    return snapshots


def _selected_cases(config, dataset):
    by_id = {case["id"]: case for case in dataset["rightbrain_cases"]}
    requested = config["development_pilot"]["case_ids"]
    missing = [case_id for case_id in requested if case_id not in by_id]
    if missing:
        raise ValueError(f"Missing V34 development cases: {missing}")
    cases = [by_id[case_id] for case_id in requested]
    categories = [case["category"] for case in cases]
    if len(cases) != 12 or len(set(categories)) != 12:
        raise ValueError("V34 development pilot must contain one case from each of 12 categories")
    return cases


def _new_report(config, dataset, snapshots):
    return {
        "schema": "uruha_rightbrain_role_ladder_pilot_raw_v34",
        "evidence_status": "development_only_not_formal_confirmation",
        "started_at": _now(),
        "completed_at": None,
        "runner_commit": _git_head(),
        "preregistration_sha256": _sha256(CONFIG_PATH),
        "source_dataset_sha256": _sha256(SOURCE_DATASET_PATH),
        "case_ids": list(config["development_pilot"]["case_ids"]),
        "model_conditions": deepcopy(config["development_pilot"]["conditions"]),
        "local_model_snapshots": snapshots,
        "rows": [],
        "transport_errors": [],
    }


def _load_or_create(output, config, dataset, snapshots):
    if not output.exists():
        return _new_report(config, dataset, snapshots)
    report = json.loads(output.read_text(encoding="utf-8"))
    checks = {
        "preregistration_sha256": _sha256(CONFIG_PATH),
        "source_dataset_sha256": _sha256(SOURCE_DATASET_PATH),
        "runner_commit": _git_head(),
    }
    for field, expected in checks.items():
        if report.get(field) != expected:
            raise ValueError(f"Existing V34 pilot report {field} mismatch")
    return report


def _model_info(condition, frozen):
    return {
        "condition": condition,
        "model_tag": frozen["ollama_tag"],
        "blob_bytes": frozen["blob_bytes"],
        "thinking": frozen.get("thinking"),
    }


def run(output=DEFAULT_OUTPUT, selected_conditions=None):
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    dataset = json.loads(SOURCE_DATASET_PATH.read_text(encoding="utf-8"))
    conditions = config["development_pilot"]["conditions"]
    selected_conditions = tuple(selected_conditions or conditions)
    unknown = sorted(set(selected_conditions) - set(conditions))
    if unknown:
        raise ValueError(f"Unknown V34 conditions: {unknown}")

    snapshots = _validate_local_models(conditions)
    cases = _selected_cases(config, dataset)
    report = _load_or_create(output, config, dataset, snapshots)
    generation = config["development_pilot"]["generation"]
    seeds = tuple(generation["seeds"])

    os.environ["URUHA_SKIP_AUTO_VENV"] = "1"
    from uruha_brain_mac import RIGHT_BRAIN_MODEL_SYSTEM_PROMPT, RightBrain

    brain = RightBrain(load_model=False)
    existing = {(row["condition"], row["case_id"], row["seed"]) for row in report["rows"]}
    total = len(selected_conditions) * len(cases) * len(seeds)
    completed = sum(row["condition"] in selected_conditions for row in report["rows"])

    for condition in selected_conditions:
        frozen = conditions[condition]
        model_info = _model_info(condition, frozen)
        for other, other_frozen in conditions.items():
            if other != condition:
                _unload_model(other_frozen["ollama_tag"])
        for case in cases:
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
                options = {
                    "temperature": generation["temperature"],
                    "top_p": generation["top_p"],
                    "top_k": generation["top_k"],
                    "repeat_penalty": generation["repeat_penalty"],
                    "seed": seed,
                    "num_ctx": generation["context_tokens"],
                    "num_predict": generation["maximum_output_tokens"],
                }
                started = time.perf_counter()
                response, elapsed, attempts, errors = _call_ollama(
                    _chat_body(model_info, messages, options=options)
                )
                elapsed = max(elapsed, time.perf_counter() - started)
                raw_reply = str((response.get("message") or {}).get("content") or "").strip()
                report["rows"].append(
                    {
                        "condition": condition,
                        "model_tag": model_info["model_tag"],
                        "case_id": case["id"],
                        "category": case["category"],
                        "seed": seed,
                        "sampling": options,
                        "raw_reply": raw_reply,
                        "score": score_rightbrain_output(brain, case, logic, raw_reply),
                        "response_metrics": _response_metrics(response, elapsed),
                        "transport_attempts": attempts,
                        "prior_transport_errors": errors,
                    }
                )
                completed += 1
                _atomic_write(output, report)
                if completed % 12 == 0:
                    print(f"[{completed}/{total}] {condition} {case['id']}", flush=True)
        _unload_model(model_info["model_tag"])

    expected_per_condition = len(cases) * len(seeds)
    if all(
        len([row for row in report["rows"] if row["condition"] == condition])
        == expected_per_condition
        for condition in conditions
    ):
        report["completed_at"] = _now()
    _atomic_write(output, report)
    return report


def main():
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    choices = tuple(config["development_pilot"]["conditions"])
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--condition", action="append", choices=choices)
    args = parser.parse_args()
    report = run(output=args.output, selected_conditions=args.condition)
    print(
        json.dumps(
            {
                "output": str(args.output),
                "row_count": len(report["rows"]),
                "completed_at": report["completed_at"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
