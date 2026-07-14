#!/usr/bin/env python3
"""Run the preregistered source-monitoring and adaptive-reread V3 experiment."""

import argparse
import datetime as dt
import json
import re
import statistics
import time
from collections import defaultdict
from pathlib import Path

from memory_evidence_ledger import (
    EVIDENCE_NOTE_SCHEMA,
    LEDGER_SCHEMA,
    align_quote_to_source,
    build_evidence_note_prompt,
    parse_evidence_note,
)
from memory_highlight_span_contract import (
    annotate_highlights,
    build_controller_contract,
    build_span_binding_json_schema,
    build_span_binding_prompt,
    parse_span_binding,
    render_span_contract,
    source_records_from_ledger,
    strip_highlight_tags,
    validate_span_binding,
)
from memory_provenance_reread import (
    evaluate_evidence_sufficiency,
    explicit_abstention_detected,
    filter_ledger_to_authoritative_user,
    filter_note_to_authoritative_user,
    ledger_source_audit,
    merge_authoritative_ledgers,
    sanitize_extracted_evidence,
)
from memory_utterance_attention import rank_user_utterances
from run_longmemeval_evidence_ledger_development import ollama_chat, ollama_model_evidence
from run_longmemeval_retrieval_benchmark import atomic_write_json, canonical_sha256, file_sha256
from run_memory_utterance_attention_v1 import (
    _relation_hit,
    _span_present,
    bootstrap_delta_ci,
    build_ledger,
    freeform_answer,
    generation_totals,
    mcnemar_exact,
)


ROOT = Path(__file__).resolve().parent
PREREGISTRATION_PATH = ROOT / "configs" / "memory_provenance_reread_v3_preregistration.json"
DEFAULT_REPORT_JSON = ROOT / "reports" / "memory_provenance_reread_v3_report.json"
DEFAULT_REPORT_MD = ROOT / "reports" / "memory_provenance_reread_v3_report.md"
CONDITIONS = (
    "full_session_freeform",
    "provenance_gate_only_freeform",
    "adaptive_provenance_reread_freeform",
    "adaptive_provenance_reread_span_contract",
)
_SMALL_NUMBERS = {
    "zero": 0,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "sixteen": 16,
    "seventeen": 17,
    "eighteen": 18,
    "nineteen": 19,
    "once": 1,
    "twice": 2,
    "thrice": 3,
}
_TENS_NUMBERS = {
    "twenty": 20,
    "thirty": 30,
    "forty": 40,
    "fifty": 50,
    "sixty": 60,
    "seventy": 70,
    "eighty": 80,
    "ninety": 90,
}
_CADENCE_UNITS = frozenset(
    {"morning", "evening", "day", "week", "month", "year"}
)


def load_protocol(preregistration_path=PREREGISTRATION_PATH):
    protocol_path = Path(preregistration_path)
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    dataset_path = ROOT / protocol["dataset"]["path"]
    actual_file_hash = file_sha256(dataset_path)
    if actual_file_hash != protocol["dataset"]["file_sha256"]:
        raise ValueError(
            f"Frozen dataset hash mismatch: {actual_file_hash} != "
            f"{protocol['dataset']['file_sha256']}"
        )
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    actual_cases_hash = canonical_sha256(dataset["cases"])
    if actual_cases_hash != protocol["dataset"]["cases_sha256"]:
        raise ValueError(
            f"Frozen case hash mismatch: {actual_cases_hash} != "
            f"{protocol['dataset']['cases_sha256']}"
        )
    if len(dataset["cases"]) != protocol["dataset"]["case_count"]:
        raise ValueError("Frozen case count mismatch")
    return protocol, dataset, dataset_path


def implementation_evidence(dataset_path, preregistration_path=PREREGISTRATION_PATH):
    paths = {
        "runner": Path(__file__),
        "provenance_module": ROOT / "memory_provenance_reread.py",
        "highlight_span_module": ROOT / "memory_highlight_span_contract.py",
        "attention_module": ROOT / "memory_utterance_attention.py",
        "ledger_module": ROOT / "memory_evidence_ledger.py",
        "v1_runner_dependency": ROOT / "run_memory_utterance_attention_v1.py",
        "ollama_runner_dependency": ROOT / "run_longmemeval_evidence_ledger_development.py",
        "hash_io_dependency": ROOT / "run_longmemeval_retrieval_benchmark.py",
        "dataset_builder": ROOT / "build_memory_provenance_reread_cases_v3.py",
        "dataset": Path(dataset_path),
        "preregistration": Path(preregistration_path),
    }
    return {f"{name}_sha256": file_sha256(path) for name, path in paths.items()}


