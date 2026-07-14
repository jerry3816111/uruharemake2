#!/usr/bin/env python3
"""Run the frozen V33 local Qwen2.5/Qwen3.5 comparison with resume support."""

import argparse
import json
import os
import re
import statistics
import subprocess
import time
import urllib.error
import urllib.request
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from rightbrain_semantic_verifier_v32 import match_group


ROOT = Path(__file__).resolve().parent
DATASET_PATH = ROOT / "datasets" / "rightbrain_qwen35_migration_v33_holdout.json"
PREREG_PATH = ROOT / "configs" / "rightbrain_qwen35_migration_v33_preregistration.json"
DEFAULT_OUTPUT = ROOT / "reports" / "rightbrain_qwen35_migration_v33_raw.json"
OLLAMA_CHAT_URL = "http://127.0.0.1:11434/api/chat"
OLLAMA_PS_URL = "http://127.0.0.1:11434/api/ps"
TZ = ZoneInfo("Asia/Tokyo")

MODEL_CONDITIONS = (
    "qwen2_5_7b_quantized_control",
    "qwen3_5_9b_quantized_treatment",
)
TEMPERATURES = (0.82, 0.96, 1.08)
TOP_P = (0.92, 0.95, 0.98)
TOP_K = (64, 96, 128)
REPEAT_PENALTIES = (1.2, 1.26, 1.32)
SEEDS = (20260715, 20260716, 20260717)
HARD_FAILURE_PREFIXES = (
    "empty",
    "missing_japanese_surface",
    "cjk_language_leak",
    "nonstandard_cjk_surface",
    "foreign_script_leak",
    "ascii_symbol_artifact",
    "unicode_replacement_character",
    "nonstandard_punctuation",
    "unexpected_ascii_leak",
    "instruction_or_plan_leak",
    "japanese_response_plan_leak",
    "awkward_or_caregiver_surface",
    "formal_register_drift",
)


def _sha256(path):
    import hashlib

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


def _post_json(url, body, timeout=240):
    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.load(response)


def _get_json(url, timeout=30):
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return json.load(response)


def _call_ollama(body, attempts=3):
    errors = []
    for attempt in range(1, attempts + 1):
        started = time.perf_counter()
        try:
            response = _post_json(OLLAMA_CHAT_URL, body)
            return response, time.perf_counter() - started, attempt, errors
        except (OSError, TimeoutError, urllib.error.URLError, json.JSONDecodeError) as exc:
            errors.append(f"{type(exc).__name__}: {exc}")
            if attempt < attempts:
                time.sleep(2 * attempt)
    raise RuntimeError("Ollama request failed: " + " | ".join(errors))


def _peak_ollama_rss_bytes():
    try:
        output = subprocess.check_output(["ps", "-axo", "rss=,command="], text=True)
    except (OSError, subprocess.SubprocessError):
        return None
    rss_kib = 0
    for line in output.splitlines():
        if "ollama" not in line.lower():
            continue
        match = re.match(r"\s*(\d+)\s+", line)
        if match:
            rss_kib += int(match.group(1))
    return rss_kib * 1024


def _resident_snapshot(model_tag):
    try:
        models = _get_json(OLLAMA_PS_URL).get("models") or []
    except (OSError, TimeoutError, urllib.error.URLError, json.JSONDecodeError):
        return {}
    for model in models:
        if model.get("name") == model_tag or model.get("model") == model_tag:
            return {
                "name": model.get("name") or model.get("model"),
                "size_bytes": model.get("size"),
                "size_vram_bytes": model.get("size_vram"),
                "details": model.get("details") or {},
            }
    return {}


def _normalize_reply(text):
    return re.sub(r"[\s\u3000。．，,、！？?!…~～ー\-_/'\"`]+", "", str(text or "").lower())


def _is_hard_failure(reasons):
    return any(any(str(reason).startswith(prefix) for prefix in HARD_FAILURE_PREFIXES) for reason in reasons)


