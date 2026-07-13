#!/usr/bin/env python3
"""Development-only LongMemEval QA comparison for memory evidence integration."""

import argparse
import datetime
import json
import math
import statistics
import time
import urllib.request
from pathlib import Path

import run_longmemeval_retrieval_benchmark as retrieval_benchmark_module
import run_longmemeval_salience_development as salience_development_module
import uruha_memory_runtime as memory_runtime_module
from memory_evidence_ledger import (
    EVIDENCE_NOTE_SCHEMA,
    LEDGER_JSON_SCHEMA,
    QUESTION_FRAME_SCHEMA,
    build_direct_answer_prompt,
    build_evidence_note_prompt,
    build_focused_evidence_note_prompt,
    build_ledger_answer_prompt,
    build_ledger_prompt,
    build_notes_answer_prompt,
    build_question_frame_prompt,
    chronological_sessions,
    align_fact_to_source,
    augment_question_frame,
    audit_question_frame,
    evidence_quotes_are_grounded,
    filter_grounded_evidence,
    focused_user_utterances,
    ground_ledger_events,
    parse_evidence_note,
    parse_ledger,
    parse_question_frame,
    reconcile_ledger_state,
    strict_answer_support,
)
from project_paths import (
    LONGMEMEVAL_DEVELOPMENT_CANDIDATE_CACHE_PATH,
    LONGMEMEVAL_EVIDENCE_LEDGER_DEVELOPMENT_REPORT_JSON_PATH,
    LONGMEMEVAL_EVIDENCE_LEDGER_DEVELOPMENT_REPORT_MD_PATH,
    LONGMEMEVAL_RETRIEVAL_REPORT_JSON_PATH,
    LONGMEMEVAL_S_CLEANED_DATASET_PATH,
)
from run_longmemeval_retrieval_benchmark import (
    OFFICIAL_REPOSITORY,
    OFFICIAL_REPOSITORY_COMMIT,
    SPLIT_SALT,
    atomic_write_json,
    canonical_sha256,
    file_sha256,
    load_and_validate_dataset,
    preregistered_split,
)
from run_longmemeval_salience_development import (
    benchmark_reference_time,
    rank_runtime_v2,
    validate_candidate_cache,
)


SCOPE = "longmemeval_evidence_ledger_development_only_v3"
CONDITIONS = ("direct_chronological", "grounded_notes", "versioned_ledger")
TARGET_TASK = "knowledge-update"
DEFAULT_MODEL = "qwen2.5:7b"
DEFAULT_SEED = 20260713
NUM_CTX = 32768
ANSWER_MAX_TOKENS = 220
QUESTION_FRAME_MAX_TOKENS = 300
EVIDENCE_NOTE_MAX_TOKENS = 700
LEDGER_MAX_TOKENS = 900
JUDGE_MAX_TOKENS = 10
REQUEST_TIMEOUT_SECONDS = 900
OFFICIAL_GENERATION_SOURCE = (
    "https://github.com/xiaowu0162/LongMemEval/blob/"
    f"{OFFICIAL_REPOSITORY_COMMIT}/src/generation/run_generation.py"
)
OFFICIAL_EVALUATION_SOURCE = (
    "https://github.com/xiaowu0162/LongMemEval/blob/"
    f"{OFFICIAL_REPOSITORY_COMMIT}/src/evaluation/evaluate_qa.py"
)
OLLAMA_STRUCTURED_OUTPUT_SOURCE = "https://docs.ollama.com/capabilities/structured-outputs"


def ollama_chat(
    prompt,
    *,
    model=DEFAULT_MODEL,
    endpoint="http://localhost:11434/api/chat",
    seed=DEFAULT_SEED,
    num_ctx=NUM_CTX,
    max_tokens=ANSWER_MAX_TOKENS,
    timeout=REQUEST_TIMEOUT_SECONDS,
    format_schema=None,
):
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "options": {
            "temperature": 0,
            "seed": seed,
            "num_ctx": num_ctx,
            "num_predict": max_tokens,
        },
    }
    if format_schema is not None:
        payload["format"] = format_schema
    request = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    started = time.time()
    with urllib.request.urlopen(request, timeout=timeout) as response:
        result = json.load(response)
    return {
        "text": str((result.get("message") or {}).get("content") or "").strip(),
        "latency_seconds": round(time.time() - started, 3),
        "prompt_tokens": result.get("prompt_eval_count"),
        "completion_tokens": result.get("eval_count"),
    }


def ollama_model_evidence(model, endpoint):
    """Bind a mutable Ollama model tag to the local digest used by the run."""
    if "/api/" not in endpoint:
        raise ValueError(f"Unsupported Ollama endpoint: {endpoint}")
    tags_endpoint = endpoint.split("/api/", 1)[0] + "/api/tags"
    with urllib.request.urlopen(tags_endpoint, timeout=30) as response:
        payload = json.load(response)
    for item in payload.get("models") or []:
        if model in {item.get("name"), item.get("model")}:
            digest = str(item.get("digest") or "")
            if not digest:
                raise ValueError(f"Ollama model has no digest: {model}")
            return {
                "name": str(item.get("name") or model),
                "digest": digest,
                "size": item.get("size"),
                "modified_at": item.get("modified_at"),
            }
    raise ValueError(f"Ollama model is not installed: {model}")


def current_implementation_evidence():
    """Hash every local module that can change selection, generation, or scoring."""
    return {
        "ledger_module_sha256": file_sha256(
            Path(__file__).with_name("memory_evidence_ledger.py")
        ),
        "runner_sha256": file_sha256(__file__),
        "retrieval_benchmark_module_sha256": file_sha256(
            Path(retrieval_benchmark_module.__file__).resolve()
        ),
        "salience_development_module_sha256": file_sha256(
            Path(salience_development_module.__file__).resolve()
        ),
        "memory_runtime_module_sha256": file_sha256(
            Path(memory_runtime_module.__file__).resolve()
        ),
        "schemas_sha256": canonical_sha256(
            {
                "question_frame": QUESTION_FRAME_SCHEMA,
                "evidence_note": EVIDENCE_NOTE_SCHEMA,
                "ledger": LEDGER_JSON_SCHEMA,
            }
        ),
    }


