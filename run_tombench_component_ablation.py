import argparse
import contextlib
import io
import json
import os
import random
import sys
from collections import Counter, defaultdict
from contextlib import contextmanager

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EXPECTED_PYTHON = os.path.join(BASE_DIR, "Style-Bert-VITS2", "venv", "bin", "python")
EXPECTED_VENV = os.path.dirname(os.path.dirname(EXPECTED_PYTHON))


def _ensure_project_python():
    if os.path.exists(EXPECTED_PYTHON) and os.path.normpath(sys.prefix) != os.path.normpath(EXPECTED_VENV):
        clean_env = os.environ.copy()
        for key in ("PYTHONHOME", "PYTHONPATH", "CONDA_PREFIX", "CONDA_DEFAULT_ENV"):
            clean_env.pop(key, None)
        clean_env["VIRTUAL_ENV"] = EXPECTED_VENV
        clean_env["PATH"] = os.path.dirname(EXPECTED_PYTHON) + os.pathsep + clean_env.get("PATH", "")
        os.execve(EXPECTED_PYTHON, [EXPECTED_PYTHON, __file__, *sys.argv[1:]], clean_env)


_ensure_project_python()

import run_formal_brain_benchmarks_v2 as formal
import uruha_brain_mac as ubm
from openai import OpenAI
from project_paths import FORMAL_BENCHMARK_CACHE_DIR, REPORTS_DIR


DEFAULT_TASKS = [
    "Discrepant Intentions",
    "Scalar Implicature Test",
    "Faux-pas Recognition Test",
    "Hinting Task Test",
    "Strange Story Task",
]

ALL_TOMBENCH_TASKS = [
    "Ambiguous Story Task",
    "Completion of Failed Actions",
    "Discrepant Desires",
    "Discrepant Emotions",
    "Discrepant Intentions",
    "Emotion Regulation",
    "False Belief Task",
    "Faux-pas Recognition Test",
    "Hidden Emotions",
    "Hinting Task Test",
    "Knowledge-Attention Links",
    "Knowledge-Pretend Play Links",
    "Moral Emotions",
    "Multiple Desires",
    "Percepts-Knowledge Links",
    "Persuasion Story Task",
    "Prediction of Actions",
    "Scalar Implicature Test",
    "Strange Story Task",
    "Unexpected Outcome Test",
]

TASK_SETS = {
    "social": DEFAULT_TASKS,
    "all": ALL_TOMBENCH_TASKS,
}

DEFAULT_CONDITIONS = [
    "control_prompt_only",
    "trace_only",
    "verifier_direct_only",
    "trace_plus_verifier_hint",
    "trace_plus_verifier_direct",
    "deterministic_left_only",
    "surface_only_fast_prompt",
]

REPORT_PREFIX = "formal_tombench_component_ablation"


