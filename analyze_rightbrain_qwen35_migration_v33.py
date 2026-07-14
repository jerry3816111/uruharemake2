#!/usr/bin/env python3
"""Analyze the frozen V33 local deployment comparison."""

import argparse
import hashlib
import json
import math
import random
import statistics
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parent
RAW_PATH = ROOT / "reports" / "rightbrain_qwen35_migration_v33_raw.json"
JSON_PATH = ROOT / "reports" / "rightbrain_qwen35_migration_v33_analysis.json"
MD_PATH = ROOT / "reports" / "rightbrain_qwen35_migration_v33_analysis.md"
DATASET_PATH = ROOT / "datasets" / "rightbrain_qwen35_migration_v33_holdout.json"
PREREG_PATH = ROOT / "configs" / "rightbrain_qwen35_migration_v33_preregistration.json"
CONTROL = "qwen2_5_7b_quantized_control"
TREATMENT = "qwen3_5_9b_quantized_treatment"


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _safe_rate(numerator, denominator):
    return numerator / denominator if denominator else None


def _fmt_pct(value):
    return "n/a" if value is None else f"{100 * value:.1f}%"


def exact_mcnemar(control_wins, treatment_wins):
    discordant = int(control_wins) + int(treatment_wins)
    if not discordant:
        return 1.0
    lower = min(int(control_wins), int(treatment_wins))
    one_tail = sum(math.comb(discordant, index) for index in range(lower + 1)) / (2**discordant)
    return min(1.0, 2 * one_tail)


def _paired_binary(control_map, treatment_map):
    if set(control_map) != set(treatment_map):
        raise ValueError("Paired maps have different keys")
    treatment_wins = sum(not control_map[key] and treatment_map[key] for key in control_map)
    control_wins = sum(control_map[key] and not treatment_map[key] for key in control_map)
    return {
        "pair_count": len(control_map),
        "control_wins": control_wins,
        "treatment_wins": treatment_wins,
        "ties": len(control_map) - control_wins - treatment_wins,
        "control_rate": _safe_rate(sum(control_map.values()), len(control_map)),
        "treatment_rate": _safe_rate(sum(treatment_map.values()), len(treatment_map)),
        "treatment_delta": _safe_rate(sum(treatment_map.values()), len(treatment_map))
        - _safe_rate(sum(control_map.values()), len(control_map)),
        "mcnemar_exact_p": exact_mcnemar(control_wins, treatment_wins),
    }


def _case_cluster_bootstrap(control_map, treatment_map, samples=10000, seed=20260715):
    cases = sorted({key[0] for key in control_map})
    rng = random.Random(seed)
    deltas = []
    for _ in range(samples):
        sampled = [rng.choice(cases) for _ in cases]
        control_values = []
        treatment_values = []
        for case_id in sampled:
            keys = sorted(key for key in control_map if key[0] == case_id)
            control_values.extend(int(control_map[key]) for key in keys)
            treatment_values.extend(int(treatment_map[key]) for key in keys)
        deltas.append(statistics.mean(treatment_values) - statistics.mean(control_values))
    deltas.sort()
    return {
        "samples": samples,
        "lower_95": deltas[int(0.025 * samples)],
        "upper_95": deltas[min(samples - 1, int(0.975 * samples))],
    }


def _rightbrain_coverage_map(rows):
    grouped = defaultdict(list)
    for row in rows:
        grouped[(row["case_id"], row["seed"])].append(bool(row["score"]["semantic_contract_pass"]))
    return {key: any(values) for key, values in grouped.items()}


def _rightbrain_strict_map(rows):
    grouped = defaultdict(list)
    for row in rows:
        grouped[(row["case_id"], row["seed"])].append(bool(row["score"]["current_gate_raw_pass"]))
    return {key: any(values) for key, values in grouped.items()}


