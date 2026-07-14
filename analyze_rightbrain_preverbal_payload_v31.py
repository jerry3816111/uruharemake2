#!/usr/bin/env python3
"""Analyze the preregistered V31 RightBrain payload factorial."""

import argparse
import hashlib
import json
import math
import random
from collections import Counter, defaultdict
from pathlib import Path

from rightbrain_preverbal_payload_v31 import CONDITION_FACTORS


ROOT = Path(__file__).resolve().parent
PREREG_PATH = ROOT / "configs/rightbrain_preverbal_payload_v31_preregistration.json"
AMENDMENT_PATH = ROOT / "configs/rightbrain_preverbal_payload_v31_amendment.json"
CONTROL_BINDING_PATH = (
    ROOT / "configs/rightbrain_preverbal_payload_v31_control_binding.json"
)
DEFAULT_JSON = ROOT / "reports/rightbrain_preverbal_payload_v31_analysis.json"
DEFAULT_MD = ROOT / "reports/rightbrain_preverbal_payload_v31_analysis.md"
CONDITIONS = tuple(CONDITION_FACTORS)
CONTROL = "mixed_json_control"
CONTRASTS = (
    ("japanese_json", CONTROL),
    ("mixed_lines", CONTROL),
    ("japanese_lines", "japanese_json"),
    ("japanese_lines", "mixed_lines"),
    ("japanese_lines", CONTROL),
)
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
CONDITION_LABELS_ZH = {
    "mixed_json_control": "現行混合標籤 JSON（對照組）",
    "japanese_json": "日文標籤 JSON",
    "mixed_lines": "現行混合標籤行式訊息",
    "japanese_lines": "日文標籤行式訊息",
}
GATE_LABELS_ZH = {
    "all_source_and_representation_checks_pass": "來源與表示完整性全部通過",
    "strict_case_coverage_delta_vs_control_at_least_10pp": "嚴格覆蓋率至少改善 10 個百分點",
    "strict_case_coverage_noninferior_in_every_seed": "每個 seed 都不低於對照組",
    "semantic_omission_improves_at_least_5pp": "語意遺漏至少改善 5 個百分點",
    "hard_surface_failure_increase_at_most_2pp": "表面硬失敗最多增加 2 個百分點",
    "holm_adjusted_mcnemar_p_at_most_005": "Holm 校正後配對檢定 p <= 0.05",
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
    classified_counts = Counter()
    rejection_reason_counts = Counter()
    pair_success = {}
    per_seed = {}
    prompt_tokens = []
    prompt_characters = []
    prompt_ascii_letters = []
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
            payload = row.get("preverbal_payload_v31") or {}
            prompt_tokens.append(int(payload.get("rendered_token_count") or 0))
            prompt_characters.append(
                int(payload.get("rendered_character_count") or 0)
            )
            prompt_ascii_letters.append(
                int(payload.get("rendered_ascii_letter_count") or 0)
            )
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
                seed_accepted,
                seed_generated,
            ),
            "strict_case_coverage_count": seed_covered,
            "strict_case_coverage_rate": safe_rate(
                seed_covered,
                len(report["cases"]),
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
            classified_counts["hard_surface_failure"],
            generated,
        ),
        "semantic_omission_count": classified_counts["semantic_omission"],
        "semantic_omission_rate": safe_rate(
            classified_counts["semantic_omission"],
            generated,
        ),
        "polite_tone_drift_count": classified_counts["polite_tone_drift"],
        "polite_tone_drift_rate": safe_rate(
            classified_counts["polite_tone_drift"],
            generated,
        ),
        "duplicate_candidate_count": classified_counts["duplicate_candidate"],
        "duplicate_candidate_rate": safe_rate(
            classified_counts["duplicate_candidate"],
            generated,
        ),
        "mean_prompt_token_count": safe_rate(sum(prompt_tokens), len(prompt_tokens)),
        "mean_prompt_character_count": safe_rate(
            sum(prompt_characters),
            len(prompt_characters),
        ),
        "mean_prompt_ascii_letter_count": safe_rate(
            sum(prompt_ascii_letters),
            len(prompt_ascii_letters),
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


def exact_mcnemar_p(treatment_wins, reference_wins):
    discordant = treatment_wins + reference_wins
    if not discordant:
        return 1.0
    lower = min(treatment_wins, reference_wins)
    probability = sum(
        math.comb(discordant, index) for index in range(lower + 1)
    ) / (2**discordant)
    return min(1.0, 2 * probability)


def paired_effect(treatment_name, reference_name, summaries):
    treatment = summaries[treatment_name]["pair_success"]
    reference = summaries[reference_name]["pair_success"]
    if set(treatment) != set(reference):
        raise ValueError(
            f"Condition seed-case pairs differ: {treatment_name}, {reference_name}"
        )
    counts = Counter()
    rows = []
    for seed, case_id in sorted(treatment):
        treatment_success = bool(treatment[(seed, case_id)])
        reference_success = bool(reference[(seed, case_id)])
        if treatment_success and reference_success:
            outcome = "both"
        elif treatment_success:
            outcome = "treatment_only"
        elif reference_success:
            outcome = "reference_only"
        else:
            outcome = "neither"
        counts[outcome] += 1
        rows.append(
            {
                "seed": seed,
                "case_id": case_id,
                "treatment_success": treatment_success,
                "reference_success": reference_success,
                "outcome": outcome,
            }
        )
    return {
        "treatment": treatment_name,
        "reference": reference_name,
        "pair_count": len(rows),
        "both": counts["both"],
        "neither": counts["neither"],
        "treatment_wins": counts["treatment_only"],
        "reference_wins": counts["reference_only"],
        "strict_case_coverage_delta": (
            summaries[treatment_name]["strict_case_coverage_rate"]
            - summaries[reference_name]["strict_case_coverage_rate"]
        ),
        "mcnemar_exact_p": exact_mcnemar_p(
            counts["treatment_only"],
            counts["reference_only"],
        ),
        "rows": rows,
    }


def cluster_bootstrap_delta(rows, samples=10000, seed=20260731):
    by_case = defaultdict(list)
    for row in rows:
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
                    int(row["treatment_success"])
                    - int(row["reference_success"])
                )
        deltas.append(sum(differences) / len(differences))
    deltas.sort()
    return {
        "method": "case_cluster_bootstrap",
        "samples": samples,
        "seed": seed,
        "lower_95": deltas[int(0.025 * samples)],
        "upper_95": deltas[min(samples - 1, int(0.975 * samples))],
    }


