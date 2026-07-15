#!/usr/bin/env python3

import hashlib
import json
import subprocess
import unittest
from pathlib import Path

from run_predicate_morphology_v60_development import CONDITIONS


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "predicate_morphology_v60_preregistration.json"
LOCK_PATH = ROOT / "configs" / "predicate_morphology_v60_replay_harness_lock.json"


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class PredicateMorphologyV60ReplayHarnessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        cls.lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
        cls.runner_source = (
            ROOT / cls.lock["frozen_artifacts"]["runner"]
        ).read_text(encoding="utf-8")
        cls.analyzer_source = (
            ROOT / cls.lock["frozen_artifacts"]["analyzer"]
        ).read_text(encoding="utf-8")

    def test_every_replay_artifact_is_hash_bound(self):
        frozen = self.lock["frozen_artifacts"]
        for key, expected in frozen.items():
            if not key.endswith("_sha256"):
                continue
            path_key = key.removesuffix("_sha256")
            self.assertIn(path_key, frozen)
            self.assertEqual(_sha256(ROOT / frozen[path_key]), expected, path_key)

    def test_conditions_and_zero_model_policy_are_frozen(self):
        self.assertEqual(tuple(self.lock["conditions"]), CONDITIONS)
        self.assertEqual(
            self.config["development_replay"]["model_calls_authorized"], 0
        )
        self.assertEqual(self.lock["model_calls_authorized"], 0)

    def test_runner_reuses_frozen_v59_evidence_without_gold_or_transport(self):
        for required in (
            'source["shared_fallback_commitment"]',
            'source["candidate_commitment"]',
            'source["candidate_state"]',
            "resolve_v60(",
            "select_commitment(state60, fallback)",
        ):
            self.assertIn(required, self.runner_source)
        for forbidden in (
            "_call_ollama",
            "_run_judgment",
            "urllib.request",
            "requests.post",
            "expected_frames",
            "expected_calls",
        ):
            self.assertNotIn(forbidden, self.runner_source)

    def test_same_frozen_compiler_is_used_for_both_conditions(self):
        self.assertEqual(
            self.runner_source.count("compile_relation_authorized_v57("), 2
        )
        self.assertNotIn("compile_target_relative_v48", self.runner_source)

    def test_analyzer_freezes_all_preregistered_effects(self):
        for required in (
            '"state_correct_count"',
            '"state_commitment_accuracy"',
            '"state_requested_precision"',
            '"state_requested_recall"',
            '"compiler_ordered_exact_count"',
            '"compiler_false_actions"',
            '"event_role_direct_focus_count"',
            '"event_role_slot_correct_count"',
            '"matched_state_fixes"',
            '"matched_state_regressions"',
            '"matched_case_fixes"',
            '"matched_case_regressions"',
        ):
            self.assertIn(required, self.analyzer_source)

    def test_result_did_not_exist_when_harness_was_frozen(self):
        result_path = ROOT / self.lock["result_artifacts"]["raw"]
        if not result_path.exists():
            self.assertFalse(result_path.exists())
            return
        freeze_commit = subprocess.check_output(
            [
                "git",
                "log",
                "--diff-filter=A",
                "--format=%H",
                "-1",
                "--",
                str(LOCK_PATH.relative_to(ROOT)),
            ],
            cwd=ROOT,
            text=True,
        ).strip()
        self.assertTrue(freeze_commit)
        historical_result = subprocess.run(
            [
                "git",
                "cat-file",
                "-e",
                f"{freeze_commit}:{result_path.relative_to(ROOT)}",
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(historical_result.returncode, 0)

    def test_harness_authorizes_no_result_tuning_or_deployment(self):
        for key in (
            "post_replay_metric_changes_authorized",
            "post_replay_threshold_changes_authorized",
            "post_replay_case_exclusion_authorized",
            "runtime_change_authorized",
            "shadow_integration_authorized",
            "physical_vrm_execution_enabled",
            "complete_rightbrain_claim_authorized",
            "broad_human_likeness_claim_authorized",
        ):
            self.assertFalse(self.lock[key], key)


if __name__ == "__main__":
    unittest.main()
