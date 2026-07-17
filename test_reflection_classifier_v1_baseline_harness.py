import copy
import unittest
from pathlib import Path
from unittest.mock import patch

import run_reflection_classifier_v1_baseline as baseline


ROOT = Path(__file__).resolve().parent
CONFIG = baseline.load_json(baseline.CONFIG_PATH)
DATASET = baseline.load_json(baseline.DATASET_PATH)
LOCK = baseline.load_json(baseline.LOCK_PATH)


def clean_main_git_value(*args):
    values = {
        ("branch", "--show-current"): "main",
        ("rev-parse", "HEAD"): "frozen-main",
        ("rev-parse", "origin/main"): "frozen-main",
        ("status", "--porcelain", "--untracked-files=no"): "",
    }
    return values[args]


class ReflectionClassifierV1BaselineHarnessTest(unittest.TestCase):
    def test_lock_covers_every_frozen_artifact(self):
        for relative, expected in LOCK["frozen_artifacts"].items():
            self.assertEqual(baseline.sha256(ROOT / relative), expected, relative)

    @patch.object(baseline, "git_value", side_effect=clean_main_git_value)
    def test_clean_synced_main_passes_verification(self, _mock_git):
        baseline.verify(CONFIG, DATASET, LOCK)

    @patch.object(baseline, "git_value", return_value="feature-branch")
    def test_non_main_branch_is_rejected(self, _mock_git):
        with self.assertRaisesRegex(ValueError, "must run from main"):
            baseline.verify(CONFIG, DATASET, LOCK)

    @patch.object(baseline, "git_value")
    def test_remote_drift_is_rejected(self, mock_git):
        mock_git.side_effect = ["main", "local-head", "remote-head"]
        with self.assertRaisesRegex(ValueError, "locked remote ref"):
            baseline.verify(CONFIG, DATASET, LOCK)

    @patch.object(baseline, "git_value", side_effect=clean_main_git_value)
    def test_artifact_drift_is_rejected(self, _mock_git):
        drifted = copy.deepcopy(LOCK)
        path = next(iter(drifted["frozen_artifacts"]))
        drifted["frozen_artifacts"][path] = "0" * 64
        with self.assertRaisesRegex(ValueError, "frozen artifact drift"):
            baseline.verify(CONFIG, DATASET, drifted)


if __name__ == "__main__":
    unittest.main()
