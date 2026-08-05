#!/usr/bin/env python3
"""Lock the corrected-oracle Top-3 lexical projection baseline."""

from __future__ import annotations

import json
from pathlib import Path

import build_source_preserving_memory_projection_v2_5_locomo_cases as v25
import build_source_preserving_memory_projection_v2_6_1_population_cases as v261


ROOT = Path(__file__).resolve().parent
CASES = ROOT / "configs/source_preserving_memory_projection_v2_6_1_population_cases.json"
REPORT_JSON = ROOT / "reports/source_preserving_memory_projection_v2_6_1_population_baseline.json"
REPORT_MD = ROOT / "reports/source_preserving_memory_projection_v2_6_1_population_baseline.md"
LOCK = ROOT / "configs/source_preserving_memory_projection_v2_6_1_population_result_lock.json"


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def summarize(manifest, prereg):
    cases = manifest["cases"]
    target_retained = sum(
        case["target"]["contains_answer_projection"] for case in cases
    )
    target_ratios = [
        case["target"]["projection_character_count"]
        / case["target"]["complete_character_count"]
        for case in cases
    ]
    all_ratios = [
        case[role]["projection_character_count"]
        / case[role]["complete_character_count"]
        for case in cases
        for role in ("target", "hard_negative")
    ]
    counts = {}
    for case in cases:
        counts[case["sample_id"]] = counts.get(case["sample_id"], 0) + 1
    return {
        "schema": "uruha_source_preserving_memory_projection_exposed_population_baseline_v2_6_1",
        "experiment_id": prereg["experiment_id"],
        "decision": "baseline_locked_authorize_adjacency_projection_preregistration_only",
        "evidence_scope": "exposed_locomo_development_baseline_only",
        "integrity": {
            "case_count": len(cases),
            "case_count_by_sample": counts,
            "all_construction_gates_passed": all(
                manifest["construction_gates"].values()
            ),
            "case_manifest_sha256": v25.file_sha256(CASES),
            "contains_official_text": manifest["contains_official_text"],
            "contains_official_answers": manifest["contains_official_answers"],
            "reserve_sample_access_count": manifest["reserve_sample_access_count"],
        },
        "metrics": {
            "top3_isolated_target_answer_retention_count": target_retained,
            "top3_isolated_target_answer_retention_rate": target_retained / len(cases),
            "target_answer_omission_count": len(cases) - target_retained,
            "mean_target_projection_character_ratio": round(
                sum(target_ratios) / len(target_ratios), 6
            ),
            "mean_all_record_projection_character_ratio": round(
                sum(all_ratios) / len(all_ratios), 6
            ),
            "construction_model_calls": manifest["construction_model_calls"],
        },
        "interpretation": "The isolated Top-3 lexical projection is efficient but not evidence-preserving on this corrected development population: it removes about eighty-three percent of target-session characters while omitting the answer-bearing turn in six of ten cases.",
        "authorization": {
            "preregister_adjacency_projection_on_same_cases": True,
            "change_any_other_variable": False,
            "model_generation": False,
            "use_reserve_conversations": False,
            "runtime_change": False,
            "runtime_shadow": False,
            "production_enablement": False,
        },
        "evidence_boundary": "This baseline measures deterministic source retention only on ten exposed LoCoMo single-hop cases. It does not evaluate an LLM or fresh reserve conversations.",
    }


def markdown(report):
    metrics = report["metrics"]
    return "\n".join(
        [
            "# V2.6.1 Corrected Development Baseline",
            "",
            f"**決策：`{report['decision']}`**",
            "",
            "| 舊 Top-3 孤立 turn 投影 | 結果 |",
            "|---|---:|",
            f"| 答案原文保留 | {metrics['top3_isolated_target_answer_retention_count']}/10 |",
            f"| 答案原文遺失 | {metrics['target_answer_omission_count']}/10 |",
            f"| 目標 Session 平均保留字元 | {metrics['mean_target_projection_character_ratio']:.1%} |",
            f"| 所有 record 平均保留字元 | {metrics['mean_all_record_projection_character_ratio']:.1%} |",
            f"| 模型呼叫 | {metrics['construction_model_calls']} |",
            "",
            "舊方法壓縮幅度大，但 60% 題目的答案原文在模型之前已經消失。這個 4/10 是下一輪鄰接視窗的固定 control。",
            "",
            "只授權在完全相同 10 題上預註冊鄰接視窗；不授權模型、reserve、runtime 或 production。",
            "",
        ]
    )


def main():
    if REPORT_JSON.exists() or REPORT_MD.exists() or LOCK.exists():
        raise SystemExit("V2.6.1 baseline result already exists")
    prereg = v261.load_preregistration()
    manifest = load_json(CASES)
    report = summarize(manifest, prereg)
    REPORT_JSON.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    REPORT_MD.write_text(markdown(report), encoding="utf-8")
    lock = {
        "schema": "uruha_source_preserving_memory_projection_exposed_population_result_lock_v2_6_1",
        "experiment_id": prereg["experiment_id"],
        "decision": report["decision"],
        "model_calls": 0,
        "artifacts": {
            path.relative_to(ROOT).as_posix(): v25.file_sha256(path)
            for path in (v261.PREREG, CASES, Path(__file__), REPORT_JSON, REPORT_MD)
        },
        "authorization": report["authorization"],
        "evidence_boundary": report["evidence_boundary"],
    }
    LOCK.write_text(json.dumps(lock, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "decision": report["decision"],
                "retention": report["metrics"][
                    "top3_isolated_target_answer_retention_count"
                ],
                "case_count": report["integrity"]["case_count"],
                "model_calls": 0,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
