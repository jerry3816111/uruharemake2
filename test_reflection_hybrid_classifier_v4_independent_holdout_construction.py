#!/usr/bin/env python3

import hashlib
import json
import subprocess
import unittest
from pathlib import Path

from audit_reflection_hybrid_classifier_v4_independent_holdout import audit
from build_reflection_hybrid_classifier_v4_independent_holdout import build


ROOT = Path(__file__).resolve().parent
CLOSURE_PATH = (
    ROOT
    / "configs"
    / "reflection_hybrid_classifier_v4_independent_holdout_construction_closure.json"
)


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ReflectionHybridClassifierV4IndependentHoldoutConstructionTest(
    unittest.TestCase
):
    @classmethod
    def setUpClass(cls):
        cls.closure = _load(CLOSURE_PATH)
        bindings = cls.closure["artifact_bindings"]
        cls.snapshot = _load(ROOT / bindings["source_snapshot"])
        cls.dataset = _load(ROOT / bindings["dataset"])
        cls.audit = _load(ROOT / bindings["audit_json"])

    def test_every_construction_artifact_is_hash_bound(self):
        bindings = self.closure["artifact_bindings"]
        for key, expected in bindings.items():
            if not key.endswith("_sha256"):
                continue
            path_key = key.removesuffix("_sha256")
            self.assertIn(path_key, bindings)
            self.assertEqual(_sha256(ROOT / bindings[path_key]), expected, path_key)

    def test_original_preregistration_is_preserved_in_git_history(self):
        original = self.closure["original_preregistration"]
        payload = subprocess.check_output(
            ["git", "show", f"{original['commit']}:{original['path']}"],
            cwd=ROOT,
        )
        self.assertEqual(hashlib.sha256(payload).hexdigest(), original["sha256"])

    def test_builder_and_auditor_reproduce_frozen_artifacts(self):
        self.assertEqual(build(), self.dataset)
        self.assertEqual(audit(), self.audit)

    def test_balance_source_exactness_and_prior_data_separation(self):
        self.assertEqual(self.dataset["case_count"], 32)
        self.assertEqual(
            self.dataset["class_counts"],
            {"interpretive": 8, "none": 8, "procedural": 8, "semantic": 8},
        )
        self.assertEqual(
            self.dataset["language_counts"], {"cmn": 6, "eng": 16, "jpn": 10}
        )
        self.assertTrue(self.audit["passed"])
        self.assertEqual(self.audit["failed_checks"], [])
        self.assertEqual(self.audit["prior_tatoeba_sentence_id_overlap_count"], 0)
        self.assertEqual(self.audit["existing_reflection_text_overlap_count"], 0)
        self.assertEqual(self.audit["exact_source_text_mismatch_count"], 0)
        self.assertEqual(self.audit["license_counts"], {"CC BY 2.0 FR": 32})

    def test_construction_cannot_run_classifier_or_evaluated_model(self):
        source = "\n".join(
            (ROOT / name).read_text(encoding="utf-8")
            for name in (
                "fetch_tatoeba_reflection_hybrid_classifier_v4_source.py",
                "build_reflection_hybrid_classifier_v4_independent_holdout.py",
                "audit_reflection_hybrid_classifier_v4_independent_holdout.py",
            )
        )
        for forbidden in (
            "classify_reflection_type(",
            "uruha_reflection_runtime",
            "localhost:11434",
            "/api/chat",
            "/api/generate",
        ):
            self.assertNotIn(forbidden, source)
        self.assertFalse(self.snapshot["evaluated_qwen_model_inference_used"])
        self.assertFalse(self.audit["evaluated_qwen_model_inference_performed"])

    def test_construction_pass_authorizes_only_harness_freeze(self):
        self.assertEqual(
            self.closure["decision"],
            "authorize_independent_holdout_evaluation_harness_freeze_only",
        )
        self.assertFalse(self.closure["classifier_evaluation_performed"])
        self.assertFalse(self.closure["runtime_change_authorized"])
        self.assertFalse(self.closure["broad_human_likeness_claim_authorized"])


if __name__ == "__main__":
    unittest.main()