def official_style_judge_prompt(question, answer, response):
    return (
        "I will give you a question, a correct answer, and a response from a model. "
        "Please answer yes if the response contains the correct answer. Otherwise, answer no. "
        "If the response contains some previous information along with an updated answer, the "
        "response should be considered as correct as long as the updated answer is the required "
        "answer.\n\n"
        f"Question: {question}\n\nCorrect Answer: {answer}\n\nModel Response: {response}\n\n"
        "Is the model response correct? Answer yes or no only."
    )


def local_diagnostic_judge(question, answer, response, chat):
    if not str(response or "").strip():
        return {
            "text": "No",
            "latency_seconds": 0.0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "label": False,
            "scoring_guard": "empty_response",
        }
    result = chat(
        official_style_judge_prompt(question, answer, response),
        max_tokens=JUDGE_MAX_TOKENS,
    )
    result["label"] = result["text"].strip().lower().startswith("yes")
    return result


def load_rows(max_items=0):
    data, data_evidence = load_and_validate_dataset(LONGMEMEVAL_S_CLEANED_DATASET_PATH)
    baseline_report = json.loads(
        Path(LONGMEMEVAL_RETRIEVAL_REPORT_JSON_PATH).read_text(encoding="utf-8")
    )
    cache = json.loads(
        Path(LONGMEMEVAL_DEVELOPMENT_CANDIDATE_CACHE_PATH).read_text(encoding="utf-8")
    )
    validate_candidate_cache(cache, data, baseline_report)
    references = {row["question_id"]: row for row in data}
    rows = []
    for cached in cache.get("rows") or []:
        question_id = cached.get("question_id")
        reference = references.get(question_id)
        if not reference or reference.get("question_type") != TARGET_TASK:
            continue
        if preregistered_split(question_id) != "development" or question_id.endswith("_abs"):
            raise ValueError("Runner attempted to cross the development data boundary")
        rows.append({**cached, "answer": reference["answer"]})
    rows.sort(key=lambda row: row["question_id"])
    if max_items:
        rows = rows[:max_items]
    return rows, data_evidence, cache, baseline_report


def selected_sessions(row, top_k, wall_now):
    ranked = rank_runtime_v2(
        row["candidates"],
        row["question"],
        wall_now,
    )[:top_k]
    return chronological_sessions(
        [
            {
                "session_id": item["metadata"]["benchmark_session_id"],
                "timestamp": item["metadata"]["timestamp"],
                "text": item["text"],
            }
            for item in ranked
        ]
    )


def generate_question_frame(row, chat):
    result = chat(
        build_question_frame_prompt(row["question"], row["question_date"]),
        max_tokens=QUESTION_FRAME_MAX_TOKENS,
        format_schema=QUESTION_FRAME_SCHEMA,
    )
    parsed = parse_question_frame(result["text"])
    audited = audit_question_frame(row["question"], parsed)
    return result, augment_question_frame(audited)


def generate_notes(row, sessions, question_frame, chat):
    if question_frame is None:
        return []
    notes = []
    for session in sessions:
        primary_result = chat(
            build_evidence_note_prompt(
                row["question"],
                row["question_date"],
                question_frame,
                session,
            ),
            max_tokens=EVIDENCE_NOTE_MAX_TOKENS,
            format_schema=EVIDENCE_NOTE_SCHEMA,
        )
        result = primary_result
        parsed_evidence = parse_evidence_note(result["text"])
        evidence = (
            filter_grounded_evidence(parsed_evidence, session["text"])
            if parsed_evidence is not None
            else None
        )
        focused_text = focused_user_utterances(
            row["question"], question_frame, session["text"]
        )
        retry_result = None
        attention_retry_used = False
        if not ((evidence or {}).get("facts")) and focused_text:
            focused_session = {**session, "text": focused_text}
            retry_result = chat(
                build_focused_evidence_note_prompt(question_frame, focused_session["text"]),
                max_tokens=EVIDENCE_NOTE_MAX_TOKENS,
                format_schema=EVIDENCE_NOTE_SCHEMA,
            )
            retry_parsed = parse_evidence_note(retry_result["text"])
            retry_evidence = (
                filter_grounded_evidence(retry_parsed, session["text"])
                if retry_parsed is not None
                else None
            )
            if (retry_evidence or {}).get("facts"):
                result = retry_result
                parsed_evidence = retry_parsed
                evidence = retry_evidence
                attention_retry_used = True
        schema_parse_ok = parsed_evidence is not None
        extracted_fact_count = len((parsed_evidence or {}).get("facts") or [])
        accepted_grounded_fact_count = len((evidence or {}).get("facts") or [])
        rejected_ungrounded_fact_count = (
            extracted_fact_count - accepted_grounded_fact_count
        )
        alignments = [
            align_fact_to_source(
                fact.get("quote"), session["text"], fact.get("source_role")
            )
            for fact in (parsed_evidence or {}).get("facts") or []
        ]
        quote_alignment_repair_count = sum(
            bool(alignment and alignment["quote_repaired"])
            for alignment in alignments
        )
        role_alignment_repair_count = sum(
            bool(alignment and alignment["role_repaired"])
            for alignment in alignments
        )
        quote_grounded = bool(
            schema_parse_ok
            and evidence_quotes_are_grounded(parsed_evidence, session["text"])
        )
        fact_source_offsets = [
            session["text"].find(fact["quote"])
            for fact in (evidence or {}).get("facts") or []
        ]
        notes.append(
            {
                "session_id": session["session_id"],
                "timestamp": session["timestamp"],
                "evidence": evidence,
                "fact_source_offsets": fact_source_offsets,
                "schema_parse_ok": schema_parse_ok,
                "quote_grounded": quote_grounded,
                "structured_parse_ok": schema_parse_ok,
                "extracted_fact_count": extracted_fact_count,
                "accepted_grounded_fact_count": accepted_grounded_fact_count,
                "rejected_ungrounded_fact_count": rejected_ungrounded_fact_count,
                "quote_alignment_repair_count": quote_alignment_repair_count,
                "role_alignment_repair_count": role_alignment_repair_count,
                "attention_retry_attempted": retry_result is not None,
                "attention_retry_used": attention_retry_used,
                "primary_generation": primary_result,
                "retry_generation": retry_result,
                "generation": result,
            }
        )
    return notes


