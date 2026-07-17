#!/usr/bin/env python3
"""Run the frozen V61 matched RightBrain pipeline shadow."""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import uruha_brain_mac as brain_module
from rightbrain_semantic_verifier_v32 import match_group


ROOT = Path(__file__).resolve().parent
PREREG_PATH = (
    ROOT / "configs" / "rightbrain_pipeline_shadow_v61_preregistration.json"
)
DATASET_CLOSURE_PATH = (
    ROOT / "configs" / "rightbrain_pipeline_shadow_v61_dataset_closure.json"
)
LOCK_PATH = (
    ROOT / "configs" / "rightbrain_pipeline_shadow_v61_harness_lock.json"
)
DEFAULT_OUTPUT = (
    ROOT / "reports" / "rightbrain_pipeline_shadow_v61_raw.json"
)
OLLAMA_CHAT_URL = "http://127.0.0.1:11434/api/chat"
OLLAMA_TAGS_URL = "http://127.0.0.1:11434/api/tags"
TZ = ZoneInfo("Asia/Tokyo")

C0 = "c0_current_deterministic_runtime"
C1 = "c1_qwen2_5_7b_one_pass"
T1 = "t1_qwen3_5_9b_one_pass"
CONDITIONS = (C0, C1, T1)
MODEL_CONDITIONS = (C1, T1)


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


def _git(*args):
    return subprocess.check_output(
        ["git", *args],
        cwd=ROOT,
        text=True,
    ).strip()


def _tracked_tree_clean():
    unstaged = subprocess.run(
        ["git", "diff", "--quiet"],
        cwd=ROOT,
        check=False,
    )
    staged = subprocess.run(
        ["git", "diff", "--cached", "--quiet"],
        cwd=ROOT,
        check=False,
    )
    return unstaged.returncode == 0 and staged.returncode == 0


