#!/usr/bin/env python3
"""Run the preregistered untouched V5 replication of the frozen V4 treatment."""

import argparse
import datetime as dt
import json
from pathlib import Path

from run_longmemeval_evidence_ledger_development import ollama_chat, ollama_model_evidence
from run_longmemeval_retrieval_benchmark import (
    atomic_write_json,
    canonical_sha256,
    file_sha256,
)
from run_memory_cue_extractive_v4 import (
    CONDITIONS,
    percent,
    run_case,
    summarize_group,
)
from run_memory_provenance_reread_v3 import paired_analysis, position_invariant_rate


ROOT = Path(__file__).resolve().parent
PREREGISTRATION_PATH = (
    ROOT / "configs" / "memory_cue_extractive_holdout_v5_preregistration.json"
)
DEFAULT_REPORT_JSON = ROOT / "reports" / "memory_cue_extractive_holdout_v5_report.json"
DEFAULT_REPORT_MD = ROOT / "reports" / "memory_cue_extractive_holdout_v5_report.md"

CONTROL, PROVENANCE, REREAD, CUE = CONDITIONS
PRIOR_DATASETS = (
    ROOT / "datasets" / "memory_utterance_attention_v1.json",
    ROOT / "datasets" / "memory_highlight_span_v2.json",
    ROOT / "datasets" / "memory_provenance_reread_v3.json",
    ROOT / "datasets" / "memory_cue_extractive_v4.json",
)


def load_protocol(preregistration_path=PREREGISTRATION_PATH):
    protocol_path = Path(preregistration_path)
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    dataset_path = ROOT / protocol["dataset"]["path"]
    if file_sha256(dataset_path) != protocol["dataset"]["file_sha256"]:
        raise ValueError("Frozen V5 dataset file hash mismatch")
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    if canonical_sha256(dataset["cases"]) != protocol["dataset"]["cases_sha256"]:
        raise ValueError("Frozen V5 case hash mismatch")
    if len(dataset["cases"]) != protocol["dataset"]["case_count"]:
        raise ValueError("Frozen V5 case count mismatch")
    builder = ROOT / "build_memory_cue_extractive_holdout_v5.py"
    if file_sha256(builder) != protocol["dataset"]["builder_sha256"]:
        raise ValueError("Frozen V5 dataset builder hash mismatch")

    for name, component in protocol["frozen_v4_treatment"].items():
        if not isinstance(component, dict) or "path" not in component:
            continue
        actual = file_sha256(ROOT / component["path"])
        if actual != component["sha256"]:
            raise ValueError(f"Frozen V4 treatment hash mismatch: {name}")

    prior_scenarios = set()
    prior_questions = set()
    for path in PRIOR_DATASETS:
        prior = json.loads(path.read_text(encoding="utf-8"))
        prior_scenarios.update(row["scenario_id"] for row in prior["cases"])
        prior_questions.update(row["question"] for row in prior["cases"])
    current_scenarios = {row["scenario_id"] for row in dataset["cases"]}
    current_questions = {row["question"] for row in dataset["cases"]}
    if current_scenarios & prior_scenarios or current_questions & prior_questions:
        raise ValueError("V5 reuses a prior scenario or question")
    return protocol, dataset, dataset_path


def implementation_evidence(dataset_path, preregistration_path=PREREGISTRATION_PATH):
    paths = {
        "v5_runner": Path(__file__),
        "v4_runner": ROOT / "run_memory_cue_extractive_v4.py",
        "cue_module": ROOT / "memory_cue_extractive.py",
        "provenance_module": ROOT / "memory_provenance_reread.py",
        "attention_module": ROOT / "memory_utterance_attention.py",
        "ledger_module": ROOT / "memory_evidence_ledger.py",
        "ollama_runner_dependency": ROOT
        / "run_longmemeval_evidence_ledger_development.py",
        "dataset_builder": ROOT / "build_memory_cue_extractive_holdout_v5.py",
        "dataset": Path(dataset_path),
        "preregistration": Path(preregistration_path),
    }
    return {f"{name}_sha256": file_sha256(path) for name, path in paths.items()}


