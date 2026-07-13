#!/usr/bin/env python3
"""Evaluate one frozen Uruha memory-attention profile on LongMemEval held-out data."""

import argparse
import datetime
import json
import math
import statistics
import time
from collections import Counter
from pathlib import Path

import chromadb

import uruha_memory_runtime as umr
from project_paths import (
    LONGMEMEVAL_FROZEN_CANDIDATE_CACHE_PATH,
    LONGMEMEVAL_RETRIEVAL_REPORT_JSON_PATH,
    LONGMEMEVAL_S_CLEANED_DATASET_PATH,
    LONGMEMEVAL_SALIENCE_DEVELOPMENT_REPORT_JSON_PATH,
    LONGMEMEVAL_SALIENCE_HELDOUT_REPORT_JSON_PATH,
    LONGMEMEVAL_SALIENCE_HELDOUT_REPORT_MD_PATH,
)
from run_longmemeval_retrieval_benchmark import (
    DATASET_SHA256,
    METRIC_KS,
    PRIMARY_K,
    SPLIT_SALT,
    all_retrieval_metrics,
    atomic_write_json,
    canonical_sha256,
    dense_candidates,
    file_sha256,
    is_abstention,
    load_and_validate_dataset,
    paired_binary_comparison,
    parse_timestamp,
    preregistered_split,
    session_document,
)
from run_longmemeval_salience_development import benchmark_reference_time


CACHE_SCHEMA = "longmemeval_frozen_candidates_v1"
REPORT_SCOPE = "longmemeval_salience_single_heldout_v1"
CONDITIONS = ("dense_chroma", "legacy_wall_clock", "runtime_v2")
EXPECTED_DEVELOPMENT_COUNT = 95
EXPECTED_HELDOUT_COUNT = 375
MIN_DELTA_VS_LEGACY = 0.10
MAX_TASK_DROP_VS_DENSE = 0.05


def non_abstention_rows(data):
    return [row for row in data if not is_abstention(row)]


def heldout_rows(data):
    return [
        row
        for row in data
        if preregistered_split(row["question_id"]) == "test"
        and not is_abstention(row)
    ]


def _flush_collection(collection, ids, documents, metadatas):
    if not ids:
        return
    collection.add(ids=list(ids), documents=list(documents), metadatas=list(metadatas))
    ids.clear()
    documents.clear()
    metadatas.clear()


