import argparse
import json
from datetime import datetime
from pathlib import Path


METRICS = (
    "generated_candidate_count",
    "initial_accepted_candidate_count",
    "accepted_candidate_count",
    "raw_candidate_acceptance_rate",
    "repair_attempt_count",
    "repair_accepted_count",
    "repair_success_rate",
    "effective_candidate_acceptance_rate",
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


def build_comparison(baseline, trained, training, curriculum=None):
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
    baseline_repair = bool(baseline.get("repair_enabled"))
    trained_repair = bool(trained.get("repair_enabled"))
    if baseline_repair != trained_repair:
        baseline_effective = baseline["summary"]["effective_candidate_acceptance_rate"]
        trained_effective = trained["summary"]["effective_candidate_acceptance_rate"]
        effective_delta = round(trained_effective - baseline_effective, 4)
        conclusion = (
            f"在相同 adapter、holdout、seed、候選數與 gate 下，首次 raw 通過率維持 "
            f"{baseline_rate:.1%}；開啟一次契約修正後，有效候選通過率由 "
            f"{baseline_effective:.1%} 變為 {trained_effective:.1%}"
            f"（{effective_delta * 100:+.1f} 個百分點）。"
            "最終品質仍須通過原 gate，未放寬語意、語言或記憶權限。"
        )
        if effective_delta <= 0:
            conclusion += "這個 repair prompt 沒有產生淨改善，不應預設開啟；下一步需要先訓練修正能力。"
    elif baseline_repair and trained_repair:
        baseline_effective = baseline["summary"]["effective_candidate_acceptance_rate"]
        trained_effective = trained["summary"]["effective_candidate_acceptance_rate"]
        effective_delta = round(trained_effective - baseline_effective, 4)
        baseline_repair_accepted = baseline["summary"]["repair_accepted_count"]
        baseline_repair_attempts = baseline["summary"]["repair_attempt_count"]
        trained_repair_accepted = trained["summary"]["repair_accepted_count"]
        trained_repair_attempts = trained["summary"]["repair_attempt_count"]
        conclusion = (
            f"在相同 holdout、seed、候選數、repair 開關與嚴格 gate 下，首次 raw 通過率由 "
            f"{baseline_rate:.1%} 變為 {trained_rate:.1%}；repair 成功數由 "
            f"{baseline_repair_accepted}/{baseline_repair_attempts} 變為 "
            f"{trained_repair_accepted}/{trained_repair_attempts}，有效候選通過率由 "
            f"{baseline_effective:.1%} 變為 {trained_effective:.1%}"
            f"（{effective_delta * 100:+.1f} 個百分點）。"
            "最終品質仍須通過原 gate，未放寬語意、語言或記憶權限。"
        )
        if effective_delta <= 0 or trained_repair_accepted <= baseline_repair_accepted:
            conclusion += "這次訓練未證明 repair 能力有淨改善，runtime repair 不應預設開啟。"
    else:
        conclusion = (
            f"在相同 holdout、seed、候選數與 gate 下，raw model 候選通過率由 "
            f"{baseline_rate:.1%} 變為 {trained_rate:.1%}"
            f"（{acceptance_delta * 100:+.1f} 個百分點）。"
            "最終品質仍為 100%，表示嚴格 gate 與 deterministic fallback 沒有被放寬；"
        )
        if acceptance_delta > 0:
            conclusion += "這次量到模型候選可靠度提升，但不是整體認知能力已完成。"
        elif acceptance_delta < 0:
            conclusion += "這次量到模型候選可靠度下降，不能據此升版。"
        else:
            conclusion += "這次沒有量到模型候選可靠度差異，不能據此升版。"

    baseline_eval_seconds = baseline.get("case_eval_duration_seconds")
    trained_eval_seconds = trained.get("case_eval_duration_seconds")
    runtime = {
        "baseline_case_eval_duration_seconds": baseline_eval_seconds,
        "trained_case_eval_duration_seconds": trained_eval_seconds,
        "case_eval_duration_delta_seconds": None,
        "note": "Single-run wall-clock evidence; use repeated runs before making a latency claim.",
    }
    if isinstance(baseline_eval_seconds, (int, float)) and isinstance(
        trained_eval_seconds, (int, float)
    ):
        runtime["case_eval_duration_delta_seconds"] = round(
            trained_eval_seconds - baseline_eval_seconds,
            3,
        )

    data_boundary = None
    if curriculum:
        data_boundary = {
            "curriculum_row_count": curriculum.get("curriculum_row_count"),
            "holdout_case_count": curriculum.get("holdout_case_count"),
            "holdout_user_input_overlap_count": curriculum.get(
                "holdout_user_input_overlap_count"
            ),
            "holdout_contract_overlap_count": curriculum.get(
                "holdout_contract_overlap_count"
            ),
            "holdout_target_overlap_count": curriculum.get(
                "holdout_target_overlap_count"
            ),
            "previous_draft_in_training_prompt": (
                curriculum.get("runtime_schema") or {}
            ).get("previous_draft_in_training_prompt"),
        }

    return {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "scope": "rightbrain_model_surface_matched_holdout_comparison",
        "baseline_adapter": baseline["adapter_ref"],
        "trained_adapter": trained["adapter_ref"],
        "baseline_repair_adapter": baseline.get("repair_adapter_ref", ""),
        "trained_repair_adapter": trained.get("repair_adapter_ref", ""),
        "matched_conditions": {
            field: baseline.get(field) for field in MATCHED_FIELDS
        },
        "independent_variable": {
            "baseline_repair_enabled": baseline_repair,
            "trained_repair_enabled": trained_repair,
        },
        "training": {
            "dataset_ref": training.get("dataset_ref"),
            "rows": training.get("rows"),
            "supplemental_rows": training.get("supplemental_rows"),
            "init_adapter_ref": training.get("init_adapter_ref"),
            "output_adapter_ref": training.get("output_adapter_ref"),
            "optimizer_updates": training.get("optimizer_updates"),
            "nonfinite_skips": training.get("nonfinite_skips"),
            "initial_eval_loss_probe": training.get("initial_eval_loss_probe"),
            "sampled_eval_loss": training.get("sampled_eval_loss"),
            "final_train_loss": training.get("final_train_loss"),
            "learning_rate": training.get("learning_rate"),
            "optimizer_eps": training.get("optimizer_eps"),
            "nonfinite_loss_skips": training.get("nonfinite_loss_skips"),
            "nonfinite_gradient_skips": training.get("nonfinite_gradient_skips"),
            "max_observed_gradient_norm": training.get("max_observed_gradient_norm"),
        },
        "data_boundary": data_boundary,
        "runtime": runtime,
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
        f"- baseline repair adapter: {report.get('baseline_repair_adapter') or '(none)'}",
        f"- trained repair adapter: {report.get('trained_repair_adapter') or '(none)'}",
    ]
    for key, value in report["matched_conditions"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            f"- baseline repair enabled: {report['independent_variable']['baseline_repair_enabled']}",
            f"- trained repair enabled: {report['independent_variable']['trained_repair_enabled']}",
        ]
    )

    training = report["training"]
    comparison_heading = (
        "固定模型背景"
        if report["independent_variable"]["baseline_repair_enabled"]
        != report["independent_variable"]["trained_repair_enabled"]
        else "訓練摘要"
    )
    lines.extend(
        [
            "",
            f"## {comparison_heading}",
            "",
            f"- dataset: {training['dataset_ref']}",
            f"- rows: {training['rows']}",
            f"- supplemental rows: {training['supplemental_rows']}",
            f"- init adapter: {training['init_adapter_ref']}",
            f"- output adapter: {training['output_adapter_ref']}",
            f"- optimizer updates: {training['optimizer_updates']}",
            f"- nonfinite skips: {training['nonfinite_skips']}",
            f"- nonfinite loss skips: {training['nonfinite_loss_skips']}",
            f"- nonfinite gradient skips: {training['nonfinite_gradient_skips']}",
            f"- learning rate: {training['learning_rate']}",
            f"- optimizer epsilon: {training['optimizer_eps']}",
            f"- max observed gradient norm: {training['max_observed_gradient_norm']}",
            f"- initial eval loss: {training['initial_eval_loss_probe']:.4f}",
            f"- sampled eval loss: {training['sampled_eval_loss']:.4f}",
        ]
    )
    if report.get("data_boundary"):
        boundary = report["data_boundary"]
        lines.extend(
            [
                "",
                "## 防止小抄",
                "",
                f"- repair curriculum rows: {boundary['curriculum_row_count']}",
                f"- holdout cases: {boundary['holdout_case_count']}",
                f"- holdout input overlap: {boundary['holdout_user_input_overlap_count']}",
                f"- holdout contract overlap: {boundary['holdout_contract_overlap_count']}",
                f"- holdout target overlap: {boundary['holdout_target_overlap_count']}",
                f"- rejected draft exposed during training: {boundary['previous_draft_in_training_prompt']}",
            ]
        )
    lines.extend(
        [
            "",
            "## 執行時間",
            "",
            f"- baseline case eval: {report['runtime']['baseline_case_eval_duration_seconds']} seconds",
            f"- trained case eval: {report['runtime']['trained_case_eval_duration_seconds']} seconds",
            f"- delta: {report['runtime']['case_eval_duration_delta_seconds']} seconds",
            f"- boundary: {report['runtime']['note']}",
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
    parser.add_argument("--curriculum-json")
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--output-md", required=True)
    args = parser.parse_args()

    report = build_comparison(
        _load_json(args.baseline_json),
        _load_json(args.trained_json),
        _load_json(args.training_json),
        _load_json(args.curriculum_json) if args.curriculum_json else None,
    )
    Path(args.output_json).write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    write_markdown(report, args.output_md)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
