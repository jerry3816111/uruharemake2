#!/usr/bin/env python3
"""Run the frozen matched typed-reflection V3 development pilot."""

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
CONFIG_PATH = ROOT / "configs" / "typed_reflection_v3_development_preregistration.json"
LOCK_PATH = ROOT / "configs" / "typed_reflection_v3_harness_lock.json"
DATASET_PATH = ROOT / "datasets" / "typed_reflection_v3_development_pilot.json"
DEFAULT_OUTPUT = ROOT / "reports" / "typed_reflection_v3_development_raw.json"
CONTROL = "same_episode_without_typed_reflection_control"
TREATMENT = "same_episode_with_typed_reflection_treatment"
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
    if tuple(config["conditions"]) != CONDITIONS or tuple(lock["conditions"]) != CONDITIONS:
        raise ValueError("typed-reflection condition order drift")
    if dataset["case_count"] != config["case_count"] or len(dataset["cases"]) != config["case_count"]:
        raise ValueError("typed-reflection case count drift")
    for relative, expected in lock["frozen_artifacts"].items():
        if sha256(ROOT / relative) != expected:
            raise ValueError(f"typed-reflection hash mismatch: {relative}")
    if git_value("branch", "--show-current") != lock["required_run_branch"]:
        raise ValueError("typed-reflection pilot can run only from merged main")
    if not tracked_tree_clean():
        raise ValueError("typed-reflection pilot requires a clean tracked worktree and index")
    committed = subprocess.run(
        ["git", "cat-file", "-e", f"HEAD:{LOCK_PATH.relative_to(ROOT)}"],
        cwd=ROOT,
        check=False,
        capture_output=True,
    )
    if committed.returncode != 0:
        raise ValueError("typed-reflection harness lock is not committed")
    forbidden = (
        "post_run_case_editing_authorized",
        "post_run_threshold_change_authorized",
        "large_scale_run_authorized",
        "human_rating_required",
        "paid_api_authorized",
        "broad_human_likeness_claim_authorized",
    )
    if any(config[key] for key in forbidden):
        raise ValueError("typed-reflection preregistration authorizes forbidden drift")


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
        if (
            "You extract ONE grounded reflection" in system_text
            or "Generate only the Japanese gist fields" in system_text
        ):
            call_kind = "typed_reflection_extraction"
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


def typed_reflection_records(memory):
    records = []
    for collection_name, collection in (
        ("wisdom", memory.wisdom_col),
        ("procedural", memory.procedural_col),
    ):
        payload = collection.get(
            where={"source": "typed_reflection"},
            include=["documents", "metadatas"],
        )
        documents = payload.get("documents") or []
        metadatas = payload.get("metadatas") or []
        ids = payload.get("ids") or []
        for index, document in enumerate(documents):
            records.append(
                {
                    "memory_id": ids[index] if index < len(ids) else "",
                    "collection": collection_name,
                    "document": str(document or ""),
                    "metadata": metadatas[index] if index < len(metadatas) else {},
                }
            )
    return records


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
        "procedural_guidance",
    )
    return {key: logic.get(key) for key in keys if logic.get(key) is not None}


def compact_working_memory(memory_data):
    return [
        {
            "source": item.get("source"),
            "text": item.get("text"),
            "score": item.get("score"),
            "metadata": item.get("metadata") or {},
        }
        for item in memory_data.get("working_memory_items") or []
    ]


def provenance_valid(records, source_episode_id, seed_user):
    expected_hash = hashlib.sha256(seed_user.encode("utf-8")).hexdigest()
    if not records:
        return False
    for record in records:
        metadata = record.get("metadata") or {}
        if metadata.get("source") != "typed_reflection":
            return False
        if metadata.get("source_episode_id") != source_episode_id:
            return False
        if metadata.get("source_user_sha256") != expected_hash:
            return False
        if str(metadata.get("evidence_quote") or "") not in seed_user:
            return False
    return True


def run_condition(brain, client, case, condition, order_index):
    tempdir = tempfile.mkdtemp(prefix=f"uruha_typed_v3_{case['id']}_{condition}_")
    start_call = len(client["log"])
    try:
        brain.reset_session(db_path=tempdir)
        brain.client_logic = client["proxy"]
        brain.left_brain.client_logic = client["proxy"]
        seed_logic = {
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
                seed_logic,
            )
            source_episode_id = brain.memory.get_runtime_snapshot()["last_saved_episode_id"]
            reflection_return = None
            if condition == TREATMENT:
                reflection_return = brain.memory.reflect_experience(
                    case["seed_user"],
                    case["seed_assistant"],
                    seed_logic,
                    client["proxy"],
                )
            reflection_state = brain.memory.get_runtime_snapshot().get("last_reflection_result") or {}
            records = typed_reflection_records(brain.memory)
            source_ok = provenance_valid(records, source_episode_id, case["seed_user"])
            brain.memory.clear_session_state()
            brain.memory.reflect_experience = lambda *_args, **_kwargs: None
            result = brain.run_turn_debug(case["future_prompt"])
        memory_data = result.get("memory_data") or {}
        working_memory = compact_working_memory(memory_data)
        retrieved = any(
            (item.get("metadata") or {}).get("source") == "typed_reflection"
            for item in working_memory
        )
        return {
            "condition": condition,
            "condition_order_index": order_index,
            "source_episode_id": source_episode_id,
            "reflection_return": reflection_return,
            "reflection_state": reflection_state,
            "reflection_type_observed": reflection_state.get("reflection_type", "none"),
            "reflection_records": records,
            "source_provenance_valid": source_ok,
            "retrieved_typed_reflection": retrieved,
            "future_reply": result.get("reply") or "",
            "future_logic": compact_logic(result.get("logic") or {}),
            "working_memory_items": working_memory,
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
    if output.exists():
        raise FileExistsError(f"refusing to overwrite existing pilot output: {output}")
    config = load_json(CONFIG_PATH)
    lock = load_json(LOCK_PATH)
    dataset = load_json(DATASET_PATH)
    verify_frozen_inputs(config, lock, dataset)
    snapshot = model_snapshot(config["fixed_model"])

    import uruha_brain_mac as brain_mod

    started_at = now()
    startup_dir = tempfile.mkdtemp(prefix="uruha_typed_v3_startup_")
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
            conditions = {}
            for order_index, condition in enumerate(order):
                conditions[condition] = run_condition(
                    brain, client, case, condition, order_index
                )
            rows.append({"case": case, "conditions": conditions})
        if len(call_log) > config["model_call_budget_max"]:
            raise ValueError(
                f"typed-reflection pilot exceeded model-call budget: {len(call_log)}"
            )
        brain.stop_async_runtime(join_timeout=0.2)
    finally:
        shutil.rmtree(startup_dir, ignore_errors=True)

    report = {
        "schema": "uruha_typed_reflection_development_raw_v3",
        "evidence_status": "frozen_matched_development_pilot_completed_without_runtime_tuning",
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