def note_extraction_latency(notes):
    total = 0.0
    for note in notes:
        if "primary_generation" in note:
            generations = (note.get("primary_generation"), note.get("retry_generation"))
        else:
            generations = (note.get("generation"),)
        total += sum(
            float((generation or {}).get("latency_seconds") or 0.0)
            for generation in generations
        )
    return total


def generate_condition(
    row,
    sessions,
    condition,
    chat,
    *,
    question_frame=None,
    frame_generation=None,
    shared_notes=None,
):
    started = time.time()
    if condition == "direct_chronological":
        answer = chat(
            build_direct_answer_prompt(
                row["question"], row["question_date"], sessions
            )
        )
        artifacts = {"answer_generation": answer}
    else:
        notes = (
            shared_notes
            if shared_notes is not None
            else generate_notes(row, sessions, question_frame, chat)
        )
        if question_frame is None or not all(
            note.get("structured_parse_ok") for note in notes
        ):
            answer = {"text": "", "latency_seconds": 0.0}
            artifacts = {
                "question_frame": question_frame,
                "frame_generation": frame_generation,
                "notes": notes,
                "answer_generation": answer,
            }
        elif condition == "grounded_notes":
            answer = chat(
                build_notes_answer_prompt(
                    row["question"],
                    row["question_date"],
                    question_frame,
                    notes,
                )
            )
            artifacts = {
                "question_frame": question_frame,
                "frame_generation": frame_generation,
                "notes": notes,
                "answer_generation": answer,
            }
        elif condition == "versioned_ledger":
            ledger_generation = chat(
                build_ledger_prompt(
                    row["question"],
                    row["question_date"],
                    question_frame,
                    notes,
                ),
                max_tokens=LEDGER_MAX_TOKENS,
                format_schema=LEDGER_JSON_SCHEMA,
            )
            parsed_ledger = parse_ledger(ledger_generation["text"])
            ledger_schema_parse_ok = parsed_ledger is not None
            grounded_ledger = (
                ground_ledger_events(parsed_ledger, notes)
                if ledger_schema_parse_ok
                else None
            )
            ledger_grounded = grounded_ledger is not None
            ledger = reconcile_ledger_state(grounded_ledger)
            if ledger is None:
                answer = {"text": "", "latency_seconds": 0.0}
            else:
                answer = chat(
                    build_ledger_answer_prompt(
                        row["question"],
                        row["question_date"],
                        ledger,
                        question_frame,
                    )
                )
            artifacts = {
                "question_frame": question_frame,
                "frame_generation": frame_generation,
                "notes": notes,
                "ledger_generation": ledger_generation,
                "ledger": ledger,
                "ledger_schema_parse_ok": ledger_schema_parse_ok,
                "ledger_grounded": ledger_grounded,
                "answer_generation": answer,
            }
        else:
            raise ValueError(f"Unknown condition: {condition}")
    artifacts["response"] = answer["text"]
    artifacts["strict_answer_support"] = strict_answer_support(
        row["answer"], answer["text"], question=row["question"]
    )
    query_latency = round(time.time() - started, 3)
    extraction_latency = (
        note_extraction_latency(artifacts.get("notes") or [])
        if condition != "direct_chronological"
        else 0.0
    )
    frame_latency = (
        float((artifacts.get("frame_generation") or {}).get("latency_seconds") or 0.0)
        if condition != "direct_chronological"
        else 0.0
    )
    artifacts["query_latency_seconds"] = query_latency
    artifacts["question_frame_latency_seconds"] = round(frame_latency, 3)
    artifacts["note_extraction_latency_seconds"] = round(extraction_latency, 3)
    artifacts["end_to_end_latency_seconds"] = round(
        query_latency + frame_latency + extraction_latency,
        3,
    )
    return artifacts


