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
    load_model_artifact,
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

    def test_nonstandard_surface_feature_catches_actual_model_pollution(self):
        row = self.rows[0]
        features = extract_candidate_features("今日は无理しないで休め。範�", row["contract_payload"])
        self.assertGreater(features["nonstandard_cjk_density"], 0.0)

    def test_surface_features_include_newly_audited_v10_residue(self):
        row = self.rows[0]
        nonstandard = extract_candidate_features(
            "共同作业の返事を待て。",
            row["contract_payload"],
        )
        chinese = extract_candidate_features(
            "どのゲームか分からなさそう呢。",
            row["contract_payload"],
        )

        self.assertGreater(nonstandard["nonstandard_cjk_density"], 0.0)
        self.assertGreater(chinese["chinese_marker_density"], 0.0)

    def test_semantic_features_prefer_current_leftbrain_meaning(self):
        payload = {
            "context": {"max_chars": 80},
            "user_input": "夜空の影がどうとか、あれ分かる？",
            "leftbrain_plan": {
                "meaning": "元ネタを特定できないので作品名や出典を聞き返す",
                "content_units": ["出典を確認する", "分かったふりをしない"],
                "grounding_terms": ["元ネタ", "作品名", "出典"],
            },
            "required_marker_groups": [],
            "forbidden_markers": [],
        }
        aligned = extract_candidate_features(
            "元ネタまでは分からない。作品名か出典を教えて。",
            payload,
        )
        drifted = extract_candidate_features(
            "今のお腹の感じ、無理しないようにね。",
            payload,
        )
        self.assertGreater(aligned["grounding_term_hit_rate"], drifted["grounding_term_hit_rate"])
        self.assertGreater(
            aligned["semantic_reference_bigram_dice"],
            drifted["semantic_reference_bigram_dice"],
        )

    def test_semantic_drift_candidates_pass_old_surface_gate(self):
        semantic_decoys = [
            (row, candidate)
            for row in self.rows
            for candidate in row["candidates"]
            if candidate.get("source") == "semantic_reference_drift"
        ]
        self.assertGreaterEqual(len(semantic_decoys), len(self.rows) // 3)
        for row, candidate in semantic_decoys[:50]:
            self.assertEqual(candidate["detected_errors"], ["semantic_reference_drift"])
            features = extract_candidate_features(candidate["text"], row["contract_payload"])
            self.assertLessEqual(features["semantic_reference_bigram_dice"], 0.20)

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
        self.assertGreater(self.report["test_semantic_drift_decoys"]["case_count"], 0)
        self.assertEqual(
            self.report["test_semantic_drift_decoys"]["semantic_decoy_rejection_rate"],
            1.0,
        )

    def test_natural_generated_holdout_has_no_contract_overlap_or_invalid_selection(self):
        natural = self.report["natural_generated_holdout"]
        self.assertEqual(natural["contract_overlap_with_selection_dataset"], 0)
        self.assertGreater(natural["invalid_candidate_count"], 0)
        self.assertEqual(natural["strategies"]["learned_selector"]["valid_selection_rate"], 1.0)

    def test_artifact_has_no_label_or_candidate_source_weights(self):
        serialized = model_to_json(self.model)
        for forbidden in ("is_gold", "detected_errors", "candidate_source", "gold_candidate_id"):
            self.assertNotIn(forbidden, serialized)

    def test_model_loader_rejects_feature_schema_drift(self):
        malformed = dict(self.model)
        malformed["feature_names"] = list(malformed["feature_names"][:-1])
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "bad-model.json"
            path.write_text(json.dumps(malformed), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "feature schema"):
                load_model_artifact(path)


if __name__ == "__main__":
    unittest.main()
