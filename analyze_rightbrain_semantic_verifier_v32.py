#!/usr/bin/env python3
"""Analyze the preregistered shadow-only RightBrain semantic verifier V32."""

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import subprocess

from rightbrain_on_policy_dev_cases_v29 import case_inputs
from rightbrain_semantic_verifier_v32 import CONDITIONS, match_group, match_marker
from uruha_brain_mac import RightBrain


ROOT = Path(__file__).resolve().parent
PREREG_PATH = ROOT / "configs/rightbrain_semantic_verifier_v32_preregistration.json"
AMENDMENT_PATH = ROOT / "configs/rightbrain_semantic_verifier_v32_amendment.json"
DEFAULT_JSON = ROOT / "reports/rightbrain_semantic_verifier_v32_analysis.json"
DEFAULT_MD = ROOT / "reports/rightbrain_semantic_verifier_v32_analysis.md"
SEMANTIC_REASON_PREFIX = "semantic_slots_missing:"
CONDITION_LABELS_ZH = {
    "legacy_control": "現行字面 matcher（對照組）",
    "lemma_polarity": "字典形＋肯否極性",
    "lemma_polarity_reading": "字典形＋肯否極性＋讀音",
}


def sha256_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def safe_rate(numerator, denominator):
    return numerator / denominator if denominator else None


def _legacy_matcher():
    rightbrain = RightBrain.__new__(RightBrain)
    return rightbrain._semantic_marker_hit


def load_preregistration():
    return json.loads(PREREG_PATH.read_text(encoding="utf-8"))


def load_calibration(preregistration):
    path = ROOT / preregistration["frozen_inputs"]["calibration_dataset_path"]
    return json.loads(path.read_text(encoding="utf-8"))


def _v31_paths(preregistration):
    return [
        ROOT / "reports" / name
        for name in preregistration["frozen_inputs"]["v31_report_sha256"]
    ]


def load_v31_reports(preregistration):
    return [
        json.loads(path.read_text(encoding="utf-8"))
        for path in _v31_paths(preregistration)
    ]


