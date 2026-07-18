#!/usr/bin/env python3
"""Run the frozen V65 local LeftBrain model screen once."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from cognitive_plan_model_screen_v65_core import CONDITIONS, parse_tool_response, referentially_valid


ROOT = Path(__file__).resolve().parent
TZ = ZoneInfo("Asia/Tokyo")
PREREG_PATH = ROOT / "configs/cognitive_plan_model_screen_v65_preregistration.json"
DATASET_PATH = ROOT / "datasets/cognitive_plan_model_screen_v65.json"
CLOSURE_PATH = ROOT / "configs/cognitive_plan_model_screen_v65_dataset_closure.json"
LOCK_PATH = ROOT / "configs/cognitive_plan_model_screen_v65_harness_lock.json"
DEFAULT_OUTPUT = ROOT / "reports/cognitive_plan_model_screen_v65_raw.json"
CHAT_URL = "http://127.0.0.1:11434/api/chat"
TAGS_URL = "http://127.0.0.1:11434/api/tags"
SYSTEM_PROMPT = """You are the Left Brain plan selector for a local cognitive dialogue system.
Call emit_cognitive_plan exactly once and return no narrative answer.
Use only IDs supplied in the planning packet. Never invent an ID.
Bind quoted first person to the quoted speaker, not the listener.
Select only evidence that directly supports the decision.
Current memory can be active. Superseded, private, or irrelevant memory must be suppressed when it should not guide or appear in the reply.
Use preserve_uncertainty when social evidence permits multiple explanations. Use abstain when the packet lacks evidence for the requested fact.
Refuse non-consensual surveillance or account access.
Mark obvious personification and playful metaphors as nonliteral while selecting a practical, socially appropriate response.
"""


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def _tracked_tree_clean():
    return subprocess.run(["git", "diff", "--quiet"], cwd=ROOT, check=False).returncode == 0 and subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=ROOT, check=False).returncode == 0


def _atomic_write(path, payload):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def _post_json(url, body, timeout):
    request = urllib.request.Request(url, data=json.dumps(body, ensure_ascii=False).encode("utf-8"), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.load(response)


def _get_json(url, timeout=30):
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return json.load(response)


def _peak_ollama_rss_bytes():
    try:
        output = subprocess.check_output(["ps", "-axo", "rss=,command="], text=True)
    except (OSError, subprocess.SubprocessError):
        return None
    total_kib = 0
    for line in output.splitlines():
        if "ollama" not in line.lower():
            continue
        match = re.match(r"\s*(\d+)\s+", line)
        if match:
            total_kib += int(match.group(1))
    return total_kib * 1024


def _stop_models(config):
    for condition in CONDITIONS:
        subprocess.run(["ollama", "stop", config["conditions"][condition]["ollama_tag"]], check=False, capture_output=True, text=True)
    time.sleep(0.5)


def _tool_schema(config):
    return {
        "type": "function",
        "function": {
            "name": "emit_cognitive_plan",
            "description": "Emit one exact cognitive response plan using only IDs from the planning packet.",
            "parameters": {
                "type": "object",
                "additionalProperties": False,
                "required": config["tool_contract"]["required_fields"],
                "properties": {
                    "response_act": {"type": "string", "enum": config["tool_contract"]["response_act_enum"]},
                    "epistemic_policy": {"type": "string", "enum": config["tool_contract"]["epistemic_policy_enum"]},
                    "primary_actor_id": {"type": "string"},
                    "decision_target_id": {"type": "string"},
                    "selected_evidence_ids": {"type": "array", "items": {"type": "string"}, "uniqueItems": True},
                    "active_memory_ids": {"type": "array", "items": {"type": "string"}, "uniqueItems": True},
                    "suppressed_memory_ids": {"type": "array", "items": {"type": "string"}, "uniqueItems": True},
                    "nonliteral": {"type": "boolean"}
                }
            }
        }
    }


def assert_gold_isolated(packet):
    forbidden = {"id", "scenario_family", "expected"}
    if forbidden.intersection(packet):
        raise ValueError("V65 scoring gold leaked into planning packet")
    encoded = json.dumps(packet, ensure_ascii=False)
    if '"expected"' in encoded:
        raise ValueError("V65 nested expected value leaked into planning packet")


def build_request(config, packet, condition):
    if condition not in CONDITIONS:
        raise ValueError(f"unknown V65 condition: {condition}")
    assert_gold_isolated(packet)
    generation = config["generation"]
    return {
        "model": config["conditions"][condition]["ollama_tag"],
        "messages": [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": json.dumps(packet, ensure_ascii=False, separators=(",", ":"))}],
        "tools": [_tool_schema(config)],
        "stream": False,
        "think": generation["thinking"],
        "keep_alive": generation["keep_alive"],
        "options": {"temperature": generation["temperature"], "top_p": generation["top_p"], "seed": generation["seed"], "num_ctx": generation["context_tokens"], "num_predict": generation["maximum_output_tokens"]}
    }


def _call_once(config, body):
    started = time.perf_counter()
    try:
        response = _post_json(CHAT_URL, body, config["generation"]["timeout_seconds"])
        return response, round(time.perf_counter() - started, 6), None
    except (OSError, TimeoutError, urllib.error.URLError, json.JSONDecodeError) as exc:
        return {}, round(time.perf_counter() - started, 6), f"{type(exc).__name__}: {exc}"


def _warmup_packet():
    return {
        "user_input": "今日は晴れている。短く返す計画を選ぶ。",
        "actors": [{"id": "person_user", "surface": "ユーザー"}],
        "evidence": [{"id": "weather_clear", "text": "晴れている", "source": "user_input"}],
        "memory_records": [],
        "decision_targets": [{"id": "acknowledge_weather", "description": "天気に短く反応する"}]
    }


def _verify_lock(lock):
    failed = []
    for artifact in lock["frozen_artifacts"].values():
        path = ROOT / artifact["path"]
        if not path.exists() or _sha256(path) != artifact["sha256"]:
            failed.append(artifact["path"])
    if failed:
        raise ValueError("V65 frozen artifact drift: " + ", ".join(failed))
    if tuple(lock["conditions"]) != tuple(_load(PREREG_PATH)["condition_order"]):
        raise ValueError("V65 condition order drift")


def _preflight(lock):
    command = [sys.executable, *lock["preflight"]["arguments"]]
    completed = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
    combined = f"{completed.stdout}\n{completed.stderr}"
    match = re.search(r"Ran\s+(\d+)\s+tests?", combined)
    observed = int(match.group(1)) if match else None
    return {"command": command, "returncode": completed.returncode, "stdout": completed.stdout, "stderr": completed.stderr, "observed_test_count": observed, "expected_test_count": lock["preflight"]["expected_test_count"], "passed": completed.returncode == 0 and observed == lock["preflight"]["expected_test_count"]}


def _model_snapshots(config):
    inventory = {row["name"]: row for row in (_get_json(TAGS_URL).get("models") or [])}
    snapshots = {}
    for condition in CONDITIONS:
        frozen = config["conditions"][condition]
        row = inventory.get(frozen["ollama_tag"])
        if not row or row.get("digest") != frozen["digest"]:
            raise ValueError(f"V65 missing or drifted model: {frozen['ollama_tag']}")
        snapshots[condition] = {"ollama_tag": frozen["ollama_tag"], "digest": row["digest"], "size_bytes": row.get("size"), "details": row.get("details") or {}}
    return snapshots


def run(output_path=DEFAULT_OUTPUT, call_fn=_call_once):
    config = _load(PREREG_PATH)
    dataset = _load(DATASET_PATH)
    lock = _load(LOCK_PATH)
    _verify_lock(lock)
    if _git("branch", "--show-current") != lock["formal_run"]["required_run_branch"]:
        raise ValueError("V65 formal run must execute from main")
    if _git("rev-parse", "HEAD") != _git("rev-parse", lock["formal_run"]["required_head_ref"]):
        raise ValueError("V65 main must match the locked remote ref")
    if not _tracked_tree_clean():
        raise ValueError("V65 formal run requires a clean tracked tree")
    if Path(output_path).exists():
        raise ValueError("V65 result exists; overwrite and rerun are forbidden")
    preflight = _preflight(lock)
    if not preflight["passed"]:
        raise ValueError("V65 preflight failed")
    snapshots = _model_snapshots(config)
    warmups = []
    rows = []
    _stop_models(config)
    for condition in config["condition_order"]:
        warm_body = build_request(config, _warmup_packet(), condition)
        warm_response, warm_seconds, warm_error = call_fn(config, warm_body)
        warmups.append({"condition": condition, "wall_seconds": warm_seconds, "transport_error": warm_error, "tool_parse_success": parse_tool_response(warm_response)["tool_parse_success"]})
        for case in dataset["cases"]:
            packet = case["planning_packet"]
            body = build_request(config, packet, condition)
            request_sha256 = hashlib.sha256(json.dumps(body, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()
            response, wall_seconds, error = call_fn(config, body)
            parsed = parse_tool_response(response)
            reference_valid = referentially_valid(parsed["plan"], packet, config) if parsed["tool_parse_success"] else False
            rows.append({"case_id": case["id"], "condition": condition, "request_sha256": request_sha256, **parsed, "referentially_valid": reference_valid, "wall_seconds": wall_seconds, "transport_attempts": 1, "transport_error": error, "ollama_rss_bytes": _peak_ollama_rss_bytes(), "total_duration_ns": response.get("total_duration"), "load_duration_ns": response.get("load_duration"), "prompt_eval_count": response.get("prompt_eval_count"), "eval_count": response.get("eval_count")})
        _stop_models(config)
    expected = config["run_invariants"]
    if len(warmups) != expected["warmup_call_count_exact"] or len(rows) != expected["scored_model_call_count_exact"]:
        raise ValueError("V65 call-count mismatch")
    raw = {
        "schema": "uruha_cognitive_plan_model_screen_raw_v65",
        "experiment_id": config["experiment_id"],
        "started_from_commit": _git("rev-parse", "HEAD"),
        "completed_at": datetime.now(TZ).isoformat(),
        "preflight": preflight,
        "model_snapshots": snapshots,
        "condition_order": config["condition_order"],
        "warmup_calls": warmups,
        "rows": rows,
        "warmup_call_count": len(warmups),
        "scored_model_call_count": len(rows),
        "transport_attempt_count": len(warmups) + len(rows),
        "transport_error_count": sum(bool(row["transport_error"]) for row in warmups) + sum(bool(row["transport_error"]) for row in rows),
        "gold_in_raw": False,
        "production_runtime_changed": False,
        "production_memory_read_or_write": False,
        "physical_vrm_action_count": 0
    }
    _atomic_write(Path(output_path), raw)
    return raw


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    raw = run(args.output)
    print(json.dumps({key: raw[key] for key in ("warmup_call_count", "scored_model_call_count", "transport_attempt_count", "transport_error_count")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
