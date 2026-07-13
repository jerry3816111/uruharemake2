import datetime
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from run_longmemeval_retrieval_benchmark import (
    DATASET_SHA256,
    all_retrieval_metrics,
    canonical_sha256,
    file_sha256,
    preregistered_split,
)
from run_longmemeval_salience_heldout import (
    CACHE_SCHEMA,
    build_report,
    ensure_first_observation,
    evaluate_heldout,
    heldout_rows,
    summarize,
    validate_candidate_cache,
    validate_development_gate,
)


def _question_id_for(split):
    index = 0
    while preregistered_split(f"heldout_probe_{index}") != split:
        index += 1
    return f"heldout_probe_{index}"


def _candidate(session_id, distance=0.2):
    return {
        "source": "episode",
        "text": f"User: memory {session_id}",
        "distance": distance,
        "memory_id": session_id,
        "collection_name": "episode",
        "metadata": {
            "benchmark_session_id": session_id,
            "timestamp": "2024-01-01 09:00:00",
            "decay_flag": False,
            "decay_multiplier": 1.0,
        },
    }


def _development_report(dataset_sha, ranking_sha, runtime_sha):
    return {
        "data_boundary": {
            "question_count": 95,
            "test_question_count_evaluated": 0,
            "dataset_sha256": dataset_sha,
            "baseline_ranking_sha256": ranking_sha,
        },
        "selected_experiment": "explicit_self_inverse_overlap",
        "frozen_runtime_variant": "runtime_v2",
        "runtime_matches_selected_experiment": True,
        "runtime_evidence": {
            "module_sha256": runtime_sha,
            "scoring_profile": "v2",
            "benchmark_reference_time": "2026-07-13T18:45:34",
        },
        "decision": {
            "authorize_test_evaluation": True,
            "authorize_runtime_change": False,
        },
    }


