#!/usr/bin/env python3
"""Run the preregistered V49 local-model binary execution-gate sweep."""

import argparse
import hashlib
import json
import os
import subprocess
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from action_candidate_perception_v47 import load_v47_anchor_ontology
from binary_execution_gate_v49 import (
    build_binary_gate_payload,
    parse_binary_gate_response,
)
from grounded_commitment_classifier_v42 import ground_supported_targets
from run_rightbrain_qwen35_migration_v33 import (
    _call_ollama,
    _chat_body,
    _response_metrics,
    _unload_model,
)


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "binary_execution_gate_v49_preregistration.json"
V45_CONFIG_PATH = ROOT / "configs" / "discourse_state_perception_v45_preregistration.json"
DATASET_PATH = ROOT / "datasets" / "discourse_state_perception_v45_holdout.json"
DEFAULT_OUTPUT = ROOT / "reports" / "binary_execution_gate_v49_development_raw.json"
TZ = ZoneInfo("Asia/Tokyo")


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _now():
    return datetime.now(TZ).isoformat(timespec="seconds")


def _git_head():
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()


def _atomic_write(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    os.replace(temporary, path)


def _validate_inputs(config, dataset):
    frozen = config["frozen_inputs"]
    for key, expected in frozen.items():
        if key.endswith("_sha256"):
            path = ROOT / frozen[key.removesuffix("_sha256")]
            if _sha256(path) != expected:
                raise ValueError(f"V49 frozen input hash mismatch: {path.name}")
    if len(dataset["cases"]) != frozen["case_count"]:
        raise ValueError("V49 retired development case count mismatch")
    if config["expected_judgment_count"] != len(config["model_conditions"]) * frozen[
        "grounded_target_count"
    ]:
        raise ValueError("V49 expected judgment count mismatch")
    if any(
        config[key]
        for key in (
            "prompt_or_parser_tuning_after_run_authorized",
            "fresh_holdout_claim_authorized",
            "runtime_change_authorized",
            "shadow_integration_authorized",
            "physical_vrm_execution_enabled",
        )
    ):
        raise ValueError("V49 development cannot pre-authorize integration")


def _model_inventory(config):
    with urllib.request.urlopen(
        "http://127.0.0.1:11434/api/tags", timeout=30
    ) as response:
        inventory = {row["name"]: row for row in json.load(response).get("models") or []}
    snapshots = {}
    for frozen in config["model_conditions"]:
        actual = inventory.get(frozen["ollama_tag"])
        if not actual or actual.get("digest") != frozen["digest"]:
            raise ValueError(f"V49 model missing or changed: {frozen['ollama_tag']}")
        if actual.get("size") != frozen["blob_bytes"]:
            raise ValueError(f"V49 model size mismatch: {frozen['ollama_tag']}")
        snapshots[frozen["condition"]] = {
            "model_tag": frozen["ollama_tag"],
            "digest": actual.get("digest"),
            "size": actual.get("size"),
            "details": actual.get("details") or {},
            "thinking": config["fixed_generation"]["thinking"],
        }
    return snapshots


def build_prompt(config):
    schema_text = json.dumps(
        config["binary_contract"], ensure_ascii=False, sort_keys=True
    )
    return (
        config["binary_gate_instruction"]
        + "\n\nExact output schema:\n"
        + schema_text
    )


def build_candidate_rows(dataset):
    ontology = load_v47_anchor_ontology()
    return [
        {
            "case_id": case["id"],
            "family": case["family"],
            "user_input": case["user_input"],
            "candidates": ground_supported_targets(case["user_input"], ontology),
        }
        for case in dataset["cases"]
    ]


def _run_judgment(
    condition,
    candidate_row,
    candidate,
    prompt,
    config,
    v45_config,
    snapshot,
):
    payload = build_binary_gate_payload(
        candidate_row["user_input"],
        candidate,
        candidate_row["candidates"],
        v45_config["deterministic_discourse_signals"]["patterns"],
        config["payload_fields"],
    )
    messages = [
        {"role": "system", "content": prompt},
        {
            "role": "user",
            "content": json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        },
    ]
    frozen = config["fixed_generation"]
    options = {
        "temperature": frozen["temperature"],
        "top_p": frozen["top_p"],
        "seed": frozen["seed"],
        "num_ctx": frozen["context_tokens"],
        "num_predict": frozen["maximum_output_tokens"],
    }
    model_info = {
        "condition": condition,
        "model_tag": snapshot["model_tag"],
        "blob_bytes": snapshot["size"],
        "thinking": snapshot["thinking"],
    }
    body = _chat_body(model_info, messages, options=options)
    body["format"] = config["binary_contract"]
    response, elapsed, attempts, errors = _call_ollama(body)
    return {
        "response_message": response.get("message") or {},
        "parsed": parse_binary_gate_response(response),
        "response_metrics": _response_metrics(response, elapsed),
        "transport_attempts": attempts,
        "prior_transport_errors": errors,
    }


def _report_checks(config, prompt):
    return {
        "runner_commit": _git_head(),
        "preregistration_sha256": _sha256(CONFIG_PATH),
        "dataset_sha256": _sha256(DATASET_PATH),
        "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
        "model_condition_order": [
            row["condition"] for row in config["model_conditions"]
        ],
    }


def _load_or_create(output, config, prompt, snapshots, candidate_rows):
    checks = _report_checks(config, prompt)
    if output.exists():
        report = json.loads(output.read_text(encoding="utf-8"))
        for field, expected in checks.items():
            if report.get(field) != expected:
                raise ValueError(f"Existing V49 report {field} mismatch")
        return report
    return {
        "schema": "uruha_binary_execution_gate_development_raw_v49",
        "evidence_status": "development_only_on_retired_v45_holdout",
        "started_at": _now(),
        "completed_at": None,
        **checks,
        "model_snapshots": snapshots,
        "candidate_rows": candidate_rows,
        "judgment_rows": [],
    }


def run(output=DEFAULT_OUTPUT):
    load = lambda path: json.loads(path.read_text(encoding="utf-8"))
    config = load(CONFIG_PATH)
    v45_config = load(V45_CONFIG_PATH)
    dataset = load(DATASET_PATH)
    _validate_inputs(config, dataset)
    snapshots = _model_inventory(config)
    prompt = build_prompt(config)
    candidate_rows = build_candidate_rows(dataset)
    target_count = sum(len(row["candidates"]) for row in candidate_rows)
    if target_count != config["frozen_inputs"]["grounded_target_count"]:
        raise ValueError("V49 grounded candidate count drift")
    report = _load_or_create(output, config, prompt, snapshots, candidate_rows)
    completed = {
        (row["condition"], row["case_id"], row["target_id"])
        for row in report["judgment_rows"]
    }
    total = config["expected_judgment_count"]
    for model in config["model_conditions"]:
        condition = model["condition"]
        snapshot = snapshots[condition]
        for candidate_row in candidate_rows:
            for candidate in candidate_row["candidates"]:
                key = (condition, candidate_row["case_id"], candidate["target_id"])
                if key in completed:
                    continue
                report["judgment_rows"].append(
                    {
                        "condition": condition,
                        "case_id": candidate_row["case_id"],
                        "target_id": candidate["target_id"],
                        "result": _run_judgment(
                            condition,
                            candidate_row,
                            candidate,
                            prompt,
                            config,
                            v45_config,
                            snapshot,
                        ),
                    }
                )
                _atomic_write(output, report)
                print(
                    f"[v49 {len(report['judgment_rows'])}/{total}] "
                    f"{condition} {candidate_row['case_id']} {candidate['target_id']}",
                    flush=True,
                )
        _unload_model(snapshot["model_tag"])
    if len(report["judgment_rows"]) == total:
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
                "rows": len(report["judgment_rows"]),
                "completed_at": report["completed_at"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