def build_candidate_cache(
    data,
    data_evidence,
    baseline_report,
    baseline_report_path,
    *,
    candidate_k=20,
    batch_size=64,
):
    """Build candidates without storing official gold answers in the cache."""
    if candidate_k < max(METRIC_KS):
        raise ValueError("candidate-k must cover every reported metric")
    client = chromadb.EphemeralClient()
    collection = client.create_collection(
        f"longmemeval_frozen_{data_evidence['sha256'][:12]}"
    )
    ids = []
    documents = []
    metadatas = []
    started = time.time()
    for question_index, row in enumerate(data):
        for session_index, (session_id, timestamp, session) in enumerate(
            zip(
                row["haystack_session_ids"],
                row["haystack_dates"],
                row["haystack_sessions"],
            )
        ):
            ids.append(f"q{question_index:04d}_s{session_index:03d}")
            documents.append(session_document(session, timestamp))
            metadatas.append(
                {
                    "question_id": row["question_id"],
                    "question_type": row["question_type"],
                    "benchmark_session_id": session_id,
                    "timestamp": parse_timestamp(timestamp),
                    "session_order": session_index,
                    "decay_flag": False,
                    "decay_multiplier": 1.0,
                }
            )
            if len(ids) >= batch_size:
                _flush_collection(collection, ids, documents, metadatas)
    _flush_collection(collection, ids, documents, metadatas)

    expected_documents = sum(len(row["haystack_session_ids"]) for row in data)
    if collection.count() != expected_documents:
        raise RuntimeError("Ephemeral held-out index count differs from the dataset")

    baseline_by_id = {
        row["question_id"]: row
        for row in baseline_report["results"]
        if not row["abstention"]
    }
    rows = []
    mismatches = []
    eligible = non_abstention_rows(data)
    for index, row in enumerate(eligible, start=1):
        candidates = dense_candidates(collection, row, candidate_k)
        ranked_ids = [
            candidate["metadata"]["benchmark_session_id"]
            for candidate in candidates
        ]
        expected_ids = baseline_by_id[row["question_id"]]["conditions"][
            "dense_chroma"
        ]["ranked_session_ids"]
        if ranked_ids != expected_ids:
            mismatches.append(row["question_id"])
        rows.append(
            {
                "question_id": row["question_id"],
                "question_type": row["question_type"],
                "question": row["question"],
                "question_date": row["question_date"],
                "split": preregistered_split(row["question_id"]),
                "candidates": candidates,
            }
        )
        if index % 25 == 0 or index == len(eligible):
            print(f"cached_frozen_queries={index}/{len(eligible)}", flush=True)
    if mismatches:
        raise RuntimeError(
            "Frozen dense candidates do not reproduce the formal baseline: "
            + ",".join(mismatches[:5])
        )
    return {
        "schema": CACHE_SCHEMA,
        "generated_at": datetime.datetime.now().astimezone().isoformat(
            timespec="seconds"
        ),
        "dataset_sha256": data_evidence["sha256"],
        "split_salt": SPLIT_SALT,
        "candidate_k": candidate_k,
        "contains_gold_answers": False,
        "question_ids_sha256": canonical_sha256(
            [row["question_id"] for row in rows]
        ),
        "baseline_ranking_sha256": baseline_report["ranking_evidence"]["sha256"],
        "baseline_report_sha256": file_sha256(baseline_report_path),
        "indexed_document_count": expected_documents,
        "build_duration_seconds": round(time.time() - started, 3),
        "rows": rows,
    }


def validate_candidate_cache(cache, data, baseline_report, baseline_report_path):
    if cache.get("schema") != CACHE_SCHEMA:
        raise ValueError("Frozen candidate cache schema differs")
    if cache.get("dataset_sha256") != DATASET_SHA256:
        raise ValueError("Frozen candidate cache dataset SHA differs")
    if cache.get("split_salt") != SPLIT_SALT:
        raise ValueError("Frozen candidate cache split salt differs")
    if cache.get("contains_gold_answers") is not False:
        raise ValueError("Frozen candidate cache must not contain gold answers")
    if cache.get("baseline_ranking_sha256") != baseline_report["ranking_evidence"][
        "sha256"
    ]:
        raise ValueError("Frozen candidate cache baseline ranking SHA differs")
    if cache.get("baseline_report_sha256") != file_sha256(baseline_report_path):
        raise ValueError("Frozen candidate cache baseline report SHA differs")

    expected_rows = non_abstention_rows(data)
    cached_rows = cache.get("rows") or []
    expected_ids = [row["question_id"] for row in expected_rows]
    if [row.get("question_id") for row in cached_rows] != expected_ids:
        raise ValueError("Frozen candidate cache question IDs differ")
    if cache.get("question_ids_sha256") != canonical_sha256(expected_ids):
        raise ValueError("Frozen candidate cache question SHA differs")
    candidate_k = cache.get("candidate_k")
    if not isinstance(candidate_k, int) or candidate_k < max(METRIC_KS):
        raise ValueError("Frozen candidate cache candidate-k is invalid")

    baseline_by_id = {
        row["question_id"]: row
        for row in baseline_report["results"]
        if not row["abstention"]
    }
    official_by_id = {row["question_id"]: row for row in expected_rows}
    for row in cached_rows:
        if "answer" in row or "answer_session_ids" in row:
            raise ValueError("Frozen candidate row leaks official gold answers")
        candidates = row.get("candidates") or []
        expected_count = min(
            candidate_k,
            len(official_by_id[row["question_id"]]["haystack_session_ids"]),
        )
        if len(candidates) != expected_count:
            raise ValueError(f"Frozen candidate cache is incomplete: {row['question_id']}")
        ranked_ids = [
            candidate["metadata"]["benchmark_session_id"]
            for candidate in candidates
        ]
        expected_ranked_ids = baseline_by_id[row["question_id"]]["conditions"][
            "dense_chroma"
        ]["ranked_session_ids"]
        if ranked_ids != expected_ranked_ids:
            raise ValueError(
                f"Frozen candidate ranking differs from baseline: {row['question_id']}"
            )
    return cached_rows


