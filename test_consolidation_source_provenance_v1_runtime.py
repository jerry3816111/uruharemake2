#!/usr/bin/env python3
"""Validate the source-preserving consolidation runtime."""

from __future__ import annotations

import contextlib
import json
import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock

import uruha_brain_mac as brain
from measure_consolidation_source_provenance_v1 import (
    StubCompletions,
    measure,
)


def _client():
    completions = StubCompletions()
    return (
        SimpleNamespace(chat=SimpleNamespace(completions=completions)),
        completions,
    )


@contextlib.contextmanager
def _temporary_memory():
    original_db_path = brain.DB_PATH
    with tempfile.TemporaryDirectory(
        prefix="uruha_consolidation_source_runtime_"
    ) as temporary:
        brain.DB_PATH = temporary
        try:
            yield brain.MemoryManager()
        finally:
            brain.DB_PATH = original_db_path


def _turn_records(memory):
    payload = memory.episode_col.get(
        where={"source": "turn_episode"},
        include=["documents", "metadatas"],
    )
    ids = payload.get("ids") or []
    documents = payload.get("documents") or []
    metadatas = payload.get("metadatas") or []
    return [
        {
            "id": source_id,
            "document": documents[index],
            "metadata": metadatas[index],
        }
        for index, source_id in enumerate(ids)
    ]


def _save_turns(memory, count):
    for index in range(count):
        memory.save_episode(
            f"runtime source event {index}",
            f"runtime source reply {index}",
            {"mood": 0, "trust": 50},
            {"intent": "chat", "scene": "casual"},
        )


