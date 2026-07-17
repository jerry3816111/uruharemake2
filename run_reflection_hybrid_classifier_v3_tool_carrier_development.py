#!/usr/bin/env python3
"""Run the frozen native tool-call reflection fallback development pilot."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import uruha_reflection_runtime as reflection
from reflection_hybrid_classifier_v2_core import analyze_condition
from run_reflection_classifier_v1_baseline import git_value, sha256


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = (
    ROOT
    / "configs"
    / "reflection_hybrid_classifier_v3_tool_carrier_development_preregistration.json"
)
LOCK_PATH = (
    ROOT / "configs" / "reflection_hybrid_classifier_v3_tool_carrier_harness_lock.json"
)
V2_RESULT_LOCK_PATH = (
    ROOT / "configs" / "reflection_hybrid_classifier_v2_result_lock.json"
)
DATASET_PATH = ROOT / "datasets" / "reflection_classifier_v1_external_holdout.json"
PRIOR_RESULT_PATH = ROOT / "reports" / "reflection_classifier_v1_external_holdout_analysis.json"
DEFAULT_OUTPUT = (
    ROOT
    / "reports"
    / "reflection_hybrid_classifier_v3_tool_carrier_development_raw.json"
)
TAGS_URL = "http://127.0.0.1:11434/api/tags"
TZ = ZoneInfo("Asia/Tokyo")
CLASSES = {"semantic", "procedural", "interpretive", "none"}


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _atomic_write(path, payload):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    os.replace(temporary, path)


def _post_json(url, body, timeout):
    request = urllib.request.Request(
        url,
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.load(response)


def _get_json(url, timeout=30):
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return json.load(response)


def _ollama_version():
    output = subprocess.check_output(
        ["ollama", "--version"], text=True, stderr=subprocess.STDOUT
    ).strip()
    prefix = "ollama version is "
    if not output.startswith(prefix):
        raise ValueError(f"unexpected Ollama version output: {output}")
    return output.removeprefix(prefix)


def _model_inventory(config):
    actual = {
        row["name"]: row for row in (_get_json(TAGS_URL).get("models") or [])
    }
    snapshots = {}
    for frozen in config["model_search"]["ordered_conditions"]:
        row = actual.get(frozen["model"])
        if not row or row.get("digest") != frozen["digest"]:
            raise ValueError(f"missing or drifted local model: {frozen['model']}")
        snapshots[frozen["model"]] = {
            "digest": row["digest"],
            "size_bytes": row.get("size"),
            "details": row.get("details") or {},
        }
    return snapshots


def _parse_tool_response(response):
    message = response.get("message") or {}
    raw_content = str(message.get("content") or "")
    raw_tool_calls = message.get("tool_calls")
    if not isinstance(raw_tool_calls, list):
        return "none", False, raw_content, raw_tool_calls, "missing_tool_calls"
    if len(raw_tool_calls) != 1:
        return "none", False, raw_content, raw_tool_calls, "tool_call_count"
    function = raw_tool_calls[0].get("function") or {}
    if function.get("name") != "classify_reflection":
        return "none", False, raw_content, raw_tool_calls, "tool_name"
    arguments = function.get("arguments")
    if not isinstance(arguments, dict):
        return "none", False, raw_content, raw_tool_calls, "arguments_type"
    if set(arguments) != {"reflection_type"}:
        return "none", False, raw_content, raw_tool_calls, "argument_keys"
    label = arguments["reflection_type"]
    if label not in CLASSES:
        return "none", False, raw_content, raw_tool_calls, "invalid_label"
    return label, True, raw_content, raw_tool_calls, None


def _call_model(config, model, language, utterance):
    generation = config["generation"]
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": config["system_prompt"]},
            {
                "role": "user",
                "content": json.dumps(
                    {"language": language, "utterance": utterance},
                    ensure_ascii=False,
                    separators=(",", ":"),
                ),
            },
        ],
        "tools": [config["tool_contract"]],
        "stream": False,
        "think": generation["thinking"],
        "keep_alive": generation["keep_alive"],
        "options": {
            "temperature": generation["temperature"],
            "top_p": generation["top_p"],
            "seed": generation["seed"],
            "num_ctx": generation["context_tokens"],
            "num_predict": generation["maximum_output_tokens"],
        },
    }
    errors = []
    for attempt in range(1, generation["transport_attempts"] + 1):
        started = time.perf_counter()
        try:
            response = _post_json(
                generation["endpoint"], body, generation["timeout_seconds"]
            )
            wall = time.perf_counter() - started
            label, parsed, content, tool_calls, parse_error = _parse_tool_response(
                response
            )
            return {
                "observed_type": label,
                "parse_success": parsed,
                "parse_error": parse_error,
                "raw_content": content,
                "raw_tool_calls": tool_calls,
                "wall_seconds": round(wall, 6),
                "transport_attempts": attempt,
                "prior_transport_errors": errors,
                "total_duration_ns": response.get("total_duration"),
                "load_duration_ns": response.get("load_duration"),
                "prompt_eval_count": response.get("prompt_eval_count"),
                "eval_count": response.get("eval_count"),
            }
        except (OSError, TimeoutError, urllib.error.URLError, json.JSONDecodeError) as exc:
            errors.append(f"{type(exc).__name__}: {exc}")
            if attempt < generation["transport_attempts"]:
                time.sleep(attempt)
    raise RuntimeError(f"Ollama request failed for {model}: {' | '.join(errors)}")


def verify(config, lock):
    if git_value("branch", "--show-current") != lock["required_run_branch"]:
        raise ValueError("tool-carrier pilot must run from main")
    if git_value("rev-parse", "HEAD") != git_value(
        "rev-parse", lock["required_head_ref"]
    ):
        raise ValueError("main must match the locked remote ref")
    if git_value("status", "--porcelain", "--untracked-files=no"):
        raise ValueError("tracked worktree must be clean")
    if _ollama_version() != config["local_runtime"]["ollama_version"]:
        raise ValueError("Ollama version drift")
    for key, expected in lock["frozen_artifacts"].items():
        if not key.endswith("_sha256"):
            continue
        path_key = key.removesuffix("_sha256")
        if sha256(ROOT / lock["frozen_artifacts"][path_key]) != expected:
            raise ValueError(f"frozen artifact drift: {path_key}")
    if config["model_inference_before_harness_merge_authorized"]:
        raise ValueError("invalid preregistration inference policy")


def _new_report(config, inventory, rules_predictions):
    return {
        "schema": "uruha_reflection_hybrid_classifier_tool_carrier_development_raw_v3",
        "evidence_status": "development_output_carrier_pilot_no_generalization_claim",
        "started_at": datetime.now(TZ).isoformat(timespec="seconds"),
        "completed_at": None,
        "runner_commit": git_value("rev-parse", "HEAD"),
        "runner_branch": git_value("branch", "--show-current"),
        "ollama_version": _ollama_version(),
        "preregistration_sha256": sha256(CONFIG_PATH),
        "harness_lock_sha256": sha256(LOCK_PATH),
        "v2_result_lock_sha256": sha256(V2_RESULT_LOCK_PATH),
        "dataset_sha256": sha256(DATASET_PATH),
        "prior_result_sha256": sha256(PRIOR_RESULT_PATH),
        "model_inventory": inventory,
        "model_calls": 0,
        "gold_label_passed_to_model": False,
        "rules_predictions": rules_predictions,
        "conditions": [],
        "active_condition": None,
        "selected_model": None,
        "early_stop_triggered": False,
    }


def run(output=DEFAULT_OUTPUT):
    config = _load(CONFIG_PATH)
    lock = _load(LOCK_PATH)
    verify(config, lock)
    dataset = _load(DATASET_PATH)
    prior = _load(PRIOR_RESULT_PATH)
    inventory = _model_inventory(config)
    rules_predictions = {
        case["id"]: reflection.classify_reflection_type(case["text"])
        for case in dataset["cases"]
    }
    prior_predictions = {
        row["id"]: row["candidate_observed_type"]
        for row in prior["matched_result"]["rows"]
    }
    if rules_predictions != prior_predictions:
        raise ValueError("rules-only control no longer reproduces frozen prior result")

    if output.exists():
        report = _load(output)
        for key, expected in {
            "runner_commit": git_value("rev-parse", "HEAD"),
            "ollama_version": _ollama_version(),
            "preregistration_sha256": sha256(CONFIG_PATH),
            "harness_lock_sha256": sha256(LOCK_PATH),
            "v2_result_lock_sha256": sha256(V2_RESULT_LOCK_PATH),
            "dataset_sha256": sha256(DATASET_PATH),
            "prior_result_sha256": sha256(PRIOR_RESULT_PATH),
            "rules_predictions": rules_predictions,
        }.items():
            if report.get(key) != expected:
                raise ValueError(f"resume provenance drift: {key}")
    else:
        report = _new_report(config, inventory, rules_predictions)
        _atomic_write(output, report)

    completed_models = {row["model"] for row in report["conditions"]}
    for model_info in config["model_search"]["ordered_conditions"]:
        model = model_info["model"]
        if model in completed_models:
            existing = next(row for row in report["conditions"] if row["model"] == model)
            if existing["gate_snapshot"]["all_gates_pass"]:
                report["selected_model"] = model
                report["early_stop_triggered"] = True
                break
            continue

        if report.get("active_condition"):
            if report["active_condition"]["model"] != model:
                raise ValueError("resume active model does not match ordered search")
        else:
            report["active_condition"] = {"model": model, "fallback_rows": []}
            _atomic_write(output, report)
        fallback_rows = report["active_condition"]["fallback_rows"]
        completed_case_ids = {row["id"] for row in fallback_rows}
        for case in dataset["cases"]:
            if rules_predictions[case["id"]] != "none":
                continue
            if case["id"] in completed_case_ids:
                continue
            called = _call_model(config, model, case["language"], case["text"])
            fallback_rows.append({"id": case["id"], **called})
            report["model_calls"] += 1
            _atomic_write(output, report)
        gate_snapshot = analyze_condition(
            dataset["cases"],
            rules_predictions,
            fallback_rows,
            config["success_gates"],
        )
        report["conditions"].append(
            {
                "model": model,
                "model_snapshot": inventory[model],
                "fallback_rows": fallback_rows,
                "gate_snapshot": gate_snapshot,
            }
        )
        report["active_condition"] = None
        _atomic_write(output, report)
        subprocess.run(
            ["ollama", "stop", model],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if gate_snapshot["all_gates_pass"]:
            report["selected_model"] = model
            report["early_stop_triggered"] = True
            break

    report["completed_at"] = datetime.now(TZ).isoformat(timespec="seconds")
    _atomic_write(output, report)
    print(output)
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    run(args.output)


if __name__ == "__main__":
    main()