def summarize_rightbrain(rows):
    coverage = _rightbrain_coverage_map(rows)
    strict = _rightbrain_strict_map(rows)
    category_pairs = defaultdict(list)
    case_category = {row["case_id"]: row["category"] for row in rows}
    for (case_id, _seed), passed in coverage.items():
        category_pairs[case_category[case_id]].append(passed)
    slot_hits = sum(row["score"]["semantic_group_hit_count"] for row in rows)
    slot_total = sum(row["score"]["semantic_group_count"] for row in rows)
    normalized = [row["score"]["normalized_reply"] for row in rows if row["score"]["normalized_reply"]]
    duplicate_count = len(normalized) - len(set(normalized))
    warm_latencies = [row["response_metrics"]["wall_seconds"] for row in rows[1:]]
    reason_counts = Counter(
        reason for row in rows for reason in row["score"]["current_gate_rejection_reasons"]
    )
    return {
        "candidate_count": len(rows),
        "seed_case_pair_count": len(coverage),
        "raw_semantic_contract_coverage_rate": _safe_rate(sum(coverage.values()), len(coverage)),
        "raw_strict_surface_coverage_rate": _safe_rate(sum(strict.values()), len(strict)),
        "candidate_semantic_contract_pass_rate": _safe_rate(
            sum(row["score"]["semantic_contract_pass"] for row in rows), len(rows)
        ),
        "v32_semantic_slot_recall": _safe_rate(slot_hits, slot_total),
        "raw_current_gate_pass_rate": _safe_rate(
            sum(row["score"]["current_gate_raw_pass"] for row in rows), len(rows)
        ),
        "hard_surface_failure_rate": _safe_rate(
            sum(row["score"]["hard_surface_failure"] for row in rows), len(rows)
        ),
        "polite_or_service_register_rate": _safe_rate(
            sum(row["score"]["polite_or_service_register"] for row in rows), len(rows)
        ),
        "private_memory_intrusion_count": sum(row["score"]["private_memory_intrusion"] for row in rows),
        "private_memory_intrusion_rate": _safe_rate(
            sum(row["score"]["private_memory_intrusion"] for row in rows), len(rows)
        ),
        "normalized_duplicate_candidate_rate": _safe_rate(duplicate_count, len(normalized)),
        "warm_generation_median_seconds": statistics.median(warm_latencies),
        "warm_generation_p95_seconds": sorted(warm_latencies)[int(0.95 * (len(warm_latencies) - 1))],
        "per_category_semantic_coverage": {
            category: _safe_rate(sum(values), len(values))
            for category, values in sorted(category_pairs.items())
        },
        "rejection_reason_counts": dict(reason_counts.most_common()),
    }


def summarize_actions(rows):
    no_action_rows = [row for row in rows if row["score"]["expected_call_count"] == 0]
    required_rows = [row for row in rows if row["score"]["expected_call_count"] > 0]
    negated = [row for row in rows if row["family"] == "negated_action"]
    by_family = defaultdict(list)
    for row in rows:
        by_family[row["family"]].append(row)
    recalls = [row["score"]["required_action_recall"] for row in required_rows]
    warm_latencies = [row["response_metrics"]["wall_seconds"] for row in rows]
    return {
        "case_count": len(rows),
        "exact_tool_call_set_and_argument_accuracy": _safe_rate(
            sum(row["score"]["exact_match"] for row in rows), len(rows)
        ),
        "no_action_case_count": len(no_action_rows),
        "no_action_specificity": _safe_rate(
            sum(row["score"]["no_action_correct"] for row in no_action_rows), len(no_action_rows)
        ),
        "mean_required_action_recall": statistics.mean(recalls) if recalls else None,
        "false_action_rate": _safe_rate(
            sum(row["score"]["false_action"] for row in rows), len(rows)
        ),
        "negation_violation_count": sum(row["score"]["negation_violation"] for row in negated),
        "invalid_tool_or_argument_count": sum(
            row["score"]["invalid_tool_or_argument"] for row in rows
        ),
        "warm_generation_median_seconds": statistics.median(warm_latencies),
        "warm_generation_p95_seconds": sorted(warm_latencies)[int(0.95 * (len(warm_latencies) - 1))],
        "per_family_exact_accuracy": {
            family: _safe_rate(sum(row["score"]["exact_match"] for row in family_rows), len(family_rows))
            for family, family_rows in sorted(by_family.items())
        },
    }


def _action_exact_map(rows):
    return {row["case_id"]: bool(row["score"]["exact_match"]) for row in rows}


def _blob_verification(prereg):
    rows = {}
    for condition, config in prereg["frozen_environment"]["conditions"].items():
        digest = config["blob_sha256"]
        path = Path.home() / ".ollama" / "models" / "blobs" / f"sha256-{digest}"
        rows[condition] = {
            "path_exists": path.exists(),
            "size_matches": path.exists() and path.stat().st_size == config["blob_bytes"],
            "sha256_matches": path.exists() and _sha256(path) == digest,
        }
    return rows


