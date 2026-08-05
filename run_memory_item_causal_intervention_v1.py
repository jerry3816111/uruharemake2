#!/usr/bin/env python3
"""Run the frozen exact-record memory causal experiment."""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import memory_item_causal_intervention_v1 as experiment
import run_rightbrain_pipeline_shadow_v61 as v61


ROOT = Path(__file__).resolve().parent
PREREG_PATH = ROOT / "configs/memory_item_causal_intervention_v1_preregistration.json"
CASES_PATH = ROOT / "configs/memory_item_causal_intervention_v1_cases.json"
LOCK_PATH = ROOT / "configs/memory_item_causal_intervention_v1_harness_lock.json"
LOCAL_DIR = ROOT / "analysis/local_memory_item_causal_intervention_v1"
RAW_PATH = LOCAL_DIR / "raw.jsonl"


class _AuditedCompletionProxy:
    def __init__(self, target, seed, call_log):
        self._target = target
        self._seed = int(seed)
        self._call_log = call_log

    def create(self, *args, **kwargs):
        kwargs["temperature"] = 0.0
        kwargs["seed"] = self._seed
        row = {
            "model": kwargs.get("model"),
            "seed": self._seed,
            "temperature": 0.0,
            "status": "started",
        }
        self._call_log.append(row)
        started = time.monotonic()
        try:
            response = self._target.create(*args, **kwargs)
        except Exception as exc:
            row.update(
                {
                    "status": "error",
                    "elapsed_seconds": round(time.monotonic() - started, 6),
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )
            raise
        row.update(
            {
                "status": "returned",
                "elapsed_seconds": round(time.monotonic() - started, 6),
            }
        )
        return response


class _ChatProxy:
    def __init__(self, completions):
        self.completions = completions


class _AuditedClient:
    def __init__(self, target_completions, seed, call_log):
        self.chat = _ChatProxy(_AuditedCompletionProxy(target_completions, seed, call_log))


def install_audited_client(bot, seed, call_log):
    current = bot.client_logic.chat.completions
    target = getattr(current, "_target", current)
    audited = _AuditedClient(target, seed, call_log)
    bot.client_logic = audited
    bot.left_brain.client_logic = audited


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )
    os.replace(temporary, path)


def load_jsonl(path):
    if not Path(path).exists():
        return []
    return [
        json.loads(line)
        for line in Path(path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def verify_lock(lock):
    failed = []
    for artifact in lock["frozen_artifacts"].values():
        path = ROOT / artifact["path"]
        if not path.is_file() or experiment.file_sha256(path) != artifact["sha256"]:
            failed.append(artifact["path"])
    if failed:
        raise ValueError(f"memory-item V1 frozen artifact drift: {failed}")


def run_preflight(lock):
    command = [sys.executable, "-m", "unittest", "-q", "test_memory_item_causal_intervention_v1.py"]
    completed = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
        env={**os.environ, "URUHA_SKIP_AUTO_VENV": "1", "TOKENIZERS_PARALLELISM": "false"},
    )
    combined = f"{completed.stdout}\n{completed.stderr}"
    match = re.search(r"Ran\s+(\d+)\s+tests?", combined)
    observed = int(match.group(1)) if match else None
    expected = int(lock["preflight"]["expected_test_count"])
    return {
        "returncode": completed.returncode,
        "observed_test_count": observed,
        "expected_test_count": expected,
        "passed": completed.returncode == 0 and observed == expected,
    }


def installed_model_digest(tag):
    rows = v61._get_json(v61.OLLAMA_TAGS_URL).get("models") or []
    return next((row.get("digest") for row in rows if row.get("name") == tag), None)


def run_condition(bot, case, condition, call_log):
    with tempfile.TemporaryDirectory(prefix=f"uruha_mici_v1_{case['id']}_") as temporary:
        with contextlib.redirect_stdout(io.StringIO()):
            bot.reset_session(db_path=temporary)
            experiment.seed_case(bot.memory, case)
            event = bot.ingest_event(case["user_input"])
        audit = experiment.capture_retrieval_audit(event["memory_data"], case)
        call_start = len(call_log)
        started = time.monotonic()
        experiment.apply_condition(bot, event, case, condition)
        with contextlib.redirect_stdout(io.StringIO()):
            tick = bot.cognitive_tick(event)
            reply = bot.right_brain.speak(
                case["user_input"],
                tick["logic"],
                event["memory_data"],
                event["psyche_before"],
            )
        elapsed = time.monotonic() - started
        score = experiment.score_outcome(
            case,
            condition,
            audit,
            event,
            tick["logic"],
            reply,
            elapsed,
            call_log[call_start:],
        )
        return {
            "schema": "uruha_memory_item_causal_raw_v1",
            "case_id": case["id"],
            "category": case["category"],
            "case_sha256": experiment.canonical_sha256(case),
            **score,
        }


def main():
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--overwrite", action="store_true")
    mode.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    if v61._git("branch", "--show-current") != "main":
        raise SystemExit("formal memory-item V1 inference requires merged main")
    if not v61._tracked_tree_clean() or v61._git("status", "--porcelain"):
        raise SystemExit("formal memory-item V1 inference requires a clean worktree")

    prereg = load_json(PREREG_PATH)
    lock = load_json(LOCK_PATH)
    verify_lock(lock)
    preflight = run_preflight(lock)
    if not preflight["passed"]:
        raise SystemExit(f"memory-item V1 preflight failed: {preflight}")
    if v61._ollama_version() != lock["environment"]["ollama_version"]:
        raise SystemExit("memory-item V1 Ollama version drift")
    model = prereg["model"]
    if installed_model_digest(model["ollama_tag"]) != model["digest"]:
        raise SystemExit("memory-item V1 LeftBrain model missing or drifted")

    cases = experiment.load_cases(CASES_PATH)
    sequence = experiment.expected_sequence(cases)
    expected = int(prereg["scope"]["expected_decision_run_count"])
    if len(sequence) != expected:
        raise SystemExit("memory-item V1 condition budget drift")
    if RAW_PATH.exists() and not (args.overwrite or args.resume):
        raise SystemExit("memory-item V1 raw result exists; use --overwrite or --resume")
    rows = load_jsonl(RAW_PATH) if args.resume else []
    expected_prefix = [(case["id"], condition) for case, condition in sequence[: len(rows)]]
    observed_prefix = [(row["case_id"], row["condition"]) for row in rows]
    if observed_prefix != expected_prefix:
        raise SystemExit("memory-item V1 resume prefix mismatch")

    with v61._isolated_brain(prereg) as (bot, call_log, isolation):
        call_log.clear()
        install_audited_client(bot, prereg["generation"]["seed"], call_log)
        for case, condition in sequence[len(rows) :]:
            print(f"[{len(rows)+1}/{expected}] {case['id']} {condition}", flush=True)
            row = run_condition(bot, case, condition, call_log)
            rows.append(row)
            write_jsonl(RAW_PATH, rows)
    metadata = {
        "row_count": len(rows),
        "preflight": preflight,
        "isolation": isolation,
        "raw_path": str(RAW_PATH),
    }
    (LOCAL_DIR / "run_metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(metadata, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