def holm_adjust(p_values):
    ordered = sorted(p_values.items(), key=lambda item: (item[1], item[0]))
    adjusted = {}
    running_max = 0.0
    count = len(ordered)
    for rank, (name, p_value) in enumerate(ordered):
        running_max = max(running_max, min(1.0, (count - rank) * p_value))
        adjusted[name] = running_max
    return adjusted


def _report_path(condition, seed, root=ROOT):
    return (
        Path(root)
        / "reports"
        / f"rightbrain_preverbal_payload_v31_{condition}_seed{seed}.json"
    )


def load_reports(preregistration, root=ROOT):
    return {
        condition: [
            json.loads(_report_path(condition, seed, root).read_text(encoding="utf-8"))
            for seed in preregistration["frozen_inputs"]["seeds"]
        ]
        for condition in CONDITIONS
    }


def verify_evidence(preregistration, reports, root=ROOT):
    frozen = preregistration["frozen_inputs"]
    prereg_sha = sha256_file(PREREG_PATH)
    amendment_sha = sha256_file(AMENDMENT_PATH)
    binding_sha = sha256_file(CONTROL_BINDING_PATH)
    expected_case_ids = None
    checks = {}
    runner_hashes = set()
    serializer_hashes = set()
    canonical_by_pair = defaultdict(dict)
    for condition in CONDITIONS:
        condition_reports = reports[condition]
        checks[f"{condition}_run_count_matches"] = len(condition_reports) == len(
            frozen["seeds"]
        )
        for report, seed in zip(condition_reports, frozen["seeds"]):
            prefix = f"{condition}_seed_{seed}"
            checks[f"{prefix}_formal_run_complete"] = (
                report.get("formal_run_complete") is True
            )
            checks[f"{prefix}_metadata_matches"] = all(
                [
                    report.get("condition") == condition,
                    report.get("seed") == seed,
                    report.get("adapter_ref") == frozen["adapter_ref"],
                    report.get("base_model_revision") == frozen["base_model_revision"],
                    report.get("preregistration_sha256") == prereg_sha,
                    report.get("amendment_sha256") == amendment_sha,
                    report.get("control_binding_sha256") == binding_sha,
                    report.get("factors") == CONDITION_FACTORS[condition],
                ]
            )
            runner_hashes.add(report.get("runner_sha256"))
            serializer_hashes.add(report.get("serializer_sha256"))
            rows = report.get("cases") or []
            case_ids = [row.get("id") for row in rows]
            if expected_case_ids is None:
                expected_case_ids = case_ids
            checks[f"{prefix}_case_order_matches"] = case_ids == expected_case_ids
            checks[f"{prefix}_candidate_accounting_matches"] = all(
                int(row.get("initial_accepted_candidate_count") or 0)
                + len(row.get("model_initial_rejected_candidates") or [])
                == frozen["candidate_count_per_case"]
                for row in rows
            )
            checks[f"{prefix}_representation_integrity_passes"] = all(
                (row.get("preverbal_payload_v31") or {}).get(
                    "representation_integrity_pass"
                )
                for row in rows
            )
            for row in rows:
                canonical_by_pair[(seed, row["id"])][condition] = (
                    row["preverbal_payload_v31"]["canonical_payload_sha256"]
                )
    checks["runner_sha256_same_across_reports"] = len(runner_hashes) == 1
    checks["serializer_sha256_same_across_reports"] = len(serializer_hashes) == 1
    checks["canonical_payload_matches_across_conditions"] = all(
        len(values) == len(CONDITIONS) and len(set(values.values())) == 1
        for values in canonical_by_pair.values()
    ) and len(canonical_by_pair) == frozen["case_count"] * len(frozen["seeds"])
    checks["all_control_runs_reproduce_v30"] = all(
        report.get("control_reproduction", {}).get(
            "raw_candidate_sequences_match"
        )
        for report in reports[CONTROL]
    )
    return checks


