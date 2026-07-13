#!/usr/bin/env python3
"""Evaluate Uruha episodic-memory selection on official LongMemEval-S."""

import argparse
import hashlib
import json
import math
import random
import re
import statistics
import time
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import chromadb
from scipy.stats import binomtest

import uruha_memory_runtime as umr
from project_paths import (
    LONGMEMEVAL_CHROMA_CACHE_DIR,
    LONGMEMEVAL_RETRIEVAL_REPORT_JSON_PATH,
    LONGMEMEVAL_RETRIEVAL_REPORT_MD_PATH,
    LONGMEMEVAL_S_CLEANED_DATASET_PATH,
)


TZ = ZoneInfo("Asia/Tokyo")
DATASET_URL = (
    "https://huggingface.co/datasets/xiaowu0162/longmemeval-cleaned/resolve/main/"
    "longmemeval_s_cleaned.json"
)
DATASET_SHA256 = "d6f21ea9d60a0d56f34a05b609c79c88a451d2ae03597821ea3d5a9678c3a442"
DATASET_BYTES = 277_383_467
DATASET_ROWS = 500
OFFICIAL_REPOSITORY = "https://github.com/xiaowu0162/LongMemEval"
OFFICIAL_REPOSITORY_COMMIT = "9e0b455f4ef0e2ab8f2e582289761153549043fc"
OFFICIAL_PAPER = "https://arxiv.org/abs/2410.10813"
OFFICIAL_METRIC_SOURCE = (
    "https://github.com/xiaowu0162/LongMemEval/blob/"
    f"{OFFICIAL_REPOSITORY_COMMIT}/src/retrieval/eval_utils.py"
)
DOCUMENT_MODE = "timestamped_session_user_and_assistant_v1"
SPLIT_SALT = "uruha-longmemeval-retrieval-v1"
CONDITIONS = (
    "recent_session_order",
    "dense_chroma",
    "uruha_salience_rerank",
)
METRIC_KS = (1, 3, 5, 10, 20)
PRIMARY_K = 5


def file_sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_sha256(value):
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def ranking_payload_sha256(results):
    payload = [
        {
            "question_id": result.get("question_id"),
            "conditions": {
                condition: (
                    (result.get("conditions") or {})
                    .get(condition, {})
                    .get("ranked_session_ids")
                    or []
                )
                for condition in CONDITIONS
            },
        }
        for result in results
    ]
    return canonical_sha256(payload)