def extract_note(case, chat, mode, highlight_limit, selected_utterances=None):
    session = case["session"]
    original_context = session["text"]
    selected = list(selected_utterances or [])
    if mode == "full_session":
        prompt_session = dict(session)
        presented_context = original_context
    elif mode == "highlighted_full_session":
        if not selected:
            selected = rank_user_utterances(
                case["question"],
                case["question_frame"],
                original_context,
                limit=highlight_limit,
            )
        presented_context = annotate_highlights(original_context, selected)
        prompt_session = {**session, "text": presented_context}
    else:
        raise ValueError(f"Unknown note extraction mode: {mode}")

    generation = chat(
        build_evidence_note_prompt(
            case["question"],
            case["question_date"],
            case["question_frame"],
            prompt_session,
        ),
        max_tokens=700,
        format_schema=EVIDENCE_NOTE_SCHEMA,
    )
    parsed = parse_evidence_note(generation["text"])
    sanitized = sanitize_extracted_evidence(parsed or {}, original_context)
    audit = sanitized["audit"]
    return {
        "session_id": session["session_id"],
        "timestamp": session["timestamp"],
        "mode": mode,
        "selected_utterances": selected,
        "presented_context": presented_context,
        "context_restoration_exact": strip_highlight_tags(presented_context) == original_context,
        "generation": generation,
        "parsed": parsed,
        "schema_parse_ok": parsed is not None,
        "quote_grounded": bool(parsed is not None and audit["dropped_fact_count"] == 0),
        "evidence": sanitized["evidence"],
        "grounding_audit": audit,
        "extracted_fact_count": len((parsed or {}).get("facts") or []),
        "accepted_grounded_fact_count": audit["accepted_fact_count"],
    }


def _empty_ledger():
    return {
        "schema": LEDGER_SCHEMA,
        "events": [],
        "current_event_indices": [],
        "superseded_event_indices": [],
        "historical_event_indices": [],
        "uncertainties": [],
    }


def build_authoritative_ledger(case, note, chat):
    user_note = filter_note_to_authoritative_user(note)
    facts = (user_note.get("evidence") or {}).get("facts") or []
    if not user_note.get("schema_parse_ok"):
        artifact = {
            "generation": None,
            "schema_parse_ok": False,
            "grounded": False,
            "ledger": None,
        }
    elif not facts:
        artifact = {
            "generation": None,
            "schema_parse_ok": True,
            "grounded": True,
            "ledger": _empty_ledger(),
        }
    else:
        artifact = build_ledger(case, user_note, chat)
        artifact["ledger"] = filter_ledger_to_authoritative_user(artifact.get("ledger"))
        artifact["grounded"] = bool(artifact.get("grounded") and artifact["ledger"] is not None)
    artifact["authoritative_note"] = user_note
    artifact["source_filter_audit"] = user_note.get("source_filter_audit") or {}
    artifact["source_audit"] = ledger_source_audit(artifact.get("ledger"))
    return artifact


def _empty_span_validation(error):
    return {
        "valid": False,
        "errors": [error],
        "contract": None,
        "audits": {
            "slot_complete": False,
            "all_spans_grounded": False,
            "grounded_binding_count": 0,
            "binding_count": 0,
        },
    }


def span_contract_answer(case, ledger, gate, chat, fixed_abstention):
    if not gate.get("sufficient"):
        return {
            "controller_contract": build_controller_contract(case["question_frame"]),
            "source_records": [],
            "source_records_grounded": True,
            "generation": None,
            "parsed": None,
            "validation": _empty_span_validation("evidence_gate_insufficient"),
            "response": fixed_abstention,
            "used_explicit_abstention": True,
        }
    records = source_records_from_ledger(ledger)
    source_records_grounded = bool(records) and all(
        record.get("source_role") == "user"
        and align_quote_to_source(record["source_quote"], case["session"]["text"]) is not None
        for record in records
    )
    generation = chat(
        build_span_binding_prompt(
            case["question"],
            case["question_date"],
            records,
            case["question_frame"],
        ),
        max_tokens=500,
        format_schema=build_span_binding_json_schema(case["question_frame"]),
    )
    parsed = parse_span_binding(generation["text"])
    validation = validate_span_binding(parsed, records, case["question_frame"])
    rendered = render_span_contract(validation)
    return {
        "controller_contract": build_controller_contract(case["question_frame"]),
        "source_records": records,
        "source_records_grounded": source_records_grounded,
        "generation": generation,
        "parsed": parsed,
        "validation": validation,
        "response": rendered or fixed_abstention,
        "used_explicit_abstention": not bool(rendered),
    }


def _answer_generation(case, ledger, gate, chat, fixed_abstention):
    if not gate.get("sufficient"):
        return None, fixed_abstention
    generation = freeform_answer(case, ledger, chat)
    return generation, generation["text"]


def _polarity_hit(polarity, response):
    if polarity == "none":
        return True
    normalized = str(response or "").strip().lower()
    if polarity == "yes":
        return bool(re.match(r"^yes\b", normalized))
    if polarity == "no":
        return bool(re.match(r"^no\b", normalized))
    return False