def verify_sources(preregistration, amendment, calibration, reports):
    frozen = preregistration["frozen_inputs"]
    checks = {
        "runtime_sha256_matches": sha256_file(ROOT / frozen["runtime_path"])
        == frozen["runtime_sha256"],
        "v29_case_module_sha256_matches": sha256_file(
            ROOT / frozen["v29_case_module_path"]
        )
        == frozen["v29_case_module_sha256"],
        "calibration_sha256_matches": sha256_file(
            ROOT / frozen["calibration_dataset_path"]
        )
        == frozen["calibration_dataset_sha256"],
        "v31_analysis_sha256_matches": sha256_file(
            ROOT / frozen["v31_analysis_path"]
        )
        == frozen["v31_analysis_sha256"],
        "calibration_case_count_matches": len(calibration["cases"])
        == frozen["calibration_case_count"],
        "calibration_positive_count_matches": sum(
            bool(row["expected_hit"]) for row in calibration["cases"]
        )
        == frozen["calibration_positive_count"],
        "calibration_negative_count_matches": sum(
            not bool(row["expected_hit"]) for row in calibration["cases"]
        )
        == frozen["calibration_negative_count"],
        "v31_report_count_matches": len(reports) == frozen["v31_report_count"],
        "initial_analysis_sha256_matches_amendment": sha256_file(
            ROOT / amendment["initial_analysis_path"]
        )
        == amendment["initial_analysis_sha256"],
    }
    pre_fix_source = subprocess.run(
        [
            "git",
            "show",
            f"{amendment['pre_fix_commit']}:rightbrain_semantic_verifier_v32.py",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
    ).stdout
    checks["pre_fix_matcher_sha256_matches_amendment"] = (
        hashlib.sha256(pre_fix_source).hexdigest()
        == amendment["pre_fix_matcher_sha256"]
    )
    expected_hashes = frozen["v31_report_sha256"]
    checks["all_v31_report_hashes_match"] = all(
        sha256_file(ROOT / "reports" / name) == digest
        for name, digest in expected_hashes.items()
    )
    checks["v31_candidate_count_matches"] = sum(
        int(case.get("initial_accepted_candidate_count") or 0)
        + len(case.get("model_initial_rejected_candidates") or [])
        for report in reports
        for case in report.get("cases") or []
    ) == frozen["v31_candidate_count"]
    checks["v31_case_ids_match_frozen_v29"] = {
        case["id"] for case in case_inputs()
    } == {
        case["id"]
        for report in reports
        for case in report.get("cases") or []
    }
    return checks


def analyze_calibration(calibration, legacy_hit):
    rows = []
    summaries = {}
    predictions = defaultdict(dict)
    for condition in CONDITIONS:
        counts = Counter()
        family_counts = defaultdict(Counter)
        mode_counts = Counter()
        condition_rows = []
        for case in calibration["cases"]:
            trace = match_marker(
                case["reply"],
                case["marker"],
                condition,
                legacy_hit,
            )
            expected = bool(case["expected_hit"])
            predicted = bool(trace.hit)
            predictions[condition][case["id"]] = predicted
            outcome = (
                "tp"
                if expected and predicted
                else "fn"
                if expected
                else "fp"
                if predicted
                else "tn"
            )
            counts[outcome] += 1
            family_counts[case["family"]][outcome] += 1
            mode_counts[trace.mode] += 1
            row = {
                **case,
                "condition": condition,
                "predicted_hit": predicted,
                "outcome": outcome,
                "trace": trace.to_dict(),
            }
            rows.append(row)
            condition_rows.append(row)
        positive_count = counts["tp"] + counts["fn"]
        negative_count = counts["tn"] + counts["fp"]
        critical_false_positives = [
            row
            for row in condition_rows
            if row.get("critical_negative") and row["outcome"] == "fp"
        ]
        summaries[condition] = {
            "case_count": len(condition_rows),
            "true_positive_count": counts["tp"],
            "false_negative_count": counts["fn"],
            "true_negative_count": counts["tn"],
            "false_positive_count": counts["fp"],
            "positive_recall": safe_rate(counts["tp"], positive_count),
            "negative_specificity": safe_rate(counts["tn"], negative_count),
            "accuracy": safe_rate(counts["tp"] + counts["tn"], len(condition_rows)),
            "critical_false_positive_count": len(critical_false_positives),
            "critical_false_positive_ids": [row["id"] for row in critical_false_positives],
            "match_mode_counts": dict(sorted(mode_counts.items())),
            "per_family": {
                family: {
                    "case_count": sum(values.values()),
                    "correct_count": values["tp"] + values["tn"],
                    "accuracy": safe_rate(
                        values["tp"] + values["tn"],
                        sum(values.values()),
                    ),
                }
                for family, values in sorted(family_counts.items())
            },
        }

    control = predictions["legacy_control"]
    for condition in CONDITIONS[1:]:
        summary = summaries[condition]
        summary["new_critical_false_positive_count"] = sum(
            1
            for case in calibration["cases"]
            if case.get("critical_negative")
            and not control[case["id"]]
            and predictions[condition][case["id"]]
        )
        summary["new_critical_false_positive_ids"] = [
            case["id"]
            for case in calibration["cases"]
            if case.get("critical_negative")
            and not control[case["id"]]
            and predictions[condition][case["id"]]
        ]
    summaries["legacy_control"]["new_critical_false_positive_count"] = 0
    summaries["legacy_control"]["new_critical_false_positive_ids"] = []
    return summaries, rows


def _semantic_group_hits(reply, groups, condition, legacy_hit):
    group_hits = []
    group_traces = []
    for group in groups:
        hit, traces = match_group(reply, group, condition, legacy_hit)
        group_hits.append(hit)
        group_traces.append([trace.to_dict() for trace in traces])
    return group_hits, group_traces


def analyze_v31_shadow(reports, legacy_hit):
    groups_by_case = {
        case["id"]: [list(group) for group in case["required_marker_groups"]]
        for case in case_inputs()
    }
    summaries = {}
    all_newly_accepted = []
    for verifier_condition in CONDITIONS:
        by_payload = defaultdict(Counter)
        per_seed_payload = defaultdict(Counter)
        newly_accepted = []
        for report in reports:
            payload_condition = report["condition"]
            seed = int(report["seed"])
            for case in report["cases"]:
                case_id = case["id"]
                current_accepted = int(
                    case.get("initial_accepted_candidate_count") or 0
                )
                treatment_accepted = current_accepted
                for rejected in case.get("model_initial_rejected_candidates") or []:
                    old_reasons = list(rejected.get("rejection_reasons") or [])
                    if verifier_condition == "legacy_control":
                        continue
                    nonsemantic_reasons = [
                        reason
                        for reason in old_reasons
                        if not str(reason).startswith(SEMANTIC_REASON_PREFIX)
                    ]
                    raw_candidate = str(rejected.get("raw_candidate") or "")
                    group_hits, group_traces = _semantic_group_hits(
                        raw_candidate,
                        groups_by_case[case_id],
                        verifier_condition,
                        legacy_hit,
                    )
                    new_reasons = list(nonsemantic_reasons)
                    if group_hits and not all(group_hits):
                        new_reasons.append(
                            f"{SEMANTIC_REASON_PREFIX}{sum(group_hits)}/{len(group_hits)}"
                        )
                    if not new_reasons:
                        treatment_accepted += 1
                        item = {
                            "verifier_condition": verifier_condition,
                            "payload_condition": payload_condition,
                            "seed": seed,
                            "case_id": case_id,
                            "candidate_index": rejected.get("candidate_index"),
                            "raw_candidate": raw_candidate,
                            "old_rejection_reasons": old_reasons,
                            "new_rejection_reasons": new_reasons,
                            "semantic_group_hits": group_hits,
                            "semantic_group_traces": group_traces,
                            "no_other_rejection_reason": not nonsemantic_reasons,
                        }
                        newly_accepted.append(item)
                        all_newly_accepted.append(item)
                current_covered = current_accepted > 0
                treatment_covered = treatment_accepted > 0
                counts = by_payload[payload_condition]
                counts["seed_case_pair_count"] += 1
                counts["current_covered"] += int(current_covered)
                counts["treatment_covered"] += int(treatment_covered)
                counts["current_candidate_accepted"] += current_accepted
                counts["treatment_candidate_accepted"] += treatment_accepted
                seed_counts = per_seed_payload[(payload_condition, seed)]
                seed_counts["pair_count"] += 1
                seed_counts["current_covered"] += int(current_covered)
                seed_counts["treatment_covered"] += int(treatment_covered)
        payload_summaries = {}
        for payload_condition, counts in sorted(by_payload.items()):
            pair_count = counts["seed_case_pair_count"]
            payload_summaries[payload_condition] = {
                "seed_case_pair_count": pair_count,
                "current_strict_case_coverage_count": counts["current_covered"],
                "current_strict_case_coverage_rate": safe_rate(
                    counts["current_covered"], pair_count
                ),
                "treatment_strict_case_coverage_count": counts[
                    "treatment_covered"
                ],
                "treatment_strict_case_coverage_rate": safe_rate(
                    counts["treatment_covered"], pair_count
                ),
                "strict_case_coverage_delta": safe_rate(
                    counts["treatment_covered"] - counts["current_covered"],
                    pair_count,
                ),
                "current_candidate_accepted_count": counts[
                    "current_candidate_accepted"
                ],
                "treatment_candidate_accepted_count": counts[
                    "treatment_candidate_accepted"
                ],
                "new_candidate_accepted_count": counts[
                    "treatment_candidate_accepted"
                ]
                - counts["current_candidate_accepted"],
                "per_seed": {
                    str(seed): {
                        "pair_count": per_seed_payload[(payload_condition, seed)][
                            "pair_count"
                        ],
                        "current_coverage_rate": safe_rate(
                            per_seed_payload[(payload_condition, seed)][
                                "current_covered"
                            ],
                            per_seed_payload[(payload_condition, seed)]["pair_count"],
                        ),
                        "treatment_coverage_rate": safe_rate(
                            per_seed_payload[(payload_condition, seed)][
                                "treatment_covered"
                            ],
                            per_seed_payload[(payload_condition, seed)]["pair_count"],
                        ),
                    }
                    for seed in sorted(
                        key_seed
                        for key_payload, key_seed in per_seed_payload
                        if key_payload == payload_condition
                    )
                },
            }
        summaries[verifier_condition] = {
            "payload_conditions": payload_summaries,
            "newly_accepted_candidate_count": len(newly_accepted),
            "all_newly_accepted_have_no_other_rejection_reason": all(
                item["no_other_rejection_reason"] for item in newly_accepted
            ),
            "newly_accepted_candidates": newly_accepted,
        }
    return summaries, all_newly_accepted


def verify_v31_baseline(preregistration, v31_shadow):
    frozen_analysis = json.loads(
        (ROOT / preregistration["frozen_inputs"]["v31_analysis_path"]).read_text(
            encoding="utf-8"
        )
    )
    control_shadow = v31_shadow["legacy_control"]["payload_conditions"]
    checks = {}
    for payload_condition, frozen in frozen_analysis["condition_summary"].items():
        observed = control_shadow[payload_condition]
        checks[f"{payload_condition}_strict_coverage_matches_v31"] = (
            observed["current_strict_case_coverage_count"]
            == frozen["strict_case_coverage_count"]
            and observed["current_strict_case_coverage_rate"]
            == frozen["strict_case_coverage_rate"]
            and observed["treatment_strict_case_coverage_count"]
            == frozen["strict_case_coverage_count"]
        )
        checks[f"{payload_condition}_accepted_candidates_match_v31"] = (
            observed["current_candidate_accepted_count"]
            == frozen["strict_accepted_candidate_count"]
            and observed["treatment_candidate_accepted_count"]
            == frozen["strict_accepted_candidate_count"]
        )
    checks["legacy_shadow_adds_no_candidate"] = (
        v31_shadow["legacy_control"]["newly_accepted_candidate_count"] == 0
    )
    return checks


def _select_treatment(calibration_summaries):
    control = calibration_summaries["legacy_control"]
    eligible = []
    complexity = {"lemma_polarity": 0, "lemma_polarity_reading": 1}
    for condition in CONDITIONS[1:]:
        summary = calibration_summaries[condition]
        if summary["new_critical_false_positive_count"]:
            continue
        if summary["negative_specificity"] < control["negative_specificity"]:
            continue
        eligible.append(condition)
    if not eligible:
        return None
    return min(
        eligible,
        key=lambda condition: (
            -calibration_summaries[condition]["positive_recall"],
            calibration_summaries[condition]["match_mode_counts"].get(
                "reading", 0
            ),
            complexity[condition],
        ),
    )


def build_analysis(preregistration, amendment, calibration, reports):
    verification = verify_sources(
        preregistration,
        amendment,
        calibration,
        reports,
    )
    legacy_hit = _legacy_matcher()
    calibration_summaries, calibration_rows = analyze_calibration(
        calibration,
        legacy_hit,
    )
    v31_shadow, newly_accepted = analyze_v31_shadow(reports, legacy_hit)
    verification.update(verify_v31_baseline(preregistration, v31_shadow))
    selected = _select_treatment(calibration_summaries)
    requirements = preregistration["advance_gate"]["requirements"]
    if selected is None:
        gates = {
            "all_hash_and_accounting_checks_pass": all(verification.values()),
            "positive_recall_delta_vs_legacy_at_least_20pp": False,
            "negative_specificity_not_below_legacy": False,
            "new_critical_false_positive_count_is_zero": False,
            "all_v31_newly_accepted_candidates_have_no_other_rejection_reason": False,
            "v31_strict_case_coverage_noninferior_in_every_payload_condition": False,
        }
    else:
        control = calibration_summaries["legacy_control"]
        treatment = calibration_summaries[selected]
        shadow = v31_shadow[selected]
        noninferior = all(
            summary["treatment_strict_case_coverage_rate"]
            >= summary["current_strict_case_coverage_rate"]
            for summary in shadow["payload_conditions"].values()
        )
        gates = {
            "all_hash_and_accounting_checks_pass": all(verification.values()),
            "positive_recall_delta_vs_legacy_at_least_20pp": (
                treatment["positive_recall"] - control["positive_recall"]
            )
            >= requirements["positive_recall_delta_vs_legacy_at_least"],
            "negative_specificity_not_below_legacy": treatment[
                "negative_specificity"
            ]
            >= control["negative_specificity"],
            "new_critical_false_positive_count_is_zero": treatment[
                "new_critical_false_positive_count"
            ]
            == requirements["new_critical_false_positive_count"],
            "all_v31_newly_accepted_candidates_have_no_other_rejection_reason": shadow[
                "all_newly_accepted_have_no_other_rejection_reason"
            ],
            "v31_strict_case_coverage_noninferior_in_every_payload_condition": noninferior,
        }
    authorize_holdout = selected is not None and all(gates.values())
    return {
        "schema": "uruha_rightbrain_semantic_verifier_analysis_v32",
        "preregistration_path": str(PREREG_PATH.relative_to(ROOT)),
        "preregistration_sha256": sha256_file(PREREG_PATH),
        "amendment_path": str(AMENDMENT_PATH.relative_to(ROOT)),
        "amendment_sha256": sha256_file(AMENDMENT_PATH),
        "implementation_path": "rightbrain_semantic_verifier_v32.py",
        "implementation_sha256": sha256_file(
            ROOT / "rightbrain_semantic_verifier_v32.py"
        ),
        "verification": verification,
        "calibration_summary": calibration_summaries,
        "calibration_rows": calibration_rows,
        "v31_shadow": v31_shadow,
        "selected_treatment": selected,
        "advance_gates": gates,
        "authorize_source_separated_verifier_holdout": authorize_holdout,
        "authorize_runtime_change": False,
        "authorize_model_retraining": False,
        "authorize_human_blind_review": False,
        "decision": (
            f"authorize_source_separated_verifier_holdout_for_{selected}"
            if authorize_holdout
            else "keep_legacy_runtime_verifier"
        ),
        "retrospective_newly_accepted_candidate_count_all_treatments": len(
            newly_accepted
        ),
        "research_boundary": preregistration["research_boundary"],
    }


def _fmt_pct(value):
    return "n/a" if value is None else f"{100 * value:.1f}%"


def _fmt_pp(value):
    return "n/a" if value is None else f"{100 * value:+.1f} pp"


def render_markdown(analysis):
    summaries = analysis["calibration_summary"]
    control = summaries["legacy_control"]
    lines = [
        "# 右腦 V32：日文語意 verifier 校準結果",
        "",
        "本輪只重算 verifier，不重新生成、改寫或訓練任何右腦回答。",
        "",
        "## 48 例校準結果",
        "",
        "| 條件 | 正例 recall | 負例 specificity | critical FP | 總正確率 |",
        "|---|---:|---:|---:|---:|",
    ]
    for condition in CONDITIONS:
        summary = summaries[condition]
        lines.append(
            f"| {CONDITION_LABELS_ZH[condition]} | "
            f"{_fmt_pct(summary['positive_recall'])} | "
            f"{_fmt_pct(summary['negative_specificity'])} | "
            f"{summary['critical_false_positive_count']} | "
            f"{_fmt_pct(summary['accuracy'])} |"
        )
    lines.extend(["", "## 相對現行 matcher", ""])
    for condition in CONDITIONS[1:]:
        summary = summaries[condition]
        lines.append(
            f"- {CONDITION_LABELS_ZH[condition]}：recall "
            f"{_fmt_pp(summary['positive_recall'] - control['positive_recall'])}；"
            f"specificity {_fmt_pp(summary['negative_specificity'] - control['negative_specificity'])}；"
            f"新增 critical FP={summary['new_critical_false_positive_count']}。"
        )
    lines.extend(["", "## V31 凍結候選 shadow", ""])
    selected = analysis["selected_treatment"]
    if selected:
        lines.extend(
            [
                f"預註冊規則選出的處理：**{CONDITION_LABELS_ZH[selected]}**。",
                "",
                "| V31 payload | 現行覆蓋率 | shadow 覆蓋率 | 差異 | 新通過候選 |",
                "|---|---:|---:|---:|---:|",
            ]
        )
        for payload, summary in analysis["v31_shadow"][selected][
            "payload_conditions"
        ].items():
            lines.append(
                f"| {payload} | {_fmt_pct(summary['current_strict_case_coverage_rate'])} | "
                f"{_fmt_pct(summary['treatment_strict_case_coverage_rate'])} | "
                f"{_fmt_pp(summary['strict_case_coverage_delta'])} | "
                f"{summary['new_candidate_accepted_count']} |"
            )
    else:
        lines.append("沒有處理條件通過基本安全選擇規則。")
    lines.extend(["", "## 晉級門檻", ""])
    for name, passed in analysis["advance_gates"].items():
        lines.append(f"- {'通過' if passed else '未通過'}：`{name}`")
    lines.extend(
        [
            "",
            "## 決定",
            "",
            f"**{analysis['decision']}**",
            "",
            "本輪不改 runtime、不重訓模型，也不要求人類盲測。通過只允許建立新的來源分離 verifier holdout。",
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
    preregistration = load_preregistration()
    amendment = json.loads(AMENDMENT_PATH.read_text(encoding="utf-8"))
    calibration = load_calibration(preregistration)
    reports = load_v31_reports(preregistration)
    analysis = build_analysis(preregistration, amendment, calibration, reports)
    Path(args.output_json).write_text(
        json.dumps(analysis, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    Path(args.output_md).write_text(
        render_markdown(analysis),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "decision": analysis["decision"],
                "selected_treatment": analysis["selected_treatment"],
                "advance_gates": analysis["advance_gates"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if all(analysis["verification"].values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