class LongMemEvalSalienceHeldoutTest(unittest.TestCase):
    def test_heldout_rows_excludes_development_and_abstention(self):
        test_id = _question_id_for("test")
        development_id = _question_id_for("development")
        rows = [
            {"question_id": test_id},
            {"question_id": development_id},
            {"question_id": f"{test_id}_abs"},
        ]

        selected = heldout_rows(rows)

        self.assertEqual([row["question_id"] for row in selected], [test_id])

    def test_development_gate_binds_runtime_and_reference_time(self):
        runtime_sha = "a" * 64
        ranking_sha = "b" * 64
        baseline = {
            "generated_at": "2026-07-13T18:45:34+09:00",
            "ranking_evidence": {"sha256": ranking_sha},
        }
        development = _development_report(DATASET_SHA256, ranking_sha, runtime_sha)

        with patch(
            "run_longmemeval_salience_heldout.file_sha256",
            return_value=runtime_sha,
        ):
            reference = validate_development_gate(
                development,
                {"sha256": DATASET_SHA256},
                baseline,
            )

        self.assertEqual(reference, datetime.datetime(2026, 7, 13, 18, 45, 34))

    def test_development_gate_rejects_unapproved_test(self):
        runtime_sha = "a" * 64
        ranking_sha = "b" * 64
        baseline = {
            "generated_at": "2026-07-13T18:45:34+09:00",
            "ranking_evidence": {"sha256": ranking_sha},
        }
        development = _development_report(DATASET_SHA256, ranking_sha, runtime_sha)
        development["decision"]["authorize_test_evaluation"] = False

        with patch(
            "run_longmemeval_salience_heldout.file_sha256",
            return_value=runtime_sha,
        ):
            with self.assertRaisesRegex(ValueError, "did not authorize"):
                validate_development_gate(
                    development,
                    {"sha256": DATASET_SHA256},
                    baseline,
                )

    def test_candidate_cache_rejects_gold_answer_fields(self):
        question_id = _question_id_for("test")
        session_ids = [f"s{index}" for index in range(20)]
        official = {
            "question_id": question_id,
            "haystack_session_ids": session_ids,
        }
        baseline = {
            "ranking_evidence": {"sha256": "b" * 64},
            "results": [
                {
                    "question_id": question_id,
                    "abstention": False,
                    "conditions": {
                        "dense_chroma": {"ranked_session_ids": session_ids}
                    },
                }
            ],
        }
        cache_row = {
            "question_id": question_id,
            "question_type": "single-session-user",
            "question": "memory",
            "question_date": "2024/01/02 (Tue) 09:00",
            "split": "test",
            "candidates": [_candidate(session_id) for session_id in session_ids],
            "answer_session_ids": ["s0"],
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            baseline_path = Path(temp_dir) / "baseline.json"
            baseline_path.write_text(json.dumps(baseline), encoding="utf-8")
            cache = {
                "schema": CACHE_SCHEMA,
                "dataset_sha256": DATASET_SHA256,
                "split_salt": "uruha-longmemeval-retrieval-v1",
                "candidate_k": 20,
                "contains_gold_answers": False,
                "question_ids_sha256": canonical_sha256([question_id]),
                "baseline_ranking_sha256": "b" * 64,
                "baseline_report_sha256": file_sha256(baseline_path),
                "rows": [cache_row],
            }

            with self.assertRaisesRegex(ValueError, "leaks official gold"):
                validate_candidate_cache(cache, [official], baseline, baseline_path)

    def test_evaluate_heldout_reads_gold_only_at_scoring_time(self):
        question_id = _question_id_for("test")
        candidates = [_candidate(f"s{index}", 0.1 + index) for index in range(20)]
        cache_rows = [
            {
                "question_id": question_id,
                "question_type": "single-session-user",
                "question": "memory s0",
                "question_date": "2024/01/02 (Tue) 09:00",
                "split": "test",
                "candidates": candidates,
            }
        ]
        data = [
            {
                "question_id": question_id,
                "answer_session_ids": ["s0"],
            }
        ]
        baseline = {
            "results": [
                {
                    "question_id": question_id,
                    "conditions": {
                        "uruha_salience_rerank": {
                            "ranked_session_ids": [f"s{index}" for index in range(20)]
                        }
                    },
                }
            ]
        }

        with patch("run_longmemeval_salience_heldout.EXPECTED_HELDOUT_COUNT", 1):
            results = evaluate_heldout(
                cache_rows,
                data,
                baseline,
                datetime.datetime(2026, 7, 13, 18, 45, 34),
            )

        self.assertEqual(results[0]["answer_session_ids"], ["s0"])
        self.assertTrue(results[0]["candidate_pool_preserved"])

    def test_preregistered_gates_authorize_only_strong_paired_gain(self):
        results = []
        for index in range(25):
            gold = f"gold_{index}"
            distractors = [f"d{index}_{rank}" for rank in range(19)]
            runtime_ids = [gold, *distractors]
            dense_ids = (
                runtime_ids
                if index < 18
                else [*distractors[:9], gold, *distractors[9:]]
            )
            legacy_ids = (
                runtime_ids
                if index < 12
                else [*distractors[:9], gold, *distractors[9:]]
            )
            rankings = {
                "dense_chroma": dense_ids,
                "legacy_wall_clock": legacy_ids,
                "runtime_v2": runtime_ids,
            }
            results.append(
                {
                    "question_id": f"q{index}",
                    "question_type": "single-session-user",
                    "split": "test",
                    "abstention": False,
                    "answer_session_ids": [gold],
                    "candidate_pool_preserved": True,
                    "conditions": {
                        condition: {
                            "ranked_session_ids": ranked_ids,
                            "metrics": all_retrieval_metrics(ranked_ids, [gold]),
                        }
                        for condition, ranked_ids in rankings.items()
                    },
                }
            )
        summaries = summarize(results)
        development = _development_report(DATASET_SHA256, "b" * 64, "a" * 64)
        cache = {
            "dataset_sha256": DATASET_SHA256,
            "baseline_ranking_sha256": "b" * 64,
            "schema": CACHE_SCHEMA,
            "candidate_k": 20,
            "contains_gold_answers": False,
            "question_ids_sha256": "c" * 64,
            "baseline_report_sha256": "d" * 64,
            "indexed_document_count": 100,
            "build_duration_seconds": 1.0,
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            development_path = Path(temp_dir) / "development.json"
            cache_path = Path(temp_dir) / "cache.json"
            development_path.write_text(json.dumps(development), encoding="utf-8")
            cache_path.write_text(json.dumps(cache), encoding="utf-8")

            with patch(
                "run_longmemeval_salience_heldout.EXPECTED_HELDOUT_COUNT",
                len(results),
            ):
                report = build_report(
                    results,
                    summaries,
                    development,
                    development_path,
                    cache,
                    cache_path,
                )

        self.assertTrue(
            report["decision"]["authorize_runtime_change"],
            report["decision"],
        )
        self.assertGreater(
            report["paired_comparisons"]["runtime_v2_vs_dense_chroma"][
                "paired_rate_delta"
            ],
            0,
        )

    def test_first_observation_cannot_be_overwritten(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_json = Path(temp_dir) / "heldout.json"
            output_md = Path(temp_dir) / "heldout.md"
            output_json.write_text("{}", encoding="utf-8")

            with self.assertRaisesRegex(FileExistsError, "already exists"):
                ensure_first_observation(output_json, output_md)


if __name__ == "__main__":
    unittest.main()
