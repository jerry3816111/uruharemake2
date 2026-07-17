#!/usr/bin/env python3
"""Test V2 pool construction and blind-review contracts."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import build_consolidation_support_equivalence_v2 as builder
import review_consolidation_support_equivalence_v2 as reviewer


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = (
    ROOT
    / "configs"
    / "consolidation_support_equivalence_v2_construction_preregistration.json"
)
POOL_PATH = (
    ROOT
    / "datasets"
    / "consolidation_support_equivalence_v2_pool.json"
)


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


class ConsolidationSupportEquivalenceV2ConstructionTest(
    unittest.TestCase
):
    @classmethod
    def setUpClass(cls):
        cls.config = _load(CONFIG_PATH)
        cls.pool = _load(POOL_PATH)

    def test_builder_is_deterministic_and_matches_frozen_matrix(self):
        rebuilt = builder.build_pool()
        self.assertEqual(rebuilt, self.pool)
        cases = self.pool["cases"]
        self.assertEqual(len(cases), 18)
        self.assertEqual(
            sum(len(case["derived_memories"]) for case in cases),
            54,
        )
        self.assertEqual(
            {
                language: sum(
                    case["language"] == language for case in cases
                )
                for language in ("eng", "jpn", "cmn")
            },
            {"eng": 6, "jpn": 6, "cmn": 6},
        )

    def test_every_memory_has_valid_minimal_sets_and_unions(self):
        for case in self.pool["cases"]:
            for kind in reviewer.MEMORY_KINDS:
                memory = case["derived_memories"][kind]
                minimal = reviewer._canonical_minimal_sets(
                    memory["minimal_support_sets"]
                )
                self.assertEqual(
                    memory["minimal_support_sets"],
                    minimal,
                )
                self.assertEqual(
                    memory["acceptable_support_unions"],
                    reviewer._acceptable_unions(minimal),
                )
                self.assertEqual(
                    memory["support_mode"],
                    "supported" if minimal else "unsupported",
                )

    def test_alternative_minimal_sets_accept_each_route_and_union(self):
        memory = self.pool["cases"][0]["derived_memories"]["wisdom"]
        self.assertEqual(memory["minimal_support_sets"], [[2], [3]])
        self.assertEqual(
            memory["acceptable_support_unions"],
            [[2], [3], [2, 3]],
        )

    def test_review_parser_recomputes_antichain(self):
        response = {
            "message": {
                "content": "",
                "tool_calls": [
                    {
                        "function": {
                            "name": reviewer.TOOL_NAME,
                            "arguments": {
                                "minimal_support_sets": [
                                    [2],
                                    [5],
                                    [2, 5],
                                ]
                            },
                        }
                    }
                ],
            }
        }
        parsed = reviewer._parse_response(response)
        self.assertEqual(parsed["minimal_support_sets"], [[2], [5]])
        self.assertEqual(
            parsed["acceptable_support_unions"],
            [[2], [5], [2, 5]],
        )

    def test_review_parser_rejects_narrative_and_invalid_indices(self):
        narrative = {
            "message": {
                "content": "Here is the answer.",
                "tool_calls": [],
            }
        }
        with self.assertRaisesRegex(ValueError, "narrative_content"):
            reviewer._parse_response(narrative)
        invalid = {
            "message": {
                "content": "",
                "tool_calls": [
                    {
                        "function": {
                            "name": reviewer.TOOL_NAME,
                            "arguments": {
                                "minimal_support_sets": [[True], [7]]
                            },
                        }
                    }
                ],
            }
        }
        with self.assertRaisesRegex(
            ValueError,
            "support_index_contract",
        ):
            reviewer._parse_response(invalid)

    def test_reviewer_request_is_gold_blind(self):
        case = self.pool["cases"][0]
        config = self.config
        body = reviewer._request_body(
            config,
            config["independent_machine_review"]["reviewer_a"],
            case,
            "wisdom",
        )
        visible = json.dumps(body, ensure_ascii=False)
        for forbidden in (
            "minimal_support_sets",
            "acceptable_support_unions",
            "support_universe",
            "support_phenomenon",
            "three_way_canonical_agreement",
        ):
            if forbidden == "minimal_support_sets":
                self.assertEqual(visible.count(forbidden), 2)
                continue
            self.assertNotIn(forbidden, visible)
        self.assertNotIn(case["id"], visible)

    def test_checkpoint_resume_never_duplicates_attempts(self):
        snapshots = {
            name: {
                "ollama_tag": self.config[
                    "independent_machine_review"
                ][name]["ollama_tag"],
                "digest": self.config[
                    "independent_machine_review"
                ][name]["digest"],
                "size": 1,
                "details": {},
            }
            for name in ("reviewer_a", "reviewer_b")
        }
        checkpoint = reviewer._checkpoint_base(
            self.config,
            self.pool,
            snapshots,
        )
        checkpoint["calls"].append(
            {
                "call_key": "reviewer_a::case::episodic",
            }
        )
        checkpoint["transport_attempts"] = 1
        reviewer._verify_checkpoint(
            checkpoint,
            self.config,
            self.pool,
            snapshots,
        )
        checkpoint["calls"].append(
            {
                "call_key": "reviewer_a::case::episodic",
            }
        )
        checkpoint["transport_attempts"] = 2
        with self.assertRaisesRegex(
            RuntimeError,
            "duplicate checkpoint calls",
        ):
            reviewer._verify_checkpoint(
                checkpoint,
                self.config,
                self.pool,
                snapshots,
            )

    def test_atomic_write_leaves_no_partial_file(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "checkpoint.json"
            reviewer._atomic_write(path, {"ok": True})
            self.assertEqual(_load(path), {"ok": True})
            self.assertFalse(path.with_suffix(".json.tmp").exists())


if __name__ == "__main__":
    unittest.main()