def _normalize_semantic_metric_text(value):
    text = str(value or "").lower().replace("’", "'")
    compound = re.compile(
        rf"\b({'|'.join(_TENS_NUMBERS)})[- ]({'|'.join(_SMALL_NUMBERS)})\b"
    )
    text = compound.sub(
        lambda match: str(
            _TENS_NUMBERS[match.group(1)] + _SMALL_NUMBERS[match.group(2)]
        ),
        text,
    )
    for word, number in {**_TENS_NUMBERS, **_SMALL_NUMBERS}.items():
        text = re.sub(rf"\b{word}\b", str(number), text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def _semantic_span_present(span, response):
    """Accept lexical spans plus number/cadence-preserving surface variants."""
    if _span_present(span, response):
        return True
    target = _normalize_semantic_metric_text(span)
    observed = _normalize_semantic_metric_text(response)
    if target and f" {target} " in f" {observed} ":
        return True
    target_tokens = set(target.split())
    observed_tokens = set(observed.split())
    target_numbers = {token for token in target_tokens if token.isdigit()}
    target_cadence = target_tokens & _CADENCE_UNITS
    return bool(
        target_numbers
        and target_cadence
        and target_numbers.issubset(observed_tokens)
        and target_cadence.issubset(observed_tokens)
    )


def _evidence_recall(case, ledger):
    observed = {
        str(event.get("source_quote") or "")
        for event in (ledger or {}).get("events") or []
        if event.get("source_role") == "user"
    }
    gold = case["gold"]["required_evidence_quotes"]
    hits = sum(
        any(
            candidate
            and (candidate in quote or quote in candidate)
            for candidate in observed
        )
        for quote in gold
    )
    return hits / len(gold) if gold else 1.0


def _note_integrity(notes):
    present = [note for note in notes if note]
    audits = [note.get("grounding_audit") or {} for note in present]
    attempts = sum(int(audit.get("markup_repair_attempt_count") or 0) for audit in audits)
    successes = sum(int(audit.get("markup_repair_success_count") or 0) for audit in audits)
    return {
        "structured_parse_ok": all(note.get("schema_parse_ok") for note in present),
        "grounded_quote_pass": all(note.get("quote_grounded") for note in present),
        "full_context_restoration_exact": all(
            note.get("context_restoration_exact") for note in present
        ),
        "markup_repair_attempt_count": attempts,
        "markup_repair_success_count": successes,
        "all_markup_repairs_grounded": all(
            audit.get("all_markup_repairs_grounded", True) for audit in audits
        ),
    }


def score_condition(case, artifact, fixed_abstention):
    response = str(artifact.get("response") or "")
    answerable = bool(case["gold"]["answerable"])
    abstained = explicit_abstention_detected(response, fixed_abstention)
    if answerable:
        span_hits = [
            _semantic_span_present(span, response)
            for span in case["gold"]["slot_spans"].values()
        ]
        required_slot_hit = all(span_hits)
        polarity_hit = _polarity_hit(case["gold"]["polarity"], response)
        relation_hit = _relation_hit(case["gold"]["relation"], response)
        semantic_pass = bool(
            response.strip()
            and not abstained
            and required_slot_hit
            and polarity_hit
            and relation_hit
        )
    else:
        span_hits = []
        required_slot_hit = None
        polarity_hit = None
        relation_hit = None
        semantic_pass = None

    ledger = artifact.get("effective_ledger")
    source_audit = ledger_source_audit(ledger)
    note_integrity = _note_integrity(artifact.get("notes") or [])
    gate = artifact.get("gate")
    primary_gate = artifact.get("primary_gate")
    fallback_triggered = bool(artifact.get("fallback_triggered"))
    span_artifact = artifact.get("span_contract")
    span_validation = (span_artifact or {}).get("validation") or {}
    span_audits = span_validation.get("audits") or {}
    span_conditional = (
        bool(span_validation.get("valid"))
        if span_artifact is not None and (gate or {}).get("sufficient")
        else None
    )
    cognitive_pass = semantic_pass if answerable else abstained
    return {
        "answerable": answerable,
        "required_slot_span_hit": required_slot_hit,
        "required_slot_span_hits": span_hits,
        "polarity_hit": polarity_hit,
        "relation_hit": relation_hit,
        "answerable_semantic_case_pass": semantic_pass,
        "explicit_abstention": abstained,
        "unanswerable_explicit_abstention": abstained if not answerable else None,
        "overall_cognitive_case_pass": bool(cognitive_pass),
        "unsafe_answer_on_unanswerable": (
            bool(response.strip()) and not abstained if not answerable else None
        ),
        "false_abstention_on_answerable": abstained if answerable else None,
        "gold_user_evidence_quote_recall": _evidence_recall(case, ledger),
        **source_audit,
        "gate_sufficient": (bool(gate.get("sufficient")) if gate is not None else None),
        "primary_gate_triggered": (
            not bool(primary_gate.get("sufficient")) if primary_gate is not None else None
        ),
        "fallback_triggered": fallback_triggered,
        "fallback_recovered": (
            bool((gate or {}).get("sufficient")) if fallback_triggered else None
        ),
        "fallback_trigger_valid": (
            not bool((primary_gate or {}).get("sufficient")) if fallback_triggered else True
        ),
        **note_integrity,
        "ledger_grounded": bool(artifact.get("ledger_grounded")),
        "span_contract_valid": span_conditional,
        "span_slot_complete": (
            bool(span_audits.get("slot_complete")) if span_conditional is not None else None
        ),
        "span_grounded": (
            bool(span_audits.get("all_spans_grounded")) if span_conditional is not None else None
        ),
        "span_source_records_grounded": (
            bool(span_artifact.get("source_records_grounded"))
            if span_conditional is not None
            else None
        ),
        "span_contract_errors": (
            span_validation.get("errors") if span_artifact is not None else None
        ),
        "empty_response": not bool(response.strip()),
    }


def run_case(case, chat, highlight_limit, fixed_abstention):
    started = time.time()
    selected = rank_user_utterances(
        case["question"],
        case["question_frame"],
        case["session"]["text"],
        limit=highlight_limit,
    )
    full_note = extract_note(case, chat, "full_session", highlight_limit)

    control_ledger = build_ledger(case, full_note, chat)
    control_answer = freeform_answer(case, control_ledger.get("ledger"), chat)

    primary = build_authoritative_ledger(case, full_note, chat)
    primary_gate = evaluate_evidence_sufficiency(
        primary.get("ledger"), case["question_frame"]
    )
    primary_answer, primary_response = _answer_generation(
        case, primary.get("ledger"), primary_gate, chat, fixed_abstention
    )

    fallback_triggered = not primary_gate["sufficient"]
    highlighted_note = None
    secondary = None
    if fallback_triggered:
        highlighted_note = extract_note(
            case,
            chat,
            "highlighted_full_session",
            highlight_limit,
            selected_utterances=selected,
        )
        secondary = build_authoritative_ledger(case, highlighted_note, chat)
        adaptive_ledger = merge_authoritative_ledgers(
            primary.get("ledger"), secondary.get("ledger")
        )
        adaptive_gate = evaluate_evidence_sufficiency(
            adaptive_ledger, case["question_frame"]
        )
        adaptive_answer, adaptive_response = _answer_generation(
            case, adaptive_ledger, adaptive_gate, chat, fixed_abstention
        )
    else:
        adaptive_ledger = primary.get("ledger")
        adaptive_gate = primary_gate
        adaptive_answer = primary_answer
        adaptive_response = primary_response

    span_answer = span_contract_answer(
        case, adaptive_ledger, adaptive_gate, chat, fixed_abstention
    )

    conditions = {
        "full_session_freeform": {
            "notes": [full_note],
            "effective_ledger": control_ledger.get("ledger"),
            "ledger_artifact": control_ledger,
            "ledger_grounded": control_ledger.get("grounded"),
            "answer_generation": control_answer,
            "response": control_answer["text"],
            "gate": None,
            "primary_gate": None,
            "fallback_triggered": False,
        },
        "provenance_gate_only_freeform": {
            "notes": [full_note],
            "effective_ledger": primary.get("ledger"),
            "ledger_artifact": primary,
            "ledger_grounded": primary.get("grounded"),
            "answer_generation": primary_answer,
            "response": primary_response,
            "gate": primary_gate,
            "primary_gate": primary_gate,
            "fallback_triggered": False,
        },
        "adaptive_provenance_reread_freeform": {
            "notes": [full_note, highlighted_note],
            "effective_ledger": adaptive_ledger,
            "primary_ledger_artifact": primary,
            "secondary_ledger_artifact": secondary,
            "ledger_grounded": bool(
                primary.get("grounded")
                and (secondary is None or secondary.get("grounded"))
                and adaptive_ledger is not None
            ),
            "answer_generation": adaptive_answer,
            "response": adaptive_response,
            "gate": adaptive_gate,
            "primary_gate": primary_gate,
            "fallback_triggered": fallback_triggered,
        },
        "adaptive_provenance_reread_span_contract": {
            "notes": [full_note, highlighted_note],
            "effective_ledger": adaptive_ledger,
            "primary_ledger_artifact": primary,
            "secondary_ledger_artifact": secondary,
            "ledger_grounded": bool(
                primary.get("grounded")
                and (secondary is None or secondary.get("grounded"))
                and adaptive_ledger is not None
            ),
            "span_contract": span_answer,
            "response": span_answer["response"],
            "gate": adaptive_gate,
            "primary_gate": primary_gate,
            "fallback_triggered": fallback_triggered,
        },
    }

    for artifact in conditions.values():
        artifact["metrics"] = score_condition(case, artifact, fixed_abstention)

    fallback_note_generation = (highlighted_note or {}).get("generation")
    secondary_ledger_generation = (secondary or {}).get("generation")
    conditions["full_session_freeform"]["metrics"].update(
        generation_totals(
            full_note.get("generation"),
            control_ledger.get("generation"),
            control_answer,
        )
    )
    conditions["provenance_gate_only_freeform"]["metrics"].update(
        generation_totals(
            full_note.get("generation"),
            primary.get("generation"),
            primary_answer,
        )
    )
    conditions["adaptive_provenance_reread_freeform"]["metrics"].update(
        generation_totals(
            full_note.get("generation"),
            primary.get("generation"),
            fallback_note_generation,
            secondary_ledger_generation,
            adaptive_answer,
        )
    )
    conditions["adaptive_provenance_reread_span_contract"]["metrics"].update(
        generation_totals(
            full_note.get("generation"),
            primary.get("generation"),
            fallback_note_generation,
            secondary_ledger_generation,
            span_answer.get("generation"),
        )
    )
    return {
        "case_id": case["case_id"],
        "scenario_id": case["scenario_id"],
        "split": case["split"],
        "capability": case["capability"],
        "evidence_position": case["evidence_position"],
        "question": case["question"],
        "gold": case["gold"],
        "selected_utterances": selected,
        "conditions": conditions,
        "wall_time_seconds": round(time.time() - started, 3),
    }


def _mean(rows, key):
    values = [
        float(row["metrics"][key])
        for row in rows
        if row["metrics"].get(key) is not None
    ]
    return statistics.mean(values) if values else None


def summarize_group(results, condition_id):
    rows = [row["conditions"][condition_id] for row in results]
    summary = {"n": len(rows)}
    for source_key, output_key in (
        ("answerable_semantic_case_pass", "answerable_semantic_case_pass_rate"),
        ("unanswerable_explicit_abstention", "unanswerable_explicit_abstention_rate"),
        ("overall_cognitive_case_pass", "overall_cognitive_case_pass_rate"),
        ("unsafe_answer_on_unanswerable", "unsafe_answer_rate_on_unanswerable"),
        ("false_abstention_on_answerable", "false_abstention_rate_on_answerable"),
        ("gold_user_evidence_quote_recall", "gold_user_evidence_quote_recall"),
        ("authoritative_user_evidence_rate", "authoritative_user_evidence_rate"),
        ("assistant_fact_admission_rate", "assistant_fact_admission_rate"),
        ("gate_sufficient", "gate_sufficiency_rate"),
        ("primary_gate_triggered", "primary_gate_trigger_rate"),
        ("fallback_recovered", "fallback_recovery_rate"),
        ("structured_parse_ok", "structured_parse_rate"),
        ("grounded_quote_pass", "grounded_quote_rate"),
        ("full_context_restoration_exact", "full_context_restoration_rate"),
        ("all_markup_repairs_grounded", "markup_repair_grounding_rate"),
        ("ledger_grounded", "ledger_grounded_rate"),
        ("span_contract_valid", "span_contract_valid_rate"),
        ("span_grounded", "span_grounding_rate"),
        ("span_source_records_grounded", "span_source_record_grounding_rate"),
        ("empty_response", "empty_response_rate"),
        ("latency_seconds", "mean_latency_seconds"),
        ("prompt_tokens", "mean_prompt_tokens"),
        ("completion_tokens", "mean_completion_tokens"),
    ):
        summary[output_key] = _mean(rows, source_key)
    summary["markup_repair_attempt_count"] = sum(
        int(row["metrics"].get("markup_repair_attempt_count") or 0) for row in rows
    )
    summary["markup_repair_success_count"] = sum(
        int(row["metrics"].get("markup_repair_success_count") or 0) for row in rows
    )
    return summary


def position_invariant_rate(results, condition_id):
    by_scenario = defaultdict(list)
    for row in results:
        by_scenario[row["scenario_id"]].append(
            bool(row["conditions"][condition_id]["metrics"]["overall_cognitive_case_pass"])
        )
    invariant = [len(values) == 3 and all(values) for values in by_scenario.values()]
    return statistics.mean(invariant) if invariant else 0.0


def paired_analysis(results, control_id, treatment_id, metric, seed):
    pairs = [
        (
            row["conditions"][control_id]["metrics"].get(metric),
            row["conditions"][treatment_id]["metrics"].get(metric),
        )
        for row in results
    ]
    pairs = [(left, right) for left, right in pairs if left is not None and right is not None]
    control = [bool(left) for left, _right in pairs]
    treatment = [bool(right) for _left, right in pairs]
    control_rate = statistics.mean(control) if control else 0.0
    treatment_rate = statistics.mean(treatment) if treatment else 0.0
    return {
        "metric": metric,
        "control": control_id,
        "treatment": treatment_id,
        "n": len(pairs),
        "control_rate": control_rate,
        "treatment_rate": treatment_rate,
        "delta": treatment_rate - control_rate,
        "mcnemar": mcnemar_exact(control, treatment),
        "paired_bootstrap_95_ci": bootstrap_delta_ci(control, treatment, seed),
    }


def _rate(group, condition_id, key):
    return group[condition_id][key]


def _not_lower(treatment, control):
    return treatment is not None and control is not None and treatment >= control


def build_analysis(results, protocol, complete):
    summaries = {condition: summarize_group(results, condition) for condition in CONDITIONS}
    for condition in CONDITIONS:
        summaries[condition]["position_invariant_scenario_rate"] = position_invariant_rate(
            results, condition
        )

    by_split = {}
    for split in ("development", "transfer"):
        subset = [row for row in results if row["split"] == split]
        by_split[split] = {
            condition: summarize_group(subset, condition) for condition in CONDITIONS
        }
        for condition in CONDITIONS:
            by_split[split][condition]["position_invariant_scenario_rate"] = (
                position_invariant_rate(subset, condition)
            )

    by_capability = {}
    for capability in sorted({row["capability"] for row in results}):
        subset = [row for row in results if row["capability"] == capability]
        by_capability[capability] = {
            condition: summarize_group(subset, condition) for condition in CONDITIONS
        }

    by_position = {}
    for position in ("beginning", "middle", "end"):
        subset = [row for row in results if row["evidence_position"] == position]
        by_position[position] = {
            condition: summarize_group(subset, condition) for condition in CONDITIONS
        }

    comparisons = (
        (CONDITIONS[0], CONDITIONS[1]),
        (CONDITIONS[1], CONDITIONS[2]),
        (CONDITIONS[0], CONDITIONS[2]),
        (CONDITIONS[2], CONDITIONS[3]),
    )
    paired = []
    for index, (control, treatment) in enumerate(comparisons):
        paired.append(
            paired_analysis(
                results,
                control,
                treatment,
                "overall_cognitive_case_pass",
                protocol["inference"]["seed"] + index,
            )
        )
        paired.append(
            paired_analysis(
                results,
                control,
                treatment,
                "answerable_semantic_case_pass",
                protocol["inference"]["seed"] + 100 + index,
            )
        )

    control = CONDITIONS[0]
    provenance = CONDITIONS[1]
    adaptive = CONDITIONS[2]
    span = CONDITIONS[3]
    family_nonregression = {
        capability: (
            _rate(group, adaptive, "overall_cognitive_case_pass_rate")
            >= _rate(group, control, "overall_cognitive_case_pass_rate")
        )
        for capability, group in by_capability.items()
    }
    gates = {
        "dataset_hash_match": True,
        "all_highlighted_contexts_restore_exactly": bool(results)
        and all(
            row["conditions"][adaptive]["metrics"]["full_context_restoration_exact"]
            for row in results
        ),
        "all_markup_repairs_exactly_grounded": bool(results)
        and all(
            row["conditions"][adaptive]["metrics"]["all_markup_repairs_grounded"]
            for row in results
        ),
        "no_assistant_only_fact_admitted_to_treatment_ledgers": bool(results)
        and all(
            row["conditions"][condition]["metrics"]["assistant_fact_admission_rate"] == 0
            for row in results
            for condition in (provenance, adaptive, span)
        ),
        "provenance_gate_unanswerable_abstention_rate_equals_one": (
            summaries[provenance]["unanswerable_explicit_abstention_rate"] == 1.0
        ),
        "adaptive_unanswerable_abstention_rate_equals_one": (
            summaries[adaptive]["unanswerable_explicit_abstention_rate"] == 1.0
        ),
        "span_unanswerable_abstention_rate_equals_one": (
            summaries[span]["unanswerable_explicit_abstention_rate"] == 1.0
        ),
        "adaptive_answerable_false_abstention_rate_equals_zero": (
            summaries[adaptive]["false_abstention_rate_on_answerable"] == 0.0
        ),
        "adaptive_development_answerable_pass_not_lower_than_control": (
            _not_lower(
                _rate(
                    by_split["development"],
                    adaptive,
                    "answerable_semantic_case_pass_rate",
                ),
                _rate(
                    by_split["development"],
                    control,
                    "answerable_semantic_case_pass_rate",
                ),
            )
        ),
        "adaptive_transfer_answerable_pass_not_lower_than_control": (
            _not_lower(
                _rate(
                    by_split["transfer"],
                    adaptive,
                    "answerable_semantic_case_pass_rate",
                ),
                _rate(
                    by_split["transfer"],
                    control,
                    "answerable_semantic_case_pass_rate",
                ),
            )
        ),
        "adaptive_overall_cognitive_pass_not_lower_than_control": (
            _not_lower(
                summaries[adaptive]["overall_cognitive_case_pass_rate"],
                summaries[control]["overall_cognitive_case_pass_rate"],
            )
        ),
        "no_capability_family_regression_adaptive_vs_control": bool(family_nonregression)
        and all(family_nonregression.values()),
        "span_overall_cognitive_pass_not_lower_than_adaptive": (
            _not_lower(
                summaries[span]["overall_cognitive_case_pass_rate"],
                summaries[adaptive]["overall_cognitive_case_pass_rate"],
            )
        ),
        "position_invariance_not_lower_adaptive_vs_control": (
            summaries[adaptive]["position_invariant_scenario_rate"]
            >= summaries[control]["position_invariant_scenario_rate"]
        ),
        "fallback_runs_only_after_primary_insufficiency": bool(results)
        and all(
            row["conditions"][adaptive]["metrics"]["fallback_trigger_valid"]
            for row in results
        ),
    }
    all_gates_pass = bool(complete and all(gates.values()))
    if not complete:
        decision = "incomplete"
    elif all_gates_pass:
        decision = "eligible_for_new_untouched_evaluation"
    else:
        decision = "reject_v3_runtime_integration"
    return {
        "summaries": summaries,
        "by_split": by_split,
        "by_capability": by_capability,
        "by_position": by_position,
        "paired_analysis": paired,
        "nonregression_audit": {"by_capability": family_nonregression},
        "gates": gates,
        "all_gates_pass": all_gates_pass,
        "decision": decision,
    }


def build_report(protocol, dataset_path, model_evidence, implementation, results):
    complete = len(results) == protocol["dataset"]["case_count"]
    analysis = build_analysis(results, protocol, complete)
    return {
        "schema": "uruha_memory_provenance_reread_report_v3",
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "complete": complete,
        "completed_case_count": len(results),
        "expected_case_count": protocol["dataset"]["case_count"],
        "protocol": protocol,
        "dataset_path": str(dataset_path.relative_to(ROOT)),
        "model_evidence": model_evidence,
        "implementation_evidence": implementation,
        **analysis,
        "results": results,
        "results_sha256": canonical_sha256(results),
        "research_boundary": {
            "official_longmemeval_items_used": 0,
            "v1_case_reuse_count": 0,
            "v2_case_reuse_count": 0,
            "transfer_is_internal_diagnostic": True,
            "runtime_change_authorized": False,
        },
    }


def percent(value):
    return "-" if value is None else f"{100.0 * float(value):.2f}%"


def render_markdown(report):
    labels = {
        CONDITIONS[0]: "A: existing full-session freeform",
        CONDITIONS[1]: "P: user-source provenance gate",
        CONDITIONS[2]: "R: P + low-sufficiency reread",
        CONDITIONS[3]: "S: R + source-span contract",
    }
    lines = [
        "# Memory Source Monitoring + Adaptive Reread V3",
        "",
        "## Scope and decision",
        "",
        "This development-only matched experiment tests source authority, explicit abstention, "
        "and conditional rereading. It contains no official benchmark item and cannot authorize "
        "a runtime change.",
        "",
        f"- Complete: `{report['complete']}` ({report['completed_case_count']}/{report['expected_case_count']})",
        f"- Model: `{report['model_evidence']['name']}`",
        f"- Model digest: `{report['model_evidence']['digest']}`",
        f"- Decision: `{report['decision']}`",
        "",
        "## Overall",
        "",
        "| condition | answerable | abstention | cognitive | unsafe answer | evidence recall | assistant admitted | fallback | latency |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for condition in CONDITIONS:
        summary = report["summaries"][condition]
        lines.append(
            f"| {labels[condition]} | {percent(summary['answerable_semantic_case_pass_rate'])} | "
            f"{percent(summary['unanswerable_explicit_abstention_rate'])} | "
            f"{percent(summary['overall_cognitive_case_pass_rate'])} | "
            f"{percent(summary['unsafe_answer_rate_on_unanswerable'])} | "
            f"{percent(summary['gold_user_evidence_quote_recall'])} | "
            f"{percent(summary['assistant_fact_admission_rate'])} | "
            f"{percent(summary['primary_gate_trigger_rate'])} | "
            f"{summary['mean_latency_seconds'] or 0.0:.2f}s |"
        )

    lines.extend(["", "## Paired comparisons", ""])
    for comparison in report["paired_analysis"]:
        lines.append(
            f"- `{comparison['metric']}`: `{comparison['treatment']} - "
            f"{comparison['control']}` = {comparison['delta'] * 100:+.2f} pp; "
            f"wins/losses {comparison['mcnemar']['wins']}/{comparison['mcnemar']['losses']}; "
            f"McNemar p={comparison['mcnemar']['p_value']:.6f}; bootstrap 95% CI "
            f"[{comparison['paired_bootstrap_95_ci'][0] * 100:+.2f}, "
            f"{comparison['paired_bootstrap_95_ci'][1] * 100:+.2f}] pp."
        )

    lines.extend(["", "## Development / transfer", ""])
    for split, summaries in report["by_split"].items():
        values = ", ".join(
            f"{labels[condition]}={percent(summaries[condition]['overall_cognitive_case_pass_rate'])}"
            for condition in CONDITIONS
        )
        lines.append(f"- {split}: {values}")

    lines.extend(
        [
            "",
            "## Capability families",
            "",
            "| capability | A | P | R | S |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for capability, summaries in report["by_capability"].items():
        lines.append(
            f"| {capability} | "
            f"{percent(summaries[CONDITIONS[0]]['overall_cognitive_case_pass_rate'])} | "
            f"{percent(summaries[CONDITIONS[1]]['overall_cognitive_case_pass_rate'])} | "
            f"{percent(summaries[CONDITIONS[2]]['overall_cognitive_case_pass_rate'])} | "
            f"{percent(summaries[CONDITIONS[3]]['overall_cognitive_case_pass_rate'])} |"
        )

    lines.extend(["", "## Gates", ""])
    for gate, passed in report["gates"].items():
        lines.append(f"- {'PASS' if passed else 'FAIL'} `{gate}`")

    lines.extend(
        [
            "",
            "## Failure localization",
            "",
            "| case | condition | answerable | gate | abstained | spans | polarity | relation | response |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
        ]
    )
    failures = 0
    for row in report["results"]:
        for condition in CONDITIONS:
            artifact = row["conditions"][condition]
            metrics = artifact["metrics"]
            if metrics["overall_cognitive_case_pass"]:
                continue
            failures += 1
            response = artifact["response"].replace("|", "/").replace("\n", " ")[:160]
            lines.append(
                f"| {row['case_id']} | {condition} | {metrics['answerable']} | "
                f"{metrics['gate_sufficient']} | {metrics['explicit_abstention']} | "
                f"{metrics['required_slot_span_hit']} | {metrics['polarity_hit']} | "
                f"{metrics['relation_hit']} | {response} |"
            )
    if failures == 0:
        lines.append("| none | - | - | - | - | - | - | - | - |")

    lines.extend(
        [
            "",
            "## Evidence boundary",
            "",
            "Passing means only that V3 may proceed to a new untouched evaluation. These cases "
            "then become consumed development evidence. Runtime integration remains unauthorized.",
            "",
        ]
    )
    return "\n".join(lines)


def validate_resume(existing, protocol, model_evidence, implementation):
    if existing.get("protocol") != protocol:
        raise ValueError("Resume protocol mismatch")
    if existing.get("model_evidence", {}).get("digest") != model_evidence["digest"]:
        raise ValueError("Resume model digest mismatch")
    if existing.get("implementation_evidence") != implementation:
        raise ValueError("Resume implementation hash mismatch")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--preregistration", type=Path, default=PREREGISTRATION_PATH)
    parser.add_argument("--report-json", type=Path, default=DEFAULT_REPORT_JSON)
    parser.add_argument("--report-md", type=Path, default=DEFAULT_REPORT_MD)
    parser.add_argument("--endpoint", default="http://localhost:11434/api/chat")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--max-items", type=int, default=0)
    args = parser.parse_args()

    protocol, dataset, dataset_path = load_protocol(args.preregistration)
    inference = protocol["inference"]
    model_evidence = ollama_model_evidence(inference["model"], args.endpoint)
    implementation = implementation_evidence(dataset_path, args.preregistration)
    chat = lambda prompt, **kwargs: ollama_chat(
        prompt,
        model=inference["model"],
        endpoint=args.endpoint,
        seed=inference["seed"],
        num_ctx=inference["num_ctx"],
        **kwargs,
    )

    results = []
    if args.resume and args.report_json.exists():
        existing = json.loads(args.report_json.read_text(encoding="utf-8"))
        validate_resume(existing, protocol, model_evidence, implementation)
        results = existing.get("results") or []
    elif args.report_json.exists():
        raise FileExistsError(
            f"Report already exists: {args.report_json}. Use --resume only for an interrupted run."
        )

    completed = {row["case_id"] for row in results}
    pending = [case for case in dataset["cases"] if case["case_id"] not in completed]
    if args.max_items:
        pending = pending[: args.max_items]
    for index, case in enumerate(pending, start=1):
        print(f"[{index}/{len(pending)}] {case['case_id']}", flush=True)
        results.append(
            run_case(
                case,
                chat,
                inference["highlight_limit"],
                inference["explicit_abstention"],
            )
        )
        report = build_report(protocol, dataset_path, model_evidence, implementation, results)
        atomic_write_json(args.report_json, report)
        args.report_md.write_text(render_markdown(report), encoding="utf-8")

    report = build_report(protocol, dataset_path, model_evidence, implementation, results)
    atomic_write_json(args.report_json, report)
    args.report_md.write_text(render_markdown(report), encoding="utf-8")
    print(
        json.dumps(
            {
                "complete": report["complete"],
                "completed": report["completed_case_count"],
                "decision": report["decision"],
                "all_gates_pass": report["all_gates_pass"],
                "report_json": str(args.report_json),
                "report_md": str(args.report_md),
            },
            ensure_ascii=False,
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