class ConsolidationSourceProvenanceV1RuntimeTest(unittest.TestCase):
    def test_frozen_twenty_case_measurement_passes_all_data_gates(self):
        report = measure(20)
        expected = {
            "source_episode_count_before": 20,
            "source_episode_count_after": 20,
            "source_episode_retention_rate": 1.0,
            "source_episode_ids_unchanged": True,
            "source_episode_documents_unchanged": True,
            "source_consolidation_states": ["consolidated"],
            "source_consolidation_batch_count": 1,
            "derived_record_count_after_first": 3,
            "derived_record_count_after_second": 3,
            "derived_records_with_exact_source_ids": 3,
            "derived_records_with_source_digest": 3,
            "derived_records_with_batch_id": 3,
            "deleted_episode_count": 0,
            "preserved_episode_count": 20,
            "marked_consolidated_count": 20,
            "stub_model_calls_after_first": 1,
            "stub_model_calls_after_second": 1,
            "second_mode": "decay_only",
            "second_pass_created_no_duplicate_derived_records": True,
        }
        for key, value in expected.items():
            self.assertEqual(report[key], value, key)

    def test_session_consolidation_marks_only_the_used_source_episodes(self):
        with _temporary_memory() as memory:
            _save_turns(memory, 4)
            before = {
                record["id"]: record["document"]
                for record in _turn_records(memory)
            }
            client, completions = _client()

            result = memory.consolidate_recent_experiences(
                client,
                minimum_turns=4,
                force=False,
            )

            after = _turn_records(memory)
            self.assertEqual(len(completions.calls), 1)
            self.assertEqual(result["preserved_episode_count"], 4)
            self.assertEqual(result["marked_consolidated_count"], 4)
            self.assertEqual(
                {record["id"]: record["document"] for record in after},
                before,
            )
            self.assertEqual(
                {
                    record["metadata"]["consolidation_state"]
                    for record in after
                },
                {"consolidated"},
            )
            self.assertEqual(
                {
                    record["metadata"]["decay_multiplier"]
                    for record in after
                },
                {brain.CONSOLIDATED_EPISODE_DECAY_MULTIPLIER},
            )
            self.assertEqual(
                len(
                    {
                        record["metadata"]["consolidation_batch_id"]
                        for record in after
                    }
                ),
                1,
            )

    def test_legacy_turn_episodes_without_state_are_treated_as_pending(self):
        with _temporary_memory() as memory:
            timestamp = "2026-07-18 00:00:00"
            ids = [f"legacy-source-{index:02d}" for index in range(20)]
            memory.episode_col.add(
                ids=ids,
                documents=[
                    f"legacy source event {index}" for index in range(20)
                ],
                metadatas=[
                    {
                        "source": "turn_episode",
                        "timestamp": timestamp,
                        "decay_flag": False,
                        "decay_multiplier": 1.0,
                    }
                    for _ in ids
                ],
            )
            client, completions = _client()

            result = memory.consolidate_recent_experiences(
                client,
                minimum_turns=4,
                force=False,
            )

            self.assertEqual(len(completions.calls), 1)
            self.assertEqual(result["marked_consolidated_count"], 20)
            records = _turn_records(memory)
            self.assertEqual(len(records), 20)
            self.assertEqual(
                {
                    record["metadata"]["consolidation_state"]
                    for record in records
                },
                {"consolidated"},
            )

    def test_summary_write_failure_leaves_sources_pending_and_retryable(self):
        with _temporary_memory() as memory:
            _save_turns(memory, 4)
            before = {
                record["id"]: (
                    record["document"],
                    dict(record["metadata"]),
                )
                for record in _turn_records(memory)
            }
            client, completions = _client()

            with mock.patch.object(
                memory.episode_col,
                "add",
                side_effect=RuntimeError("injected summary write failure"),
            ):
                failed = memory.consolidate_recent_experiences(
                    client,
                    minimum_turns=4,
                    force=False,
                )

            failed_records = {
                record["id"]: (
                    record["document"],
                    dict(record["metadata"]),
                )
                for record in _turn_records(memory)
            }
            self.assertEqual(failed["mode"], "consolidation_write_failed")
            self.assertEqual(failed["marked_consolidated_count"], 0)
            self.assertEqual(memory._consolidated_turn_index, 0)
            self.assertEqual(failed_records, before)
            self.assertEqual(memory.wisdom_col.count(), 0)
            self.assertEqual(memory.procedural_col.count(), 0)

            retried = memory.consolidate_recent_experiences(
                client,
                minimum_turns=4,
                force=False,
            )
            self.assertEqual(len(completions.calls), 2)
            self.assertEqual(retried["mode"], "three_speed_consolidation")
            self.assertEqual(retried["marked_consolidated_count"], 4)
            self.assertEqual(
                {
                    record["metadata"]["consolidation_state"]
                    for record in _turn_records(memory)
                },
                {"consolidated"},
            )

    def test_all_derived_records_share_exact_program_owned_provenance(self):
        with _temporary_memory() as memory:
            _save_turns(memory, 4)
            source_ids = sorted(
                record["id"] for record in _turn_records(memory)
            )
            client, _ = _client()
            result = memory.consolidate_recent_experiences(
                client,
                minimum_turns=4,
                force=False,
            )

            payloads = [
                memory.episode_col.get(
                    where={"source": "episodic_consolidation"},
                    include=["metadatas"],
                ),
                memory.wisdom_col.get(
                    where={"source": "idle_consolidation"},
                    include=["metadatas"],
                ),
                memory.procedural_col.get(
                    where={"source": "idle_consolidation"},
                    include=["metadatas"],
                ),
            ]
            metadatas = [
                metadata
                for payload in payloads
                for metadata in (payload.get("metadatas") or [])
            ]
            self.assertEqual(len(metadatas), 3)
            for metadata in metadatas:
                self.assertEqual(
                    sorted(json.loads(metadata["source_episode_ids"])),
                    source_ids,
                )
                self.assertEqual(
                    metadata["source_episode_count"],
                    len(source_ids),
                )
                self.assertEqual(
                    metadata["consolidation_batch_id"],
                    result["consolidation_batch_id"],
                )


if __name__ == "__main__":
    unittest.main()
