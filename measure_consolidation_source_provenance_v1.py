#!/usr/bin/env python3
"""Measure source retention and provenance in three-speed consolidation."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path
from types import SimpleNamespace

import uruha_brain_mac as brain


ROOT = Path(__file__).resolve().parent
DEFAULT_OUTPUT = (
    ROOT
    / "reports"
    / "consolidation_source_provenance_v1_baseline.json"
)


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _source_id_digest(source_ids):
    encoded = json.dumps(
        sorted(source_ids), ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class StubCompletions:
    def __init__(self):
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        payload = {
            "episodic_summary": "二十件の会話経験を整理した。",
            "wisdom_rule": "Userには継続的な制約がある。",
            "procedural_rule": "次回は制約を先に確認する。",
            "salience": 0.7,
        }
        message = SimpleNamespace(
            content=json.dumps(payload, ensure_ascii=False)
        )
        return SimpleNamespace(
            choices=[SimpleNamespace(message=message)]
        )


def _get(collection, *, source):
    return collection.get(
        where={"source": source},
        include=["documents", "metadatas"],
    )


def _records(payload):
    ids = payload.get("ids") or []
    documents = payload.get("documents") or []
    metadatas = payload.get("metadatas") or []
    return [
        {
            "id": memory_id,
            "document": documents[index] if index < len(documents) else None,
            "metadata": (
                metadatas[index]
                if index < len(metadatas)
                and isinstance(metadatas[index], dict)
                else {}
            ),
        }
        for index, memory_id in enumerate(ids)
    ]


def _derived_records(memory):
    return (
        _records(_get(memory.episode_col, source="episodic_consolidation"))
        + _records(_get(memory.wisdom_col, source="idle_consolidation"))
        + _records(
            _get(memory.procedural_col, source="idle_consolidation")
        )
    )


def _metadata_source_ids(metadata):
    raw = metadata.get("source_episode_ids")
    if not isinstance(raw, str):
        return None
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if (
        not isinstance(parsed, list)
        or not all(isinstance(value, str) and value for value in parsed)
        or len(parsed) != len(set(parsed))
    ):
        return None
    return sorted(parsed)


def measure(case_count=20):
    runtime_commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        text=True,
    ).strip()
    original_db_path = brain.DB_PATH
    completions = StubCompletions()
    client = SimpleNamespace(
        chat=SimpleNamespace(completions=completions)
    )
    with tempfile.TemporaryDirectory(
        prefix="uruha_consolidation_source_provenance_"
    ) as temporary:
        brain.DB_PATH = temporary
        try:
            memory = brain.MemoryManager()
            for index in range(case_count):
                memory.save_episode(
                    f"source provenance user event {index}",
                    f"source provenance reply {index}",
                    {"mood": 0, "trust": 50},
                    {"intent": "chat", "scene": "casual"},
                )
            before_records = _records(
                _get(memory.episode_col, source="turn_episode")
            )
            before_ids = sorted(record["id"] for record in before_records)
            before_documents = {
                record["id"]: record["document"] for record in before_records
            }

            first_result = memory.consolidate_recent_experiences(
                client, minimum_turns=4, force=True
            )
            after_records = _records(
                _get(memory.episode_col, source="turn_episode")
            )
            after_ids = sorted(record["id"] for record in after_records)
            after_documents = {
                record["id"]: record["document"] for record in after_records
            }
            derived_after_first = _derived_records(memory)

            second_result = memory.consolidate_recent_experiences(
                client, minimum_turns=4, force=False
            )
            derived_after_second = _derived_records(memory)

            expected_digest = _source_id_digest(before_ids)
            derived_with_exact_sources = 0
            derived_with_digest = 0
            derived_with_batch = 0
            for record in derived_after_first:
                metadata = record["metadata"]
                source_ids = _metadata_source_ids(metadata)
                if (
                    source_ids == before_ids
                    and metadata.get("source_episode_count")
                    == len(before_ids)
                ):
                    derived_with_exact_sources += 1
                if metadata.get("source_episode_ids_sha256") == expected_digest:
                    derived_with_digest += 1
                if metadata.get("consolidation_batch_id"):
                    derived_with_batch += 1

            source_states = {
                str(record["metadata"].get("consolidation_state") or "missing")
                for record in after_records
            }
            source_batch_ids = {
                str(record["metadata"].get("consolidation_batch_id"))
                for record in after_records
                if record["metadata"].get("consolidation_batch_id")
            }
            return {
                "schema": "uruha_consolidation_source_provenance_measurement_v1",
                "runtime_commit": runtime_commit,
                "runtime_sha256": _sha256(ROOT / "uruha_brain_mac.py"),
                "measurement_uses_temporary_chroma": True,
                "external_model_calls": 0,
                "stub_model_calls_after_first": 1,
                "stub_model_calls_after_second": len(completions.calls),
                "source_episode_count_before": len(before_ids),
                "source_episode_count_after": len(after_ids),
                "source_episode_retention_rate": (
                    round(len(after_ids) / len(before_ids), 4)
                    if before_ids
                    else 0.0
                ),
                "source_episode_ids_unchanged": after_ids == before_ids,
                "source_episode_documents_unchanged": (
                    after_documents == before_documents
                ),
                "source_consolidation_states": sorted(source_states),
                "source_consolidation_batch_count": len(source_batch_ids),
                "derived_record_count_after_first": len(
                    derived_after_first
                ),
                "derived_record_count_after_second": len(
                    derived_after_second
                ),
                "derived_records_with_exact_source_ids": (
                    derived_with_exact_sources
                ),
                "derived_records_with_source_digest": derived_with_digest,
                "derived_records_with_batch_id": derived_with_batch,
                "deleted_episode_count": first_result.get(
                    "deleted_episode_count"
                ),
                "preserved_episode_count": first_result.get(
                    "preserved_episode_count"
                ),
                "marked_consolidated_count": first_result.get(
                    "marked_consolidated_count"
                ),
                "first_mode": first_result.get("mode"),
                "second_mode": second_result.get("mode"),
                "second_pass_created_no_duplicate_derived_records": (
                    len(derived_after_second) == len(derived_after_first)
                ),
            }
        finally:
            brain.DB_PATH = original_db_path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--case-count", type=int, default=20)
    args = parser.parse_args()
    report = measure(args.case_count)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
