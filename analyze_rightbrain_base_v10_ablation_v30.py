#!/usr/bin/env python3
"""Analyze the preregistered V30 V10-versus-base RightBrain ablation."""

import argparse
import hashlib
import json
import math
import random
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PREREG_PATH = ROOT / "configs/rightbrain_base_v10_ablation_v30_preregistration.json"
DEFAULT_JSON = ROOT / "reports/rightbrain_base_v10_ablation_v30_analysis.json"
DEFAULT_MD = ROOT / "reports/rightbrain_base_v10_ablation_v30_analysis.md"
CONDITIONS = ("v10_adapter", "base_only")
HARD_SURFACE_REASONS = {
    "missing_japanese_surface",
    "cjk_language_leak",
    "nonstandard_cjk_surface",
    "foreign_script_leak",
    "ascii_symbol_artifact",
    "unicode_replacement_character",
    "nonstandard_punctuation",
    "unexpected_ascii_leak",
    "over_max_chars",
    "response_plan_leak",
}


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_rate(numerator, denominator):
    return numerator / denominator if denominator else None


def classify_rejection(reasons):
    reasons = set(reasons or [])
    return {
        "hard_surface_failure": bool(reasons & HARD_SURFACE_REASONS),
        "semantic_omission": any(
            reason.startswith("semantic_slots_missing:") for reason in reasons
        ),
        "polite_tone_drift": "polite_tone_drift" in reasons,
        "duplicate_candidate": "duplicate_candidate" in reasons,
    }


def summarize_condition(reports):
    generated = 0
    accepted = 0
    covered = 0
    rejection_reason_counts = Counter()
    classified_counts = Counter()
    per_seed = {}
    pair_success = {}
    categories = defaultdict(lambda: [0, 0])
    for report in reports:
        seed = int(report["seed"])
        seed_generated = 0
        seed_accepted = 0
        seed_covered = 0
        for row in report["cases"]:
            row_generated = int(row.get("generated_candidate_count") or 0)
            row_accepted = int(row.get("initial_accepted_candidate_count") or 0)
            success = row_accepted > 0
            generated += row_generated
            accepted += row_accepted
            covered += int(success)
            seed_generated += row_generated
            seed_accepted += row_accepted
            seed_covered += int(success)
            pair_success[(seed, row["id"])] = success
            category = str(row.get("category") or "unknown")
            categories[category][0] += int(success)
            categories[category][1] += 1
            for candidate in row.get("model_initial_rejected_candidates") or []:
                reasons = candidate.get("rejection_reasons") or []
                rejection_reason_counts.update(reasons)
                flags = classify_rejection(reasons)
                classified_counts.update(
                    name for name, value in flags.items() if value
                )
        per_seed[str(seed)] = {
            "generated_candidate_count": seed_generated,
            "strict_accepted_candidate_count": seed_accepted,
            "raw_candidate_acceptance_rate": safe_rate(
                seed_accepted, seed_generated
            ),
            "strict_case_coverage_count": seed_covered,
            "strict_case_coverage_rate": safe_rate(
                seed_covered, len(report["cases"])
            ),
        }
    seed_case_count = sum(len(report["cases"]) for report in reports)
    return {
        "run_count": len(reports),
        "seed_case_pair_count": seed_case_count,
        "generated_candidate_count": generated,
        "strict_accepted_candidate_count": accepted,
        "raw_candidate_acceptance_rate": safe_rate(accepted, generated),
        "strict_case_coverage_count": covered,
        "strict_case_coverage_rate": safe_rate(covered, seed_case_count),
        "hard_surface_failure_count": classified_counts["hard_surface_failure"],
        "hard_surface_failure_rate": safe_rate(
            classified_counts["hard_surface_failure"], generated
        ),
        "semantic_omission_count": classified_counts["semantic_omission"],
        "semantic_omission_rate": safe_rate(
            classified_counts["semantic_omission"], generated
        ),
        "polite_tone_drift_count": classified_counts["polite_tone_drift"],
        "polite_tone_drift_rate": safe_rate(
            classified_counts["polite_tone_drift"], generated
        ),
        "duplicate_candidate_count": classified_counts["duplicate_candidate"],
        "duplicate_candidate_rate": safe_rate(
            classified_counts["duplicate_candidate"], generated
        ),
        "per_seed": per_seed,
        "per_category": {
            category: {
                "strict_case_coverage_count": counts[0],
                "seed_case_pair_count": counts[1],
                "strict_case_coverage_rate": safe_rate(*counts),
            }
            for category, counts in sorted(categories.items())
        },
        "rejection_reason_counts": dict(sorted(rejection_reason_counts.items())),
        "pair_success": pair_success,
    }


