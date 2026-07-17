#!/usr/bin/env python3
"""Analyze the frozen consolidation support-attribution V1 pilot."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from consolidation_support_attribution_v1_core import (
    analyze_support_attribution,
)


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = (
    ROOT
    / "configs"
    / "consolidation_support_attribution_v1_development_preregistration.json"
)
LOCK_PATH = (
    ROOT
    / "configs"
    / "consolidation_support_attribution_v1_harness_lock.json"
)
RAW_PATH = (
    ROOT
    / "reports"
    / "consolidation_support_attribution_v1_development_raw.json"
)
DEFAULT_JSON = (
    ROOT
    / "reports"
    / "consolidation_support_attribution_v1_development_analysis.json"
)
DEFAULT_MARKDOWN = (
    ROOT
    / "reports"
    / "consolidation_support_attribution_v1_development_analysis.md"
)


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def analyze():
    config = _load(CONFIG_PATH)
    lock = _load(LOCK_PATH)
    raw = _load(RAW_PATH)
    dataset_path = ROOT / config["dataset"]["path"]
    dataset = _load(dataset_path)
    artifact_checks = {
        "preregistration_hash": (
            _sha256(CONFIG_PATH)
            == lock["frozen_artifacts"]["preregistration_sha256"]
            == raw["preregistration_sha256"]
        ),
        "harness_lock_hash": (
            _sha256(LOCK_PATH) == raw["harness_lock_sha256"]
        ),
        "dataset_hash": (
            _sha256(dataset_path)
            == lock["frozen_artifacts"]["dataset_sha256"]
            == raw["dataset_sha256"]
        ),
        "model_digest": (
            raw["model_snapshot"]["digest"]
            == config["model"]["digest"]
        ),
        "completed": bool(raw.get("completed_at")),
        "model_calls": (
            raw["model_calls"]
            == config["run_invariants"]["model_call_count_exact"]
        ),
        "transport_attempts": (
            raw["transport_attempts_made"]
            == config["run_invariants"][
                "transport_attempt_count_exact"
            ]
        ),
        "no_gold_to_model": not raw["gold_fields_passed_to_model"],
        "no_runtime_write": not raw["runtime_memory_write_performed"],
        "no_inflight_request": raw.get("inflight") is None,
    }
    result = analyze_support_attribution(
        dataset["cases"],
        raw["control_rows"],
        raw["candidate_rows"],
        config["success_gates"],
    )
    artifact_integrity_valid = all(artifact_checks.values())
    if not artifact_integrity_valid:
        decision = "invalid_experiment"
    elif result["all_success_gates_pass"]:
        decision = (
            "keep_support_attribution_candidate_for_fresh_"
            "runtime_integration_pilot"
        )
    else:
        decision = "drop_support_attribution_candidate"
    return {
        "schema": "uruha_consolidation_support_attribution_analysis_v1",
        "experiment_id": config["experiment_id"],
        "decision": decision,
        "artifact_integrity_valid": artifact_integrity_valid,
        "artifact_checks": artifact_checks,
        "result": result,
        "evidence_limits": config["evidence_limits"],
    }


def _render_markdown(analysis):
    result = analysis["result"]
    control = result["control"]
    candidate = result["candidate"]
    failed = [
        key
        for key, row in result["gates"].items()
        if not row["passed"]
    ]
    lines = [
        "# 濃縮記憶支持來源歸因 V1",
        "",
        f"**決策：`{analysis['decision']}`**",
        "",
        "| 指標 | 整批來源控制組 | 4B 支持來源歸因 |",
        "|---|---:|---:|",
        (
            "| 完全選對來源集合 | "
            f"{control['exact_set_match_count']}/18 | "
            f"{candidate['exact_set_match_count']}/18 |"
        ),
        (
            "| 證據 precision | "
            f"{control['evidence_precision']:.2%} | "
            f"{candidate['evidence_precision']:.2%} |"
        ),
        (
            "| 證據 recall | "
            f"{control['evidence_recall']:.2%} | "
            f"{candidate['evidence_recall']:.2%} |"
        ),
        (
            "| 無依據記憶正確拒絕 | "
            f"{control['unsupported_empty_count']}/6 | "
            f"{candidate['unsupported_empty_count']}/6 |"
        ),
        (
            "| 錯誤來源數 | "
            f"{control['false_source_count']} | "
            f"{candidate['false_source_count']} |"
        ),
        (
            "| 中位延遲 | 0（不呼叫模型） | "
            f"{candidate['median_wall_seconds']:.3f} 秒 |"
        ),
        "",
        f"- 新增完全正確：{result['newly_exact_count']}",
        f"- 退步：{result['regression_count']}",
        f"- 未通過門檻：{', '.join(failed) if failed else '無'}",
        "",
        "本結果只評估 18 組 Codex 標註的受控開發案例。"
        "它不直接證明真實聊天、長期回憶、人類相似度或生物學等價。",
        "",
    ]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON)
    parser.add_argument(
        "--markdown-output",
        type=Path,
        default=DEFAULT_MARKDOWN,
    )
    args = parser.parse_args()
    analysis = analyze()
    args.json_output.write_text(
        json.dumps(analysis, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    args.markdown_output.write_text(
        _render_markdown(analysis),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "experiment_id": analysis["experiment_id"],
                "decision": analysis["decision"],
                "artifact_integrity_valid": analysis[
                    "artifact_integrity_valid"
                ],
                "all_success_gates_pass": analysis["result"][
                    "all_success_gates_pass"
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    raise SystemExit(
        0 if analysis["artifact_integrity_valid"] else 1
    )


if __name__ == "__main__":
    main()
