import json
import tempfile
import unittest
from pathlib import Path

import planner_supervision_session_review_v78 as v78
import planner_supervision_v76 as v76
from test_planner_supervision_v76_collection import log_record


ROOT = Path(__file__).resolve().parent
REPORT_PATH = ROOT / "reports/planner_supervision_v78_session_review_readiness.json"


def fixture_candidates():
    return v76.build_candidates(
        [
            log_record("session-a", 1, user_text="今日は何を食べようか。"),
            log_record("session-a", 2, user_text="じゃあ温かいものにしよう。"),
            log_record("session-b", 1, user_text="今日は普通に雑談しよう。"),
        ],
        protected_inputs=set(),
    )["candidates"]


class PlannerSupervisionV78SessionReviewTests(unittest.TestCase):
    def test_builder_groups_candidates_into_session_decisions(self):
        units = v78.build_session_review_units(fixture_candidates())
        self.assertEqual(len(units), 2)
        self.assertEqual(sum(unit["session_summary"]["candidate_count"] for unit in units), 3)
        self.assertEqual(units[0]["source_session_id"], "session-a")
        self.assertEqual(units[0]["session_summary"]["candidate_count"], 2)
        self.assertEqual(units[1]["session_summary"]["candidate_count"], 1)

    def test_certified_session_can_continue_to_plan_review_but_quarantine_cannot(self):
        candidates = fixture_candidates()
        units = v78.build_session_review_units(candidates)
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            candidate_path = base / "candidates.jsonl"
            queue_path = base / "session_queue.jsonl"
            manifest_path = base / "manifest.jsonl"
            review_path = base / "plan_reviews.jsonl"
            strict_path = base / "strict.jsonl"
            v76.write_jsonl(candidate_path, candidates)
            v76.write_jsonl(queue_path, units)

            certified = v78.review_session(
                units[0]["id"],
                "certify_nonbenchmark",
                "human-reviewer",
                consent_to_training=True,
                candidate_path=candidate_path,
                queue_path=queue_path,
                manifest_path=manifest_path,
                reviewed_at="2026-07-19T12:00:00+09:00",
            )
            quarantined = v78.review_session(
                units[1]["id"],
                "quarantine",
                "human-reviewer",
                candidate_path=candidate_path,
                queue_path=queue_path,
                manifest_path=manifest_path,
                reviewed_at="2026-07-19T12:01:00+09:00",
            )
            self.assertEqual(certified["benchmark_origin"], "none")
            self.assertEqual(quarantined["benchmark_origin"], "benchmark_or_uncertain")

            first = next(row for row in candidates if row["source_session_id"] == "session-a")
            accepted = v76.review_candidate(
                first["id"],
                "accept",
                "human-reviewer",
                first["scenario_family"],
                candidate_path=candidate_path,
                manifest_path=manifest_path,
                review_path=review_path,
                strict_annotation_path=strict_path,
                protected_inputs=set(),
            )
            self.assertIsNotNone(accepted["accepted_row"])

            second = next(row for row in candidates if row["source_session_id"] == "session-b")
            with self.assertRaisesRegex(ValueError, "certified non-benchmark"):
                v76.review_candidate(
                    second["id"],
                    "accept",
                    "human-reviewer",
                    second["scenario_family"],
                    candidate_path=candidate_path,
                    manifest_path=manifest_path,
                    review_path=review_path,
                    strict_annotation_path=strict_path,
                    protected_inputs=set(),
                )

    def test_duplicate_review_and_missing_consent_are_rejected(self):
        candidates = fixture_candidates()
        units = v78.build_session_review_units(candidates)
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            candidate_path = base / "candidates.jsonl"
            queue_path = base / "queue.jsonl"
            manifest_path = base / "manifest.jsonl"
            v76.write_jsonl(candidate_path, candidates)
            v76.write_jsonl(queue_path, units)
            with self.assertRaisesRegex(ValueError, "explicit local training consent"):
                v78.review_session(
                    units[0]["id"],
                    "certify_nonbenchmark",
                    "human-reviewer",
                    candidate_path=candidate_path,
                    queue_path=queue_path,
                    manifest_path=manifest_path,
                )
            v78.review_session(
                units[0]["id"],
                "quarantine",
                "human-reviewer",
                candidate_path=candidate_path,
                queue_path=queue_path,
                manifest_path=manifest_path,
            )
            with self.assertRaisesRegex(ValueError, "already reviewed"):
                v78.review_session(
                    units[0]["id"],
                    "quarantine",
                    "human-reviewer",
                    candidate_path=candidate_path,
                    queue_path=queue_path,
                    manifest_path=manifest_path,
                )

    def test_tampered_summary_is_rejected_against_current_candidate_queue(self):
        candidates = fixture_candidates()
        units = v78.build_session_review_units(candidates)
        units[0]["session_summary"]["candidate_count"] = 99
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            candidate_path = base / "candidates.jsonl"
            queue_path = base / "queue.jsonl"
            v76.write_jsonl(candidate_path, candidates)
            v76.write_jsonl(queue_path, units)
            with self.assertRaisesRegex(ValueError, "summary hash mismatch"):
                v78.review_session(
                    units[0]["id"],
                    "quarantine",
                    "human-reviewer",
                    candidate_path=candidate_path,
                    queue_path=queue_path,
                    manifest_path=base / "manifest.jsonl",
                )

    def test_tracked_report_contains_only_aggregate_readiness(self):
        report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
        observed = report["observed"]
        self.assertTrue(report["construction_gates"]["passed"])
        self.assertEqual(observed["pending_candidate_count"], 92)
        self.assertEqual(observed["session_review_unit_count"], 6)
        self.assertEqual(observed["repeated_provenance_decisions_removed"], 86)
        self.assertEqual(observed["initial_training_rows_created"], 0)
        serialized = json.dumps(report, ensure_ascii=False)
        self.assertNotIn("202605", serialized)
        self.assertNotIn("user_utterance", serialized)

    def test_runtime_does_not_contain_v78_experiment_code(self):
        for path in (ROOT / "uruha_brain_mac.py", ROOT / "uruha_web_ui.py"):
            self.assertNotIn("session_review_v78", path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