def summarize(results):
    summary = {}
    for condition in CONDITIONS:
        rows = [row["conditions"][condition] for row in results]
        strict = [bool(row["strict_answer_support"]) for row in rows]
        judged = [bool((row.get("local_judge") or {}).get("label")) for row in rows]
        query_latencies = [
            float(row.get("query_latency_seconds") or 0.0) for row in rows
        ]
        end_to_end_latencies = [
            float(row.get("end_to_end_latency_seconds") or 0.0) for row in rows
        ]
        ledger_included_fact_count = sum(
            len((row.get("ledger") or {}).get("events") or []) for row in rows
        )
        ledger_omitted_fact_count = sum(
            len((row.get("ledger") or {}).get("omitted_grounded_facts") or [])
            for row in rows
        )
        summary[condition] = {
            "case_count": len(rows),
            "strict_answer_support_rate": sum(strict) / len(strict) if strict else 0.0,
            "local_diagnostic_judge_rate": sum(judged) / len(judged) if judged else 0.0,
            "mean_query_latency_seconds": (
                statistics.fmean(query_latencies) if query_latencies else 0.0
            ),
            "mean_end_to_end_latency_seconds": (
                statistics.fmean(end_to_end_latencies) if end_to_end_latencies else 0.0
            ),
            "median_end_to_end_latency_seconds": (
                statistics.median(end_to_end_latencies) if end_to_end_latencies else 0.0
            ),
            "ledger_parse_rate": (
                sum(row.get("ledger") is not None for row in rows) / len(rows)
                if condition == "versioned_ledger" and rows
                else None
            ),
            "ledger_schema_parse_rate": (
                sum(bool(row.get("ledger_schema_parse_ok")) for row in rows)
                / len(rows)
                if condition == "versioned_ledger" and rows
                else None
            ),
            "ledger_grounding_rate": (
                sum(bool(row.get("ledger_grounded")) for row in rows) / len(rows)
                if condition == "versioned_ledger" and rows
                else None
            ),
            "ledger_included_grounded_fact_count": (
                ledger_included_fact_count
                if condition == "versioned_ledger"
                else None
            ),
            "ledger_omitted_grounded_fact_count": (
                ledger_omitted_fact_count
                if condition == "versioned_ledger"
                else None
            ),
            "ledger_fact_coverage_rate": (
                ledger_included_fact_count
                / (ledger_included_fact_count + ledger_omitted_fact_count)
                if condition == "versioned_ledger"
                and (ledger_included_fact_count + ledger_omitted_fact_count)
                else (1.0 if condition == "versioned_ledger" else None)
            ),
            "question_frame_parse_rate": (
                sum(row.get("question_frame") is not None for row in rows) / len(rows)
                if condition != "direct_chronological" and rows
                else None
            ),
            "all_note_parse_rate": (
                sum(
                    bool(row.get("notes"))
                    and all(note.get("structured_parse_ok") for note in row["notes"])
                    for row in rows
                )
                / len(rows)
                if condition != "direct_chronological" and rows
                else None
            ),
            "all_note_schema_parse_rate": (
                sum(
                    bool(row.get("notes"))
                    and all(note.get("schema_parse_ok") for note in row["notes"])
                    for row in rows
                )
                / len(rows)
                if condition != "direct_chronological" and rows
                else None
            ),
            "all_quote_grounding_rate": (
                sum(
                    bool(row.get("notes"))
                    and all(note.get("quote_grounded") for note in row["notes"])
                    for row in rows
                )
                / len(rows)
                if condition != "direct_chronological" and rows
                else None
            ),
            "extracted_fact_count": (
                sum(
                    sum(
                        int(note.get("extracted_fact_count") or 0)
                        for note in row.get("notes") or []
                    )
                    for row in rows
                )
                if condition != "direct_chronological"
                else None
            ),
            "accepted_grounded_fact_count": (
                sum(
                    sum(
                        int(note.get("accepted_grounded_fact_count") or 0)
                        for note in row.get("notes") or []
                    )
                    for row in rows
                )
                if condition != "direct_chronological"
                else None
            ),
            "rejected_ungrounded_fact_count": (
                sum(
                    sum(
                        int(note.get("rejected_ungrounded_fact_count") or 0)
                        for note in row.get("notes") or []
                    )
                    for row in rows
                )
                if condition != "direct_chronological"
                else None
            ),
            "quote_alignment_repair_count": (
                sum(
                    sum(
                        int(note.get("quote_alignment_repair_count") or 0)
                        for note in row.get("notes") or []
                    )
                    for row in rows
                )
                if condition != "direct_chronological"
                else None
            ),
            "role_alignment_repair_count": (
                sum(
                    sum(
                        int(note.get("role_alignment_repair_count") or 0)
                        for note in row.get("notes") or []
                    )
                    for row in rows
                )
                if condition != "direct_chronological"
                else None
            ),
            "attention_retry_attempted_count": (
                sum(
                    sum(
                        bool(note.get("attention_retry_attempted"))
                        for note in row.get("notes") or []
                    )
                    for row in rows
                )
                if condition != "direct_chronological"
                else None
            ),
            "attention_retry_used_count": (
                sum(
                    sum(
                        bool(note.get("attention_retry_used"))
                        for note in row.get("notes") or []
                    )
                    for row in rows
                )
                if condition != "direct_chronological"
                else None
            ),
            "ledger_quote_alignment_repair_count": (
                sum(
                    len(
                        (row.get("ledger") or {}).get(
                            "ledger_quote_alignment_repairs"
                        )
                        or []
                    )
                    for row in rows
                )
                if condition == "versioned_ledger"
                else None
            ),
            "ledger_role_alignment_repair_count": (
                sum(
                    len(
                        (row.get("ledger") or {}).get(
                            "ledger_role_alignment_repairs"
                        )
                        or []
                    )
                    for row in rows
                )
                if condition == "versioned_ledger"
                else None
            ),
            "ledger_semantic_repair_count": (
                sum(
                    len((row.get("ledger") or {}).get("semantic_repairs") or [])
                    for row in rows
                )
                if condition == "versioned_ledger"
                else None
            ),
            "ledger_derived_numeric_conflict_count": (
                sum(
                    len(
                        (row.get("ledger") or {}).get(
                            "derived_numeric_conflicts"
                        )
                        or []
                    )
                    for row in rows
                )
                if condition == "versioned_ledger"
                else None
            ),
        }
    return summary


def exact_mcnemar_two_sided_p(ledger_wins, ledger_losses):
    """Exact two-sided McNemar p-value for paired binary outcomes."""
    discordant = ledger_wins + ledger_losses
    if discordant == 0:
        return 1.0
    tail = sum(
        math.comb(discordant, index)
        for index in range(min(ledger_wins, ledger_losses) + 1)
    ) / (2**discordant)
    return min(1.0, 2.0 * tail)


