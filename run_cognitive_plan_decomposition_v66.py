#!/usr/bin/env python3
"""Run the frozen V66 matched-compute cognitive decomposition pilot once."""

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

from cognitive_plan_decomposition_v66_core import (
    ALL_FIELDS,
    CONDITIONS,
    DECISION_FIELDS,
    MATCHED_CONTROL,
    ONE_CALL,
    SELECTION_FIELDS,
    TREATMENT,
    assemble_plan,
    parse_tool_response,
    referentially_valid,
)


ROOT = Path(__file__).resolve().parent
TZ = ZoneInfo("Asia/Tokyo")
PREREG_PATH = ROOT / "configs/cognitive_plan_decomposition_v66_preregistration.json"
DATASET_PATH = ROOT / "datasets/cognitive_plan_decomposition_v66.json"
CLOSURE_PATH = ROOT / "configs/cognitive_plan_decomposition_v66_dataset_closure.json"
LOCK_PATH = ROOT / "configs/cognitive_plan_decomposition_v66_harness_lock.json"
DEFAULT_OUTPUT = ROOT / "reports/cognitive_plan_decomposition_v66_raw.json"
CHAT_URL = "http://127.0.0.1:11434/api/chat"
TAGS_URL = "http://127.0.0.1:11434/api/tags"

ONTOLOGY = """Contract definitions:
- response_act is what the reply must do: answer, correct, clarify, recommend, support, refuse, or tease.
- epistemic_policy is assert only when evidence supports the claim, preserve_uncertainty when several explanations remain, and abstain when the requested fact is unavailable.
- primary_actor_id is the actor whose action, state, or belief is the direct target of the reply.
- selected_evidence_ids contains every supplied evidence item needed for the decision and no irrelevant item.
- every supplied memory ID must be placed exactly once in active_memory_ids or suppressed_memory_ids. Active memory may guide the reply. Suppressed memory must not guide or surface in it.
- nonliteral is true only when the utterance uses figurative, playful, or personified meaning rather than a literal claim.
- decision_target_id is the supplied response direction that best satisfies the current constraints.
Use only supplied IDs and never invent one.
"""

FULL_SYSTEM_PROMPT = """You are the cognitive-plan module of a local dialogue system.
Evaluate the supplied planning packet and call emit_cognitive_plan exactly once. Return no narrative answer.
""" + ONTOLOGY

REVISION_SYSTEM_PROMPT = """You are the second pass of a cognitive-plan module.
The supplied draft is fallible. Re-evaluate the complete planning packet, correct every error you find, and call emit_cognitive_plan exactly once. Return no narrative answer.
""" + ONTOLOGY

SELECTION_SYSTEM_PROMPT = """You are the evidence and memory selection stage of a local cognitive dialogue system.
Do not choose a response act or action. Select only the primary actor, relevant evidence, complete active/suppressed memory partition, and whether the utterance is nonliteral. Call emit_cognitive_selection exactly once and return no narrative answer.
""" + ONTOLOGY

DECISION_SYSTEM_PROMPT = """You are the epistemic and action decision stage of a local cognitive dialogue system.
The previous stage has already fixed the actor, evidence, memory policy, and nonliteral status. Using only the supplied selected context and decision targets, choose the response act, epistemic policy, and decision target. Call emit_cognitive_decision exactly once and return no narrative answer.
""" + ONTOLOGY


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def _tracked_tree_clean():
    unstaged = subprocess.run(["git", "diff", "--quiet"], cwd=ROOT, check=False).returncode == 0
    staged = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=ROOT, check=False).returncode == 0
    return unstaged and staged


def _atomic_write(path, payload):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
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


def _stop_model(config):
    subprocess.run(
        ["ollama", "stop", config["model"]["ollama_tag"]],
        check=False,
        capture_output=True,
        text=True,
    )
    time.sleep(0.5)


def _properties(config, fields):
    properties = {}
    for field in fields:
        if field == "response_act":
            properties[field] = {"type": "string", "enum": config["plan_contract"]["response_act_enum"]}
        elif field == "epistemic_policy":
            properties[field] = {"type": "string", "enum": config["plan_contract"]["epistemic_policy_enum"]}
        elif field in {"selected_evidence_ids", "active_memory_ids", "suppressed_memory_ids"}:
            properties[field] = {"type": "array", "items": {"type": "string"}, "uniqueItems": True}
        elif field == "nonliteral":
            properties[field] = {"type": "boolean"}
        else:
            properties[field] = {"type": "string"}
    return properties


