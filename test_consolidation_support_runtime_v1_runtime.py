#!/usr/bin/env python3
"""Exercise support-attributed consolidation in temporary Chroma stores."""

from __future__ import annotations

import contextlib
import json
import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock

import uruha_brain_mac as brain


MODEL_DIGEST = (
    "2a654d98e6fba55d452b7043684e9b57a947e393bbffa624"
    "85a7aac05ee4eefd"
)
CONTRACT_VERSION = "consolidation_support_runtime_v1"
DATASET_PATH = (
    brain.BASE_DIR
    + "/datasets/consolidation_support_runtime_v1_pilot.json"
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


class GoldStubAttributor:
    def __init__(self, gold, *, fail_kind=None, invalid_kind=None):
        self.gold = gold
        self.fail_kind = fail_kind
        self.invalid_kind = invalid_kind
        self.calls = []

    def __call__(
        self,
        *,
        memory_kind,
        derived_memory,
        source_events,
    ):
        self.calls.append(
            {
                "memory_kind": memory_kind,
                "derived_memory": derived_memory,
                "source_events": source_events,
            }
        )
        if memory_kind == self.fail_kind:
            raise RuntimeError("injected attribution failure")
        if memory_kind == self.invalid_kind:
            return {
                "parse_success": True,
                "index_contract_success": True,
                "support_event_indices": [99],
                "model_digest": MODEL_DIGEST,
                "contract_version": CONTRACT_VERSION,
                "wall_seconds": 0.01,
            }
        return {
            "parse_success": True,
            "index_contract_success": True,
            "support_event_indices": list(self.gold[memory_kind]),
            "model_digest": MODEL_DIGEST,
            "contract_version": CONTRACT_VERSION,
            "wall_seconds": 0.01,
            "transport_error": None,
        }


def _load_cases():
    with open(DATASET_PATH, encoding="utf-8") as handle:
        payload = json.load(handle)
    return {case["id"]: case for case in payload["cases"]}


@contextlib.contextmanager
def _temporary_memory():
    original_db_path = brain.DB_PATH
    with tempfile.TemporaryDirectory(
        prefix="uruha_support_runtime_v1_"
    ) as temporary:
        brain.DB_PATH = temporary
        try:
            yield brain.MemoryManager()
        finally:
            brain.DB_PATH = original_db_path


def _client(payload):
    completions = PayloadCompletions(payload)
    return (
        SimpleNamespace(chat=SimpleNamespace(completions=completions)),
        completions,
    )


def _save_case(memory, case):
    episode_ids = []
    for event in case["source_events"]:
        memory.save_episode(
            event["user"],
            event["assistant"],
            {"mood": 0, "trust": 50},
            {"intent": "chat", "scene": "casual"},
        )
        episode_ids.append(memory._last_saved_episode_id)
    return episode_ids


def _source_records(memory):
    payload = memory.episode_col.get(
        where={"source": "turn_episode"},
        include=["documents", "metadatas"],
    )
    return {
        source_id: {
            "document": payload["documents"][index],
            "metadata": payload["metadatas"][index],
        }
        for index, source_id in enumerate(payload.get("ids") or [])
    }


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
    records = {}
    for kind, (collection, source) in specs.items():
        payload = collection.get(
            where={"source": source},
            include=["documents", "metadatas"],
        )
        for index, memory_id in enumerate(payload.get("ids") or []):
            records[kind] = {
                "id": memory_id,
                "document": payload["documents"][index],
                "metadata": payload["metadatas"][index],
            }
    return records


def _run(memory, case, attributor=None):
    client, completions = _client(case["generated_payload"])
    result = memory.consolidate_recent_experiences(
        client,
        minimum_turns=6,
        force=True,
        support_attributor=attributor,
    )
    return result, completions


class ConsolidationSupportRuntimeV1RuntimeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = _load_cases()

    def test_default_control_preserves_current_coarse_behavior(self):
        case = self.cases["csr1_eng_ceramics_workshop"]
        with _temporary_memory() as memory:
            source_ids = _save_case(memory, case)
            result, completions = _run(memory, case)

            records = _derived_records(memory)
            self.assertEqual(len(completions.calls), 1)
            self.assertEqual(result["mode"], "three_speed_consolidation")
            self.assertEqual(set(records), {
                "episodic",
                "wisdom",
                "procedural",
            })
            for record in records.values():
                self.assertEqual(
                    sorted(
                        json.loads(
                            record["metadata"]["source_episode_ids"]
                        )
                    ),
                    sorted(source_ids),
                )
                self.assertNotIn(
                    "support_episode_ids",
                    record["metadata"],
                )

    def test_optional_unsupported_rule_is_suppressed_with_exact_support(self):
        case = self.cases["csr1_eng_ceramics_workshop"]
        attributor = GoldStubAttributor(
            case["gold_support_event_indices"]
        )
        with _temporary_memory() as memory:
            source_ids = _save_case(memory, case)
            result, completions = _run(memory, case, attributor)

            records = _derived_records(memory)
            self.assertEqual(len(completions.calls), 1)
            self.assertEqual(len(attributor.calls), 3)
            self.assertEqual(
                result["mode"],
                "support_attributed_consolidation",
            )
            self.assertEqual(
                result["stored_memory_kinds"],
                ["episodic", "procedural"],
            )
            self.assertEqual(
                result["suppressed_memory_kinds"],
                ["wisdom"],
            )
            self.assertEqual(set(records), {"episodic", "procedural"})
            for kind, record in records.items():
                expected_ids = sorted(
                    source_ids[index - 1]
                    for index in case[
                        "gold_support_event_indices"
                    ][kind]
                )
                metadata = record["metadata"]
                self.assertEqual(
                    json.loads(metadata["support_episode_ids"]),
                    expected_ids,
                )
                self.assertEqual(
                    metadata["support_episode_count"],
                    len(expected_ids),
                )
                self.assertEqual(
                    metadata["support_attribution_model_digest"],
                    MODEL_DIGEST,
                )
                self.assertEqual(
                    metadata[
                        "support_attribution_contract_version"
                    ],
                    CONTRACT_VERSION,
                )
            self.assertEqual(
                {
                    record["metadata"]["consolidation_state"]
                    for record in _source_records(memory).values()
                },
                {"consolidated"},
            )

    def test_unsupported_episodic_rejects_the_entire_batch(self):
        case = self.cases["csr1_jpn_bakery_shift"]
        attributor = GoldStubAttributor(
            case["gold_support_event_indices"]
        )
        with _temporary_memory() as memory:
            _save_case(memory, case)
            result, _ = _run(memory, case, attributor)

            self.assertEqual(len(attributor.calls), 3)
            self.assertEqual(
                result["mode"],
                "consolidation_unsupported_episodic",
            )
            self.assertEqual(_derived_records(memory), {})
            self.assertEqual(result["marked_consolidated_count"], 0)
            self.assertEqual(
                {
                    record["metadata"]["consolidation_state"]
                    for record in _source_records(memory).values()
                },
                {"pending"},
            )

    def test_attribution_exception_and_invalid_index_are_atomic(self):
        case = self.cases["csr1_eng_balcony_herbs"]
        variants = (
            GoldStubAttributor(
                case["gold_support_event_indices"],
                fail_kind="wisdom",
            ),
            GoldStubAttributor(
                case["gold_support_event_indices"],
                invalid_kind="wisdom",
            ),
        )
        for attributor in variants:
            with self.subTest(attributor=type(attributor).__name__):
                with _temporary_memory() as memory:
                    _save_case(memory, case)
                    before = _source_records(memory)
                    result, _ = _run(memory, case, attributor)

                    self.assertEqual(
                        result["mode"],
                        "consolidation_attribution_failed",
                    )
                    self.assertEqual(_derived_records(memory), {})
                    self.assertEqual(_source_records(memory), before)
                    self.assertEqual(
                        memory._consolidated_turn_index,
                        0,
                    )

    def test_each_derived_collection_write_failure_rolls_back(self):
        case = self.cases["csr1_eng_balcony_herbs"]
        for collection_name in (
            "episode_col",
            "wisdom_col",
            "procedural_col",
        ):
            with self.subTest(collection=collection_name):
                attributor = GoldStubAttributor(
                    case["gold_support_event_indices"]
                )
                with _temporary_memory() as memory:
                    _save_case(memory, case)
                    before = _source_records(memory)
                    collection = getattr(memory, collection_name)
                    with mock.patch.object(
                        collection,
                        "add",
                        side_effect=RuntimeError(
                            f"injected {collection_name} write failure"
                        ),
                    ):
                        result, _ = _run(
                            memory,
                            case,
                            attributor,
                        )

                    self.assertEqual(
                        result["mode"],
                        "consolidation_write_failed",
                    )
                    self.assertTrue(result["rollback_complete"])
                    self.assertEqual(_derived_records(memory), {})
                    self.assertEqual(_source_records(memory), before)

    def test_partial_source_transition_is_restored_and_retryable(self):
        case = self.cases["csr1_eng_balcony_herbs"]
        attributor = GoldStubAttributor(
            case["gold_support_event_indices"]
        )
        with _temporary_memory() as memory:
            source_ids = _save_case(memory, case)
            before = _source_records(memory)

            def partial_transition(*args, **kwargs):
                first_id = source_ids[0]
                metadata = dict(
                    _source_records(memory)[first_id]["metadata"]
                )
                metadata["consolidation_state"] = "consolidated"
                memory.episode_col.update(
                    ids=[first_id],
                    metadatas=[metadata],
                )
                return 1

            with mock.patch.object(
                memory,
                "_mark_source_episodes_consolidated",
                side_effect=partial_transition,
            ):
                result, _ = _run(memory, case, attributor)

            self.assertEqual(
                result["mode"],
                "consolidation_source_transition_failed",
            )
            self.assertTrue(result["rollback_complete"])
            self.assertEqual(_derived_records(memory), {})
            self.assertEqual(_source_records(memory), before)
            self.assertEqual(memory._consolidated_turn_index, 0)

            retry_attributor = GoldStubAttributor(
                case["gold_support_event_indices"]
            )
            retried, _ = _run(memory, case, retry_attributor)
            self.assertEqual(
                retried["mode"],
                "support_attributed_consolidation",
            )
            self.assertEqual(len(_derived_records(memory)), 3)
            self.assertEqual(
                {
                    record["metadata"]["consolidation_state"]
                    for record in _source_records(memory).values()
                },
                {"consolidated"},
            )


if __name__ == "__main__":
    unittest.main()
