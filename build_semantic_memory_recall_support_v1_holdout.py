#!/usr/bin/env python3
"""Build and freeze the official-derived semantic recall holdout."""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import subprocess
from pathlib import Path

from project_paths import LONGMEMEVAL_S_CLEANED_DATASET_PATH
from run_longmemeval_evidence_ledger_development import ollama_chat, ollama_model_evidence
from run_longmemeval_retrieval_benchmark import (
    canonical_sha256,
    file_sha256,
    load_and_validate_dataset,
    preregistered_split,
    session_document,
)


ROOT = Path(__file__).resolve().parent
PREREG = ROOT / "configs/semantic_memory_recall_support_v1_holdout_preregistration.json"
OUTPUT = ROOT / "configs/semantic_memory_recall_support_v1_holdout_cases.json"
SELECTION_SALT = "uruha-semantic-memory-recall-support-v1-holdout"
MODEL = "qwen2.5:7b"
SEED = 2026080502
OLLAMA_ENDPOINT = "http://localhost:11434/api/chat"

STOPWORDS = frozenset(
    {
        "a",
        "about",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "but",
        "by",
        "did",
        "do",
        "does",
        "for",
        "from",
        "had",
        "has",
        "have",
        "he",
        "her",
        "his",
        "how",
        "i",
        "in",
        "is",
        "it",
        "me",
        "my",
        "of",
        "on",
        "or",
        "she",
        "that",
        "the",
        "their",
        "them",
        "they",
        "this",
        "to",
        "was",
        "were",
        "what",
        "when",
        "where",
        "which",
        "who",
        "why",
        "with",
        "you",
        "your",
    }
)

TRANSLATION_SCHEMA = {
    "type": "object",
    "properties": {
        "question": {"type": "string"},
        "target_text": {"type": "string"},
        "hard_negative_text": {"type": "string"},
        "replacement_text": {"type": "string"},
    },
    "required": [
        "question",
        "target_text",
        "hard_negative_text",
        "replacement_text",
    ],
}

REPLACEMENT_SCHEMA = {
    "type": "object",
    "properties": {"replacement_text": {"type": "string"}},
    "required": ["replacement_text"],
}


def content_tokens(text):
    return {
        token
        for token in re.findall(r"[a-z0-9][a-z0-9_-]*", str(text or "").lower())
        if token not in STOPWORDS and len(token) > 1
    }


def lexical_overlap(query, document):
    query_tokens = content_tokens(query)
    document_tokens = content_tokens(document)
    if not query_tokens or not document_tokens:
        return 0.0
    return len(query_tokens & document_tokens) / math.sqrt(
        len(query_tokens) * len(document_tokens)
    )


def selection_digest(question_id):
    return hashlib.sha256(f"{SELECTION_SALT}:{question_id}".encode("utf-8")).hexdigest()


def eligible_rows(data):
    rows = [
        row
        for row in data
        if row.get("question_type") == "single-session-user"
        and not str(row.get("question_id") or "").endswith("_abs")
        and len(row.get("answer_session_ids") or []) == 1
        and preregistered_split(row["question_id"]) == "test"
    ]
    rows.sort(key=lambda row: selection_digest(row["question_id"]))
    return rows[:8]


def hard_negative_session(row):
    candidates = []
    answer_ids = set(row["answer_session_ids"])
    for session_id, timestamp, session in zip(
        row["haystack_session_ids"],
        row["haystack_dates"],
        row["haystack_sessions"],
    ):
        if session_id in answer_ids:
            continue
        document = session_document(session, timestamp)
        tie = hashlib.sha256(
            f"{SELECTION_SALT}:{row['question_id']}:{session_id}".encode("utf-8")
        ).hexdigest()
        candidates.append(
            {
                "session_id": session_id,
                "timestamp": timestamp,
                "session": session,
                "document": document,
                "independent_overlap": lexical_overlap(row["question"], document),
                "tie": tie,
            }
        )
    if not candidates:
        raise ValueError(f"No non-answer session for {row['question_id']}")
    candidates.sort(key=lambda item: (-item["independent_overlap"], item["tie"]))
    return candidates[0]


