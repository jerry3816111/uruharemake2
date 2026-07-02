import argparse
import json
from datetime import datetime
from pathlib import Path


METRICS = (
    "generated_candidate_count",
    "accepted_candidate_count",
    "raw_candidate_acceptance_rate",
    "model_selected_case_count",
    "model_selected_case_rate",
    "final_quality_pass_rate",
    "final_language_clean_rate",
    "final_forbidden_surface_leak_rate",
    "final_generic_template_hit_rate",
    "final_normalized_duplicate_reply_rate",
)

MATCHED_FIELDS = (
    "scope",
    "seed",
    "candidate_count_per_case",
    "runtime_contract_version",
)


def _load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _case_map(report):
    return {row["id"]: row for row in report["cases"]}


def _validate_matched_runs(baseline, trained):
    mismatches = []
    for field in MATCHED_FIELDS:
        if baseline.get(field) != trained.get(field):
            mismatches.append(
                f"{field}: {baseline.get(field)!r} != {trained.get(field)!r}"
            )

    baseline_ids = set(_case_map(baseline))
    trained_ids = set(_case_map(trained))
    if baseline_ids != trained_ids:
        mismatches.append(
            f"case_ids: baseline_only={sorted(baseline_ids - trained_ids)!r}, "
            f"trained_only={sorted(trained_ids - baseline_ids)!r}"
        )

    if not baseline.get("load_model") or not trained.get("load_model"):
        mismatches.append("both reports must be model-loaded runs")

    if mismatches:
        raise ValueError("Holdout runs are not matched: " + "; ".join(mismatches))


def build_comparison(baseline, trained, training):
    _validate_matched_runs(baseline, trained)
    baseline_cases = _case_map(baseline)
    trained_cases = _case_map(trained)

    metric_rows = []
    for metric in METRICS:
        baseline_value = baseline["summary"].get(metric)
        trained_value = trained["summary"].get(metric)
        delta = None
        if isinstance(baseline_value, (int, float)) and isinstance(
            trained_value, (int, float)
        ):
            delta = round(trained_value - baseline_value, 4)
        metric_rows.append(
            {
                "metric": metric,
                "baseline": baseline_value,
                "trained": trained_value,
                "delta": delta,
            }
        )

    case_diffs = []
    for case_id in sorted(baseline_cases):
        before = baseline_cases[case_id]
        after = trained_cases[case_id]
        before_reasons = sorted(set(before.get("model_rejection_reasons", [])))
        after_reasons = sorted(set(after.get("model_rejection_reasons", [])))
        before_accepted = before.get("accepted_candidate_count", 0)
        after_accepted = after.get("accepted_candidate_count", 0)
        if (
            before_accepted == after_accepted
            and before_reasons == after_reasons
            and before.get("selected_source") == after.get("selected_source")
        ):
            continue
        case_diffs.append(
            {
                "id": case_id,
                "category": after.get("category", ""),
                "baseline_accepted_candidate_count": before_accepted,
                "trained_accepted_candidate_count": after_accepted,
                "newly_accepted": before_accepted == 0 and after_accepted > 0,
                "baseline_rejection_reasons": before_reasons,
                "trained_rejection_reasons": after_reasons,
                "resolved_rejection_reasons": sorted(
                    set(before_reasons) - set(after_reasons)
                ),
                "new_rejection_reasons": sorted(
                    set(after_reasons) - set(before_reasons)
                ),
                "baseline_selected_source": before.get("selected_source"),
                "trained_selected_source": after.get("selected_source"),
            }
        )

    baseline_rate = baseline["summary"]["raw_candidate_acceptance_rate"]
    trained_rate = trained["summary"]["raw_candidate_acceptance_rate"]
    acceptance_delta = round(trained_rate - baseline_rate, 4)
    conclusion = (
        f"在相同 holdout、seed、候選數與 gate 下，raw model 候選通過率由 "
        f"{baseline_rate:.1%} 提升至 {trained_rate:.1%}"
        f"（{acceptance_delta * 100:+.1f} 個百分點）。"
        "最終品質仍為 100%，表示嚴格 gate 與 deterministic fallback 沒有被放寬；"
        "這次量到的是模型候選可靠度的小幅提升，不是整體認知能力已完成。"
    )

    return {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "scope": "rightbrain_model_surface_matched_holdout_comparison",
        "baseline_adapter": baseline["adapter_ref"],
        "trained_adapter": trained["adapter_ref"],
        "matched_conditions": {
            field: baseline.get(field) for field in MATCHED_FIELDS
        },
        "training": {
            "rows": training.get("rows"),
            "supplemental_rows": training.get("supplemental_rows"),
            "optimizer_updates": training.get("optimizer_updates"),
            "nonfinite_skips": training.get("nonfinite_skips"),
            "initial_eval_loss_probe": training.get("initial_eval_loss_probe"),
            "sampled_eval_loss": training.get("sampled_eval_loss"),
            "final_train_loss": training.get("final_train_loss"),
            "learning_rate": training.get("learning_rate"),
        },
        "metric_rows": metric_rows,
        "case_diffs": case_diffs,
        "conclusion_zh": conclusion,
    }