def atomic_write_json(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def download_official_dataset(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".download")
    temporary.unlink(missing_ok=True)
    urllib.request.urlretrieve(DATASET_URL, temporary)
    if temporary.stat().st_size != DATASET_BYTES:
        temporary.unlink(missing_ok=True)
        raise ValueError("Downloaded LongMemEval-S byte size does not match the pinned release")
    if file_sha256(temporary) != DATASET_SHA256:
        temporary.unlink(missing_ok=True)
        raise ValueError("Downloaded LongMemEval-S SHA does not match the pinned release")
    temporary.replace(path)


def load_and_validate_dataset(
    path,
    *,
    expected_sha=DATASET_SHA256,
    expected_bytes=DATASET_BYTES,
    expected_rows=DATASET_ROWS,
):
    path = Path(path)
    actual_bytes = path.stat().st_size
    if actual_bytes != expected_bytes:
        raise ValueError(
            f"LongMemEval-S byte size mismatch: {actual_bytes} != {expected_bytes}"
        )
    actual_sha = file_sha256(path)
    if actual_sha != expected_sha:
        raise ValueError(f"LongMemEval-S SHA mismatch: {actual_sha} != {expected_sha}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list) or len(data) != expected_rows:
        raise ValueError(f"LongMemEval-S row count mismatch: {len(data)} != {expected_rows}")
    required = {
        "question_id",
        "question_type",
        "question",
        "answer",
        "question_date",
        "haystack_session_ids",
        "haystack_dates",
        "haystack_sessions",
        "answer_session_ids",
    }
    question_ids = []
    for row in data:
        if not required.issubset(row):
            raise ValueError("LongMemEval-S row is missing an official field")
        lengths = {
            len(row["haystack_session_ids"]),
            len(row["haystack_dates"]),
            len(row["haystack_sessions"]),
        }
        if len(lengths) != 1:
            raise ValueError(f"LongMemEval-S session arrays differ for {row['question_id']}")
        question_ids.append(str(row["question_id"]))
    if len(question_ids) != len(set(question_ids)):
        raise ValueError("LongMemEval-S question IDs are not unique")
    return data, {
        "path": str(path.resolve()),
        "sha256": actual_sha,
        "bytes": actual_bytes,
        "row_count": len(data),
    }


def is_abstention(row):
    return str(row["question_id"]).endswith("_abs")


def preregistered_split(question_id):
    digest = hashlib.sha256(f"{SPLIT_SALT}:{question_id}".encode("utf-8")).digest()
    return "development" if int.from_bytes(digest[:4], "big") % 5 == 0 else "test"


def select_rows(data, max_items=0, seed=20260712):
    if not max_items or max_items >= len(data):
        return list(data)
    groups = defaultdict(list)
    for row in data:
        key = (row["question_type"], is_abstention(row))
        groups[key].append(row)
    rng = random.Random(seed)
    for rows in groups.values():
        rows.sort(key=lambda row: row["question_id"])
        rng.shuffle(rows)
    selected = []
    key_phases = [
        sorted(key for key in groups if not key[1]),
        sorted(key for key in groups if key[1]),
    ]
    for ordered_keys in key_phases:
        while len(selected) < max_items:
            progressed = False
            for key in ordered_keys:
                if groups[key] and len(selected) < max_items:
                    selected.append(groups[key].pop())
                    progressed = True
            if not progressed:
                break
        if len(selected) >= max_items:
            break
    return selected


def parse_timestamp(value):
    cleaned = re.sub(r"\s+\([A-Za-z]{3}\)\s+", " ", str(value).strip())
    parsed = datetime.strptime(cleaned, "%Y/%m/%d %H:%M")
    return parsed.strftime("%Y-%m-%d %H:%M:%S")


def session_document(session, timestamp):
    lines = [f"Time: {parse_timestamp(timestamp)}"]
    for turn in session:
        role = "User" if turn.get("role") == "user" else "Assistant"
        content = re.sub(r"\s+", " ", str(turn.get("content") or "")).strip()
        if content:
            lines.append(f"{role}: {content}")
    return "\n".join(lines)


def index_spec(rows, dataset_sha):
    question_ids = [row["question_id"] for row in rows]
    return {
        "dataset_sha256": dataset_sha,
        "document_mode": DOCUMENT_MODE,
        "question_count": len(rows),
        "question_ids_sha256": canonical_sha256(question_ids),
        "expected_document_count": sum(len(row["haystack_sessions"]) for row in rows),
    }


def prepare_chroma_index(
    rows,
    dataset_sha,
    cache_dir,
    *,
    rebuild=False,
    batch_size=64,
):
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    spec = index_spec(rows, dataset_sha)
    spec_sha = canonical_sha256(spec)
    collection_name = f"longmemeval_sessions_{spec_sha[:16]}"
    manifest_path = cache_dir / f"{collection_name}.manifest.json"
    client = chromadb.PersistentClient(path=str(cache_dir))
    collection = None
    try:
        collection = client.get_collection(collection_name)
    except Exception:
        pass
    manifest = None
    if manifest_path.is_file():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except Exception:
            manifest = None
    if not rebuild and collection is not None:
        raise RuntimeError(
            "Persistent Chroma HNSW reuse is disabled for this benchmark because the "
            "current macOS/Python build can segfault while reopening a large collection. "
            "Use --recompute-from-report for metric-only changes or --rebuild-index."
        )

    if collection is not None:
        client.delete_collection(collection_name)
    manifest_path.unlink(missing_ok=True)
    collection = client.create_collection(collection_name)
    ids = []
    documents = []
    metadatas = []
    started = time.time()

    def flush():
        if not ids:
            return
        collection.add(ids=list(ids), documents=list(documents), metadatas=list(metadatas))
        ids.clear()
        documents.clear()
        metadatas.clear()

    for question_index, row in enumerate(rows):
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
                flush()
    flush()
    if collection.count() != spec["expected_document_count"]:
        raise RuntimeError("LongMemEval Chroma index count does not match its manifest")
    manifest = {
        "generated_at": datetime.now(TZ).isoformat(timespec="seconds"),
        "collection_name": collection_name,
        "spec": spec,
        "spec_sha256": spec_sha,
        "collection_count": collection.count(),
        "build_duration_seconds": round(time.time() - started, 3),
        "reused": False,
    }
    atomic_write_json(manifest_path, manifest)
    return collection, manifest


def dense_candidates(collection, row, candidate_k):
    count = min(candidate_k, len(row["haystack_session_ids"]))
    result = collection.query(
        query_texts=[row["question"]],
        n_results=count,
        where={"question_id": row["question_id"]},
        include=["documents", "metadatas", "distances"],
    )
    candidates = []
    for memory_id, text, metadata, distance in zip(
        result["ids"][0],
        result["documents"][0],
        result["metadatas"][0],
        result["distances"][0],
    ):
        candidates.append(
            {
                "source": "episode",
                "text": text,
                "metadata": metadata,
                "distance": distance,
                "memory_id": memory_id,
                "collection_name": "episode",
            }
        )
    return candidates


def dcg(relevances, k):
    values = list(relevances)[:k]
    if not values:
        return 0.0
    return float(values[0]) + sum(
        float(values[index]) / math.log2(index + 1)
        for index in range(1, len(values))
    )


def retrieval_metrics(ranked_ids, correct_ids, k):
    ranked_ids = list(ranked_ids)
    correct_ids = set(correct_ids)
    retrieved = set(ranked_ids[:k])
    recall_any = float(bool(correct_ids & retrieved))
    recall_all = float(bool(correct_ids) and correct_ids.issubset(retrieved))
    relevances = [1 if session_id in correct_ids else 0 for session_id in ranked_ids]
    actual = dcg(relevances, k)
    ideal = dcg([1] * len(correct_ids), k)
    return {
        f"recall_any@{k}": recall_any,
        f"recall_all@{k}": recall_all,
        f"ndcg_any@{k}": actual / ideal if ideal else 0.0,
    }


def all_retrieval_metrics(ranked_ids, correct_ids, ks=METRIC_KS):
    output = {}
    for k in ks:
        output.update(retrieval_metrics(ranked_ids, correct_ids, k))
    return output


def evaluate_item(collection, row, candidate_k=20):
    candidates = dense_candidates(collection, row, candidate_k)
    dense_ids = [item["metadata"]["benchmark_session_id"] for item in candidates]
    salience_items = umr.build_working_memory(
        row["question"],
        candidates,
        working_memory_limit=len(candidates),
    )
    salience_ids = [
        item["metadata"]["benchmark_session_id"] for item in salience_items
    ]
    recent_ids = list(reversed(row["haystack_session_ids"]))
    correct_ids = list(dict.fromkeys(row.get("answer_session_ids") or []))
    rankings = {
        "recent_session_order": recent_ids,
        "dense_chroma": dense_ids,
        "uruha_salience_rerank": salience_ids,
    }
    conditions = {}
    for name, ids in rankings.items():
        ranked_ids = ids[:candidate_k]
        conditions[name] = {
            "ranked_session_ids": ranked_ids,
            "metrics": all_retrieval_metrics(ranked_ids, correct_ids),
        }
    return {
        "question_id": row["question_id"],
        "question_type": row["question_type"],
        "split": preregistered_split(row["question_id"]),
        "abstention": is_abstention(row),
        "history_session_count": len(row["haystack_sessions"]),
        "answer_session_ids": correct_ids,
        "conditions": conditions,
        "uruha_top5_attention_factors": [
            {
                "session_id": item["metadata"]["benchmark_session_id"],
                "score": item["score"],
                "attention_factors": item["attention_factors"],
            }
            for item in salience_items[:PRIMARY_K]
        ],
    }


def recompute_results_from_rankings(results):
    rebuilt = json.loads(json.dumps(results, ensure_ascii=False))
    seen_ids = set()
    for row in rebuilt:
        question_id = str(row.get("question_id") or "")
        if not question_id or question_id in seen_ids:
            raise ValueError("Ranking source report has a missing or duplicate question ID")
        seen_ids.add(question_id)
        correct_ids = list(dict.fromkeys(row.get("answer_session_ids") or []))
        conditions = row.get("conditions") or {}
        if set(conditions) != set(CONDITIONS):
            raise ValueError(f"Ranking source conditions are incomplete for {question_id}")
        for condition in CONDITIONS:
            ranked_ids = conditions[condition].get("ranked_session_ids") or []
            if not ranked_ids:
                raise ValueError(f"Ranking source is empty for {question_id}/{condition}")
            conditions[condition]["metrics"] = all_retrieval_metrics(
                ranked_ids,
                correct_ids,
            )
    return rebuilt


def validate_ranking_results_against_dataset(
    results,
    data,
    *,
    candidate_k=20,
    expected_count=None,
    expected_ids_sha=None,
):
    if candidate_k < max(METRIC_KS):
        raise ValueError(
            f"Ranking source candidate-k must cover every reported metric: {candidate_k}"
        )
    data_map = {row["question_id"]: row for row in data}
    selected = []
    seen_ids = set()
    for result in results:
        question_id = str(result.get("question_id") or "")
        if not question_id or question_id in seen_ids:
            raise ValueError("Ranking source has a missing or duplicate question ID")
        seen_ids.add(question_id)
        official = data_map.get(question_id)
        if official is None:
            raise ValueError(f"Ranking source question is absent from dataset: {question_id}")
        expected_gold = set(official.get("answer_session_ids") or [])
        observed_gold = set(result.get("answer_session_ids") or [])
        if observed_gold != expected_gold:
            raise ValueError(f"Ranking source gold IDs differ from dataset: {question_id}")
        if result.get("question_type") != official.get("question_type"):
            raise ValueError(f"Ranking source question type differs from dataset: {question_id}")
        if bool(result.get("abstention")) != is_abstention(official):
            raise ValueError(f"Ranking source abstention flag differs from dataset: {question_id}")
        if result.get("split") != preregistered_split(question_id):
            raise ValueError(f"Ranking source split differs from preregistration: {question_id}")
        allowed_counts = Counter(official["haystack_session_ids"])
        conditions = result.get("conditions") or {}
        if set(conditions) != set(CONDITIONS):
            raise ValueError(f"Ranking source conditions are incomplete for {question_id}")
        expected_ranking_count = min(candidate_k, len(official["haystack_session_ids"]))
        for condition in CONDITIONS:
            ranked_ids = conditions[condition].get("ranked_session_ids") or []
            if len(ranked_ids) != expected_ranking_count:
                raise ValueError(
                    f"Ranking source length differs from candidate pool for "
                    f"{question_id}/{condition}"
                )
            ranked_counts = Counter(ranked_ids)
            unknown_ids = set(ranked_counts) - set(allowed_counts)
            if unknown_ids:
                raise ValueError(
                    f"Ranking source contains an unknown session for {question_id}/{condition}"
                )
            if any(
                count > allowed_counts.get(session_id, 0)
                for session_id, count in ranked_counts.items()
            ):
                raise ValueError(
                    f"Ranking source session multiplicity exceeds the dataset for "
                    f"{question_id}/{condition}"
                )
        expected_recent = list(reversed(official["haystack_session_ids"]))[:candidate_k]
        if conditions["recent_session_order"]["ranked_session_ids"] != expected_recent:
            raise ValueError(f"Ranking source recent order differs from dataset: {question_id}")
        dense_ids = conditions["dense_chroma"]["ranked_session_ids"]
        salience_ids = conditions["uruha_salience_rerank"]["ranked_session_ids"]
        if Counter(dense_ids) != Counter(salience_ids):
            raise ValueError(
                f"Ranking source dense and salience candidate pools differ: {question_id}"
            )
        selected.append(official)
    if expected_count is not None and len(results) != expected_count:
        raise ValueError(
            f"Ranking source result count differs from its manifest: "
            f"{len(results)} != {expected_count}"
        )
    observed_ids_sha = canonical_sha256(
        [str(result.get("question_id") or "") for result in results]
    )
    if expected_ids_sha is not None and observed_ids_sha != expected_ids_sha:
        raise ValueError("Ranking source question ID manifest differs from its results")
    return selected


def mean_metrics(rows, condition):
    if not rows:
        return {}
    names = sorted(rows[0]["conditions"][condition]["metrics"])
    return {
        name: statistics.fmean(
            row["conditions"][condition]["metrics"][name] for row in rows
        )
        for name in names
    }


def aggregate_results(results):
    evaluated = [row for row in results if not row["abstention"]]
    summaries = {}
    for condition in CONDITIONS:
        by_split = {
            split: mean_metrics(
                [row for row in evaluated if row["split"] == split],
                condition,
            )
            for split in ("development", "test")
        }
        by_type = {
            question_type: mean_metrics(
                [
                    row
                    for row in evaluated
                    if row["question_type"] == question_type
                ],
                condition,
            )
            for question_type in sorted({row["question_type"] for row in evaluated})
        }
        summaries[condition] = {
            "overall": mean_metrics(evaluated, condition),
            "by_split": by_split,
            "by_question_type": by_type,
        }
    return summaries


def paired_binary_comparison(results, system, control, metric="recall_all@5"):
    rows = [row for row in results if not row["abstention"]]
    system_only = control_only = both_pass = both_fail = 0
    for row in rows:
        system_pass = bool(row["conditions"][system]["metrics"][metric])
        control_pass = bool(row["conditions"][control]["metrics"][metric])
        if system_pass and control_pass:
            both_pass += 1
        elif system_pass:
            system_only += 1
        elif control_pass:
            control_only += 1
        else:
            both_fail += 1
    discordant = system_only + control_only
    pvalue = (
        float(binomtest(system_only, discordant, p=0.5).pvalue)
        if discordant
        else 1.0
    )
    return {
        "system": system,
        "control": control,
        "metric": metric,
        "both_pass": both_pass,
        "system_only_pass": system_only,
        "control_only_pass": control_only,
        "both_fail": both_fail,
        "discordant_count": discordant,
        "exact_mcnemar_pvalue": pvalue,
        "paired_net_case_gain": system_only - control_only,
        "paired_rate_delta": (system_only - control_only) / len(rows) if rows else 0.0,
    }


def build_report(
    data_evidence,
    selected_rows,
    index_evidence,
    results,
    duration_seconds,
    *,
    candidate_k=20,
):
    evaluated = [row for row in results if not row["abstention"]]
    summaries = aggregate_results(results)
    dense_comparison = paired_binary_comparison(
        results,
        "uruha_salience_rerank",
        "dense_chroma",
    )
    recent_comparison = paired_binary_comparison(
        results,
        "uruha_salience_rerank",
        "recent_session_order",
    )
    if dense_comparison["paired_net_case_gain"] > 0:
        status = "salience_improves_dense_retrieval"
        decision_zh = "目前 Uruha salience 在官方題目上比相同 embedding 的 dense top-5 找回更多完整證據。"
    elif dense_comparison["paired_net_case_gain"] < 0:
        status = "salience_harms_dense_retrieval"
        decision_zh = "目前 Uruha salience 會把部分正確 dense 結果往後排；下一步應在 development split 修正注意力因子。"
    else:
        status = "salience_has_no_net_gain"
        decision_zh = "目前沒有證據顯示 Uruha salience 比相同 embedding 的 dense top-5 更好；先分析失敗類型再改演算法。"
    split_counts = Counter(row["split"] for row in evaluated)
    return {
        "generated_at": datetime.now(TZ).isoformat(timespec="seconds"),
        "scope": "longmemeval_s_cleaned_session_retrieval_matched_control_v1",
        "official_sources": {
            "repository": OFFICIAL_REPOSITORY,
            "repository_commit": OFFICIAL_REPOSITORY_COMMIT,
            "paper": OFFICIAL_PAPER,
            "dataset_url": DATASET_URL,
            "metric_source": OFFICIAL_METRIC_SOURCE,
            "license": "MIT",
        },
        "dataset_evidence": data_evidence,
        "dataset_inventory": {
            "selected_question_count": len(selected_rows),
            "selected_question_ids_sha256": canonical_sha256(
                [row["question_id"] for row in selected_rows]
            ),
            "evaluated_non_abstention_count": len(evaluated),
            "excluded_abstention_count": sum(row["abstention"] for row in results),
            "question_type_counts": dict(
                sorted(Counter(row["question_type"] for row in selected_rows).items())
            ),
            "split_counts_non_abstention": dict(sorted(split_counts.items())),
        },
        "preregistered_split": {
            "method": "sha256_salted_modulo_5",
            "salt": SPLIT_SALT,
            "development_fraction_target": 0.2,
            "answers_used_for_split": False,
        },
        "conditions": {
            "recent_session_order": "Most recent sessions only; no semantic retrieval.",
            "dense_chroma": "Current Chroma default embedding distance ranking.",
            "uruha_salience_rerank": (
                "Current Uruha attention_factors rerank over the same dense "
                f"top-{candidate_k} candidate pool."
            ),
        },
        "experiment_config": {
            "candidate_k": candidate_k,
            "working_memory_k": PRIMARY_K,
        },
        "document_mode": DOCUMENT_MODE,
        "primary_metric": "recall_all@5",
        "metric_definition": (
            "Exact reimplementation of LongMemEval session recall_any, recall_all, and nDCG. "
            "As in the official retrieval report, abstention questions are excluded."
        ),
        "index_evidence": index_evidence,
        "ranking_evidence": {
            "payload": "question_id_and_condition_ranked_session_ids_v1",
            "sha256": ranking_payload_sha256(results),
            "result_count": len(results),
        },
        "duration_seconds": round(duration_seconds, 3),
        "summaries": summaries,
        "paired_comparisons": {
            "uruha_vs_dense": dense_comparison,
            "uruha_vs_recent": recent_comparison,
        },
        "decision": {
            "status": status,
            "decision_zh": decision_zh,
            "authorize_memory_algorithm_change": False,
            "authorize_runtime_promotion": False,
        },
        "results": results,
        "research_boundary": (
            "This measures English session-level episodic retrieval, not final answer correctness, "
            "memory consolidation, privacy, personality, or complete dialogue quality. The public "
            "benchmark is used only for evaluation; no answer or has_answer label enters indexed text."
        ),
    }


def write_markdown(report, path):
    summaries = report["summaries"]
    comparison = report["paired_comparisons"]["uruha_vs_dense"]
    lines = [
        "# UruhaBrain × LongMemEval-S 官方記憶檢索基線",
        "",
        "## 結論",
        "",
        report["decision"]["decision_zh"],
        "",
        "## 實驗固定條件",
        "",
        f"- 官方 cleaned 資料：{report['dataset_evidence']['row_count']} 題，SHA `{report['dataset_evidence']['sha256']}`",
        f"- 實際 retrieval 評分：{report['dataset_inventory']['evaluated_non_abstention_count']} 題",
        f"- 依官方規則排除 abstention：{report['dataset_inventory']['excluded_abstention_count']} 題",
        "- 三組使用同一題目、同一 session 文字與同一 top-k；只有選擇規則不同。",
        "- 索引文字不含標準答案與 has_answer 標籤。",
        "",
        "## 官方來源",
        "",
        f"- LongMemEval repository（固定 commit）：{report['official_sources']['repository_commit']}",
        f"- 官方資料：{report['official_sources']['dataset_url']}",
        f"- 官方 retrieval 指標程式：{report['official_sources']['metric_source']}",
        f"- 論文：{report['official_sources']['paper']}",
        "",
        "## 三組條件",
        "",
        "| 條件 | 記憶選擇方式 |",
        "|---|---|",
        "| recent_session_order | 只取時間上最新的 session，不做語意檢索 |",
        "| dense_chroma | 用相同 Chroma embedding 直接排序 |",
        "| uruha_salience_rerank | 只把 Dense top-20 交給現行 Uruha attention/salience 重排 |",
        "",
        "## 主要結果",
        "",
        "| 條件 | recall all@5 | recall any@5 | nDCG@5 |",
        "|---|---:|---:|---:|",
    ]
    for condition in CONDITIONS:
        metrics = summaries[condition]["overall"]
        lines.append(
            f"| {condition} | {100 * metrics.get('recall_all@5', 0):.2f}% | "
            f"{100 * metrics.get('recall_any@5', 0):.2f}% | "
            f"{100 * metrics.get('ndcg_any@5', 0):.2f}% |"
        )
    lines.extend(
        [
            "",
            "## 單一部件效果",
            "",
            "`Uruha = dense top-20 + 現行 attention/salience 重排`",
            "",
            f"- Uruha 單獨答對：{comparison['system_only_pass']} 題",
            f"- Dense 單獨答對：{comparison['control_only_pass']} 題",
            f"- 淨差：{comparison['paired_net_case_gain']:+d} 題（{100 * comparison['paired_rate_delta']:+.2f} pp）",
            f"- exact McNemar p-value：{comparison['exact_mcnemar_pvalue']:.3e}",
            "",
            "## 預註冊 Split",
            "",
            "| Split | Dense recall all@5 | Uruha recall all@5 | 差值 |",
            "|---|---:|---:|---:|",
        ]
    )
    for split in ("development", "test"):
        dense = summaries["dense_chroma"]["by_split"][split].get(
            "recall_all@5", 0.0
        )
        uruha = summaries["uruha_salience_rerank"]["by_split"][split].get(
            "recall_all@5", 0.0
        )
        lines.append(
            f"| {split} | {100 * dense:.2f}% | {100 * uruha:.2f}% | {100 * (uruha - dense):+.2f} pp |"
        )
    lines.extend(
        [
            "",
            "## 各能力類型 recall all@5",
            "",
            "| 類型 | dense | Uruha | 差值 |",
            "|---|---:|---:|---:|",
        ]
    )
    types = summaries["dense_chroma"]["by_question_type"]
    for question_type in types:
        dense = summaries["dense_chroma"]["by_question_type"][question_type].get(
            "recall_all@5", 0.0
        )
        uruha = summaries["uruha_salience_rerank"]["by_question_type"][
            question_type
        ].get("recall_all@5", 0.0)
        lines.append(
            f"| {question_type} | {100 * dense:.2f}% | {100 * uruha:.2f}% | {100 * (uruha - dense):+.2f} pp |"
        )
    lines.extend(
        [
            "",
            "## 證據邊界",
            "",
            "這只測英文、session-level 的 episodic retrieval，不是最終回答正確率，也不代表記憶鞏固、隱私、人格或完整聊天品質。索引文字沒有放入標準答案或 has_answer 標籤。",
            "",
            "本報告不授權修改或升級 runtime；下一輪只能在 development split 分析與修改，完成後才可一次性檢查 test split。",
            "",
        ]
    )
    Path(path).write_text("\n".join(lines), encoding="utf-8")


def write_report_outputs(report, output_json, output_md):
    atomic_write_json(output_json, report)
    Path(output_md).parent.mkdir(parents=True, exist_ok=True)
    write_markdown(report, output_md)


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default=LONGMEMEVAL_S_CLEANED_DATASET_PATH)
    parser.add_argument("--cache-dir", default=LONGMEMEVAL_CHROMA_CACHE_DIR)
    parser.add_argument("--output-json", default=LONGMEMEVAL_RETRIEVAL_REPORT_JSON_PATH)
    parser.add_argument("--output-md", default=LONGMEMEVAL_RETRIEVAL_REPORT_MD_PATH)
    parser.add_argument("--download", action="store_true")
    parser.add_argument("--rebuild-index", action="store_true")
    parser.add_argument("--recompute-from-report")
    parser.add_argument("--max-items", type=int, default=0)
    parser.add_argument("--candidate-k", type=int, default=20)
    parser.add_argument("--seed", type=int, default=20260712)
    parser.add_argument("--batch-size", type=int, default=64)
    args = parser.parse_args(argv)

    if args.candidate_k < max(METRIC_KS):
        raise ValueError(
            f"candidate-k must be at least {max(METRIC_KS)} because @20 is reported"
        )
    dataset_path = Path(args.dataset)
    if not dataset_path.is_file():
        if not args.download:
            print(
                json.dumps(
                    {
                        "status": "dataset_missing",
                        "dataset": str(dataset_path),
                        "download_url": DATASET_URL,
                    },
                    indent=2,
                )
            )
            return 2
        download_official_dataset(dataset_path)

    data, data_evidence = load_and_validate_dataset(dataset_path)
    if args.recompute_from_report:
        recompute_started = time.time()
        source_path = Path(args.recompute_from_report)
        source_sha = file_sha256(source_path)
        source_report = json.loads(source_path.read_text(encoding="utf-8"))
        if source_report.get("dataset_evidence", {}).get("sha256") != data_evidence[
            "sha256"
        ]:
            raise ValueError("Ranking source report does not bind the current dataset SHA")
        source_candidate_k = source_report.get("experiment_config", {}).get(
            "candidate_k"
        )
        if not isinstance(source_candidate_k, int) or source_candidate_k < max(METRIC_KS):
            raise ValueError("Ranking source report has an invalid candidate-k manifest")
        source_inventory = source_report.get("dataset_inventory") or {}
        expected_count = source_inventory.get("selected_question_count")
        expected_ids_sha = source_inventory.get("selected_question_ids_sha256")
        if not isinstance(expected_count, int) or not expected_ids_sha:
            raise ValueError("Ranking source report has an incomplete dataset manifest")
        source_results = source_report.get("results") or []
        expected_ranking_sha = (source_report.get("ranking_evidence") or {}).get(
            "sha256"
        )
        if (
            expected_ranking_sha is not None
            and ranking_payload_sha256(source_results) != expected_ranking_sha
        ):
            raise ValueError("Ranking source payload differs from its SHA manifest")
        selected = validate_ranking_results_against_dataset(
            source_results,
            data,
            candidate_k=source_candidate_k,
            expected_count=expected_count,
            expected_ids_sha=expected_ids_sha,
        )
        rebuilt_results = recompute_results_from_rankings(source_results)
        index_evidence = dict(source_report.get("index_evidence") or {})
        index_evidence.update(
            {
                "ranking_source_report": str(source_path.resolve()),
                "ranking_source_report_sha256": source_sha,
                "metric_recomputed_without_chroma": True,
                "persistent_reuse_attempted": False,
            }
        )
        report = build_report(
            data_evidence,
            selected,
            index_evidence,
            rebuilt_results,
            time.time() - recompute_started,
            candidate_k=source_candidate_k,
        )
        write_report_outputs(report, args.output_json, args.output_md)
        print(
            json.dumps(
                {
                    "status": "metrics_recomputed_from_bound_rankings",
                    "source_report_sha256": source_sha,
                    "evaluated": report["dataset_inventory"][
                        "evaluated_non_abstention_count"
                    ],
                    "runtime_promotion": False,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    selected = select_rows(data, args.max_items, args.seed)
    started = time.time()
    collection, index_evidence = prepare_chroma_index(
        selected,
        data_evidence["sha256"],
        args.cache_dir,
        rebuild=args.rebuild_index,
        batch_size=args.batch_size,
    )
    results = []
    for index, row in enumerate(selected, start=1):
        results.append(evaluate_item(collection, row, args.candidate_k))
        if index % 25 == 0 or index == len(selected):
            print(f"evaluated={index}/{len(selected)}")
    report = build_report(
        data_evidence,
        selected,
        index_evidence,
        results,
        time.time() - started,
        candidate_k=args.candidate_k,
    )
    write_report_outputs(report, args.output_json, args.output_md)
    print(
        json.dumps(
            {
                "status": report["decision"]["status"],
                "evaluated": report["dataset_inventory"][
                    "evaluated_non_abstention_count"
                ],
                "uruha_recall_all_at_5": report["summaries"][
                    "uruha_salience_rerank"
                ]["overall"]["recall_all@5"],
                "dense_recall_all_at_5": report["summaries"]["dense_chroma"][
                    "overall"
                ]["recall_all@5"],
                "runtime_promotion": False,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
