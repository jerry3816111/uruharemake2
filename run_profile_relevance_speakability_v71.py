#!/usr/bin/env python3
"""Run the frozen V71 profile relevance and speakability holdout once."""

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
import urllib.request
from pathlib import Path

import uruha_brain_mac as brain_module
from uruha_memory_validity import resolve_memory_validity
from uruha_profile_memory import compile_profile_memory_record, read_profile_candidates
from uruha_profile_projection import project_profile_candidates
from uruha_profile_relevance import MultilingualProfileSelector, encoder_snapshot_path


ROOT = Path(__file__).resolve().parent
PREREG_PATH = ROOT / "configs/profile_relevance_speakability_v71_preregistration.json"
DATASET_PATH = ROOT / "datasets/profile_relevance_speakability_v71.json"
LOCK_PATH = ROOT / "configs/profile_relevance_speakability_v71_harness_lock.json"
DEFAULT_OUTPUT = ROOT / "reports/profile_relevance_speakability_v71_raw.json"
CONDITIONS = (
    "typed_active_full_projection_control",
    "typed_active_bare_key_selection_control",
    "typed_active_provenance_selection_treatment",
)


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def _clean():
    return not _git("status", "--porcelain")


def _atomic(path, payload):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


class _Completions:
    def __init__(self, target, calls):
        self.target = target
        self.calls = calls

    def create(self, *args, **kwargs):
        kwargs["temperature"] = 0.0
        kwargs["seed"] = 20260771
        self.calls.append({"model": kwargs.get("model"), "temperature": 0.0, "seed": 20260771})
        return self.target.create(*args, **kwargs)


class DeterministicClient:
    def __init__(self, target, calls):
        self.chat = type("Chat", (), {})()
        self.chat.completions = _Completions(target.chat.completions, calls)


@contextlib.contextmanager
def isolated_brain():
    original = brain_module.DB_PATH
    production = Path(original).resolve()
    with tempfile.TemporaryDirectory(prefix="uruha_v71_startup_") as directory:
        path = Path(directory).resolve()
        if path == production:
            raise ValueError("temporary database equals production database")
        brain_module.DB_PATH = str(path)
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                bot = brain_module.UruhaBrainV4_Mac(load_right_brain_model=False)
            calls = []
            client = DeterministicClient(bot.client_logic, calls)
            bot.client_logic = client
            bot.left_brain.client_logic = client
            yield bot, calls, production
        finally:
            brain_module.DB_PATH = original


def _seed(collection, history):
    for row in history:
        record = compile_profile_memory_record(
            row["fact_type"],
            row["value"],
            timestamp=row["timestamp"],
            memory_id=row["memory_id"],
            typed_state=True,
        )
        record["metadata"]["source_utterance"] = row["source_utterance"]
        collection.add(
            ids=[record["memory_id"]],
            documents=[record["document"]],
            metadatas=[record["metadata"]],
        )


def _select(selector, query, active, condition):
    if condition == CONDITIONS[0]:
        selected = list(active)
        return selected, {
            "schema": "uruha_profile_memory_selection_v1",
            "status": "full_projection_control",
            "memory_requested": None,
            "answer_use_authorized": False,
            "selected_memory_ids": [str(row["memory_id"]) for row in selected],
            "request_scores": {},
            "candidate_scores": [],
            "selector_seconds": 0.0,
            "include_provenance": None,
        }
    result = selector.select(
        query,
        active,
        include_provenance=condition == CONDITIONS[2],
    )
    return result["selected_candidates"], result["contract"]


@contextlib.contextmanager
def _injected_projection(bot, projected, contract):
    original_query = bot.memory.query_all_layers
    bot.memory.session_profile = projected

    def query_with_contract(text):
        data = original_query(text)
        data["profile_memory_selection"] = dict(contract)
        return data

    bot.memory.query_all_layers = query_with_contract
    try:
        yield
    finally:
        bot.memory.query_all_layers = original_query


def run_case(bot, selector, case, condition, production_path):
    with tempfile.TemporaryDirectory(prefix=f"uruha_v71_{case['id']}_") as directory:
        path = Path(directory).resolve()
        if path == production_path:
            raise ValueError("case database equals production database")
        with contextlib.redirect_stdout(io.StringIO()):
            bot.reset_session(db_path=str(path))
            _seed(bot.memory.profile_col, case["profile_history"])
            candidates = read_profile_candidates(bot.memory.profile_col)
            reference_time = max(row["timestamp"] for row in case["profile_history"])
            active = resolve_memory_validity(candidates, reference_time=reference_time)["eligible_candidates"]
            selected, contract = _select(selector, case["user_input"], active, condition)
            projected = project_profile_candidates(selected)
            with _injected_projection(bot, projected, contract):
                started_turn = time.perf_counter()
                result = bot.run_turn_debug(case["user_input"])
                turn_seconds = time.perf_counter() - started_turn
        logic = result["logic"]
        reasons = bot.right_brain._model_candidate_rejection_reasons(
            result["reply"], logic, 64, user_input=case["user_input"]
        )
        return {
            "case_id": case["id"],
            "scenario_family": case["scenario_family"],
            "condition": condition,
            "reply": result["reply"],
            "intent": logic.get("intent"),
            "reply_goal": logic.get("reply_goal"),
            "selected_memory_ids": [str(row["memory_id"]) for row in selected],
            "active_memory_ids": [str(row["memory_id"]) for row in active],
            "projected_profile": projected,
            "selection_contract": contract,
            "surface_gate_pass": not reasons,
            "surface_reasons": reasons,
            "turn_seconds": turn_seconds,
            "temporary_database": True,
        }


