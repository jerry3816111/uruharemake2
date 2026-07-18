#!/usr/bin/env python3
"""Run the frozen V62 matched speech-plan payload ablation once."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import tempfile
from contextlib import redirect_stdout
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import run_rightbrain_pipeline_shadow_v61 as v61


ROOT = Path(__file__).resolve().parent
TZ = ZoneInfo("Asia/Tokyo")
C0 = "c0_tick_logic_payload"
T1 = "t1_full_speech_plan_payload"
CONDITIONS = (C0, T1)
PREREG_PATH = (
    ROOT / "configs/rightbrain_speech_plan_payload_v62_preregistration.json"
)
DATASET_PATH = ROOT / "datasets/rightbrain_speech_plan_payload_v62.json"
CLOSURE_PATH = (
    ROOT / "configs/rightbrain_speech_plan_payload_v62_dataset_closure.json"
)
LOCK_PATH = (
    ROOT / "configs/rightbrain_speech_plan_payload_v62_harness_lock.json"
)
DEFAULT_OUTPUT = (
    ROOT / "reports/rightbrain_speech_plan_payload_v62_raw.json"
)


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_sha256(value):
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _verify_lock(lock):
    failed = []
    for artifact in lock["frozen_artifacts"].values():
        path = ROOT / artifact["path"]
        if not path.exists() or _sha256(path) != artifact["sha256"]:
            failed.append(artifact["path"])
    if failed:
        raise ValueError("V62 frozen artifact drift: " + ", ".join(failed))
    if tuple(lock["conditions"]) != CONDITIONS:
        raise ValueError("V62 condition order drift")
    if lock["formal_run"]["rightbrain_model_call_count_exact"] != 28:
        raise ValueError("V62 model-call budget drift")


def _run_preflight(lock):
    command = [sys.executable, *lock["preflight"]["arguments"]]
    completed = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
        env={
            **os.environ,
            "URUHA_SKIP_AUTO_VENV": "1",
            "TOKENIZERS_PARALLELISM": "false",
        },
    )
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
    condition = prereg["conditions"][T1]
    inventory = {
        row["name"]: row
        for row in (v61._get_json(v61.OLLAMA_TAGS_URL).get("models") or [])
    }
    row = inventory.get(condition["model"])
    if not row or row.get("digest") != condition["digest"]:
        raise ValueError("V62 frozen Qwen3.5 9B model missing or drifted")
    return {
        "ollama_tag": condition["model"],
        "digest": row["digest"],
        "thinking": condition["thinking"],
        "size_bytes": row.get("size"),
        "details": row.get("details") or {},
    }


def _payload_has_speech_plan(payload):
    parsed = json.loads(payload)
    plan = parsed.get("leftbrain_plan") or {}
    return bool(plan.get("content_units"))


def _assert_no_gold_fields(payload):
    parsed = json.loads(payload)
    forbidden = {
        "required_meaning_propositions",
        "forbidden_meaning_propositions",
        "expected_obligation",
        "private_memory_terms",
        "case_id",
    }

    def keys(value):
        found = set()
        if isinstance(value, dict):
            found.update(value)
            for item in value.values():
                found.update(keys(item))
        elif isinstance(value, list):
            for item in value:
                found.update(keys(item))
        return found

    leaked = forbidden.intersection(keys(parsed))
    if leaked:
        raise ValueError("V62 scoring gold leaked into model payload: " + ", ".join(sorted(leaked)))


def build_condition_payloads(
    right_brain,
    base_logic,
    user_input,
    memory_data,
    psyche_state,
    maximum_reply_chars,
):
    """Create a matched pair where only T1 receives the runtime speech plan."""
    base_logic = deepcopy(base_logic)
    if base_logic.get("human_speech_plan"):
        raise ValueError("V62 base cognitive_tick logic already contains speech plan")
    base_logic.setdefault("constraints", {})
    base_logic["constraints"]["max_chars"] = maximum_reply_chars

    plan = right_brain.build_human_speech_plan(
        deepcopy(base_logic),
        user_input,
        deepcopy(memory_data),
        deepcopy(psyche_state),
    )
    if not isinstance(plan, dict) or not plan.get("content_units") or not plan.get("dialogue_act"):
        raise ValueError("V62 runtime speech plan is empty or malformed")

    control_logic = deepcopy(base_logic)
    treatment_logic = right_brain._apply_human_speech_plan_to_logic(
        deepcopy(base_logic),
        deepcopy(plan),
    )
    if not treatment_logic.get("human_speech_plan"):
        raise ValueError("V62 treatment speech plan attachment failed")

    control_payload = right_brain._build_model_surface_payload(
        control_logic,
        deepcopy(psyche_state),
        maximum_reply_chars,
        memory_data=deepcopy(memory_data),
    )
    treatment_payload = right_brain._build_model_surface_payload(
        treatment_logic,
        deepcopy(psyche_state),
        maximum_reply_chars,
        memory_data=deepcopy(memory_data),
    )
    _assert_no_gold_fields(control_payload)
    _assert_no_gold_fields(treatment_payload)
    if _payload_has_speech_plan(control_payload):
        raise ValueError("V62 control payload unexpectedly contains speech plan")
    if not _payload_has_speech_plan(treatment_payload):
        raise ValueError("V62 treatment payload is missing speech plan")
    if json.loads(control_payload) == json.loads(treatment_payload):
        raise ValueError("V62 treatment payload is identical to control")

    return {
        "runtime_speech_plan": deepcopy(plan),
        C0: {
            "logic": control_logic,
            "payload": control_payload,
            "payload_plan_present": False,
        },
        T1: {
            "logic": treatment_logic,
            "payload": treatment_payload,
            "payload_plan_present": True,
        },
    }


def _capture_case(bot, case, production_path):
    with tempfile.TemporaryDirectory(prefix=f"uruha_v62_{case['id']}_") as temporary:
        temporary_path = Path(temporary).resolve()
        if temporary_path == Path(production_path).resolve():
            raise ValueError("V62 temporary database equals production database")
        with redirect_stdout(io.StringIO()):
            bot.reset_session(db_path=str(temporary_path))
            v61._seed_memory_fixture(bot.memory, case["memory_fixture"])
            bot.psyche.mood = case["psyche_fixture"]["mood"]
            bot.psyche.trust = case["psyche_fixture"]["trust"]
            event = bot.ingest_event(case["user_input"])
            tick = bot.cognitive_tick(event)

        memory_data = deepcopy(event["memory_data"])
        retrieved_ids = v61._retrieved_fixture_ids(
            memory_data,
            case["memory_fixture"],
        )
        expected_ids = [item["id"] for item in case["memory_fixture"]]
        if set(retrieved_ids) != set(expected_ids):
            raise ValueError(
                f"V62 fixture retrieval incomplete for {case['id']}: "
                f"{retrieved_ids} != {expected_ids}"
            )

        base_logic = deepcopy(tick["logic"])
        psyche_state = deepcopy(bot.psyche.get_state())
        payloads = build_condition_payloads(
            bot.right_brain,
            base_logic,
            case["user_input"],
            memory_data,
            psyche_state,
            case["maximum_reply_chars"],
        )
        shared_plan_sha256 = _canonical_sha256(
            {
                "user_input": case["user_input"],
                "memory_data": memory_data,
                "psyche_state": psyche_state,
                "route_info": tick["route_info"],
                "base_logic": base_logic,
                "runtime_speech_plan": payloads["runtime_speech_plan"],
            }
        )
        conditions = {}
        for condition in CONDITIONS:
            conditions[condition] = {
                "logic": payloads[condition]["logic"],
                "payload": payloads[condition]["payload"],
                "payload_sha256": hashlib.sha256(
                    payloads[condition]["payload"].encode("utf-8")
                ).hexdigest(),
                "payload_plan_present": payloads[condition][
                    "payload_plan_present"
                ],
            }
        return {
            "case_id": case["id"],
            "scenario_family": case["scenario_family"],
            "user_input": case["user_input"],
            "temporary_database": True,
            "production_database_opened": False,
            "retrieved_fixture_ids": retrieved_ids,
            "expected_fixture_ids": expected_ids,
            "memory_data": memory_data,
            "psyche_state": psyche_state,
            "route_info": deepcopy(tick["route_info"]),
            "base_logic": base_logic,
            "runtime_speech_plan": payloads["runtime_speech_plan"],
            "shared_plan_sha256": shared_plan_sha256,
            "conditions": conditions,
        }


def _run_condition(bot, prereg, case, capture, condition, model, call_fn):
    frozen = capture["conditions"][condition]
    messages = [
        {
            "role": "system",
            "content": v61.brain_module.RIGHT_BRAIN_MODEL_SYSTEM_PROMPT,
        },
        {"role": "user", "content": frozen["payload"]},
    ]
    body = v61._chat_body(model, messages, prereg["generation"])
    called = call_fn(body)
    response = called["response"]
    reply = str((response.get("message") or {}).get("content") or "").strip()
    score = v61._score_reply(
        bot,
        case,
        deepcopy(frozen["logic"]),
        reply,
    )
    return {
        "case_id": case["id"],
        "scenario_family": case["scenario_family"],
        "condition": condition,
        "shared_plan_sha256": capture["shared_plan_sha256"],
        "payload_sha256": frozen["payload_sha256"],
        "payload_plan_present": frozen["payload_plan_present"],
        "transport_attempts": called["transport_attempts"],
        "transport_error": called["transport_error"],
        "generation_metrics": v61._response_metrics(
            response,
            called["wall_seconds"],
        ),
        "peak_ollama_rss_bytes": v61._peak_ollama_rss_bytes(),
        "raw_reply": reply,
        "raw_score": score,
    }


def main(call_fn=v61._call_ollama_once):
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit(f"refusing to overwrite formal V62 result: {args.output}")
    if v61._git("branch", "--show-current") != "main":
        raise SystemExit("formal V62 run requires merged main")
    if not v61._tracked_tree_clean() or v61._git("status", "--porcelain"):
        raise SystemExit("formal V62 run requires a clean worktree")

    prereg = _load(PREREG_PATH)
    closure = _load(CLOSURE_PATH)
    lock = _load(LOCK_PATH)
    _verify_lock(lock)
    if not closure["authorizations"]["harness_implementation"]:
        raise SystemExit("V62 construction closure did not authorize harness")
    if not lock["formal_run"]["candidate_inference_authorized"]:
        raise SystemExit("V62 harness lock did not authorize inference")
    preflight = _run_preflight(lock)
    if not preflight["passed"]:
        raise SystemExit("V62 frozen preflight failed")
    if v61._ollama_version() != lock["environment"]["ollama_version"]:
        raise SystemExit("V62 Ollama version drift")

    model = _model_snapshot(prereg)
    dataset = _load(DATASET_PATH)
    cases = dataset["cases"]
    if len(cases) != prereg["fresh_dataset"]["case_count"]:
        raise SystemExit("V62 case count drift")

    started_at = datetime.now(TZ).isoformat(timespec="seconds")
    with v61._isolated_brain(prereg) as (bot, leftbrain_calls, isolation):
        captures = [
            _capture_case(
                bot,
                case,
                isolation["production_database_path"],
            )
            for case in cases
        ]
        if len(leftbrain_calls) != 14:
            raise SystemExit(
                f"V62 expected 14 LeftBrain calls, observed {len(leftbrain_calls)}"
            )
        if any(
            capture["conditions"][C0]["payload_plan_present"]
            or not capture["conditions"][T1]["payload_plan_present"]
            for capture in captures
        ):
            raise SystemExit("V62 speech-plan intervention shape mismatch")

        capture_by_id = {row["case_id"]: row for row in captures}
        rows = []
        calls = []
        for condition in CONDITIONS:
            for case in cases:
                row = _run_condition(
                    bot,
                    prereg,
                    case,
                    capture_by_id[case["id"]],
                    condition,
                    model,
                    call_fn,
                )
                rows.append(row)
                calls.append(
                    {
                        "case_id": case["id"],
                        "condition": condition,
                        "model": model["ollama_tag"],
                        "digest": model["digest"],
                        "shared_plan_sha256": row["shared_plan_sha256"],
                        "payload_sha256": row["payload_sha256"],
                        "transport_attempts": row["transport_attempts"],
                        "transport_error": row["transport_error"],
                        "wall_seconds": row["generation_metrics"]["wall_seconds"],
                    }
                )

    expected_pairs = {
        (case["id"], condition)
        for case in cases
        for condition in CONDITIONS
    }
    observed_pairs = {(row["case_id"], row["condition"]) for row in rows}
    if observed_pairs != expected_pairs or len(calls) != 28:
        raise SystemExit("V62 model-call accounting mismatch")

    raw = {
        "schema": "uruha_rightbrain_speech_plan_payload_raw_v62",
        "experiment_id": prereg["experiment_id"],
        "started_at": started_at,
        "completed_at": datetime.now(TZ).isoformat(timespec="seconds"),
        "runner_branch": v61._git("branch", "--show-current"),
        "runner_commit": v61._git("rev-parse", "HEAD"),
        "frozen_artifact_hashes": {
            name: artifact["sha256"]
            for name, artifact in lock["frozen_artifacts"].items()
        },
        "harness_lock_sha256": _sha256(LOCK_PATH),
        "ollama_version": v61._ollama_version(),
        "model_snapshot": model,
        "preflight": preflight,
        "gold_or_expected_outcome_passed_to_model": False,
        "database_isolation": isolation,
        "conditions": list(CONDITIONS),
        "plan_capture_count": len(captures),
        "leftbrain_call_count": len(leftbrain_calls),
        "leftbrain_calls": leftbrain_calls,
        "logical_model_call_count": len(calls),
        "logical_model_calls": calls,
        "transport_attempt_count": sum(
            call["transport_attempts"] for call in calls
        ),
        "transport_error_count": sum(
            bool(call["transport_error"]) for call in calls
        ),
        "production_memory_write_count": 0,
        "physical_vrm_action_count": 0,
        "captures": captures,
        "model_rows": rows,
    }
    v61._atomic_write(args.output, raw)
    print(
        json.dumps(
            {
                "experiment_id": raw["experiment_id"],
                "runner_commit": raw["runner_commit"],
                "plan_captures": raw["plan_capture_count"],
                "leftbrain_calls": raw["leftbrain_call_count"],
                "model_calls": raw["logical_model_call_count"],
                "transport_errors": raw["transport_error_count"],
                "output": str(args.output),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
