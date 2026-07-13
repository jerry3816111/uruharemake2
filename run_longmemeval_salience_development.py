#!/usr/bin/env python3
"""Run development-only LongMemEval ablations for Uruha memory attention."""

import argparse
import datetime
import json
import math
import statistics
import time
from pathlib import Path

import chromadb

import uruha_memory_runtime as umr
from project_paths import (
    LONGMEMEVAL_DEVELOPMENT_CANDIDATE_CACHE_PATH,
    LONGMEMEVAL_RETRIEVAL_REPORT_JSON_PATH,
    LONGMEMEVAL_S_CLEANED_DATASET_PATH,
    LONGMEMEVAL_SALIENCE_DEVELOPMENT_REPORT_JSON_PATH,
    LONGMEMEVAL_SALIENCE_DEVELOPMENT_REPORT_MD_PATH,
)
from run_longmemeval_retrieval_benchmark import (
    DATASET_SHA256,
    METRIC_KS,
    SPLIT_SALT,
    all_retrieval_metrics,
    atomic_write_json,
    canonical_sha256,
    dense_candidates,
    file_sha256,
    load_and_validate_dataset,
    paired_binary_comparison,
    parse_timestamp,
    preregistered_split,
    ranking_payload_sha256,
    session_document,
)


CACHE_SCHEMA = "longmemeval_development_candidates_v1"
VARIANT_COMPONENTS = {
    "legacy_wall_clock": frozenset(),
    "query_time_only": frozenset({"query_time"}),
    "inverse_distance_only": frozenset({"inverse_distance"}),
    "normalized_overlap_only": frozenset({"normalized_overlap"}),
    "explicit_self_only": frozenset({"explicit_self"}),
    "explicit_self_inverse_distance": frozenset(
        {"explicit_self", "inverse_distance"}
    ),
    "explicit_self_normalized_overlap": frozenset(
        {"explicit_self", "normalized_overlap"}
    ),
    "explicit_self_query_time": frozenset({"explicit_self", "query_time"}),
    "explicit_self_inverse_overlap": frozenset(
        {"explicit_self", "inverse_distance", "normalized_overlap"}
    ),
    "explicit_self_inverse_query_time": frozenset(
        {"explicit_self", "inverse_distance", "query_time"}
    ),
    "explicit_self_overlap_query_time": frozenset(
        {"explicit_self", "normalized_overlap", "query_time"}
    ),
    "all_component_fixes": frozenset(
        {"explicit_self", "inverse_distance", "normalized_overlap", "query_time"}
    ),
}
VARIANTS = (
    "dense_chroma",
    *VARIANT_COMPONENTS,
    "runtime_v2",
    "generative_agents_normalized",
)


def development_rows(data):
    return [
        row
        for row in data
        if preregistered_split(row["question_id"]) == "development"
        and not str(row["question_id"]).endswith("_abs")
    ]


def benchmark_reference_time(baseline_report):
    """Freeze wall-clock recency to the timestamp of the formal baseline."""
    value = str(baseline_report.get("generated_at") or "").strip()
    if not value:
        raise ValueError("Frozen baseline is missing generated_at")
    try:
        return datetime.datetime.fromisoformat(value).replace(tzinfo=None)
    except ValueError as exc:
        raise ValueError("Frozen baseline generated_at is invalid") from exc


def parse_question_time(value):
    return datetime.datetime.strptime(parse_timestamp(value), "%Y-%m-%d %H:%M:%S")


def inverse_distance_similarity(distance):
    return umr.distance_similarity(distance, scoring_profile="v2")


def normalized_overlap_bonus(query_tokens, text):
    return umr.lexical_overlap_bonus(query_tokens, text, scoring_profile="v2")


def explicit_self_relevance_bonus(candidate):
    return umr.explicit_self_relevance_bonus(candidate)


def score_from_factors(factors, replacements=None):
    values = dict(factors)
    values.update(replacements or {})
    raw_score = (
        values["similarity"]
        + values["recency"]
        + values["overlap"]
        + values["strength"]
        + values["source_bias"]
        + values["emotional"]
        + values["self_relevance"]
        + values["unresolved"]
        + values["threat"]
        - values["brevity_penalty"]
        - values["decay_penalty"]
    )
    return raw_score * values["decay_multiplier"]


