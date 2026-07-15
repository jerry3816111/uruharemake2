#!/usr/bin/env python3
"""Run the frozen non-semantic V44 carrier compatibility probe."""

import argparse
import hashlib
import json
import os
import subprocess
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from commitment_carrier_v44 import (
    CARRIERS,
    SCHEMAS,
    TOOL,
    carrier_instruction,
    parse_carrier_response,
)
from run_rightbrain_qwen35_migration_v33 import (
    _call_ollama,
    _chat_body,
    _response_metrics,
    _unload_model,
)


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "commitment_carrier_target_isolation_v44_preregistration.json"
DATASET_PATH = ROOT / "datasets" / "commitment_carrier_v44_format_probe.json"
DEFAULT_OUTPUT = ROOT / "reports" / "commitment_carrier_v44_probe_raw.json"
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
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    os.replace(temporary, path)


def _model_snapshot(config):
    frozen = config["frozen_environment"]
    with urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=30) as response:
        inventory = {row["name"]: row for row in json.load(response).get("models") or []}
    actual = inventory.get(frozen["model"])
    if not actual or actual.get("digest") != frozen["model_digest"]:
        raise ValueError("V44 fixed model missing or digest mismatch")
    return {
        "model_tag": frozen["model"],
        "digest": actual.get("digest"),
        "size": actual.get("size"),
        "details": actual.get("details") or {},
        "thinking": frozen["thinking"],
    }


def _validate_inputs(config, dataset):
    frozen = config["frozen_inputs"]
    for key, expected in frozen.items():
        if not key.endswith("_sha256"):
            continue
        path = ROOT / frozen[key.removesuffix("_sha256")]
        if _sha256(path) != expected:
            raise ValueError(f"V44 frozen input hash mismatch: {path.name}")
    if dataset["case_count"] != frozen["format_probe_case_count"]:
        raise ValueError("V44 format probe count mismatch")
    if any(
        config[key]
        for key in (
            "runtime_change_authorized",
            "shadow_integration_authorized",
            "physical_vrm_execution_enabled",
        )
    ):
        raise ValueError("V44 probe cannot authorize integration or execution")


def _model_info(snapshot):
    return {
        "condition": "qwen3_5_4b_v44_carrier_probe",
        "model_tag": snapshot["model_tag"],
        "blob_bytes": snapshot["size"],
        "thinking": snapshot["thinking"],
    }


def _options(config):
    frozen = config["frozen_environment"]
    return {
        "temperature": frozen["temperature"],
        "top_p": frozen["top_p"],
        "seed": frozen["seed"],
        "num_ctx": frozen["context_tokens"],
        "num_predict": frozen["maximum_output_tokens"],
    }


def _call_carrier(carrier, case, config, snapshot):
    messages = [
        {"role": "system", "content": carrier_instruction(carrier)},
        {
            "role": "user",
            "content": json.dumps(
                {"nonce": case["nonce"], "source_label": case["source_label"]},
                ensure_ascii=False,
                separators=(",", ":"),
            ),
        },
    ]
    tools = [TOOL] if carrier == "tool_call_schema" else None
    body = _chat_body(_model_info(snapshot), messages, options=_options(config), tools=tools)
    if carrier != "tool_call_schema":
        body["format"] = SCHEMAS[carrier]
    response, elapsed, attempts, errors = _call_ollama(body)
    return {
        "response_message": response.get("message") or {},
        "parsed": parse_carrier_response(carrier, response),
        "response_metrics": _response_metrics(response, elapsed),
        "transport_attempts": attempts,
        "prior_transport_errors": errors,
    }


def _report_checks():
    return {
        "runner_commit": _git_head(),
        "preregistration_sha256": _sha256(CONFIG_PATH),
        "dataset_sha256": _sha256(DATASET_PATH),
        "carrier_instruction_sha256": {
            carrier: hashlib.sha256(carrier_instruction(carrier).encode()).hexdigest()
            for carrier in CARRIERS
        },
    }


def run(output=DEFAULT_OUTPUT):
    if output.exists():
        raise ValueError("V44 format probe is frozen and must not overwrite an existing report")
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    dataset = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    _validate_inputs(config, dataset)
    snapshot = _model_snapshot(config)
    report = {
        "schema": "uruha_commitment_carrier_probe_raw_v44",
        "evidence_status": "frozen_nonsemantic_format_probe",
        "started_at": _now(),
        "completed_at": None,
        **_report_checks(),
        "model_snapshot": snapshot,
        "warmup_rows": [],
        "probe_rows": [],
    }
    total = len(CARRIERS) * dataset["case_count"]
    for carrier in CARRIERS:
        _unload_model(snapshot["model_tag"])
        warmup = _call_carrier(carrier, dataset["cases"][0], config, snapshot)
        report["warmup_rows"].append({"carrier": carrier, "result": warmup})
        for case in dataset["cases"]:
            result = _call_carrier(carrier, case, config, snapshot)
            report["probe_rows"].append(
                {
                    "carrier": carrier,
                    "case_id": case["id"],
                    "source_label": case["source_label"],
                    "result": result,
                }
            )
            _atomic_write(output, report)
            print(f"[v44 carrier {len(report['probe_rows'])}/{total}] {carrier} {case['id']}", flush=True)
    report["completed_at"] = _now()
    _atomic_write(output, report)
    _unload_model(snapshot["model_tag"])
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    report = run(args.output)
    print(json.dumps({"rows": len(report["probe_rows"]), "completed_at": report["completed_at"]}, indent=2))


if __name__ == "__main__":
    main()
