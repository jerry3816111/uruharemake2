import hashlib
import inspect
import json
import unittest
from pathlib import Path
from unittest.mock import patch

import uruha_reflection_runtime as reflection
import run_reflection_hybrid_classifier_v2_development as runner


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = (
    ROOT / "configs" / "reflection_hybrid_classifier_v2_development_preregistration.json"
)
LOCK_PATH = ROOT / "configs" / "reflection_hybrid_classifier_v2_harness_lock.json"


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ReflectionHybridClassifierV2HarnessTest(unittest.TestCase):
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

    def test_retired_holdout_is_development_only_and_cannot_be_reused(self):
        dataset = self.config["dataset"]
        self.assertEqual(dataset["status"], "retired_failed_holdout_repurposed_as_development_evidence")
        self.assertFalse(dataset["future_holdout_reuse_authorized"])
        self.assertEqual(self.config["evidence_role"], "development_capacity_pilot_not_generalization_test")

    def test_smallest_first_search_and_model_digests_are_frozen(self):
        models = self.config["model_search"]["ordered_conditions"]
        self.assertEqual(
            [row["model"] for row in models],
            ["qwen3.5:0.8b", "qwen3.5:2b", "qwen3.5:4b", "qwen3.5:9b"],
        )
        self.assertTrue(all(len(row["digest"]) == 64 for row in models))
        self.assertEqual(self.config["model_search"]["maximum_model_calls"], 80)
        self.assertEqual(self.config["model_search"]["expected_calls_per_tested_model"], 20)

    def test_model_payload_cannot_receive_gold_or_frozen_case_answers(self):
        source = inspect.getsource(runner._call_model)
        self.assertNotIn("expected_type", source)
        self.assertNotIn("gold", source)
        dataset = _load(ROOT / self.config["dataset"]["path"])
        combined = self.config["system_prompt"] + source
        for case in dataset["cases"]:
            self.assertNotIn(case["text"], combined)
            self.assertNotIn(case["id"], combined)

    def test_response_parser_is_strict_and_fails_to_none(self):
        valid = {"message": {"content": '{"reflection_type":"semantic","contract_ack":"reflection_v2"}'}}
        self.assertEqual(runner._parse_response(valid)[:2], ("semantic", True))
        invalid = {"message": {"content": '{"reflection_type":"semantic"}'}}
        self.assertEqual(runner._parse_response(invalid)[:2], ("none", False))

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
