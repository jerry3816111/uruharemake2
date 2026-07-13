#!/usr/bin/env python3
"""Run the frozen evidence-ledger protocol once on LongMemEval held-out data."""

import argparse
import datetime
import json
import random
from pathlib import Path

import run_longmemeval_evidence_ledger_development as development_module
import run_longmemeval_salience_heldout as salience_heldout_module
from project_paths import (
    LONGMEMEVAL_DEVELOPMENT_CANDIDATE_CACHE_PATH,
    LONGMEMEVAL_EVIDENCE_LEDGER_DEVELOPMENT_REPORT_JSON_PATH,
    LONGMEMEVAL_EVIDENCE_LEDGER_HELDOUT_REPORT_JSON_PATH,
    LONGMEMEVAL_EVIDENCE_LEDGER_HELDOUT_REPORT_MD_PATH,
    LONGMEMEVAL_FROZEN_CANDIDATE_CACHE_PATH,
    LONGMEMEVAL_RETRIEVAL_REPORT_JSON_PATH,
    LONGMEMEVAL_S_CLEANED_DATASET_PATH,
)
from run_longmemeval_evidence_ledger_development import (
    CONDITIONS,
    TARGET_TASK,
    generate_condition,
    generate_notes,
    generate_question_frame,
    inference_token_diagnostics,
    local_diagnostic_judge,
    ollama_chat,
    ollama_model_evidence,
    paired_binary_analysis,
    retrieval_conditioned_summary,
    selected_sessions,
    summarize,
)
from run_longmemeval_retrieval_benchmark import (
    SPLIT_SALT,
    atomic_write_json,
    canonical_sha256,
    file_sha256,
    load_and_validate_dataset,
    preregistered_split,
)
from run_longmemeval_salience_development import benchmark_reference_time
from run_longmemeval_salience_heldout import (
    validate_candidate_cache as validate_frozen_candidate_cache,
)


SCOPE = "longmemeval_evidence_ledger_heldout_first_observation_v1"
DEVELOPMENT_SCOPE = "longmemeval_evidence_ledger_development_only_v3"
EXPECTED_DEVELOPMENT_COUNT = 18
EXPECTED_HELDOUT_COUNT = 54
SIGNIFICANCE_ALPHA = 0.05
BOOTSTRAP_RESAMPLES = 10000
BOOTSTRAP_SEED = 20260714


def current_heldout_implementation_evidence():
    return {
        "heldout_runner_sha256": file_sha256(__file__),
        "frozen_development_implementation": (
            development_module.current_implementation_evidence()
        ),
        "frozen_candidate_validator_module_sha256": file_sha256(
            Path(salience_heldout_module.__file__).resolve()
        ),
    }


