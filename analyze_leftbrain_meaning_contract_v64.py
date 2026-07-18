#!/usr/bin/env python3
"""Analyze the frozen V64 raw outputs after collection."""

from __future__ import annotations

import argparse
import json
import math
import random
import re
import statistics
from collections import defaultdict
from pathlib import Path

from run_leftbrain_meaning_contract_v64 import C0, T1, CONDITIONS


ROOT = Path(__file__).resolve().parent
PREREG_PATH = ROOT / "configs/leftbrain_meaning_contract_v64_preregistration.json"
DATASET_PATH = ROOT / "datasets/leftbrain_meaning_contract_v64.json"
LOCK_PATH = ROOT / "configs/leftbrain_meaning_contract_v64_harness_lock.json"
RAW_PATH = ROOT / "reports/leftbrain_meaning_contract_v64_raw.json"
ANALYSIS_PATH = ROOT / "reports/leftbrain_meaning_contract_v64_analysis.json"
MARKDOWN_PATH = ROOT / "reports/leftbrain_meaning_contract_v64_analysis.md"


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _normalize(value):
    return re.sub(r"[^0-9a-zぁ-んァ-ヶ一-龠]", "", str(value or "").lower())


def _contains_any(value, options):
    haystack = _normalize(value)
    return any(_normalize(option) in haystack for option in options if _normalize(option))


def parse_json_output(text):
    raw = str(text or "").strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.IGNORECASE)
        raw = re.sub(r"\s*```$", "", raw)
    try:
        payload = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _common_schema_valid(payload):
    return bool(
        isinstance(payload, dict)
        and isinstance(payload.get("intent"), str)
        and isinstance(payload.get("user_summary"), str)
        and isinstance(payload.get("response_goal"), str)
        and isinstance(payload.get("core_message_jp"), str)
        and isinstance(payload.get("uncertainty"), (int, float))
        and isinstance(payload.get("forbidden_moves"), list)
    )


def _frame_schema_valid(payload):
    if not isinstance(payload, dict):
        return False
    frame = payload.get("semantic_frame")
    contract = payload.get("response_contract")
    if not isinstance(frame, dict) or not isinstance(contract, dict):
        return False
    actors = frame.get("actors")
    propositions = frame.get("propositions")
    memory_state = frame.get("memory_state")
    if not isinstance(actors, list) or not actors:
        return False
    if not isinstance(propositions, list) or not propositions:
        return False
    if not isinstance(memory_state, list):
        return False
    proposition_keys = {"subject", "predicate", "object", "polarity", "temporality", "source", "certainty"}
    if not all(isinstance(row, dict) and proposition_keys.issubset(row) for row in propositions):
        return False
    return bool(
        isinstance(contract.get("dialogue_act"), str)
        and isinstance(contract.get("required_moves"), list)
        and isinstance(contract.get("forbidden_moves"), list)
    )


def _commitment_text(payload):
    if not isinstance(payload, dict):
        return ""
    return " ".join(
        [
            str(payload.get("response_goal") or ""),
            str(payload.get("core_message_jp") or ""),
        ]
    )


def _score_relation(payload, expected):
    propositions = ((payload or {}).get("semantic_frame") or {}).get("propositions") or []
    for proposition in propositions:
        encoded = json.dumps(proposition, ensure_ascii=False, sort_keys=True)
        if (
            _contains_any(encoded, expected["subject_any"])
            and _contains_any(encoded, expected["predicate_any"])
            and _contains_any(encoded, expected["object_any"])
        ):
            return True
    return False


def _memory_record_accuracy(payload, case):
    expected = case.get("memory_fixture") or []
    if not expected:
        return None
    rows = ((payload or {}).get("semantic_frame") or {}).get("memory_state") or []
    by_id = {str(row.get("memory_id")): row for row in rows if isinstance(row, dict)}
    hits = 0
    for item in expected:
        row = by_id.get(item["id"], {})
        encoded = json.dumps(row, ensure_ascii=False).lower()
        if item["status"] == "current":
            valid = any(token in encoded for token in ("current", "active", "selected", "現在", "採用"))
        else:
            valid = any(token in encoded for token in ("superseded", "background", "inactive", "旧", "過去", "更新済"))
        hits += int(valid)
    return (hits, len(expected))


def score_row(row, case):
    payload = parse_json_output(row.get("output_text"))
    text = _commitment_text(payload)
    required = [
        {
            "id": item["id"],
            "hit": _contains_any(text, item["accepted_surfaces"]),
        }
        for item in case["required_commitments"]
    ]
    forbidden = [
        {
            "id": item["id"],
            "hit": _contains_any(text, item["accepted_surfaces"]),
        }
        for item in case["forbidden_commitments"]
    ]
    relations = [
        {"id": item["id"], "hit": _score_relation(payload, item)}
        for item in case["required_frame_relations"]
    ]
    memory_score = _memory_record_accuracy(payload, case)
    return {
        "parsed": payload is not None,
        "common_schema_valid": _common_schema_valid(payload),
        "frame_schema_valid": _frame_schema_valid(payload),
        "required": required,
        "required_hits": sum(item["hit"] for item in required),
        "required_count": len(required),
        "complete_case": bool(required) and all(item["hit"] for item in required),
        "forbidden": forbidden,
        "forbidden_hits": sum(item["hit"] for item in forbidden),
        "forbidden_count": len(forbidden),
        "relations": relations,
        "relation_hits": sum(item["hit"] for item in relations),
        "relation_count": len(relations),
        "memory_hits": memory_score[0] if memory_score else 0,
        "memory_count": memory_score[1] if memory_score else 0,
    }