def validate_development_gate(development_report, data_evidence, baseline_report):
    boundary = development_report.get("data_boundary") or {}
    runtime = development_report.get("runtime_evidence") or {}
    decision = development_report.get("decision") or {}
    if boundary.get("question_count") != EXPECTED_DEVELOPMENT_COUNT:
        raise ValueError("Development gate question count differs")
    if boundary.get("test_question_count_evaluated") != 0:
        raise ValueError("Development gate already evaluated held-out questions")
    if boundary.get("dataset_sha256") != data_evidence["sha256"]:
        raise ValueError("Development gate dataset SHA differs")
    if boundary.get("baseline_ranking_sha256") != baseline_report[
        "ranking_evidence"
    ]["sha256"]:
        raise ValueError("Development gate baseline ranking SHA differs")
    if development_report.get("selected_experiment") != (
        "explicit_self_inverse_overlap"
    ):
        raise ValueError("Development gate selected experiment differs")
    if development_report.get("frozen_runtime_variant") != "runtime_v2":
        raise ValueError("Development gate runtime variant differs")
    if development_report.get("runtime_matches_selected_experiment") is not True:
        raise ValueError("Development runtime does not match the frozen experiment")
    if decision.get("authorize_test_evaluation") is not True:
        raise ValueError("Development gate did not authorize held-out evaluation")
    if decision.get("authorize_runtime_change") is not False:
        raise ValueError("Development-only report cannot authorize runtime change")
    if runtime.get("scoring_profile") != "v2":
        raise ValueError("Development gate scoring profile differs")
    if runtime.get("module_sha256") != file_sha256(Path(umr.__file__).resolve()):
        raise ValueError("Memory runtime changed after development freeze")
    reference_time = runtime.get("benchmark_reference_time")
    if not reference_time:
        raise ValueError("Development gate lacks a frozen reference time")
    parsed_reference = datetime.datetime.fromisoformat(reference_time)
    if parsed_reference != benchmark_reference_time(baseline_report):
        raise ValueError("Development and baseline reference times differ")
    return parsed_reference


def evaluate_heldout(cache_rows, data, baseline_report, reference_time):
    official_by_id = {row["question_id"]: row for row in data}
    baseline_by_id = {row["question_id"]: row for row in baseline_report["results"]}
    results = []
    for cache_row in cache_rows:
        if cache_row["split"] != "test":
            continue
        official = official_by_id[cache_row["question_id"]]
        gold_ids = list(dict.fromkeys(official.get("answer_session_ids") or []))
        dense_ids = [
            candidate["metadata"]["benchmark_session_id"]
            for candidate in cache_row["candidates"]
        ]
        legacy_ids = baseline_by_id[cache_row["question_id"]]["conditions"][
            "uruha_salience_rerank"
        ]["ranked_session_ids"]
        runtime_items = umr.build_working_memory(
            cache_row["question"],
            cache_row["candidates"],
            working_memory_limit=len(cache_row["candidates"]),
            reference_time=reference_time,
            scoring_profile="v2",
        )
        runtime_ids = [
            item["metadata"]["benchmark_session_id"] for item in runtime_items
        ]
        rankings = {
            "dense_chroma": dense_ids,
            "legacy_wall_clock": legacy_ids,
            "runtime_v2": runtime_ids,
        }
        conditions = {
            condition: {
                "ranked_session_ids": ranked_ids,
                "metrics": all_retrieval_metrics(ranked_ids, gold_ids),
            }
            for condition, ranked_ids in rankings.items()
        }
        results.append(
            {
                "question_id": cache_row["question_id"],
                "question_type": cache_row["question_type"],
                "split": "test",
                "abstention": False,
                "answer_session_ids": gold_ids,
                "candidate_pool_preserved": Counter(runtime_ids) == Counter(dense_ids),
                "conditions": conditions,
            }
        )
    if len(results) != EXPECTED_HELDOUT_COUNT:
        raise RuntimeError(
            f"Held-out count differs: {len(results)} != {EXPECTED_HELDOUT_COUNT}"
        )
    return results


