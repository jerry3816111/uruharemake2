#!/usr/bin/env python3
"""Run the frozen local atomic-claim judge calibration exactly once."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from reflection_layer_audit_v1 import (
    SYSTEM_PROMPT,
    judge_prompt,
    parse_judgments,
    response_schema,
)


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "reflection_layer_audit_v1_preregistration.json"
DATASET_PATH = ROOT / "datasets" / "reflection_layer_audit_v1_calibration.json"
LOCK_PATH = ROOT / "configs" / "reflection_layer_audit_v1_harness_lock.json"
DEFAULT_OUTPUT = ROOT / "reports" / "reflection_layer_audit_v1_raw.json"
TZ = ZoneInfo("Asia/Tokyo")


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_value(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def now():
    return datetime.now(TZ).isoformat(timespec="seconds")


def atomic_write(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    temporary.replace(path)


def verify_frozen_inputs(config, dataset, lock):
    if git_value("branch", "--show-current") != lock["required_run_branch"]:
        raise ValueError("reflection layer audit must run from clean main")
    if git_value("status", "--porcelain", "--untracked-files=no"):
        raise ValueError("tracked worktree must be clean")
    if len(dataset["cases"]) != config["case_count"]:
        raise ValueError("case count drift")
    for relative, expected in lock["frozen_artifacts"].items():
        if sha256(ROOT / relative) != expected:
            raise ValueError(f"frozen artifact drift: {relative}")


def model_snapshot(config):
    model = config["judge"]["model"]
    listing = subprocess.check_output(["ollama", "list"], text=True)
    rows = [line.strip() for line in listing.splitlines() if line.startswith(model)]
    if len(rows) != 1 or config["judge"]["ollama_list_id"] not in rows[0]:
        raise ValueError(f"judge model snapshot mismatch: {rows}")
    return {"model": model, "ollama_list_row": rows[0]}


def judge_case(case, config):
    schema = response_schema(case)
    prompt = judge_prompt(case)
    payload = {
        "model": config["judge"]["model"],
        "stream": False,
        "think": False,
        "format": schema,
        "options": {
            "temperature": config["judge"]["temperature"],
            "seed": config["judge"]["seed"],
            "num_predict": 128,
        },
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
    }
    request = urllib.request.Request(
        "http://127.0.0.1:11434/api/chat",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=180) as response:
        result = json.load(response)
    raw_response = str((result.get("message") or {}).get("content") or "")
    try:
        judgments = parse_judgments(raw_response, case)
        schema_valid = True
        parse_error = None
    except ValueError as exc:
        judgments = {}
        schema_valid = False
        parse_error = str(exc)
    return {
        "case": case,
        "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        "raw_response": raw_response,
        "judgments": judgments,
        "schema_valid": schema_valid,
        "parse_error": parse_error,
        "eval_count": result.get("eval_count"),
        "total_duration_ns": result.get("total_duration"),
    }


def run(output=DEFAULT_OUTPUT):
    if output.exists():
        raise FileExistsError(f"refusing to overwrite result: {output}")
    config = load_json(CONFIG_PATH)
    dataset = load_json(DATASET_PATH)
    lock = load_json(LOCK_PATH)
    verify_frozen_inputs(config, dataset, lock)
    snapshot = model_snapshot(config)
    started_at = now()
    rows = [judge_case(case, config) for case in dataset["cases"]]
    if len(rows) != config["judge"]["maximum_model_calls"]:
        raise ValueError("model call accounting mismatch")
    report = {
        "schema": "uruha_reflection_layer_audit_raw_v1",
        "evidence_status": "frozen_calibration_completed_without_retry_or_tuning",
        "started_at": started_at,
        "completed_at": now(),
        "runner_commit": git_value("rev-parse", "HEAD"),
        "runner_branch": git_value("branch", "--show-current"),
        "preregistration_sha256": sha256(CONFIG_PATH),
        "dataset_sha256": sha256(DATASET_PATH),
        "harness_lock_sha256": sha256(LOCK_PATH),
        "judge_snapshot": snapshot,
        "model_call_count": len(rows),
        "thinking": False,
        "paid_api_used": False,
        "human_rating_used": False,
        "rows": rows,
    }
    atomic_write(output, report)
    print(output)
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    run(args.output)


if __name__ == "__main__":
    main()
