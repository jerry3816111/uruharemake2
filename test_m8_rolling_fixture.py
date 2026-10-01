from __future__ import annotations

import json
from pathlib import Path
import unittest

from build_m8_rolling_semantic_fixture import build_fixture


ROOT = Path(__file__).resolve().parent


class M8RollingFixtureTests(unittest.TestCase):
    def test_fixture_has_four_strict_cutoffs_and_unique_unseen_texts(self):
        fixture = build_fixture()
        self.assertEqual(24, len(fixture["events"]))
        self.assertEqual(4, len(fixture["rolling_cutoffs"]))
        self.assertEqual(24, len({row["observable_text"] for row in fixture["events"]}))
        old = json.loads((ROOT / "datasets/m5_state_transition_synthetic_fixture_v1.json").read_text(encoding="utf-8"))
        old_texts = set()
        for scenario in old["scenarios"]:
            old_texts.update(scenario["train_texts"])
            old_texts.add(scenario["dev_text"])
            old_texts.add(scenario["holdout_text"])
        self.assertFalse(old_texts & {row["observable_text"] for row in fixture["events"]})

    def test_history_grows_only_after_prior_outcomes_are_available(self):
        fixture = build_fixture()
        events = fixture["events"]
        counts = []
        for cutoff in fixture["rolling_cutoffs"]:
            prediction_time = cutoff["prediction_time"]
            history = [row for row in events if row["available_at"] < prediction_time]
            tests = [row for row in events if row["event_id"] in cutoff["test_event_ids"]]
            counts.append(len(history))
            self.assertTrue(all(row["event_time"] == prediction_time for row in tests))
            self.assertTrue(all(row["actual_observed_at"] > prediction_time for row in tests))
        self.assertEqual([8, 12, 16, 20], counts)

    def test_eight_history_volume_conditions_and_six_labels_are_frozen(self):
        fixture = build_fixture()
        self.assertEqual(8, len(fixture["history_volume_conditions"]))
        self.assertEqual(set(fixture["taxonomy"]["labels"]), {row["actual_observed_behavior"] for row in fixture["events"]})
        self.assertFalse(fixture["formal_target_claim"])


if __name__ == "__main__":
    unittest.main()
