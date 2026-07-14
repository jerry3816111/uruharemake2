#!/usr/bin/env python3
"""Run the preregistered utterance-attention and answer-proposition experiment."""

import argparse
import datetime as dt
import json
import math
import random
import re
import statistics
import time
from collections import defaultdict
from pathlib import Path

from memory_evidence_ledger import (
    EVIDENCE_NOTE_SCHEMA,
    LEDGER_JSON_SCHEMA,
    build_evidence_note_prompt,
    build_focused_evidence_note_prompt,
    build_ledger_answer_prompt,
    build_ledger_prompt,
    evidence_quotes_are_grounded,
    filter_grounded_evidence,
    ground_ledger_events,
    ledger_answer_view,
    normalized_answer_text,
    parse_evidence_note,
    parse_ledger,
    reconcile_ledger_state,
)
from memory_utterance_attention import (
    ANSWER_PROPOSITION_JSON_SCHEMA,
    build_answer_proposition_prompt,
    parse_answer_proposition,
    rank_user_utterances,
    render_answer_proposition,
    render_attention_context,
    validate_answer_proposition,
)
from run_longmemeval_evidence_ledger_development import ollama_chat, ollama_model_evidence
from run_longmemeval_retrieval_benchmark import atomic_write_json, canonical_sha256, file_sha256


ROOT = Path(__file__).resolve().parent
PREREGISTRATION_PATH = ROOT / "configs" / "memory_utterance_attention_v1_preregistration.json"
DEFAULT_REPORT_JSON = ROOT / "reports" / "memory_utterance_attention_v1_report.json"
DEFAULT_REPORT_MD = ROOT / "reports" / "memory_utterance_attention_v1_report.md"
CONDITIONS = (
    "full_session_freeform",
    "utterance_attention_freeform",
    "utterance_attention_proposition",
)
TENS = {
    "thirty": "30",
    "forty": "40",
    "fifty": "50",
    "sixty": "60",
    "seventy": "70",
    "eighty": "80",
    "ninety": "90",
}
ONES = {word: int(value) for word, value in {
    "one": "1",
    "two": "2",
    "three": "3",
    "four": "4",
    "five": "5",
    "six": "6",
    "seven": "7",
    "eight": "8",
    "nine": "9",
}.items()}


def load_protocol(preregistration_path=PREREGISTRATION_PATH):
    protocol = json.loads(Path(preregistration_path).read_text(encoding="utf-8"))
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
        "attention_module": ROOT / "memory_utterance_attention.py",
        "ledger_module": ROOT / "memory_evidence_ledger.py",
        "dataset": Path(dataset_path),
        "preregistration": Path(preregistration_path),
    }
    return {f"{name}_sha256": file_sha256(path) for name, path in paths.items()}


def extract_note(case, chat, mode, utterance_limit):
    session = case["session"]
    selected = []
    if mode == "full_session":
        prompt = build_evidence_note_prompt(
            case["question"],
            case["question_date"],
            case["question_frame"],
            session,
        )
        source_context = session["text"]
    elif mode == "utterance_attention":
        selected = rank_user_utterances(
            case["question"],
            case["question_frame"],
            session["text"],
            limit=utterance_limit,
        )
        source_context = render_attention_context(selected)
        prompt = build_focused_evidence_note_prompt(
            case["question_frame"], source_context
        )
    else:
        raise ValueError(f"Unknown note extraction mode: {mode}")
    generation = chat(
        prompt,
        max_tokens=700,
        format_schema=EVIDENCE_NOTE_SCHEMA,
    )
    parsed = parse_evidence_note(generation["text"])
    grounded = (
        filter_grounded_evidence(parsed, session["text"])
        if parsed is not None
        else None
    )
    return {
        "session_id": session["session_id"],
        "timestamp": session["timestamp"],
        "mode": mode,
        "selected_utterances": selected,
        "selected_context": source_context,
        "generation": generation,
        "schema_parse_ok": parsed is not None,
        "quote_grounded": bool(
            parsed is not None
            and evidence_quotes_are_grounded(parsed, session["text"])
        ),
        "evidence": grounded,
        "extracted_fact_count": len((parsed or {}).get("facts") or []),
        "accepted_grounded_fact_count": len((grounded or {}).get("facts") or []),
    }


