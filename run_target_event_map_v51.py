#!/usr/bin/env python3
"""Run the preregistered V51 target-event-map development comparison."""

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
from commitment_carrier_v44 import SCHEMAS, parse_carrier_response
from grounded_commitment_classifier_v42 import ground_supported_targets
from run_discourse_state_perception_v45 import (
    _user_payload as v45_user_payload,
    build_system_prompts as build_v45_system_prompts,
)
from run_rightbrain_qwen35_migration_v33 import (
    _call_ollama,
    _chat_body,
    _response_metrics,
    _unload_model,
)
from target_event_map_v51 import build_target_event_map


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "target_event_map_v51_preregistration.json"
V45_CONFIG_PATH = ROOT / "configs" / "discourse_state_perception_v45_preregistration.json"
V44_LOCK_PATH = ROOT / "configs" / "commitment_target_isolation_v44_semantic_lock.json"
DATASET_PATH = ROOT / "datasets" / "discourse_state_perception_v45_holdout.json"
DEFAULT_OUTPUT = ROOT / "reports" / "target_event_map_v51_development_raw.json"
CONDITIONS = ("v48_six_way_control", "target_event_map_candidate")
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
                raise ValueError(f"V51 frozen input hash mismatch: {path.name}")
    if list(config["conditions"]) != list(CONDITIONS):
        raise ValueError("V51 condition order mismatch")
    if dataset["case_count"] != frozen["case_count"]:
        raise ValueError("V51 retired development case count mismatch")
    if config["expected_judgment_count"] != (
        len(CONDITIONS) * frozen["grounded_target_count"]
    ):
        raise ValueError("V51 expected judgment count mismatch")
    if any(
        config[key]
        for key in (
            "prompt_or_map_tuning_after_run_authorized",
            "fresh_holdout_claim_authorized",
            "runtime_change_authorized",
            "shadow_integration_authorized",
            "physical_vrm_execution_enabled",
            "human_likeness_claim_authorized",
        )
    ):
        raise ValueError("V51 development cannot start with advancement authorized")


def _model_snapshot(config):
    frozen = config["fixed_model"]
    with urllib.request.urlopen(
        "http://127.0.0.1:11434/api/tags", timeout=30
    ) as response:
        inventory = {
            row["name"]: row for row in json.load(response).get("models") or []
        }
    actual = inventory.get(frozen["ollama_tag"])
    if not actual or actual.get("digest") != frozen["digest"]:
        raise ValueError("V51 fixed Qwen3.5 4B model missing or digest mismatch")
    if actual.get("size") != frozen["blob_bytes"]:
        raise ValueError("V51 fixed model blob size mismatch")
    return {
        "model_tag": frozen["ollama_tag"],
        "digest": actual.get("digest"),
        "size": actual.get("size"),
        "details": actual.get("details") or {},
        "thinking": frozen["thinking"],
    }


def build_prompts(config, v45_config, v44_lock):
    control = build_v45_system_prompts(v45_config, v44_lock)[
        "taxonomy_plus_discourse_signals_candidate"
    ]
    return {
        "v48_six_way_control": control,
        "target_event_map_candidate": "\n\n".join(
            [control, config["causal_change"]["candidate_instruction"]]
        ),
    }


def build_candidate_rows(dataset):
    ontology = load_v47_anchor_ontology()
    return [
        {
            "case_id": case["id"],
            "user_input": case["user_input"],
            "candidates": ground_supported_targets(case["user_input"], ontology),
        }
        for case in dataset["cases"]
    ]


def build_user_payload(condition, candidate_row, candidate, config, v45_config):
    payload = v45_user_payload(
        "taxonomy_plus_discourse_signals_candidate",
        candidate_row,
        candidate,
        v45_config,
    )
    if condition == "target_event_map_candidate":
        payload["target_event_map"] = build_target_event_map(
            candidate_row["user_input"],
            candidate_row["candidates"],
            candidate["target_id"],
        )
    elif condition != "v48_six_way_control":
        raise ValueError(f"Unknown V51 condition: {condition}")
    forbidden = set(config["causal_change"]["forbidden_fields"])
    if forbidden.intersection(payload):
        raise ValueError("V51 payload contains a forbidden answer field")
    return payload


def _run_judgment(
    condition, candidate_row, candidate, config, v45_config, prompts, snapshot
):
    payload = build_user_payload(
        condition, candidate_row, candidate, config, v45_config
    )
    messages = [
        {"role": "system", "content": prompts[condition]},
        {
            "role": "user",
            "content": json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        },
    ]
    frozen = config["fixed_model"]
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
    body["format"] = SCHEMAS[config["fixed_carrier"]]
    response, elapsed, attempts, errors = _call_ollama(body)
    return {
        "response_message": response.get("message") or {},
        "parsed": parse_carrier_response(config["fixed_carrier"], response),
        "response_metrics": _response_metrics(response, elapsed),
        "transport_attempts": attempts,
        "prior_transport_errors": errors,
    }


def _checks(prompts):
    return {
        "runner_commit": _git_head(),
        "preregistration_sha256": _sha256(CONFIG_PATH),
        "dataset_sha256": _sha256(DATASET_PATH),
        "prompt_sha256": {
            condition: hashlib.sha256(prompt.encode()).hexdigest()
            for condition, prompt in prompts.items()
        },
    }


def _load_or_create(output, config, prompts, snapshot, candidate_rows):
    checks = _checks(prompts)
    if output.exists():
        report = json.loads(output.read_text(encoding="utf-8"))
        for field, expected in checks.items():
            if report.get(field) != expected:
                raise ValueError(f"Existing V51 report {field} mismatch")
        return report
    return {
        "schema": "uruha_target_event_map_development_raw_v51",
        "evidence_status": "development_only_on_retired_v45_holdout",
        "started_at": _now(),
        "completed_at": None,
        **checks,
        "conditions": list(CONDITIONS),
        "selected_carrier": config["fixed_carrier"],
        "model_snapshot": snapshot,
        "candidate_rows": candidate_rows,
        "judgment_rows": [],
    }


def run(output=DEFAULT_OUTPUT):
    load = lambda path: json.loads(path.read_text(encoding="utf-8"))
    config = load(CONFIG_PATH)
    v45_config = load(V45_CONFIG_PATH)
    v44_lock = load(V44_LOCK_PATH)
    dataset = load(DATASET_PATH)
    _validate_inputs(config, dataset)
    snapshot = _model_snapshot(config)
    prompts = build_prompts(config, v45_config, v44_lock)
    candidate_rows = build_candidate_rows(dataset)
    target_count = sum(len(row["candidates"]) for row in candidate_rows)
    if target_count != config["frozen_inputs"]["grounded_target_count"]:
        raise ValueError("V51 grounded candidate count drift")
    report = _load_or_create(output, config, prompts, snapshot, candidate_rows)
    completed = {
        (row["condition"], row["case_id"], row["target_id"])
        for row in report["judgment_rows"]
    }
    total = config["expected_judgment_count"]
    for condition in CONDITIONS:
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
                            config,
                            v45_config,
                            prompts,
                            snapshot,
                        ),
                    }
                )
                _atomic_write(output, report)
                print(
                    f"[v51 {len(report['judgment_rows'])}/{total}] "
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
