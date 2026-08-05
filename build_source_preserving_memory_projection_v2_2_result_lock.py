#!/usr/bin/env python3
"""Lock the V2.2 9B capacity-screen result and its failure localization."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PREREG = ROOT / "configs/source_preserving_memory_projection_v2_2_model_capacity_preregistration.json"
CONTRACT = ROOT / "configs/source_preserving_memory_projection_v2_2_model_capacity_evaluation_contract.json"
RAW = ROOT / "analysis/local_source_preserving_memory_projection_v2_2_9b_capacity/raw.jsonl"
METADATA = ROOT / "analysis/local_source_preserving_memory_projection_v2_2_9b_capacity/run_metadata.json"
REPORT = ROOT / "reports/source_preserving_memory_projection_v2_2_9b_capacity_development.json"
REPORT_MD = ROOT / "reports/source_preserving_memory_projection_v2_2_9b_capacity_development.md"
FAILURE_JSON = ROOT / "reports/source_preserving_memory_projection_v2_2_9b_capacity_failure_analysis.json"
FAILURE_MD = ROOT / "reports/source_preserving_memory_projection_v2_2_9b_capacity_failure_analysis.md"
RESULT_LOCK = ROOT / "configs/source_preserving_memory_projection_v2_2_model_capacity_result_lock.json"


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
    errors = Counter(
        error for row in invalid for error in row["evidence_validation"].get("errors", [])
    )
    metrics = report["metrics"]
    control_latency = load_json(
        ROOT / prereg["frozen_control"]["report_path"]
    )["metrics"]["mean_latency_seconds_by_representation"]
    return {
        "schema": "uruha_source_preserving_memory_projection_model_capacity_failure_v2_2",
        "experiment_id": prereg["experiment_id"],
        "decision": report["decision"],
        "hypothesis_result": {
            "capacity_improves_projected_semantic_extraction": True,
            "capacity_alone_satisfies_operational_contract": False,
            "frozen_4b_projected_target_support_count": metrics[
                "frozen_4b_projected_target_support_count"
            ],
            "intervention_9b_projected_target_support_count": metrics[
                "intervention_9b_projected_target_support_count"
            ],
            "support_gain_count": metrics["projected_9b_minus_frozen_4b_support_count"],
            "projected_false_support_count": metrics[
                "intervention_9b_projected_false_support_count"
            ],
        },
        "blocking_failure": {
            "classification": "single_long_record_is_split_into_nonexistent_source_indices",
            "invalid_row_count": len(invalid),
            "invalid_rows_all_complete_session": all(
                row["representation"] == "complete_session" for row in invalid
            ),
            "error_counts": dict(sorted(errors.items())),
            "rows": [
                {
                    "case_id": row["case_id"],
                    "condition": row["condition"],
                    "representation": row["representation"],
                    "visible_character_count": row["visible_character_count"],
                    "errors": row["evidence_validation"].get("errors", []),
                }
                for row in invalid
            ],
        },
        "cost": {
            "frozen_4b_mean_latency_seconds": control_latency,
            "intervention_9b_mean_latency_seconds": metrics[
                "mean_latency_seconds_by_representation"
            ],
            "complete_latency_multiplier": round(
                metrics["mean_latency_seconds_by_representation"]["complete_session"]
                / control_latency["complete_session"],
                6,
            ),
            "projection_latency_multiplier": round(
                metrics["mean_latency_seconds_by_representation"]["source_projection"]
                / control_latency["source_projection"],
                6,
            ),
        },
        "integrity": report["integrity"],
        "next_hypothesis_boundary": "Keep the 9B model, exact source texts, cases, inference parameters, and semantic decision rule fixed. Change only the one-record output carrier so a single memory record cannot emit nonexistent source indices.",
        "evidence_boundary": prereg["evidence_boundary"],
    }


def markdown(analysis):
    result = analysis["hypothesis_result"]
    blocking = analysis["blocking_failure"]
    cost = analysis["cost"]
    return "\n".join(
        [
            "# V2.2 9B Capacity Screen Result",
            "",
            "**Decision: semantic extraction improved, but the operational contract failed.**",
            "",
            f"- Projected target support: {result['frozen_4b_projected_target_support_count']}/8 -> {result['intervention_9b_projected_target_support_count']}/8",
            f"- Projected false support: {result['projected_false_support_count']}/8",
            f"- Invalid long-record outputs: {blocking['invalid_row_count']}/32",
            f"- Complete-session latency multiplier: {cost['complete_latency_multiplier']:.2f}x",
            f"- Projection latency multiplier: {cost['projection_latency_multiplier']:.2f}x",
            "",
            "The 9B model improved evidence recognition, but it treated turns inside one long memory as separate source records and emitted nonexistent indices. Model size alone is therefore insufficient.",
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
        "schema": "uruha_source_preserving_memory_projection_model_capacity_result_lock_v2_2",
        "experiment_id": prereg["experiment_id"],
        "status": "locked_failed_operational_contract",
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
            "runtime_change": False,
            "production_enablement": False,
            "fresh_holdout": False,
            "new_one_variable_carrier_experiment_after_preregistration": True,
        },
        "next_hypothesis_boundary": analysis["next_hypothesis_boundary"],
        "evidence_boundary": analysis["evidence_boundary"],
    }
    RESULT_LOCK.write_text(json.dumps(lock, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"result_lock": str(RESULT_LOCK), "decision": report["decision"]}, indent=2))


if __name__ == "__main__":
    main()