def exact_mcnemar_p(base_only_wins, v10_wins):
    discordant = base_only_wins + v10_wins
    if not discordant:
        return 1.0
    lower = min(base_only_wins, v10_wins)
    probability = sum(
        math.comb(discordant, index) for index in range(lower + 1)
    ) / (2**discordant)
    return min(1.0, 2 * probability)


def paired_effect(v10_summary, base_summary):
    v10 = v10_summary["pair_success"]
    base = base_summary["pair_success"]
    keys = sorted(set(v10) | set(base))
    if set(v10) != set(base):
        raise ValueError("Condition seed-case pairs do not match")
    counts = Counter()
    rows = []
    for seed, case_id in keys:
        v10_success = bool(v10[(seed, case_id)])
        base_success = bool(base[(seed, case_id)])
        if v10_success and base_success:
            outcome = "both"
        elif base_success:
            outcome = "base_only_only"
        elif v10_success:
            outcome = "v10_only"
        else:
            outcome = "neither"
        counts[outcome] += 1
        rows.append(
            {
                "seed": seed,
                "case_id": case_id,
                "v10_success": v10_success,
                "base_only_success": base_success,
                "outcome": outcome,
            }
        )
    return {
        "pair_count": len(keys),
        "both": counts["both"],
        "neither": counts["neither"],
        "base_only_wins": counts["base_only_only"],
        "v10_wins": counts["v10_only"],
        "strict_case_coverage_delta": (
            base_summary["strict_case_coverage_rate"]
            - v10_summary["strict_case_coverage_rate"]
        ),
        "mcnemar_exact_p": exact_mcnemar_p(
            counts["base_only_only"], counts["v10_only"]
        ),
        "rows": rows,
    }


def cluster_bootstrap_delta(paired_rows, samples=10000, seed=20260730):
    by_case = defaultdict(list)
    for row in paired_rows:
        by_case[row["case_id"]].append(row)
    case_ids = sorted(by_case)
    rng = random.Random(seed)
    deltas = []
    for _ in range(samples):
        sampled = [rng.choice(case_ids) for _ in case_ids]
        differences = []
        for case_id in sampled:
            for row in by_case[case_id]:
                differences.append(
                    int(row["base_only_success"]) - int(row["v10_success"])
                )
        deltas.append(sum(differences) / len(differences))
    deltas.sort()
    lower = deltas[int(0.025 * samples)]
    upper = deltas[min(samples - 1, int(0.975 * samples))]
    return {
        "method": "case_cluster_bootstrap",
        "samples": samples,
        "seed": seed,
        "lower_95": lower,
        "upper_95": upper,
    }


def _load_reports(preregistration, root=ROOT):
    v10_reports = []
    base_reports = []
    for row in preregistration["frozen_v10_reports"]:
        v10_reports.append(
            json.loads((Path(root) / row["path"]).read_text(encoding="utf-8"))
        )
    for seed in preregistration["frozen_inputs"]["seeds"]:
        path = (
            Path(root)
            / "reports"
            / f"rightbrain_base_v10_ablation_v30_base_only_seed{seed}.json"
        )
        base_reports.append(json.loads(path.read_text(encoding="utf-8")))
    return {"v10_adapter": v10_reports, "base_only": base_reports}


