#!/usr/bin/env python3
"""Run the frozen V3 static-vs-conditional persona development screen."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

import planner_supervision_bounded_review_v82 as v82
import public_persona_contract_v3 as contract
import run_rightbrain_pipeline_shadow_v61 as v61
from project_paths import PUBLIC_PERSONA_CONTRACT_V3_DATASET_PATH, PUBLIC_PERSONA_CONTRACT_V3_RAW_PATH
from uruha_brain_mac import RIGHT_BRAIN_MODEL_SYSTEM_PROMPT, RightBrain


ROOT = Path(__file__).resolve().parent
PREREGISTRATION = ROOT / "configs/public_persona_contract_v3_preregistration.json"
LOCK = ROOT / "configs/public_persona_contract_v3_harness_lock.json"
CONDITIONS = ("c0_static_persona_brief", "t1_conditional_surface_brief")


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha_bytes(value):
    return hashlib.sha256(value).hexdigest()


def sha_file(path):
    return sha_bytes(Path(path).read_bytes())


def canonical_sha(value):
    return sha_bytes(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    )


def verify_lock(lock):
    failed = []
    for artifact in lock["frozen_artifacts"].values():
        path = ROOT / artifact["path"]
        if not path.is_file() or sha_file(path) != artifact["sha256"]:
            failed.append(artifact["path"])
    if failed:
        raise ValueError(f"V3 frozen artifact drift: {failed}")


def run_preflight(lock):
    completed = subprocess.run(
        [sys.executable, "-m", "unittest", "-v", "test_public_persona_contract_v3.py"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
        env={**os.environ, "URUHA_SKIP_AUTO_VENV": "1", "TOKENIZERS_PARALLELISM": "false"},
    )
    combined = f"{completed.stdout}\n{completed.stderr}"
    matched = re.search(r"Ran\s+(\d+)\s+tests?", combined)
    observed = int(matched.group(1)) if matched else None
    expected = int(lock["preflight"]["expected_test_count"])
    return {
        "returncode": completed.returncode,
        "observed_test_count": observed,
        "expected_test_count": expected,
        "passed": completed.returncode == 0 and observed == expected,
    }


def without_persona(payload):
    copied = copy.deepcopy(payload)
    copied["context"].pop("persona_expression_brief", None)
    return copied


def build_payload(right_brain, case, condition):
    logic = copy.deepcopy(case["logic"])
    previous = right_brain.public_persona_conditional_brief_enabled
    right_brain.public_persona_conditional_brief_enabled = condition == CONDITIONS[1]
    try:
        payload_text = right_brain._build_model_surface_payload(
            logic,
            case["psyche"],
            case["persona_evaluation"]["maximum_characters"],
        )
    finally:
        right_brain.public_persona_conditional_brief_enabled = previous
    payload = json.loads(payload_text)
    return logic, payload_text, payload


def build_request(preregistration, payload_text, case_index):
    generation = preregistration["generation"]
    return {
        "model": preregistration["model"]["ollama_tag"],
        "messages": [
            {"role": "system", "content": RIGHT_BRAIN_MODEL_SYSTEM_PROMPT},
            {"role": "user", "content": payload_text},
        ],
        "stream": False,
        "think": bool(preregistration["model"]["thinking"]),
        "keep_alive": "20m",
        "options": {
            "temperature": generation["temperature"],
            "top_p": generation["top_p"],
            "num_ctx": generation["context_tokens"],
            "num_predict": generation["maximum_output_tokens"],
            "seed": generation["seed"] + case_index,
        },
    }


def atomic_write(path, payload):
    path = Path(path)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=PUBLIC_PERSONA_CONTRACT_V3_RAW_PATH)
    args = parser.parse_args()
    if v61._git("branch", "--show-current") != "main":
        raise SystemExit("formal V3 model screen requires merged main")
    if not v61._tracked_tree_clean() or v61._git("status", "--porcelain"):
        raise SystemExit("formal V3 model screen requires a clean worktree")
    if v61._git("rev-parse", "HEAD") != v61._git("rev-parse", "origin/main"):
        raise SystemExit("formal V3 model screen requires HEAD at origin/main")
    if args.output.exists():
        raise SystemExit("V3 raw result already exists; refusing a second formal run")

    preregistration = load(PREREGISTRATION)
    lock = load(LOCK)
    verify_lock(lock)
    preflight = run_preflight(lock)
    if not preflight["passed"]:
        raise SystemExit(f"V3 preflight failed: {preflight}")
    installed = v82.installed_model_digests()
    model = preregistration["model"]
    if installed.get(model["ollama_tag"]) != model["digest"]:
        raise SystemExit("V3 model missing or digest drifted")

    dataset = load(PUBLIC_PERSONA_CONTRACT_V3_DATASET_PATH)
    right_brain = RightBrain(load_model=False)
    rows = []
    for case_index, case in enumerate(dataset["cases"]):
        paired = {}
        for condition in CONDITIONS:
            logic, payload_text, payload = build_payload(right_brain, case, condition)
            paired[condition] = {
                "logic": logic,
                "payload_text": payload_text,
                "payload": payload,
            }
        if without_persona(paired[CONDITIONS[0]]["payload"]) != without_persona(
            paired[CONDITIONS[1]]["payload"]
        ):
            raise SystemExit(f"non-persona payload drift: {case['case_id']}")
        active = case["context"] in contract.POLICIES
        if not active and paired[CONDITIONS[0]]["payload_text"] != paired[CONDITIONS[1]]["payload_text"]:
            raise SystemExit(f"inactive payload drift: {case['case_id']}")

        order = CONDITIONS if case_index % 2 == 0 else tuple(reversed(CONDITIONS))
        for condition in order:
            packet = paired[condition]
            request = build_request(preregistration, packet["payload_text"], case_index)
            started = time.monotonic()
            response = None
            transport_error = ""
            try:
                response = v82._post_json_bounded(
                    request,
                    curl_max_time_seconds=preregistration["generation"]["curl_max_time_seconds"],
                    hard_deadline_seconds=preregistration["generation"]["hard_deadline_seconds"],
                )
            except Exception as exc:
                transport_error = str(exc) or type(exc).__name__
            elapsed = time.monotonic() - started
            response = response if isinstance(response, dict) else {}
            message = response.get("message") or {}
            raw_reply = str(message.get("content") or "").strip()
            rows.append(
                {
                    "schema": "uruha_public_persona_contract_raw_row_v3",
                    "case_id": case["case_id"],
                    "case_index": case_index,
                    "context": case["context"],
                    "contract_active": active,
                    "condition": condition,
                    "condition_order_index": order.index(condition),
                    "payload_sha256": sha_bytes(packet["payload_text"].encode("utf-8")),
                    "nonpersona_payload_sha256": canonical_sha(without_persona(packet["payload"])),
                    "persona_expression_brief": packet["payload"]["context"]["persona_expression_brief"],
                    "request_sha256": canonical_sha(request),
                    "model": model["ollama_tag"],
                    "model_digest": model["digest"],
                    "response_model": response.get("model"),
                    "done": response.get("done") is True,
                    "transport_error": transport_error,
                    "elapsed_seconds": round(elapsed, 6),
                    "prompt_eval_count": response.get("prompt_eval_count"),
                    "eval_count": response.get("eval_count"),
                    "peak_ollama_rss_bytes": v61._peak_ollama_rss_bytes(),
                    "raw_reply": raw_reply,
                    "raw_reply_sha256": sha_bytes(raw_reply.encode("utf-8")),
                    "tool_calls": message.get("tool_calls") or [],
                }
            )
            report = {
                "schema": "uruha_public_persona_contract_development_raw_v3",
                "experiment_id": preregistration["experiment_id"],
                "git_head": v61._git("rev-parse", "HEAD"),
                "preregistration_sha256": sha_file(PREREGISTRATION),
                "dataset_sha256": sha_file(PUBLIC_PERSONA_CONTRACT_V3_DATASET_PATH),
                "harness_lock_sha256": sha_file(LOCK),
                "system_prompt_sha256": sha_bytes(RIGHT_BRAIN_MODEL_SYSTEM_PROMPT.encode("utf-8")),
                "case_count": len(dataset["cases"]),
                "condition_count": len(CONDITIONS),
                "expected_model_call_count": preregistration["scope"]["expected_model_call_count"],
                "completed_model_call_count": len(rows),
                "preflight": preflight,
                "gold_or_expected_reply_in_raw": False,
                "v2_holdout_content_review_count": 0,
                "production_memory_write_count": 0,
                "physical_vrm_action_count": 0,
                "rows": rows,
            }
            atomic_write(args.output, report)
            print(
                f"[{len(rows)}/{preregistration['scope']['expected_model_call_count']}] "
                f"{case['case_id']} {condition} {elapsed:.3f}s",
                flush=True,
            )
    if len(rows) != preregistration["scope"]["expected_model_call_count"]:
        raise SystemExit("V3 model call count drift")
    print(json.dumps({"output": str(args.output), "model_calls": len(rows)}, indent=2))


if __name__ == "__main__":
    main()