def expected_holdout_accounting(prereg):
    holdout = prereg["stage_1_design"]["fresh_holdout"]
    return {
        "rightbrain_categories": {
            category: holdout["rightbrain_cases_per_category"]
            for category in holdout["rightbrain_categories"]
        },
        "action_families": {
            family: holdout["action_cases_per_family"]
            for family in holdout["action_families"]
        },
    }


def _find_examples(control_rows, treatment_rows, key_fn, limit=6):
    control = {row["case_id"] if "seed" not in row else (row["case_id"], row["seed"], row.get("candidate_index")): row for row in control_rows}
    treatment = {row["case_id"] if "seed" not in row else (row["case_id"], row["seed"], row.get("candidate_index")): row for row in treatment_rows}
    treatment_wins = []
    control_wins = []
    for key in sorted(set(control) & set(treatment), key=str):
        control_pass = key_fn(control[key])
        treatment_pass = key_fn(treatment[key])
        item = {"key": key, "control": control[key], "treatment": treatment[key]}
        if treatment_pass and not control_pass and len(treatment_wins) < limit:
            treatment_wins.append(item)
        elif control_pass and not treatment_pass and len(control_wins) < limit:
            control_wins.append(item)
    return {"treatment_wins": treatment_wins, "control_wins": control_wins}


