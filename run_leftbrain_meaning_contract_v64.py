#!/usr/bin/env python3
"""Run the frozen V64 compact-plan versus meaning-contract pilot once."""

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


ROOT = Path(__file__).resolve().parent
TZ = ZoneInfo("Asia/Tokyo")
C0 = "c0_compact_plan"
T1 = "t1_structured_meaning_contract"
CONDITIONS = (C0, T1)
PREREG_PATH = ROOT / "configs/leftbrain_meaning_contract_v64_preregistration.json"
DATASET_PATH = ROOT / "datasets/leftbrain_meaning_contract_v64.json"
CLOSURE_PATH = ROOT / "configs/leftbrain_meaning_contract_v64_dataset_closure.json"
LOCK_PATH = ROOT / "configs/leftbrain_meaning_contract_v64_harness_lock.json"
DEFAULT_OUTPUT = ROOT / "reports/leftbrain_meaning_contract_v64_raw.json"
OLLAMA_CHAT_URL = "http://127.0.0.1:11434/api/chat"
OLLAMA_TAGS_URL = "http://127.0.0.1:11434/api/tags"
GOLD_FIELDS = {
    "id",
    "scenario_family",
    "expected_response_act",
    "required_commitments",
    "forbidden_commitments",
    "required_frame_relations",
}

BASE_PROMPT = """You are the Left Brain content planner in a local cognitive dialogue system.
Plan what the final reply must mean. Do not imitate a character voice and do not write a polished final chat line.
Use only the current user utterance and supplied memory records.

General rules:
- Preserve who did what to whom; quoted first person refers to the quoted speaker.
- Separate a user's claim from a fact the reply should endorse.
- Current memory overrides superseded memory when they conflict.
- Do not expose private or irrelevant memory.
- If evidence is missing, preserve uncertainty instead of inventing.
- Refuse privacy invasion or non-consensual tracking and give a safe alternative.
- Treat obvious joking personification as non-literal while retaining a useful response.
- Return valid JSON only. No markdown and no commentary outside JSON.
"""

COMMON_SCHEMA = """Return exactly these common planning fields:
{
  "intent": "short label",
  "user_summary": "short Japanese factual summary",
  "response_goal": "short Japanese description of what the reply must accomplish",
  "core_message_jp": "short Japanese statement containing every meaning the final reply must preserve",
  "uncertainty": 0.0,
  "forbidden_moves": ["short Japanese descriptions"]
}
The core message is planning content, not character wording.
"""

STRUCTURED_SCHEMA = """First construct an explicit meaning frame, then derive the same common planning fields from it.
Return exactly this schema:
{
  "intent": "short label",
  "user_summary": "short Japanese factual summary",
  "semantic_frame": {
    "actors": [{"id": "stable actor id", "role": "speaker|addressee|other"}],
    "propositions": [{
      "subject": "actor or entity",
      "predicate": "relation or action",
      "object": "target or value",
      "polarity": "positive|negative|uncertain|nonliteral",
      "temporality": "current|superseded|future|unknown",
      "source": "user_utterance|memory:<id>|general_knowledge",
      "certainty": 0.0
    }],
    "memory_state": [{
      "memory_id": "input memory id",
      "status": "current|superseded|private|irrelevant",
      "relevance": "active|background|forbidden",
      "reason": "short Japanese reason"
    }]
  },
  "response_contract": {
    "dialogue_act": "answer|correct|clarify|recommend|support|refuse|tease",
    "required_moves": ["short semantic moves"],
    "forbidden_moves": ["short semantic moves"]
  },
  "response_goal": "short Japanese description of what the reply must accomplish",
  "core_message_jp": "short Japanese statement containing every required move",
  "uncertainty": 0.0,
  "forbidden_moves": ["short Japanese descriptions"]
}
The common fields are the only reply commitments. The frame is reasoning support and must not contain invented facts.
"""


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def _tracked_tree_clean():
    unstaged = subprocess.run(["git", "diff", "--quiet"], cwd=ROOT, check=False)
    staged = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=ROOT, check=False)
    return unstaged.returncode == 0 and staged.returncode == 0