def _rate(group, condition, key):
    return group[condition][key]


def _not_lower(treatment, control):
    return treatment is not None and control is not None and treatment >= control


def _paired_state_counts(results, control, treatment, metric):
    wins = []
    losses = []
    both_pass = 0
    neither_pass = 0
    for row in results:
        left = row["conditions"][control]["metrics"].get(metric)
        right = row["conditions"][treatment]["metrics"].get(metric)
        if left is None or right is None:
            continue
        if left and right:
            both_pass += 1
        elif right:
            wins.append(row["case_id"])
        elif left:
            losses.append(row["case_id"])
        else:
            neither_pass += 1
    return {
        "both_pass": both_pass,
        "treatment_only": len(wins),
        "control_only": len(losses),
        "neither_pass": neither_pass,
        "treatment_win_case_ids": wins,
        "treatment_loss_case_ids": losses,
    }


def _summarize_subsets(results, key, ordered_values=None):
    values = ordered_values or sorted({row[key] for row in results})
    output = {}
    for value in values:
        subset = [row for row in results if row[key] == value]
        if not subset:
            continue
        output[value] = {
            condition: summarize_group(subset, condition) for condition in CONDITIONS
        }
        if key == "split":
            for condition in CONDITIONS:
                output[value][condition]["position_invariant_scenario_rate"] = (
                    position_invariant_rate(subset, condition)
                )
    return output


