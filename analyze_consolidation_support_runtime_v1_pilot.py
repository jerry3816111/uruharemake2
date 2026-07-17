#!/usr/bin/env python3
"""Analyze the frozen support-attribution runtime integration pilot."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
from pathlib import Path

from consolidation_support_attribution_v1_core import (
    build_coarse_control_rows,
    summarize_condition,
)


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = (
    ROOT
    / "configs"
    / "consolidation_support_runtime_v1_preregistration.json"
)
LOCK_PATH = (
    ROOT
    / "configs"
    / "consolidation_support_runtime_v1_harness_lock.json"
)
RAW_PATH = (
    ROOT
    / "reports"
    / "consolidation_support_runtime_v1_pilot_raw.json"
)
DEFAULT_JSON_OUTPUT = (
    ROOT
    / "reports"
    / "consolidation_support_runtime_v1_pilot_analysis.json"
)
DEFAULT_MARKDOWN_OUTPUT = (
    ROOT
    / "reports"
    / "consolidation_support_runtime_v1_pilot_analysis.md"
)
MEMORY_KINDS = ("episodic", "wisdom", "procedural")


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _p95(values):
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, math.ceil(0.95 * len(ordered)) - 1)
    return round(ordered[index], 4)


def _flat_cases(dataset):
    rows = []
    for case in dataset["cases"]:
        for memory_kind in MEMORY_KINDS:
            gold = case["gold_support_event_indices"][memory_kind]
            rows.append(
                {
                    "id": f"{case['id']}::{memory_kind}",
                    "case_id": case["id"],
                    "language": case["language"],
                    "memory_kind": memory_kind,
                    "support_mode": (
                        "supported" if gold else "unsupported"
                    ),
                    "gold_support_event_indices": gold,
                }
            )
    return rows


def _candidate_score_rows(raw):
    return [
        {
            "id": f"{call['case_id']}::{call['memory_kind']}",
            "parse_success": call["parse_success"],
            "index_contract_success": call[
                "index_contract_success"
            ],
            "support_event_indices": call["support_event_indices"],
            "wall_seconds": call["wall_seconds"],
            "transport_error": call["transport_error"],
        }
        for call in raw["candidate_model_calls"]
    ]


def _metadata_matches_support(
    metadata,
    expected_ids,
    expected_indices,
):
    try:
        observed_ids = json.loads(metadata["support_episode_ids"])
        observed_indices = json.loads(metadata["support_event_indices"])
    except (KeyError, TypeError, json.JSONDecodeError):
        return False
    encoded_ids = json.dumps(
        sorted(expected_ids),
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return (
        observed_ids == sorted(expected_ids)
        and metadata.get("support_episode_count") == len(expected_ids)
        and metadata.get("support_episode_ids_sha256")
        == hashlib.sha256(encoded_ids.encode("utf-8")).hexdigest()
        and observed_indices == sorted(expected_indices)
        and metadata.get("support_attribution_status") == "verified"
        and bool(
            metadata.get("support_attribution_contract_version")
        )
        and bool(metadata.get("support_attribution_model_digest"))
    )


def _runtime_summary(dataset, rows, condition):
    dataset_by_id = {case["id"]: case for case in dataset["cases"]}
    stored_record_count = 0
    exact_support_metadata_count = 0
    unsupported_written_count = 0
    successful_batch_count = 0
    rejected_unsupported_episodic_batch_count = 0
    marked_consolidated_count = 0
    pending_count = 0
    partial_batch_count = 0
    batch_seconds = []
    scored_cases = []

    for row in rows:
        case = dataset_by_id[row["case_id"]]
        source_ids = row["source_episode_ids_in_event_order"]
        records = {
            record["memory_kind"]: record
            for record in row["derived_records_after"]
        }
        stored_record_count += len(records)
        expected_outcome = case["expected_candidate_outcome"]
        expected_stored = set(
            expected_outcome["stored_memory_kinds"]
        )
        if condition == "coarse_runtime_control":
            expected_stored = set(MEMORY_KINDS)
        if set(records) != expected_stored:
            partial_batch_count += 1

        for memory_kind, record in records.items():
            gold_indices = case["gold_support_event_indices"][
                memory_kind
            ]
            if not gold_indices:
                unsupported_written_count += 1
            expected_ids = [
                source_ids[index - 1] for index in gold_indices
            ]
            if _metadata_matches_support(
                record["metadata"],
                expected_ids,
                gold_indices,
            ):
                exact_support_metadata_count += 1

        mode = row["runtime_result"]["mode"]
        successful_batch_count += (
            mode == "support_attributed_consolidation"
            if condition == "support_attributed_runtime_candidate"
            else mode == "three_speed_consolidation"
        )
        rejected_unsupported_episodic_batch_count += (
            mode == "consolidation_unsupported_episodic"
        )
        states = [
            record["metadata"].get(
                "consolidation_state",
                "pending",
            )
            for record in row["source_records_after"]
        ]
        marked_consolidated_count += states.count("consolidated")
        pending_count += states.count("pending")
        batch_seconds.append(float(row["case_wall_seconds"]))
        scored_cases.append(
            {
                "case_id": row["case_id"],
                "mode": mode,
                "stored_memory_kinds": sorted(records),
                "expected_stored_memory_kinds": sorted(
                    expected_stored
                ),
                "source_states": sorted(set(states)),
                "case_wall_seconds": row["case_wall_seconds"],
            }
        )

    return {
        "case_count": len(rows),
        "stored_record_count": stored_record_count,
        "stored_records_with_exact_support_metadata": (
            exact_support_metadata_count
        ),
        "unsupported_derived_records_written": (
            unsupported_written_count
        ),
        "successful_batch_count": successful_batch_count,
        "rejected_unsupported_episodic_batch_count": (
            rejected_unsupported_episodic_batch_count
        ),
        "source_episodes_marked_consolidated": (
            marked_consolidated_count
        ),
        "source_episodes_left_pending": pending_count,
        "partial_batch_count": partial_batch_count,
        "median_batch_seconds": round(
            statistics.median(batch_seconds),
            4,
        ),
        "batch_p95_seconds": _p95(batch_seconds),
        "scored_cases": scored_cases,
    }


def _artifact_checks(config, lock, raw):
    checks = {
        "experiment_id": (
            raw["experiment_id"] == config["experiment_id"]
        ),
        "runner_branch_main": raw["runner_branch"] == "main",
        "ollama_version": (
            raw["ollama_version"]
            == config["local_runtime"]["ollama_version"]
        ),
        "model_tag": (
            raw["model_snapshot"]["ollama_tag"]
            == config["model"]["ollama_tag"]
        ),
        "model_digest": (
            raw["model_snapshot"]["digest"]
            == config["model"]["digest"]
        ),
        "preflight_passed": bool(raw["preflight"]["passed"]),
        "gold_isolation": not raw[
            "gold_or_expected_outcome_passed_to_runtime"
        ],
        "production_database_writes_zero": (
            raw["production_database_writes"] == 0
        ),
        "no_inflight_request": (
            raw["inflight_request_at_completion"] is None
        ),
        "harness_lock_hash": (
            raw["harness_lock_sha256"] == _sha256(LOCK_PATH)
        ),
    }
    for name, artifact in lock["frozen_artifacts"].items():
        checks[f"artifact_{name}"] = (
            _sha256(ROOT / artifact["path"])
            == artifact["sha256"]
            == raw["frozen_artifact_hashes"][name]
        )
    database_rows = raw["control"] + raw["candidate"]
    checks["temporary_database_per_case"] = all(
        row["database_isolation"]["temporary_database"]
        and not row["database_isolation"][
            "production_database_opened"
        ]
        and row["database_isolation"]["temporary_database_path"]
        != row["database_isolation"]["production_database_path"]
        for row in database_rows
    )
    model_visible = json.dumps(
        [
            call["model_visible_request"]
            for call in raw["candidate_model_calls"]
        ],
        ensure_ascii=False,
    )
    checks["model_request_has_no_gold_fields"] = all(
        forbidden not in model_visible
        for forbidden in (
            "gold_support_event_indices",
            "expected_candidate_outcome",
            "case_id",
        )
    )
    return checks


def _evaluate_gates(config, raw, candidate_score, candidate_runtime):
    expected = config["success_gates"]
    observations = {
        "artifact_integrity_valid": (
            True,
            "exact",
        ),
        "candidate_exact_support_set_count_min": (
            candidate_score["exact_set_match_count"],
            "minimum",
        ),
        "candidate_evidence_precision_min": (
            candidate_score["evidence_precision"],
            "minimum",
        ),
        "candidate_evidence_recall_min": (
            candidate_score["evidence_recall"],
            "minimum",
        ),
        "candidate_unsupported_empty_count_exact": (
            candidate_score["unsupported_empty_count"],
            "exact",
        ),
        "candidate_false_support_source_count_max": (
            candidate_score["false_source_count"],
            "maximum",
        ),
        "candidate_missed_support_source_count_max": (
            candidate_score["missed_source_count"],
            "maximum",
        ),
        "candidate_parse_success_count_exact": (
            candidate_score["parse_success_count"],
            "exact",
        ),
        "candidate_index_contract_success_count_exact": (
            candidate_score["index_contract_success_count"],
            "exact",
        ),
        "candidate_transport_error_count_exact": (
            candidate_score["transport_error_count"],
            "exact",
        ),
        "candidate_median_attribution_seconds_max": (
            candidate_score["median_wall_seconds"],
            "maximum",
        ),
        "candidate_warm_p95_attribution_seconds_max": (
            candidate_score["warm_p95_wall_seconds"],
            "maximum",
        ),
        "candidate_batch_p95_seconds_max": (
            candidate_runtime["batch_p95_seconds"],
            "maximum",
        ),
        "candidate_stored_record_count_exact": (
            candidate_runtime["stored_record_count"],
            "exact",
        ),
        "candidate_stored_records_with_exact_support_metadata_exact": (
            candidate_runtime[
                "stored_records_with_exact_support_metadata"
            ],
            "exact",
        ),
        "candidate_unsupported_derived_records_written_exact": (
            candidate_runtime[
                "unsupported_derived_records_written"
            ],
            "exact",
        ),
        "candidate_successful_batch_count_exact": (
            candidate_runtime["successful_batch_count"],
            "exact",
        ),
        "candidate_rejected_unsupported_episodic_batch_count_exact": (
            candidate_runtime[
                "rejected_unsupported_episodic_batch_count"
            ],
            "exact",
        ),
        "candidate_source_episodes_marked_consolidated_exact": (
            candidate_runtime[
                "source_episodes_marked_consolidated"
            ],
            "exact",
        ),
        "candidate_source_episodes_left_pending_exact": (
            candidate_runtime["source_episodes_left_pending"],
            "exact",
        ),
        "candidate_partial_batch_count_exact": (
            candidate_runtime["partial_batch_count"],
            "exact",
        ),
        "candidate_production_database_writes_exact": (
            raw["production_database_writes"],
            "exact",
        ),
        "injected_attribution_failure_is_atomic": (
            raw["preflight"]["passed"],
            "exact",
        ),
        "injected_each_collection_write_failure_is_atomic": (
            raw["preflight"]["passed"],
            "exact",
        ),
        "injected_source_transition_failure_is_atomic": (
            raw["preflight"]["passed"],
            "exact",
        ),
        "retry_after_injected_failure_creates_one_batch_only": (
            raw["preflight"]["passed"],
            "exact",
        ),
        "existing_memory_and_reflection_regression_tests_pass": (
            raw["preflight"]["passed"],
            "exact",
        ),
    }
    gates = {}
    for key, (observed, comparison) in observations.items():
        required = expected[key]
        if comparison == "minimum":
            passed = observed >= required
        elif comparison == "maximum":
            passed = observed <= required
        else:
            passed = observed == required
        gates[key] = {
            "required": required,
            "observed": observed,
            "comparison": comparison,
            "passed": passed,
        }
    return gates


def analyze():
    config = _load(CONFIG_PATH)
    lock = _load(LOCK_PATH)
    dataset = _load(ROOT / config["dataset"]["path"])
    raw = _load(RAW_PATH)
    flat_cases = _flat_cases(dataset)
    control_score = summarize_condition(
        flat_cases,
        build_coarse_control_rows(flat_cases),
    )
    candidate_score = summarize_condition(
        flat_cases,
        _candidate_score_rows(raw),
    )
    control_runtime = _runtime_summary(
        dataset,
        raw["control"],
        "coarse_runtime_control",
    )
    candidate_runtime = _runtime_summary(
        dataset,
        raw["candidate"],
        "support_attributed_runtime_candidate",
    )
    artifact_checks = _artifact_checks(config, lock, raw)
    artifact_integrity_valid = all(artifact_checks.values())
    gates = _evaluate_gates(
        config,
        raw,
        candidate_score,
        candidate_runtime,
    )
    gates["artifact_integrity_valid"]["observed"] = (
        artifact_integrity_valid
    )
    gates["artifact_integrity_valid"]["passed"] = (
        artifact_integrity_valid
    )
    all_success_gates_pass = all(
        row["passed"] for row in gates.values()
    )
    if not artifact_integrity_valid:
        decision = "INVALID"
    elif all_success_gates_pass:
        decision = (
            "keep_disabled_support_attributed_runtime_candidate_for_"
            "fresh_retrieval_impact_pilot"
        )
    else:
        decision = "drop_support_attributed_runtime_candidate"
    return {
        "schema": "uruha_consolidation_support_runtime_analysis_v1",
        "experiment_id": config["experiment_id"],
        "decision": decision,
        "artifact_integrity_valid": artifact_integrity_valid,
        "artifact_checks": artifact_checks,
        "all_success_gates_pass": all_success_gates_pass,
        "failed_success_gates": [
            key for key, row in gates.items() if not row["passed"]
        ],
        "gates": gates,
        "support_scoring": {
            "control": control_score,
            "candidate": candidate_score,
        },
        "runtime_scoring": {
            "control": control_runtime,
            "candidate": candidate_runtime,
        },
        "formal_run": {
            "runner_commit": raw["runner_commit"],
            "started_at": raw["started_at"],
            "completed_at": raw["completed_at"],
            "model_calls": raw["candidate_model_call_count"],
            "transport_attempts": raw[
                "candidate_transport_attempt_count"
            ],
        },
        "evidence_limits": config["evidence_limits"],
    }


def _render_markdown(result):
    support = result["support_scoring"]
    runtime = result["runtime_scoring"]
    return "\n".join(
        [
            "# 記憶來源歸因 Runtime Pilot V1",
            "",
            f"**決策：`{result['decision']}`**",
            "",
            "| 指標 | 現行整批來源 | 逐條來源歸因 |",
            "|---|---:|---:|",
            (
                "| 完全選對來源集合 | "
                f"{support['control']['exact_set_match_count']}/18 | "
                f"{support['candidate']['exact_set_match_count']}/18 |"
            ),
            (
                "| 證據 precision | "
                f"{support['control']['evidence_precision']:.2%} | "
                f"{support['candidate']['evidence_precision']:.2%} |"
            ),
            (
                "| 證據 recall | "
                f"{support['control']['evidence_recall']:.2%} | "
                f"{support['candidate']['evidence_recall']:.2%} |"
            ),
            (
                "| 寫入衍生記憶 | "
                f"{runtime['control']['stored_record_count']} | "
                f"{runtime['candidate']['stored_record_count']} |"
            ),
            (
                "| 寫入無依據記憶 | "
                f"{runtime['control']['unsupported_derived_records_written']} | "
                f"{runtime['candidate']['unsupported_derived_records_written']} |"
            ),
            (
                "| 部分批次 | "
                f"{runtime['control']['partial_batch_count']} | "
                f"{runtime['candidate']['partial_batch_count']} |"
            ),
            "",
            (
                f"- 所有門檻："
                f"{'通過' if result['all_success_gates_pass'] else '未通過'}"
            ),
            (
                f"- Artifact 完整性："
                f"{'有效' if result['artifact_integrity_valid'] else '無效'}"
            ),
            "",
            "本結果只測試全新臨時 Chroma 的寫入整合。"
            "它不證明生成內容、檢索、長期回憶、對話或人類相似度改善。",
            "",
        ]
    )


def _write_json(path, payload):
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--json-output",
        type=Path,
        default=DEFAULT_JSON_OUTPUT,
    )
    parser.add_argument(
        "--markdown-output",
        type=Path,
        default=DEFAULT_MARKDOWN_OUTPUT,
    )
    args = parser.parse_args()
    result = analyze()
    _write_json(args.json_output, result)
    args.markdown_output.write_text(
        _render_markdown(result),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "experiment_id": result["experiment_id"],
                "decision": result["decision"],
                "artifact_integrity_valid": result[
                    "artifact_integrity_valid"
                ],
                "all_success_gates_pass": result[
                    "all_success_gates_pass"
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    raise SystemExit(
        0
        if result["artifact_integrity_valid"]
        else 2
    )


if __name__ == "__main__":
    main()