CONDITION_SPECS = {
    "control_prompt_only": {
        "label": "prompt-only control",
        "description": "Same LLM, official story/question/options only. No UruhaBrain process trace or verifier.",
        "requires_llm": True,
        "step_flags": {
            "1_understand_utterance": "llm_prompt_only",
            "2_working_memory": "disabled",
            "3_prediction_error": "disabled",
            "4_high_low_router": "disabled",
            "5_left_brain_plan": "disabled",
            "6_right_brain_surface": "not_applicable_mcq",
            "7_self_check": "disabled",
            "8_memory_update": "disabled",
        },
    },
    "trace_only": {
        "label": "left-brain process trace only",
        "description": "Adds UruhaBrain social reasoning trace to the same LLM, but disables candidate verifier.",
        "requires_llm": True,
        "step_flags": {
            "1_understand_utterance": "enabled_social_core",
            "2_working_memory": "disabled",
            "3_prediction_error": "belief_intent_conflict_proxy",
            "4_high_low_router": "high_road_only",
            "5_left_brain_plan": "enabled_process_trace",
            "6_right_brain_surface": "not_applicable_mcq",
            "7_self_check": "disabled",
            "8_memory_update": "disabled",
        },
    },
    "trace_plus_verifier_hint": {
        "label": "process trace plus self-check hint",
        "description": "Adds process trace and candidate-fit verifier explanation, but LLM still chooses the final letter.",
        "requires_llm": True,
        "env": {
            "URUHA_ENABLE_CANDIDATE_VERIFIER": "1",
            "URUHA_ENABLE_SCALAR_CANDIDATE_VERIFIER": "1",
            "URUHA_VERIFIER_DIRECT_DECISION": "0",
            "URUHA_SCALAR_VERIFIER_DIRECT_DECISION": "0",
        },
        "step_flags": {
            "1_understand_utterance": "enabled_social_core",
            "2_working_memory": "disabled",
            "3_prediction_error": "belief_intent_conflict_proxy",
            "4_high_low_router": "high_road_only",
            "5_left_brain_plan": "enabled_process_trace",
            "6_right_brain_surface": "not_applicable_mcq",
            "7_self_check": "enabled_hint_only",
            "8_memory_update": "disabled",
        },
    },
    "trace_plus_verifier_direct": {
        "label": "full ToMBench cognitive system",
        "description": "Process trace plus high-confidence candidate verifier direct decision; fallback is traced LLM.",
        "requires_llm": True,
        "env": {
            "URUHA_ENABLE_CANDIDATE_VERIFIER": "1",
            "URUHA_ENABLE_SCALAR_CANDIDATE_VERIFIER": "1",
            "URUHA_VERIFIER_DIRECT_DECISION": "1",
            "URUHA_SCALAR_VERIFIER_DIRECT_DECISION": "1",
        },
        "step_flags": {
            "1_understand_utterance": "enabled_social_core",
            "2_working_memory": "disabled",
            "3_prediction_error": "belief_intent_conflict_proxy",
            "4_high_low_router": "high_road_only",
            "5_left_brain_plan": "enabled_process_trace",
            "6_right_brain_surface": "not_applicable_mcq",
            "7_self_check": "enabled_direct_when_high_confidence",
            "8_memory_update": "disabled",
        },
    },
    "verifier_direct_only": {
        "label": "self-check verifier only",
        "description": "Candidate verifier selects directly when high-confidence; otherwise falls back to prompt-only LLM. No verifier trace is fed to the LLM.",
        "requires_llm": True,
        "step_flags": {
            "1_understand_utterance": "enabled_social_core",
            "2_working_memory": "disabled",
            "3_prediction_error": "belief_intent_conflict_proxy",
            "4_high_low_router": "high_road_only",
            "5_left_brain_plan": "minimal_marker_extraction",
            "6_right_brain_surface": "not_applicable_mcq",
            "7_self_check": "enabled_direct_when_high_confidence",
            "8_memory_update": "disabled",
        },
    },
    "deterministic_left_only": {
        "label": "left-brain deterministic solver only",
        "description": "Uses deterministic social-reasoning solver only. Uncovered rows are counted incorrect, so this measures rule coverage and precision without LLM fallback.",
        "requires_llm": False,
        "step_flags": {
            "1_understand_utterance": "enabled_rule_parser",
            "2_working_memory": "disabled",
            "3_prediction_error": "belief_intent_conflict_proxy",
            "4_high_low_router": "high_road_only",
            "5_left_brain_plan": "deterministic_solver",
            "6_right_brain_surface": "not_applicable_mcq",
            "7_self_check": "embedded_rule_confidence",
            "8_memory_update": "disabled",
        },
    },
    "surface_only_fast_prompt": {
        "label": "low-road proxy / surface-only fast prompt",
        "description": "Negative control: the same LLM sees task/question/options but not the story. This approximates removing slow contextual high-road reasoning, not the production crisis low-road.",
        "requires_llm": True,
        "step_flags": {
            "1_understand_utterance": "question_options_only",
            "2_working_memory": "disabled",
            "3_prediction_error": "disabled",
            "4_high_low_router": "forced_fast_surface_proxy",
            "5_left_brain_plan": "disabled",
            "6_right_brain_surface": "not_applicable_mcq",
            "7_self_check": "disabled",
            "8_memory_update": "disabled",
        },
    },
}

CONTROLLED_VARIABLES = {
    "benchmark": "official ToMBench rows loaded by run_formal_brain_benchmarks_v2.load_tombench_items(full=True)",
    "model": "qwen2.5:7b through the same local OpenAI-compatible endpoint for LLM conditions",
    "temperature": 0.0,
    "scoring": "exact match against official A/B/C/D answer key",
    "memory": "disabled for all ToMBench ablation conditions; no profile, episodes, recent_dialogue, or working_memory_items are passed",
    "right_brain": "not used for MCQ scoring because ToMBench only accepts option letters",
    "cache_policy": "condition-specific checkpoints; use --force-refresh for strict no-cache reruns",
}

