#!/usr/bin/env python3
"""Run the locked V88 fresh-generation plus production-gate holdout."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

import planner_supervision_bounded_review_v82 as v82
import planner_supervision_v76 as v76
import rightbrain_forbidden_projection_v88 as v88
import run_rightbrain_pipeline_shadow_v61 as v61


ROOT = Path(__file__).resolve().parent
PREREG_PATH = ROOT / "configs/rightbrain_forbidden_projection_v88_preregistration.json"
LOCK_PATH = ROOT / "configs/rightbrain_forbidden_projection_v88_harness_lock.json"


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def verify_lock(lock):
    failed = []
    for artifact in lock["frozen_artifacts"].values():
        path = ROOT / artifact["path"]
        if not path.is_file() or v88.file_sha256(path) != artifact["sha256"]:
            failed.append(artifact["path"])
    if failed:
        raise ValueError(f"V88 frozen artifact drift: {failed}")


def run_preflight(lock):
    command = [
        sys.executable,
        "-m",
        "unittest",
        "-v",
        "test_rightbrain_forbidden_conflict_projection_v87.py",
        "test_rightbrain_forbidden_projection_v88.py",
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
    observed = int(match.group(1)) if match else None
    expected = int(lock["preflight"]["expected_test_count"])
    return {
        "returncode": completed.returncode,
        "observed": observed,
        "expected": expected,
        "passed": completed.returncode == 0 and observed == expected,
    }


def load_selection_sources(contract):
    sources = contract["private_sources"]
    candidates = v76.load_jsonl(ROOT / sources["candidate_queue"]["path"])
    manifest = v76.load_jsonl(ROOT / sources["session_manifest"]["path"])
    exclusions = {
        name: v76.load_jsonl(ROOT / sources[name]["path"])
        for name in ("v79", "v81", "v82", "v84", "v86")
    }
    return candidates, manifest, exclusions


def build_packets(contract, right_brain):
    candidates, manifest, exclusions = load_selection_sources(contract)
    selected = v88.select_fresh_candidates(
        candidates,
        manifest,
        exclusions,
        contract,
        right_brain,
    )
    return selected, [v88.build_packet(right_brain, candidate) for candidate in selected]


def run_call(right_brain, candidate, packet, contract, condition, sample_index):
    request = v88.build_request(packet, contract, condition, sample_index)
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
    raw_reply = str((response.get("message") or {}).get("content") or "").strip()
    gate = v88.evaluate_production_gate(right_brain, candidate, packet, condition, raw_reply)
    return {
        "schema": "uruha_rightbrain_forbidden_projection_raw_v88",
        "candidate_id": packet["candidate_id"],
        "stratum": packet["stratum"],
        "condition": condition,
        "sample_index": sample_index,
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
        "peak_ollama_rss_bytes": v61._peak_ollama_rss_bytes(),
        "raw_reply": raw_reply,
        "raw_reply_sha256": hashlib.sha256(raw_reply.encode("utf-8")).hexdigest(),
        "raw_score": v88.score_reply(packet, raw_reply),
        **gate,
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
        raise SystemExit("formal V88 run requires merged main")
    if not v61._tracked_tree_clean() or v61._git("status", "--porcelain"):
        raise SystemExit("formal V88 run requires a clean worktree")
    contract = load_json(PREREG_PATH)
    lock = load_json(LOCK_PATH)
    verify_lock(lock)
    preflight = run_preflight(lock)
    if not preflight["passed"]:
        raise SystemExit(f"V88 preflight failed: {preflight}")
    source_checks = v88.verify_sources(contract, ROOT)
    installed = v82.installed_model_digests()
    model = contract["model"]["ollama_tag"]
    if installed.get(model) != contract["model"]["digest"]:
        raise SystemExit("V88 model missing or drifted")
    with v61._isolated_brain(contract) as (bot, calls, isolation):
        selected, packets = build_packets(contract, bot.right_brain)
        if calls:
            raise SystemExit("V88 packet construction unexpectedly called LeftBrain")
        candidates_by_id = {candidate["id"]: candidate for candidate in selected}
        local = {name: ROOT / value for name, value in contract["local_paths"].items()}
        raw_path = local["raw_results"]
        if raw_path.exists() and not (args.overwrite or args.resume):
            raise SystemExit("V88 raw result exists; pass --resume or --overwrite")
        v76.write_jsonl(local["packet_queue"], packets)
        rows = v76.load_jsonl(raw_path) if args.resume else []
        sequence = v88.validate_resume_prefix(packets, rows, contract)
        if len(sequence) != int(contract["scope"]["expected_model_call_count"]):
            raise SystemExit("V88 call budget drift")
        for packet, condition, sample_index in sequence[len(rows):]:
            print(
                f"[{len(rows)+1}/{len(sequence)}] stratum={packet['stratum']} condition={condition} sample={sample_index}",
                flush=True,
            )
            rows.append(
                run_call(
                    bot.right_brain,
                    candidates_by_id[packet["candidate_id"]],
                    packet,
                    contract,
                    condition,
                    sample_index,
                )
            )
            v76.write_jsonl(raw_path, rows)
    print(
        json.dumps(
            {
                "attempt_count": len(rows),
                "preflight": preflight,
                "sources": source_checks,
                "isolation": isolation,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
