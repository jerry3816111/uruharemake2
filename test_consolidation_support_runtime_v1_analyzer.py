#!/usr/bin/env python3
"""Validate runtime-pilot scoring without model or database calls."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

import analyze_consolidation_support_runtime_v1_pilot as analyzer
import consolidation_support_runtime as support_runtime
from consolidation_support_attribution_v1_core import (
    summarize_condition,
)


ROOT = Path(__file__).resolve().parent
DATASET_PATH = (
    ROOT / "datasets" / "consolidation_support_runtime_v1_pilot.json"
)
MODEL_DIGEST = (
    "2a654d98e6fba55d452b7043684e9b57a947e393bbffa624"
    "85a7aac05ee4eefd"
)


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _perfect_runtime_rows(dataset, condition):
    rows = []
    for case in dataset["cases"]:
        source_ids = [
            f"{case['id']}-E{index}" for index in range(1, 7)
        ]
        if condition == "coarse_runtime_control":
            stored_kinds = list(analyzer.MEMORY_KINDS)
            mode = "three_speed_consolidation"
            source_state = "consolidated"
        else:
            outcome = case["expected_candidate_outcome"]
            stored_kinds = outcome["stored_memory_kinds"]
            mode = (
                "support_attributed_consolidation"
                if outcome["batch_status"] == "stored"
                else "consolidation_unsupported_episodic"
            )
            source_state = (
                "consolidated"
                if outcome["batch_status"] == "stored"
                else "pending"
            )
        derived = []
        for memory_kind in stored_kinds:
            metadata = {}
            if condition != "coarse_runtime_control":
                indices = case["gold_support_event_indices"][
                    memory_kind
                ]
                metadata = support_runtime.support_provenance(
                    {
                        "support_event_indices": indices,
                        "support_episode_ids": [
                            source_ids[index - 1]
                            for index in indices
                        ],
                        "model_digest": MODEL_DIGEST,
                        "contract_version": (
                            "consolidation_support_runtime_v1"
                        ),
                        "wall_seconds": 0.01,
                    }
                )
            derived.append(
                {
                    "memory_kind": memory_kind,
                    "id": f"{case['id']}-{memory_kind}",
                    "document": memory_kind,
                    "metadata": metadata,
                }
            )
        rows.append(
            {
                "case_id": case["id"],
                "source_episode_ids_in_event_order": source_ids,
                "derived_records_after": derived,
                "source_records_after": [
                    {
                        "id": source_id,
                        "metadata": {
                            "consolidation_state": source_state
                        },
                    }
                    for source_id in source_ids
                ],
                "runtime_result": {"mode": mode},
                "case_wall_seconds": 0.03,
            }
        )
    return rows


class ConsolidationSupportRuntimeV1AnalyzerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dataset = _load(DATASET_PATH)

    def test_perfect_support_rows_score_all_eighteen_exact(self):
        cases = analyzer._flat_cases(self.dataset)
        rows = [
            {
                "id": case["id"],
                "parse_success": True,
                "index_contract_success": True,
                "support_event_indices": case[
                    "gold_support_event_indices"
                ],
                "wall_seconds": 0.01,
                "transport_error": None,
            }
            for case in cases
        ]
        score = summarize_condition(cases, rows)
        self.assertEqual(score["exact_set_match_count"], 18)
        self.assertEqual(score["unsupported_empty_count"], 3)
        self.assertEqual(score["evidence_precision"], 1.0)
        self.assertEqual(score["evidence_recall"], 1.0)

    def test_runtime_summary_counts_control_and_candidate(self):
        control = analyzer._runtime_summary(
            self.dataset,
            _perfect_runtime_rows(
                self.dataset,
                "coarse_runtime_control",
            ),
            "coarse_runtime_control",
        )
        candidate = analyzer._runtime_summary(
            self.dataset,
            _perfect_runtime_rows(
                self.dataset,
                "support_attributed_runtime_candidate",
            ),
            "support_attributed_runtime_candidate",
        )
        self.assertEqual(control["stored_record_count"], 18)
        self.assertEqual(
            control["unsupported_derived_records_written"],
            3,
        )
        self.assertEqual(
            control["stored_records_with_exact_support_metadata"],
            0,
        )
        self.assertEqual(candidate["stored_record_count"], 13)
        self.assertEqual(
            candidate["stored_records_with_exact_support_metadata"],
            13,
        )
        self.assertEqual(
            candidate["unsupported_derived_records_written"],
            0,
        )
        self.assertEqual(candidate["successful_batch_count"], 5)
        self.assertEqual(
            candidate[
                "rejected_unsupported_episodic_batch_count"
            ],
            1,
        )
        self.assertEqual(
            candidate["source_episodes_marked_consolidated"],
            30,
        )
        self.assertEqual(
            candidate["source_episodes_left_pending"],
            6,
        )
        self.assertEqual(candidate["partial_batch_count"], 0)

    def test_wrong_event_indices_cannot_pass_exact_metadata_gate(self):
        metadata = support_runtime.support_provenance(
            {
                "support_event_indices": [2],
                "support_episode_ids": ["source-E1"],
                "model_digest": MODEL_DIGEST,
                "contract_version": (
                    "consolidation_support_runtime_v1"
                ),
                "wall_seconds": 0.01,
            }
        )
        self.assertFalse(
            analyzer._metadata_matches_support(
                metadata,
                ["source-E1"],
                [1],
            )
        )


if __name__ == "__main__":
    unittest.main()