def deduplicate_candidates(candidates):
    output = []
    seen = set()
    for candidate in candidates:
        normalized = " ".join(str(candidate.get("text") or "").split())
        if not normalized:
            continue
        key = (candidate.get("source"), normalized[:120])
        if key in seen:
            continue
        seen.add(key)
        output.append(candidate)
    return output


def minmax(values):
    if not values:
        return []
    low = min(values)
    high = max(values)
    if math.isclose(low, high):
        return [0.5 for _ in values]
    return [(value - low) / (high - low) for value in values]


def rank_independent_variant(candidates, question, question_now, wall_now, variant):
    if variant == "legacy_wall_clock":
        candidates = deduplicate_candidates(candidates)
        return umr.build_working_memory(
            question,
            candidates,
            working_memory_limit=len(candidates),
            reference_time=wall_now,
            scoring_profile="legacy",
        )
    components = VARIANT_COMPONENTS[variant]
    query_tokens = umr.memory_tokens(question)
    scored = []
    for dense_rank, candidate in enumerate(deduplicate_candidates(candidates)):
        factor_now = question_now if "query_time" in components else wall_now
        factors = umr.attention_factor_values(
            candidate,
            query_tokens,
            factor_now,
            scoring_profile="legacy",
        )
        replacements = {}
        if "inverse_distance" in components:
            replacements["similarity"] = inverse_distance_similarity(
                candidate.get("distance")
            )
        if "normalized_overlap" in components:
            replacements["overlap"] = normalized_overlap_bonus(
                query_tokens,
                candidate.get("text") or "",
            )
        if "explicit_self" in components:
            replacements["self_relevance"] = explicit_self_relevance_bonus(candidate)
        score = score_from_factors(factors, replacements)
        scored.append((score, -dense_rank, candidate))
    scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return [candidate for _, _, candidate in scored]


def rank_generative_agents_normalized(candidates, question, question_now):
    query_tokens = umr.memory_tokens(question)
    prepared = []
    for dense_rank, candidate in enumerate(deduplicate_candidates(candidates)):
        factors = umr.attention_factors(candidate, query_tokens, question_now)
        similarity = inverse_distance_similarity(candidate.get("distance"))
        importance = min(
            1.0,
            factors["strength"]
            + factors["emotional"]
            + explicit_self_relevance_bonus(candidate)
            + factors["unresolved"]
            + factors["threat"],
        )
        prepared.append(
            {
                "candidate": candidate,
                "dense_rank": dense_rank,
                "similarity": similarity,
                "recency": factors["recency"],
                "importance": importance,
                "penalty": factors["brevity_penalty"] + factors["decay_penalty"],
                "decay_multiplier": factors["decay_multiplier"],
            }
        )
    relevance_norm = minmax([item["similarity"] for item in prepared])
    recency_norm = minmax([item["recency"] for item in prepared])
    importance_norm = minmax([item["importance"] for item in prepared])
    scored = []
    for index, item in enumerate(prepared):
        # Generative Agents reference weights: relevance=3, importance=2, recency=0.5.
        score = (
            3.0 * relevance_norm[index]
            + 2.0 * importance_norm[index]
            + 0.5 * recency_norm[index]
            - item["penalty"]
        ) * item["decay_multiplier"]
        scored.append((score, -item["dense_rank"], item["candidate"]))
    scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return [candidate for _, _, candidate in scored]


def rank_runtime_v2(candidates, question, wall_now):
    candidates = deduplicate_candidates(candidates)
    return umr.build_working_memory(
        question,
        candidates,
        working_memory_limit=len(candidates),
        reference_time=wall_now,
        scoring_profile="v2",
    )


def rank_variant(candidates, question, question_now, wall_now, variant):
    if variant == "dense_chroma":
        return list(candidates)
    if variant == "runtime_v2":
        return rank_runtime_v2(candidates, question, wall_now)
    if variant == "generative_agents_normalized":
        return rank_generative_agents_normalized(candidates, question, question_now)
    return rank_independent_variant(candidates, question, question_now, wall_now, variant)


def _flush_collection(collection, ids, documents, metadatas):
    if not ids:
        return
    collection.add(ids=list(ids), documents=list(documents), metadatas=list(metadatas))
    ids.clear()
    documents.clear()
    metadatas.clear()


