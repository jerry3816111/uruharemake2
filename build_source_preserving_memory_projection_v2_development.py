#!/usr/bin/env python3
"""Build source-preserving LongMemEval development cases without model calls."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

from audit_semantic_memory_recall_support_v1_evidence_contract import (
    content_tokens,
    file_sha256,
    load_dataset,
)
from project_paths import LONGMEMEVAL_S_CLEANED_DATASET_PATH


ROOT = Path(__file__).resolve().parent
PREREG = ROOT / "configs/source_preserving_memory_projection_v2_development_preregistration.json"
V1_CASES = ROOT / "configs/semantic_memory_recall_support_v1_holdout_cases.json"
OUTPUT = ROOT / "configs/source_preserving_memory_projection_v2_development_cases.json"
FEASIBILITY_REPORT_JSON = ROOT / "reports/source_preserving_memory_projection_v2_construction_feasibility.json"
FEASIBILITY_REPORT_MD = ROOT / "reports/source_preserving_memory_projection_v2_construction_feasibility.md"
FEASIBILITY_LOCK = ROOT / "configs/source_preserving_memory_projection_v2_construction_feasibility_lock.json"
SELECTION_SALT = "uruha-source-preserving-memory-projection-v2-development"
SPLIT_SALT = "uruha-longmemeval-retrieval-v1"
TARGET_SCORE = 0.9
HARD_NEGATIVE_SCORE = 0.82


def canonical_sha256(value):
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def preregistered_split(question_id):
    digest = hashlib.sha256(f"{SPLIT_SALT}:{question_id}".encode("utf-8")).digest()
    return "development" if int.from_bytes(digest[:4], "big") % 5 == 0 else "test"


def selection_digest(question_id):
    return hashlib.sha256(f"{SELECTION_SALT}:{question_id}".encode("utf-8")).hexdigest()


def turn_payload(index, turn):
    return {
        "source_turn_index": index,
        "role": str(turn.get("role") or ""),
        "content": str(turn.get("content") or ""),
    }


def serialized_turn(turn):
    role = "User" if turn["role"] == "user" else "Assistant"
    return f"{role}: {turn['content']}"


def serialize_turns(timestamp, turns):
    return "\n".join([f"Time: {timestamp}", *(serialized_turn(turn) for turn in turns)])


def complete_representation(session, timestamp):
    turns = [turn_payload(index, turn) for index, turn in enumerate(session)]
    text = serialize_turns(timestamp, turns)
    return {
        "text": text,
        "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "source_turn_count": len(turns),
        "source_turn_sha256_list": [canonical_sha256(turn) for turn in turns],
        "source_turn_indices": [turn["source_turn_index"] for turn in turns],
    }


def projection_representation(session, timestamp, question, top_k=3):
    question_tokens = content_tokens(question)
    ranked = []
    for index, raw_turn in enumerate(session):
        turn = turn_payload(index, raw_turn)
        if turn["role"] != "user" or not turn["content"]:
            continue
        overlap = len(question_tokens & content_tokens(turn["content"]))
        ranked.append((-overlap, index, turn))
    ranked.sort(key=lambda item: (item[0], item[1]))
    selected = sorted((item[2] for item in ranked[:top_k]), key=lambda turn: turn["source_turn_index"])
    text = serialize_turns(timestamp, selected)
    return {
        "text": text,
        "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "source_turn_count": len(selected),
        "source_turn_sha256_list": [canonical_sha256(turn) for turn in selected],
        "source_turn_indices": [turn["source_turn_index"] for turn in selected],
        "top_k": top_k,
    }


def lexical_overlap(question, text):
    question_tokens = content_tokens(question)
    text_tokens = content_tokens(text)
    if not question_tokens or not text_tokens:
        return 0.0
    return len(question_tokens & text_tokens) / math.sqrt(len(question_tokens) * len(text_tokens))


def source_session(row, session_id):
    index = row["haystack_session_ids"].index(session_id)
    return {
        "session_id": session_id,
        "timestamp": row["haystack_dates"][index],
        "session": row["haystack_sessions"][index],
    }


def answer_in_user_turn(session, answer):
    answer = str(answer).casefold()
    return any(
        turn.get("role") == "user" and answer in str(turn.get("content") or "").casefold()
        for turn in session
    )


def choose_hard_negative(row, maximum_characters):
    answer = str(row["answer"]).casefold()
    answer_ids = set(row["answer_session_ids"])
    candidates = []
    for session_id, timestamp, session in zip(
        row["haystack_session_ids"], row["haystack_dates"], row["haystack_sessions"]
    ):
        if session_id in answer_ids:
            continue
        complete = complete_representation(session, timestamp)
        if len(complete["text"]) > maximum_characters:
            continue
        if answer in complete["text"].casefold():
            continue
        tie = hashlib.sha256(
            f"{SELECTION_SALT}:{row['question_id']}:{session_id}".encode("utf-8")
        ).hexdigest()
        candidates.append(
            {
                "session_id": session_id,
                "timestamp": timestamp,
                "session": session,
                "complete": complete,
                "overlap": lexical_overlap(row["question"], complete["text"]),
                "tie": tie,
            }
        )
    if not candidates:
        return None
    candidates.sort(key=lambda item: (-item["overlap"], item["tie"]))
    return candidates[0]


def eligible_case(row, excluded_ids, prereg):
    selection = prereg["case_selection"]
    size = selection["source_size_rules"]
    question_id = str(row.get("question_id") or "")
    if (
        question_id in excluded_ids
        or row.get("question_type") != selection["question_type"]
        or question_id.endswith("_abs")
        or len(row.get("answer_session_ids") or []) != 1
        or preregistered_split(question_id) != selection["required_existing_split"]
        or not isinstance(row.get("answer"), str)
        or not row["answer"].strip()
    ):
        return None
    target = source_session(row, row["answer_session_ids"][0])
    target_complete = complete_representation(target["session"], target["timestamp"])
    if len(target_complete["text"]) > size["maximum_target_characters"]:
        return None
    if not answer_in_user_turn(target["session"], row["answer"]):
        return None
    negative = choose_hard_negative(row, size["maximum_hard_negative_characters"])
    if negative is None:
        return None
    if len(target_complete["text"]) + len(negative["complete"]["text"]) > size[
        "maximum_combined_visible_characters"
    ]:
        return None
    return {"row": row, "target": target, "target_complete": target_complete, "negative": negative}


def select_cases(data, excluded_ids, prereg):
    eligible = []
    for row in data:
        candidate = eligible_case(row, excluded_ids, prereg)
        if candidate is not None:
            eligible.append(candidate)
    eligible.sort(key=lambda item: selection_digest(item["row"]["question_id"]))
    return eligible[: prereg["case_selection"]["question_count"]], len(eligible)


def eligibility_diagnostics(data, excluded_ids, prereg):
    selection = prereg["case_selection"]
    size = selection["source_size_rules"]
    counts = Counter()
    eligible_ids = []
    for row in data:
        question_id = str(row.get("question_id") or "")
        if question_id in excluded_ids:
            counts["excluded_v1"] += 1
            continue
        if row.get("question_type") != selection["question_type"]:
            counts["wrong_question_type"] += 1
            continue
        if question_id.endswith("_abs"):
            counts["abstention"] += 1
            continue
        if len(row.get("answer_session_ids") or []) != 1:
            counts["answer_session_count_not_one"] += 1
            continue
        if preregistered_split(question_id) != selection["required_existing_split"]:
            counts["development_split"] += 1
            continue
        if not isinstance(row.get("answer"), str) or not row["answer"].strip():
            counts["answer_not_nonempty_string"] += 1
            continue
        target = source_session(row, row["answer_session_ids"][0])
        target_complete = complete_representation(target["session"], target["timestamp"])
        if not answer_in_user_turn(target["session"], row["answer"]):
            counts["answer_not_exact_in_user_turn"] += 1
            continue
        if len(target_complete["text"]) > size["maximum_target_characters"]:
            counts["target_over_character_limit"] += 1
            continue
        negative = choose_hard_negative(row, size["maximum_hard_negative_characters"])
        if negative is None:
            counts["no_hard_negative_under_contract"] += 1
            continue
        if len(target_complete["text"]) + len(negative["complete"]["text"]) > size[
            "maximum_combined_visible_characters"
        ]:
            counts["combined_over_character_limit"] += 1
            continue
        counts["eligible"] += 1
        eligible_ids.append(question_id)
    eligible_ids.sort(key=selection_digest)
    return dict(counts), eligible_ids


def write_feasibility_failure(prereg, source_evidence, preflight, counts, eligible_ids):
    report = {
        "schema": "uruha_source_preserving_memory_projection_construction_feasibility_v2",
        "experiment_id": prereg["experiment_id"],
        "status": "construction_infeasible_locked",
        "decision": "do_not_build_or_run_model",
        "source": source_evidence,
        "frozen_limits": prereg["case_selection"]["source_size_rules"],
        "required_case_count": prereg["case_selection"]["question_count"],
        "eligible_case_count": counts.get("eligible", 0),
        "eligible_question_ids": eligible_ids,
        "sequential_exclusion_counts": counts,
        "root_cause": "The preregistered 7,000-character target-session ceiling is incompatible with this LongMemEval task population; 39 otherwise preceding candidates exceed that target limit and only one case remains eligible.",
        "model_calls": 0,
        "case_file_written": False,
        "preflight": preflight,
        "authorization": {
            "runtime_change": False,
            "production_enablement": False,
            "model_evaluation": False,
            "reuse_as_holdout": False,
            "new_preregistration_changing_only_context_limits": True,
        },
        "evidence_boundary": "This result tests construction feasibility only. It says nothing about memory projection quality or model capability.",
    }
    FEASIBILITY_REPORT_JSON.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    FEASIBILITY_REPORT_MD.write_text(
        "\n".join(
            [
                "# Source-preserving Memory Projection V2 建構可行性",
                "",
                "## 結論",
                "",
                "固定規格下只有 1 題符合條件，少於預註冊的 8 題，因此沒有建立 cases，也沒有呼叫模型。",
                "",
                f"- 需要題數：{report['required_case_count']}",
                f"- 實際可用：{report['eligible_case_count']}",
                f"- target 超過 7,000 字：{counts.get('target_over_character_limit', 0)}",
                f"- 模型呼叫：{report['model_calls']}",
                "",
                "主要原因不是資料不足，而是 LongMemEval 的完整 Session 通常大於事前假設。下一版只能重新預註冊 context 上限，不能直接修改這次已凍結的規格。",
                "",
                "本結果不評價記憶投影好壞，也不授權 runtime 修改。",
                "",
            ]
        ),
        encoding="utf-8",
    )
    lock = {
        "schema": "uruha_source_preserving_memory_projection_construction_feasibility_lock_v2",
        "experiment_id": prereg["experiment_id"],
        "status": report["status"],
        "decision": report["decision"],
        "required_case_count": report["required_case_count"],
        "eligible_case_count": report["eligible_case_count"],
        "model_calls": 0,
        "artifacts": {
            path.relative_to(ROOT).as_posix(): file_sha256(path)
            for path in (
                Path(__file__),
                PREREG,
                V1_CASES,
                FEASIBILITY_REPORT_JSON,
                FEASIBILITY_REPORT_MD,
            )
        },
        "authorization": report["authorization"],
        "next_required_step": "Create a new preregistration changing only source character limits, justified by the locked size distribution; keep projection, model, prompts, metrics, and gates unchanged.",
        "evidence_boundary": report["evidence_boundary"],
    }
    FEASIBILITY_LOCK.write_text(
        json.dumps(lock, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return lock


def record_payload(question_id, kind, source, complete, projection, score):
    return {
        "trace_id": f"source-v2:{question_id}:{kind}",
        "official_session_id": source["session_id"],
        "score": score,
        "complete_session": complete,
        "source_projection": projection,
    }


def build_case(item):
    row = item["row"]
    target = item["target"]
    negative = item["negative"]
    target_projection = projection_representation(
        target["session"], target["timestamp"], row["question"]
    )
    negative_projection = projection_representation(
        negative["session"], negative["timestamp"], row["question"]
    )
    return {
        "case_id": f"source-v2-{row['question_id']}",
        "official_question_id": row["question_id"],
        "official_question_type": row["question_type"],
        "question": row["question"],
        "official_answer": row["answer"],
        "target": record_payload(
            row["question_id"],
            "target",
            target,
            item["target_complete"],
            target_projection,
            TARGET_SCORE,
        ),
        "hard_negative": record_payload(
            row["question_id"],
            "hard-negative",
            negative,
            negative["complete"],
            negative_projection,
            HARD_NEGATIVE_SCORE,
        ),
    }


def run_preflight():
    command = [
        sys.executable,
        "-m",
        "unittest",
        "-q",
        "test_source_preserving_memory_projection_v2_development_preregistration.py",
        "test_build_source_preserving_memory_projection_v2_development.py",
    ]
    completed = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
    if completed.returncode:
        raise SystemExit(f"Builder preflight failed:\n{completed.stdout}\n{completed.stderr}")
    return {"passed": True, "tests": command[4:]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--overwrite-feasibility", action="store_true")
    args = parser.parse_args()
    if OUTPUT.exists():
        raise SystemExit("Frozen V2 development cases already exist; refusing to overwrite")
    feasibility_outputs = (
        FEASIBILITY_REPORT_JSON,
        FEASIBILITY_REPORT_MD,
        FEASIBILITY_LOCK,
    )
    if not args.overwrite_feasibility and any(path.exists() for path in feasibility_outputs):
        raise SystemExit(
            "Frozen construction-feasibility result already exists; refusing to overwrite"
        )
    prereg = json.loads(PREREG.read_text(encoding="utf-8"))
    v1_cases = json.loads(V1_CASES.read_text(encoding="utf-8"))
    if file_sha256(V1_CASES) != prereg["prior_invalidity_evidence"]["v1_cases"]["sha256"]:
        raise SystemExit("V1 exclusion artifact hash drift")
    data, source_evidence = load_dataset(LONGMEMEVAL_S_CLEANED_DATASET_PATH)
    if source_evidence["sha256"] != prereg["official_source"]["dataset_sha256"]:
        raise SystemExit("Official source dataset hash drift")
    excluded_ids = {case["official_question_id"] for case in v1_cases["cases"]}
    preflight = run_preflight()
    selected, eligible_count = select_cases(data, excluded_ids, prereg)
    if len(selected) != prereg["case_selection"]["question_count"]:
        counts, eligible_ids = eligibility_diagnostics(data, excluded_ids, prereg)
        lock = write_feasibility_failure(
            prereg, source_evidence, preflight, counts, eligible_ids
        )
        print(json.dumps(lock, ensure_ascii=False, indent=2))
        raise SystemExit(2)
    cases = [build_case(item) for item in selected]
    payload = {
        "schema": "uruha_source_preserving_memory_projection_development_cases_v2",
        "status": "frozen_before_model_evaluation",
        "experiment_id": prereg["experiment_id"],
        "data_status": prereg["why_this_is_not_a_holdout"]["status"],
        "source": source_evidence,
        "selection": {
            **prereg["case_selection"],
            "eligible_count": eligible_count,
            "selected_question_ids_sha256": canonical_sha256(
                [case["official_question_id"] for case in cases]
            ),
        },
        "construction": {
            "model_calls": 0,
            "builder_sha256": file_sha256(__file__),
            "preregistration_sha256": file_sha256(PREREG),
            "v1_exclusion_artifact_sha256": file_sha256(V1_CASES),
            "preflight": preflight,
        },
        "case_count": len(cases),
        "case_ids_sha256": canonical_sha256([case["case_id"] for case in cases]),
        "cases": cases,
        "authorization": prereg["decision_and_authorization"],
    }
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "output": str(OUTPUT),
                "sha256": file_sha256(OUTPUT),
                "selected_question_ids": [case["official_question_id"] for case in cases],
                "eligible_count": eligible_count,
                "model_calls": 0,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