def build_ledger(case, note, chat):
    if not note["schema_parse_ok"]:
        return {
            "generation": None,
            "schema_parse_ok": False,
            "grounded": False,
            "ledger": None,
        }
    generation = chat(
        build_ledger_prompt(
            case["question"],
            case["question_date"],
            case["question_frame"],
            [note],
        ),
        max_tokens=900,
        format_schema=LEDGER_JSON_SCHEMA,
    )
    parsed = parse_ledger(generation["text"])
    grounded = ground_ledger_events(parsed, [note]) if parsed is not None else None
    ledger = reconcile_ledger_state(grounded)
    return {
        "generation": generation,
        "schema_parse_ok": parsed is not None,
        "grounded": grounded is not None,
        "ledger": ledger,
    }


def freeform_answer(case, ledger, chat):
    if ledger is None:
        return {"text": "", "latency_seconds": 0.0, "prompt_tokens": 0, "completion_tokens": 0}
    return chat(
        build_ledger_answer_prompt(
            case["question"],
            case["question_date"],
            ledger,
            case["question_frame"],
        ),
        max_tokens=220,
    )


def proposition_answer(case, ledger, chat):
    if ledger is None:
        return {
            "view": None,
            "generation": None,
            "parsed": None,
            "validation": {
                "valid": False,
                "errors": ["missing_ledger"],
                "proposition": None,
            },
            "text": "",
        }
    view = ledger_answer_view(ledger, case["question_frame"])
    generation = chat(
        build_answer_proposition_prompt(
            case["question"],
            case["question_date"],
            view,
            case["question_frame"],
        ),
        max_tokens=500,
        format_schema=ANSWER_PROPOSITION_JSON_SCHEMA,
    )
    parsed = parse_answer_proposition(generation["text"])
    validation = validate_answer_proposition(
        parsed, view, case["question_frame"]
    )
    return {
        "view": view,
        "generation": generation,
        "parsed": parsed,
        "validation": validation,
        "text": render_answer_proposition(validation),
    }


def _normalize_metric_text(value):
    text = str(value or "").lower()
    compound_pattern = re.compile(
        rf"\b({'|'.join(TENS)})[- ]({'|'.join(ONES)})\b"
    )
    text = compound_pattern.sub(
        lambda match: str(int(TENS[match.group(1)]) + ONES[match.group(2)]),
        text,
    )
    for word, number in TENS.items():
        text = text.replace(word, number)
    text = text.replace("-", " ")
    return normalized_answer_text(text)


def _span_present(span, response):
    target = _normalize_metric_text(span)
    observed = _normalize_metric_text(response)
    return bool(target and f" {target} " in f" {observed} ")


def _relation_hit(relation, response):
    if relation == "none":
        return True
    text = _normalize_metric_text(response)
    if relation == "yes":
        return bool(text.startswith("yes ") or text == "yes")
    if relation == "no":
        return bool(text.startswith("no ") or text == "no")
    if relation == "decrease":
        return any(
            token in text.split()
            for token in ("decrease", "decreased", "shorter", "reduced", "lower")
        )
    if relation == "increase":
        return any(
            token in text.split()
            for token in ("increase", "increased", "longer", "raised", "higher")
        )
    if relation == "same":
        return any(phrase in text for phrase in ("same", "unchanged", "no change"))
    return False


def answer_bearing_quotes(case):
    spans = case["gold"]["answer_spans"]
    return [
        quote
        for quote in case["gold"]["attention_quotes"]
        if any(span.lower() in quote.lower() for span in spans)
    ]


