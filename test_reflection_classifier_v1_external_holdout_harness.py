import hashlib
import json
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

import reflection_classifier_v1_legacy as legacy
import uruha_reflection_runtime as candidate
import run_reflection_classifier_v1_external_holdout as runner


ROOT = Path(__file__).resolve().parent
LOCK_PATH = ROOT / "configs" / "reflection_classifier_v1_external_holdout_harness_lock.json"
DEVELOPMENT_PATH = ROOT / "datasets" / "reflection_classifier_v1_development.json"
BASELINE_PATH = ROOT / "reports" / "reflection_classifier_v1_legacy_baseline.json"


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ReflectionClassifierV1ExternalHoldoutHarnessTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lock = _load(LOCK_PATH)

    def test_every_harness_artifact_is_hash_bound(self):
        bindings = self.lock["frozen_artifacts"]
        for key, expected in bindings.items():
            if not key.endswith("_sha256"):
                continue
            path_key = key.removesuffix("_sha256")
            self.assertIn(path_key, bindings)
            self.assertEqual(_sha256(ROOT / bindings[path_key]), expected, path_key)

    def test_legacy_snapshot_reproduces_every_frozen_development_prediction(self):
        development = _load(DEVELOPMENT_PATH)
        baseline = _load(BASELINE_PATH)
        expected_by_id = {row["id"]: row["observed_type"] for row in baseline["rows"]}
        observed_by_id = {
            case["id"]: legacy.classify_reflection_type(case["text"])
            for case in development["cases"]
        }
        self.assertEqual(observed_by_id, expected_by_id)

    def test_legacy_provenance_points_to_the_exact_historical_runtime(self):
        payload = subprocess.check_output(
            ["git", "show", f"{legacy.LEGACY_RUNTIME_COMMIT}:uruha_reflection_runtime.py"],
            cwd=ROOT,
        )
        self.assertEqual(hashlib.sha256(payload).hexdigest(), legacy.LEGACY_RUNTIME_SHA256)
        self.assertEqual(
            legacy.LEGACY_RUNTIME_SHA256,
            self.lock["legacy_provenance"]["historical_runtime_sha256"],
        )

    def test_runner_has_no_case_specific_answers_or_model_calls(self):
        runner = (ROOT / "run_reflection_classifier_v1_external_holdout.py").read_text(
            encoding="utf-8"
        )
        dataset = _load(
            ROOT / self.lock["frozen_artifacts"]["external_holdout_dataset"]
        )
        for case in dataset["cases"]:
            self.assertNotIn(str(case["source_provenance"]["sentence_id"]), runner)
            self.assertNotIn(case["id"], runner)
        for forbidden in ("localhost:11434", "api/generate", "expected_type\"]"):
            self.assertNotIn(forbidden, runner)
        self.assertEqual(self.lock["model_calls_authorized"], 0)

    def test_freeze_requires_clean_synced_main_and_preserves_runtime_off(self):
        self.assertEqual(self.lock["required_run_branch"], "main")
        self.assertEqual(self.lock["required_head_ref"], "origin/main")
        self.assertFalse(self.lock["holdout_inference_before_harness_merge_authorized"])
        self.assertFalse(self.lock["post_result_case_exclusion_authorized"])
        self.assertFalse(self.lock["post_result_threshold_change_authorized"])
        self.assertFalse(self.lock["runtime_memory_write_authorized"])
        self.assertFalse(self.lock["broad_human_likeness_claim_authorized"])
        self.assertFalse(candidate.typed_reflection_runtime_enabled({}))

    def test_runner_rejects_wrong_branch_dirty_tree_and_artifact_drift(self):
        def git_value_wrong_branch(*args):
            return "codex/test" if args == ("branch", "--show-current") else ""

        with patch.object(runner, "git_value", side_effect=git_value_wrong_branch):
            with self.assertRaisesRegex(ValueError, "must run from main"):
                runner.verify(self.lock)

        def git_value_dirty(*args):
            values = {
                ("branch", "--show-current"): "main",
                ("rev-parse", "HEAD"): "same",
                ("rev-parse", "origin/main"): "same",
                ("status", "--porcelain", "--untracked-files=no"): " M tracked.py",
            }
            return values[args]

        with patch.object(runner, "git_value", side_effect=git_value_dirty):
            with self.assertRaisesRegex(ValueError, "tracked worktree must be clean"):
                runner.verify(self.lock)

        def git_value_clean(*args):
            values = {
                ("branch", "--show-current"): "main",
                ("rev-parse", "HEAD"): "same",
                ("rev-parse", "origin/main"): "same",
                ("status", "--porcelain", "--untracked-files=no"): "",
            }
            return values[args]

        with patch.object(runner, "git_value", side_effect=git_value_clean), patch.object(
            runner, "sha256", return_value="drift"
        ):
            with self.assertRaisesRegex(ValueError, "frozen artifact drift"):
                runner.verify(self.lock)


if __name__ == "__main__":
    unittest.main()
