#!/usr/bin/env python3
"""Analyze the frozen source-provenance consolidation experiment."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = (
    ROOT
    / "configs"
    / "consolidation_source_provenance_v1_preregistration.json"
)
BASELINE_PATH = (
    ROOT / "reports" / "consolidation_source_provenance_v1_baseline.json"
)
TREATMENT_PATH = (
    ROOT / "reports" / "consolidation_source_provenance_v1_treatment.json"
)
DEFAULT_OUTPUT = (
    ROOT / "reports" / "consolidation_source_provenance_v1_analysis.md"
)


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_file_sha256(commit, path):
    content = subprocess.check_output(
        ["git", "show", f"{commit}:{path}"],
        cwd=ROOT,
    )
    return hashlib.sha256(content).hexdigest()


def _evaluate_gates(config, treatment):
    expected = config["success_gates"]
    observed = {
        "source_episode_count_before_exact": treatment[
            "source_episode_count_before"
        ],
        "source_episode_count_after_exact": treatment[
            "source_episode_count_after"
        ],
        "source_episode_retention_rate_exact": treatment[
            "source_episode_retention_rate"
        ],
        "source_episode_ids_unchanged": treatment[
            "source_episode_ids_unchanged"
        ],
        "source_episode_documents_unchanged": treatment[
            "source_episode_documents_unchanged"
        ],
        "source_consolidation_state_exact": (
            treatment["source_consolidation_states"][0]
            if len(treatment["source_consolidation_states"]) == 1
            else treatment["source_consolidation_states"]
        ),
        "source_consolidation_batch_count_exact": treatment[
            "source_consolidation_batch_count"
        ],
        "derived_record_count_after_first_exact": treatment[
            "derived_record_count_after_first"
        ],
        "derived_records_with_exact_source_ids_exact": treatment[
            "derived_records_with_exact_source_ids"
        ],
        "derived_records_with_source_digest_exact": treatment[
            "derived_records_with_source_digest"
        ],
        "derived_records_with_batch_id_exact": treatment[
            "derived_records_with_batch_id"
        ],
        "deleted_episode_count_exact": treatment[
            "deleted_episode_count"
        ],
        "preserved_episode_count_exact": treatment[
            "preserved_episode_count"
        ],
        "marked_consolidated_count_exact": treatment[
            "marked_consolidated_count"
        ],
        "stub_model_calls_after_first_exact": treatment[
            "stub_model_calls_after_first"
        ],
        "stub_model_calls_after_second_exact": treatment[
            "stub_model_calls_after_second"
        ],
        "second_mode_exact": treatment["second_mode"],
        "second_pass_created_no_duplicate_derived_records": treatment[
            "second_pass_created_no_duplicate_derived_records"
        ],
    }
    return {
        key: {
            "expected": expected[key],
            "observed": value,
            "passed": expected[key] == value,
        }
        for key, value in observed.items()
    }


def analyze():
    config = _load(CONFIG_PATH)
    baseline = _load(BASELINE_PATH)
    treatment = _load(TREATMENT_PATH)
    frozen = config["frozen_baseline"]
    current_commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        text=True,
    ).strip()

    artifact_checks = {
        "baseline_runtime_hash": (
            _git_file_sha256(frozen["commit"], frozen["runtime_path"])
            == frozen["runtime_sha256"]
        ),
        "measurement_hash": (
            _sha256(ROOT / frozen["measurement_path"])
            == frozen["measurement_sha256"]
        ),
        "baseline_report_hash": (
            _sha256(ROOT / frozen["report_path"])
            == frozen["report_sha256"]
        ),
        "treatment_runtime_commit": (
            treatment["runtime_commit"] == current_commit
        ),
        "treatment_runtime_hash": (
            treatment["runtime_sha256"]
            == _sha256(ROOT / frozen["runtime_path"])
        ),
        "temporary_database": bool(
            treatment["measurement_uses_temporary_chroma"]
        ),
        "no_external_model_calls": treatment["external_model_calls"] == 0,
    }
    gates = _evaluate_gates(config, treatment)
    data_gates_passed = all(
        artifact_checks.values()
    ) and all(item["passed"] for item in gates.values())
    return {
        "experiment_id": config["experiment_id"],
        "baseline_commit": frozen["commit"],
        "treatment_commit": treatment["runtime_commit"],
        "artifact_checks": artifact_checks,
        "gates": gates,
        "data_gates_passed": data_gates_passed,
        "baseline": baseline,
        "treatment": treatment,
    }


def _render_markdown(result):
    baseline = result["baseline"]
    treatment = result["treatment"]
    decision = "KEEP" if result["data_gates_passed"] else "DROP"
    lines = [
        "# 記憶鞏固來源保留實驗 V1",
        "",
        f"**資料門檻判定：{decision}**",
        "",
        "本實驗只改變原始 `turn_episode` 在鞏固後的處理與來源欄位。"
        "模型、Prompt、temperature、檢索排序與測試輸入保持不變。",
        "",
        "| 指標 | 修改前 | 修改後 |",
        "|---|---:|---:|",
        (
            "| 原始經歷保留 | "
            f"{baseline['source_episode_count_after']}/"
            f"{baseline['source_episode_count_before']} | "
            f"{treatment['source_episode_count_after']}/"
            f"{treatment['source_episode_count_before']} |"
        ),
        (
            "| 具有完整來源 ID 的衍生記憶 | "
            f"{baseline['derived_records_with_exact_source_ids']}/"
            f"{baseline['derived_record_count_after_first']} | "
            f"{treatment['derived_records_with_exact_source_ids']}/"
            f"{treatment['derived_record_count_after_first']} |"
        ),
        (
            "| 被實體刪除的原始經歷 | "
            f"{baseline['deleted_episode_count']} | "
            f"{treatment['deleted_episode_count']} |"
        ),
        (
            "| 第二次執行是否重複產生記憶 | "
            f"{'否' if baseline['second_pass_created_no_duplicate_derived_records'] else '是'} | "
            f"{'否' if treatment['second_pass_created_no_duplicate_derived_records'] else '是'} |"
        ),
        "",
        "## 門檢結果",
        "",
        "| 門檢 | 預期 | 實測 | 結果 |",
        "|---|---|---|---|",
    ]
    for name, item in result["gates"].items():
        lines.append(
            f"| `{name}` | `{item['expected']}` | "
            f"`{item['observed']}` | "
            f"{'通過' if item['passed'] else '失敗'} |"
        )
    lines.extend(
        [
            "",
            "## 證據邊界",
            "",
            "這次結果只證明來源保留、可追溯、無重複鞏固，以及失敗後可重試。"
            "它不證明摘要內容正確、檢索改善、對話改善、像人類，"
            "也不代表原始經歷應永久保存。",
            "",
        ]
    )
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    result = analyze()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(_render_markdown(result), encoding="utf-8")
    print(
        json.dumps(
            {
                "experiment_id": result["experiment_id"],
                "data_gates_passed": result["data_gates_passed"],
                "failed_artifact_checks": [
                    key
                    for key, passed in result["artifact_checks"].items()
                    if not passed
                ],
                "failed_gates": [
                    key
                    for key, item in result["gates"].items()
                    if not item["passed"]
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    raise SystemExit(0 if result["data_gates_passed"] else 1)


if __name__ == "__main__":
    main()
