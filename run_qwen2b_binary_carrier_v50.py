#!/usr/bin/env python3
"""Run the frozen non-semantic V50 Qwen2B carrier compatibility probe."""

import argparse
import hashlib
import json
import os
import subprocess
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from qwen2b_binary_carrier_v50 import carrier_instruction, parse_carrier_response
from run_rightbrain_qwen35_migration_v33 import (
    _call_ollama,
    _chat_body,
    _response_metrics,
    _unload_model,
)


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "qwen2b_binary_carrier_v50_preregistration.json"
DATASET_PATH = ROOT / "datasets" / "qwen2b_binary_carrier_v50_format_probe.json"
DEFAULT_OUTPUT = ROOT / "reports" / "qwen2b_binary_carrier_v50_probe_raw.json"
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
    for key, expected in config["frozen_inputs"].items():
        if key.endswith("_sha256"):
            path = ROOT / config["frozen_inputs"][key.removesuffix("_sha256")]
            if _sha256(path) != expected:
                raise ValueError(f"V50 frozen input hash mismatch: {path.name}")
    if dataset["case_count"] != config["frozen_inputs"]["format_probe_case_count"]:
        raise ValueError("V50 probe case count mismatch")
    if config["expected_scored_call_count"] != len(config["carrier_order"]) * dataset[
        "case_count"
    ]:
        raise ValueError("V50 expected call count mismatch")
    if any(
        config[key]
        for key in (
            "semantic_prompt_tuning_authorized",
            "v51_fresh_holdout_construction_authorized",
            "runtime_change_authorized",
            "shadow_integration_authorized",
            "physical_vrm_execution_enabled",
        )
    ):
        raise ValueError("V50 probe cannot pre-authorize later stages")


def _model_snapshot(config):
    frozen = config["frozen_model"]
    with urllib.request.urlopen(
        "http://127.0.0.1:11434/api/tags", timeout=30
    ) as response:
        inventory = {row["name"]: row for row in json.load(response).get("models") or []}
    actual = inventory.get(frozen["ollama_tag"])
    if not actual or actual.get("digest") != frozen["digest"]:
        raise ValueError("V50 fixed Qwen2B model missing or changed")
    if actual.get("size") != frozen["blob_bytes"]:
        raise ValueError("V50 fixed Qwen2B model size mismatch")
    return {
        "model_tag": frozen["ollama_tag"],
        "digest": actual.get("digest"),
        "size": actual.get("size"),
        "details": actual.get("details") or {},
        "thinking": frozen["thinking"],
    }


def _options(config):
    fixed = config["fixed_generation"]
    return {
        "temperature": fixed["temperature"],
        "top_p": fixed["top_p"],
        "seed": fixed["seed"],
        "num_ctx": fixed["context_tokens"],
        "num_predict": fixed["maximum_output_tokens"],
    }


def _call_carrier(carrier, case, config, snapshot):
    messages = [
        {"role": "system", "content": carrier_instruction(config, carrier)},
        {
            "role": "user",
            "content": json.dumps(
                {"nonce": case["nonce"], "source_decision": case["source_decision"]},
                separators=(",", ":"),
            ),
        },
    ]
    model_info = {
        "condition": f"qwen3_5_2b_v50_{carrier}",
        "model_tag": snapshot["model_tag"],
        "blob_bytes": snapshot["size"],
        "thinking": snapshot["thinking"],
    }
    body = _chat_body(model_info, messages, options=_options(config))
    body["format"] = config["carriers"][carrier]["schema"]
    response, elapsed, attempts, errors = _call_ollama(body)
    return {
        "response_message": response.get("message") or {},
        "parsed": parse_carrier_response(config, carrier, response),
        "response_metrics": _response_metrics(response, elapsed),
        "transport_attempts": attempts,
        "prior_transport_errors": errors,
    }


def _report_checks(config):
    return {
        "runner_commit": _git_head(),
        "preregistration_sha256": _sha256(CONFIG_PATH),
        "dataset_sha256": _sha256(DATASET_PATH),
        "carrier_instruction_sha256": {
            carrier: hashlib.sha256(
                carrier_instruction(config, carrier).encode()
            ).hexdigest()
            for carrier in config["carrier_order"]
        },
    }


def run(output=DEFAULT_OUTPUT):
    if output.exists():
        raise ValueError("V50 carrier probe is frozen and cannot overwrite a report")
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    dataset = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    _validate_inputs(config, dataset)
    snapshot = _model_snapshot(config)
    report = {
        "schema": "uruha_qwen2b_binary_carrier_probe_raw_v50",
        "evidence_status": "frozen_nonsemantic_qwen2b_format_probe",
        "started_at": _now(),
        "completed_at": None,
        **_report_checks(config),
        "model_snapshot": snapshot,
        "warmup_rows": [],
        "probe_rows": [],
    }
    total = config["expected_scored_call_count"]
    for carrier in config["carrier_order"]:
        _unload_model(snapshot["model_tag"])
        warmup = _call_carrier(carrier, dataset["cases"][0], config, snapshot)
        report["warmup_rows"].append({"carrier": carrier, "result": warmup})
        for case in dataset["cases"]:
            result = _call_carrier(carrier, case, config, snapshot)
            report["probe_rows"].append(
                {
                    "carrier": carrier,
                    "case_id": case["id"],
                    "source_decision": case["source_decision"],
                    "result": result,
                }
            )
            _atomic_write(output, report)
            print(
                f"[v50 {len(report['probe_rows'])}/{total}] {carrier} {case['id']}",
                flush=True,
            )
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
            {"rows": len(report["probe_rows"]), "completed_at": report["completed_at"]},
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
