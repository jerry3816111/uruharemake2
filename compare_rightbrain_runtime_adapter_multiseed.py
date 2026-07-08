import argparse
import json
from datetime import datetime
from pathlib import Path

from compare_rightbrain_model_surface_holdouts import _validate_matched_runs
from project_paths import (
    RIGHTBRAIN_RUNTIME_ADAPTER_MULTISEED_REPORT_JSON_PATH,
    RIGHTBRAIN_RUNTIME_ADAPTER_MULTISEED_REPORT_MD_PATH,
)


def _load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _aggregate(reports):
    generated = sum(row["summary"]["generated_candidate_count"] for row in reports)
    accepted = sum(row["summary"]["accepted_candidate_count"] for row in reports)
    case_count = sum(row["summary"]["case_count"] for row in reports)
    selected = sum(row["summary"]["model_selected_case_count"] for row in reports)

    def weighted_rate(metric):
        numerator = sum(row["summary"][metric] * row["summary"]["case_count"] for row in reports)
        return round(numerator / case_count, 4) if case_count else None

    return {
        "run_count": len(reports),
        "case_count": case_count,
        "generated_candidate_count": generated,
        "accepted_candidate_count": accepted,
        "raw_candidate_acceptance_rate": round(accepted / generated, 4) if generated else None,
        "model_selected_case_count": selected,
        "model_selected_case_rate": round(selected / case_count, 4) if case_count else None,
        "final_quality_pass_rate": weighted_rate("final_quality_pass_rate"),
        "final_language_clean_rate": weighted_rate("final_language_clean_rate"),
        "final_forbidden_surface_leak_rate": weighted_rate("final_forbidden_surface_leak_rate"),
        "final_generic_template_hit_rate": weighted_rate("final_generic_template_hit_rate"),
        "case_eval_duration_seconds": round(sum(row.get("case_eval_duration_seconds", 0.0) for row in reports), 3),
    }


def build_report(baselines, promoted):
    if not baselines or len(baselines) != len(promoted):
        raise ValueError("baseline and promoted reports must have the same non-zero count")

    baseline_adapter = baselines[0].get("adapter_ref")
    promoted_adapter = promoted[0].get("adapter_ref")
    candidate_count = baselines[0].get("candidate_count_per_case")
    seen_seeds = set()
    per_seed = []
    for baseline, candidate in zip(baselines, promoted):
        _validate_matched_runs(baseline, candidate)
        if baseline.get("adapter_ref") != baseline_adapter:
            raise ValueError("baseline adapter changed across seeds")
        if candidate.get("adapter_ref") != promoted_adapter:
            raise ValueError("promoted adapter changed across seeds")
        if baseline.get("candidate_count_per_case") != candidate_count:
            raise ValueError("candidate count changed across seeds")
        seed = baseline.get("seed")
        if seed in seen_seeds:
            raise ValueError(f"duplicate seed: {seed}")
        seen_seeds.add(seed)
        before = baseline["summary"]
        after = candidate["summary"]
        per_seed.append(
            {
                "seed": seed,
                "baseline_raw_candidate_acceptance_rate": before["raw_candidate_acceptance_rate"],
                "promoted_raw_candidate_acceptance_rate": after["raw_candidate_acceptance_rate"],
                "raw_candidate_acceptance_delta": round(
                    after["raw_candidate_acceptance_rate"] - before["raw_candidate_acceptance_rate"],
                    4,
                ),
                "baseline_model_selected_case_count": before["model_selected_case_count"],
                "promoted_model_selected_case_count": after["model_selected_case_count"],
                "baseline_final_quality_pass_rate": before["final_quality_pass_rate"],
                "promoted_final_quality_pass_rate": after["final_quality_pass_rate"],
            }
        )

    baseline_aggregate = _aggregate(baselines)
    promoted_aggregate = _aggregate(promoted)
    acceptance_delta = round(
        promoted_aggregate["raw_candidate_acceptance_rate"]
        - baseline_aggregate["raw_candidate_acceptance_rate"],
        4,
    )
    quality_guard_pass = (
        promoted_aggregate["final_quality_pass_rate"] == 1.0
        and promoted_aggregate["final_language_clean_rate"] == 1.0
        and promoted_aggregate["final_forbidden_surface_leak_rate"] == 0.0
        and promoted_aggregate["final_generic_template_hit_rate"] == 0.0
    )
    all_seed_noninferior = all(row["raw_candidate_acceptance_delta"] >= 0 for row in per_seed)
    promotion_recommended = (
        len(per_seed) >= 2
        and acceptance_delta > 0
        and all_seed_noninferior
        and promoted_aggregate["model_selected_case_count"] >= baseline_aggregate["model_selected_case_count"]
        and quality_guard_pass
    )
    if promotion_recommended:
        decision_zh = (
            f"建議升版：{len(per_seed)} 個 matched seeds 合計 raw 接受率由 "
            f"{baseline_aggregate['raw_candidate_acceptance_rate']:.1%} 提升至 "
            f"{promoted_aggregate['raw_candidate_acceptance_rate']:.1%}，模型接管數由 "
            f"{baseline_aggregate['model_selected_case_count']} 增至 "
            f"{promoted_aggregate['model_selected_case_count']}，且最終品質防線維持 100%。"
        )
    else:
        decision_zh = "不建議升版：多 seed 證據未同時通過候選可靠度、接管數與最終品質門檻。"

    return {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "scope": "rightbrain_runtime_adapter_multiseed_promotion_gate",
        "baseline_adapter": baseline_adapter,
        "promoted_adapter": promoted_adapter,
        "candidate_count_per_case": candidate_count,
        "seeds": sorted(seen_seeds),
        "promotion_recommended": promotion_recommended,
        "quality_guard_pass": quality_guard_pass,
        "all_seed_noninferior": all_seed_noninferior,
        "aggregate": {
            "baseline": baseline_aggregate,
            "promoted": promoted_aggregate,
            "raw_candidate_acceptance_delta": acceptance_delta,
        },
        "per_seed": per_seed,
        "decision_zh": decision_zh,
        "research_boundary": (
            "This gate compares adapters under matched seeds and runtime candidate count. "
            "It measures model candidate reliability and guarded integration, not human naturalness."
        ),
    }