def _tool_schema(config, name, fields, description):
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "additionalProperties": False,
                "required": list(fields),
                "properties": _properties(config, fields),
            },
        },
    }


def full_tool_schema(config):
    return _tool_schema(config, "emit_cognitive_plan", ALL_FIELDS, "Emit one complete cognitive plan using only supplied IDs.")


def selection_tool_schema(config):
    return _tool_schema(config, "emit_cognitive_selection", SELECTION_FIELDS, "Emit only the actor, evidence, memory partition, and nonliteral selection.")


def decision_tool_schema(config):
    return _tool_schema(config, "emit_cognitive_decision", DECISION_FIELDS, "Emit only the response act, epistemic policy, and decision target.")


def assert_gold_isolated(value):
    forbidden = {"id", "scenario_family", "expected"}
    if isinstance(value, dict) and forbidden.intersection(value):
        raise ValueError("V66 scoring gold leaked into model input")
    encoded = json.dumps(value, ensure_ascii=False)
    if '"expected"' in encoded or '"scenario_family"' in encoded:
        raise ValueError("V66 nested scoring metadata leaked into model input")


def _request(config, system_prompt, user_payload, tool):
    assert_gold_isolated(user_payload)
    generation = config["generation"]
    return {
        "model": config["model"]["ollama_tag"],
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False, separators=(",", ":"))},
        ],
        "tools": [tool],
        "stream": False,
        "think": generation["thinking"],
        "keep_alive": generation["keep_alive"],
        "options": {
            "temperature": generation["temperature"],
            "top_p": generation["top_p"],
            "seed": generation["seed"],
            "num_ctx": generation["context_tokens"],
            "num_predict": generation["maximum_output_tokens_per_call"],
        },
    }


def build_full_request(config, packet, draft=None):
    payload = {"planning_packet": packet}
    system = FULL_SYSTEM_PROMPT
    if draft is not None:
        payload["fallible_draft"] = draft
        system = REVISION_SYSTEM_PROMPT
    return _request(config, system, payload, full_tool_schema(config))


def build_selection_request(config, packet):
    return _request(config, SELECTION_SYSTEM_PROMPT, {"planning_packet": packet}, selection_tool_schema(config))


def _selected_rows(rows, selected_ids):
    selected = set(selected_ids or [])
    return [row for row in rows if row["id"] in selected]


def build_decision_payload(packet, selection):
    actor_rows = _selected_rows(packet["actors"], [selection.get("primary_actor_id")])
    return {
        "user_input": packet["user_input"],
        "primary_actor": actor_rows,
        "selected_evidence": _selected_rows(packet["evidence"], selection.get("selected_evidence_ids")),
        "active_memories": _selected_rows(packet["memory_records"], selection.get("active_memory_ids")),
        "suppressed_memory_ids": list(selection.get("suppressed_memory_ids") or []),
        "nonliteral": selection.get("nonliteral"),
        "decision_targets": packet["decision_targets"],
    }


def build_decision_request(config, packet, selection):
    return _request(
        config,
        DECISION_SYSTEM_PROMPT,
        {"selected_context": build_decision_payload(packet, selection)},
        decision_tool_schema(config),
    )


def _call_once(config, body):
    started = time.perf_counter()
    try:
        response = _post_json(CHAT_URL, body, config["generation"]["timeout_seconds"])
        return response, round(time.perf_counter() - started, 6), None
    except (OSError, TimeoutError, urllib.error.URLError, json.JSONDecodeError) as exc:
        return {}, round(time.perf_counter() - started, 6), f"{type(exc).__name__}: {exc}"