def mean_metrics(results, condition):
    names = sorted(results[0]["conditions"][condition]["metrics"])
    return {
        metric: statistics.fmean(
            row["conditions"][condition]["metrics"][metric] for row in results
        )
        for metric in names
    }


def summarize(results):
    question_types = sorted({row["question_type"] for row in results})
    return {
        condition: {
            "overall": mean_metrics(results, condition),
            "by_question_type": {
                question_type: mean_metrics(
                    [
                        row
                        for row in results
                        if row["question_type"] == question_type
                    ],
                    condition,
                )
                for question_type in question_types
            },
        }
        for condition in CONDITIONS
    }


def heldout_ranking_sha256(results):
    return canonical_sha256(
        [
            {
                "question_id": row["question_id"],
                "conditions": {
                    condition: row["conditions"][condition]["ranked_session_ids"]
                    for condition in CONDITIONS
                },
            }
            for row in results
        ]
    )


def build_report(
    results,
    summaries,
    development_report,
    development_report_path,
    candidate_cache,
    candidate_cache_path,
):
    dense_comparison = paired_binary_comparison(
        results, "runtime_v2", "dense_chroma"
    )
    legacy_comparison = paired_binary_comparison(
        results, "runtime_v2", "legacy_wall_clock"
    )
    task_counts = Counter(row["question_type"] for row in results)
    task_deltas = {
        question_type: (
            summaries["runtime_v2"]["by_question_type"][question_type][
                f"recall_all@{PRIMARY_K}"
            ]
            - summaries["dense_chroma"]["by_question_type"][question_type][
                f"recall_all@{PRIMARY_K}"
            ]
        )
        for question_type in sorted(task_counts)
    }
    candidate_pool_preservation_rate = statistics.fmean(
        float(row["candidate_pool_preserved"]) for row in results
    )
    top20_preserved = math.isclose(candidate_pool_preservation_rate, 1.0)
    recall20_preserved = math.isclose(
        summaries["runtime_v2"]["overall"]["recall_all@20"],
        summaries["dense_chroma"]["overall"]["recall_all@20"],
    )
    task_floor_passed = all(
        delta >= -MAX_TASK_DROP_VS_DENSE for delta in task_deltas.values()
    )
    gates = {
        "development_authorized_test": development_report["decision"][
            "authorize_test_evaluation"
        ],
        "heldout_count_exact": len(results) == EXPECTED_HELDOUT_COUNT,
        "runtime_beats_dense": (
            dense_comparison["paired_rate_delta"] > 0
            and dense_comparison["exact_mcnemar_pvalue"] < 0.05
        ),
        "runtime_beats_legacy_by_preregistered_margin": (
            legacy_comparison["paired_rate_delta"] >= MIN_DELTA_VS_LEGACY
            and legacy_comparison["exact_mcnemar_pvalue"] < 0.05
        ),
        "candidate_pool_preserved": top20_preserved,
        "recall_all_at_20_preserved": recall20_preserved,
        "no_task_drop_beyond_margin": task_floor_passed,
    }
    authorize_runtime = all(gates.values())
    return {
        "generated_at": datetime.datetime.now().astimezone().isoformat(
            timespec="seconds"
        ),
        "scope": REPORT_SCOPE,
        "protocol": {
            "heldout_observations": 1,
            "primary_metric": f"recall_all@{PRIMARY_K}",
            "minimum_delta_vs_legacy": MIN_DELTA_VS_LEGACY,
            "maximum_task_drop_vs_dense": MAX_TASK_DROP_VS_DENSE,
            "conditions": list(CONDITIONS),
        },
        "data_boundary": {
            "split": "test",
            "question_count": len(results),
            "development_question_count": EXPECTED_DEVELOPMENT_COUNT,
            "answers_used_to_define_split": False,
            "split_salt": SPLIT_SALT,
            "dataset_sha256": candidate_cache["dataset_sha256"],
            "candidate_cache_sha256": file_sha256(candidate_cache_path),
            "baseline_ranking_sha256": candidate_cache[
                "baseline_ranking_sha256"
            ],
        },
        "frozen_evidence": {
            "development_report_sha256": file_sha256(development_report_path),
            "runtime_module_sha256": development_report["runtime_evidence"][
                "module_sha256"
            ],
            "scoring_profile": "v2",
            "benchmark_reference_time": development_report["runtime_evidence"][
                "benchmark_reference_time"
            ],
        },
        "candidate_cache_evidence": {
            key: candidate_cache[key]
            for key in (
                "schema",
                "candidate_k",
                "contains_gold_answers",
                "question_ids_sha256",
                "baseline_report_sha256",
                "indexed_document_count",
                "build_duration_seconds",
            )
        },
        "summaries": summaries,
        "paired_comparisons": {
            "runtime_v2_vs_dense_chroma": dense_comparison,
            "runtime_v2_vs_legacy_wall_clock": legacy_comparison,
        },
        "task_counts": dict(sorted(task_counts.items())),
        "task_deltas_vs_dense": task_deltas,
        "candidate_pool_preservation_rate": candidate_pool_preservation_rate,
        "ranking_evidence": {
            "sha256": heldout_ranking_sha256(results),
            "result_count": len(results),
        },
        "decision": {
            "gates": gates,
            "authorize_runtime_change": authorize_runtime,
            "decision_zh": (
                "一次性 held-out 門檻全部通過，可將凍結的 v2 注意力規則接入正式 runtime。"
                if authorize_runtime
                else "一次性 held-out 至少一項門檻未通過，不得將 v2 設為正式預設。"
            ),
        },
        "results": results,
    }


