#!/usr/bin/env python3
"""Analyze the sequential V2 RightBrain carrier screen without model calls."""

from __future__ import annotations

import json
from pathlib import Path

import run_rightbrain_carrier_model_screen_v1 as generation


ROOT = Path(__file__).resolve().parent
EXPERIMENT_ID = "rightbrain_carrier_model_screen_v2"
PREREGISTRATION_PATH = ROOT / "configs/rightbrain_carrier_model_screen_v2_preregistration.json"
CALIBRATION_PATH = ROOT / "reports/rightbrain_carrier_model_screen_v1_control_calibration.json"
RESULT_JSON_PATH = ROOT / "reports/rightbrain_carrier_model_screen_v2_result.json"
RESULT_MD_PATH = ROOT / "reports/rightbrain_carrier_model_screen_v2_result.md"
CONTROL_ID = "qwen2_5_7b_q4_control"
CANDIDATE_IDS = (
    "qwen3_5_4b_q4_candidate",
    "qwen3_5_9b_q4_candidate",
)
RAW_POLLUTION_REASONS = {
    "cjk_language_leak",
    "nonstandard_cjk_surface",
    "foreign_script_leak",
    "unexpected_ascii_leak",
    "ascii_symbol_artifact",
}


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def validate_preregistration(preregistration):
    frozen = preregistration["frozen_inputs"]
    bindings = {
        "v1_preregistration": generation.sha256_file(generation.PREREGISTRATION_PATH),
        "deep_preflight": generation.sha256_file(generation.PREFLIGHT_PATH),
        "control_artifact": generation.sha256_file(
            generation.CONDITION_ARTIFACTS[CONTROL_ID]
        ),
        "control_calibration": generation.sha256_file(CALIBRATION_PATH),
        "cases": generation.sha256_file(generation.CASES_PATH),
        "generation_harness": generation.sha256_file(
            ROOT / preregistration["generation_harness"]["path"]
        ),
    }
    checks = {
        "experiment_id": preregistration.get("experiment_id") == EXPERIMENT_ID,
        "status_frozen_before_candidates": preregistration.get("status")
        == "frozen_after_control_calibration_before_candidate_inference",
        "v1_preregistration_hash": bindings["v1_preregistration"]
        == frozen["v1_preregistration_sha256"],
        "deep_preflight_hash": bindings["deep_preflight"]
        == frozen["deep_preflight_sha256"],
        "control_artifact_hash": bindings["control_artifact"]
        == frozen["control_artifact_sha256"],
        "control_calibration_hash": bindings["control_calibration"]
        == frozen["control_calibration_sha256"],
        "cases_hash": bindings["cases"] == frozen["cases_sha256"],
        "generation_harness_hash": bindings["generation_harness"]
        == preregistration["generation_harness"]["sha256"],
        "candidate_count": preregistration[
            "actual_candidate_generation_count_total"
        ]
        == 20,
        "no_broad_authorization": not any(
            preregistration["authorizations"][key]
            for key in (
                "run_disjoint_holdout",
                "change_production_default",
                "train_persona_adapter",
                "claim_persona_similarity",
                "request_human_blind_rating",
                "public_impersonation",
            )
        ),
    }
    return checks, bindings


def raw_pollution_count(rows):
    return sum(
        bool(set(row.get("raw_rejection_reasons") or []) & RAW_POLLUTION_REASONS)
        for row in rows
    )


def explicit_summary(artifact):
    summary = artifact["summary"]
    families = summary.get("rejection_families") or {}
    return {
        "generation_count": summary["generation_count"],
        "nonempty_raw_generation_count": summary["nonempty_raw_generation_count"],
        "strict_valid_generation_count": summary["strict_valid_generation_count"],
        "strict_valid_target_count": summary["strict_valid_target_count"],
        "strict_valid_neutral_count": summary["strict_valid_neutral_count"],
        "both_conditions_strict_valid_pair_count": summary[
            "both_conditions_strict_valid_pair_count"
        ],
        "distinct_normalized_output_count": summary[
            "distinct_normalized_output_count"
        ],
        "raw_language_or_script_pollution_count": raw_pollution_count(
            artifact["generations"]
        ),
        "final_required_semantics_missing_count": families.get(
            "required_semantics_missing", 0
        ),
        "final_polite_register_drift_count": families.get(
            "polite_register_drift", 0
        ),
        "warm_wall_latency_median_seconds": summary[
            "warm_wall_latency_median_seconds"
        ],
        "warm_wall_latency_p95_seconds": summary["warm_wall_latency_p95_seconds"],
        "model_blob_bytes": artifact["model"]["model_blob_bytes"],
        "ollama_reported_resident_size_bytes": artifact["resources"][
            "ollama_reported_resident_size_bytes"
        ],
        "maximum_ollama_process_rss_bytes": artifact["resources"][
            "maximum_ollama_process_rss_bytes"
        ],
    }