def _model_info(prereg, condition):
    frozen = prereg["frozen_environment"]["conditions"][condition]
    return {
        "condition": condition,
        "model_tag": frozen["ollama_tag"],
        "blob_sha256": frozen["blob_sha256"],
        "blob_bytes": frozen["blob_bytes"],
        "thinking": frozen.get("thinking"),
    }


def _chat_body(model_info, messages, *, options, tools=None):
    body = {
        "model": model_info["model_tag"],
        "messages": messages,
        "stream": False,
        "keep_alive": "20m",
        "options": options,
    }
    if tools:
        body["tools"] = tools
    if model_info.get("thinking") is not None:
        body["think"] = bool(model_info["thinking"])
    return body


def _response_metrics(response, elapsed_seconds):
    return {
        "wall_seconds": round(elapsed_seconds, 6),
        "total_duration_ns": response.get("total_duration"),
        "load_duration_ns": response.get("load_duration"),
        "prompt_eval_count": response.get("prompt_eval_count"),
        "prompt_eval_duration_ns": response.get("prompt_eval_duration"),
        "eval_count": response.get("eval_count"),
        "eval_duration_ns": response.get("eval_duration"),
    }


def score_rightbrain_output(brain, case, logic, raw_reply):
    max_chars = int((logic.get("constraints") or {}).get("max_chars") or 48)
    groups = [list(group) for group in brain._model_required_semantic_groups(logic)]
    group_rows = []
    for group in groups:
        hit, traces = match_group(
            raw_reply,
            group,
            "lemma_polarity",
            brain._semantic_marker_hit,
        )
        group_rows.append(
            {
                "markers": group,
                "hit": bool(hit),
                "traces": [trace.to_dict() for trace in traces],
            }
        )
    reasons = brain._model_candidate_rejection_reasons(
        raw_reply,
        logic,
        max_chars,
        user_input=case["user_input"],
    )
    forbidden_hits = sorted(
        {
            str(marker)
            for marker in [
                *(case.get("forbidden_substrings") or []),
                *brain._audited_memory_forbidden_surface_terms(logic),
            ]
            if str(marker).strip() and str(marker) in str(raw_reply or "")
        }
    )
    return {
        "semantic_groups": group_rows,
        "semantic_group_hit_count": sum(row["hit"] for row in group_rows),
        "semantic_group_count": len(group_rows),
        "semantic_contract_pass": bool(group_rows) and all(row["hit"] for row in group_rows),
        "current_gate_rejection_reasons": reasons,
        "current_gate_raw_pass": not reasons,
        "hard_surface_failure": _is_hard_failure(reasons),
        "polite_or_service_register": any(
            reason in {"polite_tone_drift", "formal_register_drift"} for reason in reasons
        ),
        "private_or_forbidden_memory_hits": forbidden_hits,
        "private_memory_intrusion": bool(forbidden_hits),
        "normalized_reply": _normalize_reply(raw_reply),
        "character_count": len(str(raw_reply or "")),
    }


def _canonical_call(call):
    function = call.get("function") if isinstance(call, dict) else None
    function = function if isinstance(function, dict) else call
    name = str((function or {}).get("name") or "")
    arguments = (function or {}).get("arguments") or {}
    if isinstance(arguments, str):
        try:
            arguments = json.loads(arguments)
        except json.JSONDecodeError:
            arguments = {"__unparsed__": arguments}
    return {"name": name, "arguments": arguments if isinstance(arguments, dict) else {"__invalid__": arguments}}


