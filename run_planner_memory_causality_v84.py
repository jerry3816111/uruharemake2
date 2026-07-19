#!/usr/bin/env python3
"""Run the frozen V84 planner-memory causal intervention."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

import planner_memory_causality_v84 as v84
import planner_supervision_bounded_review_v82 as v82
import planner_supervision_v76 as v76
import run_rightbrain_pipeline_shadow_v61 as v61


ROOT = Path(__file__).resolve().parent
PREREG_PATH = ROOT / "configs/planner_memory_causality_v84_preregistration.json"
LOCK_PATH = ROOT / "configs/planner_memory_causality_v84_harness_lock.json"


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def verify_lock(lock):
    failures = []
    for artifact in lock["frozen_artifacts"].values():
        path = ROOT / artifact["path"]
        if not path.is_file() or v84.file_sha256(path) != artifact["sha256"]:
            failures.append(artifact["path"])
    if failures:
        raise ValueError(f"V84 frozen artifact drift: {failures}")


def run_preflight(lock):
    command = [sys.executable, "-m", "unittest", "-v", "test_planner_memory_causality_v84.py"]
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


def build_packets(contract, right_brain):
    paths = {name: ROOT / artifact["path"] for name, artifact in contract["private_sources"].items()}
    selected = v84.select_fresh_candidates(
        v76.load_jsonl(paths["candidate_queue"]),
        v76.load_jsonl(paths["session_manifest"]),
        v76.load_jsonl(paths["v79_queue"]),
        v76.load_jsonl(paths["v81_packets"]),
        v76.load_jsonl(paths["v82_packets"]),
        contract,
    )
    return [v84.build_packet(right_brain, candidate) for candidate in selected]


def run_call(packet, contract, seed, condition):
    request = v84.build_request(packet, contract, condition, seed)
    started = time.monotonic()
    response = None
    transport_error = ""
    try:
        response = v82._post_json_bounded(
            request,
            curl_max_time_seconds=contract["generation"]["curl_max_time_seconds"],
            hard_deadline_seconds=contract["generation"]["hard_deadline_seconds"],
        )
    except Exception as exc:
        transport_error = str(exc) or type(exc).__name__
    elapsed = time.monotonic() - started
    response = response if isinstance(response, dict) else {}
    reply = str((response.get("message") or {}).get("content") or "").strip()
    return {
        "schema": "uruha_planner_memory_causality_raw_v84",
        "candidate_id": packet["candidate_id"],
        "scenario_family": packet["scenario_family"],
        "seed": seed,
        "condition": condition,
        "packet_sha256": packet["packet_sha256"],
        "payload_sha256": packet["payload_sha256"][condition],
        "request_sha256": v76.canonical_sha256(request),
        "model": contract["model"]["ollama_tag"],
        "model_digest": contract["model"]["digest"],
        "response_model": response.get("model"),
        "done": response.get("done") is True,
        "transport_error": transport_error,
        "elapsed_seconds": round(elapsed, 6),
        "prompt_eval_count": response.get("prompt_eval_count"),
        "eval_count": response.get("eval_count"),
        "peak_ollama_rss_bytes": v61._peak_ollama_rss_bytes(),
        "raw_reply": reply,
        "score": v84.score_reply(packet, reply),
        "production_memory_write_count": 0,
        "physical_vrm_action_count": 0,
    }


def main():
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--overwrite", action="store_true")
    mode.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    if v61._git("branch", "--show-current") != "main":
        raise SystemExit("formal V84 run requires merged main")
    if not v61._tracked_tree_clean() or v61._git("status", "--porcelain"):
        raise SystemExit("formal V84 run requires a clean worktree")
    contract = load_json(PREREG_PATH)
    lock = load_json(LOCK_PATH)
    verify_lock(lock)
    if not lock["formal_run"]["candidate_inference_authorized"]:
        raise SystemExit("V84 harness lock does not authorize formal inference")
    preflight = run_preflight(lock)
    if not preflight["passed"]:
        raise SystemExit(f"V84 frozen preflight failed: {preflight}")
    source_checks = v84.verify_private_sources(contract, ROOT)
    if v61._ollama_version() != lock["environment"]["ollama_version"]:
        raise SystemExit("V84 Ollama version drift")
    installed = v82.installed_model_digests()
    model_name = contract["model"]["ollama_tag"]
    if installed.get(model_name) != contract["model"]["digest"]:
        raise SystemExit("V84 frozen RightBrain model missing or drifted")

    local_paths = {name: ROOT / value for name, value in contract["local_paths"].items()}
    raw_path = local_paths["raw_results"]
    if raw_path.exists() and not (args.overwrite or args.resume):
        raise SystemExit("V84 raw result exists; pass --resume or --overwrite")
    with v61._isolated_brain(contract) as (bot, leftbrain_calls, isolation):
        packets = build_packets(contract, bot.right_brain)
    if leftbrain_calls:
        raise SystemExit("V84 packet construction unexpectedly called LeftBrain")
    v76.write_jsonl(local_paths["packet_queue"], packets)
    rows = v76.load_jsonl(raw_path) if args.resume else []
    sequence = v84.validate_resume_prefix(packets, rows, contract)
    expected = int(contract["scope"]["expected_model_call_count"])
    if len(sequence) != expected:
        raise SystemExit("V84 call budget drift")
    for seed, packet, condition in sequence[len(rows):]:
        print(f"[{len(rows)+1}/{expected}] seed={seed} condition={condition}", flush=True)
        rows.append(run_call(packet, contract, seed, condition))
        v76.write_jsonl(raw_path, rows)
    metadata = {
        "source_checks": source_checks,
        "isolation": isolation,
        "packet_count": len(packets),
        "attempt_count": len(rows),
        "preflight": preflight,
        "raw_path": str(raw_path),
    }
    print(json.dumps(metadata, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
