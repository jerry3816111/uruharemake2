#!/usr/bin/env python3
"""Run the preregistered V46 local-model capacity development sweep."""

import argparse
import hashlib
import json
import os
import subprocess
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from commitment_carrier_v44 import SCHEMAS, parse_carrier_response
from run_discourse_state_perception_v45 import (
    _user_payload as v45_user_payload,
    build_system_prompts as build_v45_system_prompts,
)
from run_discourse_state_perception_v45_holdout import build_candidate_rows
from run_rightbrain_qwen35_migration_v33 import (
    _call_ollama,
    _chat_body,
    _response_metrics,
    _unload_model,
)


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "commitment_model_capacity_v46_preregistration.json"
V45_CONFIG_PATH = ROOT / "configs" / "discourse_state_perception_v45_preregistration.json"
V44_LOCK_PATH = ROOT / "configs" / "commitment_target_isolation_v44_semantic_lock.json"
DATASET_PATH = ROOT / "datasets" / "discourse_state_perception_v45_holdout.json"
AUDIT_PATH = ROOT / "reports" / "discourse_state_perception_v45_holdout_audit.json"
DEFAULT_OUTPUT = ROOT / "reports" / "commitment_model_capacity_v46_development_raw.json"
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


def _validate_inputs(config, dataset, audit):
    frozen = config["frozen_retired_development_inputs"]
    for key, expected in frozen.items():
        if not key.endswith("_sha256"):
            continue
        path = ROOT / frozen[key.removesuffix("_sha256")]
        if _sha256(path) != expected:
            raise ValueError(f"V46 frozen development hash mismatch: {path.name}")
    if dataset["case_count"] != frozen["case_count"]:
        raise ValueError("V46 retired development case count mismatch")
    if audit["candidate_target_count"] != frozen["candidate_target_count"]:
        raise ValueError("V46 candidate target count mismatch")
    if audit["supported_expected_target_count"] != frozen["supported_target_count"]:
        raise ValueError("V46 supported target count mismatch")
    if config["expected_judgment_count"] != len(config["model_conditions"]) * audit[
        "candidate_target_count"
    ]:
        raise ValueError("V46 expected judgment count mismatch")
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
        raise ValueError("V46 development cannot start with integration authorized")


def _model_inventory(config):
    with urllib.request.urlopen(
        "http://127.0.0.1:11434/api/tags", timeout=30
    ) as response:
        inventory = {row["name"]: row for row in json.load(response).get("models") or []}
    snapshots = {}
    for frozen in config["model_conditions"]:
        actual = inventory.get(frozen["ollama_tag"])
        if not actual or actual.get("digest") != frozen["digest"]:
            raise ValueError(f"V46 fixed model missing or digest mismatch: {frozen['ollama_tag']}")
        if actual.get("size") != frozen["blob_bytes"]:
            raise ValueError(f"V46 fixed model size mismatch: {frozen['ollama_tag']}")
        snapshots[frozen["condition"]] = {
            "model_tag": frozen["ollama_tag"],
            "digest": actual.get("digest"),
            "size": actual.get("size"),
            "details": actual.get("details") or {},
            "thinking": config["fixed_generation"]["thinking"],
        }
    return snapshots


def build_prompt(config, v45_config, v44_lock):
    condition = config["fixed_generation"]["prompt_condition"]
    return build_v45_system_prompts(v45_config, v44_lock)[condition]


def build_user_payload(config, v45_config, candidate_row, candidate):
    return v45_user_payload(
        config["fixed_generation"]["prompt_condition"],
        candidate_row,
        candidate,
        v45_config,
    )


def _run_judgment(
    model_condition, candidate_row, candidate, prompt, config, v45_config, snapshot
):
    payload = build_user_payload(config, v45_config, candidate_row, candidate)
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
        "condition": model_condition,
        "model_tag": snapshot["model_tag"],
        "blob_bytes": snapshot["size"],
        "thinking": snapshot["thinking"],
    }
    body = _chat_body(model_info, messages, options=options)
    body["format"] = SCHEMAS[frozen["carrier"]]
    response, elapsed, attempts, errors = _call_ollama(body)
    return {
        "response_message": response.get("message") or {},
        "parsed": parse_carrier_response(frozen["carrier"], response),
        "response_metrics": _response_metrics(response, elapsed),
        "transport_attempts": attempts,
        "prior_transport_errors": errors,
    }


def _report_checks(config, prompt):
    return {
        "runner_commit": _git_head(),
        "preregistration_sha256": _sha256(CONFIG_PATH),
        "dataset_sha256": _sha256(DATASET_PATH),
        "candidate_audit_sha256": _sha256(AUDIT_PATH),
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
                raise ValueError(f"Existing V46 report {field} mismatch")
        return report
    return {
        "schema": "uruha_commitment_model_capacity_development_raw_v46",
        "evidence_status": "development_only_on_retired_v45_holdout",
        "started_at": _now(),
        "completed_at": None,
        **checks,
        "selected_carrier": config["fixed_generation"]["carrier"],
        "model_snapshots": snapshots,
        "candidate_rows": candidate_rows,
        "judgment_rows": [],
    }


def run(output=DEFAULT_OUTPUT):
    load = lambda path: json.loads(path.read_text(encoding="utf-8"))
    config = load(CONFIG_PATH)
    v45_config = load(V45_CONFIG_PATH)
    v44_lock = load(V44_LOCK_PATH)
    dataset = load(DATASET_PATH)
    audit = load(AUDIT_PATH)
    _validate_inputs(config, dataset, audit)
    snapshots = _model_inventory(config)
    prompt = build_prompt(config, v45_config, v44_lock)
    candidate_rows = build_candidate_rows(dataset)
    if sum(len(row["candidates"]) for row in candidate_rows) != audit[
        "candidate_target_count"
    ]:
        raise ValueError("V46 grounded candidate count drift")
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
                    f"[v46 {len(report['judgment_rows'])}/{total}] "
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
