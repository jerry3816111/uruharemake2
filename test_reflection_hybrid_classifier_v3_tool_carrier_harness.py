import hashlib
import inspect
import json
import unittest
from pathlib import Path
from unittest.mock import patch

import uruha_reflection_runtime as reflection
import run_reflection_hybrid_classifier_v3_tool_carrier_development as runner


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = (
    ROOT
    / "configs"
    / "reflection_hybrid_classifier_v3_tool_carrier_development_preregistration.json"
)
LOCK_PATH = (
    ROOT / "configs" / "reflection_hybrid_classifier_v3_tool_carrier_harness_lock.json"
)


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ReflectionHybridClassifierV3ToolCarrierHarnessTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = _load(CONFIG_PATH)
        cls.lock = _load(LOCK_PATH)

    def test_every_harness_artifact_is_hash_bound(self):
        bindings = self.lock["frozen_artifacts"]
        for key, expected in bindings.items():
            if not key.endswith("_sha256"):
                continue
            path_key = key.removesuffix("_sha256")
            self.assertIn(path_key, bindings)
            self.assertEqual(_sha256(ROOT / bindings[path_key]), expected, path_key)

    def test_retired_data_is_development_only(self):
        dataset = self.config["dataset"]
        self.assertEqual(
            dataset["status"],
            "retired_failed_holdout_repurposed_as_development_evidence",
        )
        self.assertFalse(dataset["future_holdout_reuse_authorized"])
        self.assertEqual(
            self.config["evidence_role"],
            "development_output_carrier_pilot_not_generalization_test",
        )

    def test_tool_carrier_is_the_only_semantic_architecture_change(self):
        conditions = self.config["conditions"]
        self.assertEqual(
            conditions["single_architecture_variable"],
            "model_decision_output_carrier",
        )
        self.assertEqual(
            self.config["tool_contract"]["function"]["name"],
            "classify_reflection",
        )
        self.assertEqual(
            set(
                self.config["tool_contract"]["function"]["parameters"]["properties"]
                ["reflection_type"]["enum"]
            ),
            {"semantic", "procedural", "interpretive", "none"},
        )

    def test_smallest_first_search_and_model_digests_are_frozen(self):
        models = self.config["model_search"]["ordered_conditions"]
        self.assertEqual(
            [row["model"] for row in models],
            ["qwen3.5:0.8b", "qwen3.5:2b", "qwen3.5:4b", "qwen3.5:9b"],
        )
        self.assertTrue(all(len(row["digest"]) == 64 for row in models))
        self.assertEqual(self.config["model_search"]["maximum_model_calls"], 80)
        self.assertEqual(
            self.config["model_search"]["expected_calls_per_tested_model"], 20
        )

    def test_model_payload_cannot_receive_gold_or_case_answers(self):
        source = inspect.getsource(runner._call_model)
        self.assertNotIn("expected_type", source)
        self.assertNotIn("gold", source)
        dataset = _load(ROOT / self.config["dataset"]["path"])
        combined = self.config["system_prompt"] + json.dumps(
            self.config["tool_contract"], ensure_ascii=False
        )
        for case in dataset["cases"]:
            self.assertNotIn(case["text"], combined)
            self.assertNotIn(case["id"], combined)

    def test_native_tool_parser_is_strict_and_fails_closed(self):
        valid = {
            "message": {
                "content": "",
                "tool_calls": [
                    {
                        "function": {
                            "name": "classify_reflection",
                            "arguments": {"reflection_type": "semantic"},
                        }
                    }
                ],
            }
        }
        self.assertEqual(runner._parse_tool_response(valid)[:2], ("semantic", True))
        missing = {"message": {"content": "semantic"}}
        self.assertEqual(runner._parse_tool_response(missing)[:2], ("none", False))
        wrong_keys = {
            "message": {
                "tool_calls": [
                    {
                        "function": {
                            "name": "classify_reflection",
                            "arguments": {"label": "semantic"},
                        }
                    }
                ]
            }
        }
        self.assertEqual(
            runner._parse_tool_response(wrong_keys)[:2], ("none", False)
        )

    def test_runner_rejects_wrong_branch_and_runtime_remains_off(self):
        def wrong_branch(*args):
            return "codex/test" if args == ("branch", "--show-current") else ""

        with patch.object(runner, "git_value", side_effect=wrong_branch):
            with self.assertRaisesRegex(ValueError, "must run from main"):
                runner.verify(self.config, self.lock)
        self.assertFalse(self.lock["model_inference_before_harness_merge_authorized"])
        self.assertFalse(self.lock["runtime_memory_write_authorized"])
        self.assertFalse(reflection.typed_reflection_runtime_enabled({}))


if __name__ == "__main__":
    unittest.main()
