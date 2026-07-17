import hashlib
import inspect
import json
import unittest
from pathlib import Path
from unittest.mock import patch

import uruha_reflection_runtime as reflection
import run_reflection_hybrid_classifier_v4_independent_holdout as runner
from reflection_hybrid_classifier_v4_core import scorer_gates


ROOT = Path(__file__).resolve().parent
PREREG_PATH = (
    ROOT
    / "configs"
    / "reflection_hybrid_classifier_v4_independent_holdout_construction_preregistration.json"
)
AMENDMENT_PATH = (
    ROOT
    / "configs"
    / "reflection_hybrid_classifier_v4_independent_holdout_protocol_amendment.json"
)
CARRIER_CONTRACT_PATH = (
    ROOT
    / "configs"
    / "reflection_hybrid_classifier_v3_tool_carrier_development_preregistration.json"
)
LOCK_PATH = (
    ROOT
    / "configs"
    / "reflection_hybrid_classifier_v4_independent_holdout_harness_lock.json"
)


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ReflectionHybridClassifierV4IndependentHoldoutHarnessTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.preregistration = _load(PREREG_PATH)
        cls.amendment = _load(AMENDMENT_PATH)
        cls.contract = _load(CARRIER_CONTRACT_PATH)
        cls.lock = _load(LOCK_PATH)
        cls.dataset = _load(
            ROOT / cls.lock["frozen_artifacts"]["independent_holdout_dataset"]
        )

    def test_every_harness_artifact_is_hash_bound(self):
        bindings = self.lock["frozen_artifacts"]
        for key, expected in bindings.items():
            if not key.endswith("_sha256"):
                continue
            path_key = key.removesuffix("_sha256")
            self.assertIn(path_key, bindings)
            self.assertEqual(_sha256(ROOT / bindings[path_key]), expected, path_key)

    def test_protocol_mapping_preserves_all_capability_gates(self):
        gates = scorer_gates(self.preregistration, self.amendment)
        self.assertEqual(gates["hybrid_correct_count_min"], 28)
        self.assertEqual(gates["hybrid_accuracy_min"], 0.875)
        self.assertEqual(gates["procedural_correct_min"], 6)
        self.assertEqual(gates["interpretive_correct_min"], 6)
        self.assertEqual(gates["none_correct"], 8)
        self.assertEqual(gates["model_call_count_max"], 22)

    def test_selected_model_and_carrier_match_passing_v3_result(self):
        frozen = self.preregistration["frozen_system_conditions"]
        result = _load(
            ROOT / self.lock["frozen_artifacts"]["v3_development_result_lock"]
        )
        self.assertEqual(frozen["selected_model"], "qwen3.5:4b")
        self.assertEqual(frozen["selected_model"], result["local_runtime"]["selected_model"])
        self.assertEqual(
            frozen["selected_model_digest"],
            result["local_runtime"]["selected_model_digest"],
        )
        self.assertEqual(
            self.contract["tool_contract"]["function"]["name"],
            "classify_reflection",
        )

    def test_model_payload_cannot_receive_gold_or_case_answers(self):
        source = inspect.getsource(runner._call_model)
        self.assertNotIn("expected_type", source)
        self.assertNotIn("gold", source)
        combined = self.contract["system_prompt"] + json.dumps(
            self.contract["tool_contract"], ensure_ascii=False
        )
        for case in self.dataset["cases"]:
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
                            "arguments": {"reflection_type": "procedural"},
                        }
                    }
                ],
            }
        }
        self.assertEqual(runner._parse_tool_response(valid)[:2], ("procedural", True))
        content_only = {"message": {"content": "procedural"}}
        self.assertEqual(
            runner._parse_tool_response(content_only)[:2], ("none", False)
        )

    def test_rules_fallback_set_is_exactly_the_frozen_22_cases(self):
        observed = [
            case["id"]
            for case in self.dataset["cases"]
            if reflection.classify_reflection_type(case["text"]) == "none"
        ]
        self.assertEqual(
            observed,
            self.amendment["frozen_rules_feasibility_snapshot"][
                "rules_none_case_ids"
            ],
        )
        self.assertEqual(len(observed), 22)

    def test_runner_rejects_wrong_branch_and_runtime_remains_off(self):
        def wrong_branch(*args):
            return "codex/test" if args == ("branch", "--show-current") else ""

        with patch.object(runner, "git_value", side_effect=wrong_branch):
            with self.assertRaisesRegex(ValueError, "must run from main"):
                runner.verify(
                    self.preregistration,
                    self.amendment,
                    self.contract,
                    self.lock,
                )
        self.assertFalse(self.lock["model_inference_before_harness_merge_authorized"])
        self.assertFalse(self.lock["runtime_memory_write_authorized"])
        self.assertFalse(reflection.typed_reflection_runtime_enabled({}))

    def test_no_result_exists_before_harness_merge(self):
        for path in self.lock["result_artifacts"].values():
            self.assertFalse((ROOT / path).exists(), path)


if __name__ == "__main__":
    unittest.main()
