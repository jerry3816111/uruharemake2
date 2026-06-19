import argparse
import json
from datetime import datetime
from collections import Counter

from project_paths import (
    FORMAL_DAILYDIALOG_HOLDOUT_REPORT_JSON_PATH,
    FORMAL_DAILYDIALOG_HOLDOUT_REPORT_MD_PATH,
    ensure_project_dirs,
)
from run_formal_brain_benchmarks_v2 import DD_ACT_NAMES, DD_EMOTION_NAMES, eval_dailydialog


DEFAULT_LABELERS = ("interpreter_v4", "interpreter_v5", "interpreter_v6")


def _first_misses(results, key, limit):
    gold_key = f"gold_{key}"
    pred_key = f"pred_{key}"
    name_key = f"{key}_name"
    rows = []
    for row in results:
        if row[gold_key] == row[pred_key]:
            continue
        rows.append(
            {
                "id": row["id"],
                "context": row.get("context", [])[-2:],
                "target_utterance": row["target_utterance"],
                f"gold_{name_key}": row[f"gold_{name_key}"],
                f"pred_{name_key}": row[f"pred_{name_key}"],
                "rule": row.get(f"{key}_rule"),
                "confidence": row.get(f"{key}_confidence"),
            }
        )
        if len(rows) >= limit:
            break
    return rows


def _confusion_pairs(results, key):
    counter = Counter()
    gold_key = f"gold_{key}_name"
    pred_key = f"pred_{key}_name"
    for row in results:
        if row[gold_key] != row[pred_key]:
            counter[(row[gold_key], row[pred_key])] += 1
    return [
        {"gold": gold, "pred": pred, "count": count}
        for (gold, pred), count in counter.most_common()
    ]


def build_report(sample_size, labelers, miss_limit):
    report = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "benchmark": "DailyDialog v2 official utterance holdout",
        "sample_size": sample_size,
        "purpose": (
            "Larger official-test-split check for utterance-level act/emotion interpretation. "
            "This guards against overclaiming from the 60-item formal interpreter report."
        ),
        "labelers": {},
    }

    for labeler in labelers:
        summary, results = eval_dailydialog(None, None, sample_size, "llm_only", labeler)
        report["labelers"][labeler] = {
            "summary": summary,
            "act_confusion_pairs": _confusion_pairs(results, "act"),
            "emotion_confusion_pairs": _confusion_pairs(results, "emotion"),
            "act_miss_examples": _first_misses(results, "act", miss_limit),
            "emotion_miss_examples": _first_misses(results, "emotion", miss_limit),
        }
    report["best_by_act_accuracy"] = max(
        report["labelers"],
        key=lambda key: report["labelers"][key]["summary"]["dialog_act_accuracy"],
    )
    report["best_by_emotion_accuracy"] = max(
        report["labelers"],
        key=lambda key: report["labelers"][key]["summary"]["emotion_accuracy"],
    )
    return report


def build_markdown(report):
    lines = [
        "# Formal DailyDialog Holdout Report",
        "",
        f"- generated_at: {report['generated_at']}",
        f"- sample_size: {report['sample_size']}",
        "- source: DailyDialog official test split via the v2 benchmark loader",
        "- scope: utterance-level act/emotion interpretation, not final chat generation",
        f"- best_by_act_accuracy: {report['best_by_act_accuracy']}",
        f"- best_by_emotion_accuracy: {report['best_by_emotion_accuracy']}",
        "",
        "## Summary",
        "",
        "| labeler | act accuracy | act macro-F1 | emotion accuracy | emotion supported macro-F1 | emotion macro-F1 |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for labeler, payload in report["labelers"].items():
        summary = payload["summary"]
        lines.append(
            f"| {labeler} | {summary['dialog_act_accuracy']} | {summary['dialog_act_macro_f1']} | "
            f"{summary['emotion_accuracy']} | {summary['emotion_supported_macro_f1']} | "
            f"{summary['emotion_macro_f1']} |"
        )

    lines.extend(
        [
            "",
            "## Label Meaning",
            "",
            "- Act labels: "
            + ", ".join(f"{idx}={name}" for idx, name in sorted(DD_ACT_NAMES.items())),
            "- Emotion labels: "
            + ", ".join(f"{idx}={name}" for idx, name in sorted(DD_EMOTION_NAMES.items())),
            "",
            "## Main Error Patterns",
            "",
        ]
    )

    for labeler, payload in report["labelers"].items():
        lines.extend([f"### {labeler}", ""])
        lines.append("Act confusion pairs:")
        if payload["act_confusion_pairs"]:
            for pair in payload["act_confusion_pairs"][:8]:
                lines.append(f"- {pair['gold']} -> {pair['pred']}: {pair['count']}")
        else:
            lines.append("- none")
        lines.append("")
        lines.append("Emotion confusion pairs:")
        if payload["emotion_confusion_pairs"]:
            for pair in payload["emotion_confusion_pairs"][:8]:
                lines.append(f"- {pair['gold']} -> {pair['pred']}: {pair['count']}")
        else:
            lines.append("- none")
        lines.append("")

    lines.extend(["## Example Misses", ""])
    for labeler, payload in report["labelers"].items():
        lines.extend([f"### {labeler}", "", "| type | gold | pred | utterance | rule |", "| --- | --- | --- | --- | --- |"])
        for row in payload["act_miss_examples"][:5]:
            utterance = row["target_utterance"].replace("|", "/")
            lines.append(f"| act | {row['gold_act_name']} | {row['pred_act_name']} | {utterance} | {row['rule']} |")
        for row in payload["emotion_miss_examples"][:5]:
            utterance = row["target_utterance"].replace("|", "/")
            lines.append(
                f"| emotion | {row['gold_emotion_name']} | {row['pred_emotion_name']} | {utterance} | {row['rule']} |"
            )
        lines.append("")

    lines.extend(
        [
            "## Reproduction",
            "",
            "```bash",
            f"python run_formal_dailydialog_holdout_eval.py --sample-size {report['sample_size']}",
            "```",
            "",
        ]
    )

    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description="Run DailyDialog v2 holdout interpreter comparison.")
    parser.add_argument("--sample-size", type=int, default=200)
    parser.add_argument("--labeler", action="append", choices=DEFAULT_LABELERS)
    parser.add_argument("--miss-limit", type=int, default=20)
    args = parser.parse_args()

    ensure_project_dirs()
    labelers = tuple(args.labeler) if args.labeler else DEFAULT_LABELERS
    report = build_report(args.sample_size, labelers, args.miss_limit)
    with open(FORMAL_DAILYDIALOG_HOLDOUT_REPORT_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    with open(FORMAL_DAILYDIALOG_HOLDOUT_REPORT_MD_PATH, "w", encoding="utf-8") as f:
        f.write(build_markdown(report))
    print(json.dumps({
        labeler: payload["summary"]
        for labeler, payload in report["labelers"].items()
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
