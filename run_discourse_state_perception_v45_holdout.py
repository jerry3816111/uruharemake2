#!/usr/bin/env python3
"""Run the frozen V44 control and V45 candidate on the fresh V45 holdout."""

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
from grounded_commitment_classifier_v42 import ground_supported_targets
from grounded_frame_isolation_v39 import load_v39_anchor_ontology
from run_commitment_target_isolation_v44 import (
    _user_payload as v44_user_payload,
    build_system_prompts as build_v44_system_prompts,
)
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


ROOT = Path(__file__).resolve().parent
LOCK_PATH = ROOT / "configs" / "discourse_state_perception_v45_holdout_lock.json"
V45_CONFIG_PATH = ROOT / "configs" / "discourse_state_perception_v45_preregistration.json"
V44_LOCK_PATH = ROOT / "configs" / "commitment_target_isolation_v44_semantic_lock.json"
DATASET_PATH = ROOT / "datasets" / "discourse_state_perception_v45_holdout.json"
AUDIT_PATH = ROOT / "reports" / "discourse_state_perception_v45_holdout_audit.json"
DEFAULT_OUTPUT = ROOT / "reports" / "discourse_state_perception_v45_holdout_raw.json"
TZ = ZoneInfo("Asia/Tokyo")
CONDITIONS = ("v44_scope_control", "v45_discourse_candidate")


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


def _validate_hash_section(section, path_key_suffix="_sha256"):
    for key, expected in section.items():
        if not key.endswith(path_key_suffix):
            continue
        path_key = key.removesuffix(path_key_suffix)
        path_value = section.get(path_key)
        if not path_value:
            continue
        path = ROOT / path_value
        if _sha256(path) != expected:
            raise ValueError(f"V45 holdout frozen hash mismatch: {path.name}")


def _validate_inputs(lock, v45_config, dataset, audit):
    _validate_hash_section(lock["authorization_provenance"])
    _validate_hash_section(lock["frozen_implementations"])
    _validate_hash_section(lock["frozen_holdout"])
    if not lock["authorization_provenance"]["development_gate_passed"]:
        raise ValueError("V45 development did not authorize a holdout")
    if not lock["frozen_holdout"]["construction_gate_passed"]:
        raise ValueError("V45 holdout construction gate failed")
    if audit["model_inference_used"]:
        raise ValueError("V45 construction audit must not use model inference")
    if dataset["case_count"] != lock["frozen_holdout"]["case_count"]:
        raise ValueError("V45 holdout case count mismatch")
    if audit["case_count"] != dataset["case_count"]:
        raise ValueError("V45 holdout audit case count mismatch")
    if audit["candidate_target_count"] != 63:
        raise ValueError("V45 frozen holdout candidate count mismatch")
    if lock["holdout_has_been_observed_by_model"]:
        raise ValueError("V45 holdout lock says the model has already observed the holdout")
    if any(
        lock[key]
        for key in (
            "runtime_change_authorized",
            "shadow_integration_authorized",
            "physical_vrm_execution_enabled",
        )
    ):
        raise ValueError("V45 holdout cannot start with integration already authorized")
    generation = lock["fixed_model_and_generation"]
    frozen = v45_config["frozen_model"]
    expected_pairs = {
        "ollama_tag": "ollama_tag",
        "digest": "digest",
        "thinking": "thinking",
        "temperature": "temperature",
        "top_p": "top_p",
        "seed": "seed",
        "context_tokens": "context_tokens",
        "maximum_output_tokens": "maximum_output_tokens",
    }
    for holdout_key, development_key in expected_pairs.items():
        if generation[holdout_key] != frozen[development_key]:
            raise ValueError(f"V45 holdout generation drift: {holdout_key}")
    if generation["carrier"] != v45_config["fixed_carrier"]:
        raise ValueError("V45 holdout carrier drift")


def _model_snapshot(lock):
    frozen = lock["fixed_model_and_generation"]
    with urllib.request.urlopen(
        "http://127.0.0.1:11434/api/tags", timeout=30
    ) as response:
        inventory = {row["name"]: row for row in json.load(response).get("models") or []}
    actual = inventory.get(frozen["ollama_tag"])
    if not actual or actual.get("digest") != frozen["digest"]:
        raise ValueError("V45 holdout fixed model missing or digest mismatch")
    return {
        "model_tag": frozen["ollama_tag"],
        "digest": actual.get("digest"),
        "size": actual.get("size"),
        "details": actual.get("details") or {},
        "thinking": frozen["thinking"],
    }