def build_candidate_cache(data, data_evidence, baseline_report, candidate_k=20, batch_size=64):
    if candidate_k < max(METRIC_KS):
        raise ValueError("candidate-k must cover every reported metric")
    client = chromadb.EphemeralClient()
    collection = client.create_collection(
        f"longmemeval_dev_probe_{data_evidence['sha256'][:12]}"
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
        raise RuntimeError("Ephemeral development index count differs from the dataset")

    baseline_by_id = {
        row["question_id"]: row
        for row in baseline_report["results"]
        if row["split"] == "development" and not row["abstention"]
    }
    rows = []
    mismatch_ids = []
    for index, row in enumerate(development_rows(data), start=1):
        candidates = dense_candidates(collection, row, candidate_k)
        dense_ids = [
            candidate["metadata"]["benchmark_session_id"] for candidate in candidates
        ]
        expected_ids = baseline_by_id[row["question_id"]]["conditions"]["dense_chroma"][
            "ranked_session_ids"
        ]
        if dense_ids != expected_ids:
            mismatch_ids.append(row["question_id"])
        rows.append(
            {
                "question_id": row["question_id"],
                "question_type": row["question_type"],
                "question": row["question"],
                "question_date": row["question_date"],
                "answer_session_ids": row["answer_session_ids"],
                "candidates": candidates,
            }
        )
        if index % 20 == 0 or index == len(baseline_by_id):
            print(f"cached_development_queries={index}/{len(baseline_by_id)}")
    if mismatch_ids:
        raise RuntimeError(
            "Development dense candidates do not reproduce the frozen baseline: "
            + ",".join(mismatch_ids[:5])
        )
    return {
        "schema": CACHE_SCHEMA,
        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "dataset_sha256": data_evidence["sha256"],
        "split_salt": SPLIT_SALT,
        "candidate_k": candidate_k,
        "development_question_ids_sha256": canonical_sha256(
            [row["question_id"] for row in rows]
        ),
        "baseline_ranking_sha256": baseline_report["ranking_evidence"]["sha256"],
        "baseline_report_sha256": file_sha256(LONGMEMEVAL_RETRIEVAL_REPORT_JSON_PATH),
        "indexed_document_count": expected_documents,
        "build_duration_seconds": round(time.time() - started, 3),
        "rows": rows,
    }


def validate_candidate_cache(cache, data, baseline_report):
    if cache.get("schema") != CACHE_SCHEMA:
        raise ValueError("Development candidate cache schema differs")
    if cache.get("dataset_sha256") != DATASET_SHA256:
        raise ValueError("Development candidate cache dataset SHA differs")
    if cache.get("split_salt") != SPLIT_SALT:
        raise ValueError("Development candidate cache split salt differs")
    expected_rows = development_rows(data)
    cached_rows = cache.get("rows") or []
    expected_ids = [row["question_id"] for row in expected_rows]
    if [row.get("question_id") for row in cached_rows] != expected_ids:
        raise ValueError("Development candidate cache question IDs differ")
    if cache.get("development_question_ids_sha256") != canonical_sha256(expected_ids):
        raise ValueError("Development candidate cache question SHA differs")
    if cache.get("baseline_ranking_sha256") != baseline_report["ranking_evidence"][
        "sha256"
    ]:
        raise ValueError("Development candidate cache baseline ranking SHA differs")
    candidate_k = cache.get("candidate_k")
    if not isinstance(candidate_k, int) or candidate_k < max(METRIC_KS):
        raise ValueError("Development candidate cache candidate-k is invalid")
    for row in cached_rows:
        candidates = row.get("candidates") or []
        if len(candidates) != candidate_k:
            raise ValueError(f"Development candidate cache is incomplete: {row['question_id']}")
    return cached_rows


def mean_metrics(results, variant):
    names = sorted(results[0]["conditions"][variant]["metrics"])
    return {
        metric: statistics.fmean(
            row["conditions"][variant]["metrics"][metric] for row in results
        )
        for metric in names
    }


def evaluate_cache(cache_rows, wall_now=None):
    wall_now = wall_now or datetime.datetime.now()
    results = []
    for row in cache_rows:
        question_now = parse_question_time(row["question_date"])
        conditions = {}
        for variant in VARIANTS:
            ranked = rank_variant(
                row["candidates"],
                row["question"],
                question_now,
                wall_now,
                variant,
            )
            ranked_ids = [
                item["metadata"]["benchmark_session_id"] for item in ranked
            ]
            conditions[variant] = {
                "ranked_session_ids": ranked_ids,
                "metrics": all_retrieval_metrics(
                    ranked_ids,
                    row["answer_session_ids"],
                ),
            }
        results.append(
            {
                "question_id": row["question_id"],
                "question_type": row["question_type"],
                "split": "development",
                "abstention": False,
                "answer_session_ids": row["answer_session_ids"],
                "conditions": conditions,
            }
        )
    return results


def summarize(results):
    question_types = sorted({row["question_type"] for row in results})
    summaries = {}
    for variant in VARIANTS:
        summaries[variant] = {
            "overall": mean_metrics(results, variant),
            "by_question_type": {
                question_type: mean_metrics(
                    [row for row in results if row["question_type"] == question_type],
                    variant,
                )
                for question_type in question_types
            },
        }
    comparisons = {
        variant: paired_binary_comparison(results, variant, "dense_chroma")
        for variant in VARIANTS
        if variant != "dense_chroma"
    }
    return summaries, comparisons


def build_report(
    cache,
    results,
    summaries,
    comparisons,
    *,
    candidate_cache_path=LONGMEMEVAL_DEVELOPMENT_CANDIDATE_CACHE_PATH,
    reference_time=None,
):
    best_variant = max(
        VARIANTS,
        key=lambda variant: summaries[variant]["overall"]["recall_all@5"],
    )
    baseline_reproduced = math.isclose(
        summaries["dense_chroma"]["overall"]["recall_all@5"],
        66 / 95,
    ) and math.isclose(
        summaries["legacy_wall_clock"]["overall"]["recall_all@5"],
        26 / 95,
    )
    selected_experiment = "explicit_self_inverse_overlap"
    frozen_runtime_variant = "runtime_v2"
    runtime_matches_experiment = all(
        row["conditions"][frozen_runtime_variant]["ranked_session_ids"]
        == row["conditions"][selected_experiment]["ranked_session_ids"]
        for row in results
    )
    frozen_comparison = comparisons[frozen_runtime_variant]
    authorize_test = (
        baseline_reproduced
        and runtime_matches_experiment
        and frozen_comparison["paired_net_case_gain"] > 0
        and frozen_comparison["exact_mcnemar_pvalue"] < 0.05
    )
    return {
        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "scope": "longmemeval_salience_development_only_v1",
        "research_sources": {
            "chroma_distance": "https://docs.trychroma.com/docs/collections/configure",
            "generative_agents_paper": "https://arxiv.org/abs/2304.03442",
            "generative_agents_retrieval_code": (
                "https://github.com/joonspk-research/generative_agents/blob/main/"
                "reverie/backend_server/persona/cognitive_modules/retrieve.py"
            ),
        },
        "data_boundary": {
            "split": "development",
            "question_count": len(results),
            "test_question_count_evaluated": 0,
            "answers_used_to_define_split": False,
            "split_salt": SPLIT_SALT,
            "dataset_sha256": cache["dataset_sha256"],
            "candidate_cache_sha256": file_sha256(candidate_cache_path),
            "baseline_ranking_sha256": cache["baseline_ranking_sha256"],
        },
        "runtime_evidence": {
            "module": "uruha_memory_runtime.py",
            "module_sha256": file_sha256(Path(umr.__file__).resolve()),
            "scoring_profile": "v2",
            "benchmark_reference_time": (
                reference_time.isoformat(timespec="seconds")
                if reference_time is not None
                else None
            ),
        },
        "candidate_cache_evidence": {
            key: cache[key]
            for key in (
                "schema",
                "candidate_k",
                "development_question_ids_sha256",
                "baseline_report_sha256",
                "indexed_document_count",
                "build_duration_seconds",
            )
        },
        "variants": list(VARIANTS),
        "summaries": summaries,
        "paired_vs_dense": comparisons,
        "ranking_evidence": {
            "sha256": ranking_payload_sha256(results),
            "result_count": len(results),
        },
        "baseline_reproduced": baseline_reproduced,
        "best_development_variant": best_variant,
        "selected_experiment": selected_experiment,
        "frozen_runtime_variant": frozen_runtime_variant,
        "runtime_matches_selected_experiment": runtime_matches_experiment,
        "decision": {
            "authorize_test_evaluation": authorize_test,
            "authorize_runtime_change": False,
            "decision_zh": (
                "development 已完成單變因與交互作用消融；若 test gate 為 true，"
                "只允許凍結後做一次 held-out test，仍不能直接升級 runtime。"
            ),
        },
        "results": results,
    }


def write_markdown(report, path):
    lines = [
        "# LongMemEval 記憶注意力 Development 消融",
        "",
        "## 邊界",
        "",
        f"- 只測 development：{report['data_boundary']['question_count']} 題",
        "- test 評分：0 題",
        f"- 凍結 Dense top-{report['candidate_cache_evidence']['candidate_k']} 候選；只改排序規則。",
        f"- 正式基線重現：{'通過' if report['baseline_reproduced'] else '失敗'}",
        "",
        "## 結果",
        "",
        "| Variant | recall all@5 | nDCG@5 | 相對 Dense |",
        "|---|---:|---:|---:|",
    ]
    dense = report["summaries"]["dense_chroma"]["overall"]["recall_all@5"]
    for variant in VARIANTS:
        metrics = report["summaries"][variant]["overall"]
        value = metrics["recall_all@5"]
        lines.append(
            f"| {variant} | {100 * value:.2f}% | "
            f"{100 * metrics['ndcg_any@5']:.2f}% | {100 * (value - dense):+.2f} pp |"
        )
    lines.extend(
        [
            "",
            "## 判定",
            "",
            report["decision"]["decision_zh"],
            "",
            f"目前 development 最佳：`{report['best_development_variant']}`。",
            f"凍結 runtime：`{report['frozen_runtime_variant']}`。",
            f"與選定實驗逐題同排序：{'是' if report['runtime_matches_selected_experiment'] else '否'}。",
            f"允許一次 held-out test：{'是' if report['decision']['authorize_test_evaluation'] else '否'}。",
            "",
        ]
    )
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text("\n".join(lines), encoding="utf-8")


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default=LONGMEMEVAL_S_CLEANED_DATASET_PATH)
    parser.add_argument("--baseline-report", default=LONGMEMEVAL_RETRIEVAL_REPORT_JSON_PATH)
    parser.add_argument("--candidate-cache", default=LONGMEMEVAL_DEVELOPMENT_CANDIDATE_CACHE_PATH)
    parser.add_argument("--output-json", default=LONGMEMEVAL_SALIENCE_DEVELOPMENT_REPORT_JSON_PATH)
    parser.add_argument("--output-md", default=LONGMEMEVAL_SALIENCE_DEVELOPMENT_REPORT_MD_PATH)
    parser.add_argument("--rebuild-cache", action="store_true")
    parser.add_argument("--batch-size", type=int, default=64)
    args = parser.parse_args(argv)

    data, data_evidence = load_and_validate_dataset(args.dataset)
    baseline_report = json.loads(Path(args.baseline_report).read_text(encoding="utf-8"))
    if baseline_report.get("dataset_evidence", {}).get("sha256") != data_evidence[
        "sha256"
    ]:
        raise ValueError("Frozen baseline and official dataset SHA differ")

    cache_path = Path(args.candidate_cache)
    if args.rebuild_cache or not cache_path.is_file():
        cache = build_candidate_cache(
            data,
            data_evidence,
            baseline_report,
            batch_size=args.batch_size,
        )
        atomic_write_json(cache_path, cache)
    cache = json.loads(cache_path.read_text(encoding="utf-8"))
    cache_rows = validate_candidate_cache(cache, data, baseline_report)
    reference_time = benchmark_reference_time(baseline_report)
    results = evaluate_cache(cache_rows, wall_now=reference_time)
    summaries, comparisons = summarize(results)
    report = build_report(
        cache,
        results,
        summaries,
        comparisons,
        candidate_cache_path=cache_path,
        reference_time=reference_time,
    )
    if not report["baseline_reproduced"]:
        raise RuntimeError("Development probe failed to reproduce the frozen baseline")
    atomic_write_json(args.output_json, report)
    write_markdown(report, args.output_md)
    print(
        json.dumps(
            {
                "status": "development_only_complete",
                "question_count": len(results),
                "test_question_count": 0,
                "best_variant": report["best_development_variant"],
                "best_recall_all_at_5": report["summaries"][
                    report["best_development_variant"]
                ]["overall"]["recall_all@5"],
                "runtime_change": False,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