def candidate_gate(candidate, control, integrity):
    checks = {
        "integrity": bool(integrity),
        "nonempty_raw_generation_count": candidate[
            "nonempty_raw_generation_count"
        ]
        == 10,
        "strict_valid_minimum": candidate["strict_valid_generation_count"] >= 9,
        "strict_valid_delta": candidate["strict_valid_generation_count"]
        - control["strict_valid_generation_count"]
        >= 3,
        "raw_pollution_maximum": candidate[
            "raw_language_or_script_pollution_count"
        ]
        <= 2,
        "raw_pollution_reduction": control[
            "raw_language_or_script_pollution_count"
        ]
        - candidate["raw_language_or_script_pollution_count"]
        >= 2,
        "semantic_failure_maximum": candidate[
            "final_required_semantics_missing_count"
        ]
        <= 1,
        "semantic_failure_reduction": control[
            "final_required_semantics_missing_count"
        ]
        - candidate["final_required_semantics_missing_count"]
        >= 1,
        "polite_drift_not_worse": candidate[
            "final_polite_register_drift_count"
        ]
        <= 2,
        "warm_latency": candidate["warm_wall_latency_median_seconds"] <= 5.0,
        "model_blob_size": candidate["model_blob_bytes"] <= 8589934592,
    }
    return {"passed": all(checks.values()), "requirements": checks}


def select_candidate(gates, summaries):
    passed = [condition_id for condition_id in CANDIDATE_IDS if gates[condition_id]["passed"]]
    if not passed:
        return None, "reject_simple_carrier_swap_and_investigate_role_specialization"
    if len(passed) == 1:
        return passed[0], "authorize_disjoint_exact_current_contract_holdout_for_selected_carrier_only"

    four = summaries["qwen3_5_4b_q4_candidate"]
    nine = summaries["qwen3_5_9b_q4_candidate"]
    four_is_comparable = (
        four["strict_valid_generation_count"] >= nine["strict_valid_generation_count"] - 1
        and four["raw_language_or_script_pollution_count"]
        <= nine["raw_language_or_script_pollution_count"]
        and four["final_required_semantics_missing_count"]
        <= nine["final_required_semantics_missing_count"]
        and four["warm_wall_latency_median_seconds"]
        < nine["warm_wall_latency_median_seconds"]
    )
    if four_is_comparable:
        selected = "qwen3_5_4b_q4_candidate"
    else:
        selected = sorted(
            passed,
            key=lambda condition_id: (
                -summaries[condition_id]["strict_valid_generation_count"],
                summaries[condition_id]["raw_language_or_script_pollution_count"],
                summaries[condition_id]["final_required_semantics_missing_count"],
                summaries[condition_id]["warm_wall_latency_median_seconds"],
            ),
        )[0]
    return selected, "authorize_disjoint_exact_current_contract_holdout_for_selected_carrier_only"