def _call_key(call):
    return json.dumps(_canonical_call(call), ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def score_action_output(case, tool_calls):
    actual = [_canonical_call(call) for call in tool_calls]
    expected_keys = sorted(_call_key(call) for call in case["expected_calls"])
    actual_keys = sorted(_call_key(call) for call in actual)
    forbidden_keys = {_call_key(call) for call in case["forbidden_calls"]}
    expected_set = set(expected_keys)
    actual_set = set(actual_keys)
    invalid = [call for call in actual if not call["name"] or "__unparsed__" in call["arguments"] or "__invalid__" in call["arguments"]]
    return {
        "actual_calls": actual,
        "exact_match": actual_keys == expected_keys,
        "expected_call_count": len(expected_keys),
        "actual_call_count": len(actual_keys),
        "required_action_recall": (
            len(expected_set & actual_set) / len(expected_set) if expected_set else None
        ),
        "extra_call_count": len(actual_set - expected_set),
        "false_action": bool(actual_set - expected_set),
        "forbidden_call_hits": sorted(actual_set & forbidden_keys),
        "negation_violation": bool(actual_set & forbidden_keys),
        "invalid_tool_or_argument": bool(invalid),
        "no_action_correct": bool(case["expected_no_action"] and not actual_keys),
    }


def _new_report(dataset, prereg):
    return {
        "schema": "uruha_rightbrain_qwen35_migration_raw_v33",
        "started_at": _now(),
        "completed_at": None,
        "runner_commit": _git_head(),
        "preregistration_sha256": _sha256(PREREG_PATH),
        "dataset_sha256": _sha256(DATASET_PATH),
        "dataset_accounting": dataset["accounting"],
        "model_conditions": {
            condition: _model_info(prereg, condition) for condition in MODEL_CONDITIONS
        },
        "rightbrain_rows": [],
        "action_rows": [],
        "resource_summary": {},
        "transport_errors": [],
    }


def _load_or_create(output, dataset, prereg):
    if output.exists():
        report = json.loads(output.read_text(encoding="utf-8"))
        if report.get("preregistration_sha256") != _sha256(PREREG_PATH):
            raise ValueError("Existing report preregistration hash mismatch")
        if report.get("dataset_sha256") != _sha256(DATASET_PATH):
            raise ValueError("Existing report dataset hash mismatch")
        if report.get("runner_commit") != _git_head():
            raise ValueError("Existing report runner commit mismatch")
        return report
    return _new_report(dataset, prereg)


def _unload_model(model_tag):
    subprocess.run(
        ["ollama", "stop", model_tag],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _update_resource(report, condition, model_info, response_metrics):
    resource = report["resource_summary"].setdefault(
        condition,
        {
            "model_tag": model_info["model_tag"],
            "blob_bytes": model_info["blob_bytes"],
            "cold_start_wall_seconds": None,
            "max_ollama_process_rss_bytes": 0,
            "resident_snapshots": [],
        },
    )
    if resource["cold_start_wall_seconds"] is None:
        resource["cold_start_wall_seconds"] = response_metrics["wall_seconds"]
    rss = _peak_ollama_rss_bytes()
    if rss is not None:
        resource["max_ollama_process_rss_bytes"] = max(resource["max_ollama_process_rss_bytes"], rss)
    snapshot = _resident_snapshot(model_info["model_tag"])
    if snapshot and snapshot not in resource["resident_snapshots"]:
        resource["resident_snapshots"].append(snapshot)


def run(output=DEFAULT_OUTPUT, selected_conditions=MODEL_CONDITIONS):
    dataset = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    prereg = json.loads(PREREG_PATH.read_text(encoding="utf-8"))
    report = _load_or_create(output, dataset, prereg)

    os.environ["URUHA_SKIP_AUTO_VENV"] = "1"
    from uruha_brain_mac import RIGHT_BRAIN_MODEL_SYSTEM_PROMPT, RightBrain

    brain = RightBrain(load_model=False)
    existing_right = {
        (row["condition"], row["case_id"], row["seed"], row["candidate_index"])
        for row in report["rightbrain_rows"]
    }
    existing_action = {(row["condition"], row["case_id"]) for row in report["action_rows"]}
    total_expected = len(selected_conditions) * (
        len(dataset["rightbrain_cases"]) * len(SEEDS) * len(TEMPERATURES)
        + len(dataset["action_cases"])
    )
    completed = sum(key[0] in selected_conditions for key in existing_right) + sum(
        key[0] in selected_conditions for key in existing_action
    )

    for condition in selected_conditions:
        model_info = report["model_conditions"][condition]
        for other in MODEL_CONDITIONS:
            if other != condition:
                _unload_model(report["model_conditions"][other]["model_tag"])

        for case in dataset["rightbrain_cases"]:
            for seed in SEEDS:
                for candidate_index in range(len(TEMPERATURES)):
                    key = (condition, case["id"], seed, candidate_index)
                    if key in existing_right:
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
                        "temperature": TEMPERATURES[candidate_index],
                        "top_p": TOP_P[candidate_index],
                        "top_k": TOP_K[candidate_index],
                        "repeat_penalty": REPEAT_PENALTIES[candidate_index],
                        "seed": seed + candidate_index * 10000,
                        "num_ctx": 4096,
                        "num_predict": 96,
                    }
                    response, elapsed, attempts, errors = _call_ollama(
                        _chat_body(model_info, messages, options=options)
                    )
                    raw_reply = str((response.get("message") or {}).get("content") or "").strip()
                    metrics = _response_metrics(response, elapsed)
                    report["rightbrain_rows"].append(
                        {
                            "condition": condition,
                            "model_tag": model_info["model_tag"],
                            "case_id": case["id"],
                            "category": case["category"],
                            "seed": seed,
                            "candidate_index": candidate_index,
                            "sampling": options,
                            "raw_reply": raw_reply,
                            "score": score_rightbrain_output(brain, case, logic, raw_reply),
                            "response_metrics": metrics,
                            "transport_attempts": attempts,
                            "prior_transport_errors": errors,
                        }
                    )
                    _update_resource(report, condition, model_info, metrics)
                    completed += 1
                    _atomic_write(output, report)
                    if completed % 10 == 0:
                        print(f"[{completed}/{total_expected}] rightbrain {condition} {case['id']}", flush=True)

        for case in dataset["action_cases"]:
            key = (condition, case["id"])
            if key in existing_action:
                continue
            messages = [
                {"role": "system", "content": dataset["tool_system_prompt"]},
                {"role": "user", "content": case["user_input"]},
            ]
            options = {
                "temperature": 0,
                "top_p": 1.0,
                "seed": 20260715,
                "num_ctx": 4096,
                "num_predict": 128,
            }
            response, elapsed, attempts, errors = _call_ollama(
                _chat_body(model_info, messages, options=options, tools=dataset["tool_schemas"])
            )
            message = response.get("message") or {}
            tool_calls = message.get("tool_calls") or []
            metrics = _response_metrics(response, elapsed)
            report["action_rows"].append(
                {
                    "condition": condition,
                    "model_tag": model_info["model_tag"],
                    "case_id": case["id"],
                    "family": case["family"],
                    "raw_content": str(message.get("content") or ""),
                    "score": score_action_output(case, tool_calls),
                    "response_metrics": metrics,
                    "transport_attempts": attempts,
                    "prior_transport_errors": errors,
                }
            )
            _update_resource(report, condition, model_info, metrics)
            completed += 1
            _atomic_write(output, report)
            if completed % 10 == 0:
                print(f"[{completed}/{total_expected}] action {condition} {case['id']}", flush=True)
        _unload_model(model_info["model_tag"])

    if all(
        len([row for row in report["rightbrain_rows"] if row["condition"] == condition])
        == len(dataset["rightbrain_cases"]) * len(SEEDS) * len(TEMPERATURES)
        and len([row for row in report["action_rows"] if row["condition"] == condition])
        == len(dataset["action_cases"])
        for condition in MODEL_CONDITIONS
    ):
        report["completed_at"] = _now()
    _atomic_write(output, report)
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--condition", action="append", choices=MODEL_CONDITIONS)
    args = parser.parse_args()
    selected = tuple(args.condition or MODEL_CONDITIONS)
    report = run(output=args.output, selected_conditions=selected)
    print(
        json.dumps(
            {
                "output": str(args.output),
                "rightbrain_rows": len(report["rightbrain_rows"]),
                "action_rows": len(report["action_rows"]),
                "completed_at": report["completed_at"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