def write_markdown(report, output_path):
    before = report["aggregate"]["baseline"]
    after = report["aggregate"]["promoted"]
    lines = [
        "# RightBrain Runtime Adapter Multi-seed Promotion Gate",
        "",
        "## 結論",
        "",
        report["decision_zh"],
        "",
        "## 控制變因",
        "",
        f"- baseline adapter: `{report['baseline_adapter']}`",
        f"- promoted adapter: `{report['promoted_adapter']}`",
        f"- seeds: `{report['seeds']}`",
        f"- candidates per case: `{report['candidate_count_per_case']}`",
        f"- all seeds non-inferior: `{report['all_seed_noninferior']}`",
        f"- final quality guard: `{report['quality_guard_pass']}`",
        "",
        "## 合計結果",
        "",
        "| 指標 | 舊 adapter | promoted adapter |",
        "|---|---:|---:|",
        f"| raw 候選接受 | {before['accepted_candidate_count']}/{before['generated_candidate_count']} ({before['raw_candidate_acceptance_rate']:.1%}) | {after['accepted_candidate_count']}/{after['generated_candidate_count']} ({after['raw_candidate_acceptance_rate']:.1%}) |",
        f"| 模型實際接管 | {before['model_selected_case_count']}/{before['case_count']} | {after['model_selected_case_count']}/{after['case_count']} |",
        f"| 最終品質通過率 | {before['final_quality_pass_rate']:.1%} | {after['final_quality_pass_rate']:.1%} |",
        "",
        "## 各 Seed",
        "",
        "| seed | baseline raw | promoted raw | delta | baseline selected | promoted selected |",
        "|---:|---:|---:|---:|---:|---:|",
    ]
    for row in report["per_seed"]:
        lines.append(
            f"| {row['seed']} | {row['baseline_raw_candidate_acceptance_rate']:.1%} | "
            f"{row['promoted_raw_candidate_acceptance_rate']:.1%} | "
            f"{row['raw_candidate_acceptance_delta']:+.1%} | "
            f"{row['baseline_model_selected_case_count']} | "
            f"{row['promoted_model_selected_case_count']} |"
        )
    lines.extend(["", f"研究邊界：{report['research_boundary']}", ""])
    Path(output_path).write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline-json", action="append", required=True)
    parser.add_argument("--promoted-json", action="append", required=True)
    parser.add_argument("--output-json", default=RIGHTBRAIN_RUNTIME_ADAPTER_MULTISEED_REPORT_JSON_PATH)
    parser.add_argument("--output-md", default=RIGHTBRAIN_RUNTIME_ADAPTER_MULTISEED_REPORT_MD_PATH)
    args = parser.parse_args()

    report = build_report(
        [_load_json(path) for path in args.baseline_json],
        [_load_json(path) for path in args.promoted_json],
    )
    Path(args.output_json).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_markdown(report, args.output_md)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["promotion_recommended"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