def analyze(raw_path=RAW_PATH):
    raw = json.loads(raw_path.read_text(encoding="utf-8"))
    dataset = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    prereg = json.loads(PREREG_PATH.read_text(encoding="utf-8"))
    right_rows = {
        condition: [row for row in raw["rightbrain_rows"] if row["condition"] == condition]
        for condition in (CONTROL, TREATMENT)
    }
    action_rows = {
        condition: [row for row in raw["action_rows"] if row["condition"] == condition]
        for condition in (CONTROL, TREATMENT)
    }
    right_summary = {condition: summarize_rightbrain(rows) for condition, rows in right_rows.items()}
    action_summary = {condition: summarize_actions(rows) for condition, rows in action_rows.items()}
    right_pair = _paired_binary(
        _rightbrain_coverage_map(right_rows[CONTROL]),
        _rightbrain_coverage_map(right_rows[TREATMENT]),
    )
    right_pair["case_cluster_bootstrap_95"] = _case_cluster_bootstrap(
        _rightbrain_coverage_map(right_rows[CONTROL]),
        _rightbrain_coverage_map(right_rows[TREATMENT]),
    )
    action_pair = _paired_binary(
        _action_exact_map(action_rows[CONTROL]),
        _action_exact_map(action_rows[TREATMENT]),
    )

    expected_right_rows = len(dataset["rightbrain_cases"]) * 3 * 3
    expected_action_rows = len(dataset["action_cases"])
    right_keys = [
        (row["condition"], row["case_id"], row["seed"], row["candidate_index"])
        for row in raw["rightbrain_rows"]
    ]
    action_keys = [(row["condition"], row["case_id"]) for row in raw["action_rows"]]
    blob_verification = _blob_verification(prereg)
    expected_accounting = expected_holdout_accounting(prereg)
    verification = {
        "run_completed": bool(raw.get("completed_at")),
        "preregistration_sha256_matches": raw.get("preregistration_sha256") == _sha256(PREREG_PATH),
        "dataset_sha256_matches": raw.get("dataset_sha256") == _sha256(DATASET_PATH),
        "dataset_preregistration_sha256_matches": dataset.get("preregistration_sha256") == _sha256(PREREG_PATH),
        "rightbrain_row_count_matches": all(len(right_rows[c]) == expected_right_rows for c in (CONTROL, TREATMENT)),
        "action_row_count_matches": all(len(action_rows[c]) == expected_action_rows for c in (CONTROL, TREATMENT)),
        "rightbrain_keys_unique": len(right_keys) == len(set(right_keys)),
        "action_keys_unique": len(action_keys) == len(set(action_keys)),
        "rightbrain_category_accounting_matches": dataset["accounting"]["rightbrain_categories"]
        == expected_accounting["rightbrain_categories"],
        "action_family_accounting_matches": dataset["accounting"]["action_families"]
        == expected_accounting["action_families"],
        "model_blob_hashes_match": all(
            row["path_exists"] and row["size_matches"] and row["sha256_matches"]
            for row in blob_verification.values()
        ),
    }

    control_right = right_summary[CONTROL]
    treatment_right = right_summary[TREATMENT]
    control_action = action_summary[CONTROL]
    treatment_action = action_summary[TREATMENT]
    slowdown = treatment_right["warm_generation_median_seconds"] / control_right["warm_generation_median_seconds"]
    gate_requirements = prereg["stage_1_advance_gate"]["requirements"]
    gates = {
        "all_hash_source_separation_and_accounting_checks_pass": all(verification.values()),
        "rightbrain_raw_semantic_coverage_delta_vs_qwen2_5_at_least_0": right_pair["treatment_delta"]
        >= gate_requirements["rightbrain_raw_semantic_coverage_delta_vs_qwen2_5_at_least"],
        "rightbrain_hard_surface_failure_delta_vs_qwen2_5_at_most_2pp": treatment_right["hard_surface_failure_rate"]
        - control_right["hard_surface_failure_rate"]
        <= gate_requirements["rightbrain_hard_surface_failure_delta_vs_qwen2_5_at_most"],
        "private_memory_intrusion_count_is_0": treatment_right["private_memory_intrusion_count"]
        == gate_requirements["private_memory_intrusion_count"],
        "action_exact_accuracy_delta_vs_qwen2_5_at_least_5pp": action_pair["treatment_delta"]
        >= gate_requirements["action_exact_accuracy_delta_vs_qwen2_5_at_least"],
        "action_no_action_specificity_not_lower": treatment_action["no_action_specificity"]
        - control_action["no_action_specificity"]
        >= gate_requirements["action_no_action_specificity_delta_vs_qwen2_5_at_least"],
        "negation_violation_count_is_0": treatment_action["negation_violation_count"]
        == gate_requirements["negation_violation_count"],
        "warm_generation_median_seconds_at_most_5": treatment_right["warm_generation_median_seconds"]
        <= gate_requirements["warm_generation_median_seconds_at_most"],
        "warm_generation_slowdown_ratio_at_most_1_75": slowdown
        <= gate_requirements["warm_generation_slowdown_ratio_vs_qwen2_5_at_most"],
        "model_blob_bytes_at_most_8gib": raw["model_conditions"][TREATMENT]["blob_bytes"]
        <= gate_requirements["model_blob_bytes_at_most"],
    }
    decision = (
        prereg["stage_1_advance_gate"]["decision_if_all_pass"]
        if all(gates.values())
        else "do_not_authorize_qwen3_5_persona_adapter_experiment"
    )
    return {
        "schema": "uruha_rightbrain_qwen35_migration_analysis_v33",
        "raw_report_path": str(raw_path.relative_to(ROOT)),
        "raw_report_sha256": _sha256(raw_path),
        "preregistration_sha256": _sha256(PREREG_PATH),
        "dataset_sha256": _sha256(DATASET_PATH),
        "verification": verification,
        "blob_verification": blob_verification,
        "rightbrain_summary": right_summary,
        "rightbrain_paired": right_pair,
        "action_summary": action_summary,
        "action_paired": action_pair,
        "resource_summary": raw["resource_summary"],
        "warm_generation_slowdown_ratio": slowdown,
        "advance_gates": gates,
        "decision": decision,
        "rightbrain_examples": _find_examples(
            right_rows[CONTROL], right_rows[TREATMENT], lambda row: row["score"]["semantic_contract_pass"]
        ),
        "action_examples": _find_examples(
            action_rows[CONTROL], action_rows[TREATMENT], lambda row: row["score"]["exact_match"]
        ),
        "evidence_boundary": prereg["research_boundary"],
    }


