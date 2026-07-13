import datetime
import unittest

from run_longmemeval_salience_development import (
    VARIANTS,
    benchmark_reference_time,
    build_report,
    development_rows,
    evaluate_cache,
    explicit_self_relevance_bonus,
    inverse_distance_similarity,
    normalized_overlap_bonus,
    rank_generative_agents_normalized,
    rank_independent_variant,
    rank_runtime_v2,
    summarize,
)
from run_longmemeval_retrieval_benchmark import preregistered_split


def _question_id_for(split):
    index = 0
    while preregistered_split(f"probe_{index}") != split:
        index += 1
    return f"probe_{index}"


def _candidate(session_id, distance, text, timestamp="2024-01-01 09:00:00", **metadata):
    return {
        "source": "episode",
        "text": text,
        "distance": distance,
        "memory_id": session_id,
        "metadata": {
            "benchmark_session_id": session_id,
            "timestamp": timestamp,
            "decay_flag": False,
            "decay_multiplier": 1.0,
            **metadata,
        },
    }


class LongMemEvalSalienceDevelopmentTest(unittest.TestCase):
    def test_benchmark_reference_time_uses_frozen_baseline_timestamp(self):
        reference = benchmark_reference_time(
            {"generated_at": "2026-07-13T18:45:34+09:00"}
        )

        self.assertEqual(reference, datetime.datetime(2026, 7, 13, 18, 45, 34))

    def test_development_rows_never_selects_test_or_abstention(self):
        development_id = _question_id_for("development")
        test_id = _question_id_for("test")
        rows = [
            {"question_id": development_id},
            {"question_id": test_id},
            {"question_id": f"{development_id}_abs"},
        ]

        selected = development_rows(rows)

        self.assertEqual([row["question_id"] for row in selected], [development_id])

    def test_inverse_distance_is_bounded_and_monotonic_past_one(self):
        self.assertGreater(inverse_distance_similarity(0.5), inverse_distance_similarity(1.5))
        self.assertGreater(inverse_distance_similarity(1.5), 0.0)
        self.assertLessEqual(inverse_distance_similarity(0.0), 1.0)

    def test_normalized_overlap_does_not_saturate_on_one_word_in_long_memory(self):
        text = "User: tea " + " ".join(f"unrelated{index}" for index in range(60))

        score = normalized_overlap_bonus(["user", "tea", "favorite"], text)

        self.assertGreater(score, 0.0)
        self.assertLess(score, 0.45)

    def test_explicit_self_relevance_ignores_generic_role_text(self):
        generic = _candidate("generic", 0.2, "User: remember my name")
        explicit = _candidate("explicit", 0.2, "ordinary memory", self_relevance=True)

        self.assertEqual(explicit_self_relevance_bonus(generic), 0.0)
        self.assertEqual(explicit_self_relevance_bonus(explicit), 0.16)

    def test_inverse_distance_variant_preserves_relevance_when_other_factors_match(self):
        candidates = [
            _candidate("near", 0.4, "same neutral memory"),
            _candidate("far", 1.4, "same neutral memory plus detail"),
        ]
        now = datetime.datetime(2024, 1, 2, 9, 0, 0)

        ranked = rank_independent_variant(
            candidates,
            "neutral question",
            now,
            now,
            "inverse_distance_only",
        )

        self.assertEqual(ranked[0]["memory_id"], "near")

    def test_generative_agents_weights_keep_strong_relevance_ahead_of_recency(self):
        candidates = [
            _candidate("near_old", 0.1, "relevant memory", "2024-01-01 09:00:00"),
            _candidate("far_new", 2.0, "unrelated memory", "2024-01-02 08:59:00"),
        ]
        now = datetime.datetime(2024, 1, 2, 9, 0, 0)

        ranked = rank_generative_agents_normalized(candidates, "relevant", now)

        self.assertEqual(ranked[0]["memory_id"], "near_old")

    def test_runtime_v2_exactly_matches_selected_experimental_formula(self):
        candidates = [
            _candidate(
                f"s{index}",
                0.2 + index * 0.08,
                f"User: memory topic{index % 4} detail{index}",
            )
            for index in range(20)
        ]
        now = datetime.datetime(2024, 1, 2, 9, 0, 0)

        experimental = rank_independent_variant(
            candidates,
            "topic2 memory",
            now,
            now,
            "explicit_self_inverse_overlap",
        )
        runtime = rank_runtime_v2(candidates, "topic2 memory", now)

        self.assertEqual(
            [item["memory_id"] for item in runtime],
            [item["memory_id"] for item in experimental],
        )

    def test_evaluate_cache_emits_only_declared_development_variants(self):
        candidates = [
            _candidate(f"s{index}", 0.1 + index * 0.05, f"memory {index}")
            for index in range(20)
        ]
        cache_rows = [
            {
                "question_id": _question_id_for("development"),
                "question_type": "single-session-user",
                "question": "memory 0",
                "question_date": "2024/01/02 (Tue) 09:00",
                "answer_session_ids": ["s0"],
                "candidates": candidates,
            }
        ]

        results = evaluate_cache(
            cache_rows,
            wall_now=datetime.datetime(2024, 1, 2, 9, 0, 0),
        )

        self.assertEqual(results[0]["split"], "development")
        self.assertEqual(set(results[0]["conditions"]), set(VARIANTS))

    def test_report_cannot_authorize_runtime_or_test_from_development(self):
        candidates = [
            _candidate(f"s{index}", 0.1 + index * 0.05, f"memory {index}")
            for index in range(20)
        ]
        rows = [
            {
                "question_id": _question_id_for("development"),
                "question_type": "single-session-user",
                "question": "memory 0",
                "question_date": "2024/01/02 (Tue) 09:00",
                "answer_session_ids": ["s0"],
                "candidates": candidates,
            }
        ]
        results = evaluate_cache(
            rows,
            wall_now=datetime.datetime(2024, 1, 2, 9, 0, 0),
        )
        summaries, comparisons = summarize(results)
        cache = {
            "dataset_sha256": "a" * 64,
            "baseline_ranking_sha256": "b" * 64,
            "schema": "longmemeval_development_candidates_v1",
            "candidate_k": 20,
            "development_question_ids_sha256": "c" * 64,
            "baseline_report_sha256": "d" * 64,
            "indexed_document_count": 20,
            "build_duration_seconds": 1.0,
        }

        from unittest.mock import patch

        with patch(
            "run_longmemeval_salience_development.file_sha256",
            return_value="e" * 64,
        ):
            report = build_report(cache, results, summaries, comparisons)

        self.assertEqual(report["data_boundary"]["test_question_count_evaluated"], 0)
        self.assertEqual(report["runtime_evidence"]["module_sha256"], "e" * 64)
        self.assertFalse(report["decision"]["authorize_test_evaluation"])
        self.assertFalse(report["decision"]["authorize_runtime_change"])


if __name__ == "__main__":
    unittest.main()