def write_markdown(report, path):
    primary = report["protocol"]["primary_metric"]
    lines = [
        "# LongMemEval 記憶注意力一次性 Held-out 結果",
        "",
        "## 實驗邊界",
        "",
        f"- 開發集：{report['data_boundary']['development_question_count']} 題（用來選規則）",
        f"- 測試集：{report['data_boundary']['question_count']} 題（只觀察一次）",
        "- 三組使用同一 Dense top-20 候選；v2 只改候選的注意力排序。",
        "- 候選快取不含官方答案；評分時才從固定官方資料讀取 gold session。",
        "",
        "## 總結果",
        "",
        f"| 組別 | {primary} | nDCG@5 | recall all@20 |",
        "|---|---:|---:|---:|",
    ]
    for condition in CONDITIONS:
        metrics = report["summaries"][condition]["overall"]
        lines.append(
            f"| {condition} | {100 * metrics[primary]:.2f}% | "
            f"{100 * metrics['ndcg_any@5']:.2f}% | "
            f"{100 * metrics['recall_all@20']:.2f}% |"
        )
    lines.extend(
        [
            "",
            "## 配對差異",
            "",
            "| 比較 | 淨增答對題 | 差異 | McNemar p |",
            "|---|---:|---:|---:|",
        ]
    )
    for label, comparison in report["paired_comparisons"].items():
        lines.append(
            f"| {label} | {comparison['paired_net_case_gain']:+d} | "
            f"{100 * comparison['paired_rate_delta']:+.2f} pp | "
            f"{comparison['exact_mcnemar_pvalue']:.6g} |"
        )
    lines.extend(
        [
            "",
            "## 各任務相對 Dense",
            "",
            "| 任務 | 題數 | v2 差異 |",
            "|---|---:|---:|",
        ]
    )
    for question_type, count in report["task_counts"].items():
        lines.append(
            f"| {question_type} | {count} | "
            f"{100 * report['task_deltas_vs_dense'][question_type]:+.2f} pp |"
        )
    lines.extend(
        [
            "",
            "## 決定",
            "",
            report["decision"]["decision_zh"],
            "",
            "| 預先設定門檻 | 結果 |",
            "|---|---:|",
        ]
    )
    for gate, passed in report["decision"]["gates"].items():
        lines.append(f"| {gate} | {'通過' if passed else '失敗'} |")
    lines.append("")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text("\n".join(lines), encoding="utf-8")
    temporary.replace(path)