def paired_binary_analysis(results, metric):
    if metric not in {"strict_answer_support", "local_judge"}:
        raise ValueError(f"Unsupported paired metric: {metric}")

    def value(condition):
        if metric == "strict_answer_support":
            return bool(condition.get(metric))
        return bool((condition.get("local_judge") or {}).get("label"))

    counts = {
        "both_correct": 0,
        "ledger_wins": 0,
        "ledger_losses": 0,
        "both_wrong": 0,
    }
    for row in results:
        direct = value(row["conditions"]["direct_chronological"])
        ledger = value(row["conditions"]["versioned_ledger"])
        if direct and ledger:
            counts["both_correct"] += 1
        elif not direct and ledger:
            counts["ledger_wins"] += 1
        elif direct and not ledger:
            counts["ledger_losses"] += 1
        else:
            counts["both_wrong"] += 1
    counts["net_ledger_wins"] = counts["ledger_wins"] - counts["ledger_losses"]
    counts["discordant_pairs"] = counts["ledger_wins"] + counts["ledger_losses"]
    counts["exact_mcnemar_two_sided_p"] = exact_mcnemar_two_sided_p(
        counts["ledger_wins"], counts["ledger_losses"]
    )
    return counts


def retrieval_conditioned_summary(results):
    evidence_available = [
        row for row in results if row.get("all_gold_sessions_retrieved") is True
    ]
    rates = {}
    for condition in CONDITIONS:
        condition_rows = [row["conditions"][condition] for row in evidence_available]
        rates[condition] = {
            "case_count": len(condition_rows),
            "strict_answer_support_rate": (
                sum(bool(row.get("strict_answer_support")) for row in condition_rows)
                / len(condition_rows)
                if condition_rows
                else None
            ),
            "local_diagnostic_judge_rate": (
                sum(
                    bool((row.get("local_judge") or {}).get("label"))
                    for row in condition_rows
                )
                / len(condition_rows)
                if condition_rows
                else None
            ),
        }
    return {
        "all_gold_sessions_retrieved_count": len(evidence_available),
        "all_gold_sessions_retrieved_rate": (
            len(evidence_available) / len(results) if results else 0.0
        ),
        "condition_rates_when_evidence_available": rates,
    }


def inference_token_diagnostics(results):
    stages = {
        "direct_answer": [],
        "question_frame": [],
        "evidence_note": [],
        "grounded_answer": [],
        "ledger_build": [],
        "ledger_answer": [],
        "local_judge": [],
    }

    def add(stage, generation):
        if not isinstance(generation, dict):
            return
        prompt_tokens = generation.get("prompt_tokens")
        completion_tokens = generation.get("completion_tokens")
        if isinstance(prompt_tokens, int) and isinstance(completion_tokens, int):
            stages[stage].append(
                {
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                }
            )

    for result in results:
        conditions = result["conditions"]
        direct = conditions["direct_chronological"]
        grounded = conditions["grounded_notes"]
        ledger = conditions["versioned_ledger"]
        add("direct_answer", direct.get("answer_generation"))
        add("question_frame", grounded.get("frame_generation"))
        for note in grounded.get("notes") or []:
            if "primary_generation" in note:
                add("evidence_note", note.get("primary_generation"))
                add("evidence_note", note.get("retry_generation"))
            else:
                add("evidence_note", note.get("generation"))
        add("grounded_answer", grounded.get("answer_generation"))
        add("ledger_build", ledger.get("ledger_generation"))
        add("ledger_answer", ledger.get("answer_generation"))
        for condition in CONDITIONS:
            add("local_judge", conditions[condition].get("local_judge"))

    summaries = {}
    all_calls = []
    for stage, calls in stages.items():
        all_calls.extend(calls)
        summaries[stage] = {
            "observed_call_count": len(calls),
            "max_prompt_tokens": max(
                (call["prompt_tokens"] for call in calls), default=None
            ),
            "max_completion_tokens": max(
                (call["completion_tokens"] for call in calls), default=None
            ),
        }
    max_observed_total = max(
        (
            call["prompt_tokens"] + call["completion_tokens"]
            for call in all_calls
        ),
        default=None,
    )
    return {
        "num_ctx": NUM_CTX,
        "observed_call_count": len(all_calls),
        "max_observed_total_tokens": max_observed_total,
        "minimum_observed_context_headroom_tokens": (
            NUM_CTX - max_observed_total if max_observed_total is not None else None
        ),
        "stages": summaries,
    }


