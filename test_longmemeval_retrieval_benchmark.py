import json
import tempfile
import unittest
from pathlib import Path

from run_longmemeval_retrieval_benchmark import (
    CONDITIONS,
    all_retrieval_metrics,
    build_report,
    evaluate_item,
    is_abstention,
    load_and_validate_dataset,
    paired_binary_comparison,
    parse_timestamp,
    preregistered_split,
    ranking_payload_sha256,
    recompute_results_from_rankings,
    select_rows,
    session_document,
    validate_ranking_results_against_dataset,
)


def _row(question_id, question_type="single-session-user", abstention=False):
    question_id = f"{question_id}_abs" if abstention else question_id
    return {
        "question_id": question_id,
        "question_type": question_type,
        "question": "What is my favorite drink?",
        "answer": "tea",
        "question_date": "2024/01/02 (Tue) 09:00",
        "haystack_session_ids": ["old", "answer_1", "recent"],
        "haystack_dates": [
            "2024/01/01 (Mon) 08:00",
            "2024/01/01 (Mon) 09:00",
            "2024/01/01 (Mon) 10:00",
        ],
        "haystack_sessions": [
            [{"role": "user", "content": "Weather."}],
            [
                {
                    "role": "user",
                    "content": "My favorite drink is tea.",
                    "has_answer": True,
                },
                {"role": "assistant", "content": "I will remember that."},
            ],
            [{"role": "user", "content": "Something recent."}],
        ],
        "answer_session_ids": ["answer_1"],
    }


def _result(question_id, system_pass, control_pass, recent_pass=False):
    metrics = {}
    for condition, passed in (
        ("uruha_salience_rerank", system_pass),
        ("dense_chroma", control_pass),
        ("recent_session_order", recent_pass),
    ):
        values = {}
        for k in (1, 3, 5, 10, 20):
            values[f"recall_any@{k}"] = float(passed)
            values[f"recall_all@{k}"] = float(passed)
            values[f"ndcg_any@{k}"] = float(passed)
        metrics[condition] = {"ranked_session_ids": [], "metrics": values}
    return {
        "question_id": question_id,
        "question_type": "single-session-user",
        "split": preregistered_split(question_id),
        "abstention": False,
        "history_session_count": 3,
        "answer_session_ids": ["answer_1"],
        "conditions": metrics,
        "uruha_top5_attention_factors": [],
    }


def _bound_result(row, candidate_k=20):
    result = _result(row["question_id"], True, True)
    result.update(
        {
            "question_type": row["question_type"],
            "split": preregistered_split(row["question_id"]),
            "abstention": is_abstention(row),
            "history_session_count": len(row["haystack_session_ids"]),
            "answer_session_ids": list(row["answer_session_ids"]),
        }
    )
    dense_ids = list(row["haystack_session_ids"])[:candidate_k]
    rankings = {
        "recent_session_order": list(reversed(row["haystack_session_ids"]))[
            :candidate_k
        ],
        "dense_chroma": dense_ids,
        "uruha_salience_rerank": list(reversed(dense_ids)),
    }
    for condition, ranked_ids in rankings.items():
        result["conditions"][condition]["ranked_session_ids"] = ranked_ids
    return result


def _large_row(question_id):
    row = _row(question_id)
    for index in range(3, 21):
        row["haystack_session_ids"].append(f"extra_{index}")
        row["haystack_dates"].append(f"2024/01/{index + 1:02d} (Mon) 10:00")
        row["haystack_sessions"].append(
            [{"role": "user", "content": f"Unrelated memory {index}."}]
        )
    return row