def build_analysis(results, protocol, complete):
    summaries = {condition: summarize_group(results, condition) for condition in CONDITIONS}
    for condition in CONDITIONS:
        summaries[condition]["position_invariant_scenario_rate"] = position_invariant_rate(
            results, condition
        )
    by_split = _summarize_subsets(results, "split", ("holdout_a", "holdout_b"))
    by_capability = _summarize_subsets(results, "capability")
    by_position = _summarize_subsets(
        results, "evidence_position", ("beginning", "middle", "end")
    )

    comparisons = (
        (CONTROL, PROVENANCE),
        (PROVENANCE, REREAD),
        (PROVENANCE, CUE),
        (REREAD, CUE),
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

    cue_vs_provenance = _paired_state_counts(
        results, PROVENANCE, CUE, "overall_cognitive_case_pass"
    )
    cue_vs_reread = _paired_state_counts(
        results, REREAD, CUE, "overall_cognitive_case_pass"
    )
    recovered = [
        row
        for row in results
        if row["gold"]["answerable"]
        and row["conditions"][CUE]["metrics"]["fallback_semantic_recovered"]
    ]
    recovered_scenarios = sorted({row["scenario_id"] for row in recovered})
    recovery_splits = sorted({row["split"] for row in recovered})
    candidate_rows = [
        row["conditions"][CUE]
        for row in results
        if row["conditions"][CUE]["metrics"]["fallback_triggered"]
    ]
    family_nonregression = {
        capability: _not_lower(
            _rate(group, CUE, "overall_cognitive_case_pass_rate"),
            _rate(group, PROVENANCE, "overall_cognitive_case_pass_rate"),
        )
        for capability, group in by_capability.items()
    }

    gates = {
        "dataset_and_treatment_hashes_match": True,
        "no_v1_v2_v3_v4_scenario_or_question_reuse": True,
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
            for condition in (REREAD, CUE)
        ),
        "cue_unanswerable_abstention_rate_equals_one": summaries[CUE][
            "unanswerable_explicit_abstention_rate"
        ]
        == 1.0,
        "cue_unsafe_answer_rate_on_unanswerable_equals_zero": summaries[CUE][
            "unsafe_answer_rate_on_unanswerable"
        ]
        == 0.0,
        "cue_answerable_pass_not_lower_than_provenance": _not_lower(
            summaries[CUE]["answerable_semantic_case_pass_rate"],
            summaries[PROVENANCE]["answerable_semantic_case_pass_rate"],
        ),
        "cue_overall_pass_not_lower_than_provenance": _not_lower(
            summaries[CUE]["overall_cognitive_case_pass_rate"],
            summaries[PROVENANCE]["overall_cognitive_case_pass_rate"],
        ),
        "cue_vs_provenance_paired_loss_count_equals_zero": cue_vs_provenance[
            "control_only"
        ]
        == 0,
        "cue_vs_provenance_distinct_recovered_scenario_count_at_least_two": len(
            recovered_scenarios
        )
        >= 2,
        "cue_recovery_represented_in_both_holdout_splits": set(recovery_splits)
        == {"holdout_a", "holdout_b"},
        "no_capability_family_regression_cue_vs_provenance": bool(
            family_nonregression
        )
        and all(family_nonregression.values()),
        "cue_position_invariance_not_lower_than_provenance": _not_lower(
            summaries[CUE]["position_invariant_scenario_rate"],
            summaries[PROVENANCE]["position_invariant_scenario_rate"],
        ),
        "cue_correctness_not_lower_than_model_reread": _not_lower(
            summaries[CUE]["overall_cognitive_case_pass_rate"],
            summaries[REREAD]["overall_cognitive_case_pass_rate"],
        )
        and _not_lower(
            summaries[CUE]["answerable_semantic_case_pass_rate"],
            summaries[REREAD]["answerable_semantic_case_pass_rate"],
        ),
        "cue_vs_reread_paired_loss_count_equals_zero": cue_vs_reread["control_only"]
        == 0,
        "cue_mean_latency_strictly_lower_than_model_reread": summaries[CUE][
            "mean_latency_seconds"
        ]
        < summaries[REREAD]["mean_latency_seconds"],
        "cue_mean_prompt_tokens_strictly_lower_than_model_reread": summaries[CUE][
            "mean_prompt_tokens"
        ]
        < summaries[REREAD]["mean_prompt_tokens"],
    }
    breadth_gates = {
        "cue_vs_provenance_distinct_recovered_scenario_count_at_least_two",
        "cue_recovery_represented_in_both_holdout_splits",
    }
    quality_and_safety_pass = bool(
        complete
        and all(value for key, value in gates.items() if key not in breadth_gates)
    )
    all_gates_pass = bool(complete and all(gates.values()))
    if not complete:
        decision = "incomplete"
    elif all_gates_pass:
        decision = "eligible_for_separate_shadow_integration_review_only"
    elif quality_and_safety_pass:
        decision = "replicated_efficiency_only_no_runtime"
    else:
        decision = "reject_v5_integration"
    return {
        "summaries": summaries,
        "by_split": by_split,
        "by_capability": by_capability,
        "by_position": by_position,
        "paired_analysis": paired,
        "paired_states": {
            "cue_vs_provenance": cue_vs_provenance,
            "cue_vs_reread": cue_vs_reread,
        },
        "recovery_audit": {
            "case_count": len(recovered),
            "case_ids": [row["case_id"] for row in recovered],
            "distinct_scenario_count": len(recovered_scenarios),
            "scenario_ids": recovered_scenarios,
            "splits": recovery_splits,
        },
        "nonregression_audit": {"by_capability": family_nonregression},
        "gates": gates,
        "quality_and_safety_pass": quality_and_safety_pass,
        "all_gates_pass": all_gates_pass,
        "decision": decision,
    }


