#!/usr/bin/env python3
"""Run the frozen temporary-Chroma support-attribution runtime pilot."""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import io
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.request
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import uruha_brain_mac as brain
from consolidation_support_runtime_v1_model import (
    FrozenRuntimeSupportAttributor,
)


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = (
    ROOT
    / "configs"
    / "consolidation_support_runtime_v1_preregistration.json"
)
LOCK_PATH = (
    ROOT
    / "configs"
    / "consolidation_support_runtime_v1_harness_lock.json"
)
DEFAULT_OUTPUT = (
    ROOT
    / "reports"
    / "consolidation_support_runtime_v1_pilot_raw.json"
)
TAGS_URL = "http://127.0.0.1:11434/api/tags"
TZ = ZoneInfo("Asia/Tokyo")


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git(*args):
    return subprocess.check_output(
        ["git", *args],
        cwd=ROOT,
        text=True,
    ).strip()


def _atomic_write(path, payload):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


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


def _model_snapshot(config):
    inventory = {
        row["name"]: row
        for row in (_get_json(TAGS_URL).get("models") or [])
    }
    frozen = config["model"]
    row = inventory.get(frozen["ollama_tag"])
    if not row or row.get("digest") != frozen["digest"]:
        raise ValueError("missing or drifted local attribution model")
    return {
        "ollama_tag": frozen["ollama_tag"],
        "digest": row["digest"],
        "size_bytes": row.get("size"),
        "details": row.get("details") or {},
    }


def _verify_frozen_artifacts(lock):
    failed = []
    for artifact in lock["frozen_artifacts"].values():
        path = ROOT / artifact["path"]
        if not path.exists() or _sha256(path) != artifact["sha256"]:
            failed.append(artifact["path"])
    if failed:
        raise ValueError(
            "drifted frozen artifacts: " + ", ".join(failed)
        )


class PayloadCompletions:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content=json.dumps(
                            self.payload,
                            ensure_ascii=False,
                        )
                    )
                )
            ]
        )


def _client(payload):
    completions = PayloadCompletions(payload)
    return (
        SimpleNamespace(chat=SimpleNamespace(completions=completions)),
        completions,
    )


def _source_records(memory):
    payload = memory.episode_col.get(
        where={"source": "turn_episode"},
        include=["documents", "metadatas"],
    )
    return [
        {
            "id": source_id,
            "document": payload["documents"][index],
            "metadata": payload["metadatas"][index],
        }
        for index, source_id in enumerate(payload.get("ids") or [])
    ]


def _derived_records(memory):
    specs = {
        "episodic": (
            memory.episode_col,
            "episodic_consolidation",
        ),
        "wisdom": (
            memory.wisdom_col,
            "idle_consolidation",
        ),
        "procedural": (
            memory.procedural_col,
            "idle_consolidation",
        ),
    }
    records = []
    for kind, (collection, source) in specs.items():
        payload = collection.get(
            where={"source": source},
            include=["documents", "metadatas"],
        )
        for index, memory_id in enumerate(payload.get("ids") or []):
            records.append(
                {
                    "memory_kind": kind,
                    "id": memory_id,
                    "document": payload["documents"][index],
                    "metadata": payload["metadatas"][index],
                }
            )
    return records


@contextlib.contextmanager
def _temporary_memory():
    production_path = Path(brain.DB_PATH).resolve()
    original_db_path = brain.DB_PATH
    with tempfile.TemporaryDirectory(
        prefix="uruha_support_runtime_formal_"
    ) as temporary:
        temporary_path = Path(temporary).resolve()
        if temporary_path == production_path:
            raise ValueError("temporary database equals production path")
        brain.DB_PATH = str(temporary_path)
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                memory = brain.MemoryManager()
            yield memory, {
                "temporary_database": True,
                "production_database_path": str(production_path),
                "temporary_database_path": str(temporary_path),
                "production_database_opened": False,
            }
        finally:
            brain.DB_PATH = original_db_path


def _save_case(memory, case):
    source_ids = []
    for event in case["source_events"]:
        memory.save_episode(
            event["user"],
            event["assistant"],
            {"mood": 0, "trust": 50},
            {"intent": "chat", "scene": "casual"},
        )
        source_ids.append(memory._last_saved_episode_id)
    return source_ids