def _contrast_key(treatment, reference):
    return f"{treatment}__minus__{reference}"


def _select_best_noncontrol(summaries):
    return min(
        (condition for condition in CONDITIONS if condition != CONTROL),
        key=lambda condition: (
            -summaries[condition]["strict_case_coverage_rate"],
            summaries[condition]["semantic_omission_rate"],
            summaries[condition]["hard_surface_failure_rate"],
            summaries[condition]["mean_prompt_token_count"],
            condition,
        ),
    )


def build_analysis(preregistration, amendment, reports, root=ROOT):
    verification = verify_evidence(preregistration, reports, root=root)
    summaries = {
        condition: summarize_condition(condition_reports)
        for condition, condition_reports in reports.items()
    }
    contrasts = {}
    for index, (treatment, reference) in enumerate(CONTRASTS):
        key = _contrast_key(treatment, reference)
        effect = paired_effect(treatment, reference, summaries)
        effect["cluster_bootstrap_95"] = cluster_bootstrap_delta(
            effect["rows"],
            seed=20260731 + index,
        )
        contrasts[key] = effect
    adjusted = holm_adjust(
        {key: effect["mcnemar_exact_p"] for key, effect in contrasts.items()}
    )
    for key, value in adjusted.items():
        contrasts[key]["holm_adjusted_mcnemar_p"] = value

    best = _select_best_noncontrol(summaries)
    control_summary = summaries[CONTROL]
    best_summary = summaries[best]
    best_key = _contrast_key(best, CONTROL)
    best_effect = contrasts[best_key]
    threshold = preregistration["advance_gate"]["requirements"]
    gates = {
        "all_source_and_representation_checks_pass": all(verification.values()),
        "strict_case_coverage_delta_vs_control_at_least_10pp": best_effect[
            "strict_case_coverage_delta"
        ]
        >= threshold["strict_case_coverage_delta_vs_control_at_least"],
        "strict_case_coverage_noninferior_in_every_seed": all(
            best_summary["per_seed"][str(seed)]["strict_case_coverage_rate"]
            >= control_summary["per_seed"][str(seed)]["strict_case_coverage_rate"]
            for seed in preregistration["frozen_inputs"]["seeds"]
        ),
        "semantic_omission_improves_at_least_5pp": (
            best_summary["semantic_omission_rate"]
            - control_summary["semantic_omission_rate"]
        )
        <= threshold["semantic_omission_delta_vs_control_at_most"],
        "hard_surface_failure_increase_at_most_2pp": (
            best_summary["hard_surface_failure_rate"]
            - control_summary["hard_surface_failure_rate"]
        )
        <= threshold["hard_surface_failure_delta_vs_control_at_most"],
        "holm_adjusted_mcnemar_p_at_most_005": best_effect[
            "holm_adjusted_mcnemar_p"
        ]
        <= threshold["holm_adjusted_mcnemar_p_at_most"],
    }
    authorize_holdout = all(gates.values())
    report_sha256 = {
        condition: {
            str(seed): sha256_file(_report_path(condition, seed, root))
            for seed in preregistration["frozen_inputs"]["seeds"]
        }
        for condition in CONDITIONS
    }
    language_json = contrasts[_contrast_key("japanese_json", CONTROL)]
    language_lines = contrasts[
        _contrast_key("japanese_lines", "mixed_lines")
    ]
    format_mixed = contrasts[_contrast_key("mixed_lines", CONTROL)]
    format_japanese = contrasts[
        _contrast_key("japanese_lines", "japanese_json")
    ]
    factor_diagnosis = {
        "japanese_label_effect_same_direction_across_formats": (
            language_json["strict_case_coverage_delta"] > 0
            and language_lines["strict_case_coverage_delta"] > 0
        ),
        "line_format_effect_same_direction_across_languages": (
            format_mixed["strict_case_coverage_delta"] > 0
            and format_japanese["strict_case_coverage_delta"] > 0
        ),
        "japanese_label_simple_effects": {
            "within_json": language_json["strict_case_coverage_delta"],
            "within_lines": language_lines["strict_case_coverage_delta"],
        },
        "line_format_simple_effects": {
            "within_mixed_labels": format_mixed["strict_case_coverage_delta"],
            "within_japanese_labels": format_japanese[
                "strict_case_coverage_delta"
            ],
        },
    }
    for summary in summaries.values():
        summary.pop("pair_success", None)
    decision = (
        f"authorize_source_separated_holdout_for_{best}"
        if authorize_holdout
        else "keep_current_payload_no_runtime_change"
    )
    return {
        "schema": "uruha_rightbrain_preverbal_payload_analysis_v31",
        "preregistration_path": str(PREREG_PATH.relative_to(ROOT)),
        "preregistration_sha256": sha256_file(PREREG_PATH),
        "amendment_path": str(AMENDMENT_PATH.relative_to(ROOT)),
        "amendment_sha256": sha256_file(AMENDMENT_PATH),
        "control_binding_path": str(CONTROL_BINDING_PATH.relative_to(ROOT)),
        "control_binding_sha256": sha256_file(CONTROL_BINDING_PATH),
        "condition_report_sha256": report_sha256,
        "verification": verification,
        "condition_summary": summaries,
        "contrasts": contrasts,
        "best_noncontrol_condition": best,
        "factor_diagnosis": factor_diagnosis,
        "advance_gates": gates,
        "authorize_source_separated_holdout": authorize_holdout,
        "authorize_runtime_change": False,
        "authorize_human_blind_review": False,
        "decision": decision,
        "research_boundary": preregistration["research_boundary"],
    }