DEPENDENT_VARIABLES = [
    "accuracy",
    "correct_count",
    "unparsed_count",
    "task_breakdown accuracy",
    "delta_vs_baseline_full_cognitive_system",
    "only_condition_correct / only_baseline_correct against baseline",
    "selection_mode_breakdown",
]


def _read_json(path):
    if not os.path.exists(path):
        return {"rows": []}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _write_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def _write_text(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def _checkpoint_rows(path):
    return {row["id"]: row for row in _read_json(path).get("rows", [])}


def _save_checkpoint(path, rows):
    _write_json(path, {"rows": [rows[key] for key in sorted(rows)]})


def _even_sample(task_items, per_task):
    if len(task_items) <= per_task:
        return list(task_items)
    if per_task <= 1:
        return [task_items[0]]
    indexes = []
    for idx in range(per_task):
        pos = round(idx * (len(task_items) - 1) / (per_task - 1))
        indexes.append(pos)
    return [task_items[pos] for pos in dict.fromkeys(indexes)]


def _select_items(items, tasks, per_task, sample_strategy, full, shuffle_seed):
    selected = []
    task_set = set(tasks)
    by_task = defaultdict(list)
    for item in items:
        if item["task"] in task_set:
            by_task[item["task"]].append(item)
    for task in tasks:
        task_items = by_task.get(task, [])
        if full:
            selected.extend(task_items)
        elif sample_strategy == "even":
            selected.extend(_even_sample(task_items, per_task))
        else:
            selected.extend(task_items[:per_task])
    if shuffle_seed is not None:
        rng = random.Random(shuffle_seed)
        rng.shuffle(selected)
    return selected


@contextmanager
def _temporary_env(updates):
    managed = {
        "URUHA_ENABLE_CANDIDATE_VERIFIER",
        "URUHA_ENABLE_SCALAR_CANDIDATE_VERIFIER",
        "URUHA_VERIFIER_DIRECT_DECISION",
        "URUHA_SCALAR_VERIFIER_DIRECT_DECISION",
    }
    old_values = {key: os.environ.get(key) for key in managed}
    try:
        for key in managed:
            os.environ.pop(key, None)
        for key, value in (updates or {}).items():
            os.environ[key] = str(value)
        yield
    finally:
        for key in managed:
            if old_values[key] is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = old_values[key]


def _parse_letter(text):
    return formal.parse_option_letter(text)


def _ask_surface_only_fast_prompt(client, item):
    option_lines = "\n".join(f"{key}. {value}" for key, value in item["options"].items())
    text = formal.chat(
        client,
        [
            {
                "role": "system",
                "content": (
                    "You are answering a multiple-choice benchmark under a fast surface-only condition. "
                    "Use only the task name, question, and options. Return exactly one capital letter: A, B, C, or D. "
                    "Do not explain."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"[task]\n{item['task']}\n\n"
                    f"[question]\n{item['question']}\n\n"
                    f"[options]\n{option_lines}\n"
                    "Answer with one letter only."
                ),
            },
        ],
        max_tokens=4,
    )
    return _parse_letter(text), text, {}, "[surface_only_fast_prompt] story removed by ablation condition", {}, "surface_only_fast_prompt", {}


def _ask_verifier_direct_only(client, item):
    core = formal.analyze_social_reasoning(
        item.get("story_zh") or item.get("story") or "",
        question=item.get("question_zh") or item.get("question") or "",
        options_zh=item.get("options_zh") or {},
        options_en=item.get("options") or {},
    )
    verifier = formal.verify_social_reasoning_candidates(
        item.get("story_zh") or item.get("story") or "",
        question=item.get("question_zh") or item.get("question") or "",
        options_zh=item.get("options_zh") or {},
        options_en=item.get("options") or {},
        core=core,
    )
    if verifier.get("confidence") == "high" and verifier.get("top_option"):
        answer = verifier["top_option"]
        raw = json.dumps(
            {
                "answer": answer,
                "solver": "candidate_verifier_only",
                "selection_mode": "candidate_verifier_direct_only",
                "details": verifier,
            },
            ensure_ascii=False,
        )
        return answer, raw, {}, "", {"social_reasoning_core": core, "candidate_verifier": verifier}, "candidate_verifier_direct_only", {
            "candidate_verifier": verifier,
            "note": "Direct verifier-only condition; no verifier trace was sent to LLM.",
        }
    answer, raw, hidden_intent, scratchpad, social_frame, selection_mode, details = formal.ask_tombench_official_mcq(
        client,
        None,
        item,
        "llm_only",
        "llm",
    )
    return answer, raw, hidden_intent, scratchpad, social_frame, f"verifier_fallback_{selection_mode}", {
        "candidate_verifier": verifier,
        "fallback_details": details,
    }


def _ask_deterministic_left_only(item):
    answer, selection_mode, details = formal.solve_tombench_task_p2_general_v1(item)
    if not answer:
        return "", "", {}, "", {}, "uncovered_deterministic_left_only", details
    raw = json.dumps(
        {
            "answer": answer,
            "solver": "p2_general_v1",
            "selection_mode": selection_mode,
            "details": details,
        },
        ensure_ascii=False,
    )
    return answer, raw, {}, "", {}, selection_mode, details


def _ask_condition(client, left, item, condition):
    spec = CONDITION_SPECS[condition]
    with _temporary_env(spec.get("env")):
        if condition == "control_prompt_only":
            return formal.ask_tombench_official_mcq(client, left, item, "llm_only", "llm")
        if condition == "trace_only":
            return formal.ask_tombench_official_mcq(client, left, item, "cognitive_adapter", "llm")
        if condition in {"trace_plus_verifier_hint", "trace_plus_verifier_direct"}:
            return formal.ask_tombench_official_mcq(client, left, item, "cognitive_adapter", "llm")
        if condition == "verifier_direct_only":
            return _ask_verifier_direct_only(client, item)
        if condition == "deterministic_left_only":
            return _ask_deterministic_left_only(item)
        if condition == "surface_only_fast_prompt":
            return _ask_surface_only_fast_prompt(client, item)
    raise ValueError(f"Unknown condition: {condition}")


def _run_condition(client, left, items, condition, checkpoint_path, force_refresh):
    rows_by_id = {} if force_refresh else _checkpoint_rows(checkpoint_path)
    rows = []
    for idx, item in enumerate(items, 1):
        cached = rows_by_id.get(item["id"])
        if cached:
            row = cached
        else:
            answer, raw, hidden_intent, scratchpad, social_frame, selection_mode, details = _ask_condition(client, left, item, condition)
            row = {
                "id": item["id"],
                "task": item["task"],
                "question": item["question"],
                "gold_answer": item["answer"],
                "pred_answer": answer,
                "correct": int(answer == item["answer"]),
                "unparsed": int(not bool(answer)),
                "condition": condition,
                "selection_mode": selection_mode,
                "hidden_intent": hidden_intent,
                "scratchpad": scratchpad,
                "social_frame": social_frame,
                "solver_details": details,
                "raw_reply": raw,
            }
            rows_by_id[item["id"]] = row
            _save_checkpoint(checkpoint_path, rows_by_id)
        rows.append(row)
        if idx % 50 == 0 or idx == len(items):
            correct = sum(row["correct"] for row in rows)
            print(f"[{condition} {idx:04d}/{len(items)}] acc={correct}/{len(rows)}")
    return rows


def _rate(rows):
    return round(sum(row["correct"] for row in rows) / len(rows), 4) if rows else 0.0


def _summarize_condition(rows):
    by_task = defaultdict(list)
    for row in rows:
        by_task[row["task"]].append(row)
    return {
        "count": len(rows),
        "correct": sum(row["correct"] for row in rows),
        "accuracy": _rate(rows),
        "unparsed_count": sum(row["unparsed"] for row in rows),
        "selection_mode_breakdown": dict(sorted(Counter(row["selection_mode"] for row in rows).items())),
        "task_breakdown": {
            task: {
                "count": len(task_rows),
                "correct": sum(row["correct"] for row in task_rows),
                "accuracy": _rate(task_rows),
                "unparsed_count": sum(row["unparsed"] for row in task_rows),
            }
            for task, task_rows in sorted(by_task.items())
        },
    }


def _compare_to_baseline(condition_rows, baseline_rows):
    condition_by_id = {row["id"]: row for row in condition_rows}
    baseline_by_id = {row["id"]: row for row in baseline_rows}
    shared_ids = [row_id for row_id in baseline_by_id if row_id in condition_by_id]
    only_condition_correct = 0
    only_baseline_correct = 0
    both_correct = 0
    both_wrong = 0
    deltas = []
    for row_id in shared_ids:
        row = condition_by_id[row_id]
        base = baseline_by_id[row_id]
        if row["correct"] and base["correct"]:
            both_correct += 1
        elif row["correct"] and not base["correct"]:
            only_condition_correct += 1
            deltas.append(_delta_row(row, base))
        elif not row["correct"] and base["correct"]:
            only_baseline_correct += 1
            deltas.append(_delta_row(row, base))
        else:
            both_wrong += 1
    return {
        "shared_count": len(shared_ids),
        "accuracy_delta": round(_rate(condition_rows) - _rate(baseline_rows), 4),
        "only_condition_correct": only_condition_correct,
        "only_baseline_correct": only_baseline_correct,
        "both_correct": both_correct,
        "both_wrong": both_wrong,
        "first_40_deltas": deltas[:40],
    }


def _delta_row(row, base):
    return {
        "id": row["id"],
        "task": row["task"],
        "gold_answer": row["gold_answer"],
        "condition_pred": row["pred_answer"],
        "baseline_pred": base["pred_answer"],
        "condition_selection_mode": row["selection_mode"],
        "baseline_selection_mode": base["selection_mode"],
        "question": row["question"],
    }


def _write_markdown(report, path):
    lines = [
        "# ToMBench Component Ablation",
        "",
        "This is a research ablation report. It changes one cognitive component condition at a time while holding the benchmark, model, scoring, and memory policy fixed.",
        "",
        "## Variables",
        "",
        "### Independent / Operated Variables",
    ]
    for condition in report["conditions"]:
        spec = report["condition_specs"][condition]
        lines.extend(
            [
                f"- {condition}: {spec['label']}",
                f"  - {spec['description']}",
            ]
        )
    lines.extend(["", "### Controlled Variables"])
    for key, value in report["controlled_variables"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "### Dependent Variables"])
    for value in report["dependent_variables"]:
        lines.append(f"- {value}")
    lines.extend(
        [
            "",
            "## Important Scope Note",
            "",
            "ToMBench can evaluate social understanding, belief/intent inference, process traces, and candidate self-checking. "
            "It cannot directly evaluate right-brain Japanese surface naturalness because the dependent variable is only an A/B/C/D option letter. "
            "Therefore right_brain_surface is marked not_applicable_mcq rather than falsely treated as proven by this benchmark.",
            "",
            "## Summary",
        ]
    )
    baseline = report["baseline_condition"]
    for condition, summary in report["summary_by_condition"].items():
        cmp = report["comparisons_vs_baseline"].get(condition)
        delta = "" if not cmp else f", delta_vs_{baseline}={cmp['accuracy_delta']}"
        lines.append(
            f"- {condition}: correct={summary['correct']}/{summary['count']}, "
            f"accuracy={summary['accuracy']}, unparsed={summary['unparsed_count']}{delta}"
        )
    lines.extend(["", "## Task Breakdown"])
    for condition, summary in report["summary_by_condition"].items():
        lines.append(f"### {condition}")
        for task, stats in summary["task_breakdown"].items():
            lines.append(
                f"- {task}: correct={stats['correct']}/{stats['count']}, "
                f"accuracy={stats['accuracy']}, unparsed={stats['unparsed_count']}"
            )
    lines.extend(["", f"## Deltas Against Baseline: {baseline}"])
    for condition, cmp in report["comparisons_vs_baseline"].items():
        if condition == baseline:
            continue
        lines.extend(
            [
                f"### {condition}",
                f"- accuracy_delta: {cmp['accuracy_delta']}",
                f"- only_condition_correct: {cmp['only_condition_correct']}",
                f"- only_baseline_correct: {cmp['only_baseline_correct']}",
                f"- both_correct: {cmp['both_correct']}",
                f"- both_wrong: {cmp['both_wrong']}",
            ]
        )
        for row in cmp["first_40_deltas"][:10]:
            lines.append(
                f"- {row['id']} {row['task']}: gold={row['gold_answer']}, "
                f"condition={row['condition_pred']}({row['condition_selection_mode']}), "
                f"baseline={row['baseline_pred']}({row['baseline_selection_mode']})"
            )
    lines.extend(
        [
            "",
            "## Reproduction Command",
            "",
            "```bash",
            " ".join(report["reproduction_command"]),
            "```",
            "",
        ]
    )
    _write_text(path, "\n".join(lines))