def relevant_excerpt(session, timestamp, question, answer=None, max_turns=8):
    query_tokens = content_tokens(question)
    answer_text = json.dumps(answer, ensure_ascii=False).strip('"').lower()
    ranked = []
    for index, turn in enumerate(session):
        content = re.sub(r"\s+", " ", str(turn.get("content") or "")).strip()
        if not content:
            continue
        overlap = len(query_tokens & content_tokens(content))
        answer_hit = bool(answer_text and answer_text in content.lower())
        ranked.append((int(answer_hit), overlap, index, turn.get("role"), content))
    ranked.sort(key=lambda item: (-item[0], -item[1], item[2]))
    selected_indices = sorted(item[2] for item in ranked[:max_turns])
    lines = [f"Time: {timestamp}"]
    for index in selected_indices:
        turn = session[index]
        role = "User" if turn.get("role") == "user" else "Assistant"
        content = re.sub(r"\s+", " ", str(turn.get("content") or "")).strip()
        lines.append(f"{role}: {content[:900]}")
    return "\n".join(lines)


def target_session(row):
    target_id = row["answer_session_ids"][0]
    index = row["haystack_session_ids"].index(target_id)
    return {
        "session_id": target_id,
        "timestamp": row["haystack_dates"][index],
        "session": row["haystack_sessions"][index],
    }


def generation_prompt(language, question, target_text, hard_negative_text):
    if language == "English":
        instruction = (
            "Keep question, target_text, and hard_negative_text exactly unchanged. "
            "Write replacement_text as a faithful English paraphrase of target_text."
        )
    else:
        instruction = (
            f"Translate question, target_text, and hard_negative_text into {language}. "
            f"Write replacement_text as a faithful {language} paraphrase of the translated "
            "target_text. Preserve every fact, name, number, and uncertainty."
        )
    return (
        "Create one controlled memory-recall evaluation row. "
        f"{instruction} Do not answer the question, add facts, or omit facts.\n\n"
        f"question:\n{question}\n\n"
        f"target_text:\n{target_text}\n\n"
        f"hard_negative_text:\n{hard_negative_text}"
    )


def generate_language_row(language, question, target_text, hard_negative_text):
    retry_response = None
    if language == "English":
        prompt = (
            "Faithfully paraphrase the following English memory transcript. Preserve every "
            "fact, name, number, role, and uncertainty. Do not answer a question or add facts.\n\n"
            f"target_text:\n{target_text}"
        )
        response = ollama_chat(
            prompt,
            model=MODEL,
            seed=SEED,
            max_tokens=1600,
            format_schema=REPLACEMENT_SCHEMA,
        )
        generated = json.loads(response["text"])
        payload = {
            "question": question,
            "target_text": target_text,
            "hard_negative_text": hard_negative_text,
            "replacement_text": str(generated.get("replacement_text") or "").strip(),
        }
    else:
        response = ollama_chat(
            generation_prompt(language, question, target_text, hard_negative_text),
            model=MODEL,
            seed=SEED,
            max_tokens=2400,
            format_schema=TRANSLATION_SCHEMA,
        )
        payload = json.loads(response["text"])
    for field in TRANSLATION_SCHEMA["required"]:
        if not str(payload.get(field) or "").strip():
            raise ValueError(f"Construction model returned empty {field}")
    if language == "English" and (
        payload["question"] != question
        or payload["target_text"] != target_text
        or payload["hard_negative_text"] != hard_negative_text
    ):
        raise ValueError("English construction did not preserve official-derived text")
    if payload["replacement_text"].strip() == payload["target_text"].strip():
        retry_response = ollama_chat(
            (
                f"Rewrite the following {language} memory transcript using different wording "
                "and sentence structure. Preserve every fact, name, number, role, and "
                "uncertainty. The output must not be identical to the input.\n\n"
                f"target_text:\n{payload['target_text']}"
            ),
            model=MODEL,
            seed=SEED,
            max_tokens=1600,
            format_schema=REPLACEMENT_SCHEMA,
        )
        replacement = json.loads(retry_response["text"])
        payload["replacement_text"] = str(
            replacement.get("replacement_text") or ""
        ).strip()
    if not payload["replacement_text"] or (
        payload["replacement_text"].strip() == payload["target_text"].strip()
    ):
        raise ValueError("Replacement is not a distinct paraphrase after retry")
    return payload, {
        "latency_seconds": round(
            float(response.get("latency_seconds") or 0.0)
            + float((retry_response or {}).get("latency_seconds") or 0.0),
            3,
        ),
        "prompt_tokens": int(response.get("prompt_tokens") or 0)
        + int((retry_response or {}).get("prompt_tokens") or 0),
        "completion_tokens": int(response.get("completion_tokens") or 0)
        + int((retry_response or {}).get("completion_tokens") or 0),
        "paraphrase_retry_used": retry_response is not None,
    }


