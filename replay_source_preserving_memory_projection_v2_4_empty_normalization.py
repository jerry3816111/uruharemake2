#!/usr/bin/env python3
"""Replay frozen V2.3 outputs through the preregistered empty normalization."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

from answer_bearing_memory_single_record import parse, validate
from answer_bearing_memory_single_record_normalization import normalize
from answer_bearing_memory_span import supported_candidates
from run_source_preserving_memory_projection_v2_1_development import (
    ROOT,
    condition_candidates,
    file_sha256,
    load_json,
)


CONTRACT = ROOT / "configs/source_preserving_memory_projection_v2_4_empty_normalization_replay_contract.json"
DEFAULT_REPLAY = ROOT / "analysis/local_source_preserving_memory_projection_v2_4_empty_normalization/replay.jsonl"
DEFAULT_REPORT = ROOT / "reports/source_preserving_memory_projection_v2_4_empty_normalization_replay.json"
DEFAULT_MARKDOWN = ROOT / "reports/source_preserving_memory_projection_v2_4_empty_normalization_replay.md"
DEFAULT_LOCK = ROOT / "configs/source_preserving_memory_projection_v2_4_empty_normalization_replay_result_lock.json"


def canonical_sha256(value):
    payload = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def load_jsonl(path):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line]


def binding(path):
    return {"path": str(path.relative_to(ROOT)), "sha256": file_sha256(path)}


def load_frozen_configuration():
    contract = load_json(CONTRACT)
    prereg = load_json(ROOT / contract["artifacts"]["preregistration"]["path"])
    for artifact in contract["artifacts"].values():
        if file_sha256(ROOT / artifact["path"]) != artifact["sha256"]:
            raise ValueError(f"frozen artifact hash mismatch: {artifact['path']}")
    base = load_json(ROOT / "configs/source_preserving_memory_projection_v2_development_preregistration.json")
    conditions = {row["id"]: row for row in base["matched_conditions"]}
    cases_payload = load_json(ROOT / contract["artifacts"]["cases"]["path"])
    return contract, prereg, conditions, cases_payload


def replay_row(row, case, condition, candidate):
    parsed = parse(row["model_output"])
    normalized, normalization = normalize(parsed)
    replay_validation = validate(normalized, candidate)
    supported = supported_candidates(replay_validation, [candidate])
    supported_trace_ids = sorted(item["trace_id"] for item in supported)
    supported_roles = sorted(item["role"] for item in supported)
    original_semantics = {
        "target_supported": row["target_supported"],
        "hard_negative_supported": row["hard_negative_supported"],
        "supported_trace_ids": sorted(row["supported_trace_ids"]),
    }
    replay_semantics = {
        "target_supported": "target" in supported_roles,
        "hard_negative_supported": "hard_negative" in supported_roles,
        "supported_trace_ids": supported_trace_ids,
    }
    return {
        "schema": "uruha_source_preserving_memory_projection_empty_normalization_replay_row_v2_4",
        "case_id": row["case_id"],
        "official_question_id": row["official_question_id"],
        "condition": row["condition"],
        "representation": row["representation"],
        "source_raw_row_sha256": canonical_sha256(row),
        "model_output_sha256_before": canonical_sha256(row["model_output"]),
        "model_output_sha256_after": canonical_sha256(row["model_output"]),
        "normalization": normalization,
        "original_validation": row["evidence_validation"],
        "replay_validation": replay_validation,
        "original_semantics": original_semantics,
        "replay_semantics": replay_semantics,
        "semantic_support_changed": original_semantics != replay_semantics,
        "previously_valid_regressed": bool(row["evidence_validation"].get("valid"))
        and not replay_validation.get("valid"),
        "production_memory_write_count": 0,
        "physical_vrm_action_count": 0,
        "model_call_count": 0,
    }


def replay_all(raw_rows, cases_payload, conditions):
    cases = {case["case_id"]: case for case in cases_payload["cases"]}
    output = []
    for row in raw_rows:
        case = cases[row["case_id"]]
        condition = conditions[row["condition"]]
        candidates = condition_candidates(case, condition, row["representation"])
        if len(candidates) != 1:
            raise ValueError("V2.4 replay requires exactly one visible candidate")
        output.append(replay_row(row, case, condition, candidates[0]))
    return output


def summarize(rows, prereg, integrity):
    keys = [(row["case_id"], row["condition"], row["representation"]) for row in rows]
    normalized_count = sum(row["normalization"]["applied"] for row in rows)
    valid_count = sum(row["replay_validation"].get("valid", False) for row in rows)
    grounded_count = sum(
        row["replay_validation"].get("all_spans_grounded", False) for row in rows
    )
    complete_targets = [
        row
        for row in rows
        if row["condition"] == "remove_exact_hard_negative"
        and row["representation"] == "complete_session"
    ]
    projected_targets = [
        row
        for row in rows
        if row["condition"] == "remove_exact_hard_negative"
        and row["representation"] == "source_projection"
    ]
    projected_removed = [
        row
        for row in rows
        if row["condition"] == "remove_exact_target"
        and row["representation"] == "source_projection"
    ]
    metrics = {
        "row_count": len(rows),
        "unique_row_key_count": len(set(keys)),
        "model_call_count": sum(row["model_call_count"] for row in rows),
        "model_output_sha_unchanged_count": sum(
            row["model_output_sha256_before"] == row["model_output_sha256_after"]
            for row in rows
        ),
        "normalized_row_count": normalized_count,
        "previously_valid_regression_count": sum(
            row["previously_valid_regressed"] for row in rows
        ),
        "semantic_support_change_count": sum(row["semantic_support_changed"] for row in rows),
        "replay_valid_row_count": valid_count,
        "replay_grounded_row_count": grounded_count,
        "complete_target_support_count": sum(
            row["replay_semantics"]["target_supported"] for row in complete_targets
        ),
        "projected_target_support_count": sum(
            row["replay_semantics"]["target_supported"] for row in projected_targets
        ),
        "projected_false_support_count": sum(
            row["replay_semantics"]["hard_negative_supported"] for row in projected_removed
        ),
        "production_memory_write_count": sum(
            row["production_memory_write_count"] for row in rows
        ),
        "physical_vrm_action_count": sum(row["physical_vrm_action_count"] for row in rows),
    }
    success = prereg["success_gates"]
    gates = {
        **{f"integrity_{key}": value for key, value in integrity.items()},
        "all_32_rows_present_once": len(rows) == 32 and len(set(keys)) == 32,
        "model_call_count_equals_zero": metrics["model_call_count"]
        == success["model_call_count_equals"],
        "model_output_sha_unchanged_count_equals_32": metrics[
            "model_output_sha_unchanged_count"
        ]
        == success["model_output_sha_unchanged_count_equals"],
        "normalized_row_count_equals_one": normalized_count
        == success["normalized_row_count_equals"],
        "previously_valid_regression_count_equals_zero": metrics[
            "previously_valid_regression_count"
        ]
        == success["previously_valid_regression_count_equals"],
        "semantic_support_change_count_equals_zero": metrics[
            "semantic_support_change_count"
        ]
        == success["semantic_support_change_count_equals"],
        "replay_valid_row_count_equals_32": valid_count
        == success["replay_valid_row_count_equals"],
        "replay_grounded_row_count_equals_32": grounded_count
        == success["replay_grounded_row_count_equals"],
        "complete_target_support_count_equals_six": metrics[
            "complete_target_support_count"
        ]
        == success["complete_target_support_count_equals"],
        "projected_target_support_count_equals_seven": metrics[
            "projected_target_support_count"
        ]
        == success["projected_target_support_count_equals"],
        "projected_false_support_count_equals_zero": metrics[
            "projected_false_support_count"
        ]
        == success["projected_false_support_count_equals"],
        "production_memory_write_count_equals_zero": metrics[
            "production_memory_write_count"
        ]
        == success["production_memory_write_count_equals"],
        "physical_vrm_action_count_equals_zero": metrics["physical_vrm_action_count"]
        == success["physical_vrm_action_count_equals"],
    }
    decision = (
        "replay_pass_authorizes_external_fresh_holdout_preregistration_only"
        if all(gates.values())
        else "replay_reject_or_inconclusive"
    )
    return {
        "schema": "uruha_source_preserving_memory_projection_empty_normalization_replay_report_v2_4",
        "experiment_id": prereg["experiment_id"],
        "decision": decision,
        "evidence_type": prereg["evidence_type"],
        "integrity": integrity,
        "metrics": metrics,
        "gates": gates,
        "authorization": {
            "external_fresh_holdout_preregistration": decision
            == "replay_pass_authorizes_external_fresh_holdout_preregistration_only",
            "runtime_change": False,
            "production_enablement": False,
            "training_use": False,
            "fresh_generation_claim": False,
        },
        "evidence_boundary": prereg["evidence_boundary"],
    }


def markdown(report):
    metrics = report["metrics"]
    failed = [name for name, passed in report["gates"].items() if not passed]
    return "\n".join(
        [
            "# V2.4 Quote-only Empty Normalization Replay",
            "",
            f"**Decision: {report['decision']}**",
            "",
            f"- Model calls: {metrics['model_call_count']}",
            f"- Model outputs unchanged: {metrics['model_output_sha_unchanged_count']}/32",
            f"- Normalized rows: {metrics['normalized_row_count']}/32",
            f"- Valid grounded rows: {metrics['replay_valid_row_count']}/32",
            f"- Semantic support changes: {metrics['semantic_support_change_count']}",
            "",
            "## Failed gates",
            "",
            *([f"- `{name}`" for name in failed] or ["- None"]),
            "",
            "This is a replay of known outputs. A pass can authorize only a disjoint external fresh-generation holdout.",
            "",
        ]
    )


def write_outputs(rows, report, contract, prereg, replay_path, report_path, md_path, lock_path):
    replay_path.parent.mkdir(parents=True, exist_ok=True)
    replay_path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(markdown(report), encoding="utf-8")
    lock = {
        "schema": "uruha_source_preserving_memory_projection_empty_normalization_replay_result_lock_v2_4",
        "experiment_id": prereg["experiment_id"],
        "decision": report["decision"],
        "evidence_type": prereg["evidence_type"],
        "artifacts": {
            "evaluation_contract": binding(CONTRACT),
            "preregistration": binding(ROOT / contract["artifacts"]["preregistration"]["path"]),
            "frozen_v2_3_raw": binding(ROOT / contract["artifacts"]["frozen_v2_3_raw"]["path"]),
            "replay_rows": binding(replay_path),
            "report_json": binding(report_path),
            "report_markdown": binding(md_path),
        },
        "authorization": report["authorization"],
        "evidence_boundary": report["evidence_boundary"],
    }
    lock_path.write_text(json.dumps(lock, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    outputs = (DEFAULT_REPLAY, DEFAULT_REPORT, DEFAULT_MARKDOWN, DEFAULT_LOCK)
    if any(path.exists() for path in outputs):
        raise SystemExit("Frozen V2.4 replay output already exists; refusing to overwrite")
    contract, prereg, conditions, cases_payload = load_frozen_configuration()
    raw_path = ROOT / contract["artifacts"]["frozen_v2_3_raw"]["path"]
    raw_rows = load_jsonl(raw_path)
    replay_rows = replay_all(raw_rows, cases_payload, conditions)
    actual_raw_hash = file_sha256(raw_path)
    integrity = {
        "frozen_raw_hash_match": actual_raw_hash == prereg["frozen_source"]["raw_sha256"],
        "frozen_result_lock_hash_match": file_sha256(
            ROOT / prereg["frozen_source"]["result_lock_path"]
        )
        == prereg["frozen_source"]["result_lock_sha256"],
        "input_row_count_match": len(raw_rows) == prereg["frozen_source"]["row_count"],
    }
    report = summarize(replay_rows, prereg, integrity)
    write_outputs(
        replay_rows,
        report,
        contract,
        prereg,
        DEFAULT_REPLAY,
        DEFAULT_REPORT,
        DEFAULT_MARKDOWN,
        DEFAULT_LOCK,
    )
    print(json.dumps({"decision": report["decision"], "metrics": report["metrics"]}, indent=2))


if __name__ == "__main__":
    main()