def _atomic_write(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def _post_json(url, body, timeout=240):
    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.load(response)


def _get_json(url, timeout=30):
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return json.load(response)


def _ollama_version():
    output = subprocess.check_output(
        ["ollama", "--version"],
        text=True,
        stderr=subprocess.STDOUT,
    ).strip()
    prefix = "ollama version is "
    if not output.startswith(prefix):
        raise ValueError(f"unexpected Ollama version: {output}")
    return output.removeprefix(prefix)


def _model_inventory(prereg):
    inventory = {
        row["name"]: row
        for row in (_get_json(OLLAMA_TAGS_URL).get("models") or [])
    }
    snapshots = {}
    for condition in MODEL_CONDITIONS:
        frozen = prereg["conditions"][condition]
        row = inventory.get(frozen["ollama_tag"])
        if not row or row.get("digest") != frozen["digest"]:
            raise ValueError(f"missing or drifted model for {condition}")
        snapshots[condition] = {
            "ollama_tag": frozen["ollama_tag"],
            "digest": row["digest"],
            "size_bytes": row.get("size"),
            "details": row.get("details") or {},
            "thinking": frozen.get("thinking"),
        }
    return snapshots


def _peak_ollama_rss_bytes():
    try:
        output = subprocess.check_output(
            ["ps", "-axo", "rss=,command="],
            text=True,
        )
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


def _call_ollama_once(body):
    started = time.perf_counter()
    try:
        response = _post_json(OLLAMA_CHAT_URL, body)
        return {
            "response": response,
            "wall_seconds": round(time.perf_counter() - started, 6),
            "transport_attempts": 1,
            "transport_error": None,
        }
    except (
        OSError,
        TimeoutError,
        urllib.error.URLError,
        json.JSONDecodeError,
    ) as exc:
        return {
            "response": {},
            "wall_seconds": round(time.perf_counter() - started, 6),
            "transport_attempts": 1,
            "transport_error": f"{type(exc).__name__}: {exc}",
        }


def _chat_body(model, messages, generation):
    body = {
        "model": model["ollama_tag"],
        "messages": messages,
        "stream": False,
        "keep_alive": "20m",
        "options": {
            "temperature": generation["temperature"],
            "top_p": generation["top_p"],
            "top_k": generation["top_k"],
            "repeat_penalty": generation["repeat_penalty"],
            "seed": generation["seed"],
            "num_ctx": generation["context_tokens"],
            "num_predict": generation["maximum_output_tokens"],
        },
    }
    if model.get("thinking") is not None:
        body["think"] = bool(model["thinking"])
    return body


def _response_metrics(response, elapsed_seconds):
    return {
        "wall_seconds": elapsed_seconds,
        "total_duration_ns": response.get("total_duration"),
        "load_duration_ns": response.get("load_duration"),
        "prompt_eval_count": response.get("prompt_eval_count"),
        "prompt_eval_duration_ns": response.get("prompt_eval_duration"),
        "eval_count": response.get("eval_count"),
        "eval_duration_ns": response.get("eval_duration"),
    }


class _CompletionProxy:
    def __init__(self, target, seed, call_log):
        self._target = target
        self._seed = seed
        self._call_log = call_log

    def create(self, *args, **kwargs):
        kwargs["temperature"] = 0.0
        kwargs["seed"] = self._seed
        self._call_log.append(
            {
                "model": kwargs.get("model"),
                "seed": self._seed,
                "temperature": 0.0,
            }
        )
        return self._target.create(*args, **kwargs)


class _ChatProxy:
    def __init__(self, target, seed, call_log):
        self.completions = _CompletionProxy(
            target.completions,
            seed,
            call_log,
        )


class DeterministicClient:
    def __init__(self, target, seed, call_log):
        self.chat = _ChatProxy(target.chat, seed, call_log)


def _verify_lock(lock):
    failed = []
    for artifact in lock["frozen_artifacts"].values():
        path = ROOT / artifact["path"]
        if not path.exists() or _sha256(path) != artifact["sha256"]:
            failed.append(artifact["path"])
    if failed:
        raise ValueError(
            "V61 frozen artifact drift: " + ", ".join(failed)
        )
    if tuple(lock["conditions"]) != CONDITIONS:
        raise ValueError("V61 condition order drift")
    if lock["formal_run"]["logical_model_call_count_exact"] != 60:
        raise ValueError("V61 model-call budget drift")


def _run_preflight(lock):
    command = [
        sys.executable,
        *lock["preflight"]["arguments"],
    ]
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
    combined_output = f"{completed.stdout}\n{completed.stderr}"
    match = re.search(r"Ran\s+(\d+)\s+tests?", combined_output)
    observed_test_count = int(match.group(1)) if match else None
    expected_test_count = lock["preflight"]["expected_test_count"]
    return {
        "command": command,
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "observed_test_count": observed_test_count,
        "expected_test_count": expected_test_count,
        "passed": (
            completed.returncode == 0
            and observed_test_count == expected_test_count
        ),
    }


def _fixture_metadata(item):
    return {
        "source": "rightbrain_pipeline_shadow_v61_fixture",
        "fixture_id": item["id"],
        "original_layer": item["layer"],
        "status": item["status"],
        "speakability": item["speakability"],
        "last_accessed_at": "2026-07-18 00:00:00",
        "decay_flag": False,
        "decay_multiplier": 1.0,
        "self_relevance": True,
    }


def _seed_memory_fixture(memory, fixture):
    for item in fixture:
        metadata = _fixture_metadata(item)
        if item["layer"] == "profile":
            memory.session_profile["likes"].append(item["text"])
            memory.profile_col.add(
                ids=[item["id"]],
                documents=[item["text"]],
                metadatas=[metadata],
            )
            continue
        if item["layer"] != "episodic":
            raise ValueError(
                f"unsupported V61 fixture layer: {item['layer']}"
            )
        memory.episode_col.add(
            ids=[item["id"]],
            documents=[item["text"]],
            metadatas=[metadata],
        )


def _retrieved_fixture_ids(memory_data, fixture):
    working_texts = [
        str(row.get("text") or "")
        for row in memory_data.get("working_memory_items") or []
    ]
    return [
        item["id"]
        for item in fixture
        if any(item["text"] in text for text in working_texts)
    ]


def _proposition_rows(right_brain, reply, propositions):
    rows = []
    for proposition in propositions:
        hit, traces = match_group(
            reply,
            proposition["accepted_surfaces"],
            "lemma_polarity",
            right_brain._semantic_marker_hit,
        )
        rows.append(
            {
                "id": proposition["id"],
                "description": proposition["description"],
                "accepted_surfaces": proposition["accepted_surfaces"],
                "hit": bool(hit),
                "traces": [trace.to_dict() for trace in traces],
            }
        )
    return rows


def _score_reply(brain, case, logic, reply):
    reply = str(reply or "").strip()
    max_chars = int(case["maximum_reply_chars"])
    semantic_groups = [
        list(group)
        for group in brain.right_brain._model_required_semantic_groups(
            logic
        )
    ]
    semantic_rows = []
    for group in semantic_groups:
        hit, traces = match_group(
            reply,
            group,
            "lemma_polarity",
            brain.right_brain._semantic_marker_hit,
        )
        semantic_rows.append(
            {
                "markers": group,
                "hit": bool(hit),
                "traces": [trace.to_dict() for trace in traces],
            }
        )
    required_rows = _proposition_rows(
        brain.right_brain,
        reply,
        case["required_meaning_propositions"],
    )
    forbidden_rows = _proposition_rows(
        brain.right_brain,
        reply,
        case["forbidden_meaning_propositions"],
    )
    private_hits = sorted(
        term
        for term in case["private_memory_terms"]
        if brain.right_brain._semantic_marker_hit(reply, term)
    )
    reasons = brain.right_brain._model_candidate_rejection_reasons(
        reply,
        logic,
        max_chars,
        user_input=case["user_input"],
    )
    return {
        "reply": reply,
        "character_count": len(reply),
        "semantic_groups": semantic_rows,
        "semantic_group_hit_count": sum(
            row["hit"] for row in semantic_rows
        ),
        "semantic_group_count": len(semantic_rows),
        "semantic_contract_pass": bool(semantic_rows)
        and all(row["hit"] for row in semantic_rows),
        "required_meaning_propositions": required_rows,
        "required_meaning_hit_count": sum(
            row["hit"] for row in required_rows
        ),
        "required_meaning_count": len(required_rows),
        "required_meaning_pass": all(
            row["hit"] for row in required_rows
        ),
        "forbidden_meaning_propositions": forbidden_rows,
        "forbidden_meaning_hit_count": sum(
            row["hit"] for row in forbidden_rows
        ),
        "private_memory_hits": private_hits,
        "private_memory_intrusion": bool(private_hits),
        "current_gate_rejection_reasons": reasons,
        "current_gate_pass": not reasons,
        "normalized_reply": re.sub(
            r"[\s\u3000。．，,、！？?!…~～ー\-_/'\"`]+",
            "",
            reply.lower(),
        ),
    }


def _finalize_with_runtime(
    brain,
    case,
    logic,
    memory_data,
    psyche_state,
    initial_reply,
):
    before = str(initial_reply or "").strip()
    monitor_before = brain._self_monitor_reply(
        case["user_input"],
        before,
        logic,
        memory_data,
    )
    after = brain._repair_reply_from_self_monitor(
        before,
        logic,
        monitor_before,
        case["user_input"],
        memory_data,
        psyche_state,
    )
    monitor_after = brain._self_monitor_reply(
        case["user_input"],
        after,
        logic,
        memory_data,
    )
    post_check = brain._attach_reply_post_check(
        logic,
        case["user_input"],
        after,
        memory_data,
    )
    return {
        "initial_reply": before,
        "final_reply": after,
        "self_monitor_before": monitor_before,
        "self_monitor_after": monitor_after,
        "post_check": post_check,
        "repair_changed_reply": before != after,
    }


@contextlib.contextmanager
def _isolated_brain(prereg):
    production_path = Path(brain_module.DB_PATH).resolve()
    original_db_path = brain_module.DB_PATH
    with tempfile.TemporaryDirectory(
        prefix="uruha_v61_startup_"
    ) as startup_directory:
        startup_path = Path(startup_directory).resolve()
        if startup_path == production_path:
            raise ValueError("V61 temporary database equals production path")
        brain_module.DB_PATH = str(startup_path)
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                bot = brain_module.UruhaBrainV4_Mac(
                    load_right_brain_model=False
                )
            leftbrain_calls = []
            deterministic = DeterministicClient(
                bot.client_logic,
                prereg["generation"]["seed"],
                leftbrain_calls,
            )
            bot.client_logic = deterministic
            bot.left_brain.client_logic = deterministic
            yield bot, leftbrain_calls, {
                "production_database_path": str(production_path),
                "startup_temporary_database_path": str(startup_path),
                "production_database_opened": False,
                "production_database_writes": 0,
            }
        finally:
            brain_module.DB_PATH = original_db_path


def _capture_case(bot, case, production_path):
    with tempfile.TemporaryDirectory(
        prefix=f"uruha_v61_{case['id']}_"
    ) as temporary:
        temporary_path = Path(temporary).resolve()
        if temporary_path == Path(production_path).resolve():
            raise ValueError("V61 case database equals production path")
        with contextlib.redirect_stdout(io.StringIO()):
            bot.reset_session(db_path=str(temporary_path))
            _seed_memory_fixture(bot.memory, case["memory_fixture"])
            bot.psyche.mood = case["psyche_fixture"]["mood"]
            bot.psyche.trust = case["psyche_fixture"]["trust"]
            event = bot.ingest_event(case["user_input"])
            tick = bot.cognitive_tick(event)

        memory_data = deepcopy(event["memory_data"])
        retrieved_ids = _retrieved_fixture_ids(
            memory_data,
            case["memory_fixture"],
        )
        expected_ids = [item["id"] for item in case["memory_fixture"]]
        if set(retrieved_ids) != set(expected_ids):
            raise ValueError(
                f"V61 fixture retrieval incomplete for {case['id']}: "
                f"{retrieved_ids} != {expected_ids}"
            )

        logic = deepcopy(tick["logic"])
        logic.setdefault("constraints", {})
        logic["constraints"]["max_chars"] = case["maximum_reply_chars"]
        psyche_state = deepcopy(bot.psyche.get_state())
        route_info = deepcopy(tick["route_info"])
        captured_plan_sha256 = _canonical_sha256(
            {
                "user_input": case["user_input"],
                "memory_data": memory_data,
                "psyche_state": psyche_state,
                "route_info": route_info,
                "logic": logic,
            }
        )

        control_logic = deepcopy(logic)
        bot.right_brain.reset_session_state()
        with contextlib.redirect_stdout(io.StringIO()):
            deterministic_reply = bot.right_brain.speak(
                case["user_input"],
                control_logic,
                memory_data,
                psyche_state,
            )
            control_runtime = _finalize_with_runtime(
                bot,
                case,
                control_logic,
                memory_data,
                psyche_state,
                deterministic_reply,
            )
        control_score = _score_reply(
            bot,
            case,
            control_logic,
            control_runtime["final_reply"],
        )

        payload_logic = deepcopy(logic)
        payload = bot.right_brain._build_model_surface_payload(
            payload_logic,
            psyche_state,
            case["maximum_reply_chars"],
            memory_data=memory_data,
        )
        payload_json = json.loads(payload)
        forbidden_payload_keys = {
            "required_meaning_propositions",
            "forbidden_meaning_propositions",
            "expected_obligation",
            "private_memory_terms",
            "case_id",
        }
        if forbidden_payload_keys.intersection(payload_json):
            raise ValueError(
                f"V61 gold field leaked into model payload: {case['id']}"
            )
        bot.right_brain.reset_session_state()

        return {
            "case_id": case["id"],
            "scenario_family": case["scenario_family"],
            "user_input": case["user_input"],
            "shared_plan_sha256": captured_plan_sha256,
            "temporary_database": True,
            "production_database_opened": False,
            "temporary_database_path": str(temporary_path),
            "retrieved_fixture_ids": retrieved_ids,
            "expected_fixture_ids": expected_ids,
            "working_memory_items": memory_data.get(
                "working_memory_items"
            )
            or [],
            "memory_data": memory_data,
            "psyche_state": psyche_state,
            "route_info": route_info,
            "logic": logic,
            "model_payload": payload,
            "model_payload_sha256": hashlib.sha256(
                payload.encode("utf-8")
            ).hexdigest(),
            "deterministic_control": {
                "condition": C0,
                "runtime": control_runtime,
                "score": control_score,
            },
        }


def _run_model_condition(
    bot,
    prereg,
    case,
    captured,
    condition,
    model,
    call_fn=_call_ollama_once,
):
    logic = deepcopy(captured["logic"])
    memory_data = deepcopy(captured["memory_data"])
    payload = captured["model_payload"]
    messages = [
        {
            "role": "system",
            "content": brain_module.RIGHT_BRAIN_MODEL_SYSTEM_PROMPT,
        },
        {"role": "user", "content": payload},
    ]
    body = _chat_body(
        model,
        messages,
        prereg["generation"],
    )
    called = call_fn(body)
    response = called["response"]
    raw_reply = str(
        (response.get("message") or {}).get("content") or ""
    ).strip()
    raw_score = _score_reply(
        bot,
        case,
        logic,
        raw_reply,
    )

    prepared_reply = ""
    prepared_reasons = list(
        raw_score["current_gate_rejection_reasons"]
    )
    if not prepared_reasons:
        prepared_reply, prepared_reasons = (
            bot.right_brain._prepare_model_surface_candidate(
                raw_reply,
                logic,
                case["user_input"],
                memory_data,
                case["maximum_reply_chars"],
            )
        )
    strict_takeover = bool(
        raw_score["current_gate_pass"]
        and prepared_reply
        and not prepared_reasons
    )
    fallback_reply = captured["deterministic_control"]["runtime"][
        "final_reply"
    ]
    selected_reply = prepared_reply if strict_takeover else fallback_reply
    bot.right_brain.reset_session_state()
    with contextlib.redirect_stdout(io.StringIO()):
        runtime = _finalize_with_runtime(
            bot,
            case,
            logic,
            memory_data,
            captured["psyche_state"],
            selected_reply,
        )
    final_score = _score_reply(
        bot,
        case,
        logic,
        runtime["final_reply"],
    )
    final_model_takeover = bool(
        strict_takeover
        and runtime["final_reply"] != fallback_reply
    )
    return {
        "case_id": case["id"],
        "scenario_family": case["scenario_family"],
        "condition": condition,
        "shared_plan_sha256": captured["shared_plan_sha256"],
        "model_payload_sha256": captured["model_payload_sha256"],
        "transport_attempts": called["transport_attempts"],
        "transport_error": called["transport_error"],
        "generation_metrics": _response_metrics(
            response,
            called["wall_seconds"],
        ),
        "peak_ollama_rss_bytes": _peak_ollama_rss_bytes(),
        "raw_reply": raw_reply,
        "raw_score": raw_score,
        "prepared_reply": prepared_reply,
        "prepared_rejection_reasons": prepared_reasons,
        "strict_takeover_before_self_monitor": strict_takeover,
        "model_takeover": final_model_takeover,
        "fallback_reply": fallback_reply,
        "runtime": runtime,
        "final_score": final_score,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
    )
    args = parser.parse_args()

    if args.output.exists():
        raise SystemExit(
            f"refusing to overwrite formal V61 result: {args.output}"
        )
    if _git("branch", "--show-current") != "main":
        raise SystemExit("formal V61 run requires merged main")
    if not _tracked_tree_clean() or _git("status", "--porcelain"):
        raise SystemExit("formal V61 run requires a clean worktree")

    prereg = _load(PREREG_PATH)
    closure = _load(DATASET_CLOSURE_PATH)
    lock = _load(LOCK_PATH)
    _verify_lock(lock)
    if not closure["authorizations"]["harness_implementation"]:
        raise SystemExit("V61 dataset closure did not authorize harness")
    if not lock["formal_run"]["candidate_inference_authorized"]:
        raise SystemExit("V61 harness lock did not authorize inference")

    preflight = _run_preflight(lock)
    if not preflight["passed"]:
        raise SystemExit("V61 frozen preflight failed before plan capture")
    if _ollama_version() != lock["environment"]["ollama_version"]:
        raise SystemExit("V61 Ollama version drift")
    models = _model_inventory(prereg)
    dataset = _load(ROOT / prereg["fresh_dataset"]["path"])
    cases = dataset["cases"]
    if len(cases) != prereg["fresh_dataset"]["case_count"]:
        raise SystemExit("V61 case count drift")

    started_at = datetime.now(TZ).isoformat(timespec="seconds")
    with _isolated_brain(prereg) as (
        bot,
        leftbrain_calls,
        isolation,
    ):
        captures = []
        for case in cases:
            captures.append(
                _capture_case(
                    bot,
                    case,
                    isolation["production_database_path"],
                )
            )
        if len(captures) != len(cases):
            raise SystemExit(
                "V61 shared plan capture incomplete before inference"
            )
        if any(
            set(row["retrieved_fixture_ids"])
            != set(row["expected_fixture_ids"])
            for row in captures
        ):
            raise SystemExit(
                "V61 memory fixture retrieval incomplete before inference"
            )

        rows = []
        calls = []
        capture_by_id = {
            row["case_id"]: row for row in captures
        }
        for condition in MODEL_CONDITIONS:
            model = models[condition]
            for case in cases:
                row = _run_model_condition(
                    bot,
                    prereg,
                    case,
                    capture_by_id[case["id"]],
                    condition,
                    model,
                )
                rows.append(row)
                calls.append(
                    {
                        "case_id": case["id"],
                        "condition": condition,
                        "model": model["ollama_tag"],
                        "digest": model["digest"],
                        "shared_plan_sha256": row[
                            "shared_plan_sha256"
                        ],
                        "model_payload_sha256": row[
                            "model_payload_sha256"
                        ],
                        "transport_attempts": row[
                            "transport_attempts"
                        ],
                        "transport_error": row[
                            "transport_error"
                        ],
                        "wall_seconds": row[
                            "generation_metrics"
                        ]["wall_seconds"],
                    }
                )

    expected_pairs = {
        (case["id"], condition)
        for case in cases
        for condition in MODEL_CONDITIONS
    }
    observed_pairs = {
        (row["case_id"], row["condition"])
        for row in rows
    }
    if observed_pairs != expected_pairs or len(calls) != 60:
        raise SystemExit("V61 logical model-call accounting mismatch")

    completed_at = datetime.now(TZ).isoformat(timespec="seconds")
    raw = {
        "schema": "uruha_rightbrain_pipeline_shadow_raw_v61",
        "experiment_id": prereg["experiment_id"],
        "runner_commit": _git("rev-parse", "HEAD"),
        "runner_branch": _git("branch", "--show-current"),
        "started_at": started_at,
        "completed_at": completed_at,
        "conditions": list(CONDITIONS),
        "ollama_version": _ollama_version(),
        "model_snapshots": models,
        "harness_lock_sha256": _sha256(LOCK_PATH),
        "frozen_artifact_hashes": {
            name: _sha256(ROOT / artifact["path"])
            for name, artifact in lock["frozen_artifacts"].items()
        },
        "system_prompt_sha256": hashlib.sha256(
            brain_module.RIGHT_BRAIN_MODEL_SYSTEM_PROMPT.encode(
                "utf-8"
            )
        ).hexdigest(),
        "preflight": preflight,
        "database_isolation": isolation,
        "production_memory_write_count": 0,
        "physical_vrm_action_count": 0,
        "gold_or_expected_outcome_passed_to_model": False,
        "leftbrain_call_count": len(leftbrain_calls),
        "leftbrain_calls": leftbrain_calls,
        "plan_capture_count": len(captures),
        "captures": captures,
        "model_rows": rows,
        "logical_model_calls": calls,
        "logical_model_call_count": len(calls),
        "transport_attempt_count": sum(
            call["transport_attempts"] for call in calls
        ),
        "transport_error_count": sum(
            bool(call["transport_error"]) for call in calls
        ),
        "inflight_request_at_completion": None,
    }
    _atomic_write(args.output, raw)
    print(
        json.dumps(
            {
                "experiment_id": raw["experiment_id"],
                "runner_commit": raw["runner_commit"],
                "plan_captures": raw["plan_capture_count"],
                "model_calls": raw["logical_model_call_count"],
                "transport_attempts": raw[
                    "transport_attempt_count"
                ],
                "transport_errors": raw[
                    "transport_error_count"
                ],
                "output": str(args.output),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
