import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from analyze_rightbrain_on_policy_blind_v29 import _read_jsonl
from build_rightbrain_human_on_policy_preference_v30 import (
    _canonical_sha256,
    _file_sha256,
    bind_source_file_hashes,
    build_dataset,
    load_authorized_probe_rows,
    write_outputs,
)
from project_paths import (
    RIGHTBRAIN_ON_POLICY_V29_BLIND_KEY_PATH,
    RIGHTBRAIN_ON_POLICY_V29_BLIND_PACKAGE_PATH,
)
from test_analyze_rightbrain_on_policy_blind_v29 import _complete_ratings
from train_uruha_rightbrain_dpo_v18 import load_preference_rows


class RightBrainHumanOnPolicyPreferenceV30Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.package = json.loads(
            Path(RIGHTBRAIN_ON_POLICY_V29_BLIND_PACKAGE_PATH).read_text(
                encoding="utf-8"
            )
        )
        cls.key_rows = _read_jsonl(RIGHTBRAIN_ON_POLICY_V29_BLIND_KEY_PATH)
        cls.base_ids = [
            row["comparison_id"]
            for row in cls.key_rows
            if not row["is_consistency_repeat"]
        ]

    def _build(self, ratings, holdout_outputs=None):
        return build_dataset(
            self.package,
            self.key_rows,
            ratings,
            promotion_holdout_inputs=set(),
            promotion_holdout_outputs=set(holdout_outputs or []),
        )

    def test_authorized_human_choices_build_trainer_compatible_pairs(self):
        ratings = _complete_ratings(self.package, self.key_rows)
        rows, report = self._build(ratings)

        self.assertEqual(len(rows), 9)
        self.assertTrue(report["authorize_preference_probe"])
        self.assertFalse(report["authorize_training"])
        self.assertFalse(report["authorize_runtime_promotion"])
        self.assertEqual(len({row["source_family"] for row in rows}), 9)
        for row in rows:
            with self.subTest(row=row["id"]):
                self.assertTrue(row["prompt_messages"])
                self.assertNotEqual(row["chosen"], row["rejected"])
                self.assertEqual(row["messages"][-1]["content"], row["chosen"])
                self.assertTrue(row["pair_diagnostics"]["chosen_hard_surface_pass"])
                self.assertTrue(row["pair_diagnostics"]["rejected_hard_surface_pass"])

        with tempfile.TemporaryDirectory() as tmpdir:
            dataset_path = Path(tmpdir) / "dataset.json"
            report_path = Path(tmpdir) / "report.json"
            ratings_path = Path(tmpdir) / "ratings.json"
            ratings_path.write_text(
                json.dumps(ratings, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            bind_source_file_hashes(
                report,
                RIGHTBRAIN_ON_POLICY_V29_BLIND_PACKAGE_PATH,
                RIGHTBRAIN_ON_POLICY_V29_BLIND_KEY_PATH,
                ratings_path,
            )
            write_outputs(
                rows,
                report,
                dataset_path,
                report_path,
                Path(tmpdir) / "report.md",
            )
            with self.assertRaisesRegex(ValueError, "authorized evidence"):
                load_preference_rows(dataset_path)
            loaded = load_authorized_probe_rows(
                dataset_path,
                report_path,
                ratings_path=ratings_path,
            )
            self.assertEqual(len(loaded), 9)

    def test_tie_and_both_bad_are_excluded_without_blocking_other_pairs(self):
        ratings = _complete_ratings(
            self.package,
            self.key_rows,
            {
                self.base_ids[0]: "tie",
                self.base_ids[1]: "both_bad",
            },
        )
        rows, report = self._build(ratings)

        self.assertEqual(len(rows), 7)
        self.assertTrue(report["authorize_preference_probe"])
        comparison_ids = {
            row["human_preference_evidence"]["comparison_id"] for row in rows
        }
        self.assertNotIn(self.base_ids[0], comparison_ids)
        self.assertNotIn(self.base_ids[1], comparison_ids)

    def test_partial_ratings_never_authorize_or_write_dataset(self):
        ratings = _complete_ratings(self.package, self.key_rows)
        ratings["ratings"] = ratings["ratings"][:3]
        ratings["rated_count"] = 3
        ratings["completed"] = False
        rows, report = self._build(ratings)
        self.assertFalse(report["authorize_preference_probe"])

        with tempfile.TemporaryDirectory() as tmpdir:
            dataset = Path(tmpdir) / "dataset.json"
            dataset.write_text("stale", encoding="utf-8")
            write_outputs(
                rows,
                report,
                dataset,
                Path(tmpdir) / "report.json",
                Path(tmpdir) / "report.md",
            )
            self.assertFalse(dataset.exists())

    def test_inconsistent_repeat_never_authorizes_dataset(self):
        ratings = _complete_ratings(self.package, self.key_rows)
        repeat_ids = {
            row["comparison_id"]
            for row in self.key_rows
            if row["is_consistency_repeat"]
        }
        for row in ratings["ratings"]:
            if row["comparison_id"] in repeat_ids:
                row["choice"] = "left_better"
        _, report = self._build(ratings)

        self.assertFalse(report["authorize_preference_probe"])
        self.assertFalse(
            report["gates"]["human_analysis_authorized_dataset_build"]
        )

    def test_tampered_ratings_hash_never_authorizes_dataset(self):
        ratings = _complete_ratings(self.package, self.key_rows)
        ratings["package_sha256"] = "wrong"
        _, report = self._build(ratings)

        self.assertFalse(report["authorize_preference_probe"])
        self.assertFalse(
            report["gates"]["human_analysis_authorized_dataset_build"]
        )

    def test_promotion_holdout_text_overlap_blocks_probe(self):
        ratings = _complete_ratings(self.package, self.key_rows)
        rows, _ = self._build(ratings)
        _, report = self._build(ratings, holdout_outputs={rows[0]["chosen"]})

        self.assertFalse(report["authorize_preference_probe"])
        self.assertEqual(report["promotion_holdout_overlap"]["chosen_count"], 1)

    def test_key_tampering_blocks_materialization(self):
        ratings = _complete_ratings(self.package, self.key_rows)
        key_rows = deepcopy(self.key_rows)
        key_rows[0]["left_candidate"]["text"] = "改ざん"
        rows, report = build_dataset(
            self.package,
            key_rows,
            ratings,
            promotion_holdout_inputs=set(),
            promotion_holdout_outputs=set(),
        )

        self.assertFalse(report["authorize_preference_probe"])
        self.assertFalse(
            report["gates"]["human_analysis_authorized_dataset_build"]
        )

    def test_authorized_loader_rejects_dataset_changed_after_report(self):
        ratings = _complete_ratings(self.package, self.key_rows)
        rows, report = self._build(ratings)
        with tempfile.TemporaryDirectory() as tmpdir:
            dataset_path = Path(tmpdir) / "dataset.json"
            report_path = Path(tmpdir) / "report.json"
            ratings_path = Path(tmpdir) / "ratings.json"
            ratings_path.write_text(
                json.dumps(ratings, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            bind_source_file_hashes(
                report,
                RIGHTBRAIN_ON_POLICY_V29_BLIND_PACKAGE_PATH,
                RIGHTBRAIN_ON_POLICY_V29_BLIND_KEY_PATH,
                ratings_path,
            )
            write_outputs(
                rows,
                report,
                dataset_path,
                report_path,
                Path(tmpdir) / "report.md",
            )
            payload = json.loads(dataset_path.read_text(encoding="utf-8"))
            payload[0]["chosen"] += "改"
            dataset_path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "changed after"):
                load_authorized_probe_rows(
                    dataset_path,
                    report_path,
                    ratings_path=ratings_path,
                )

    def test_authorized_loader_rejects_ratings_changed_after_report(self):
        ratings = _complete_ratings(self.package, self.key_rows)
        rows, report = self._build(ratings)
        with tempfile.TemporaryDirectory() as tmpdir:
            dataset_path = Path(tmpdir) / "dataset.json"
            report_path = Path(tmpdir) / "report.json"
            ratings_path = Path(tmpdir) / "ratings.json"
            ratings_path.write_text(
                json.dumps(ratings, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            bind_source_file_hashes(
                report,
                RIGHTBRAIN_ON_POLICY_V29_BLIND_PACKAGE_PATH,
                RIGHTBRAIN_ON_POLICY_V29_BLIND_KEY_PATH,
                ratings_path,
            )
            write_outputs(
                rows,
                report,
                dataset_path,
                report_path,
                Path(tmpdir) / "report.md",
            )
            ratings["ratings"][0]["choice"] = (
                "left_better"
                if ratings["ratings"][0]["choice"] != "left_better"
                else "right_better"
            )
            ratings_path.write_text(
                json.dumps(ratings, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "source evidence changed"):
                load_authorized_probe_rows(
                    dataset_path,
                    report_path,
                    ratings_path=ratings_path,
                )

    def test_authorized_loader_rebuilds_pairs_instead_of_trusting_rewritten_report(self):
        ratings = _complete_ratings(self.package, self.key_rows)
        rows, report = self._build(ratings)
        with tempfile.TemporaryDirectory() as tmpdir:
            dataset_path = Path(tmpdir) / "dataset.json"
            report_path = Path(tmpdir) / "report.json"
            ratings_path = Path(tmpdir) / "ratings.json"
            ratings_path.write_text(
                json.dumps(ratings, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            bind_source_file_hashes(
                report,
                RIGHTBRAIN_ON_POLICY_V29_BLIND_PACKAGE_PATH,
                RIGHTBRAIN_ON_POLICY_V29_BLIND_KEY_PATH,
                ratings_path,
            )
            write_outputs(
                rows,
                report,
                dataset_path,
                report_path,
                Path(tmpdir) / "report.md",
            )
            payload = json.loads(dataset_path.read_text(encoding="utf-8"))
            payload[0]["chosen"] += "改"
            dataset_path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            rewritten_report = json.loads(report_path.read_text(encoding="utf-8"))
            rewritten_report["dataset_file_sha256"] = _file_sha256(dataset_path)
            rewritten_report["dataset_canonical_sha256"] = _canonical_sha256(payload)
            report_path.write_text(
                json.dumps(rewritten_report, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "rebuilt human preference pairs"):
                load_authorized_probe_rows(
                    dataset_path,
                    report_path,
                    ratings_path=ratings_path,
                )


if __name__ == "__main__":
    unittest.main()