def render_markdown(report):
    control_right = report["rightbrain_summary"][CONTROL]
    treatment_right = report["rightbrain_summary"][TREATMENT]
    control_action = report["action_summary"][CONTROL]
    treatment_action = report["action_summary"][TREATMENT]
    lines = [
        "# V33：Qwen2.5-7B 與 Qwen3.5-9B 本機候選正式比較",
        "",
        "## 結果總覽",
        "",
        "| 指標 | Qwen2.5-7B | Qwen3.5-9B | 差異 |",
        "|---|---:|---:|---:|",
        f"| 右腦語意契約覆蓋 | {_fmt_pct(control_right['raw_semantic_contract_coverage_rate'])} | {_fmt_pct(treatment_right['raw_semantic_contract_coverage_rate'])} | {_fmt_pct(report['rightbrain_paired']['treatment_delta'])} |",
        f"| V32 語意槽命中 | {_fmt_pct(control_right['v32_semantic_slot_recall'])} | {_fmt_pct(treatment_right['v32_semantic_slot_recall'])} | {_fmt_pct(treatment_right['v32_semantic_slot_recall'] - control_right['v32_semantic_slot_recall'])} |",
        f"| 硬性表面失敗 | {_fmt_pct(control_right['hard_surface_failure_rate'])} | {_fmt_pct(treatment_right['hard_surface_failure_rate'])} | {_fmt_pct(treatment_right['hard_surface_failure_rate'] - control_right['hard_surface_failure_rate'])} |",
        f"| 私密記憶洩漏 | {control_right['private_memory_intrusion_count']} | {treatment_right['private_memory_intrusion_count']} | {treatment_right['private_memory_intrusion_count'] - control_right['private_memory_intrusion_count']} |",
        f"| VRM 動作完全正確 | {_fmt_pct(control_action['exact_tool_call_set_and_argument_accuracy'])} | {_fmt_pct(treatment_action['exact_tool_call_set_and_argument_accuracy'])} | {_fmt_pct(report['action_paired']['treatment_delta'])} |",
        f"| 不該動作時正確 | {_fmt_pct(control_action['no_action_specificity'])} | {_fmt_pct(treatment_action['no_action_specificity'])} | {_fmt_pct(treatment_action['no_action_specificity'] - control_action['no_action_specificity'])} |",
        f"| 否定命令違反 | {control_action['negation_violation_count']} | {treatment_action['negation_violation_count']} | {treatment_action['negation_violation_count'] - control_action['negation_violation_count']} |",
        f"| 暖機生成中位數 | {control_right['warm_generation_median_seconds']:.2f} 秒 | {treatment_right['warm_generation_median_seconds']:.2f} 秒 | {report['warm_generation_slowdown_ratio']:.2f} 倍 |",
        "",
        "## 配對統計",
        "",
        f"- 右腦：Qwen3.5 單獨勝 {report['rightbrain_paired']['treatment_wins']} 組，Qwen2.5 單獨勝 {report['rightbrain_paired']['control_wins']} 組，McNemar p={report['rightbrain_paired']['mcnemar_exact_p']:.6f}。",
        f"- 右腦 case-cluster bootstrap 95%：[{_fmt_pct(report['rightbrain_paired']['case_cluster_bootstrap_95']['lower_95'])}, {_fmt_pct(report['rightbrain_paired']['case_cluster_bootstrap_95']['upper_95'])}]。",
        f"- 動作：Qwen3.5 單獨勝 {report['action_paired']['treatment_wins']} 題，Qwen2.5 單獨勝 {report['action_paired']['control_wins']} 題，McNemar p={report['action_paired']['mcnemar_exact_p']:.6f}。",
        "",
        "## 右腦各能力群",
        "",
        "| 能力群 | Qwen2.5 | Qwen3.5 |",
        "|---|---:|---:|",
    ]
    for category in sorted(control_right["per_category_semantic_coverage"]):
        lines.append(
            f"| {category} | {_fmt_pct(control_right['per_category_semantic_coverage'][category])} | {_fmt_pct(treatment_right['per_category_semantic_coverage'][category])} |"
        )
    lines.extend(["", "## VRM 動作各能力群", "", "| 能力群 | Qwen2.5 | Qwen3.5 |", "|---|---:|---:|"])
    for family in sorted(control_action["per_family_exact_accuracy"]):
        lines.append(
            f"| {family} | {_fmt_pct(control_action['per_family_exact_accuracy'][family])} | {_fmt_pct(treatment_action['per_family_exact_accuracy'][family])} |"
        )
    lines.extend(["", "## 預註冊晉級門檻", ""])
    for name, passed in report["advance_gates"].items():
        lines.append(f"- {'通過' if passed else '未通過'}：`{name}`")
    lines.extend(
        [
            "",
            "## 決定",
            "",
            f"**{report['decision']}**",
            "",
            "這項決定不會直接修改正式聊天 runtime，也不代表人格相似或人類意識。",
            "",
            "## 證據邊界",
            "",
            report["evidence_boundary"],
            "",
        ]
    )
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", type=Path, default=RAW_PATH)
    parser.add_argument("--json", type=Path, default=JSON_PATH)
    parser.add_argument("--markdown", type=Path, default=MD_PATH)
    args = parser.parse_args()
    report = analyze(args.raw)
    args.json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.markdown.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps({"decision": report["decision"], "advance_gates": report["advance_gates"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
