#!/usr/bin/env python3
"""Run the frozen semantic recall-support holdout exactly once."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import uruha_memory_runtime as umr


ROOT = Path(__file__).resolve().parent
CONTRACT = ROOT / "configs/semantic_memory_recall_support_v1_holdout_evaluation_contract.json"
CASES = ROOT / "configs/semantic_memory_recall_support_v1_holdout_cases.json"
OUTPUT_DIR = ROOT / "analysis/local_semantic_memory_recall_support_v1_holdout"
RAW = OUTPUT_DIR / "raw.jsonl"
METADATA = OUTPUT_DIR / "run_metadata.json"
REPORT_JSON = ROOT / "reports/semantic_memory_recall_support_v1_holdout.json"
REPORT_MD = ROOT / "reports/semantic_memory_recall_support_v1_holdout.md"


def file_sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def rate(rows, predicate):
    return sum(bool(predicate(row)) for row in rows) / len(rows) if rows else 0.0


def memory_item(record):
    return {
        "source": "episode",
        "collection_name": "holdout",
        "memory_id": record["trace_id"].rsplit(":", 1)[-1],
        "trace_id": record["trace_id"],
        "text": record["text"],
        "score": record["score"],
    }


def wrapped_query(case, contract):
    template = contract["query_wrapper"][case["language"]]
    return template.format(question=case["question"])


def condition_records(case, condition):
    if condition == "c0_intact_target_and_hard_negative":
        return [case["target"], case["hard_negative"]]
    if condition == "t1_remove_exact_target":
        return [case["hard_negative"]]
    if condition == "t2_replace_exact_target":
        return [case["replacement"], case["hard_negative"]]
    if condition == "n1_remove_exact_hard_negative":
        return [case["target"]]
    raise ValueError(f"Unknown condition: {condition}")


def expected_trace(case, condition):
    if condition in {"c0_intact_target_and_hard_negative", "n1_remove_exact_hard_negative"}:
        return case["target"]["trace_id"]
    if condition == "t2_replace_exact_target":
        return case["replacement"]["trace_id"]
    return None


def safe_outcome(decision, expected, condition):
    selected = bool(decision.get("selected"))
    trace_id = decision.get("trace_id")
    if condition == "t1_remove_exact_target":
        return not selected
    if selected:
        return trace_id == expected
    return condition in {
        "c0_intact_target_and_hard_negative",
        "t2_replace_exact_target",
    } and decision.get("status") == "ambiguous"


def evaluate_case(case, contract):
    query = wrapped_query(case, contract)
    rows = []
    selector = contract["selector"]
    for condition in contract["conditions_in_order"]:
        records = condition_records(case, condition)
        decision = umr.select_high_confidence_recall_item(
            query,
            {"working_memory_items": [memory_item(record) for record in records]},
            minimum_top_score=selector["minimum_top_score"],
            minimum_margin=selector["minimum_supported_runner_up_margin"],
            minimum_shared_focus_unit_count=selector["minimum_shared_focus_unit_count"],
            trust=selector["trust"],
        )
        expected = expected_trace(case, condition)
        selected_trace = decision.get("trace_id") if decision.get("selected") else None
        rows.append(
            {
                "schema": "uruha_semantic_memory_recall_support_holdout_raw_v1",
                "case_id": case["case_id"],
                "official_question_id": case["official_question_id"],
                "language": case["language"],
                "condition": condition,
                "expected_trace_id": expected,
                "selected": bool(decision.get("selected")),
                "selected_trace_id": selected_trace,
                "status": decision.get("status"),
                "safe_outcome": safe_outcome(decision, expected, condition),
                "wrong_trace_selected": bool(selected_trace and selected_trace != expected),
                "support_evidence": {
                    key: decision.get(key)
                    for key in (
                        "support_schema",
                        "candidate_count",
                        "supported_candidate_count",
                        "query_focus_unit_count",
                        "shared_focus_units",
                        "shared_focus_unit_count",
                        "query_focus_coverage",
                        "top_score",
                        "runner_up_score",
                        "margin",
                    )
                },
                "transport_error_count": 0,
                "production_memory_write_count": 0,
                "physical_vrm_action_count": 0,
            }
        )
    return rows


def boundary_probes():
    def decide(query, text):
        return umr.select_high_confidence_recall_item(
            query,
            {"working_memory_items": [memory_item({"trace_id": "probe:item", "text": text, "score": 0.95})]},
        )

    probes = {
        "sensitive": decide(
            "前に話したパスワード、覚えてる？",
            "パスワードはsample-secretだと言った。",
        ),
        "non_recall": decide(
            "今日は観葉植物に水をあげた。",
            "観葉植物の呼び名はアオバ。",
        ),
        "broad_presence": decide(
            "Do you remember me?",
            "The user once bought a blue hat.",
        ),
    }
    return {
        name: {"status": result.get("status"), "selected": bool(result.get("selected"))}
        for name, result in probes.items()
    }


def build_report(rows, cases_payload, prereg, contract, metadata):
    gates_spec = prereg["holdout_gates"]
    by_condition = {
        condition: [row for row in rows if row["condition"] == condition]
        for condition in contract["conditions_in_order"]
    }
    probes = metadata["boundary_probes"]
    wrong = [row for row in rows if row["wrong_trace_selected"]]
    removed_selected = [
        row for row in by_condition["t1_remove_exact_target"] if row["selected"]
    ]
    gates = {
        "row_count_exact": len(rows) == gates_spec["row_count_exact"],
        "question_count_exact": cases_payload["case_count"]
        == gates_spec["question_count_exact"],
        "no_wrong_trace_selection": len(wrong)
        <= gates_spec["wrong_trace_selection_count_max"],
        "target_removal_never_selects": len(removed_selected)
        <= gates_spec["target_removed_selection_count_max"],
        "intact_safe": rate(
            by_condition["c0_intact_target_and_hard_negative"],
            lambda row: row["safe_outcome"],
        )
        >= gates_spec["intact_safe_outcome_rate_min"],
        "replacement_safe": rate(
            by_condition["t2_replace_exact_target"],
            lambda row: row["safe_outcome"],
        )
        >= gates_spec["replacement_safe_outcome_rate_min"],
        "irrelevant_removed_selects_target": rate(
            by_condition["n1_remove_exact_hard_negative"],
            lambda row: row["selected"]
            and row["selected_trace_id"] == row["expected_trace_id"],
        )
        >= gates_spec["irrelevant_removed_target_selection_rate_min"],
        "no_sensitive_fast_path": int(bool(probes["sensitive"]["selected"]))
        <= gates_spec["fast_path_sensitive_exposure_count_max"],
        "no_non_recall_fast_path": int(bool(probes["non_recall"]["selected"]))
        <= gates_spec["fast_path_non_recall_activation_count_max"],
        "no_broad_presence_fast_path": int(bool(probes["broad_presence"]["selected"]))
        <= gates_spec["fast_path_broad_presence_activation_count_max"],
        "no_transport_errors": not any(row["transport_error_count"] for row in rows),
        "no_production_writes": not any(
            row["production_memory_write_count"] for row in rows
        ),
        "no_vrm_actions": not any(row["physical_vrm_action_count"] for row in rows),
    }
    condition_summary = {
        condition: {
            "safe_outcome_rate": rate(condition_rows, lambda row: row["safe_outcome"]),
            "selection_rate": rate(condition_rows, lambda row: row["selected"]),
            "ambiguous_rate": rate(
                condition_rows, lambda row: row["status"] == "ambiguous"
            ),
            "unsupported_rate": rate(
                condition_rows, lambda row: row["status"] == "unsupported"
            ),
        }
        for condition, condition_rows in by_condition.items()
    }
    language_summary = {}
    for language in sorted({row["language"] for row in rows}):
        language_rows = [row for row in rows if row["language"] == language]
        language_summary[language] = {
            "row_count": len(language_rows),
            "safe_outcome_rate": rate(language_rows, lambda row: row["safe_outcome"]),
            "wrong_trace_selection_count": sum(
                row["wrong_trace_selected"] for row in language_rows
            ),
        }
    return {
        "schema": "uruha_semantic_memory_recall_support_holdout_result_v1",
        "decision": "holdout_pass_production_still_disabled"
        if all(gates.values())
        else "holdout_reject_or_inconclusive",
        "evidence_scope": contract["scoring_exclusions"],
        "row_count": len(rows),
        "question_count": cases_payload["case_count"],
        "wrong_trace_selection_count": len(wrong),
        "target_removed_selection_count": len(removed_selected),
        "conditions": condition_summary,
        "languages": language_summary,
        "gates": gates,
        "run_metadata": metadata,
        "authorization": {
            "production_default_enablement": False,
            "benchmark_score_claim": False,
            "persona_similarity_claim": False,
            "human_memory_equivalence_claim": False,
        },
    }


def markdown(report):
    lines = [
        "# Semantic memory recall support V1 holdout result",
        "",
        f"- Decision: `{report['decision']}`",
        f"- Questions / decisions: {report['question_count']} / {report['row_count']}",
        f"- Wrong trace selections: {report['wrong_trace_selection_count']}",
        f"- Target-removed selections: {report['target_removed_selection_count']}",
        "",
        "| Condition | Safe | Selected | Ambiguous | Unsupported |",
        "|---|---:|---:|---:|---:|",
    ]
    for condition, summary in report["conditions"].items():
        lines.append(
            f"| {condition} | {summary['safe_outcome_rate']:.1%} | "
            f"{summary['selection_rate']:.1%} | {summary['ambiguous_rate']:.1%} | "
            f"{summary['unsupported_rate']:.1%} |"
        )
    lines.extend(["", "## Gates", ""])
    lines.extend(
        f"- {name}: {'PASS' if passed else 'FAIL'}"
        for name, passed in report["gates"].items()
    )
    lines.extend(
        [
            "",
            "## Evidence boundary",
            "",
            "This is a selector safety holdout, not official LongMemEval answer accuracy. Production remains disabled.",
        ]
    )
    return "\n".join(lines) + "\n"


def main():
    if RAW.exists() or REPORT_JSON.exists():
        raise SystemExit("Holdout result already exists; refusing a second observation")
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    cases_payload = json.loads(CASES.read_text(encoding="utf-8"))
    prereg_path = ROOT / contract["inputs"]["preregistration_path"]
    prereg = json.loads(prereg_path.read_text(encoding="utf-8"))
    for key in ("cases", "preregistration", "development_lock", "runtime"):
        path = ROOT / contract["inputs"][f"{key}_path"]
        if file_sha256(path) != contract["inputs"][f"{key}_sha256"]:
            raise SystemExit(f"Frozen {key} hash drift")

    rows = []
    for case in cases_payload["cases"]:
        rows.extend(evaluate_case(case, contract))
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    RAW.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )
    metadata = {
        "schema": "uruha_semantic_memory_recall_support_holdout_run_v1",
        "commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "contract_sha256": file_sha256(CONTRACT),
        "cases_sha256": file_sha256(CASES),
        "runtime_sha256": file_sha256(ROOT / contract["inputs"]["runtime_path"]),
        "boundary_probes": boundary_probes(),
        "production_database_opened": False,
        "production_memory_writes": 0,
        "physical_vrm_actions": 0,
    }
    METADATA.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n")
    report = build_report(rows, cases_payload, prereg, contract, metadata)
    REPORT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    REPORT_MD.write_text(markdown(report), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
