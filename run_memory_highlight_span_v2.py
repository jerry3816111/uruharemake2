#!/usr/bin/env python3
"""Run the preregistered full-context highlight and span-contract V2 experiment."""

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
    align_quote_to_source,
    build_evidence_note_prompt,
    evidence_quotes_are_grounded,
    filter_grounded_evidence,
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
PREREGISTRATION_PATH = ROOT / "configs" / "memory_highlight_span_v2_preregistration.json"
DEFAULT_REPORT_JSON = ROOT / "reports" / "memory_highlight_span_v2_report.json"
DEFAULT_REPORT_MD = ROOT / "reports" / "memory_highlight_span_v2_report.md"
CONDITIONS = (
    "full_session_freeform",
    "highlighted_full_session_freeform",
    "highlighted_full_session_span_contract",
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
        "highlight_span_module": ROOT / "memory_highlight_span_contract.py",
        "attention_module": ROOT / "memory_utterance_attention.py",
        "ledger_module": ROOT / "memory_evidence_ledger.py",
        "v1_runner_dependency": ROOT / "run_memory_utterance_attention_v1.py",
        "ollama_runner_dependency": ROOT / "run_longmemeval_evidence_ledger_development.py",
        "hash_io_dependency": ROOT / "run_longmemeval_retrieval_benchmark.py",
        "dataset_builder": ROOT / "build_memory_highlight_span_cases_v2.py",
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
        highlighted_context = original_context
    elif mode == "highlighted_full_session":
        if not selected:
            selected = rank_user_utterances(
                case["question"],
                case["question_frame"],
                original_context,
                limit=highlight_limit,
            )
        highlighted_context = annotate_highlights(original_context, selected)
        prompt_session = {**session, "text": highlighted_context}
    else:
        raise ValueError(f"Unknown note extraction mode: {mode}")

    context_restoration_exact = strip_highlight_tags(highlighted_context) == original_context
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
    grounded = (
        filter_grounded_evidence(parsed, original_context) if parsed is not None else None
    )
    return {
        "session_id": session["session_id"],
        "timestamp": session["timestamp"],
        "mode": mode,
        "selected_utterances": selected,
        "highlighted_context": highlighted_context,
        "context_restoration_exact": context_restoration_exact,
        "generation": generation,
        "schema_parse_ok": parsed is not None,
        "quote_grounded": bool(
            parsed is not None and evidence_quotes_are_grounded(parsed, original_context)
        ),
        "evidence": grounded,
        "extracted_fact_count": len((parsed or {}).get("facts") or []),
        "accepted_grounded_fact_count": len((grounded or {}).get("facts") or []),
    }


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


def span_contract_answer(case, ledger, chat):
    if ledger is None:
        return {
            "controller_contract": build_controller_contract(case["question_frame"]),
            "source_records": [],
            "source_records_grounded": False,
            "generation": None,
            "parsed": None,
            "validation": _empty_span_validation("missing_ledger"),
            "text": "",
        }
    records = source_records_from_ledger(ledger)
    source_records_grounded = bool(records) and all(
        align_quote_to_source(record["source_quote"], case["session"]["text"]) is not None
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
    return {
        "controller_contract": build_controller_contract(case["question_frame"]),
        "source_records": records,
        "source_records_grounded": source_records_grounded,
        "generation": generation,
        "parsed": parsed,
        "validation": validation,
        "text": render_span_contract(validation),
    }


def answer_bearing_quotes(case):
    spans = case["gold"]["answer_spans"]
    return [
        quote
        for quote in case["gold"]["attention_quotes"]
        if any(span.lower() in quote.lower() for span in spans)
    ]


def _polarity_hit(polarity, response):
    if polarity == "none":
        return True
    normalized = str(response or "").strip().lower()
    if polarity == "yes":
        return bool(re.match(r"^yes\b", normalized))
    if polarity == "no":
        return bool(re.match(r"^no\b", normalized))
    return False


def score_condition(case, note, ledger_artifact, response, span_artifact=None):
    selected = note.get("selected_utterances") or []
    selected_text = [str(row.get("text") or "") for row in selected]
    attention_quotes = case["gold"]["attention_quotes"]
    attention_hits = sum(quote in selected_text for quote in attention_quotes)
    facts = ((note.get("evidence") or {}).get("facts") or [])
    extracted_quotes = [str(fact.get("quote") or "") for fact in facts]
    gold_quotes = answer_bearing_quotes(case)
    evidence_hits = [
        any(quote == extracted for extracted in extracted_quotes) for quote in gold_quotes
    ]
    span_hits = [
        _span_present(span, response) for span in case["gold"]["slot_spans"].values()
    ]
    polarity_hit = _polarity_hit(case["gold"]["polarity"], response)
    relation_hit = _relation_hit(case["gold"]["relation"], response)
    validation = (span_artifact or {}).get("validation") or {}
    audits = validation.get("audits") or {}
    return {
        "attention_selection_precision": (
            attention_hits / len(selected) if selected else None
        ),
        "attention_selection_recall": (
            attention_hits / len(attention_quotes) if selected and attention_quotes else None
        ),
        "selected_utterance_count": len(selected),
        "selected_gold_utterance_count": attention_hits,
        "gold_evidence_quote_recall": (
            sum(evidence_hits) / len(evidence_hits) if evidence_hits else 1.0
        ),
        "required_slot_span_hit": all(span_hits),
        "required_slot_span_hits": span_hits,
        "polarity_hit": polarity_hit,
        "relation_hit": relation_hit,
        "semantic_case_pass": bool(
            response.strip() and all(span_hits) and polarity_hit and relation_hit
        ),
        "structured_parse_ok": bool(
            note.get("schema_parse_ok") and ledger_artifact.get("schema_parse_ok")
        ),
        "grounded_quote_pass": bool(note.get("quote_grounded")),
        "ledger_grounded": bool(ledger_artifact.get("grounded")),
        "full_context_restoration_exact": bool(note.get("context_restoration_exact")),
        "empty_response": not bool(response.strip()),
        "span_contract_valid": (
            bool(validation.get("valid")) if span_artifact is not None else None
        ),
        "span_slot_complete": (
            bool(audits.get("slot_complete")) if span_artifact is not None else None
        ),
        "span_grounded": (
            bool(audits.get("all_spans_grounded")) if span_artifact is not None else None
        ),
        "span_source_records_grounded": (
            bool(span_artifact.get("source_records_grounded"))
            if span_artifact is not None
            else None
        ),
        "span_contract_errors": (
            validation.get("errors") if span_artifact is not None else None
        ),
    }


def run_case(case, chat, highlight_limit):
    started = time.time()
    selected = rank_user_utterances(
        case["question"],
        case["question_frame"],
        case["session"]["text"],
        limit=highlight_limit,
    )

    full_note = extract_note(case, chat, "full_session", highlight_limit)
    full_ledger = build_ledger(case, full_note, chat)
    full_answer = freeform_answer(case, full_ledger["ledger"], chat)

    highlighted_note = extract_note(
        case,
        chat,
        "highlighted_full_session",
        highlight_limit,
        selected_utterances=selected,
    )
    highlighted_ledger = build_ledger(case, highlighted_note, chat)
    highlighted_answer = freeform_answer(case, highlighted_ledger["ledger"], chat)
    span_answer = span_contract_answer(case, highlighted_ledger["ledger"], chat)

    conditions = {
        "full_session_freeform": {
            "note": full_note,
            "ledger": full_ledger,
            "answer_generation": full_answer,
            "response": full_answer["text"],
        },
        "highlighted_full_session_freeform": {
            "note": highlighted_note,
            "ledger": highlighted_ledger,
            "answer_generation": highlighted_answer,
            "response": highlighted_answer["text"],
        },
        "highlighted_full_session_span_contract": {
            "note": highlighted_note,
            "ledger": highlighted_ledger,
            "span_contract": span_answer,
            "response": span_answer["text"],
        },
    }
    for condition_id, artifacts in conditions.items():
        artifacts["metrics"] = score_condition(
            case,
            artifacts["note"],
            artifacts["ledger"],
            artifacts["response"],
            artifacts.get("span_contract"),
        )
    conditions["full_session_freeform"]["metrics"].update(
        generation_totals(
            full_note.get("generation"),
            full_ledger.get("generation"),
            full_answer,
        )
    )
    conditions["highlighted_full_session_freeform"]["metrics"].update(
        generation_totals(
            highlighted_note.get("generation"),
            highlighted_ledger.get("generation"),
            highlighted_answer,
        )
    )
    conditions["highlighted_full_session_span_contract"]["metrics"].update(
        generation_totals(
            highlighted_note.get("generation"),
            highlighted_ledger.get("generation"),
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
        ("attention_selection_precision", "attention_selection_precision"),
        ("attention_selection_recall", "attention_selection_recall"),
        ("gold_evidence_quote_recall", "gold_evidence_quote_recall"),
        ("required_slot_span_hit", "required_slot_span_hit_rate"),
        ("polarity_hit", "polarity_hit_rate"),
        ("relation_hit", "relation_hit_rate"),
        ("semantic_case_pass", "semantic_case_pass_rate"),
        ("structured_parse_ok", "structured_parse_rate"),
        ("grounded_quote_pass", "grounded_quote_rate"),
        ("ledger_grounded", "ledger_grounded_rate"),
        ("full_context_restoration_exact", "full_context_restoration_rate"),
        ("empty_response", "empty_response_rate"),
        ("span_contract_valid", "span_contract_valid_rate"),
        ("span_slot_complete", "span_slot_complete_rate"),
        ("span_grounded", "span_grounding_rate"),
        ("span_source_records_grounded", "span_source_record_grounding_rate"),
        ("latency_seconds", "mean_latency_seconds"),
        ("prompt_tokens", "mean_prompt_tokens"),
        ("completion_tokens", "mean_completion_tokens"),
    ):
        summary[output_key] = _mean(rows, source_key)
    return summary


def position_invariant_rate(results, condition_id):
    by_scenario = defaultdict(list)
    for row in results:
        by_scenario[row["scenario_id"]].append(
            bool(row["conditions"][condition_id]["metrics"]["semantic_case_pass"])
        )
    invariant = [len(values) == 3 and all(values) for values in by_scenario.values()]
    return statistics.mean(invariant) if invariant else 0.0


def paired_analysis(results, control_id, treatment_id, seed):
    control = [
        bool(row["conditions"][control_id]["metrics"]["semantic_case_pass"])
        for row in results
    ]
    treatment = [
        bool(row["conditions"][treatment_id]["metrics"]["semantic_case_pass"])
        for row in results
    ]
    control_rate = statistics.mean(control) if control else 0.0
    treatment_rate = statistics.mean(treatment) if treatment else 0.0
    return {
        "control": control_id,
        "treatment": treatment_id,
        "n": len(results),
        "control_rate": control_rate,
        "treatment_rate": treatment_rate,
        "delta": treatment_rate - control_rate,
        "mcnemar": mcnemar_exact(control, treatment),
        "paired_bootstrap_95_ci": bootstrap_delta_ci(control, treatment, seed),
    }


def _condition_rate(group, condition_id):
    return group[condition_id]["semantic_case_pass_rate"]


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

    control = "full_session_freeform"
    highlight = "highlighted_full_session_freeform"
    span = "highlighted_full_session_span_contract"
    paired = [
        paired_analysis(results, control, highlight, protocol["inference"]["seed"]),
        paired_analysis(results, highlight, span, protocol["inference"]["seed"] + 1),
    ]

    highlighted_contexts_restore = bool(results) and all(
        row["conditions"][condition]["metrics"]["full_context_restoration_exact"]
        for row in results
        for condition in (highlight, span)
    )
    all_source_quotes_grounded = bool(results) and all(
        row["conditions"][condition]["metrics"]["grounded_quote_pass"]
        and row["conditions"][condition]["metrics"]["ledger_grounded"]
        for row in results
        for condition in CONDITIONS
    )
    all_span_contracts_valid = bool(results) and all(
        row["conditions"][span]["metrics"]["span_contract_valid"] for row in results
    )
    all_required_slots_complete = bool(results) and all(
        row["conditions"][span]["metrics"]["span_slot_complete"] for row in results
    )
    all_admitted_spans_grounded = bool(results) and all(
        row["conditions"][span]["metrics"]["span_grounded"]
        and row["conditions"][span]["metrics"]["span_source_records_grounded"]
        for row in results
    )

    split_nonregression = {}
    for split, group in by_split.items():
        has_rows = group[control]["n"] > 0
        split_nonregression[split] = {
            "highlight_vs_control": has_rows
            and _condition_rate(group, highlight) >= _condition_rate(group, control),
            "span_vs_highlight": has_rows
            and _condition_rate(group, span) >= _condition_rate(group, highlight),
        }
    family_nonregression = {
        capability: (
            _condition_rate(group, highlight) >= _condition_rate(group, control)
            and _condition_rate(group, span) >= _condition_rate(group, highlight)
        )
        for capability, group in by_capability.items()
    }
    position_nonregression = (
        summaries[highlight]["position_invariant_scenario_rate"]
        >= summaries[control]["position_invariant_scenario_rate"]
        and summaries[span]["position_invariant_scenario_rate"]
        >= summaries[highlight]["position_invariant_scenario_rate"]
    )

    gates = {
        "dataset_hash_match": True,
        "all_highlighted_contexts_restore_exactly": highlighted_contexts_restore,
        "all_source_quotes_grounded": all_source_quotes_grounded,
        "all_span_contracts_valid": all_span_contracts_valid,
        "all_required_slots_complete": all_required_slots_complete,
        "all_admitted_spans_grounded": all_admitted_spans_grounded,
        "highlight_development_semantic_pass_not_lower_than_control": (
            split_nonregression["development"]["highlight_vs_control"]
        ),
        "highlight_transfer_semantic_pass_not_lower_than_control": (
            split_nonregression["transfer"]["highlight_vs_control"]
        ),
        "span_development_semantic_pass_not_lower_than_highlight": (
            split_nonregression["development"]["span_vs_highlight"]
        ),
        "span_transfer_semantic_pass_not_lower_than_highlight": (
            split_nonregression["transfer"]["span_vs_highlight"]
        ),
        "no_capability_family_regression_for_either_change": bool(family_nonregression)
        and all(family_nonregression.values()),
        "position_invariance_not_lower_for_either_change": position_nonregression,
    }
    all_gates_pass = bool(complete and all(gates.values()))
    if not complete:
        decision = "incomplete"
    elif all_gates_pass:
        decision = "eligible_for_new_untouched_evaluation"
    else:
        decision = "reject_v2_runtime_integration"
    return {
        "summaries": summaries,
        "by_split": by_split,
        "by_capability": by_capability,
        "by_position": by_position,
        "paired_analysis": paired,
        "nonregression_audit": {
            "by_split": split_nonregression,
            "by_capability": family_nonregression,
        },
        "gates": gates,
        "all_gates_pass": all_gates_pass,
        "decision": decision,
    }


def build_report(protocol, dataset_path, model_evidence, implementation, results):
    complete = len(results) == protocol["dataset"]["case_count"]
    analysis = build_analysis(results, protocol, complete)
    return {
        "schema": "uruha_memory_highlight_span_report_v2",
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
            "consumed_heldout_reused": False,
            "transfer_is_internal_diagnostic": True,
            "runtime_change_authorized": False,
        },
    }


def percent(value):
    return "-" if value is None else f"{100.0 * float(value):.2f}%"


def render_markdown(report):
    labels = {
        "full_session_freeform": "A: full context + freeform",
        "highlighted_full_session_freeform": "B: full context + highlights + freeform",
        "highlighted_full_session_span_contract": "C: B + controller span contract",
    }
    lines = [
        "# Memory Highlight + Span Contract V2",
        "",
        "## Scope and decision",
        "",
        "This development-only matched experiment tests attention that preserves the full source "
        "and a controller-owned semantic binding stage. It contains no official LongMemEval item "
        "and cannot authorize a runtime change.",
        "",
        f"- Complete: `{report['complete']}` ({report['completed_case_count']}/{report['expected_case_count']})",
        f"- Model: `{report['model_evidence']['name']}`",
        f"- Model digest: `{report['model_evidence']['digest']}`",
        f"- Decision: `{report['decision']}`",
        "",
        "## Overall",
        "",
        "| condition | evidence recall | slot spans | polarity | relation | semantic pass | position-invariant | latency |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for condition in CONDITIONS:
        summary = report["summaries"][condition]
        lines.append(
            f"| {labels[condition]} | {percent(summary['gold_evidence_quote_recall'])} | "
            f"{percent(summary['required_slot_span_hit_rate'])} | "
            f"{percent(summary['polarity_hit_rate'])} | "
            f"{percent(summary['relation_hit_rate'])} | "
            f"{percent(summary['semantic_case_pass_rate'])} | "
            f"{percent(summary['position_invariant_scenario_rate'])} | "
            f"{summary['mean_latency_seconds'] or 0.0:.2f}s |"
        )

    highlight = report["summaries"]["highlighted_full_session_freeform"]
    lines.extend(
        [
            "",
            "## Frozen attention audit",
            "",
            f"- Target recall: {percent(highlight['attention_selection_recall'])}.",
            f"- Selection precision: {percent(highlight['attention_selection_precision'])}; the "
            "two preregistered adjacent false positives were retained.",
            f"- Full-context restoration: {percent(highlight['full_context_restoration_rate'])}.",
            "",
            "## Paired comparisons",
            "",
        ]
    )
    for comparison in report["paired_analysis"]:
        lines.append(
            f"- `{comparison['treatment']} - {comparison['control']}`: "
            f"{comparison['delta'] * 100:+.2f} pp; wins/losses "
            f"{comparison['mcnemar']['wins']}/{comparison['mcnemar']['losses']}; "
            f"McNemar p={comparison['mcnemar']['p_value']:.6f}; bootstrap 95% CI "
            f"[{comparison['paired_bootstrap_95_ci'][0] * 100:+.2f}, "
            f"{comparison['paired_bootstrap_95_ci'][1] * 100:+.2f}] pp."
        )

    lines.extend(["", "## Development / transfer", ""])
    for split, summaries in report["by_split"].items():
        values = ", ".join(
            f"{labels[condition]}={percent(summaries[condition]['semantic_case_pass_rate'])}"
            for condition in CONDITIONS
        )
        lines.append(f"- {split}: {values}")

    lines.extend(
        [
            "",
            "## Capability families",
            "",
            "| capability | A | B | C |",
            "| --- | ---: | ---: | ---: |",
        ]
    )
    for capability, summaries in report["by_capability"].items():
        lines.append(
            f"| {capability} | "
            f"{percent(summaries['full_session_freeform']['semantic_case_pass_rate'])} | "
            f"{percent(summaries['highlighted_full_session_freeform']['semantic_case_pass_rate'])} | "
            f"{percent(summaries['highlighted_full_session_span_contract']['semantic_case_pass_rate'])} |"
        )

    lines.extend(["", "## Gates", ""])
    for gate, passed in report["gates"].items():
        lines.append(f"- {'PASS' if passed else 'FAIL'} `{gate}`")

    lines.extend(
        [
            "",
            "## Failure localization",
            "",
            "| case | condition | evidence | spans | polarity | relation | contract errors | response |",
            "| --- | --- | ---: | ---: | ---: | ---: | --- | --- |",
        ]
    )
    failures = 0
    for row in report["results"]:
        for condition in CONDITIONS:
            artifact = row["conditions"][condition]
            metrics = artifact["metrics"]
            if metrics["semantic_case_pass"]:
                continue
            failures += 1
            errors = ",".join(metrics.get("span_contract_errors") or []) or "-"
            response = artifact["response"].replace("|", "/").replace("\n", " ")[:140]
            lines.append(
                f"| {row['case_id']} | {condition} | "
                f"{percent(metrics['gold_evidence_quote_recall'])} | "
                f"{metrics['required_slot_span_hit']} | {metrics['polarity_hit']} | "
                f"{metrics['relation_hit']} | {errors} | {response} |"
            )
    if failures == 0:
        lines.append("| none | - | - | - | - | - | - | - |")

    lines.extend(
        [
            "",
            "## Evidence boundary",
            "",
            "Passing means only that V2 may proceed to a new untouched evaluation. These cases "
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
        results.append(run_case(case, chat, inference["highlight_limit"]))
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