def _run_case(condition, case, model_attributor=None):
    with _temporary_memory() as (memory, isolation):
        source_ids = _save_case(memory, case)
        source_before = _source_records(memory)
        client, completions = _client(case["generated_payload"])
        support_attributor = None
        if model_attributor is not None:
            support_attributor = lambda **kwargs: (
                model_attributor.attribute(
                    case_id=case["id"],
                    **kwargs,
                )
            )
        started = time.perf_counter()
        result = memory.consolidate_recent_experiences(
            client,
            minimum_turns=6,
            force=True,
            support_attributor=support_attributor,
        )
        wall_seconds = round(time.perf_counter() - started, 6)
        source_after = _source_records(memory)
        derived_after = _derived_records(memory)
    return {
        "case_id": case["id"],
        "language": case["language"],
        "condition": condition,
        "source_episode_ids_in_event_order": source_ids,
        "source_records_before": source_before,
        "source_records_after": source_after,
        "derived_records_after": derived_after,
        "runtime_result": result,
        "generator_stub_calls": len(completions.calls),
        "case_wall_seconds": wall_seconds,
        "database_isolation": isolation,
    }


def _runtime_cases(dataset):
    return [
        {
            "id": case["id"],
            "language": case["language"],
            "source_events": case["source_events"],
            "generated_payload": case["generated_payload"],
        }
        for case in dataset["cases"]
    ]


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
            "TOKENIZERS_PARALLELISM": "false",
        },
    )
    return {
        "command": command,
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "passed": completed.returncode == 0,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit(f"refusing to overwrite formal result: {args.output}")
    if _git("branch", "--show-current") != "main":
        raise SystemExit("formal run requires the main branch")
    if _git("status", "--porcelain"):
        raise SystemExit("formal run requires a clean worktree")

    config = _load(CONFIG_PATH)
    lock = _load(LOCK_PATH)
    _verify_frozen_artifacts(lock)
    dataset = _load(ROOT / config["dataset"]["path"])
    preflight = _run_preflight(lock)
    if not preflight["passed"]:
        raise SystemExit("frozen preflight failed before model inference")
    if _ollama_version() != config["local_runtime"]["ollama_version"]:
        raise SystemExit("Ollama version drift")
    model_snapshot = _model_snapshot(config)
    runtime_cases = _runtime_cases(dataset)

    started_at = datetime.now(TZ).isoformat(timespec="seconds")
    control_rows = [
        _run_case("coarse_runtime_control", case)
        for case in runtime_cases
    ]
    model_attributor = FrozenRuntimeSupportAttributor(
        config,
        model_snapshot,
    )
    candidate_rows = [
        _run_case(
            "support_attributed_runtime_candidate",
            case,
            model_attributor,
        )
        for case in runtime_cases
    ]
    completed_at = datetime.now(TZ).isoformat(timespec="seconds")
    raw = {
        "schema": "uruha_consolidation_support_runtime_raw_v1",
        "experiment_id": config["experiment_id"],
        "runner_commit": _git("rev-parse", "HEAD"),
        "runner_branch": _git("branch", "--show-current"),
        "started_at": started_at,
        "completed_at": completed_at,
        "ollama_version": _ollama_version(),
        "model_snapshot": model_snapshot,
        "harness_lock_sha256": _sha256(LOCK_PATH),
        "frozen_artifact_hashes": {
            name: _sha256(ROOT / artifact["path"])
            for name, artifact in lock["frozen_artifacts"].items()
        },
        "preflight": preflight,
        "gold_or_expected_outcome_passed_to_runtime": False,
        "production_database_writes": 0,
        "control": control_rows,
        "candidate": candidate_rows,
        "candidate_model_calls": model_attributor.calls,
        "candidate_model_call_count": len(model_attributor.calls),
        "candidate_transport_attempt_count": sum(
            call["transport_attempts"]
            for call in model_attributor.calls
        ),
        "inflight_request_at_completion": None,
    }
    _atomic_write(args.output, raw)
    print(
        json.dumps(
            {
                "experiment_id": raw["experiment_id"],
                "runner_commit": raw["runner_commit"],
                "control_cases": len(control_rows),
                "candidate_cases": len(candidate_rows),
                "model_calls": raw["candidate_model_call_count"],
                "transport_attempts": raw[
                    "candidate_transport_attempt_count"
                ],
                "output": str(args.output),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