def _atomic_write(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def _post_json(url, body, timeout=240):
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
    rss_kib = 0
    for line in output.splitlines():
        if "ollama" not in line.lower():
            continue
        match = re.match(r"\s*(\d+)\s+", line)
        if match:
            rss_kib += int(match.group(1))
    return rss_kib * 1024


def _verify_lock(lock):
    failed = []
    for artifact in lock["frozen_artifacts"].values():
        path = ROOT / artifact["path"]
        if not path.exists() or _sha256(path) != artifact["sha256"]:
            failed.append(artifact["path"])
    if failed:
        raise ValueError("V64 frozen artifact drift: " + ", ".join(failed))
    if tuple(lock["conditions"]) != CONDITIONS:
        raise ValueError("V64 condition order drift")
    if lock["formal_run"]["model_call_count_exact"] != 28:
        raise ValueError("V64 model-call budget drift")


def _run_preflight(lock):
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


def _model_snapshot(prereg):
    inventory = {row["name"]: row for row in (_get_json(OLLAMA_TAGS_URL).get("models") or [])}
    model = prereg["model"]
    row = inventory.get(model["ollama_tag"])
    if not row or row.get("digest") != model["digest"]:
        raise ValueError("V64 frozen LeftBrain model missing or drifted")
    return {
        "ollama_tag": model["ollama_tag"],
        "digest": row["digest"],
        "size_bytes": row.get("size"),
        "details": row.get("details") or {},
        "thinking": model["thinking"],
    }


def model_input(case):
    return {
        "user_input": case["user_input"],
        "memory_records": [
            {
                "memory_id": row["id"],
                "text": row["text"],
                "status": row["status"],
                "speakability": row["speakability"],
            }
            for row in case["memory_fixture"]
        ],
    }


def assert_gold_isolated(payload):
    leaked = GOLD_FIELDS.intersection(payload)
    if leaked:
        raise ValueError("V64 scoring gold leaked into request: " + ", ".join(sorted(leaked)))
    encoded = json.dumps(payload, ensure_ascii=False)
    for field in GOLD_FIELDS:
        if f'"{field}"' in encoded:
            raise ValueError(f"V64 nested scoring gold leaked into request: {field}")


def build_messages(case, condition):
    if condition not in CONDITIONS:
        raise ValueError(f"unknown V64 condition: {condition}")
    payload = model_input(case)
    assert_gold_isolated(payload)
    schema = COMMON_SCHEMA if condition == C0 else STRUCTURED_SCHEMA
    return [
        {"role": "system", "content": BASE_PROMPT + "\n" + schema},
        {"role": "user", "content": json.dumps(payload, ensure_ascii=False, separators=(",", ":"))},
    ]


def _chat_body(prereg, messages):
    generation = prereg["generation"]
    return {
        "model": prereg["model"]["ollama_tag"],
        "messages": messages,
        "stream": False,
        "format": "json",
        "keep_alive": "20m",
        "options": {
            "temperature": generation["temperature"],
            "top_p": generation["top_p"],
            "seed": generation["seed"],
            "num_ctx": generation["context_tokens"],
            "num_predict": generation["maximum_output_tokens"],
        },
    }


def _call_once(body):
    started = time.perf_counter()
    try:
        response = _post_json(OLLAMA_CHAT_URL, body)
        return response, round(time.perf_counter() - started, 6), None
    except (OSError, TimeoutError, urllib.error.URLError, json.JSONDecodeError) as exc:
        return {}, round(time.perf_counter() - started, 6), f"{type(exc).__name__}: {exc}"


def run(output_path=DEFAULT_OUTPUT, call_fn=_call_once):
    prereg = _load(PREREG_PATH)
    dataset = _load(DATASET_PATH)
    lock = _load(LOCK_PATH)
    _verify_lock(lock)
    if _git("branch", "--show-current") != lock["formal_run"]["required_run_branch"]:
        raise ValueError("V64 formal run must execute from main")
    if not _tracked_tree_clean():
        raise ValueError("V64 formal run requires a clean tracked tree")
    if Path(output_path).exists():
        raise ValueError("V64 result already exists; overwrite and rerun are forbidden")
    preflight = _run_preflight(lock)
    if not preflight["passed"]:
        raise ValueError("V64 preflight failed")
    snapshot = _model_snapshot(prereg)

    rows = []
    peak_rss = 0
    transport_errors = 0
    for case in dataset["cases"]:
        for condition in CONDITIONS:
            messages = build_messages(case, condition)
            body = _chat_body(prereg, messages)
            request_sha256 = hashlib.sha256(json.dumps(body, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()
            response, wall_seconds, error = call_fn(body)
            output_text = str((response.get("message") or {}).get("content") or "")
            rss = _peak_ollama_rss_bytes()
            if rss is not None:
                peak_rss = max(peak_rss, rss)
            if error:
                transport_errors += 1
            rows.append(
                {
                    "case_id": case["id"],
                    "condition": condition,
                    "request_sha256": request_sha256,
                    "output_text": output_text,
                    "transport_error": error,
                    "generation_metrics": {
                        "wall_seconds": wall_seconds,
                        "total_duration_ns": response.get("total_duration"),
                        "load_duration_ns": response.get("load_duration"),
                        "prompt_eval_count": response.get("prompt_eval_count"),
                        "eval_count": response.get("eval_count"),
                    },
                    "ollama_rss_bytes": rss,
                }
            )

    expected_calls = lock["formal_run"]["model_call_count_exact"]
    if len(rows) != expected_calls:
        raise ValueError(f"V64 call-count mismatch: {len(rows)} != {expected_calls}")
    raw = {
        "schema": "uruha_leftbrain_meaning_contract_raw_v64",
        "experiment_id": prereg["experiment_id"],
        "started_from_commit": _git("rev-parse", "HEAD"),
        "completed_at": datetime.now(TZ).isoformat(),
        "preflight": preflight,
        "model_snapshot": snapshot,
        "condition_order": list(CONDITIONS),
        "case_count": len(dataset["cases"]),
        "model_call_count": len(rows),
        "transport_attempt_count": len(rows),
        "transport_error_count": transport_errors,
        "peak_ollama_rss_bytes": peak_rss or None,
        "rows": rows,
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
    print(json.dumps({key: raw[key] for key in ("case_count", "model_call_count", "transport_error_count", "peak_ollama_rss_bytes")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