def verify_evidence(preregistration, reports, root=ROOT):
    checks = {}
    for name, entry in preregistration["frozen_inputs"].items():
        if not isinstance(entry, dict) or "path" not in entry:
            continue
        path = Path(root) / entry["path"]
        checks[f"{name}_sha256_matches"] = (
            path.is_file() and sha256_file(path) == entry["sha256"]
        )
    for row, report in zip(
        preregistration["frozen_v10_reports"], reports["v10_adapter"]
    ):
        path = Path(root) / row["path"]
        checks[f"v10_seed_{row['seed']}_sha256_matches"] = (
            sha256_file(path) == row["sha256"]
        )
        checks[f"v10_seed_{row['seed']}_metadata_matches"] = (
            report.get("seed") == row["seed"]
            and report.get("adapter_ref")
            == preregistration["conditions"]["v10_adapter"]["adapter_ref"]
        )
    expected_seeds = preregistration["frozen_inputs"]["seeds"]
    prereg_sha = sha256_file(PREREG_PATH)
    for report, seed in zip(reports["base_only"], expected_seeds):
        checks[f"base_seed_{seed}_formal_run_complete"] = (
            report.get("formal_run_complete") is True
        )
        checks[f"base_seed_{seed}_metadata_matches"] = (
            report.get("seed") == seed
            and report.get("condition") == "base_only"
            and report.get("adapter_ref") == "base_model_only"
            and report.get("preregistration_sha256") == prereg_sha
        )
    for condition in CONDITIONS:
        condition_reports = reports[condition]
        checks[f"{condition}_seeds_match"] = [
            report.get("seed") for report in condition_reports
        ] == expected_seeds
        checks[f"{condition}_case_ids_match"] = all(
            [row.get("id") for row in report.get("cases") or []]
            == [case["id"] for case in reports[condition][0]["cases"]]
            for report in condition_reports
        )
        checks[f"{condition}_candidate_shape_matches"] = all(
            report["summary"]["case_count"]
            == preregistration["frozen_inputs"]["case_count"]
            and report["summary"]["generated_candidate_count"]
            == preregistration["frozen_inputs"][
                "case_count"
            ]
            * preregistration["frozen_inputs"]["candidate_count_per_case"]
            for report in condition_reports
        )
    checks["cross_condition_case_ids_match"] = all(
        [row["id"] for row in v10_report["cases"]]
        == [row["id"] for row in base_report["cases"]]
        for v10_report, base_report in zip(
            reports["v10_adapter"], reports["base_only"]
        )
    )
    return checks


def build_analysis(preregistration, reports, root=ROOT):
    verification = verify_evidence(preregistration, reports, root=root)
    summaries = {
        condition: summarize_condition(condition_reports)
        for condition, condition_reports in reports.items()
    }
    paired = paired_effect(summaries["v10_adapter"], summaries["base_only"])
    paired["cluster_bootstrap_95"] = cluster_bootstrap_delta(paired["rows"])
    base = summaries["base_only"]
    v10 = summaries["v10_adapter"]
    threshold = preregistration["blind_review_gate"]
    gates = {
        "all_hash_and_shape_checks_pass": all(verification.values()),
        "base_strict_case_coverage_delta_at_least_10pp": paired[
            "strict_case_coverage_delta"
        ]
        >= threshold["base_strict_case_coverage_delta_at_least"],
        "base_strict_case_coverage_not_lower_in_any_seed": all(
            base["per_seed"][str(seed)]["strict_case_coverage_rate"]
            >= v10["per_seed"][str(seed)]["strict_case_coverage_rate"]
            for seed in preregistration["frozen_inputs"]["seeds"]
        ),
        "base_hard_surface_failure_rate_not_higher": base[
            "hard_surface_failure_rate"
        ]
        <= v10["hard_surface_failure_rate"],
        "base_semantic_omission_rate_increase_at_most_2pp": base[
            "semantic_omission_rate"
        ]
        <= v10["semantic_omission_rate"]
        + threshold["base_semantic_omission_rate_increase_at_most"],
    }
    authorize_blind = all(gates.values())
    for summary in summaries.values():
        summary.pop("pair_success", None)
    decision = (
        "authorize_human_blind_base_vs_v10_only"
        if authorize_blind
        else "keep_v10_no_runtime_change"
    )
    return {
        "schema": "uruha_rightbrain_base_v10_ablation_analysis_v30",
        "preregistration_path": str(PREREG_PATH.relative_to(ROOT)),
        "preregistration_sha256": sha256_file(PREREG_PATH),
        "verification": verification,
        "condition_summary": summaries,
        "paired_effect": paired,
        "blind_review_gates": gates,
        "authorize_human_blind_review": authorize_blind,
        "authorize_runtime_change": False,
        "decision": decision,
        "research_boundary": (
            "This diagnostic matched ablation can retain V10 or authorize a new human blind review. "
            "It cannot establish human likeness, justify benchmark claims, or promote base-only runtime."
        ),
    }