def _percentile(values, quantile):
    if not values:
        return None
    ordered = sorted(values)
    index = (len(ordered) - 1) * quantile
    lower = math.floor(index)
    upper = math.ceil(index)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (index - lower)


def _condition_metrics(rows):
    scores = [row["score"] for row in rows]
    required_hits = sum(score["required_hits"] for score in scores)
    required_count = sum(score["required_count"] for score in scores)
    forbidden_hits = sum(score["forbidden_hits"] for score in scores)
    forbidden_count = sum(score["forbidden_count"] for score in scores)
    relation_hits = sum(score["relation_hits"] for score in scores)
    relation_count = sum(score["relation_count"] for score in scores)
    memory_hits = sum(score["memory_hits"] for score in scores)
    memory_count = sum(score["memory_count"] for score in scores)
    latencies = [row["generation_metrics"]["wall_seconds"] for row in rows]
    rss_values = [row.get("ollama_rss_bytes") for row in rows if row.get("ollama_rss_bytes") is not None]
    count = len(rows)
    return {
        "row_count": count,
        "json_parse_rate": sum(score["parsed"] for score in scores) / count,
        "common_schema_valid_rate": sum(score["common_schema_valid"] for score in scores) / count,
        "frame_schema_valid_rate": sum(score["frame_schema_valid"] for score in scores) / count,
        "response_commitment_recall": required_hits / required_count,
        "required_hits": required_hits,
        "required_count": required_count,
        "complete_case_rate": sum(score["complete_case"] for score in scores) / count,
        "complete_case_count": sum(score["complete_case"] for score in scores),
        "forbidden_commitment_violation_rate": forbidden_hits / forbidden_count if forbidden_count else 0.0,
        "forbidden_hits": forbidden_hits,
        "forbidden_count": forbidden_count,
        "required_frame_relation_recall": relation_hits / relation_count if relation_count else 0.0,
        "relation_hits": relation_hits,
        "relation_count": relation_count,
        "memory_current_over_superseded_accuracy": memory_hits / memory_count if memory_count else 0.0,
        "memory_hits": memory_hits,
        "memory_count": memory_count,
        "latency_median_seconds": statistics.median(latencies),
        "latency_p95_seconds": _percentile(latencies, 0.95),
        "peak_ollama_rss_bytes": max(rss_values) if rss_values else None,
    }


def _bootstrap_delta(case_recalls, samples):
    rng = random.Random(20260764)
    case_ids = sorted(case_recalls)
    deltas = []
    for _ in range(samples):
        chosen = [rng.choice(case_ids) for _ in case_ids]
        deltas.append(sum(case_recalls[case_id][T1] - case_recalls[case_id][C0] for case_id in chosen) / len(chosen))
    ordered = sorted(deltas)
    return {
        "samples": samples,
        "lower_95": ordered[int(samples * 0.025)],
        "upper_95": ordered[min(samples - 1, int(samples * 0.975))],
    }