def score_condition(case, note, ledger_artifact, response, proposition=None):
    facts = ((note.get("evidence") or {}).get("facts") or [])
    extracted_quotes = [str(fact.get("quote") or "") for fact in facts]
    gold_quotes = answer_bearing_quotes(case)
    evidence_hits = [
        any(quote == extracted for extracted in extracted_quotes) for quote in gold_quotes
    ]
    span_hits = [
        _span_present(span, response) for span in case["gold"]["answer_spans"]
    ]
    relation_hit = _relation_hit(case["gold"]["relation"], response)
    selected_text = note.get("selected_context") or ""
    attention_quotes = case["gold"]["attention_quotes"]
    selection_hits = [quote in selected_text for quote in attention_quotes]
    proposition_validation = (proposition or {}).get("validation") or {}
    metrics = {
        "attention_selection_recall": (
            sum(selection_hits) / len(selection_hits) if selection_hits else 1.0
        ),
        "gold_evidence_quote_recall": (
            sum(evidence_hits) / len(evidence_hits) if evidence_hits else 1.0
        ),
        "required_answer_span_hit": all(span_hits),
        "required_answer_span_hits": span_hits,
        "relation_hit": relation_hit,
        "semantic_case_pass": bool(response.strip() and all(span_hits) and relation_hit),
        "structured_parse_ok": bool(
            note.get("schema_parse_ok") and ledger_artifact.get("schema_parse_ok")
        ),
        "grounded_quote_pass": bool(note.get("quote_grounded")),
        "ledger_grounded": bool(ledger_artifact.get("grounded")),
        "empty_response": not bool(response.strip()),
        "proposition_valid": (
            bool(proposition_validation.get("valid")) if proposition is not None else None
        ),
        "proposition_errors": (
            proposition_validation.get("errors") if proposition is not None else None
        ),
    }
    return metrics


def generation_totals(*generations):
    present = [generation for generation in generations if generation]
    return {
        "latency_seconds": round(
            sum(float(generation.get("latency_seconds") or 0.0) for generation in present),
            3,
        ),
        "prompt_tokens": sum(int(generation.get("prompt_tokens") or 0) for generation in present),
        "completion_tokens": sum(
            int(generation.get("completion_tokens") or 0) for generation in present
        ),
    }


