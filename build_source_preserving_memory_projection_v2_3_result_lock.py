#!/usr/bin/env python3
"""Lock the V2.3 single-record carrier result without post-hoc normalization."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PREREG = ROOT / "configs/source_preserving_memory_projection_v2_3_single_record_carrier_preregistration.json"
CONTRACT = ROOT / "configs/source_preserving_memory_projection_v2_3_single_record_carrier_evaluation_contract.json"
RAW = ROOT / "analysis/local_source_preserving_memory_projection_v2_3_single_record_carrier/raw.jsonl"
METADATA = ROOT / "analysis/local_source_preserving_memory_projection_v2_3_single_record_carrier/run_metadata.json"
REPORT = ROOT / "reports/source_preserving_memory_projection_v2_3_single_record_carrier_development.json"
REPORT_MD = ROOT / "reports/source_preserving_memory_projection_v2_3_single_record_carrier_development.md"
FAILURE_JSON = ROOT / "reports/source_preserving_memory_projection_v2_3_single_record_carrier_failure_analysis.json"
FAILURE_MD = ROOT / "reports/source_preserving_memory_projection_v2_3_single_record_carrier_failure_analysis.md"
RESULT_LOCK = ROOT / "configs/source_preserving_memory_projection_v2_3_single_record_carrier_result_lock.json"


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_jsonl(path):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line]


def binding(path):
    return {"path": str(path.relative_to(ROOT)), "sha256": sha256(path)}


def build_failure_analysis(rows, prereg, report):
    invalid = [row for row in rows if not row["evidence_validation"].get("valid")]
    metrics = report["metrics"]
    return {
        "schema": "uruha_source_preserving_memory_projection_single_record_failure_v2_3",
        "experiment_id": prereg["experiment_id"],
        "decision": report["decision"],
        "carrier_effect": {
            "indexed_9b_complete_target_support_count": metrics[
                "frozen_9b_indexed_complete_target_support_count"
            ],
            "single_record_complete_target_support_count": metrics[
                "single_record_complete_target_support_count"
            ],
            "indexed_9b_projected_target_support_count": metrics[
                "frozen_9b_indexed_projected_target_support_count"
            ],
            "single_record_projected_target_support_count": metrics[
                "single_record_projected_target_support_count"
            ],
            "projected_false_support_count": metrics[
                "single_record_projected_false_support_count"
            ],
            "indexed_control_nonexistent_source_index_errors": 6,
            "single_record_nonexistent_source_index_errors": metrics[
                "nonexistent_source_index_error_count"
            ],
            "indexed_control_valid_rows": 26,
            "single_record_valid_rows": round(metrics["structured_contract_rate"] * len(rows)),
        },
        "remaining_failure": {
            "classification": "noncanonical_quoted_empty_placeholder",
            "invalid_row_count": len(invalid),
            "rows": [
                {
                    "case_id": row["case_id"],
                    "condition": row["condition"],
                    "representation": row["representation"],
                    "model_output": row["model_output"],
                    "errors": row["evidence_validation"].get("errors", []),
                }
                for row in invalid
            ],
        },
        "integrity": report["integrity"],
        "next_hypothesis_boundary": "A separately preregistered deterministic replay may normalize only quote-only empty placeholders to an empty string when supports_answer is false. The replay cannot establish fresh generation and may authorize only a disjoint external holdout.",
        "evidence_boundary": prereg["evidence_boundary"],
    }


def markdown(analysis):
    effect = analysis["carrier_effect"]
    failure = analysis["remaining_failure"]
    return "\n".join(
        [
            "# V2.3 Single-record Carrier Result",
            "",
            "**Decision: major carrier gain, but the frozen 100% contract gate failed.**",
            "",
            f"- Complete target support: {effect['indexed_9b_complete_target_support_count']}/8 -> {effect['single_record_complete_target_support_count']}/8",
            f"- Projected target support: {effect['indexed_9b_projected_target_support_count']}/8 -> {effect['single_record_projected_target_support_count']}/8",
            f"- Nonexistent source-index errors: {effect['indexed_control_nonexistent_source_index_errors']} -> {effect['single_record_nonexistent_source_index_errors']}",
            f"- Valid rows: {effect['indexed_control_valid_rows']}/32 -> {effect['single_record_valid_rows']}/32",
            f"- Remaining invalid rows: {failure['invalid_row_count']}/32",
            "",
            "The remaining row used a literal quoted-empty placeholder instead of an empty string. It remains invalid under the frozen contract; no post-hoc pass is claimed.",
            "",
        ]
    )


def main():
    for output in (FAILURE_JSON, FAILURE_MD, RESULT_LOCK):
        if output.exists():
            raise SystemExit(f"Frozen result output already exists: {output}")
    rows = load_jsonl(RAW)
    prereg = load_json(PREREG)
    metadata = load_json(METADATA)
    report = load_json(REPORT)
    if metadata["raw_sha256"] != sha256(RAW):
        raise SystemExit("Raw result hash mismatch")
    if report["decision"] != "development_reject_or_inconclusive":
        raise SystemExit("Unexpected frozen decision")
    if not all(report["integrity"].values()):
        raise SystemExit("Run integrity failed")
    analysis = build_failure_analysis(rows, prereg, report)
    FAILURE_JSON.write_text(json.dumps(analysis, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    FAILURE_MD.write_text(markdown(analysis), encoding="utf-8")
    lock = {
        "schema": "uruha_source_preserving_memory_projection_single_record_result_lock_v2_3",
        "experiment_id": prereg["experiment_id"],
        "status": "locked_failed_strict_contract",
        "decision": report["decision"],
        "executed_model_calls": len(rows),
        "artifacts": {
            "lock_builder": binding(Path(__file__)),
            "preregistration": binding(PREREG),
            "evaluation_contract": binding(CONTRACT),
            "raw": binding(RAW),
            "metadata": binding(METADATA),
            "report_json": binding(REPORT),
            "report_markdown": binding(REPORT_MD),
            "failure_analysis_json": binding(FAILURE_JSON),
            "failure_analysis_markdown": binding(FAILURE_MD),
        },
        "authorization": {
            "rerun_same_contract": False,
            "change_threshold_post_hoc": False,
            "treat_quoted_empty_as_empty_post_hoc": False,
            "runtime_change": False,
            "production_enablement": False,
            "fresh_holdout": False,
            "new_normalization_replay_after_preregistration": True,
        },
        "next_hypothesis_boundary": analysis["next_hypothesis_boundary"],
        "evidence_boundary": analysis["evidence_boundary"],
    }
    RESULT_LOCK.write_text(json.dumps(lock, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"result_lock": str(RESULT_LOCK), "decision": report["decision"]}, indent=2))


if __name__ == "__main__":
    main()