def analyze(raw, prereg, dataset, lock):
    cases = {case["id"]: case for case in dataset["cases"]}
    rows_by_condition = defaultdict(list)
    rows_by_case = defaultdict(dict)
    scored_rows = []
    for row in raw["rows"]:
        scored = dict(row)
        scored["score"] = score_row(row, cases[row["case_id"]])
        scored_rows.append(scored)
        rows_by_condition[row["condition"]].append(scored)
        rows_by_case[row["case_id"]][row["condition"]] = scored

    metrics = {condition: _condition_metrics(rows_by_condition[condition]) for condition in CONDITIONS}
    delta = metrics[T1]["response_commitment_recall"] - metrics[C0]["response_commitment_recall"]
    case_recalls = {
        case_id: {
            condition: rows_by_case[case_id][condition]["score"]["required_hits"] / rows_by_case[case_id][condition]["score"]["required_count"]
            for condition in CONDITIONS
        }
        for case_id in cases
    }
    gates = prereg["automatic_advance_gates"]
    checks = {
        "model_call_count_exact": raw["model_call_count"] == gates["model_call_count_exact"],
        "transport_error_count_exact": raw["transport_error_count"] == gates["transport_error_count_exact"],
        "t1_json_parse_rate": metrics[T1]["json_parse_rate"] >= gates["t1_json_parse_rate_at_least"],
        "t1_common_schema_valid_rate": metrics[T1]["common_schema_valid_rate"] >= gates["t1_common_schema_valid_rate_at_least"],
        "t1_frame_schema_valid_rate": metrics[T1]["frame_schema_valid_rate"] >= gates["t1_frame_schema_valid_rate_at_least"],
        "t1_response_commitment_recall": metrics[T1]["response_commitment_recall"] >= gates["t1_response_commitment_recall_at_least"],
        "t1_recall_delta_vs_c0": delta >= gates["t1_response_commitment_recall_delta_vs_c0_at_least"],
        "t1_complete_case_rate": metrics[T1]["complete_case_rate"] >= gates["t1_complete_case_rate_at_least"],
        "t1_forbidden_violation_rate": metrics[T1]["forbidden_commitment_violation_rate"] <= gates["t1_forbidden_commitment_violation_rate_at_most"],
        "t1_frame_relation_recall": metrics[T1]["required_frame_relation_recall"] >= gates["t1_required_frame_relation_recall_at_least"],
        "t1_memory_state_accuracy": metrics[T1]["memory_current_over_superseded_accuracy"] == gates["t1_memory_current_over_superseded_accuracy_exact"],
        "t1_latency_median": metrics[T1]["latency_median_seconds"] <= gates["t1_latency_median_seconds_at_most"],
        "t1_latency_p95": metrics[T1]["latency_p95_seconds"] <= gates["t1_latency_p95_seconds_at_most"],
        "t1_peak_rss": metrics[T1]["peak_ollama_rss_bytes"] is not None and metrics[T1]["peak_ollama_rss_bytes"] <= gates["t1_peak_ollama_rss_bytes_at_most"],
    }
    passed = all(checks.values())
    per_case = []
    for case_id, condition_rows in rows_by_case.items():
        case = cases[case_id]
        per_case.append(
            {
                "case_id": case_id,
                "scenario_family": case["scenario_family"],
                "conditions": {
                    condition: {
                        "parsed_output": parse_json_output(condition_rows[condition]["output_text"]),
                        "score": condition_rows[condition]["score"],
                    }
                    for condition in CONDITIONS
                },
            }
        )
    return {
        "schema": "uruha_leftbrain_meaning_contract_analysis_v64",
        "experiment_id": prereg["experiment_id"],
        "decision": "advance_only_to_fresh_rightbrain_realization_pilot" if passed else "freeze_negative_result_and_stop_structured_meaning_contract_hypothesis",
        "automatic_gates": {"passed": passed, "checks": checks},
        "metrics": metrics,
        "paired_effect": {
            "response_commitment_recall_delta": delta,
            "bootstrap_95_ci": _bootstrap_delta(case_recalls, lock["statistics"]["bootstrap_samples"]),
        },
        "per_case": per_case,
        "evidence_boundary": prereg["causal_boundary"],
        "production_runtime_changed": False,
    }


def _markdown(report):
    c0 = report["metrics"][C0]
    t1 = report["metrics"][T1]
    delta = report["paired_effect"]["response_commitment_recall_delta"]
    failed = [name for name, passed in report["automatic_gates"]["checks"].items() if not passed]
    lines = [
        "# V64 左腦意義契約實驗結果",
        "",
        f"**決策：** `{report['decision']}`",
        "",
        "| 指標 | 精簡計畫 | 結構化意義契約 |",
        "|---|---:|---:|",
        f"| 必要意思命中 | {c0['required_hits']}/{c0['required_count']} ({c0['response_commitment_recall']:.1%}) | {t1['required_hits']}/{t1['required_count']} ({t1['response_commitment_recall']:.1%}) |",
        f"| 整題完整 | {c0['complete_case_count']}/14 ({c0['complete_case_rate']:.1%}) | {t1['complete_case_count']}/14 ({t1['complete_case_rate']:.1%}) |",
        f"| 禁止意思違反 | {c0['forbidden_hits']}/{c0['forbidden_count']} | {t1['forbidden_hits']}/{t1['forbidden_count']} |",
        f"| JSON 解析 | {c0['json_parse_rate']:.1%} | {t1['json_parse_rate']:.1%} |",
        f"| 角色關係命中 | 不適用 | {t1['relation_hits']}/{t1['relation_count']} ({t1['required_frame_relation_recall']:.1%}) |",
        f"| 記憶新舊判定 | 不適用 | {t1['memory_hits']}/{t1['memory_count']} ({t1['memory_current_over_superseded_accuracy']:.1%}) |",
        "",
        f"必要意思差異：{delta:+.1%}；95% bootstrap CI [{report['paired_effect']['bootstrap_95_ci']['lower_95']:+.1%}, {report['paired_effect']['bootstrap_95_ci']['upper_95']:+.1%}]。",
        "",
        "## 未通過門檻" if failed else "## 通過門檻",
        "",
        *(f"- `{name}`" for name in failed),
        "",
        "這份結果只評估左腦內容規劃 schema，不代表右腦輸出、完整聊天或廣義人類相似度。",
    ]
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", type=Path, default=RAW_PATH)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    report = analyze(_load(args.raw), _load(PREREG_PATH), _load(DATASET_PATH), _load(LOCK_PATH))
    if args.write:
        ANALYSIS_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        MARKDOWN_PATH.write_text(_markdown(report), encoding="utf-8")
    print(json.dumps({"decision": report["decision"], "automatic_gates": report["automatic_gates"], "metrics": report["metrics"], "paired_effect": report["paired_effect"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