def _fmt_pct(value):
    return "n/a" if value is None else f"{100 * value:.1f}%"


def render_markdown(analysis):
    summaries = analysis["condition_summary"]
    paired = analysis["paired_effect"]
    lines = [
        "# 右腦 V30：V10 LoRA 對原始 Qwen 7B 的單一變因實驗",
        "",
        "## 實驗問題",
        "",
        "相同 Qwen2.5-7B、12 個情境、三個 seed、payload、採樣與 gate；唯一差別是 V10 LoRA 開或關。",
        "",
        "## 總結果",
        "",
        "| 指標 | V10 LoRA | Base-only |",
        "|---|---:|---:|",
    ]
    metric_labels = [
        ("strict_case_coverage_rate", "每組至少一個合格候選"),
        ("raw_candidate_acceptance_rate", "raw 候選通過率"),
        ("hard_surface_failure_rate", "語言/格式硬失敗率"),
        ("semantic_omission_rate", "必要語意遺失率"),
        ("polite_tone_drift_rate", "敬語/客服語域漂移率"),
    ]
    for key, label in metric_labels:
        lines.append(
            f"| {label} | {_fmt_pct(summaries['v10_adapter'][key])} | "
            f"{_fmt_pct(summaries['base_only'][key])} |"
        )
    lines.extend(
        [
            "",
            "## 配對差異",
            "",
            f"- Base-only 勝：{paired['base_only_wins']} 組",
            f"- V10 勝：{paired['v10_wins']} 組",
            f"- 覆蓋率差：{_fmt_pct(paired['strict_case_coverage_delta'])}",
            f"- McNemar exact p：{paired['mcnemar_exact_p']:.4f}",
            "- 95% case-cluster bootstrap："
            f"[{_fmt_pct(paired['cluster_bootstrap_95']['lower_95'])}, "
            f"{_fmt_pct(paired['cluster_bootstrap_95']['upper_95'])}]",
            "",
            "## 預註冊門檻",
            "",
        ]
    )
    for name, value in analysis["blind_review_gates"].items():
        lines.append(f"- {name}: {value}")
    lines.extend(
        [
            "",
            "## 決定",
            "",
            f"**{analysis['decision']}**",
            "",
            "這次自動結果不會直接改 runtime。即使 Base-only 通過，也只能進入新的同政策人類盲評。",
            "",
            "## 證據邊界",
            "",
            analysis["research_boundary"],
        ]
    )
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-json", default=DEFAULT_JSON)
    parser.add_argument("--output-md", default=DEFAULT_MD)
    args = parser.parse_args()
    preregistration = json.loads(PREREG_PATH.read_text(encoding="utf-8"))
    reports = _load_reports(preregistration)
    analysis = build_analysis(preregistration, reports)
    Path(args.output_json).write_text(
        json.dumps(analysis, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    Path(args.output_md).write_text(render_markdown(analysis), encoding="utf-8")
    print(
        json.dumps(
            {
                "decision": analysis["decision"],
                "paired_effect": analysis["paired_effect"],
                "blind_review_gates": analysis["blind_review_gates"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if all(analysis["verification"].values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
