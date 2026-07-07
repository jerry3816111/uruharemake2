import json
import tempfile
import unittest
from pathlib import Path

from eval_rightbrain_repair_selector_v1 import build_evaluation_report
from project_paths import (
    RIGHTBRAIN_REPAIR_SELECTION_V1_DATASET_PATH,
    RIGHTBRAIN_REPAIR_SELECTOR_V1_NATURAL_HOLDOUT_SOURCE_PATH,
)
from rightbrain_repair_selector import (
    FEATURE_NAMES,
    extract_candidate_features,
    grouped_contract_split,
    model_to_json,
    select_learned_candidate,
    split_fingerprint_overlap,
    train_selector,
)


class RightBrainRepairSelectorTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = json.loads(Path(RIGHTBRAIN_REPAIR_SELECTION_V1_DATASET_PATH).read_text(encoding="utf-8"))
        cls.splits = grouped_contract_split(cls.rows)
        cls.model, cls.history = train_selector(cls.splits["train"], cls.splits["validation"])
        cls.model["split_seed"] = 20260707
        cls.model["dataset_scope"] = "rightbrain_repair_selection_v1"
        natural_report = json.loads(
            Path(RIGHTBRAIN_REPAIR_SELECTOR_V1_NATURAL_HOLDOUT_SOURCE_PATH).read_text(encoding="utf-8")
        )
        cls.report = build_evaluation_report(cls.rows, cls.model, natural_report=natural_report)

    def test_grouped_split_has_no_contract_leakage(self):
        self.assertEqual(split_fingerprint_overlap(self.splits), {
            "train_validation": 0,
            "train_test": 0,
            "validation_test": 0,
        })
        self.assertEqual(sum(len(rows) for rows in self.splits.values()), len(self.rows))
        for rows in self.splits.values():
            self.assertTrue(rows)

    def test_features_only_use_text_and_contract(self):
        row = self.rows[0]
        candidate = row["candidates"][0]
        first = extract_candidate_features(candidate["text"], row["contract_payload"])
        mutated = dict(candidate)
        mutated.update({"is_gold": not candidate["is_gold"], "source": "fake", "detected_errors": ["fake"]})
        second = extract_candidate_features(mutated["text"], row["contract_payload"])
        self.assertEqual(first, second)
        self.assertEqual(tuple(first), FEATURE_NAMES)

    def test_model_round_trip_preserves_selection(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "model.json"
            path.write_text(model_to_json(self.model), encoding="utf-8")
            restored = json.loads(path.read_text(encoding="utf-8"))
        for row in self.splits["test"][:12]:
            before = select_learned_candidate(self.model, row)[0]["candidate_id"]
            after = select_learned_candidate(restored, row)[0]["candidate_id"]
            self.assertEqual(before, after)

    def test_held_out_gate_passes(self):
        self.assertTrue(self.report["gate_passed"], msg=self.report["gate"])
        learned = self.report["test_strategies"]["learned_selector"]
        first = self.report["test_strategies"]["first_candidate"]
        self.assertGreaterEqual(learned["gold_selection_rate"], 0.95)
        self.assertGreaterEqual(learned["gold_selection_rate"] - first["gold_selection_rate"], 0.5)

    def test_natural_generated_holdout_has_no_contract_overlap_or_invalid_selection(self):
        natural = self.report["natural_generated_holdout"]
        self.assertEqual(natural["contract_overlap_with_selection_dataset"], 0)
        self.assertGreater(natural["invalid_candidate_count"], 0)
        self.assertEqual(natural["strategies"]["learned_selector"]["valid_selection_rate"], 1.0)

    def test_artifact_has_no_label_or_candidate_source_weights(self):
        serialized = model_to_json(self.model)
        for forbidden in ("is_gold", "detected_errors", "candidate_source", "gold_candidate_id"):
            self.assertNotIn(forbidden, serialized)


if __name__ == "__main__":
    unittest.main()
