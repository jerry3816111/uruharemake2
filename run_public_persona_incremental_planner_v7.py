#!/usr/bin/env python3
"""Run the frozen V7 incremental planner-obligation mechanism screen."""

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
import public_persona_contract_v3 as v3
import public_persona_incremental_planner_v7 as incremental
import run_public_persona_contract_v3_development as v3_runner
import run_rightbrain_pipeline_shadow_v61 as v61
from uruha_brain_mac import RIGHT_BRAIN_MODEL_SYSTEM_PROMPT, RightBrain


ROOT = Path(__file__).resolve().parent
PREREGISTRATION = ROOT / "configs/public_persona_incremental_planner_v7_preregistration.json"
LOCK = ROOT / "configs/public_persona_incremental_planner_v7_harness_lock.json"
DATASET = ROOT / "datasets/public_persona_contract_v3_development.json"
DEFAULT_OUTPUT = ROOT / "reports/public_persona_incremental_planner_v7_raw.json"
CONDITIONS = ("c0_existing_speech_plan", "t1_incremental_dialogue_obligations")
INCREMENTAL_FIELDS = ("dialogue_obligations", "epistemic_boundary")


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha_bytes(value):
    return hashlib.sha256(value).hexdigest()


def sha_file(path):
    return sha_bytes(Path(path).read_bytes())


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def canonical_sha(value):
    return sha_bytes(canonical(value).encode("utf-8"))


def without_incremental_fields(payload):
    copied = copy.deepcopy(payload)
    plan = copied.get("leftbrain_plan") or {}
    for field in INCREMENTAL_FIELDS:
        plan.pop(field, None)
    return copied


def verify_lock(lock):
    drift = []
    for artifact in lock["frozen_artifacts"].values():
        path = ROOT / artifact["path"]
        if not path.is_file() or sha_file(path) != artifact["sha256"]:
            drift.append(artifact["path"])
    if drift:
        raise ValueError(f"V7 frozen artifact drift: {drift}")


def run_preflight(lock):
    completed = subprocess.run(
        [sys.executable, "-m", "unittest", "-v", "test_public_persona_incremental_planner_v7.py"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
        env={**os.environ, "URUHA_SKIP_AUTO_VENV": "1", "TOKENIZERS_PARALLELISM": "false"},
    )
    output = f"{completed.stdout}\n{completed.stderr}"
    matched = re.search(r"Ran\s+(\d+)\s+tests?", output)
    observed = int(matched.group(1)) if matched else None
    expected = int(lock["preflight"]["expected_test_count"])
    return {
        "returncode": completed.returncode,
        "observed_test_count": observed,
        "expected_test_count": expected,
        "passed": completed.returncode == 0 and observed == expected,
    }


def build_payload(right_brain, case, condition):
    logic, _, baseline_payload = v3_runner.build_payload(
        right_brain, case, v3_runner.CONDITIONS[0]
    )
    contract = incremental.compile_incremental_contract(logic)
    if condition == CONDITIONS[0]:
        payload = baseline_payload
    elif condition == CONDITIONS[1]:
        payload = incremental.project_into_payload(baseline_payload, contract)
    else:
        raise ValueError(f"unsupported V7 condition: {condition}")
    payload_text = canonical(payload)
    return logic, contract, payload_text, payload


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
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    if v61._git("branch", "--show-current") != "main":
        raise SystemExit("formal V7 screen requires merged main")
    if not v61._tracked_tree_clean() or v61._git("status", "--porcelain"):
        raise SystemExit("formal V7 screen requires a clean worktree")
    if v61._git("rev-parse", "HEAD") != v61._git("rev-parse", "origin/main"):
        raise SystemExit("formal V7 screen requires HEAD at origin/main")
    if args.output.exists():
        raise SystemExit("V7 raw result already exists; refusing a second formal run")

    preregistration = load(PREREGISTRATION)
    lock = load(LOCK)
    verify_lock(lock)
    preflight = run_preflight(lock)
    if not preflight["passed"]:
        raise SystemExit(f"V7 preflight failed: {preflight}")
    model = preregistration["model"]
    if v82.installed_model_digests().get(model["ollama_tag"]) != model["digest"]:
        raise SystemExit("V7 model missing or digest drifted")

    dataset = load(DATASET)
    right_brain = RightBrain(load_model=False)
    rows = []
    for case_index, case in enumerate(dataset["cases"]):
        packets = {condition: build_payload(right_brain, case, condition) for condition in CONDITIONS}
        _, control_contract, control_text, control_payload = packets[CONDITIONS[0]]
        _, treatment_contract, treatment_text, treatment_payload = packets[CONDITIONS[1]]
        active = case["context"] in v3.POLICIES
        if without_incremental_fields(treatment_payload) != control_payload:
            raise SystemExit(f"V7 non-incremental payload drift: {case['case_id']}")
        if not active and control_text != treatment_text:
            raise SystemExit(f"V7 inactive payload drift: {case['case_id']}")
        if active and control_text == treatment_text:
            raise SystemExit(f"V7 active payload unchanged: {case['case_id']}")
        if control_contract != treatment_contract:
            raise SystemExit(f"V7 contract drift across conditions: {case['case_id']}")

        order = CONDITIONS if case_index % 2 == 0 else tuple(reversed(CONDITIONS))
        for order_index, condition in enumerate(order):
            _, contract, payload_text, payload = packets[condition]
            request = build_request(preregistration, payload_text, case_index)
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
            reply = str(message.get("content") or "").strip()
            rows.append(
                {
                    "case_id": case["case_id"],
                    "case_index": case_index,
                    "context": case["context"],
                    "contract_active": active,
                    "condition": condition,
                    "condition_order_index": order_index,
                    "payload_sha256": sha_bytes(payload_text.encode("utf-8")),
                    "baseline_payload_sha256": canonical_sha(without_incremental_fields(payload)),
                    "incremental_contract_sha256": canonical_sha(contract),
                    "request_sha256": canonical_sha(request),
                    "model": model["ollama_tag"],
                    "model_digest": model["digest"],
                    "response_model": response.get("model"),
                    "done": response.get("done") is True,
                    "transport_error": transport_error,
                    "elapsed_seconds": round(elapsed, 6),
                    "peak_ollama_rss_bytes": v61._peak_ollama_rss_bytes(),
                    "raw_reply": reply,
                    "raw_reply_sha256": sha_bytes(reply.encode("utf-8")),
                    "tool_calls": message.get("tool_calls") or [],
                }
            )
            report = {
                "schema": "uruha_public_persona_incremental_planner_raw_v7",
                "experiment_id": preregistration["experiment_id"],
                "git_head": v61._git("rev-parse", "HEAD"),
                "preregistration_sha256": sha_file(PREREGISTRATION),
                "dataset_sha256": sha_file(DATASET),
                "harness_lock_sha256": sha_file(LOCK),
                "system_prompt_sha256": sha_bytes(RIGHT_BRAIN_MODEL_SYSTEM_PROMPT.encode("utf-8")),
                "case_count": len(dataset["cases"]),
                "condition_count": len(CONDITIONS),
                "expected_model_call_count": preregistration["scope"]["expected_model_call_count"],
                "completed_model_call_count": len(rows),
                "preflight": preflight,
                "gold_or_expected_reply_in_raw": False,
                "v4_scorer_in_model_payload": False,
                "specificity_scorer_in_model_payload": False,
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
        raise SystemExit("V7 model call count drift")
    print(json.dumps({"output": str(args.output), "model_calls": len(rows)}, indent=2))


if __name__ == "__main__":
    main()