def _fmt_pct(value):
    return "n/a" if value is None else f"{100 * value:.1f}%"


def _fmt_pp(value):
    return "n/a" if value is None else f"{100 * value:+.1f} pp"


def render_markdown(analysis):
    summaries = analysis["condition_summary"]
    control = summaries[CONTROL]
    best_name = analysis["best_noncontrol_condition"]
    best = summaries[best_name]
    per_seed_deltas = {
        seed: (
            best["per_seed"][seed]["strict_case_coverage_rate"]
            - control["per_seed"][seed]["strict_case_coverage_rate"]
        )
        for seed in control["per_seed"]
    }
    lines = [
        "# 右腦 V31：語言 × 訊息格式配對實驗",
        "",
        "四組使用同一個 Qwen2.5-7B、V10 adapter、動態語意、12 個情境、三個 seed、採樣與 gate。",
        "唯一因素是標籤語言與 payload 序列化格式。",
        "",
        "## 四組結果",
        "",
        "| 條件 | seed-case 覆蓋率 | raw 通過率 | 語意遺失 | 硬失敗 | 平均 prompt tokens |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for condition in CONDITIONS:
        summary = summaries[condition]
        lines.append(
            f"| {CONDITION_LABELS_ZH[condition]} | "
            f"{_fmt_pct(summary['strict_case_coverage_rate'])} | "
            f"{_fmt_pct(summary['raw_candidate_acceptance_rate'])} | "
            f"{_fmt_pct(summary['semantic_omission_rate'])} | "
            f"{_fmt_pct(summary['hard_surface_failure_rate'])} | "
            f"{summary['mean_prompt_token_count']:.1f} |"
        )
    lines.extend(
        [
            "",
            "嚴格覆蓋率以 36 個 seed-case 配對為單位；raw 通過率以 108 個候選回答為單位。",
            "",
            "## 預註冊配對差異",
            "",
            "以下差異的單位是百分點（pp），不是相對百分比。",
            "",
        ]
    )
    for effect in analysis["contrasts"].values():
        lines.append(
            f"- {CONDITION_LABELS_ZH[effect['treatment']]} - "
            f"{CONDITION_LABELS_ZH[effect['reference']]}："
            f"{_fmt_pp(effect['strict_case_coverage_delta'])}，"
            f"McNemar p={effect['mcnemar_exact_p']:.4f}，"
            f"Holm p={effect['holm_adjusted_mcnemar_p']:.4f}，"
            f"95% CI=[{_fmt_pct(effect['cluster_bootstrap_95']['lower_95'])}, "
            f"{_fmt_pct(effect['cluster_bootstrap_95']['upper_95'])}]"
        )
    lines.extend(
        [
            "",
            "## 因素診斷",
            "",
            f"- 日文標籤在兩種格式都同方向改善：{'是' if analysis['factor_diagnosis']['japanese_label_effect_same_direction_across_formats'] else '否'}",
            f"- 行式格式在兩種語言都同方向改善：{'是' if analysis['factor_diagnosis']['line_format_effect_same_direction_across_languages'] else '否'}",
            f"- 預註冊規則選出的最佳非對照條件：{CONDITION_LABELS_ZH[best_name]}",
            "",
            "### 最佳條件在各 seed 的差異",
            "",
            "| seed | 對照組 | 最佳條件 | 差異（pp） |",
            "|---:|---:|---:|---:|",
        ]
    )
    for seed, delta in per_seed_deltas.items():
        lines.append(
            f"| {seed} | "
            f"{_fmt_pct(control['per_seed'][seed]['strict_case_coverage_rate'])} | "
            f"{_fmt_pct(best['per_seed'][seed]['strict_case_coverage_rate'])} | "
            f"{_fmt_pp(delta)} |"
        )
    lines.extend(
        [
            "",
            "觀察到的改善在三個 seed 並不平均；這也是不能只看總分就改 runtime 的原因。",
            "",
            "## 晉級門檻",
            "",
        ]
    )
    for name, value in analysis["advance_gates"].items():
        lines.append(f"- {'通過' if value else '未通過'}：{GATE_LABELS_ZH[name]}")
    lines.extend(
        [
            "",
            "## 決定",
            "",
            "**維持現行 payload，不修改正式聊天 runtime。**",
            "",
            "行式訊息有值得保留的候選訊號，但 Holm 校正後 p=0.4614，且 95% 信賴區間跨過 0。",
            "因此本輪不改 runtime、不要求人類盲測，也不建立新 holdout。",
            "",
            "## 證據邊界",
            "",
            "這 12 個情境是先前已觀察過的 V29 開發案例。結果只能診斷表示法方向，不能證明更像人類、不能證明認知理論，也不能授權重訓或上線。",
        ]
    )
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-json", default=DEFAULT_JSON)
    parser.add_argument("--output-md", default=DEFAULT_MD)
    args = parser.parse_args()
    preregistration = json.loads(PREREG_PATH.read_text(encoding="utf-8"))
    amendment = json.loads(AMENDMENT_PATH.read_text(encoding="utf-8"))
    reports = load_reports(preregistration)
    analysis = build_analysis(preregistration, amendment, reports)
    Path(args.output_json).write_text(
        json.dumps(analysis, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    Path(args.output_md).write_text(render_markdown(analysis), encoding="utf-8")
    print(
        json.dumps(
            {
                "decision": analysis["decision"],
                "best_noncontrol_condition": analysis[
                    "best_noncontrol_condition"
                ],
                "advance_gates": analysis["advance_gates"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if all(analysis["verification"].values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