def build_report(
    rows,
    results,
    data_evidence,
    cache,
    baseline_report,
    model,
    seed,
    top_k,
    development_population_question_count,
    model_evidence,
):
    summaries = summarize(results)
    direct = summaries["direct_chronological"]
    ledger = summaries["versioned_ledger"]
    strict_delta = (
        ledger["strict_answer_support_rate"] - direct["strict_answer_support_rate"]
    )
    judge_delta = (
        ledger["local_diagnostic_judge_rate"] - direct["local_diagnostic_judge_rate"]
    )
    complete = len(results) == len(rows) and all(
        set(row.get("conditions") or {}) == set(CONDITIONS) for row in results
    )
    development_population_complete = bool(
        complete
        and len(rows) == development_population_question_count
        and len(results) == development_population_question_count
    )
    paired_analysis = {
        "strict_answer_support": paired_binary_analysis(
            results, "strict_answer_support"
        ),
        "local_diagnostic_judge": paired_binary_analysis(results, "local_judge"),
    }
    authorize_test_evaluation = bool(
        development_population_complete
        and strict_delta > 0
        and judge_delta > 0
        and paired_analysis["strict_answer_support"]["net_ledger_wins"] > 0
        and paired_analysis["local_diagnostic_judge"]["net_ledger_wins"] > 0
        and ledger["ledger_parse_rate"] == 1.0
        and ledger["ledger_schema_parse_rate"] == 1.0
        and ledger["ledger_grounding_rate"] == 1.0
        and ledger["question_frame_parse_rate"] == 1.0
        and ledger["all_note_parse_rate"] == 1.0
        and ledger["all_note_schema_parse_rate"] == 1.0
    )
    if not development_population_complete:
        decision_zh = (
            f"目前只完成 development population 的 {len(results)}/"
            f"{development_population_question_count} 題，僅能作為 pilot，不授權 test 或 runtime。"
        )
    elif authorize_test_evaluation:
        decision_zh = (
            "完整 development 診斷通過；只授權一次凍結後 held-out test，"
            "不授權正式 runtime 修改。"
        )
    else:
        decision_zh = (
            "完整 development 診斷未通過預設閘門，不授權 test 或 runtime。"
        )
    return {
        "scope": SCOPE,
        "generated_at": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
        "research_sources": {
            "repository": OFFICIAL_REPOSITORY,
            "repository_commit": OFFICIAL_REPOSITORY_COMMIT,
            "generation_method": OFFICIAL_GENERATION_SOURCE,
            "evaluation_method": OFFICIAL_EVALUATION_SOURCE,
            "structured_output_method": OLLAMA_STRUCTURED_OUTPUT_SOURCE,
        },
        "data_boundary": {
            "dataset_path": str(Path(LONGMEMEVAL_S_CLEANED_DATASET_PATH).resolve()),
            "dataset_sha256": data_evidence["sha256"],
            "candidate_cache_path": str(
                Path(LONGMEMEVAL_DEVELOPMENT_CANDIDATE_CACHE_PATH).resolve()
            ),
            "candidate_cache_sha256": file_sha256(
                LONGMEMEVAL_DEVELOPMENT_CANDIDATE_CACHE_PATH
            ),
            "candidate_cache_schema": cache.get("schema"),
            "baseline_report_sha256": file_sha256(
                LONGMEMEVAL_RETRIEVAL_REPORT_JSON_PATH
            ),
            "ranking_reference_time": benchmark_reference_time(
                baseline_report
            ).isoformat(timespec="seconds"),
            "split_salt": SPLIT_SALT,
            "split": "development",
            "task": TARGET_TASK,
            "development_population_question_count": development_population_question_count,
            "development_population_complete": development_population_complete,
            "development_coverage_rate": (
                len(results) / development_population_question_count
                if development_population_question_count
                else 0.0
            ),
            "test_question_count_evaluated": 0,
            "selected_question_ids_sha256": canonical_sha256(
                [row["question_id"] for row in rows]
            ),
        },
        "matched_control": {
            "fixed": [
                "qwen reader",
                "temperature=0",
                "seed",
                "v2 top-k retrieved sessions",
                "chronological session order",
                "question set",
                "local diagnostic judge prompt",
                "Ollama JSON schemas",
            ],
            "independent_variable": "post-retrieval evidence integration method",
            "conditions": list(CONDITIONS),
            "top_k": top_k,
            "model": model,
            "model_evidence": model_evidence,
            "seed": seed,
            "generation_options": {
                "temperature": 0,
                "num_ctx": NUM_CTX,
                "request_timeout_seconds": REQUEST_TIMEOUT_SECONDS,
                "max_tokens": {
                    "answer": ANSWER_MAX_TOKENS,
                    "question_frame": QUESTION_FRAME_MAX_TOKENS,
                    "evidence_note": EVIDENCE_NOTE_MAX_TOKENS,
                    "ledger": LEDGER_MAX_TOKENS,
                    "judge": JUDGE_MAX_TOKENS,
                },
            },
            "minimum_generation_calls_per_answer": {
                "direct_chronological": 1,
                "grounded_notes": 2 + top_k,
                "versioned_ledger": 3 + top_k,
            },
        },
        "question_count": len(rows),
        "completed_question_count": len(results),
        "complete": complete,
        "summaries": summaries,
        "paired_strict_delta_ledger_minus_direct": strict_delta,
        "paired_local_judge_delta_ledger_minus_direct": judge_delta,
        "paired_analysis": paired_analysis,
        "retrieval_conditioning": retrieval_conditioned_summary(results),
        "inference_token_diagnostics": inference_token_diagnostics(results),
        "results_sha256": canonical_sha256(results),
        "implementation_evidence": current_implementation_evidence(),
        "results": results,
        "decision": {
            "authorize_test_evaluation": authorize_test_evaluation,
            "authorize_runtime_change": False,
            "decision_zh": decision_zh,
        },
        "research_boundary": (
            "The official dataset, task split, top-k memories, reader model, temperature, seed, "
            "and judging prompt are fixed. The local Qwen judge is diagnostic only and must not "
            "be reported as official LongMemEval accuracy. Gold answers are used only after "
            "generation for scoring and never appear in reader prompts."
        ),
    }