def run_case(case, chat, utterance_limit):
    started = time.time()
    full_note = extract_note(case, chat, "full_session", utterance_limit)
    full_ledger = build_ledger(case, full_note, chat)
    full_answer = freeform_answer(case, full_ledger["ledger"], chat)

    attention_note = extract_note(case, chat, "utterance_attention", utterance_limit)
    attention_ledger = build_ledger(case, attention_note, chat)
    attention_answer = freeform_answer(case, attention_ledger["ledger"], chat)
    typed = proposition_answer(case, attention_ledger["ledger"], chat)

    conditions = {
        "full_session_freeform": {
            "note": full_note,
            "ledger": full_ledger,
            "answer_generation": full_answer,
            "response": full_answer["text"],
        },
        "utterance_attention_freeform": {
            "note": attention_note,
            "ledger": attention_ledger,
            "answer_generation": attention_answer,
            "response": attention_answer["text"],
        },
        "utterance_attention_proposition": {
            "note": attention_note,
            "ledger": attention_ledger,
            "proposition": typed,
            "response": typed["text"],
        },
    }
    for condition_id, artifacts in conditions.items():
        artifacts["metrics"] = score_condition(
            case,
            artifacts["note"],
            artifacts["ledger"],
            artifacts["response"],
            artifacts.get("proposition"),
        )
    conditions["full_session_freeform"]["metrics"].update(
        generation_totals(
            full_note.get("generation"),
            full_ledger.get("generation"),
            full_answer,
        )
    )
    conditions["utterance_attention_freeform"]["metrics"].update(
        generation_totals(
            attention_note.get("generation"),
            attention_ledger.get("generation"),
            attention_answer,
        )
    )
    conditions["utterance_attention_proposition"]["metrics"].update(
        generation_totals(
            attention_note.get("generation"),
            attention_ledger.get("generation"),
            typed.get("generation"),
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
    values = [float(row["metrics"][key]) for row in rows]
    return statistics.mean(values) if values else 0.0


def summarize_group(results, condition_id):
    rows = [row["conditions"][condition_id] for row in results]
    return {
        "n": len(rows),
        "attention_selection_recall": _mean(rows, "attention_selection_recall"),
        "gold_evidence_quote_recall": _mean(rows, "gold_evidence_quote_recall"),
        "required_answer_span_hit_rate": _mean(rows, "required_answer_span_hit"),
        "relation_hit_rate": _mean(rows, "relation_hit"),
        "semantic_case_pass_rate": _mean(rows, "semantic_case_pass"),
        "structured_parse_rate": _mean(rows, "structured_parse_ok"),
        "grounded_quote_rate": _mean(rows, "grounded_quote_pass"),
        "ledger_grounded_rate": _mean(rows, "ledger_grounded"),
        "empty_response_rate": _mean(rows, "empty_response"),
        "mean_latency_seconds": _mean(rows, "latency_seconds"),
        "mean_prompt_tokens": _mean(rows, "prompt_tokens"),
        "mean_completion_tokens": _mean(rows, "completion_tokens"),
        "proposition_valid_rate": (
            statistics.mean(
                float(row["metrics"]["proposition_valid"])
                for row in rows
                if row["metrics"]["proposition_valid"] is not None
            )
            if any(row["metrics"]["proposition_valid"] is not None for row in rows)
            else None
        ),
    }


def position_invariant_rate(results, condition_id):
    by_scenario = defaultdict(list)
    for row in results:
        by_scenario[row["scenario_id"]].append(
            bool(row["conditions"][condition_id]["metrics"]["semantic_case_pass"])
        )
    invariant = [len(values) == 3 and all(values) for values in by_scenario.values()]
    return statistics.mean(invariant) if invariant else 0.0


def mcnemar_exact(control, treatment):
    wins = sum((not left) and right for left, right in zip(control, treatment))
    losses = sum(left and (not right) for left, right in zip(control, treatment))
    discordant = wins + losses
    if discordant == 0:
        p_value = 1.0
    else:
        tail = sum(math.comb(discordant, k) for k in range(min(wins, losses) + 1))
        p_value = min(1.0, 2.0 * tail / (2**discordant))
    return {"wins": wins, "losses": losses, "discordant": discordant, "p_value": p_value}


def bootstrap_delta_ci(control, treatment, seed, samples=10000):
    deltas = [float(right) - float(left) for left, right in zip(control, treatment)]
    if not deltas:
        return [0.0, 0.0]
    rng = random.Random(seed)
    estimates = []
    for _ in range(samples):
        estimates.append(statistics.mean(rng.choice(deltas) for _ in deltas))
    estimates.sort()
    return [estimates[int(samples * 0.025)], estimates[int(samples * 0.975)]]


def paired_analysis(results, control_id, treatment_id, seed):
    control = [
        bool(row["conditions"][control_id]["metrics"]["semantic_case_pass"])
        for row in results
    ]
    treatment = [
        bool(row["conditions"][treatment_id]["metrics"]["semantic_case_pass"])
        for row in results
    ]
    return {
        "control": control_id,
        "treatment": treatment_id,
        "n": len(results),
        "control_rate": statistics.mean(control) if control else 0.0,
        "treatment_rate": statistics.mean(treatment) if treatment else 0.0,
        "delta": (statistics.mean(treatment) - statistics.mean(control)) if control else 0.0,
        "mcnemar": mcnemar_exact(control, treatment),
        "paired_bootstrap_95_ci": bootstrap_delta_ci(control, treatment, seed),
    }


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
    paired = [
        paired_analysis(
            results,
            "full_session_freeform",
            "utterance_attention_freeform",
            protocol["inference"]["seed"],
        ),
        paired_analysis(
            results,
            "utterance_attention_freeform",
            "utterance_attention_proposition",
            protocol["inference"]["seed"] + 1,
        ),
    ]
    proposed = "utterance_attention_proposition"
    control = "full_session_freeform"
    all_quotes_grounded = all(
        row["conditions"][condition]["metrics"]["grounded_quote_pass"]
        for row in results
        for condition in CONDITIONS
    )
    all_propositions_grounded = all(
        row["conditions"][proposed]["metrics"]["proposition_valid"]
        for row in results
    )
    split_nonregression = {
        split: by_split[split][proposed]["semantic_case_pass_rate"]
        >= by_split[split][control]["semantic_case_pass_rate"]
        for split in by_split
    }
    family_nonregression = {
        capability: by_capability[capability][proposed]["semantic_case_pass_rate"]
        >= by_capability[capability][control]["semantic_case_pass_rate"]
        for capability in by_capability
    }
    gates = {
        "dataset_hash_match": True,
        "all_source_quotes_grounded": all_quotes_grounded,
        "all_valid_proposition_spans_grounded": all_propositions_grounded,
        "development_semantic_pass_not_lower_than_control": split_nonregression.get(
            "development", False
        ),
        "transfer_semantic_pass_not_lower_than_control": split_nonregression.get(
            "transfer", False
        ),
        "no_capability_family_regression": all(family_nonregression.values()),
        "position_invariance_not_lower_than_control": summaries[proposed][
            "position_invariant_scenario_rate"
        ]
        >= summaries[control]["position_invariant_scenario_rate"],
    }
    return {
        "summaries": summaries,
        "by_split": by_split,
        "by_capability": by_capability,
        "paired_analysis": paired,
        "gates": gates,
        "all_gates_pass": bool(complete and all(gates.values())),
        "decision": (
            "eligible_for_new_untouched_evaluation"
            if complete and all(gates.values())
            else "not_eligible_for_runtime_or_heldout_promotion"
        ),
    }


def build_report(protocol, dataset_path, model_evidence, implementation, results):
    complete = len(results) == protocol["dataset"]["case_count"]
    analysis = build_analysis(results, protocol, complete)
    return {
        "schema": "uruha_memory_utterance_attention_report_v1",
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
            "consumed_heldout_reused": False,
            "transfer_is_internal_diagnostic": True,
            "runtime_change_authorized": False,
        },
    }


def percent(value):
    return f"{100.0 * float(value):.2f}%"


def render_markdown(report):
    lines = [
        "# Memory Utterance Attention V1",
        "",
        "## Scope",
        "",
        "This is a development-only matched experiment. It uses 36 synthetic, source-separated "
        "cases and zero official LongMemEval items. It does not authorize a runtime change.",
        "",
        f"- Complete: `{report['complete']}` ({report['completed_case_count']}/{report['expected_case_count']})",
        f"- Model: `{report['model_evidence']['name']}`",
        f"- Model digest: `{report['model_evidence']['digest']}`",
        f"- Decision: `{report['decision']}`",
        "",
        "## Overall",
        "",
        "| condition | evidence recall | answer spans | relation | semantic pass | position-invariant | latency |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    labels = {
        "full_session_freeform": "full session + freeform",
        "utterance_attention_freeform": "utterance attention + freeform",
        "utterance_attention_proposition": "utterance attention + proposition",
    }
    for condition in CONDITIONS:
        summary = report["summaries"][condition]
        lines.append(
            f"| {labels[condition]} | {percent(summary['gold_evidence_quote_recall'])} | "
            f"{percent(summary['required_answer_span_hit_rate'])} | "
            f"{percent(summary['relation_hit_rate'])} | "
            f"{percent(summary['semantic_case_pass_rate'])} | "
            f"{percent(summary['position_invariant_scenario_rate'])} | "
            f"{summary['mean_latency_seconds']:.2f}s |"
        )
    lines.extend(["", "## Paired comparisons", ""])
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
            "| capability | control | attention | proposition |",
            "| --- | ---: | ---: | ---: |",
        ]
    )
    for capability, summaries in report["by_capability"].items():
        lines.append(
            f"| {capability} | {percent(summaries['full_session_freeform']['semantic_case_pass_rate'])} | "
            f"{percent(summaries['utterance_attention_freeform']['semantic_case_pass_rate'])} | "
            f"{percent(summaries['utterance_attention_proposition']['semantic_case_pass_rate'])} |"
        )
    lines.extend(["", "## Gates", ""])
    for gate, passed in report["gates"].items():
        lines.append(f"- {'PASS' if passed else 'FAIL'} `{gate}`")
    lines.extend(
        [
            "",
            "## Failure localization",
            "",
            "| case | split | capability | condition | evidence | spans | relation | response |",
            "| --- | --- | --- | --- | ---: | ---: | ---: | --- |",
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
            response = artifact["response"].replace("|", "/").replace("\n", " ")[:160]
            lines.append(
                f"| {row['case_id']} | {row['split']} | {row['capability']} | {condition} | "
                f"{percent(metrics['gold_evidence_quote_recall'])} | "
                f"{metrics['required_answer_span_hit']} | {metrics['relation_hit']} | {response} |"
            )
    if failures == 0:
        lines.append("| none | - | - | - | - | - | - | - |")
    lines.extend(
        [
            "",
            "## Evidence boundary",
            "",
            "Passing this development gate means only that the mechanism may proceed to a new, "
            "untouched evaluation. The consumed LongMemEval heldout was not reused, and runtime "
            "integration remains unauthorized.",
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
        results.append(run_case(case, chat, inference["utterance_limit"]))
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
