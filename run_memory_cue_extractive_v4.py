#!/usr/bin/env python3
"""Run the preregistered cue-driven extractive memory fallback V4 experiment."""

import argparse
import datetime as dt
import json
import statistics
import time
from collections import defaultdict
from pathlib import Path

from memory_cue_extractive import (
    answer_from_candidate_artifact,
    build_candidate_artifact,
)
from memory_provenance_reread import (
    evaluate_evidence_sufficiency,
    merge_authoritative_ledgers,
)
from memory_utterance_attention import rank_user_utterances
from run_longmemeval_evidence_ledger_development import ollama_chat, ollama_model_evidence
from run_longmemeval_retrieval_benchmark import (
    atomic_write_json,
    canonical_sha256,
    file_sha256,
)
from run_memory_provenance_reread_v3 import (
    _answer_generation,
    _not_lower,
    _rate,
    build_authoritative_ledger,
    extract_note,
    paired_analysis,
    position_invariant_rate,
    score_condition,
    summarize_group as summarize_v3_group,
)
from run_memory_utterance_attention_v1 import (
    build_ledger,
    freeform_answer,
    generation_totals,
)


ROOT = Path(__file__).resolve().parent
PREREGISTRATION_PATH = ROOT / "configs" / "memory_cue_extractive_v4_preregistration.json"
DEFAULT_REPORT_JSON = ROOT / "reports" / "memory_cue_extractive_v4_report.json"
DEFAULT_REPORT_MD = ROOT / "reports" / "memory_cue_extractive_v4_report.md"
CONDITIONS = (
    "full_session_freeform",
    "provenance_gate_freeform",
    "model_reread_fallback",
    "cue_extractive_fallback",
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
    frozen = protocol["frozen_preimplementation_components"]
    frozen_paths = {
        "selector": ROOT / "memory_utterance_attention.py",
        "candidate_sufficiency_gate": ROOT / "memory_provenance_reread.py",
    }
    for name, path in frozen_paths.items():
        actual = file_sha256(path)
        expected = frozen[name]["module_sha256"]
        if actual != expected:
            raise ValueError(f"Frozen {name} hash mismatch: {actual} != {expected}")
    if len(dataset["cases"]) != protocol["dataset"]["case_count"]:
        raise ValueError("Frozen case count mismatch")
    return protocol, dataset, dataset_path


def implementation_evidence(dataset_path, preregistration_path=PREREGISTRATION_PATH):
    paths = {
        "runner": Path(__file__),
        "cue_module": ROOT / "memory_cue_extractive.py",
        "v3_runner_dependency": ROOT / "run_memory_provenance_reread_v3.py",
        "provenance_module": ROOT / "memory_provenance_reread.py",
        "attention_module": ROOT / "memory_utterance_attention.py",
        "ledger_module": ROOT / "memory_evidence_ledger.py",
        "ollama_runner_dependency": ROOT / "run_longmemeval_evidence_ledger_development.py",
        "dataset_builder": ROOT / "build_memory_cue_extractive_cases_v4.py",
        "dataset": Path(dataset_path),
        "preregistration": Path(preregistration_path),
    }
    return {f"{name}_sha256": file_sha256(path) for name, path in paths.items()}


def _candidate_metric_projection(artifact):
    if artifact is None:
        return {
            "candidate_gate_sufficient": None,
            "candidate_context_user_source_rate": None,
            "candidate_context_exact_source_rate": None,
            "candidate_assistant_turn_admission_rate": None,
            "candidate_count": None,
        }
    audit = artifact["source_audit"]
    return {
        "candidate_gate_sufficient": bool(artifact["gate"]["sufficient"]),
        "candidate_context_user_source_rate": audit[
            "candidate_context_user_source_rate"
        ],
        "candidate_context_exact_source_rate": audit[
            "candidate_context_exact_source_rate"
        ],
        "candidate_assistant_turn_admission_rate": audit[
            "assistant_turn_admission_rate"
        ],
        "candidate_count": audit["candidate_count"],
    }


def run_case(case, chat, candidate_limit, fixed_abstention):
    started = time.time()
    selected = rank_user_utterances(
        case["question"],
        case["question_frame"],
        case["session"]["text"],
        limit=candidate_limit,
    )
    full_note = extract_note(case, chat, "full_session", candidate_limit)

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
            candidate_limit,
            selected_utterances=selected,
        )
        secondary = build_authoritative_ledger(case, highlighted_note, chat)
        reread_ledger = merge_authoritative_ledgers(
            primary.get("ledger"), secondary.get("ledger")
        )
        reread_gate = evaluate_evidence_sufficiency(
            reread_ledger, case["question_frame"]
        )
        reread_answer, reread_response = _answer_generation(
            case, reread_ledger, reread_gate, chat, fixed_abstention
        )

        candidate = build_candidate_artifact(case, selected)
        candidate_answer = answer_from_candidate_artifact(
            case, candidate, chat, fixed_abstention
        )
        cue_ledger = candidate["ledger"]
        cue_gate = candidate["gate"]
        cue_generation = candidate_answer["generation"]
        cue_response = candidate_answer["response"]
    else:
        reread_ledger = primary.get("ledger")
        reread_gate = primary_gate
        reread_answer = primary_answer
        reread_response = primary_response
        candidate = None
        candidate_answer = None
        cue_ledger = primary.get("ledger")
        cue_gate = primary_gate
        cue_generation = primary_answer
        cue_response = primary_response

    conditions = {
        CONDITIONS[0]: {
            "notes": [full_note],
            "effective_ledger": control_ledger.get("ledger"),
            "ledger_artifact": control_ledger,
            "ledger_grounded": control_ledger.get("grounded"),
            "answer_generation": control_answer,
            "response": control_answer["text"],
            "gate": None,
            "primary_gate": None,
            "fallback_triggered": False,
            "candidate_artifact": None,
        },
        CONDITIONS[1]: {
            "notes": [full_note],
            "effective_ledger": primary.get("ledger"),
            "ledger_artifact": primary,
            "ledger_grounded": primary.get("grounded"),
            "answer_generation": primary_answer,
            "response": primary_response,
            "gate": primary_gate,
            "primary_gate": primary_gate,
            "fallback_triggered": False,
            "candidate_artifact": None,
        },
        CONDITIONS[2]: {
            "notes": [full_note, highlighted_note],
            "effective_ledger": reread_ledger,
            "primary_ledger_artifact": primary,
            "secondary_ledger_artifact": secondary,
            "ledger_grounded": bool(
                primary.get("grounded")
                and (secondary is None or secondary.get("grounded"))
                and reread_ledger is not None
            ),
            "answer_generation": reread_answer,
            "response": reread_response,
            "gate": reread_gate,
            "primary_gate": primary_gate,
            "fallback_triggered": fallback_triggered,
            "candidate_artifact": None,
        },
        CONDITIONS[3]: {
            "notes": [full_note],
            "effective_ledger": cue_ledger,
            "primary_ledger_artifact": primary,
            "candidate_artifact": candidate,
            "candidate_answer": candidate_answer,
            "ledger_grounded": bool(
                primary.get("grounded")
                and cue_ledger is not None
                and (
                    candidate is None
                    or candidate["source_audit"]["all_candidates_exact_user_source"]
                )
            ),
            "answer_generation": cue_generation,
            "response": cue_response,
            "gate": cue_gate,
            "primary_gate": primary_gate,
            "fallback_triggered": fallback_triggered,
        },
    }

    for artifact in conditions.values():
        artifact["metrics"] = score_condition(case, artifact, fixed_abstention)
        artifact["metrics"].update(
            _candidate_metric_projection(artifact.get("candidate_artifact"))
        )

    primary_pass = conditions[CONDITIONS[1]]["metrics"][
        "overall_cognitive_case_pass"
    ]
    for condition in (CONDITIONS[2], CONDITIONS[3]):
        metrics = conditions[condition]["metrics"]
        metrics["fallback_semantic_recovered"] = (
            bool(
                case["gold"]["answerable"]
                and fallback_triggered
                and not primary_pass
                and metrics["answerable_semantic_case_pass"]
            )
            if fallback_triggered and case["gold"]["answerable"]
            else None
        )
    for condition in (CONDITIONS[0], CONDITIONS[1]):
        conditions[condition]["metrics"]["fallback_semantic_recovered"] = None

    fallback_note_generation = (highlighted_note or {}).get("generation")
    secondary_ledger_generation = (secondary or {}).get("generation")
    conditions[CONDITIONS[0]]["metrics"].update(
        generation_totals(
            full_note.get("generation"),
            control_ledger.get("generation"),
            control_answer,
        )
    )
    conditions[CONDITIONS[1]]["metrics"].update(
        generation_totals(
            full_note.get("generation"),
            primary.get("generation"),
            primary_answer,
        )
    )
    conditions[CONDITIONS[2]]["metrics"].update(
        generation_totals(
            full_note.get("generation"),
            primary.get("generation"),
            fallback_note_generation,
            secondary_ledger_generation,
            reread_answer,
        )
    )
    conditions[CONDITIONS[3]]["metrics"].update(
        generation_totals(
            full_note.get("generation"),
            primary.get("generation"),
            cue_generation,
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
    summary = summarize_v3_group(results, condition_id)
    rows = [row["conditions"][condition_id] for row in results]
    for key, output in (
        ("fallback_semantic_recovered", "fallback_semantic_recovery_rate"),
        ("candidate_gate_sufficient", "candidate_gate_sufficiency_rate"),
        ("candidate_context_user_source_rate", "candidate_context_user_source_rate"),
        ("candidate_context_exact_source_rate", "candidate_context_exact_source_rate"),
        (
            "candidate_assistant_turn_admission_rate",
            "candidate_assistant_turn_admission_rate",
        ),
        ("candidate_count", "mean_candidate_count"),
    ):
        summary[output] = _mean(rows, key)
    return summary


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
        (CONDITIONS[1], CONDITIONS[3]),
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

    provenance = CONDITIONS[1]
    reread = CONDITIONS[2]
    cue = CONDITIONS[3]
    family_nonregression = {
        capability: _not_lower(
            _rate(group, cue, "overall_cognitive_case_pass_rate"),
            _rate(group, provenance, "overall_cognitive_case_pass_rate"),
        )
        for capability, group in by_capability.items()
    }
    candidate_rows = [
        row["conditions"][cue]
        for row in results
        if row["conditions"][cue]["metrics"]["fallback_triggered"]
    ]
    gates = {
        "dataset_hash_match": True,
        "no_v1_v2_v3_scenario_or_question_reuse": True,
        "all_candidate_context_is_exact_user_source": bool(candidate_rows)
        and all(
            row["metrics"]["candidate_context_user_source_rate"] == 1.0
            and row["metrics"]["candidate_context_exact_source_rate"] == 1.0
            for row in candidate_rows
        ),
        "no_assistant_turn_admitted_to_candidate_context": bool(candidate_rows)
        and all(
            row["metrics"]["candidate_assistant_turn_admission_rate"] == 0.0
            for row in candidate_rows
        ),
        "fallback_runs_only_after_primary_insufficiency": bool(results)
        and all(
            row["conditions"][condition]["metrics"]["fallback_trigger_valid"]
            for row in results
            for condition in (reread, cue)
        ),
        "cue_unanswerable_abstention_rate_equals_one": (
            summaries[cue]["unanswerable_explicit_abstention_rate"] == 1.0
        ),
        "cue_unsafe_answer_rate_on_unanswerable_equals_zero": (
            summaries[cue]["unsafe_answer_rate_on_unanswerable"] == 0.0
        ),
        "cue_answerable_pass_strictly_higher_than_provenance": (
            summaries[cue]["answerable_semantic_case_pass_rate"]
            > summaries[provenance]["answerable_semantic_case_pass_rate"]
        ),
        "cue_overall_pass_strictly_higher_than_provenance": (
            summaries[cue]["overall_cognitive_case_pass_rate"]
            > summaries[provenance]["overall_cognitive_case_pass_rate"]
        ),
        "cue_development_answerable_not_lower_than_provenance": _not_lower(
            _rate(
                by_split["development"], cue, "answerable_semantic_case_pass_rate"
            ),
            _rate(
                by_split["development"],
                provenance,
                "answerable_semantic_case_pass_rate",
            ),
        ),
        "cue_transfer_answerable_not_lower_than_provenance": _not_lower(
            _rate(by_split["transfer"], cue, "answerable_semantic_case_pass_rate"),
            _rate(
                by_split["transfer"],
                provenance,
                "answerable_semantic_case_pass_rate",
            ),
        ),
        "no_capability_family_regression_cue_vs_provenance": bool(
            family_nonregression
        )
        and all(family_nonregression.values()),
        "cue_position_invariance_not_lower_than_provenance": (
            summaries[cue]["position_invariant_scenario_rate"]
            >= summaries[provenance]["position_invariant_scenario_rate"]
        ),
        "cue_fallback_recovery_rate_greater_than_zero": (
            summaries[cue]["fallback_semantic_recovery_rate"] is not None
            and summaries[cue]["fallback_semantic_recovery_rate"] > 0.0
        ),
        "cue_mean_latency_not_higher_than_model_reread": _not_lower(
            summaries[reread]["mean_latency_seconds"],
            summaries[cue]["mean_latency_seconds"],
        ),
        "cue_mean_prompt_tokens_not_higher_than_model_reread": _not_lower(
            summaries[reread]["mean_prompt_tokens"],
            summaries[cue]["mean_prompt_tokens"],
        ),
    }
    all_gates_pass = bool(complete and all(gates.values()))
    if not complete:
        decision = "incomplete"
    elif all_gates_pass:
        decision = "eligible_for_new_untouched_evaluation"
    else:
        decision = "reject_v4_runtime_integration"
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
        "schema": "uruha_memory_cue_extractive_report_v4",
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
            "v3_case_reuse_count": 0,
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
        CONDITIONS[2]: "R: P + model reread fallback",
        CONDITIONS[3]: "E: P + exact user-utterance fallback",
    }
    lines = [
        "# Memory cue-driven extractive fallback V4",
        "",
        "## Scope and decision",
        "",
        "This preregistered development experiment compares two fallback methods after the "
        "same provenance-gated primary path. It contains no official benchmark item and cannot "
        "authorize a runtime change.",
        "",
        f"- Complete: `{report['complete']}` ({report['completed_case_count']}/{report['expected_case_count']})",
        f"- Model: `{report['model_evidence']['name']}`",
        f"- Model digest: `{report['model_evidence']['digest']}`",
        f"- Decision: `{report['decision']}`",
        "",
        "## Overall",
        "",
        "| condition | answerable | abstention | cognitive | fallback semantic recovery | latency | prompt tokens |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for condition in CONDITIONS:
        summary = report["summaries"][condition]
        lines.append(
            f"| {labels[condition]} | "
            f"{percent(summary['answerable_semantic_case_pass_rate'])} | "
            f"{percent(summary['unanswerable_explicit_abstention_rate'])} | "
            f"{percent(summary['overall_cognitive_case_pass_rate'])} | "
            f"{percent(summary['fallback_semantic_recovery_rate'])} | "
            f"{summary['mean_latency_seconds'] or 0.0:.3f}s | "
            f"{summary['mean_prompt_tokens'] or 0.0:.1f} |"
        )

    cue = report["summaries"][CONDITIONS[3]]
    lines.extend(
        [
            "",
            "## Candidate integrity",
            "",
            f"- Exact user-source rate: {percent(cue['candidate_context_exact_source_rate'])}",
            f"- Assistant admission rate: {percent(cue['candidate_assistant_turn_admission_rate'])}",
            f"- Candidate gate sufficiency: {percent(cue['candidate_gate_sufficiency_rate'])}",
            "",
            "## Paired comparisons",
            "",
        ]
    )
    for comparison in report["paired_analysis"]:
        lines.append(
            f"- `{comparison['metric']}`: `{comparison['treatment']} - "
            f"{comparison['control']}` = {comparison['delta'] * 100:+.2f} pp; "
            f"wins/losses {comparison['mcnemar']['wins']}/{comparison['mcnemar']['losses']}; "
            f"McNemar p={comparison['mcnemar']['p_value']:.6f}; bootstrap 95% CI "
            f"[{comparison['paired_bootstrap_95_ci'][0] * 100:+.2f}, "
            f"{comparison['paired_bootstrap_95_ci'][1] * 100:+.2f}] pp."
        )

    lines.extend(["", "## Capability families", ""])
    lines.extend(
        [
            "| capability | A | P | R | E |",
            "|---|---:|---:|---:|---:|",
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
            "| case | condition | gate | abstained | spans | polarity | relation | response |",
            "|---|---|---:|---:|---:|---:|---:|---|",
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
                f"| {row['case_id']} | {condition} | {metrics['gate_sufficient']} | "
                f"{metrics['explicit_abstention']} | {metrics['required_slot_span_hit']} | "
                f"{metrics['polarity_hit']} | {metrics['relation_hit']} | {response} |"
            )
    if failures == 0:
        lines.append("| none | - | - | - | - | - | - | - |")

    lines.extend(
        [
            "",
            "## Evidence boundary",
            "",
            "Passing means only that E may proceed to a new untouched evaluation. V4 cases "
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
    parser.add_argument("--case-id", action="append", default=[])
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
    if args.case_id:
        requested = set(args.case_id)
        known = {case["case_id"] for case in dataset["cases"]}
        unknown = requested - known
        if unknown:
            raise ValueError(f"Unknown case IDs: {sorted(unknown)}")
        pending = [case for case in pending if case["case_id"] in requested]
    if args.max_items:
        pending = pending[: args.max_items]

    for index, case in enumerate(pending, start=1):
        print(f"[{index}/{len(pending)}] {case['case_id']}", flush=True)
        results.append(
            run_case(
                case,
                chat,
                inference["candidate_limit"],
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