def analyze(output_json=RESULT_JSON_PATH, output_md=RESULT_MD_PATH):
    preregistration = load_json(PREREGISTRATION_PATH)
    prereg_checks, prereg_bindings = validate_preregistration(preregistration)
    artifacts = {
        condition_id: load_json(generation.CONDITION_ARTIFACTS[condition_id])
        for condition_id in (CONTROL_ID, *CANDIDATE_IDS)
    }
    artifact_validity = {
        condition_id: generation.validate_condition_artifact(artifact, condition_id)
        for condition_id, artifact in artifacts.items()
    }
    summaries = {
        condition_id: explicit_summary(artifact)
        for condition_id, artifact in artifacts.items()
    }
    control = summaries[CONTROL_ID]
    control_matches_frozen = all(
        control[key] == expected
        for key, expected in {
            "strict_valid_generation_count": 6,
            "raw_language_or_script_pollution_count": 4,
            "final_required_semantics_missing_count": 2,
            "final_polite_register_drift_count": 2,
            "warm_wall_latency_median_seconds": 2.2623,
        }.items()
    )
    gates = {
        condition_id: candidate_gate(
            summaries[condition_id],
            control,
            all(prereg_checks.values())
            and artifact_validity[CONTROL_ID]
            and artifact_validity[condition_id],
        )
        for condition_id in CANDIDATE_IDS
    }
    selected, decision = select_candidate(gates, summaries)
    checks = {
        "preregistration_valid": all(prereg_checks.values()),
        "control_matches_frozen_calibration": control_matches_frozen,
        "all_condition_artifacts_valid": all(artifact_validity.values()),
        "candidate_generation_count_exact": sum(
            artifacts[condition_id]["actual_model_generation_call_count"]
            for condition_id in CANDIDATE_IDS
        )
        == preregistration["actual_candidate_generation_count_total"],
        "production_memory_unchanged": sum(
            artifact["production_memory_write_count"] for artifact in artifacts.values()
        )
        == 0,
        "no_formal_persona_score": sum(
            artifact["formal_persona_score_count"] for artifact in artifacts.values()
        )
        == 0,
    }
    valid = all(checks.values())
    report = {
        "schema": "uruha_rightbrain_carrier_model_screen_result_v2",
        "experiment_id": EXPERIMENT_ID,
        "status": "valid_screen" if valid else "invalid_screen",
        "decision": decision if valid else "invalidate_and_repair_experiment",
        "selected_candidate": selected if valid else None,
        "git_head": generation.git_head(),
        "inputs": {
            "preregistration": generation.binding(PREREGISTRATION_PATH),
            "control_calibration": generation.binding(CALIBRATION_PATH),
            "condition_artifacts": {
                condition_id: generation.binding(generation.CONDITION_ARTIFACTS[condition_id])
                for condition_id in artifacts
            },
            "generation_runner": generation.binding(
                ROOT / preregistration["generation_harness"]["path"]
            ),
        },
        "checks": checks,
        "preregistration_checks": prereg_checks,
        "preregistration_bindings": prereg_bindings,
        "artifact_validity": artifact_validity,
        "condition_summaries": summaries,
        "candidate_gates": gates,
        "authorizations": {
            "run_disjoint_exact_current_contract_holdout_for_selected_candidate": bool(
                valid and selected
            ),
            "change_production_default": False,
            "train_persona_adapter": False,
            "claim_persona_similarity": False,
            "request_human_blind_rating": False,
            "public_impersonation": False,
        },
        "evidence_boundary": preregistration["evidence_boundary"],
    }
    generation.atomic_write(output_json, report)
    Path(output_md).write_text(render_markdown(report), encoding="utf-8")
    return report


def render_markdown(report):
    labels = {
        CONTROL_ID: "Qwen2.5-7B 對照",
        "qwen3_5_4b_q4_candidate": "Qwen3.5-4B",
        "qwen3_5_9b_q4_candidate": "Qwen3.5-9B",
    }
    lines = [
        "# 右腦本機承載模型篩選 V2",
        "",
        f"**決策：`{report['decision']}`**",
        "",
        "| 條件 | 嚴格有效 | 原始污染 | 最終語意缺失 | 最終禮貌漂移 | 暖機中位延遲 |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for condition_id in (CONTROL_ID, *CANDIDATE_IDS):
        row = report["condition_summaries"][condition_id]
        lines.append(
            f"| {labels[condition_id]} | {row['strict_valid_generation_count']}/10 | "
            f"{row['raw_language_or_script_pollution_count']}/10 | "
            f"{row['final_required_semantics_missing_count']}/10 | "
            f"{row['final_polite_register_drift_count']}/10 | "
            f"{row['warm_wall_latency_median_seconds']:.2f}s |"
        )
    lines.extend(["", "## 預註冊門檻", ""])
    for condition_id in CANDIDATE_IDS:
        gate = report["candidate_gates"][condition_id]
        failed = [key for key, value in gate["requirements"].items() if not value]
        lines.append(f"- {labels[condition_id]}：{'通過' if gate['passed'] else '未通過'}")
        if failed:
            lines.append(f"- 未通過：`{', '.join(failed)}`")
    lines.extend(
        [
            "",
            "## 邊界",
            "",
            "V2 只比較現行右腦契約的本機承載能力。即使候選通過，也只可為該模型建立來源獨立 holdout；不代表人格更像、不代表可上線，也不授權訓練。",
            "",
        ]
    )
    return "\n".join(lines)


if __name__ == "__main__":
    report = analyze()
    print(
        json.dumps(
            {
                "experiment_id": report["experiment_id"],
                "status": report["status"],
                "decision": report["decision"],
                "selected_candidate": report["selected_candidate"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