def validate_development_gate(development_report, data_evidence, baseline_report):
    boundary = development_report.get("data_boundary") or {}
    control = development_report.get("matched_control") or {}
    decision = development_report.get("decision") or {}
    if development_report.get("scope") != DEVELOPMENT_SCOPE:
        raise ValueError("Evidence-ledger development scope differs")
    if development_report.get("complete") is not True:
        raise ValueError("Evidence-ledger development report is incomplete")
    if boundary.get("split") != "development" or boundary.get("task") != TARGET_TASK:
        raise ValueError("Evidence-ledger development data boundary differs")
    if boundary.get("development_population_question_count") != EXPECTED_DEVELOPMENT_COUNT:
        raise ValueError("Evidence-ledger development population differs")
    if boundary.get("development_population_complete") is not True:
        raise ValueError("Evidence-ledger development population is incomplete")
    if development_report.get("completed_question_count") != EXPECTED_DEVELOPMENT_COUNT:
        raise ValueError("Evidence-ledger development result count differs")
    if boundary.get("test_question_count_evaluated") != 0:
        raise ValueError("Development report crossed the held-out boundary")
    if boundary.get("dataset_sha256") != data_evidence["sha256"]:
        raise ValueError("Development report dataset SHA differs")
    if boundary.get("split_salt") != SPLIT_SALT:
        raise ValueError("Development report split salt differs")
    if boundary.get("baseline_report_sha256") != file_sha256(
        LONGMEMEVAL_RETRIEVAL_REPORT_JSON_PATH
    ):
        raise ValueError("Development report baseline SHA differs")
    if boundary.get("candidate_cache_sha256") != file_sha256(
        LONGMEMEVAL_DEVELOPMENT_CANDIDATE_CACHE_PATH
    ):
        raise ValueError("Development candidate cache changed after freeze")
    if development_report.get("results_sha256") != canonical_sha256(
        development_report.get("results") or []
    ):
        raise ValueError("Development result payload SHA differs")
    if development_report.get("implementation_evidence") != (
        development_module.current_implementation_evidence()
    ):
        raise ValueError("Frozen evidence-ledger implementation changed")
    if list(control.get("conditions") or []) != list(CONDITIONS):
        raise ValueError("Development conditions differ")
    if decision.get("authorize_test_evaluation") is not True:
        raise ValueError("Development report did not authorize held-out evaluation")
    if decision.get("authorize_runtime_change") is not False:
        raise ValueError("Development report cannot pre-authorize runtime changes")
    reference_time = benchmark_reference_time(baseline_report)
    if boundary.get("ranking_reference_time") != reference_time.isoformat(
        timespec="seconds"
    ):
        raise ValueError("Development ranking reference time differs")
    return {
        "model": control.get("model"),
        "model_evidence": control.get("model_evidence"),
        "seed": control.get("seed"),
        "top_k": control.get("top_k"),
        "reference_time": reference_time,
    }


def load_heldout_rows():
    data, data_evidence = load_and_validate_dataset(
        LONGMEMEVAL_S_CLEANED_DATASET_PATH
    )
    baseline_report = json.loads(
        Path(LONGMEMEVAL_RETRIEVAL_REPORT_JSON_PATH).read_text(encoding="utf-8")
    )
    development_report = json.loads(
        Path(LONGMEMEVAL_EVIDENCE_LEDGER_DEVELOPMENT_REPORT_JSON_PATH).read_text(
            encoding="utf-8"
        )
    )
    frozen = json.loads(
        Path(LONGMEMEVAL_FROZEN_CANDIDATE_CACHE_PATH).read_text(encoding="utf-8")
    )
    cached_rows = validate_frozen_candidate_cache(
        frozen,
        data,
        baseline_report,
        LONGMEMEVAL_RETRIEVAL_REPORT_JSON_PATH,
    )
    frozen_config = validate_development_gate(
        development_report,
        data_evidence,
        baseline_report,
    )
    official_by_id = {row["question_id"]: row for row in data}
    rows = []
    for cached in cached_rows:
        question_id = cached["question_id"]
        official = official_by_id[question_id]
        if cached.get("split") != "test" or official.get("question_type") != TARGET_TASK:
            continue
        if preregistered_split(question_id) != "test" or question_id.endswith("_abs"):
            raise ValueError("Runner attempted to cross the held-out data boundary")
        rows.append(
            {
                **cached,
                "answer": official["answer"],
                "answer_session_ids": list(official.get("answer_session_ids") or []),
            }
        )
    rows.sort(key=lambda row: row["question_id"])
    if len(rows) != EXPECTED_HELDOUT_COUNT:
        raise ValueError(
            f"Held-out {TARGET_TASK} population differs: "
            f"{len(rows)} != {EXPECTED_HELDOUT_COUNT}"
        )
    return (
        rows,
        data_evidence,
        frozen,
        baseline_report,
        development_report,
        frozen_config,
    )


def _condition_value(condition, metric):
    if metric == "strict_answer_support":
        return bool(condition.get(metric))
    if metric == "local_judge":
        return bool((condition.get("local_judge") or {}).get("label"))
    raise ValueError(f"Unsupported metric: {metric}")


