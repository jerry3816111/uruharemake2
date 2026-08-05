#!/usr/bin/env python3
"""Lock the failed V2.1 development run without changing its frozen analysis."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONTRACT = ROOT / "configs/source_preserving_memory_projection_v2_1_evaluation_contract.json"
CASES = ROOT / "configs/source_preserving_memory_projection_v2_1_development_cases.json"
RAW = ROOT / "analysis/local_source_preserving_memory_projection_v2_1/raw.jsonl"
METADATA = ROOT / "analysis/local_source_preserving_memory_projection_v2_1/run_metadata.json"
REPORT = ROOT / "reports/source_preserving_memory_projection_v2_1_development.json"
REPORT_MD = ROOT / "reports/source_preserving_memory_projection_v2_1_development.md"
FAILURE_JSON = ROOT / "reports/source_preserving_memory_projection_v2_1_failure_analysis.json"
FAILURE_MD = ROOT / "reports/source_preserving_memory_projection_v2_1_failure_analysis.md"
RESULT_LOCK = ROOT / "configs/source_preserving_memory_projection_v2_1_result_lock.json"


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_jsonl(path):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line]


def binding(path):
    return {"path": str(path.relative_to(ROOT)), "sha256": sha256(path)}


def build_failure_analysis(rows, metadata, report, cases_payload):
    cases = {case["case_id"]: case for case in cases_payload["cases"]}
    projected_target_rows = [
        row
        for row in rows
        if row["condition"] == "remove_exact_hard_negative"
        and row["representation"] == "source_projection"
    ]
    projected_misses = [row for row in projected_target_rows if not row["target_supported"]]
    invalid_rows = [row for row in rows if not row["evidence_validation"].get("valid")]
    invalid_error_counts = Counter(
        error for row in invalid_rows for error in row["evidence_validation"].get("errors", [])
    )
    metrics = report["metrics"]
    return {
        "schema": "uruha_source_preserving_memory_projection_failure_analysis_v2_1",
        "experiment_id": report["experiment_id"],
        "decision": report["decision"],
        "phase_1_passed": metadata["phase_1_passed"],
        "executed_model_calls": len(rows),
        "phase_2_model_calls": sum(
            row["condition"] == "intact_target_and_hard_negative" for row in rows
        ),
        "primary_failure": {
            "classification": "local_model_false_negatives_on_exact_source_projection",
            "projected_target_support_count": metrics[
                "projected_target_only_answer_support_count"
            ],
            "required_count": 6,
            "miss_count": len(projected_misses),
            "misses": [
                {
                    "case_id": row["case_id"],
                    "official_question_id": row["official_question_id"],
                    "question": cases[row["case_id"]]["question"],
                    "official_answer": cases[row["case_id"]]["official_answer"],
                    "answer_preserved_in_projection": str(
                        cases[row["case_id"]]["official_answer"]
                    ).casefold()
                    in cases[row["case_id"]]["target"]["source_projection"]["text"].casefold(),
                }
                for row in projected_misses
            ],
        },
        "secondary_failure": {
            "classification": "long_context_tool_contract_index_drift",
            "invalid_row_count": len(invalid_rows),
            "invalid_error_counts": dict(sorted(invalid_error_counts.items())),
            "invalid_rows": [
                {
                    "case_id": row["case_id"],
                    "condition": row["condition"],
                    "representation": row["representation"],
                    "visible_character_count": row["visible_character_count"],
                    "errors": row["evidence_validation"].get("errors", []),
                }
                for row in invalid_rows
            ],
        },
        "positive_observation": {
            "complete_target_support_count": metrics[
                "complete_target_only_answer_support_count"
            ],
            "projected_target_support_count": metrics[
                "projected_target_only_answer_support_count"
            ],
            "paired_gain_count": metrics["paired_target_only_support_gain_count"],
            "paired_loss_count": metrics["paired_target_only_support_loss_count"],
            "mean_prompt_character_reduction_rate": metrics[
                "mean_prompt_character_reduction_rate"
            ],
            "mean_complete_latency_seconds": metrics[
                "mean_latency_seconds_by_representation"
            ]["complete_session"],
            "mean_projection_latency_seconds": metrics[
                "mean_latency_seconds_by_representation"
            ]["source_projection"],
        },
        "ruled_out_by_integrity_evidence": {
            "source_projection_corruption": report["integrity"]["official_source_hash_match"]
            and metrics["source_projection_exactness_rate"] == 1.0,
            "transport_failure": metrics["transport_error_count"] == 0,
            "row_loss_or_duplication": report["integrity"]["exact_expected_row_key_set"]
            and report["integrity"]["no_duplicate_row_keys"],
            "model_version_drift": report["integrity"]["model_digest_match"],
        },
        "evidence_boundary": "The exposed development run localizes an operational evidence-extraction failure. It does not measure fresh generalization, persona similarity, official LongMemEval accuracy, or human-memory equivalence.",
    }


def markdown(analysis):
    primary = analysis["primary_failure"]
    secondary = analysis["secondary_failure"]
    positive = analysis["positive_observation"]
    return "\n".join(
        [
            "# Source-preserving Memory Projection V2.1 Failure Analysis",
            "",
            "**Decision: phase 1 failed; no phase 2 and no runtime authorization.**",
            "",
            f"- Exact projections recognized: {primary['projected_target_support_count']}/8 (gate: >= {primary['required_count']}/8)",
            f"- Projection misses despite preserved answers: {primary['miss_count']}/8",
            f"- Invalid long-context tool outputs: {secondary['invalid_row_count']}/32",
            f"- Prompt characters reduced: {positive['mean_prompt_character_reduction_rate']:.1%}",
            f"- Mean latency: {positive['mean_complete_latency_seconds']:.2f}s -> {positive['mean_projection_latency_seconds']:.2f}s",
            "",
            "## Localized failures",
            "",
            *[
                f"- `{row['official_question_id']}`: {row['question']} (answer preserved: {row['answer_preserved_in_projection']})"
                for row in primary["misses"]
            ],
            "",
            "The source projection remained exact and transport/model identity checks passed. The frozen 4B evidence extractor, not source corruption, is the unresolved bottleneck.",
            "",
        ]
    )


def main():
    for output in (FAILURE_JSON, FAILURE_MD, RESULT_LOCK):
        if output.exists():
            raise SystemExit(f"Frozen result output already exists: {output}")
    rows = load_jsonl(RAW)
    metadata = load_json(METADATA)
    report = load_json(REPORT)
    cases_payload = load_json(CASES)
    if metadata["raw_sha256"] != sha256(RAW):
        raise SystemExit("Raw result hash mismatch")
    if report["decision"] != "development_reject_or_inconclusive":
        raise SystemExit("This lock builder only accepts the frozen failed decision")
    if not all(report["integrity"][key] for key in report["integrity"] if isinstance(report["integrity"][key], bool) and key != "phase_1_passed"):
        raise SystemExit("Run integrity did not pass")
    analysis = build_failure_analysis(rows, metadata, report, cases_payload)
    FAILURE_JSON.write_text(json.dumps(analysis, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    FAILURE_MD.write_text(markdown(analysis), encoding="utf-8")
    result_lock = {
        "schema": "uruha_source_preserving_memory_projection_result_lock_v2_1",
        "experiment_id": report["experiment_id"],
        "status": "locked_failed_phase_1",
        "decision": report["decision"],
        "executed_model_calls": len(rows),
        "phase_2_executed": False,
        "artifacts": {
            "lock_builder": binding(Path(__file__)),
            "evaluation_contract": binding(CONTRACT),
            "cases": binding(CASES),
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
            "new_experiment_after_new_preregistration": True,
        },
        "next_hypothesis_boundary": "A new preregistration may change exactly one evidence-extractor variable while preserving the source projection, cases, prompt, and scoring contract. This failed run remains the frozen control.",
        "evidence_boundary": analysis["evidence_boundary"],
    }
    RESULT_LOCK.write_text(
        json.dumps(result_lock, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"result_lock": str(RESULT_LOCK), "decision": report["decision"]}, indent=2))


if __name__ == "__main__":
    main()