def _execute_call(config, body, parser_name, fields, call_fn):
    request_sha256 = hashlib.sha256(
        json.dumps(body, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()
    response, wall_seconds, error = call_fn(config, body)
    parsed = parse_tool_response(response, parser_name, fields)
    return {
        "request_sha256": request_sha256,
        **parsed,
        "wall_seconds": wall_seconds,
        "transport_error": error,
        "ollama_rss_bytes": _peak_ollama_rss_bytes(),
        "total_duration_ns": response.get("total_duration"),
        "load_duration_ns": response.get("load_duration"),
        "prompt_eval_count": response.get("prompt_eval_count"),
        "eval_count": response.get("eval_count"),
    }


def run_case(config, packet, condition, call_fn=_call_once):
    if condition not in CONDITIONS:
        raise ValueError(f"unknown V66 condition: {condition}")
    calls = []
    if condition == ONE_CALL:
        final_call = _execute_call(
            config,
            build_full_request(config, packet),
            "emit_cognitive_plan",
            ALL_FIELDS,
            call_fn,
        )
        calls.append(final_call)
        plan = final_call["values"]
        intermediate = {}
    elif condition == MATCHED_CONTROL:
        draft_call = _execute_call(
            config,
            build_full_request(config, packet),
            "emit_cognitive_plan",
            ALL_FIELDS,
            call_fn,
        )
        calls.append(draft_call)
        final_call = _execute_call(
            config,
            build_full_request(config, packet, draft=draft_call["values"]),
            "emit_cognitive_plan",
            ALL_FIELDS,
            call_fn,
        )
        calls.append(final_call)
        plan = final_call["values"]
        intermediate = {"fallible_draft": draft_call["values"]}
    else:
        selection_call = _execute_call(
            config,
            build_selection_request(config, packet),
            "emit_cognitive_selection",
            SELECTION_FIELDS,
            call_fn,
        )
        calls.append(selection_call)
        decision_call = _execute_call(
            config,
            build_decision_request(config, packet, selection_call["values"]),
            "emit_cognitive_decision",
            DECISION_FIELDS,
            call_fn,
        )
        calls.append(decision_call)
        plan = assemble_plan(selection_call["values"], decision_call["values"])
        intermediate = {
            "selection": selection_call["values"],
            "decision": decision_call["values"],
        }

    all_parse = all(call["tool_parse_success"] for call in calls)
    valid = referentially_valid(plan, packet, config) if all_parse else False
    rss_values = [call["ollama_rss_bytes"] for call in calls if call["ollama_rss_bytes"] is not None]
    return {
        "plan": plan,
        "intermediate": intermediate,
        "all_required_tools_parse": all_parse,
        "referentially_valid": valid,
        "stage_parse_success": [call["tool_parse_success"] for call in calls],
        "stage_parse_errors": [call["parse_error"] for call in calls],
        "request_sha256s": [call["request_sha256"] for call in calls],
        "wall_seconds": sum(call["wall_seconds"] for call in calls),
        "transport_attempts": len(calls),
        "transport_errors": [call["transport_error"] for call in calls],
        "ollama_rss_bytes": max(rss_values) if rss_values else None,
        "prompt_eval_count_total": sum(call["prompt_eval_count"] or 0 for call in calls),
        "eval_count_total": sum(call["eval_count"] or 0 for call in calls),
        "call_records": calls,
    }


def _warmup_packet():
    return {
        "user_input": "窓の外は晴れている。短い反応方針を選ぶ。",
        "actors": [{"id": "person_user", "surface": "使用者"}],
        "evidence": [{"id": "weather_clear", "text": "晴れている", "source": "current_utterance"}],
        "memory_records": [],
        "decision_targets": [{"id": "acknowledge_weather", "description": "天気に短く反応する"}],
    }


def _verify_lock(lock):
    failed = []
    for artifact in lock["frozen_artifacts"].values():
        path = ROOT / artifact["path"]
        if not path.exists() or _sha256(path) != artifact["sha256"]:
            failed.append(artifact["path"])
    if failed:
        raise ValueError("V66 frozen artifact drift: " + ", ".join(failed))
    if tuple(lock["conditions"]) != tuple(_load(PREREG_PATH)["condition_order"]):
        raise ValueError("V66 condition order drift")


def _preflight(lock):
    command = [sys.executable, *lock["preflight"]["arguments"]]
    completed = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
    combined = f"{completed.stdout}\n{completed.stderr}"
    match = re.search(r"Ran\s+(\d+)\s+tests?", combined)
    observed = int(match.group(1)) if match else None
    expected = lock["preflight"]["expected_test_count"]
    return {
        "command": command,
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "observed_test_count": observed,
        "expected_test_count": expected,
        "passed": completed.returncode == 0 and observed == expected,
    }


def _model_snapshot(config):
    inventory = {row["name"]: row for row in (_get_json(TAGS_URL).get("models") or [])}
    frozen = config["model"]
    row = inventory.get(frozen["ollama_tag"])
    if not row or row.get("digest") != frozen["digest"]:
        raise ValueError(f"V66 missing or drifted model: {frozen['ollama_tag']}")
    return {
        "ollama_tag": frozen["ollama_tag"],
        "digest": row["digest"],
        "size_bytes": row.get("size"),
        "details": row.get("details") or {},
    }


def run(output_path=DEFAULT_OUTPUT, call_fn=_call_once):
    config = _load(PREREG_PATH)
    dataset = _load(DATASET_PATH)
    lock = _load(LOCK_PATH)
    _verify_lock(lock)
    if _git("branch", "--show-current") != lock["formal_run"]["required_run_branch"]:
        raise ValueError("V66 formal run must execute from main")
    if _git("rev-parse", "HEAD") != _git("rev-parse", lock["formal_run"]["required_head_ref"]):
        raise ValueError("V66 main must match the locked remote ref")
    if not _tracked_tree_clean():
        raise ValueError("V66 formal run requires a clean tracked tree")
    if Path(output_path).exists():
        raise ValueError("V66 result exists; overwrite and rerun are forbidden")
    preflight = _preflight(lock)
    if not preflight["passed"]:
        raise ValueError("V66 preflight failed")
    snapshot = _model_snapshot(config)

    warmups = []
    rows = []
    _stop_model(config)
    for condition in config["condition_order"]:
        warm = run_case(config, _warmup_packet(), condition, call_fn)
        warmups.append({
            "condition": condition,
            "transport_attempts": warm["transport_attempts"],
            "transport_errors": warm["transport_errors"],
            "all_required_tools_parse": warm["all_required_tools_parse"],
            "wall_seconds": warm["wall_seconds"],
        })
        for case in dataset["cases"]:
            result = run_case(config, case["planning_packet"], condition, call_fn)
            rows.append({"case_id": case["id"], "condition": condition, **result})
        _stop_model(config)

    warmup_attempts = sum(row["transport_attempts"] for row in warmups)
    scored_attempts = sum(row["transport_attempts"] for row in rows)
    invariants = config["run_invariants"]
    if warmup_attempts != invariants["warmup_transport_attempt_count_exact"]:
        raise ValueError("V66 warmup call-count mismatch")
    if scored_attempts != invariants["scored_transport_attempt_count_exact"]:
        raise ValueError("V66 scored call-count mismatch")
    if any(sum(row["condition"] == condition for row in rows) != 12 for condition in CONDITIONS):
        raise ValueError("V66 per-condition case-count mismatch")

    transport_errors = sum(bool(error) for row in warmups for error in row["transport_errors"])
    transport_errors += sum(bool(error) for row in rows for error in row["transport_errors"])
    raw = {
        "schema": "uruha_cognitive_plan_decomposition_raw_v66",
        "experiment_id": config["experiment_id"],
        "started_from_commit": _git("rev-parse", "HEAD"),
        "completed_at": datetime.now(TZ).isoformat(),
        "preflight": preflight,
        "model_snapshot": snapshot,
        "condition_order": config["condition_order"],
        "warmup_calls": warmups,
        "rows": rows,
        "warmup_transport_attempt_count": warmup_attempts,
        "scored_case_count": len(rows),
        "scored_transport_attempt_count": scored_attempts,
        "transport_attempt_count": warmup_attempts + scored_attempts,
        "transport_error_count": transport_errors,
        "gold_in_raw": False,
        "production_runtime_changed": False,
        "production_memory_read_or_write": False,
        "physical_vrm_action_count": 0,
    }
    _atomic_write(Path(output_path), raw)
    return raw


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    raw = run(args.output)
    summary_keys = (
        "warmup_transport_attempt_count",
        "scored_case_count",
        "scored_transport_attempt_count",
        "transport_attempt_count",
        "transport_error_count",
    )
    print(json.dumps({key: raw[key] for key in summary_keys}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