class LongMemEvalRetrievalBenchmarkTest(unittest.TestCase):
    class FakeCollection:
        def query(self, **_kwargs):
            return {
                "ids": [["memory-answer", "memory-noise", "memory-recent"]],
                "documents": [[
                    "Time: 2024-01-01 09:00:00\nUser: My favorite drink is tea.",
                    "Time: 2024-01-01 08:00:00\nUser: Weather.",
                    "Time: 2024-01-01 10:00:00\nUser: Something recent.",
                ]],
                "metadatas": [[
                    {"benchmark_session_id": "answer_1", "timestamp": "2024-01-01 09:00:00"},
                    {"benchmark_session_id": "old", "timestamp": "2024-01-01 08:00:00"},
                    {"benchmark_session_id": "recent", "timestamp": "2024-01-01 10:00:00"},
                ]],
                "distances": [[0.1, 0.8, 1.1]],
            }

    def test_session_document_excludes_answer_annotations(self):
        row = _row("q1")
        text = session_document(row["haystack_sessions"][1], row["haystack_dates"][1])

        self.assertIn("User: My favorite drink is tea.", text)
        self.assertIn("Assistant: I will remember that.", text)
        self.assertNotIn("has_answer", text)
        self.assertNotIn("True", text)

    def test_timestamp_conversion_is_locale_independent(self):
        self.assertEqual(
            parse_timestamp("2024/01/02 (Tue) 09:03"),
            "2024-01-02 09:03:00",
        )

    def test_item_runner_connects_dense_salience_and_metrics(self):
        result = evaluate_item(self.FakeCollection(), _row("q1"), candidate_k=3)

        self.assertEqual(result["question_id"], "q1")
        self.assertEqual(
            result["conditions"]["dense_chroma"]["ranked_session_ids"][0],
            "answer_1",
        )
        self.assertEqual(
            result["conditions"]["dense_chroma"]["metrics"]["recall_all@5"],
            1.0,
        )

    def test_item_runner_scores_only_the_shared_candidate_budget(self):
        row = _row("q1")
        row["answer_session_ids"] = ["old"]
        result = evaluate_item(self.FakeCollection(), row, candidate_k=2)

        recent = result["conditions"]["recent_session_order"]
        self.assertEqual(len(recent["ranked_session_ids"]), 2)
        self.assertEqual(recent["metrics"]["recall_any@3"], 0.0)

    def test_official_recall_all_and_any_distinguish_partial_evidence(self):
        metrics = all_retrieval_metrics(["a", "noise", "b"], ["a", "b"])

        self.assertEqual(metrics["recall_any@1"], 1.0)
        self.assertEqual(metrics["recall_all@1"], 0.0)
        self.assertEqual(metrics["recall_all@3"], 1.0)
        self.assertGreater(metrics["ndcg_any@3"], 0.0)
        self.assertLessEqual(metrics["ndcg_any@3"], 1.0)

    def test_ndcg_ideal_denominator_includes_unretrieved_evidence(self):
        metrics = all_retrieval_metrics(["a", "noise"], ["a", "b"])

        self.assertEqual(metrics["recall_any@3"], 1.0)
        self.assertEqual(metrics["recall_all@3"], 0.0)
        self.assertLess(metrics["ndcg_any@3"], 1.0)

    def test_preregistered_split_uses_only_question_id(self):
        self.assertEqual(preregistered_split("same"), preregistered_split("same"))
        self.assertIn(preregistered_split("same"), {"development", "test"})

    def test_stratified_selection_covers_question_types_before_repeating(self):
        data = []
        types = ["single-session-user", "knowledge-update", "temporal-reasoning"]
        for question_type in types:
            for index in range(4):
                data.append(_row(f"{question_type}_{index}", question_type))
        selected = select_rows(data, max_items=3, seed=7)

        self.assertEqual(len(selected), 3)
        self.assertEqual({row["question_type"] for row in selected}, set(types))

    def test_limited_selection_does_not_waste_slots_on_abstention(self):
        data = [
            _row("normal_a", "single-session-user"),
            _row("normal_b", "knowledge-update"),
            _row("abs_a", "single-session-user", abstention=True),
            _row("abs_b", "knowledge-update", abstention=True),
        ]
        selected = select_rows(data, max_items=2, seed=7)

        self.assertFalse(any(is_abstention(row) for row in selected))

    def test_dataset_validation_binds_bytes_sha_rows_and_fields(self):
        rows = [_row("q1"), _row("q2")]
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "dataset.json"
            path.write_text(json.dumps(rows), encoding="utf-8")
            from run_longmemeval_retrieval_benchmark import file_sha256

            loaded, evidence = load_and_validate_dataset(
                path,
                expected_sha=file_sha256(path),
                expected_bytes=path.stat().st_size,
                expected_rows=2,
            )
            self.assertEqual(len(loaded), 2)
            self.assertEqual(evidence["row_count"], 2)

    def test_paired_comparison_counts_direction_not_only_mean(self):
        results = [
            _result("a", True, False),
            _result("b", True, True),
            _result("c", False, True),
            _result("d", True, False),
        ]
        comparison = paired_binary_comparison(
            results,
            "uruha_salience_rerank",
            "dense_chroma",
        )

        self.assertEqual(comparison["system_only_pass"], 2)
        self.assertEqual(comparison["control_only_pass"], 1)
        self.assertEqual(comparison["paired_net_case_gain"], 1)

    def test_metric_recompute_uses_bound_rankings_and_all_gold_sessions(self):
        result = _result("q", True, True)
        result["answer_session_ids"] = ["a", "b"]
        for condition in CONDITIONS:
            result["conditions"][condition]["ranked_session_ids"] = ["a", "noise"]
            result["conditions"][condition]["metrics"] = {"stale": 1.0}

        rebuilt = recompute_results_from_rankings([result])
        metrics = rebuilt[0]["conditions"]["dense_chroma"]["metrics"]
        self.assertNotIn("stale", metrics)
        self.assertEqual(metrics["recall_any@5"], 1.0)
        self.assertEqual(metrics["recall_all@5"], 0.0)
        self.assertLess(metrics["ndcg_any@5"], 1.0)

    def test_ranking_payload_sha_binds_order_and_condition(self):
        official = _row("q")
        result = _bound_result(official)
        original_sha = ranking_payload_sha256([result])

        result["conditions"]["dense_chroma"]["ranked_session_ids"].reverse()

        self.assertNotEqual(ranking_payload_sha256([result]), original_sha)

    def test_ranking_source_gold_must_match_official_dataset(self):
        official = _row("q")
        result = _bound_result(official)
        result["answer_session_ids"] = ["tampered"]
        with self.assertRaisesRegex(ValueError, "gold IDs differ"):
            validate_ranking_results_against_dataset([result], [official])

    def test_ranking_source_cannot_reference_outside_session(self):
        official = _row("q")
        result = _bound_result(official)
        result["conditions"]["dense_chroma"]["ranked_session_ids"][0] = "outside"
        with self.assertRaisesRegex(ValueError, "unknown session"):
            validate_ranking_results_against_dataset([result], [official])

    def test_ranking_source_rejects_excess_session_multiplicity(self):
        official = _row("q")
        result = _bound_result(official)
        dense_ids = result["conditions"]["dense_chroma"]["ranked_session_ids"]
        dense_ids[0] = dense_ids[1]
        with self.assertRaisesRegex(ValueError, "multiplicity exceeds"):
            validate_ranking_results_against_dataset([result], [official])

    def test_salience_must_rerank_the_same_dense_candidate_pool(self):
        official = _large_row("q")
        result = _bound_result(official)
        salience_ids = result["conditions"]["uruha_salience_rerank"][
            "ranked_session_ids"
        ]
        salience_ids[0] = official["haystack_session_ids"][-1]
        with self.assertRaisesRegex(ValueError, "candidate pools differ"):
            validate_ranking_results_against_dataset([result], [official])

    def test_ranking_source_result_count_must_match_manifest(self):
        official = _row("q")
        result = _bound_result(official)
        with self.assertRaisesRegex(ValueError, "result count differs"):
            validate_ranking_results_against_dataset(
                [result],
                [official],
                expected_count=2,
            )

    def test_report_never_authorizes_runtime_from_retrieval_only(self):
        results = [_result("a", True, False), _result("b", True, False)]
        selected = [_row("a"), _row("b")]
        report = build_report(
            {"sha256": "a" * 64, "row_count": 500},
            selected,
            {"collection_count": 6},
            results,
            1.0,
        )

        self.assertEqual(
            report["decision"]["status"],
            "salience_improves_dense_retrieval",
        )
        self.assertFalse(report["decision"]["authorize_memory_algorithm_change"])
        self.assertFalse(report["decision"]["authorize_runtime_promotion"])
        self.assertIn("not final answer correctness", report["research_boundary"])

    def test_abstention_detection_matches_official_id_rule(self):
        self.assertTrue(is_abstention(_row("q", abstention=True)))
        self.assertFalse(is_abstention(_row("q")))


if __name__ == "__main__":
    unittest.main()