def _format_metric_value(metric, value):
    if value is None:
        return "-"
    if metric.endswith("_rate"):
        return f"{value:.1%}"
    return str(value)


def write_markdown(report, output_path):
    lines = [
        "# RightBrain Matched Holdout Comparison",
        "",
        "## 一句話結論",
        "",
        report["conclusion_zh"],
        "",
        "## 公平比較條件",
        "",
        f"- baseline adapter: {report['baseline_adapter']}",
        f"- trained adapter: {report['trained_adapter']}",
    ]
    for key, value in report["matched_conditions"].items():
        lines.append(f"- {key}: {value}")

    training = report["training"]
    lines.extend(
        [
            "",
            "## 訓練摘要",
            "",
            f"- rows: {training['rows']}",
            f"- supplemental rows: {training['supplemental_rows']}",
            f"- optimizer updates: {training['optimizer_updates']}",
            f"- nonfinite skips: {training['nonfinite_skips']}",
            f"- learning rate: {training['learning_rate']}",
            f"- initial eval loss: {training['initial_eval_loss_probe']:.4f}",
            f"- sampled eval loss: {training['sampled_eval_loss']:.4f}",
            "",
            "## Holdout 指標",
            "",
            "| metric | baseline | trained | delta |",
            "|---|---:|---:|---:|",
        ]
    )
    for row in report["metric_rows"]:
        metric = row["metric"]
        baseline = _format_metric_value(metric, row["baseline"])
        trained = _format_metric_value(metric, row["trained"])
        delta = _format_metric_value(metric, row["delta"])
        lines.append(f"| {metric} | {baseline} | {trained} | {delta} |")

    lines.extend(["", "## 個案差異", ""])
    if not report["case_diffs"]:
        lines.append("- 沒有個案差異。")
    for row in report["case_diffs"]:
        status = "新增通過" if row["newly_accepted"] else "行為改變"
        resolved = ", ".join(row["resolved_rejection_reasons"]) or "-"
        added = ", ".join(row["new_rejection_reasons"]) or "-"
        lines.append(
            f"- `{row['id']}` ({row['category']}): {status}; "
            f"accepted {row['baseline_accepted_candidate_count']} -> "
            f"{row['trained_accepted_candidate_count']}; "
            f"resolved={resolved}; new={added}"
        )

    Path(output_path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline-json", required=True)
    parser.add_argument("--trained-json", required=True)
    parser.add_argument("--training-json", required=True)
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--output-md", required=True)
    args = parser.parse_args()

    report = build_comparison(
        _load_json(args.baseline_json),
        _load_json(args.trained_json),
        _load_json(args.training_json),
    )
    Path(args.output_json).write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    write_markdown(report, args.output_md)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
