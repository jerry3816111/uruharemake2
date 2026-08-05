#!/usr/bin/env python3
"""Run the known-fixture development comparison for recall V1."""

from __future__ import annotations

import contextlib
import io
import json
import os
import re
import subprocess
import tempfile
import time
from pathlib import Path

import memory_item_causal_intervention_v1 as experiment
import run_memory_item_causal_intervention_v1 as baseline_runner
import run_rightbrain_pipeline_shadow_v61 as v61


ROOT = Path(__file__).resolve().parent
PREREG = ROOT / "configs/high_confidence_memory_recall_v1_preregistration.json"
BASE_PREREG = ROOT / "configs/memory_item_causal_intervention_v1_preregistration.json"
CASES = ROOT / "configs/memory_item_causal_intervention_v1_cases.json"
OUTPUT_DIR = ROOT / "analysis/local_high_confidence_memory_recall_v1_development"
RAW = OUTPUT_DIR / "raw.jsonl"


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def run_preflight():
    command = [
        os.environ.get("PYTHON", os.sys.executable),
        "-m",
        "unittest",
        "-q",
        "test_high_confidence_memory_recall_v1.py",
        "test_high_confidence_memory_recall_v1_preregistration.py",
    ]
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
    return {
        "passed": completed.returncode == 0,
        "observed_test_count": int(match.group(1)) if match else None,
        "returncode": completed.returncode,
    }


def write_jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )
    os.replace(temporary, path)


def run_condition(bot, case, condition, call_log):
    with tempfile.TemporaryDirectory(prefix=f"uruha_recall_v1_{case['id']}_") as temporary:
        with contextlib.redirect_stdout(io.StringIO()):
            bot.reset_session(db_path=temporary)
            experiment.seed_case(bot.memory, case)
            event = bot.ingest_event(case["user_input"])
        audit = experiment.capture_retrieval_audit(event["memory_data"], case)
        call_start = len(call_log)
        started = time.monotonic()
        experiment.apply_condition(bot, event, case, condition)
        event["memory_data"]["experimental_high_confidence_recall_v1_enabled"] = True
        with contextlib.redirect_stdout(io.StringIO()):
            tick = bot.cognitive_tick(event)
            logic = tick["logic"]
            reply = bot.right_brain.speak(
                case["user_input"],
                logic,
                event["memory_data"],
                event["psyche_before"],
            )
        elapsed = time.monotonic() - started
        row = experiment.score_outcome(
            case,
            condition,
            audit,
            event,
            logic,
            reply,
            elapsed,
            call_log[call_start:],
        )
        return {
            "schema": "uruha_high_confidence_memory_recall_development_raw_v1",
            "case_id": case["id"],
            "category": case["category"],
            "case_sha256": experiment.canonical_sha256(case),
            "planner_path": logic.get("planner_path"),
            "memory_recall_contract": logic.get("memory_recall_contract") or {},
            **row,
        }


def main():
    prereg = load_json(PREREG)
    base_prereg = load_json(BASE_PREREG)
    preflight = run_preflight()
    if not preflight["passed"]:
        raise SystemExit(f"recall V1 development preflight failed: {preflight}")
    model = base_prereg["model"]
    if baseline_runner.installed_model_digest(model["ollama_tag"]) != model["digest"]:
        raise SystemExit("required qwen2.5:7b model missing or drifted")

    cases = experiment.load_cases(CASES)
    sequence = experiment.expected_sequence(cases)
    expected = prereg["development_checks"]["expected_decision_run_count"]
    if len(sequence) != expected:
        raise SystemExit("development condition count drift")

    rows = []
    with v61._isolated_brain(base_prereg) as (bot, call_log, isolation):
        call_log.clear()
        baseline_runner.install_audited_client(
            bot,
            base_prereg["generation"]["seed"],
            call_log,
        )
        for index, (case, condition) in enumerate(sequence, start=1):
            print(f"[{index}/{expected}] {case['id']} {condition}", flush=True)
            rows.append(run_condition(bot, case, condition, call_log))
            write_jsonl(RAW, rows)

    metadata = {
        "schema": "uruha_high_confidence_memory_recall_development_run_v1",
        "row_count": len(rows),
        "branch": v61._git("branch", "--show-current"),
        "commit": v61._git("rev-parse", "HEAD"),
        "preflight": preflight,
        "isolation": isolation,
        "raw_path": str(RAW),
    }
    (OUTPUT_DIR / "run_metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(metadata, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
