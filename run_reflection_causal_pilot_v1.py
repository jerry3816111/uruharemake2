#!/usr/bin/env python3
"""Run the frozen matched reflection-on/off pilot against the local system."""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import io
import json
import os
import shutil
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "reflection_causal_pilot_v1_preregistration.json"
LOCK_PATH = ROOT / "configs" / "reflection_causal_pilot_v1_harness_lock.json"
DATASET_PATH = ROOT / "datasets" / "reflection_causal_pilot_v1.json"
DEFAULT_OUTPUT = ROOT / "reports" / "reflection_causal_pilot_v1_raw.json"
CONTROL = "episodic_memory_only_control"
TREATMENT = "same_episodic_memory_plus_current_reflection_treatment"
CONDITIONS = (CONTROL, TREATMENT)
TZ = ZoneInfo("Asia/Tokyo")


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def now():
    return datetime.now(TZ).isoformat(timespec="seconds")


def git_value(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def tracked_tree_clean():
    return all(
        subprocess.run(command, cwd=ROOT, check=False).returncode == 0
        for command in (["git", "diff", "--quiet"], ["git", "diff", "--cached", "--quiet"])
    )


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def atomic_write(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    os.replace(temporary, path)


def verify_frozen_inputs(config, lock, dataset):
    if tuple(config["conditions"]) != CONDITIONS:
        raise ValueError("reflection pilot condition order drift")
    if tuple(lock["conditions"]) != CONDITIONS:
        raise ValueError("reflection pilot harness condition order drift")
    if dataset["case_count"] != config["case_count"] or len(dataset["cases"]) != config["case_count"]:
        raise ValueError("reflection pilot case count drift")
    for relative, expected in lock["frozen_artifacts"].items():
        path = ROOT / relative
        if sha256(path) != expected:
            raise ValueError(f"reflection pilot hash mismatch: {relative}")
    if git_value("branch", "--show-current") != lock["required_run_branch"]:
        raise ValueError("reflection pilot can run only from merged main")
    if not tracked_tree_clean():
        raise ValueError("reflection pilot requires a clean tracked worktree and index")
    committed = subprocess.run(
        ["git", "cat-file", "-e", f"HEAD:{LOCK_PATH.relative_to(ROOT)}"],
        cwd=ROOT,
        check=False,
        capture_output=True,
    )
    if committed.returncode != 0:
        raise ValueError("reflection pilot harness lock is not committed")
    forbidden = (
        "post_run_case_editing_authorized",
        "post_run_threshold_change_authorized",
        "runtime_reflection_change_authorized_before_result",
        "human_rating_required",
        "paid_api_authorized",
        "broad_human_likeness_claim_authorized",
    )
    if any(config[key] for key in forbidden):
        raise ValueError("reflection pilot preregistration authorizes forbidden drift")


class _CompletionProxy:
    def __init__(self, target, seed, call_log):
        self._target = target
        self._seed = seed
        self._call_log = call_log

    def create(self, *args, **kwargs):
        messages = kwargs.get("messages") or []
        system_text = "\n".join(
            str(message.get("content") or "")
            for message in messages
            if message.get("role") == "system"
        )
        if "Extract at most ONE stable user profile rule" in system_text:
            call_kind = "reflection_extraction"
        elif "Left Brain Planner" in system_text:
            call_kind = "left_brain_planning"
        else:
            call_kind = "other"
        kwargs["temperature"] = 0.0
        kwargs["seed"] = self._seed
        self._call_log.append(
            {"kind": call_kind, "model": kwargs.get("model"), "seed": self._seed}
        )
        return self._target.create(*args, **kwargs)


class _ChatProxy:
    def __init__(self, target, seed, call_log):
        self.completions = _CompletionProxy(target.completions, seed, call_log)


class DeterministicClient:
    def __init__(self, target, seed, call_log):
        self.chat = _ChatProxy(target.chat, seed, call_log)


def reflection_documents(memory):
    payload = memory.wisdom_col.get(
        where={"source": "reflection_rule"}, include=["documents", "metadatas"]
    )
    return [str(item) for item in payload.get("documents") or [] if str(item).strip()]


def compact_logic(logic):
    keys = (
        "intent",
        "scene",
        "reply_goal",
        "core_message_jp",
        "surface_act",
        "response_mode",
        "user_belief",
        "my_hidden_knowledge",
        "user_expectation",
        "internal_monologue",
    )
    return {key: logic.get(key) for key in keys if logic.get(key) is not None}


def compact_working_memory(memory_data):
    rows = []
    for item in memory_data.get("working_memory_items") or []:
        rows.append(
            {
                "source": item.get("source"),
                "text": item.get("text"),
                "score": item.get("score"),
                "metadata": item.get("metadata") or {},
            }
        )
    return rows


def run_condition(brain, client, case, condition, case_index):
    tempdir = tempfile.mkdtemp(prefix=f"uruha_reflection_{case['id']}_{condition}_")
    start_call = len(client["log"])
    try:
        brain.reset_session(db_path=tempdir)
        brain.client_logic = client["proxy"]
        brain.left_brain.client_logic = client["proxy"]
        logic_seed = {
            "intent": "memory_seed",
            "scene": "memory",
            "jp_summary": case["seed_user"],
            "cognitive_mode": "direct",
            "premise_check": "accept",
            "routing_path": "high_road",
        }
        with contextlib.redirect_stdout(io.StringIO()):
            brain.memory.save_episode(
                case["seed_user"],
                case["seed_assistant"],
                {"mood": 0, "trust": 50},
                logic_seed,
            )
            reflection_return = None
            if condition == TREATMENT:
                reflection_return = brain.memory.reflect_experience(
                    case["seed_user"],
                    case["seed_assistant"],
                    logic_seed,
                    client["proxy"],
                )
            documents = reflection_documents(brain.memory)
            brain.memory.clear_session_state()
            brain.memory.reflect_experience = lambda *_args, **_kwargs: None
            result = brain.run_turn_debug(case["future_prompt"])
        logic = compact_logic(result.get("logic") or {})
        memory_data = result.get("memory_data") or {}
        working_memory = compact_working_memory(memory_data)
        retrieved = any(
            item.get("source") == "wisdom"
            and (item.get("metadata") or {}).get("source") == "reflection_rule"
            for item in working_memory
        )
        return {
            "condition": condition,
            "condition_order_index": case_index,
            "reflection_return": reflection_return,
            "reflection_documents": documents,
            "retrieved_reflection": retrieved,
            "future_reply": result.get("reply") or "",
            "future_logic": logic,
            "future_logic_text": json.dumps(logic, ensure_ascii=False, sort_keys=True),
            "working_memory_items": working_memory,
            "wisdom_query": memory_data.get("wisdom"),
            "model_calls": client["log"][start_call:],
        }
    finally:
        shutil.rmtree(tempdir, ignore_errors=True)


def model_snapshot(model):
    listing = subprocess.check_output(["ollama", "list"], text=True)
    matching = [line.strip() for line in listing.splitlines() if line.strip().startswith(model)]
    if len(matching) != 1:
        raise ValueError(f"expected exactly one local model row for {model}: {matching}")
    return {"model": model, "ollama_list_row": matching[0]}


def run(output=DEFAULT_OUTPUT):
    config = load_json(CONFIG_PATH)
    lock = load_json(LOCK_PATH)
    dataset = load_json(DATASET_PATH)
    verify_frozen_inputs(config, lock, dataset)
    snapshot = model_snapshot(config["fixed_model"])

    import uruha_brain_mac as brain_mod

    started_at = now()
    startup_dir = tempfile.mkdtemp(prefix="uruha_reflection_startup_")
    brain_mod.DB_PATH = startup_dir
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            brain = brain_mod.UruhaBrainV4_Mac(load_right_brain_model=False)
        call_log = []
        proxy = DeterministicClient(brain.client_logic, config["fixed_seed"], call_log)
        client = {"proxy": proxy, "log": call_log}
        rows = []
        for index, case in enumerate(dataset["cases"]):
            order = CONDITIONS if index % 2 == 0 else tuple(reversed(CONDITIONS))
            condition_rows = {}
            for order_index, condition in enumerate(order):
                condition_rows[condition] = run_condition(
                    brain, client, case, condition, order_index
                )
            rows.append({"case": case, "conditions": condition_rows})
        if len(call_log) > config["model_call_budget_max"]:
            raise ValueError(
                f"reflection pilot exceeded model-call budget: {len(call_log)}"
            )
        brain.stop_async_runtime(join_timeout=0.2)
    finally:
        shutil.rmtree(startup_dir, ignore_errors=True)

    report = {
        "schema": "uruha_reflection_causal_pilot_raw_v1",
        "evidence_status": "frozen_matched_pilot_completed_without_runtime_tuning",
        "started_at": started_at,
        "completed_at": now(),
        "runner_commit": git_value("rev-parse", "HEAD"),
        "runner_branch": git_value("branch", "--show-current"),
        "preregistration_sha256": sha256(CONFIG_PATH),
        "harness_lock_sha256": sha256(LOCK_PATH),
        "dataset_sha256": sha256(DATASET_PATH),
        "conditions": list(CONDITIONS),
        "model_snapshot": snapshot,
        "temperature": config["fixed_temperature"],
        "seed": config["fixed_seed"],
        "model_call_budget_max": config["model_call_budget_max"],
        "model_call_count": len(call_log),
        "model_call_counts_by_kind": {
            kind: sum(1 for row in call_log if row["kind"] == kind)
            for kind in sorted({row["kind"] for row in call_log})
        },
        "right_brain_model_loaded": False,
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