def paired_condition_analysis(results, baseline, treatment, metric):
    differences = []
    counts = {
        "both_correct": 0,
        "treatment_wins": 0,
        "treatment_losses": 0,
        "both_wrong": 0,
    }
    for row in results:
        baseline_value = _condition_value(row["conditions"][baseline], metric)
        treatment_value = _condition_value(row["conditions"][treatment], metric)
        differences.append(int(treatment_value) - int(baseline_value))
        if baseline_value and treatment_value:
            counts["both_correct"] += 1
        elif not baseline_value and treatment_value:
            counts["treatment_wins"] += 1
        elif baseline_value and not treatment_value:
            counts["treatment_losses"] += 1
        else:
            counts["both_wrong"] += 1
    development_style = paired_binary_analysis(
        [
            {
                **row,
                "conditions": {
                    "direct_chronological": row["conditions"][baseline],
                    "versioned_ledger": row["conditions"][treatment],
                },
            }
            for row in results
        ],
        metric,
    )
    counts["net_treatment_wins"] = (
        counts["treatment_wins"] - counts["treatment_losses"]
    )
    counts["paired_rate_delta"] = (
        sum(differences) / len(differences) if differences else 0.0
    )
    counts["discordant_pairs"] = development_style["discordant_pairs"]
    counts["exact_mcnemar_two_sided_p"] = development_style[
        "exact_mcnemar_two_sided_p"
    ]
    counts["bootstrap_95_ci"] = paired_delta_bootstrap_ci(differences)
    return counts


def paired_delta_bootstrap_ci(differences):
    if not differences:
        return [0.0, 0.0]
    rng = random.Random(BOOTSTRAP_SEED)
    size = len(differences)
    estimates = []
    for _ in range(BOOTSTRAP_RESAMPLES):
        estimates.append(
            sum(differences[rng.randrange(size)] for _ in range(size)) / size
        )
    estimates.sort()
    lower = estimates[int(0.025 * BOOTSTRAP_RESAMPLES)]
    upper = estimates[int(0.975 * BOOTSTRAP_RESAMPLES) - 1]
    return [lower, upper]