def build_matched_prompts(v45_config, v44_lock):
    return {
        "v44_scope_control": build_v44_system_prompts(v44_lock)[
            "isolated_scope_signals_candidate"
        ],
        "v45_discourse_candidate": build_v45_system_prompts(v45_config, v44_lock)[
            "taxonomy_plus_discourse_signals_candidate"
        ],
    }


def build_candidate_rows(dataset):
    ontology = load_v39_anchor_ontology()
    return [
        {
            "case_id": case["id"],
            "family": case["family"],
            "user_input": case["user_input"],
            "candidates": ground_supported_targets(case["user_input"], ontology),
        }
        for case in dataset["cases"]
    ]


def build_user_payload(condition, candidate_row, candidate, v45_config):
    if condition == "v44_scope_control":
        return v44_user_payload(
            "isolated_scope_signals_candidate", candidate_row, candidate
        )
    if condition == "v45_discourse_candidate":
        return v45_user_payload(
            "taxonomy_plus_discourse_signals_candidate",
            candidate_row,
            candidate,
            v45_config,
        )
    raise ValueError(f"Unknown V45 holdout condition: {condition}")


def _run_judgment(
    condition, candidate_row, candidate, prompts, lock, v45_config, snapshot
):
    payload = build_user_payload(condition, candidate_row, candidate, v45_config)
    messages = [
        {"role": "system", "content": prompts[condition]},
        {
            "role": "user",
            "content": json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        },
    ]
    frozen = lock["fixed_model_and_generation"]
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
    carrier = frozen["carrier"]
    body["format"] = SCHEMAS[carrier]
    response, elapsed, attempts, errors = _call_ollama(body)
    return {
        "response_message": response.get("message") or {},
        "parsed": parse_carrier_response(carrier, response),
        "response_metrics": _response_metrics(response, elapsed),
        "transport_attempts": attempts,
        "prior_transport_errors": errors,
    }


def _report_checks(prompts):
    return {
        "runner_commit": _git_head(),
        "holdout_lock_sha256": _sha256(LOCK_PATH),
        "dataset_sha256": _sha256(DATASET_PATH),
        "construction_audit_sha256": _sha256(AUDIT_PATH),
        "prompt_sha256": {
            condition: hashlib.sha256(prompt.encode()).hexdigest()
            for condition, prompt in prompts.items()
        },
    }


def _load_or_create(output, prompts, snapshot, candidate_rows, lock):
    checks = _report_checks(prompts)
    if output.exists():
        report = json.loads(output.read_text(encoding="utf-8"))
        for field, expected in checks.items():
            if report.get(field) != expected:
                raise ValueError(f"Existing V45 holdout report {field} mismatch")
        return report
    return {
        "schema": "uruha_discourse_state_perception_holdout_raw_v45",
        "evidence_status": "fresh_frozen_matched_holdout",
        "started_at": _now(),
        "completed_at": None,
        **checks,
        "conditions": list(CONDITIONS),
        "selected_carrier": lock["fixed_model_and_generation"]["carrier"],
        "model_snapshot": snapshot,
        "candidate_rows": candidate_rows,
        "judgment_rows": [],
    }


def run(output=DEFAULT_OUTPUT):
    load = lambda path: json.loads(path.read_text(encoding="utf-8"))
    lock = load(LOCK_PATH)
    v45_config = load(V45_CONFIG_PATH)
    v44_lock = load(V44_LOCK_PATH)
    dataset = load(DATASET_PATH)
    audit = load(AUDIT_PATH)
    _validate_inputs(lock, v45_config, dataset, audit)
    snapshot = _model_snapshot(lock)
    prompts = build_matched_prompts(v45_config, v44_lock)
    candidate_rows = build_candidate_rows(dataset)
    candidate_count = sum(len(row["candidates"]) for row in candidate_rows)
    if candidate_count != audit["candidate_target_count"]:
        raise ValueError("V45 holdout grounded candidate count drift")
    report = _load_or_create(output, prompts, snapshot, candidate_rows, lock)
    completed = {
        (row["condition"], row["case_id"], row["target_id"])
        for row in report["judgment_rows"]
    }
    total = len(CONDITIONS) * candidate_count
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
                            prompts,
                            lock,
                            v45_config,
                            snapshot,
                        ),
                    }
                )
                _atomic_write(output, report)
                print(
                    f"[v45 holdout {len(report['judgment_rows'])}/{total}] "
                    f"{condition} {candidate_row['case_id']} {candidate['target_id']}",
                    flush=True,
                )
    if len(report["judgment_rows"]) == total:
        report["completed_at"] = _now()
    _atomic_write(output, report)
    _unload_model(snapshot["model_tag"])
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
