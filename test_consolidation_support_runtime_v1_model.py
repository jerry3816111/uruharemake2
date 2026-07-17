#!/usr/bin/env python3
"""Validate the frozen local support-attribution transport contract."""

from __future__ import annotations

import json
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

import consolidation_support_runtime_v1_model as model_runtime


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = (
    ROOT
    / "configs"
    / "consolidation_support_runtime_v1_preregistration.json"
)
DATASET_PATH = (
    ROOT / "datasets" / "consolidation_support_runtime_v1_pilot.json"
)


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _source_events(case):
    return [
        {
            **event,
            "episode_id": f"private-episode-{event['index']}",
        }
        for event in case["source_events"]
    ]


class ConsolidationSupportRuntimeV1ModelTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = _load(CONFIG_PATH)
        cls.case = _load(DATASET_PATH)["cases"][0]
        cls.snapshot = {
            "digest": cls.config["model"]["digest"],
            "ollama_tag": cls.config["model"]["ollama_tag"],
        }

    def test_request_contains_only_frozen_model_visible_fields(self):
        body = model_runtime._render_request(
            self.config,
            "wisdom",
            self.case["generated_payload"]["wisdom_rule"],
            _source_events(self.case),
        )
        encoded = json.dumps(body, ensure_ascii=False)
        self.assertEqual(
            body["model"],
            self.config["model"]["ollama_tag"],
        )
        self.assertEqual(len(body["tools"]), 1)
        self.assertEqual(
            body["tools"][0]["function"]["name"],
            "attribute_memory_support",
        )
        for forbidden in (
            self.case["id"],
            "gold_support_event_indices",
            "expected_candidate_outcome",
            "private-episode-1",
        ):
            self.assertNotIn(forbidden, encoded)

    def test_valid_tool_call_is_returned_once_with_frozen_identity(self):
        response = {
            "message": {
                "content": "",
                "tool_calls": [
                    {
                        "function": {
                            "name": "attribute_memory_support",
                            "arguments": {
                                "support_event_indices": [2]
                            },
                        }
                    }
                ],
            }
        }
        attributor = model_runtime.FrozenRuntimeSupportAttributor(
            self.config,
            self.snapshot,
        )
        with mock.patch.object(
            model_runtime,
            "_post_json",
            return_value=response,
        ) as post:
            result = attributor.attribute(
                case_id=self.case["id"],
                memory_kind="wisdom",
                derived_memory=self.case["generated_payload"][
                    "wisdom_rule"
                ],
                source_events=_source_events(self.case),
            )

        self.assertEqual(post.call_count, 1)
        self.assertEqual(len(attributor.calls), 1)
        self.assertTrue(result["parse_success"])
        self.assertEqual(result["support_event_indices"], [2])
        self.assertEqual(
            result["model_digest"],
            self.config["model"]["digest"],
        )
        self.assertEqual(
            result["contract_version"],
            self.config["fixed_support_contract"]["version"],
        )

    def test_transport_failure_is_fail_closed_without_retry(self):
        attributor = model_runtime.FrozenRuntimeSupportAttributor(
            self.config,
            self.snapshot,
        )
        with mock.patch.object(
            model_runtime,
            "_post_json",
            side_effect=urllib.error.URLError("injected"),
        ) as post:
            result = attributor.attribute(
                case_id=self.case["id"],
                memory_kind="episodic",
                derived_memory=self.case["generated_payload"][
                    "episodic_summary"
                ],
                source_events=_source_events(self.case),
            )

        self.assertEqual(post.call_count, 1)
        self.assertFalse(result["parse_success"])
        self.assertIsNotNone(result["transport_error"])
        self.assertEqual(
            attributor.calls[0]["transport_attempts"],
            1,
        )


if __name__ == "__main__":
    unittest.main()