def evaluate_row(row, frozen_config, chat):
    sessions = selected_sessions(
        row,
        frozen_config["top_k"],
        frozen_config["reference_time"],
    )
    conditions = {}
    direct = generate_condition(row, sessions, "direct_chronological", chat)
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
    return {
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


def build_report(
    rows,
    results,
    data_evidence,
    frozen_cache,
    development_report,
    frozen_config,
    model_evidence,
):
    complete = len(results) == len(rows) == EXPECTED_HELDOUT_COUNT
    summaries = summarize(results)
    comparisons = {
        "ledger_vs_direct_strict": paired_condition_analysis(
            results,
            "direct_chronological",
            "versioned_ledger",
            "strict_answer_support",
        ),
        "ledger_vs_direct_local_judge": paired_condition_analysis(
            results,
            "direct_chronological",
            "versioned_ledger",
            "local_judge",
        ),
        "ledger_vs_grounded_notes_strict": paired_condition_analysis(
            results,
            "grounded_notes",
            "versioned_ledger",
            "strict_answer_support",
        ),
    }
    ledger = summaries["versioned_ledger"]
    strict = comparisons["ledger_vs_direct_strict"]
    structural_integrity = bool(
        complete
        and ledger["question_frame_parse_rate"] == 1.0
        and ledger["all_note_schema_parse_rate"] == 1.0
        and ledger["all_quote_grounding_rate"] == 1.0
        and ledger["ledger_schema_parse_rate"] == 1.0
        and ledger["ledger_grounding_rate"] == 1.0
    )
    supports_hypothesis = bool(
        structural_integrity
        and strict["paired_rate_delta"] > 0
        and strict["treatment_wins"] > strict["treatment_losses"]
        and strict["exact_mcnemar_two_sided_p"] < SIGNIFICANCE_ALPHA
    )
    if not complete:
        decision_zh = (
            f"一次性 held-out 執行中：{len(results)}/{EXPECTED_HELDOUT_COUNT}；"
            "尚不得解讀結果。"
        )
    elif supports_hypothesis:
        decision_zh = (
            "凍結的 evidence ledger 在 held-out 嚴格診斷中呈現顯著正增益；"
            "只授權另開 development-only runtime 整合實驗，不直接修改正式 runtime。"
        )
    else:
        decision_zh = (
            "一次性 held-out 未通過預先設定的顯著正增益門檻；"
            "不得宣稱 evidence ledger 已被外部資料支持，也不得修改正式 runtime。"
        )
    result_ids = [row["question_id"] for row in results]
    return {
        "scope": SCOPE,
        "generated_at": datetime.datetime.now().astimezone().isoformat(
            timespec="seconds"
        ),
        "status": "complete" if complete else "in_progress",
        "protocol": {
            "first_observation_only": True,
            "task": TARGET_TASK,
            "expected_question_count": EXPECTED_HELDOUT_COUNT,
            "primary_diagnostic": "strict_answer_support",
            "paired_test": "exact two-sided McNemar",
            "significance_alpha": SIGNIFICANCE_ALPHA,
            "bootstrap_resamples": BOOTSTRAP_RESAMPLES,
            "runtime_change_requires_separate_experiment": True,
        },
        "data_boundary": {
            "split": "test",
            "task": TARGET_TASK,
            "question_count": len(rows),
            "completed_question_count": len(results),
            "development_question_count": EXPECTED_DEVELOPMENT_COUNT,
            "dataset_sha256": data_evidence["sha256"],
            "candidate_cache_sha256": file_sha256(
                LONGMEMEVAL_FROZEN_CANDIDATE_CACHE_PATH
            ),
            "candidate_cache_schema": frozen_cache.get("schema"),
            "candidate_cache_contains_gold_answers": frozen_cache.get(
                "contains_gold_answers"
            ),
            "baseline_report_sha256": file_sha256(
                LONGMEMEVAL_RETRIEVAL_REPORT_JSON_PATH
            ),
            "split_salt": SPLIT_SALT,
            "selected_question_ids_sha256": canonical_sha256(
                [row["question_id"] for row in rows]
            ),
            "completed_question_ids_sha256": canonical_sha256(result_ids),
        },
        "frozen_evidence": {
            "development_scope": development_report["scope"],
            "development_report_sha256": file_sha256(
                LONGMEMEVAL_EVIDENCE_LEDGER_DEVELOPMENT_REPORT_JSON_PATH
            ),
            "development_results_sha256": development_report["results_sha256"],
            "development_implementation_evidence": development_report[
                "implementation_evidence"
            ],
            "heldout_implementation_evidence": (
                current_heldout_implementation_evidence()
            ),
            "model": frozen_config["model"],
            "model_evidence": model_evidence,
            "seed": frozen_config["seed"],
            "top_k": frozen_config["top_k"],
            "reference_time": frozen_config["reference_time"].isoformat(
                timespec="seconds"
            ),
            "conditions": list(CONDITIONS),
        },
        "question_count": len(rows),
        "completed_question_count": len(results),
        "complete": complete,
        "summaries": summaries,
        "paired_comparisons": comparisons,
        "retrieval_conditioning": retrieval_conditioned_summary(results),
        "inference_token_diagnostics": inference_token_diagnostics(results),
        "results_sha256": canonical_sha256(results),
        "results": results,
        "decision": {
            "structural_integrity": structural_integrity,
            "supports_evidence_ledger_hypothesis": supports_hypothesis,
            "authorize_followup_development_runtime_pilot": supports_hypothesis,
            "authorize_runtime_change": False,
            "decision_zh": decision_zh,
        },
        "research_boundary": (
            "The official held-out split is observed as one frozen population. Gold answers "
            "are never passed to generation prompts and are used only after each response "
            "for scoring. Strict answer support and "
            "the local Qwen official-style judge are diagnostic metrics, not official "
            "LongMemEval accuracy. A successful held-out result does not directly authorize "
            "a production runtime change."
        ),
    }


def validate_resume_checkpoint(report, rows, binding):
    if report.get("scope") != SCOPE:
        raise ValueError("Checkpoint scope differs")
    if report.get("complete") is True:
        raise ValueError("Held-out first observation is already complete")
    if report.get("results_sha256") != canonical_sha256(report.get("results") or []):
        raise ValueError("Checkpoint result payload SHA differs")
    expected_ids = [row["question_id"] for row in rows]
    completed_ids = [row.get("question_id") for row in report.get("results") or []]
    if completed_ids != expected_ids[: len(completed_ids)]:
        raise ValueError("Checkpoint results are not a valid population prefix")
    frozen = report.get("frozen_evidence") or {}
    boundary = report.get("data_boundary") or {}
    expected_frozen = binding["frozen_evidence"]
    for key, expected in expected_frozen.items():
        if frozen.get(key) != expected:
            raise ValueError(f"Checkpoint frozen evidence differs: {key}")
    for key, expected in binding["data_boundary"].items():
        if boundary.get(key) != expected:
            raise ValueError(f"Checkpoint data boundary differs: {key}")
    return list(report.get("results") or [])


def checkpoint_binding(
    rows,
    data_evidence,
    development_report,
    frozen_config,
    model_evidence,
):
    return {
        "data_boundary": {
            "dataset_sha256": data_evidence["sha256"],
            "candidate_cache_sha256": file_sha256(
                LONGMEMEVAL_FROZEN_CANDIDATE_CACHE_PATH
            ),
            "baseline_report_sha256": file_sha256(
                LONGMEMEVAL_RETRIEVAL_REPORT_JSON_PATH
            ),
            "selected_question_ids_sha256": canonical_sha256(
                [row["question_id"] for row in rows]
            ),
        },
        "frozen_evidence": {
            "development_scope": development_report["scope"],
            "development_report_sha256": file_sha256(
                LONGMEMEVAL_EVIDENCE_LEDGER_DEVELOPMENT_REPORT_JSON_PATH
            ),
            "development_results_sha256": development_report["results_sha256"],
            "development_implementation_evidence": development_report[
                "implementation_evidence"
            ],
            "heldout_implementation_evidence": (
                current_heldout_implementation_evidence()
            ),
            "model": frozen_config["model"],
            "model_evidence": model_evidence,
            "seed": frozen_config["seed"],
            "top_k": frozen_config["top_k"],
            "reference_time": frozen_config["reference_time"].isoformat(
                timespec="seconds"
            ),
            "conditions": list(CONDITIONS),
        },
    }


def write_markdown(report, path):
    lines = [
        "# LongMemEval Evidence Ledger 一次性 Held-out 實驗",
        "",
        f"- 狀態：`{report['status']}`",
        f"- 題型：`{TARGET_TASK}`",
        (
            f"- 完成：{report['completed_question_count']}/"
            f"{report['question_count']} 題"
        ),
        "- 三組固定同一模型、同一 top-5 記憶與同一生成參數。",
        "- 唯一自變變因：檢索後如何整合跨時間證據。",
        "- 本機 Qwen judge 與嚴格字面支持率都是診斷，不是官方 LongMemEval 分數。",
        "",
        "## 結果",
        "",
        "| 條件 | 嚴格答案支持率 | 本機診斷 judge | 平均端到端延遲 |",
        "|---|---:|---:|---:|",
    ]
    for condition in CONDITIONS:
        values = report["summaries"][condition]
        lines.append(
            f"| {condition} | {100 * values['strict_answer_support_rate']:.2f}% | "
            f"{100 * values['local_diagnostic_judge_rate']:.2f}% | "
            f"{values['mean_end_to_end_latency_seconds']:.1f}s |"
        )
    lines.extend(
        [
            "",
            "## 配對比較",
            "",
            "| 比較 | 修正 | 弄錯 | 差異 | 95% bootstrap CI | McNemar p |",
            "|---|---:|---:|---:|---:|---:|",
        ]
    )
    for label, values in report["paired_comparisons"].items():
        interval = values["bootstrap_95_ci"]
        lines.append(
            f"| {label} | {values['treatment_wins']} | "
            f"{values['treatment_losses']} | "
            f"{100 * values['paired_rate_delta']:+.2f} pp | "
            f"[{100 * interval[0]:+.2f}, {100 * interval[1]:+.2f}] pp | "
            f"{values['exact_mcnemar_two_sided_p']:.6g} |"
        )
    lines.extend(
        [
            "",
            "## 決定",
            "",
            report["decision"]["decision_zh"],
            "",
            "正式 runtime 修改：**未授權**。",
            "",
        ]
    )
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text("\n".join(lines), encoding="utf-8")
    temporary.replace(path)


def persist_report(report):
    atomic_write_json(LONGMEMEVAL_EVIDENCE_LEDGER_HELDOUT_REPORT_JSON_PATH, report)
    write_markdown(report, LONGMEMEVAL_EVIDENCE_LEDGER_HELDOUT_REPORT_MD_PATH)


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--endpoint", default="http://localhost:11434/api/chat")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args(argv)

    (
        rows,
        data_evidence,
        frozen_cache,
        _baseline_report,
        development_report,
        frozen_config,
    ) = load_heldout_rows()
    model_evidence = ollama_model_evidence(
        frozen_config["model"],
        args.endpoint,
    )
    if model_evidence != frozen_config["model_evidence"]:
        raise ValueError("Installed model digest differs from the development freeze")
    binding = checkpoint_binding(
        rows,
        data_evidence,
        development_report,
        frozen_config,
        model_evidence,
    )
    output_json = Path(LONGMEMEVAL_EVIDENCE_LEDGER_HELDOUT_REPORT_JSON_PATH)
    output_md = Path(LONGMEMEVAL_EVIDENCE_LEDGER_HELDOUT_REPORT_MD_PATH)
    if args.resume:
        if not output_json.is_file():
            raise FileNotFoundError("No held-out checkpoint exists to resume")
        checkpoint = json.loads(output_json.read_text(encoding="utf-8"))
        results = validate_resume_checkpoint(checkpoint, rows, binding)
    else:
        existing = [str(path) for path in (output_json, output_md) if path.exists()]
        if existing:
            raise FileExistsError(
                "Held-out first observation already started; use --resume only for an "
                "unchanged incomplete checkpoint: " + ", ".join(existing)
            )
        results = []

    def chat(
        prompt,
        max_tokens=development_module.ANSWER_MAX_TOKENS,
        format_schema=None,
    ):
        return ollama_chat(
            prompt,
            model=frozen_config["model"],
            endpoint=args.endpoint,
            seed=frozen_config["seed"],
            max_tokens=max_tokens,
            format_schema=format_schema,
        )

    initial_report = build_report(
        rows,
        results,
        data_evidence,
        frozen_cache,
        development_report,
        frozen_config,
        model_evidence,
    )
    persist_report(initial_report)

    for index, row in enumerate(rows[len(results) :], start=len(results) + 1):
        results.append(evaluate_row(row, frozen_config, chat))
        report = build_report(
            rows,
            results,
            data_evidence,
            frozen_cache,
            development_report,
            frozen_config,
            model_evidence,
        )
        persist_report(report)
        print(
            f"completed={index}/{len(rows)} question_id={row['question_id']}",
            flush=True,
        )

    final_report = build_report(
        rows,
        results,
        data_evidence,
        frozen_cache,
        development_report,
        frozen_config,
        model_evidence,
    )
    persist_report(final_report)
    print(
        json.dumps(
            {
                "status": final_report["status"],
                "question_count": final_report["question_count"],
                "summaries": final_report["summaries"],
                "paired_comparisons": final_report["paired_comparisons"],
                "decision": final_report["decision"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