def verify_lock(lock):
    return [
        name
        for name, artifact in lock["frozen_artifacts"].items()
        if not (ROOT / artifact["path"]).exists()
        or _sha256(ROOT / artifact["path"]) != artifact["sha256"]
    ]


def verify_encoder_artifacts(lock):
    snapshot = encoder_snapshot_path()
    failures = []
    for name, artifact in lock["environment"]["encoder_artifacts"].items():
        path = snapshot / artifact["path"]
        if not path.exists() or _sha256(path) != artifact["sha256"]:
            failures.append(name)
    return failures


def _run_locked_tests(lock):
    completed = subprocess.run(
        [sys.executable, *lock["preflight"]["arguments"]],
        cwd=ROOT,
        capture_output=True,
        text=True,
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
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "observed_test_count": observed,
        "expected_test_count": expected,
        "passed": completed.returncode == 0 and observed == expected,
    }


def preflight(output, formal):
    lock = _load(LOCK_PATH)
    failures = [f"artifact_drift:{name}" for name in verify_lock(lock)]
    failures.extend(f"encoder_artifact_drift:{name}" for name in verify_encoder_artifacts(lock))
    if formal:
        formal_run = lock["formal_run"]
        if not lock["formal_inference_authorized_only_after_lock_merge"]:
            failures.append("lock_merge_requirement_missing")
        if not formal_run["formal_inference_authorized"]:
            failures.append("formal_inference_not_authorized")
        if formal_run["production_database_access_authorized"]:
            failures.append("production_database_access_must_remain_forbidden")
        if formal_run["physical_action_authorized"]:
            failures.append("physical_actions_must_remain_forbidden")
        with urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=10) as response:
            models = json.load(response).get("models", [])
        model = next((row for row in models if row.get("name") == "qwen2.5:7b"), None)
        if not model or model.get("digest") != lock["environment"]["leftbrain_digest"]:
            failures.append("model_digest_drift")
        if not _clean():
            failures.append("dirty_tracked_tree")
        if _git("branch", "--show-current") != formal_run["required_run_branch"]:
            failures.append("wrong_branch")
        if _git("rev-parse", "HEAD") != _git("rev-parse", formal_run["required_head_ref"]):
            failures.append("head_not_origin_main")
        if output.exists():
            failures.append("result_exists")
    return lock, failures


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--preflight-only", action="store_true")
    args = parser.parse_args()
    lock, failures = preflight(args.output, not args.preflight_only)
    if failures:
        print(json.dumps({"passed": False, "failures": failures}, indent=2))
        raise SystemExit(1)
    if args.preflight_only:
        print(json.dumps({"passed": True}, indent=2))
        return
    test_result = _run_locked_tests(lock)
    if not test_result["passed"]:
        print(json.dumps(test_result, indent=2))
        raise SystemExit("V71 locked preflight tests failed")

    selector = MultilingualProfileSelector()
    rows = []
    dataset = _load(DATASET_PATH)
    with isolated_brain() as (bot, calls, production):
        for source in dataset["cases"]:
            case = {
                key: source[key]
                for key in ("id", "scenario_family", "user_input", "profile_history")
            }
            for condition in CONDITIONS:
                rows.append(run_case(bot, selector, case, condition, production))
    selector_times = [
        row["selection_contract"]["selector_seconds"]
        for row in rows
        if row["condition"] != CONDITIONS[0]
    ]
    raw = {
        "schema": "uruha_profile_relevance_speakability_raw_v71",
        "git_head": _git("rev-parse", "HEAD"),
        "case_count": 24,
        "row_count": len(rows),
        "conditions": list(CONDITIONS),
        "gold_in_raw": False,
        "locked_preflight": test_result,
        "encoder_load_seconds": selector.load_seconds,
        "encoder_peak_rss_delta_bytes": selector.peak_rss_delta_bytes,
        "selector_call_count": len(selector_times),
        "leftbrain_call_count": len(calls),
        "leftbrain_calls": calls,
        "rightbrain_model_loading": False,
        "production_database_access_count": 0,
        "physical_action_count": 0,
        "transport_error_count": 0,
        "rows": rows,
    }
    _atomic(args.output, raw)
    print(
        json.dumps(
            {
                "output": str(args.output),
                "rows": len(rows),
                "selector_calls": len(selector_times),
                "leftbrain_calls": len(calls),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
