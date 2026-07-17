import copy
import unittest
from pathlib import Path
from unittest.mock import patch

import run_reflection_classifier_v1_candidate as candidate


ROOT = Path(__file__).resolve().parent
CONFIG = candidate.load_json(candidate.CONFIG_PATH)
DATASET = candidate.load_json(candidate.DATASET_PATH)
BASELINE = candidate.load_json(candidate.BASELINE_PATH)
LOCK = candidate.load_json(candidate.LOCK_PATH)


def clean_main_git_value(*args):
    values = {
        ("branch", "--show-current"): "main",
        ("rev-parse", "HEAD"): "frozen-main",
        ("rev-parse", "origin/main"): "frozen-main",
        ("status", "--porcelain", "--untracked-files=no"): "",
    }
    return values[args]


class ReflectionClassifierV1CandidateHarnessTest(unittest.TestCase):
    def test_lock_covers_every_frozen_artifact(self):
        for relative, expected in LOCK["frozen_artifacts"].items():
            self.assertEqual(candidate.sha256(ROOT / relative), expected, relative)

    @patch.object(candidate, "git_value", side_effect=clean_main_git_value)
    def test_clean_synced_main_passes_verification(self, _mock_git):
        candidate.verify(CONFIG, DATASET, BASELINE, LOCK)

    @patch.object(candidate, "git_value", return_value="feature-branch")
    def test_non_main_branch_is_rejected(self, _mock_git):
        with self.assertRaisesRegex(ValueError, "must run from main"):
            candidate.verify(CONFIG, DATASET, BASELINE, LOCK)

    @patch.object(candidate, "git_value")
    def test_remote_drift_is_rejected(self, mock_git):
        mock_git.side_effect = ["main", "local-head", "remote-head"]
        with self.assertRaisesRegex(ValueError, "locked remote ref"):
            candidate.verify(CONFIG, DATASET, BASELINE, LOCK)

    @patch.object(candidate, "git_value", side_effect=clean_main_git_value)
    def test_artifact_drift_is_rejected(self, _mock_git):
        drifted = copy.deepcopy(LOCK)
        path = next(iter(drifted["frozen_artifacts"]))
        drifted["frozen_artifacts"][path] = "0" * 64
        with self.assertRaisesRegex(ValueError, "frozen artifact drift"):
            candidate.verify(CONFIG, DATASET, BASELINE, drifted)

    def test_runtime_reflection_remains_unauthorized(self):
        self.assertFalse(LOCK["runtime_memory_write_authorized"])
        self.assertFalse(LOCK["independent_holdout_authorized"])


if __name__ == "__main__":
    unittest.main()