def run_preflight():
    command = [
        os.environ.get("PYTHON", os.sys.executable),
        "-m",
        "unittest",
        "-q",
        "test_semantic_memory_recall_support_v1_holdout_preregistration.py",
        "test_build_semantic_memory_recall_support_v1_holdout.py",
    ]
    completed = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
        env={**os.environ, "URUHA_SKIP_AUTO_VENV": "1"},
    )
    if completed.returncode:
        raise SystemExit(f"holdout builder preflight failed:\n{completed.stdout}\n{completed.stderr}")
    return {"passed": True, "tests": command[4:]}


def main():
    if OUTPUT.exists():
        raise SystemExit("Frozen holdout already exists; refusing to overwrite")
    prereg = json.loads(PREREG.read_text(encoding="utf-8"))
    preflight = run_preflight()
    model_evidence = ollama_model_evidence(MODEL, OLLAMA_ENDPOINT)
    if model_evidence["digest"] != prereg["frozen_construction"]["construction_model_digest"]:
        raise SystemExit("construction model digest drift")
    data, data_evidence = load_and_validate_dataset(LONGMEMEVAL_S_CLEANED_DATASET_PATH)
    rows = eligible_rows(data)
    if len(rows) != prereg["frozen_selection"]["selected_question_count"]:
        raise SystemExit("eligible holdout count drift")

    languages = ["English"] * 4 + ["Japanese"] * 2 + ["Traditional Chinese"] * 2
    cases = []
    generations = []
    for index, (row, language) in enumerate(zip(rows, languages), start=1):
        target = target_session(row)
        negative = hard_negative_session(row)
        target_text = relevant_excerpt(
            target["session"],
            target["timestamp"],
            row["question"],
            row["answer"],
        )
        hard_negative_text = relevant_excerpt(
            negative["session"],
            negative["timestamp"],
            row["question"],
        )
        print(f"[{index}/8] construct {language} row {row['question_id']}", flush=True)
        generated, generation = generate_language_row(
            language,
            row["question"],
            target_text,
            hard_negative_text,
        )
        cases.append(
            {
                "case_id": f"official-{index:02d}-{row['question_id']}",
                "official_question_id": row["question_id"],
                "official_question_type": row["question_type"],
                "language": language,
                "question": generated["question"],
                "official_answer": row["answer"],
                "target": {
                    "trace_id": f"holdout:{row['question_id']}:target",
                    "official_session_id": target["session_id"],
                    "text": generated["target_text"],
                    "score": prereg["fixed_scores"]["target"],
                },
                "hard_negative": {
                    "trace_id": f"holdout:{row['question_id']}:hard-negative",
                    "official_session_id": negative["session_id"],
                    "text": generated["hard_negative_text"],
                    "score": prereg["fixed_scores"]["hard_negative"],
                    "independent_overlap": round(negative["independent_overlap"], 6),
                },
                "replacement": {
                    "trace_id": f"holdout:{row['question_id']}:replacement",
                    "text": generated["replacement_text"],
                    "score": prereg["fixed_scores"]["replacement"],
                },
            }
        )
        generations.append({"case_id": cases[-1]["case_id"], **generation})

    payload = {
        "schema": "uruha_semantic_memory_recall_support_holdout_cases_v1",
        "status": "frozen_before_evaluation",
        "source": data_evidence,
        "official_sources": prereg["official_source"],
        "selection": prereg["frozen_selection"],
        "construction": {
            "model": model_evidence,
            "seed": SEED,
            "temperature": 0.0,
            "preflight": preflight,
            "builder_commit": subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
            ).strip(),
            "builder_sha256": file_sha256(__file__),
            "preregistration_sha256": file_sha256(PREREG),
            "generation_diagnostics": generations,
        },
        "case_count": len(cases),
        "case_ids_sha256": canonical_sha256([case["case_id"] for case in cases]),
        "cases": cases,
    }
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(OUTPUT), "sha256": file_sha256(OUTPUT)}, indent=2))


if __name__ == "__main__":
    main()