def ensure_first_observation(output_json, output_md):
    existing = [str(path) for path in (Path(output_json), Path(output_md)) if path.exists()]
    if existing:
        raise FileExistsError(
            "Held-out result already exists; define a new protocol version instead of "
            "overwriting the first observation: " + ", ".join(existing)
        )


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default=LONGMEMEVAL_S_CLEANED_DATASET_PATH)
    parser.add_argument("--baseline-report", default=LONGMEMEVAL_RETRIEVAL_REPORT_JSON_PATH)
    parser.add_argument(
        "--development-report",
        default=LONGMEMEVAL_SALIENCE_DEVELOPMENT_REPORT_JSON_PATH,
    )
    parser.add_argument(
        "--candidate-cache", default=LONGMEMEVAL_FROZEN_CANDIDATE_CACHE_PATH
    )
    parser.add_argument(
        "--output-json", default=LONGMEMEVAL_SALIENCE_HELDOUT_REPORT_JSON_PATH
    )
    parser.add_argument("--output-md", default=LONGMEMEVAL_SALIENCE_HELDOUT_REPORT_MD_PATH)
    parser.add_argument("--batch-size", type=int, default=64)
    args = parser.parse_args(argv)

    ensure_first_observation(args.output_json, args.output_md)
    data, data_evidence = load_and_validate_dataset(args.dataset)
    baseline_path = Path(args.baseline_report)
    development_path = Path(args.development_report)
    baseline_report = json.loads(baseline_path.read_text(encoding="utf-8"))
    development_report = json.loads(development_path.read_text(encoding="utf-8"))
    if baseline_report.get("dataset_evidence", {}).get("sha256") != data_evidence[
        "sha256"
    ]:
        raise ValueError("Frozen baseline and official dataset SHA differ")
    reference_time = validate_development_gate(
        development_report,
        data_evidence,
        baseline_report,
    )

    cache_path = Path(args.candidate_cache)
    if not cache_path.is_file():
        cache = build_candidate_cache(
            data,
            data_evidence,
            baseline_report,
            baseline_path,
            batch_size=args.batch_size,
        )
        atomic_write_json(cache_path, cache)
    cache = json.loads(cache_path.read_text(encoding="utf-8"))
    cache_rows = validate_candidate_cache(
        cache,
        data,
        baseline_report,
        baseline_path,
    )
    results = evaluate_heldout(cache_rows, data, baseline_report, reference_time)
    summaries = summarize(results)
    report = build_report(
        results,
        summaries,
        development_report,
        development_path,
        cache,
        cache_path,
    )
    atomic_write_json(args.output_json, report)
    write_markdown(report, args.output_md)
    print(
        json.dumps(
            {
                "status": "heldout_first_observation_complete",
                "question_count": len(results),
                "runtime_recall_all_at_5": report["summaries"]["runtime_v2"][
                    "overall"
                ]["recall_all@5"],
                "delta_vs_dense": report["paired_comparisons"][
                    "runtime_v2_vs_dense_chroma"
                ]["paired_rate_delta"],
                "authorize_runtime_change": report["decision"][
                    "authorize_runtime_change"
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