def main():
    parser = argparse.ArgumentParser(description="Run component ablations for UruhaBrain on official ToMBench rows.")
    parser.add_argument("--conditions", nargs="*", default=DEFAULT_CONDITIONS, choices=sorted(CONDITION_SPECS))
    parser.add_argument("--baseline-condition", default="trace_plus_verifier_direct", choices=sorted(CONDITION_SPECS))
    parser.add_argument(
        "--task-set",
        choices=sorted(TASK_SETS),
        default="social",
        help="Named ToMBench task set. Use --tasks to override this list explicitly.",
    )
    parser.add_argument("--tasks", nargs="*", default=None)
    parser.add_argument("--per-task", type=int, default=8)
    parser.add_argument("--full", action="store_true", help="Use all selected task rows instead of --per-task sampling.")
    parser.add_argument("--sample-strategy", choices=["first", "even"], default="even")
    parser.add_argument("--shuffle-seed", type=int, default=None)
    parser.add_argument("--force-refresh", action="store_true")
    parser.add_argument("--report-prefix", default=REPORT_PREFIX)
    args = parser.parse_args()

    conditions = list(dict.fromkeys(args.conditions))
    if args.baseline_condition not in conditions:
        conditions.append(args.baseline_condition)

    selected_tasks = args.tasks if args.tasks else TASK_SETS[args.task_set]
    meta = formal.load_tombench_items(per_task=10, full=True)
    items = _select_items(meta["items"], selected_tasks, args.per_task, args.sample_strategy, args.full, args.shuffle_seed)
    if not items:
        raise SystemExit("No ToMBench items selected.")

    needs_llm = any(CONDITION_SPECS[condition].get("requires_llm") for condition in conditions)
    client = None
    left = None
    if needs_llm:
        client = OpenAI(base_url=ubm.OLLAMA_URL, api_key=ubm.OLLAMA_API_KEY)
        with contextlib.redirect_stdout(io.StringIO()):
            left = ubm.LeftBrain(client)

    all_rows = {}
    checkpoint_paths = {}
    for condition in conditions:
        checkpoint = os.path.join(
            FORMAL_BENCHMARK_CACHE_DIR,
            f"{args.report_prefix}_{condition}_checkpoint.json",
        )
        checkpoint_paths[condition] = checkpoint
        all_rows[condition] = _run_condition(client, left, items, condition, checkpoint, args.force_refresh)

    summary_by_condition = {
        condition: _summarize_condition(rows)
        for condition, rows in all_rows.items()
    }
    baseline_rows = all_rows[args.baseline_condition]
    comparisons = {
        condition: _compare_to_baseline(rows, baseline_rows)
        for condition, rows in all_rows.items()
    }
    report = {
        "version": "tombench_component_ablation_2026_05_20",
        "source": meta["source"],
        "sample": {
            "count": len(items),
            "task_set": args.task_set,
            "tasks": selected_tasks,
            "per_task": args.per_task,
            "full": args.full,
            "sample_strategy": args.sample_strategy,
            "shuffle_seed": args.shuffle_seed,
        },
        "conditions": conditions,
        "baseline_condition": args.baseline_condition,
        "condition_specs": {condition: CONDITION_SPECS[condition] for condition in conditions},
        "controlled_variables": CONTROLLED_VARIABLES,
        "dependent_variables": DEPENDENT_VARIABLES,
        "summary_by_condition": summary_by_condition,
        "comparisons_vs_baseline": comparisons,
        "rows_by_condition": all_rows,
        "checkpoints": checkpoint_paths,
        "reproduction_command": [EXPECTED_PYTHON, os.path.abspath(__file__), *sys.argv[1:]],
    }

    json_path = os.path.join(REPORTS_DIR, f"{args.report_prefix}.json")
    md_path = os.path.join(REPORTS_DIR, f"{args.report_prefix}.md")
    _write_json(json_path, report)
    _write_markdown(report, md_path)

    print(json.dumps(summary_by_condition, ensure_ascii=False, indent=2))
    print(f"Wrote {json_path}")
    print(f"Wrote {md_path}")


if __name__ == "__main__":
    main()
