#!/usr/bin/env python3
"""Validate the bounded source-pointer candidate implementation."""

from __future__ import annotations

import hashlib
import json
import unittest
from unittest import mock

import uruha_brain_mac as brain
import uruha_memory_runtime as memory_runtime


def _pointer_metadata(source_ids, batch_id="batch-1"):
    encoded = json.dumps(
        sorted(source_ids),
        separators=(",", ":"),
    )
    return {
        "source": "idle_consolidation",
        "source_episode_ids": encoded,
        "source_episode_count": len(source_ids),
        "source_episode_ids_sha256": hashlib.sha256(
            encoded.encode("utf-8")
        ).hexdigest(),
        "consolidation_batch_id": batch_id,
    }


class ConsolidationSourcePointerV1CandidateTest(unittest.TestCase):
    def test_pointer_parser_accepts_only_complete_canonical_provenance(self):
        valid = _pointer_metadata(["source-b", "source-a"])
        parsed = memory_runtime.parse_consolidation_source_pointer(valid)
        self.assertTrue(parsed["valid"])
        self.assertEqual(
            parsed["source_episode_ids"],
            ["source-a", "source-b"],
        )
        for key, expected_reason in (
            ("source_episode_ids", "malformed_source_episode_ids"),
            ("source_episode_ids_sha256", "source_episode_digest_mismatch"),
            ("consolidation_batch_id", "missing_consolidation_batch_id"),
        ):
            with self.subTest(key=key):
                invalid = dict(valid)
                if key == "source_episode_ids":
                    invalid[key] = "[invalid"
                else:
                    invalid[key] = ""
                result = memory_runtime.parse_consolidation_source_pointer(
                    invalid
                )
                self.assertFalse(result["valid"])
                self.assertEqual(result["reason"], expected_reason)

    def test_exact_user_text_is_extracted_without_assistant_content(self):
        document = (
            "Time: 2026-07-18 00:00:00 | Intent: chat | "
            "User: I keep it in the blue drawer. | Summary: storage | "
            "Uruha: Maybe the red drawer."
        )
        self.assertEqual(
            memory_runtime.episode_user_text(document),
            "I keep it in the blue drawer.",
        )
        self.assertEqual(
            memory_runtime.episode_user_text("unstructured text"),
            "",
        )

    def test_manager_attaches_at_most_one_source_without_reordering(self):
        manager = object.__new__(brain.MemoryManager)
        manager.episode_col = object()
        pointer = _pointer_metadata(["source-1"])
        items = [
            {
                "source": "wisdom",
                "memory_id": "derived-1",
                "text": "first",
                "metadata": pointer,
                "score": 1.0,
            },
            {
                "source": "procedural",
                "memory_id": "derived-2",
                "text": "second",
                "metadata": pointer,
                "score": 0.9,
            },
        ]
        resolved = {
            "source_evidence": [
                {
                    "source": "episode",
                    "memory_id": "source-1",
                    "user_text": "Exact user source.",
                    "text": "User: Exact user source.",
                    "score": 0.8,
                }
            ],
            "audit": {
                "status": "attached",
                "reason": "verified_exact_source_attached",
                "gold_used": False,
            },
        }
        with mock.patch.object(
            brain.umr,
            "resolve_consolidation_source_evidence",
            return_value=resolved,
        ) as resolve:
            enriched = manager._attach_consolidation_source_evidence(
                "question",
                items,
            )
        self.assertEqual(
            [item["memory_id"] for item in enriched],
            ["derived-1", "derived-2"],
        )
        self.assertEqual(resolve.call_count, 1)
        self.assertEqual(len(enriched[0]["source_evidence"]), 1)
        self.assertNotIn("source_evidence", enriched[1])

    def test_summary_exposes_only_attached_exact_user_text(self):
        item = {
            "source": "wisdom",
            "text": "Derived gist.",
            "score": 1.0,
            "source_evidence": [
                {
                    "user_text": "Exact original user statement.",
                }
            ],
        }
        summary = memory_runtime.working_memory_summary([item])
        self.assertIn(
            "exact_user_source: Exact original user statement.",
            summary,
        )


if __name__ == "__main__":
    unittest.main()
