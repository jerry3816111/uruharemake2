import json
from datetime import datetime

from project_paths import (
    FORMAL_DAILYDIALOG_INTERPRETER_REPORT_JSON_PATH,
    FORMAL_DAILYDIALOG_INTERPRETER_REPORT_MD_PATH,
    ensure_project_dirs,
)
from run_formal_brain_benchmarks import DD_ACT_NAMES, DD_EMOTION_NAMES, eval_dailydialog


def build_markdown(report):
    summary = report["summary"]
    lines = [
        "# Formal DailyDialog Interpreter Report",
        "",
        f"- generated_at: {report['generated_at']}",
        f"- sample_size: {summary['sample_size']}",
        f"- labeler: {summary['labeler']}",
        "",
        "## Scores",
        "",
        f"- dialog_act_accuracy: {summary['dialog_act_accuracy']}",
        f"- dialog_act_macro_f1: {summary['dialog_act_macro_f1']}",
        f"- emotion_accuracy: {summary['emotion_accuracy']}",
        f"- emotion_macro_f1: {summary['emotion_macro_f1']}",
        "",
        "## Method",
        "",
        "- Source: official DailyDialog test split sample from the configured Hugging Face dataset.",
        "- Scoring: exact match against official utterance-level act and emotion IDs.",
        "- Runtime: labeler-only; no local LLM planner call is required for this report.",
        "- Purpose: measure dialogue-act/emotion interpretation, not final Japanese surface generation.",
        "",
        "## Act Breakdown",
        "",
        "| act | count | one-vs-rest accuracy |",
        "| --- | ---: | ---: |",
    ]
    for label_id in sorted(DD_ACT_NAMES):
        name = DD_ACT_NAMES[label_id]
        row = summary["act_breakdown"][name]
        lines.append(f"| {name} | {row['count']} | {row['accuracy']} |")

    lines.extend(
        [
            "",
            "## Emotion Breakdown",
            "",
            "| emotion | count | one-vs-rest accuracy |",
            "| --- | ---: | ---: |",
        ]
    )
    for label_id in sorted(DD_EMOTION_NAMES):
        name = DD_EMOTION_NAMES[label_id]
        row = summary["emotion_breakdown"][name]
        lines.append(f"| {name} | {row['count']} | {row['accuracy']} |")

    return "\n".join(lines) + "\n"


def main():
    ensure_project_dirs()
    summary, results = eval_dailydialog(None)
    report = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "summary": summary,
        "results": results,
    }
    with open(FORMAL_DAILYDIALOG_INTERPRETER_REPORT_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    with open(FORMAL_DAILYDIALOG_INTERPRETER_REPORT_MD_PATH, "w", encoding="utf-8") as f:
        f.write(build_markdown(report))
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
