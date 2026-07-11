import json
import tempfile
import unittest
from pathlib import Path

from build_rightbrain_on_policy_blind_package_v29 import (
    FORMAL_ADAPTER,
    _json_sha256,
    build_blind_package,
)
from rightbrain_on_policy_dev_cases_v29 import case_inputs
from serve_rightbrain_on_policy_blind_v29 import RatingStore, load_package


def _candidate_text(case, variant):
    markers = [group[0] for group in case["required_marker_groups"]]
    joined = "、".join(markers)
    if variant == 1:
        return f"{joined}ってことなら、少し考えればいい。"
    return f"{joined}なら、今日は軽く決めよう。"


def _synthetic_report(candidates_per_case=2):
    rows = []
    for case in case_inputs():
        rows.append(
            {
                "id": case["id"],
                "model_accepted_candidates": [
                    {
                        "raw_candidate": _candidate_text(case, variant),
                        "candidate": _candidate_text(case, variant),
                    }
                    for variant in range(1, candidates_per_case + 1)
                ],
                "model_initial_rejected_candidates": [],
            }
        )
    return {
        "adapter_ref": FORMAL_ADAPTER,
        "adapter_model_sha256": "a" * 64,
        "load_model": True,
        "repair_enabled": False,
        "seed": 20260712,
        "authorize_blind_package_build": True,
        "candidate_collection_gates": {"all": True},
        "cases": rows,
    }


class RightBrainOnPolicyBlindPackageV29Test(unittest.TestCase):
    def test_package_uses_same_policy_strict_pass_pairs_and_hidden_repeats(self):
        package, key_rows, report = build_blind_package(
            [("synthetic.json", _synthetic_report())],
            prior_output_texts=set(),
            promotion_output_texts=set(),
        )
        self.assertTrue(report["authorize_human_rating"], msg=report["gates"])
        self.assertFalse(report["authorize_preference_training"])
        self.assertEqual(package["comparison_count"], 12)
        self.assertEqual(len(key_rows), 12)
        self.assertEqual(sum(row["is_consistency_repeat"] for row in key_rows), 2)
        self.assertTrue(report["gates"]["consistency_repeats_are_spaced"])
        self.assertTrue(
            all(
                gap >= report["minimum_consistency_repeat_gap"]
                for gap in report["consistency_repeat_display_gaps"]
            )
        )
        self.assertEqual(
            _json_sha256(
                {key: value for key, value in package.items() if key != "package_sha256"}
            ),
            package["package_sha256"],
        )
        package_text = json.dumps(package, ensure_ascii=False)
        self.assertNotIn("adapter_ref", package_text)
        self.assertNotIn("current_strict_pass", package_text)
        for row in key_rows:
            self.assertTrue(row["left_candidate"]["hard_surface_pass"])
            self.assertTrue(row["right_candidate"]["hard_surface_pass"])
            self.assertNotEqual(
                row["left_candidate"]["normalized_text_sha256"],
                row["right_candidate"]["normalized_text_sha256"],
            )

    def test_package_refuses_to_weaken_gate_when_pairs_are_missing(self):
        with self.assertRaisesRegex(ValueError, "Generate another seed"):
            build_blind_package(
                [("synthetic.json", _synthetic_report(candidates_per_case=1))],
                prior_output_texts=set(),
                promotion_output_texts=set(),
            )


class RatingStoreV29Test(unittest.TestCase):
    def _package(self):
        package = {
            "schema_version": 1,
            "package_id": "test",
            "comparison_count": 2,
            "comparisons": [
                {"comparison_id": "one"},
                {"comparison_id": "two"},
            ],
        }
        package["package_sha256"] = _json_sha256(package)
        return package

    def test_each_vote_is_atomically_saved_and_resume_uses_next_item(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "ratings.json"
            store = RatingStore(path, self._package())
            self.assertEqual(store.next_unrated_id(), "one")
            store.record("one", "left_better", "自然")
            saved = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(saved["rated_count"], 1)
            self.assertFalse(saved["completed"])
            self.assertEqual(saved["ratings"][0]["note"], "自然")
            resumed = RatingStore(path, self._package())
            self.assertEqual(resumed.next_unrated_id(), "two")

    def test_store_refuses_a_different_package_hash(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "ratings.json"
            store = RatingStore(path, self._package())
            store.record("one", "tie")
            changed = self._package()
            changed["package_sha256"] = "different"
            with self.assertRaisesRegex(ValueError, "different blind package"):
                RatingStore(path, changed)

    def test_load_package_rejects_duplicate_ids(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "package.json"
            package = self._package()
            package["comparisons"][1]["comparison_id"] = "one"
            package["package_sha256"] = _json_sha256(
                {key: value for key, value in package.items() if key != "package_sha256"}
            )
            path.write_text(json.dumps(package), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "IDs are invalid"):
                load_package(path)

    def test_load_package_rejects_content_changed_after_hashing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "package.json"
            package = self._package()
            package["comparisons"][0]["extra"] = "changed"
            path.write_text(json.dumps(package), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "SHA does not match"):
                load_package(path)


if __name__ == "__main__":
    unittest.main()