def write_markdown(report, path):
    boundary = report["data_boundary"]
    model_evidence = report["matched_control"]["model_evidence"]
    lines = [
        "# LongMemEval 記憶證據整合 Development 實驗",
        "",
        f"- 範圍：`{report['scope']}`",
        f"- 題型：`{TARGET_TASK}`",
        f"- 題數：{report['completed_question_count']}/{report['question_count']}",
        (
            "- Development population 覆蓋："
            f"{report['completed_question_count']}/"
            f"{boundary['development_population_question_count']} "
            f"({100 * boundary['development_coverage_rate']:.1f}%)"
        ),
        "- 測試集使用：0 題",
        f"- 模型 digest：`{model_evidence['digest']}`",
        "- 注意：本機 Qwen judge 只是診斷，不是官方 LongMemEval 分數。",
        "",
        "## 結果",
        "",
        "| 條件 | 嚴格答案支持率 | 本機診斷 judge | 查詢延遲 | 端到端延遲 | Frame | Note JSON | Quote 來源 | Ledger JSON | Ledger 來源 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for condition in CONDITIONS:
        values = report["summaries"][condition]
        ledger_schema_rate = values["ledger_schema_parse_rate"]
        ledger_grounding_rate = values["ledger_grounding_rate"]
        frame_rate = values["question_frame_parse_rate"]
        note_schema_rate = values["all_note_schema_parse_rate"]
        quote_grounding_rate = values["all_quote_grounding_rate"]
        lines.append(
            f"| {condition} | {100 * values['strict_answer_support_rate']:.1f}% | "
            f"{100 * values['local_diagnostic_judge_rate']:.1f}% | "
            f"{values['mean_query_latency_seconds']:.1f}s | "
            f"{values['mean_end_to_end_latency_seconds']:.1f}s | "
            f"{'-' if frame_rate is None else f'{100 * frame_rate:.1f}%'} | "
            f"{'-' if note_schema_rate is None else f'{100 * note_schema_rate:.1f}%'} | "
            f"{'-' if quote_grounding_rate is None else f'{100 * quote_grounding_rate:.1f}%'} | "
            f"{'-' if ledger_schema_rate is None else f'{100 * ledger_schema_rate:.1f}%'} | "
            f"{'-' if ledger_grounding_rate is None else f'{100 * ledger_grounding_rate:.1f}%'} |"
        )
    ledger_values = report["summaries"]["versioned_ledger"]
    lines.extend(
        [
            "",
            (
                "- 抽取 facts："
                f"{ledger_values['extracted_fact_count']}；逐字來源驗證通過："
                f"{ledger_values['accepted_grounded_fact_count']}；拒絕且未進入 ledger："
                f"{ledger_values['rejected_ungrounded_fact_count']}。"
            ),
            (
                "- Ledger 採用/省略已驗證 facts："
                f"{ledger_values['ledger_included_grounded_fact_count']}/"
                f"{ledger_values['ledger_omitted_grounded_fact_count']}；coverage="
                f"{100 * ledger_values['ledger_fact_coverage_rate']:.1f}%。"
                "此 coverage 僅報告資訊壓縮程度，不作為任意通過門檻；"
                "所有實際採用事件仍必須逐字對應來源。"
            ),
            (
                "- 僅引號標點等價並回填原文："
                f"{ledger_values['quote_alignment_repair_count']} 次。"
            ),
            (
                "- Note 來源角色回填："
                f"{ledger_values['role_alignment_repair_count']} 次；"
                "聚焦重試嘗試/採用："
                f"{ledger_values['attention_retry_attempted_count']}/"
                f"{ledger_values['attention_retry_used_count']} 次。"
            ),
            (
                "- Note→Ledger 引號/角色回填："
                f"{ledger_values['ledger_quote_alignment_repair_count']}/"
                f"{ledger_values['ledger_role_alignment_repair_count']} 次。"
            ),
            (
                "- Ledger 內部一致性修復："
                f"{ledger_values['ledger_semantic_repair_count']} 次；修復規則不讀取 gold answer。"
            ),
            (
                "- 衍生數字與逐字來源衝突："
                f"{ledger_values['ledger_derived_numeric_conflict_count']} 次；"
                "衍生 claim/value 已隔離，不會送進回答 prompt。"
            ),
        ]
    )
    retrieval = report["retrieval_conditioning"]
    lines.extend(
        [
            "",
            "## Retrieval 分層",
            "",
            (
                "- Top-k 已包含全部 gold sessions："
                f"{retrieval['all_gold_sessions_retrieved_count']}/"
                f"{report['completed_question_count']} "
                f"({100 * retrieval['all_gold_sessions_retrieved_rate']:.1f}%)"
            ),
            "",
            "| 條件 | 證據已取回題數 | 嚴格答案支持率 | 本機診斷 judge |",
            "|---|---:|---:|---:|",
        ]
    )
    for condition in CONDITIONS:
        values = retrieval["condition_rates_when_evidence_available"][condition]
        strict_rate = values["strict_answer_support_rate"]
        judge_rate = values["local_diagnostic_judge_rate"]
        lines.append(
            f"| {condition} | {values['case_count']} | "
            f"{'-' if strict_rate is None else f'{100 * strict_rate:.1f}%'} | "
            f"{'-' if judge_rate is None else f'{100 * judge_rate:.1f}%'} |"
        )
    lines.extend(
        [
            "",
            "## 成對差異",
            "",
            "| 指標 | Ledger 修正 | Ledger 弄錯 | 淨增 | Exact McNemar p |",
            "|---|---:|---:|---:|---:|",
        ]
    )
    for label, key in (
        ("嚴格答案支持", "strict_answer_support"),
        ("本機診斷 judge", "local_diagnostic_judge"),
    ):
        paired = report["paired_analysis"][key]
        lines.append(
            f"| {label} | {paired['ledger_wins']} | {paired['ledger_losses']} | "
            f"{paired['net_ledger_wins']:+d} | "
            f"{paired['exact_mcnemar_two_sided_p']:.4f} |"
        )
    lines.extend(
        [
            "",
            "## 因果邊界",
            "",
            "三組固定同一模型、同一題、同一批 v2 top-k 記憶與時間順序；唯一變因是檢索後如何整合證據。",
            "Gold answer 只在生成後評分使用，不會放進回答 prompt。",
            (
                "單題獨立執行時，direct 至少需 1 次生成、notes 至少需 "
                f"{2 + report['matched_control']['top_k']} 次、ledger 需 "
                f"{3 + report['matched_control']['top_k']} 次；聚焦重試會增加呼叫，"
                "延遲成本必須與正確率一起判斷。"
            ),
            (
                "實際單次呼叫最大 token 使用為 "
                f"{report['inference_token_diagnostics']['max_observed_total_tokens']} / "
                f"{NUM_CTX}，最小觀察 context 餘裕為 "
                f"{report['inference_token_diagnostics']['minimum_observed_context_headroom_tokens']} tokens。"
            ),
            "",
            f"結論：{report['decision']['decision_zh']}",
            "",
        ]
    )
    Path(path).write_text("\n".join(lines), encoding="utf-8")


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-items", type=int, default=0)
    parser.add_argument("--question-id", action="append", default=[])
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--endpoint", default="http://localhost:11434/api/chat")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--output-json", default=LONGMEMEVAL_EVIDENCE_LEDGER_DEVELOPMENT_REPORT_JSON_PATH)
    parser.add_argument("--output-md", default=LONGMEMEVAL_EVIDENCE_LEDGER_DEVELOPMENT_REPORT_MD_PATH)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args(argv)
    if args.top_k < 1 or args.top_k > 20:
        raise ValueError("top-k must be between 1 and the frozen candidate cache size")

    population_rows, data_evidence, cache, baseline_report = load_rows(0)
    development_population_question_count = len(population_rows)
    rows = list(population_rows)
    if args.question_id:
        requested = set(args.question_id)
        rows = [row for row in rows if row["question_id"] in requested]
        missing = requested - {row["question_id"] for row in rows}
        if missing:
            raise ValueError(f"Requested question IDs are not development {TARGET_TASK}: {sorted(missing)}")
    if args.max_items:
        rows = rows[: args.max_items]
    model_evidence = ollama_model_evidence(args.model, args.endpoint)
    candidate_cache_sha256 = file_sha256(
        LONGMEMEVAL_DEVELOPMENT_CANDIDATE_CACHE_PATH
    )
    baseline_report_sha256 = file_sha256(LONGMEMEVAL_RETRIEVAL_REPORT_JSON_PATH)
    ranking_reference_time = benchmark_reference_time(baseline_report).isoformat(
        timespec="seconds"
    )
    prior_results = {}
    output_path = Path(args.output_json)
    if args.resume and output_path.is_file():
        prior = json.loads(output_path.read_text(encoding="utf-8"))
        prior_control = prior.get("matched_control") or {}
        prior_implementation = prior.get("implementation_evidence") or {}
        current_implementation = current_implementation_evidence()
        current_ids = {row["question_id"] for row in rows}
        if (
            prior.get("scope") == SCOPE
            and prior_control.get("model") == args.model
            and prior_control.get("seed") == args.seed
            and prior_control.get("top_k") == args.top_k
            and prior_control.get("model_evidence") == model_evidence
            and (prior.get("data_boundary") or {}).get("dataset_sha256")
            == data_evidence["sha256"]
            and (prior.get("data_boundary") or {}).get("candidate_cache_sha256")
            == candidate_cache_sha256
            and (prior.get("data_boundary") or {}).get("baseline_report_sha256")
            == baseline_report_sha256
            and (prior.get("data_boundary") or {}).get("ranking_reference_time")
            == ranking_reference_time
            and prior_implementation == current_implementation
        ):
            prior_results = {
                row["question_id"]: row
                for row in prior.get("results") or []
                if row.get("question_id") in current_ids
                and set(row.get("conditions") or {}) == set(CONDITIONS)
            }

    def chat(prompt, max_tokens=220, format_schema=None):
        return ollama_chat(
            prompt,
            model=args.model,
            endpoint=args.endpoint,
            seed=args.seed,
            max_tokens=max_tokens,
            format_schema=format_schema,
        )

    wall_now = benchmark_reference_time(baseline_report)
    results = []
    for index, row in enumerate(rows, start=1):
        if row["question_id"] in prior_results:
            results.append(prior_results[row["question_id"]])
            continue
        sessions = selected_sessions(row, args.top_k, wall_now)
        conditions = {}
        direct = generate_condition(
            row,
            sessions,
            "direct_chronological",
            chat,
        )
        direct["local_judge"] = local_diagnostic_judge(
            row["question"], row["answer"], direct["response"], chat
        )
        conditions["direct_chronological"] = direct
        frame_generation, question_frame = generate_question_frame(row, chat)
        shared_notes = generate_notes(row, sessions, question_frame, chat)
        for condition in ("grounded_notes", "versioned_ledger"):
            artifacts = generate_condition(
                row,
                sessions,
                condition,
                chat,
                question_frame=question_frame,
                frame_generation=frame_generation,
                shared_notes=shared_notes,
            )
            artifacts["local_judge"] = local_diagnostic_judge(
                row["question"], row["answer"], artifacts["response"], chat
            )
            conditions[condition] = artifacts
        results.append(
            {
                "question_id": row["question_id"],
                "question_type": row["question_type"],
                "question": row["question"],
                "answer": row["answer"],
                "selected_session_ids": [session["session_id"] for session in sessions],
                "all_gold_sessions_retrieved": set(row["answer_session_ids"]).issubset(
                    {session["session_id"] for session in sessions}
                ),
                "conditions": conditions,
            }
        )
        report = build_report(
            rows,
            results,
            data_evidence,
            cache,
            baseline_report,
            args.model,
            args.seed,
            args.top_k,
            development_population_question_count,
            model_evidence,
        )
        atomic_write_json(output_path, report)
        write_markdown(report, args.output_md)
        print(f"completed={index}/{len(rows)} question_id={row['question_id']}", flush=True)

    report = build_report(
        rows,
        results,
        data_evidence,
        cache,
        baseline_report,
        args.model,
        args.seed,
        args.top_k,
        development_population_question_count,
        model_evidence,
    )
    atomic_write_json(output_path, report)
    write_markdown(report, args.output_md)
    print(
        json.dumps(
            {
                "complete": report["complete"],
                "question_count": report["question_count"],
                "summaries": report["summaries"],
                "decision": report["decision"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