def build_report(protocol, dataset_path, model_evidence, implementation, results):
    complete = len(results) == protocol["dataset"]["case_count"]
    return {
        "schema": "uruha_memory_cue_extractive_holdout_report_v5",
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "complete": complete,
        "completed_case_count": len(results),
        "expected_case_count": protocol["dataset"]["case_count"],
        "protocol": protocol,
        "dataset_path": str(dataset_path.relative_to(ROOT)),
        "model_evidence": model_evidence,
        "implementation_evidence": implementation,
        **build_analysis(results, protocol, complete),
        "results": results,
        "results_sha256": canonical_sha256(results),
        "research_boundary": {
            "official_benchmark_items_used": 0,
            "prior_scenario_or_question_reuse_count": 0,
            "v4_treatment_modified": False,
            "active_runtime_change_authorized": False,
        },
    }


def render_markdown(report):
    labels = {
        CONTROL: "A: full-session freeform",
        PROVENANCE: "P: provenance gate",
        REREAD: "R: model reread fallback",
        CUE: "E: exact user-utterance fallback",
    }
    lines = [
        "# Memory cue-driven fallback V5 untouched holdout",
        "",
        "## Decision",
        "",
        f"- Complete: `{report['complete']}` ({report['completed_case_count']}/{report['expected_case_count']})",
        f"- Decision: `{report['decision']}`",
        "- Active runtime change authorized: `False`",
        "",
        "## Overall",
        "",
        "| Condition | Answerable | Unanswerable abstention | Overall | Position-invariant | Latency | Prompt tokens |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for condition in CONDITIONS:
        row = report["summaries"][condition]
        lines.append(
            f"| {labels[condition]} | "
            f"{percent(row['answerable_semantic_case_pass_rate'])} | "
            f"{percent(row['unanswerable_explicit_abstention_rate'])} | "
            f"{percent(row['overall_cognitive_case_pass_rate'])} | "
            f"{percent(row['position_invariant_scenario_rate'])} | "
            f"{row['mean_latency_seconds'] or 0.0:.3f}s | "
            f"{row['mean_prompt_tokens'] or 0.0:.1f} |"
        )
    recovery = report["recovery_audit"]
    lines.extend(
        [
            "",
            "## Recovery breadth",
            "",
            f"- Recovered cases: `{recovery['case_count']}`",
            f"- Distinct recovered scenarios: `{recovery['distinct_scenario_count']}`",
            f"- Recovery splits: `{', '.join(recovery['splits']) or 'none'}`",
            f"- Scenario IDs: `{', '.join(recovery['scenario_ids']) or 'none'}`",
            "",
            "## Gates",
            "",
        ]
    )
    lines.extend(
        f"- {'PASS' if passed else 'FAIL'} `{name}`"
        for name, passed in report["gates"].items()
    )
    lines.extend(
        [
            "",
            "## Failure localization",
            "",
            "| Case | Condition | Gate | Abstained | Spans | Polarity | Relation | Response |",
            "|---|---|---:|---:|---:|---:|---:|---|",
        ]
    )
    failures = 0
    for result in report["results"]:
        for condition in CONDITIONS:
            artifact = result["conditions"][condition]
            metrics = artifact["metrics"]
            if metrics["overall_cognitive_case_pass"]:
                continue
            failures += 1
            response = artifact["response"].replace("|", "/").replace("\n", " ")[:160]
            lines.append(
                f"| {result['case_id']} | {condition} | {metrics['gate_sufficient']} | "
                f"{metrics['explicit_abstention']} | {metrics['required_slot_span_hit']} | "
                f"{metrics['polarity_hit']} | {metrics['relation_hit']} | {response} |"
            )
    if not failures:
        lines.append("| none | - | - | - | - | - | - | - |")
    lines.extend(
        [
            "",
            "## Evidence boundary",
            "",
            "V5 never authorizes a default-on runtime change. Passing all gates permits "
            "only a separate review for an off-by-default shadow integration. Failure "
            "or insufficient recovery breadth preserves the current runtime.",
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
            f"Report already exists: {args.report_json}. Use --resume only after interruption."
        )

    completed = {row["case_id"] for row in results}
    pending = [case for case in dataset["cases"] if case["case_id"] not in completed]
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
